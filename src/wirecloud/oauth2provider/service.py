"""Provider-independent delegated authorization, shared by WireCloud features.

No MCP or identity-provider dependencies belong in this module. A resource server
registers its audience/scopes and receives a current WireCloud principal.
"""

from __future__ import annotations

import base64
import hmac
import ipaddress
import socket
from dataclasses import dataclass
from datetime import timedelta
from urllib.parse import urlsplit

import httpx
from fastapi import HTTPException, Request

from wirecloud import settings
from wirecloud.commons.auth.crud import get_user_with_all_info, is_token_valid
from wirecloud.commons.auth.schemas import UserAll
from wirecloud.commons.auth.tokens import digest, now, pkce, random_token, utc
from wirecloud.database import DBSession, Id, commit
from wirecloud.oauth2provider import crud


class OAuthError(HTTPException):
    pass


def oauth_error(error="invalid_request", description="Invalid authorization request", status=400):
    raise OAuthError(status, {"error": error, "error_description": description})


@dataclass(frozen=True)
class OAuthResource:
    audience: str
    scopes: dict[str, str]
    name: str
    default_scopes: tuple[str, ...] = ()


@dataclass
class OAuthPrincipal:
    user: UserAll
    client_id: str
    grant_id: str
    session_id: str
    audience: str
    scopes: frozenset[str]

    def require(self, *scopes):
        if not set(scopes).issubset(self.scopes):
            raise HTTPException(403, {"error": "insufficient_scope", "required_scopes": list(scopes)})


def register_resource(app, resource: OAuthResource):
    from wirecloud.platform.plugins import ImproperlyConfigured

    if "wirecloud.oauth2provider" not in settings.INSTALLED_APPS:
        raise ImproperlyConfigured("Enable wirecloud.oauth2provider to register OAuth resources")

    parsed = urlsplit(resource.audience)
    if (
        not valid_redirect(resource.audience)
        or parsed.query
        or parsed.fragment
        or not resource.scopes
        or not set(resource.default_scopes).issubset(resource.scopes)
        or any(
            not scope
            or any(
                character.isspace() or character in '\\"' or ord(character) < 33 or ord(character) > 126
                for character in scope
            )
            for scope in resource.scopes
        )
    ):
        raise ImproperlyConfigured("OAuth resources require an HTTPS or loopback audience and valid scopes")
    resources = getattr(app.state, "oauth2_resources", {})
    if resource.audience in resources:
        raise ImproperlyConfigured("OAuth resource audience is already registered")
    resources[resource.audience] = resource
    app.state.oauth2_resources = resources


def get_resource(request, audience):
    resource = getattr(request.app.state, "oauth2_resources", {}).get(audience)
    if resource is None:
        oauth_error("invalid_target", "Unknown resource")
    return resource


def public_base(request: Request) -> str:
    configured = getattr(settings, "OAUTH2_PUBLIC_URL", "")
    if configured:
        return configured.rstrip("/")
    from wirecloud.commons.auth.tokens import public_base as login_base

    return login_base(request)


def resource_metadata_url(audience):
    parsed = urlsplit(audience)
    return f"{parsed.scheme}://{parsed.netloc}/.well-known/oauth-protected-resource{parsed.path.rstrip('/')}"


def valid_redirect(uri: str) -> bool:
    if len(uri) > 2048 or any(ord(c) < 33 for c in uri) or "\\" in uri:
        return False
    try:
        parsed = urlsplit(uri)
        if parsed.port is not None and not 0 < parsed.port < 65536:
            return False
    except ValueError:
        return False
    if parsed.username or parsed.password or parsed.fragment or not parsed.hostname:
        return False
    return parsed.scheme == "https" or (
        parsed.scheme == "http" and parsed.hostname in ("127.0.0.1", "::1", "localhost")
    )


def redirect_matches(registered, requested):
    if registered == requested:
        return True
    if not valid_redirect(requested):
        return False
    original, actual = urlsplit(registered), urlsplit(requested)
    # RFC 8252 loopback callbacks use ephemeral ports. All other URI parts
    # remain exact, and the code is bound to the full selected callback URI.
    return (
        original.scheme == actual.scheme == "http"
        and original.hostname in ("127.0.0.1", "::1")
        and original.hostname == actual.hostname
        and original.path == actual.path
        and original.query == actual.query
    )


def validate_client(data):
    redirects = data.get("redirect_uris", [])
    if (
        not isinstance(redirects, list)
        or not redirects
        or len(redirects) > 20
        or any(not isinstance(uri, str) or not valid_redirect(uri) for uri in redirects)
    ):
        oauth_error("invalid_client_metadata", "Explicit HTTPS or loopback redirect URIs are required")
    method = data.get("token_endpoint_auth_method", "none")
    if method not in ("none", "client_secret_post", "client_secret_basic"):
        oauth_error("invalid_client_metadata", "Unsupported client authentication method")
    return {
        "client_name": str(data.get("client_name", "Application"))[:150],
        "redirect_uris": redirects,
        "token_endpoint_auth_method": method,
        "grant_types": ["authorization_code", "refresh_token"],
        "response_types": ["code"],
    }


def bearer_token(request):
    scheme, _, token = request.headers.get("authorization", "").partition(" ")
    return token if scheme.casefold() == "bearer" else ""


async def metadata_client(client_id):
    """Resolve public CIMD documents without allowing metadata SSRF/redirects."""
    try:
        import asyncio

        parsed = urlsplit(client_id)
        if (
            len(client_id) > 2048
            or parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.fragment
            or parsed.port not in (None, 443)
        ):
            oauth_error("invalid_client", "Invalid client metadata URL")
        addresses = await asyncio.wait_for(
            asyncio.get_running_loop().getaddrinfo(parsed.hostname, 443, type=socket.SOCK_STREAM), 5
        )
        if not addresses or any(not ipaddress.ip_address(item[4][0]).is_global for item in addresses):
            raise ValueError()
        # Connect to the validated address, retaining the original Host and TLS name.
        address = addresses[0][4][0]
        host = f"[{address}]" if ":" in address else address
        url = client_id.replace(parsed.netloc, host, 1)
        async with httpx.AsyncClient(timeout=5, follow_redirects=False) as client:
            async with client.stream(
                "GET", url, headers={"Host": parsed.netloc}, extensions={"sni_hostname": parsed.hostname}
            ) as response:
                response.raise_for_status()
                content = bytearray()
                async for chunk in response.aiter_bytes():
                    content.extend(chunk)
                    if len(content) > 65536:
                        raise ValueError()
        import json

        data = json.loads(content)
        if (
            not isinstance(data, dict)
            or data.get("client_id") != client_id
            or data.get("token_endpoint_auth_method", "none") != "none"
        ):
            raise ValueError()
        return dict(validate_client(data), client_id=client_id)
    except (ValueError, OSError, asyncio.TimeoutError, httpx.HTTPError):
        oauth_error("invalid_client", "Cannot resolve client metadata")


async def get_client(db: DBSession, client_id: str):
    client = await crud.get_client_by_id(db, client_id)
    if client is None:
        for candidate in getattr(settings, "OAUTH2_CLIENTS", []):
            if candidate.get("client_id") == client_id:
                client = dict(validate_client(candidate), client_id=client_id)
                if candidate.get("client_secret"):
                    client["secret_hash"] = digest(candidate["client_secret"])
                break
    if client is None and client_id.startswith("https://"):
        client = await metadata_client(client_id)
    if client is None:
        oauth_error("invalid_client", "Unknown client", 401)
    return client


async def authenticate_client(db: DBSession, form, authorization=""):
    client_id = str(form.get("client_id", ""))
    secret = str(form.get("client_secret", ""))
    method = "client_secret_post" if secret else "none"
    scheme, _, credentials = authorization.partition(" ")
    if scheme.casefold() == "basic":
        try:
            from urllib.parse import unquote_plus

            client_id, secret = (
                unquote_plus(v) for v in base64.b64decode(credentials, validate=True).decode().split(":", 1)
            )
            method = "client_secret_basic"
        except (ValueError, UnicodeError):
            oauth_error("invalid_client", "Invalid client authentication", 401)
    client = await get_client(db, client_id)
    if client["token_endpoint_auth_method"] != method or (
        method != "none" and not hmac.compare_digest(client.get("secret_hash", ""), digest(secret))
    ):
        oauth_error("invalid_client", "Invalid client authentication", 401)
    return client


async def active_grant(db: DBSession, grant_id: str):
    grant = await crud.get_unrevoked_grant(db, grant_id)
    if grant is None or utc(grant["expires_at"]) <= now() or not await is_token_valid(db, Id(grant["session_id"])):
        return None
    user = await get_user_with_all_info(db, Id(grant["user_id"]))
    if user is None or not user.is_active:
        return None
    return grant, user


async def verify_access_token(db: DBSession, token: str, audience: str):
    record = await crud.get_token_by_id(db, digest(token), kind="access")
    if record is None or utc(record["expires_at"]) <= now():
        return None
    result = await active_grant(db, record["grant_id"])
    if result is None:
        return None
    grant, user = result
    if grant["audience"] != audience:
        return None
    return OAuthPrincipal(
        user, grant["client_id"], grant["_id"], grant["session_id"], audience, frozenset(record["scopes"])
    )


async def issue_tokens(db: DBSession, grant, scopes):
    access, refresh = random_token(), random_token()
    expiration = min(now() + timedelta(minutes=15), utc(grant["expires_at"]))
    for token, kind, expiry in ((access, "access", expiration), (refresh, "refresh", utc(grant["expires_at"]))):
        await crud.create_token(
            db,
            {
                "_id": digest(token),
                "kind": kind,
                "grant_id": grant["_id"],
                "scopes": list(scopes),
                "expires_at": expiry,
                "used": False,
            }
        )
    return {
        "access_token": access,
        "refresh_token": refresh,
        "token_type": "Bearer",
        "expires_in": max(0, int((expiration - now()).total_seconds())),
        "scope": " ".join(scopes),
    }


async def exchange_code(db: DBSession, client, form):
    verifier = str(form.get("code_verifier", ""))
    if not 43 <= len(verifier) <= 128 or any(
        c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-._~" for c in verifier
    ):
        oauth_error("invalid_grant", "Invalid PKCE verifier")
    code = await crud.consume_code(
        db,
        digest(str(form.get("code", ""))),
        client["client_id"],
        str(form.get("redirect_uri", "")),
        str(form.get("resource", "")),
        pkce(verifier),
        now(),
    )
    if code is None:
        oauth_error("invalid_grant", "Invalid or expired code")
    result = await active_grant(db, code["grant_id"])
    if result is None:
        oauth_error("invalid_grant", "Authorizing session ended")
    return await issue_tokens(db, result[0], result[0]["scopes"])


async def exchange_refresh(db: DBSession, client, form):
    token_id = digest(str(form.get("refresh_token", "")))
    record = await crud.get_token_by_id(db, token_id, kind="refresh")
    if record is None:
        oauth_error("invalid_grant", "Invalid refresh token")
    result = await active_grant(db, record["grant_id"])
    if result is None:
        oauth_error("invalid_grant", "Authorizing session ended")
    grant, _ = result
    if grant["client_id"] != client["client_id"] or grant["audience"] != str(form.get("resource", "")):
        oauth_error("invalid_grant", "Invalid client or resource")
    scopes = str(form.get("scope", " ".join(record["scopes"]))).split()
    if not set(scopes).issubset(record["scopes"]):
        oauth_error("invalid_scope", "Refresh cannot increase access")
    consumed = await crud.consume_refresh_token(db, token_id, now())
    if not consumed:
        await crud.revoke_grant(db, grant["_id"])
        await commit(db)
        oauth_error("invalid_grant", "Refresh token reuse; connection revoked")
    return await issue_tokens(db, grant, scopes)
