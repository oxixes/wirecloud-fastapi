"""WireCloud-owned OAuth endpoints. Resource plugins only register audiences."""
from __future__ import annotations

import hmac
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode, urlsplit

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse, RedirectResponse
from starlette.middleware.cors import CORSMiddleware

from wirecloud import settings
from wirecloud.database import DBDep, commit
from wirecloud.oauth2provider import service as auth
from wirecloud.commons.auth.utils import get_token_contents, get_user
from wirecloud.oauth2provider.pages import render_page

router = APIRouter()
metadata_router = APIRouter()


class AuthorizationCORSMiddleware:
    """Public OAuth protocol endpoints support browser clients, without cookies.

    Consent, sign-in, and connection management retain same-origin protections.
    """
    def __init__(self, app):
        self.app = app
        self.cors = CORSMiddleware(app, allow_origins=["*"], allow_methods=["GET", "POST"],
            allow_headers=["Authorization", "Content-Type"], expose_headers=["WWW-Authenticate"])

    async def __call__(self, scope, receive, send):
        path = scope.get("path", "")
        prefix = scope.get("root_path", "").rstrip("/")
        if prefix and path.startswith(prefix + "/"):
            path = path[len(prefix):]
        if scope["type"] == "http" and (path.startswith("/.well-known/oauth-") or path in (
            "/oauth2/token", "/oauth2/register", "/oauth2/revoke")):
            return await self.cors(scope, receive, send)
        return await self.app(scope, receive, send)


async def oauth_error_handler(request, exc):
    return JSONResponse(exc.detail, exc.status_code, headers={"Cache-Control": "no-store"})


async def browser_identity(request, db):
    # A browser consent is never authenticated by a bearer token or URL argument.
    token = await get_token_contents(request.cookies.get("token", ""), request, db, csrf=False)
    user = await get_user(db, token, False)
    if token and "real_user" in token:
        raise HTTPException(403, "End impersonation before connecting an application")
    return user, token


@metadata_router.get("/.well-known/oauth-authorization-server")
@metadata_router.get("/.well-known/oauth-authorization-server/oauth2")
@metadata_router.get("/.well-known/oauth-authorization-server/{issuer_path:path}")
async def authorization_metadata(request: Request):
    resources = getattr(request.app.state, "oauth2_resources", {})
    if not resources:
        raise HTTPException(404)
    issuer = auth.public_base(request) + "/oauth2"
    result = {"issuer": issuer, "authorization_endpoint": issuer + "/authorize", "token_endpoint": issuer + "/token",
              "revocation_endpoint": issuer + "/revoke", "response_types_supported": ["code"],
              "grant_types_supported": ["authorization_code", "refresh_token"],
              "code_challenge_methods_supported": ["S256"], "client_id_metadata_document_supported": True,
              "authorization_response_iss_parameter_supported": True,
              "token_endpoint_auth_methods_supported": ["none", "client_secret_post", "client_secret_basic"],
              "scopes_supported": sorted({s for r in resources.values() for s in r.scopes})}
    if getattr(settings, "OAUTH2_DYNAMIC_REGISTRATION", True):
        result["registration_endpoint"] = issuer + "/register"
    return result


@metadata_router.get("/.well-known/oauth-protected-resource")
@metadata_router.get("/.well-known/oauth-protected-resource/{resource_path:path}")
async def resource_metadata(request: Request, resource_path: str = ""):
    for resource in getattr(request.app.state, "oauth2_resources", {}).values():
        if urlsplit(resource.audience).path.rstrip("/") == "/" + resource_path.strip("/") or (
                not resource_path and len(getattr(request.app.state, "oauth2_resources", {})) == 1):
            return {"resource": resource.audience, "resource_name": resource.name,
                    "authorization_servers": [auth.public_base(request) + "/oauth2"],
                    "scopes_supported": list(resource.scopes), "bearer_methods_supported": ["header"]}
    raise HTTPException(404)


@router.post("/register", status_code=201)
async def register(request: Request, db: DBDep):
    if not getattr(request.app.state, "oauth2_resources", {}) or not getattr(settings, "OAUTH2_DYNAMIC_REGISTRATION", True):
        raise HTTPException(404)
    bucket = "registration:" + auth.digest(request.client.host) + ":" + auth.now().strftime("%Y%m%d%H")
    count = await db.client.oauth_attempts.find_one_and_update(
        {"_id": bucket}, {"$inc": {"count": 1}, "$setOnInsert": {"expires_at": auth.now() + timedelta(hours=1)}}, upsert=True)
    await commit(db)
    if count and count["count"] >= 60:
        raise HTTPException(429, "Too many registrations")
    try:
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > 65536:
                auth.oauth_error("invalid_client_metadata", "Metadata too large")
        import json
        data = json.loads(body)
        client = auth.validate_client(data)
    except (ValueError, AttributeError, TypeError):
        auth.oauth_error("invalid_client_metadata", "Invalid metadata")
    client["client_id"] = auth.random_token()
    response = dict(client)
    if client["token_endpoint_auth_method"] != "none":
        secret = auth.random_token()
        client["secret_hash"] = auth.digest(secret)
        response.update(client_secret=secret, client_secret_expires_at=0)
    await db.client.oauth_clients.insert_one(client)
    await commit(db)
    return JSONResponse(response, 201, headers={"Cache-Control": "no-store"})


@router.get("/authorize")
async def authorize(request: Request, db: DBDep):
    q = request.query_params
    resource = auth.get_resource(request, q.get("resource", ""))
    client = await auth.get_client(db, q.get("client_id", ""))
    redirect = q.get("redirect_uri", "")
    if not any(auth.redirect_matches(registered, redirect) for registered in client["redirect_uris"]):
        auth.oauth_error(description="Unregistered redirect URI")
    if q.get("response_type") != "code" or q.get("code_challenge_method") != "S256" or not re.fullmatch(r"[A-Za-z0-9_-]{43}", q.get("code_challenge", "")):
        auth.oauth_error(description="Authorization code with S256 PKCE is required")
    scopes = q.get("scope", " ".join(resource.default_scopes)).split()
    if not scopes or not set(scopes).issubset(resource.scopes) or len(q.get("state", "")) > 2048:
        auth.oauth_error("invalid_scope", "Unknown or empty scopes")
    handle, csrf = auth.random_token(), auth.random_token()
    browser = request.cookies.get("wc_oauth_browser") or auth.random_token()
    await db.client.oauth_attempts.insert_one({"_id": auth.digest(handle), "client_id": client["client_id"],
        "client_name": client["client_name"], "redirect_uri": redirect, "audience": resource.audience,
        "scopes": scopes, "challenge": q["code_challenge"], "state": q.get("state"),
        "browser": auth.digest(browser), "csrf": auth.digest(csrf), "expires_at": auth.now() + timedelta(minutes=10)})
    await commit(db)
    # CSRF is an unguessable form token, not an authorization code or credential.
    response = RedirectResponse(auth.public_base(request) + "/oauth2/consent?" + urlencode({"request_id": handle, "csrf": csrf}), 302)
    response.set_cookie("wc_oauth_browser", browser, secure=auth.public_base(request).startswith("https:"),
                        httponly=True, samesite="lax", max_age=600)
    return response


async def attempt_for_browser(request, db, handle, csrf):
    attempt = await db.client.oauth_attempts.find_one({"_id": auth.digest(handle), "expires_at": {"$gt": auth.now()}})
    if attempt is None or not hmac.compare_digest(attempt["browser"], auth.digest(request.cookies.get("wc_oauth_browser", ""))) or not hmac.compare_digest(attempt["csrf"], auth.digest(csrf)):
        auth.oauth_error(description="Expired or invalid browser authorization attempt")
    return attempt


@router.get("/consent")
async def consent(request: Request, db: DBDep, request_id: str, csrf: str):
    attempt = await attempt_for_browser(request, db, request_id, csrf)
    resource = auth.get_resource(request, attempt["audience"])
    user, token = await browser_identity(request, db)
    if user is None:
        target = request.url.path + "?" + urlencode({"request_id": request_id, "csrf": csrf})
        return RedirectResponse(auth.public_base(request) + "/auth/login?" + urlencode({"return_to": target}), 302)
    # Bind the displayed consent to this user and session, including when another
    # tab signs in to a different account before the form is submitted.
    binding = {"user_id": str(user.id), "session_id": token["jti"]}
    bound = await db.client.oauth_attempts.update_one({"_id": attempt["_id"], "$or": [
        {"session_id": {"$exists": False}}, binding]}, {"$set": binding})
    if not bound.matched_count:
        auth.oauth_error(description="Sign-in session changed; start authorization again")
    await commit(db)
    return render_page(request, "consent", {"user": user, "resource": resource, "attempt": attempt,
        "permissions": [resource.scopes[scope] for scope in attempt["scopes"]], "request_id": request_id, "csrf": csrf},
        form_redirect_uri=attempt["redirect_uri"])


@router.post("/consent")
async def approve(request: Request, db: DBDep):
    form = await request.form(max_files=0, max_fields=5)
    attempt = await attempt_for_browser(request, db, str(form.get("request_id", "")), str(form.get("csrf", "")))
    user, token = await browser_identity(request, db)
    if user is None:
        raise HTTPException(401, "Sign in before authorizing")
    consumed = await db.client.oauth_attempts.find_one_and_delete({"_id": attempt["_id"],
        "user_id": str(user.id), "session_id": token["jti"]})
    if consumed is None:
        auth.oauth_error(description="Authorization attempt already used or sign-in session changed")
    params = {"iss": auth.public_base(request) + "/oauth2"}
    if attempt.get("state") is not None:
        params["state"] = attempt["state"]
    if form.get("decision") != "approve":
        params["error"] = "access_denied"
    else:
        grant_id, code = auth.random_token(), auth.random_token()
        expiration = min(auth.utc((await db.client.tokens.find_one({"_id": token_id(token)}))["expiration"]),
                         datetime.fromtimestamp(token["exp"], tz=timezone.utc))
        await db.client.oauth_grants.insert_one({"_id": grant_id, "client_id": attempt["client_id"],
            "client_name": attempt["client_name"], "user_id": str(user.id), "session_id": token["jti"],
            "audience": attempt["audience"], "scopes": attempt["scopes"], "revoked": False,
            "created_at": auth.now(), "expires_at": expiration})
        await db.client.oauth_codes.insert_one({"_id": auth.digest(code), "grant_id": grant_id,
            "client_id": attempt["client_id"], "audience": attempt["audience"], "redirect_uri": attempt["redirect_uri"],
            "challenge": attempt["challenge"], "expires_at": auth.now() + timedelta(seconds=60)})
        params["code"] = code
    await commit(db)
    separator = "&" if "?" in attempt["redirect_uri"] else "?"
    return RedirectResponse(attempt["redirect_uri"] + separator + urlencode(params), 302, headers={"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"})


def token_id(token):
    from wirecloud.database import Id
    return Id(token["jti"])


@router.post("/token")
async def token_endpoint(request: Request, db: DBDep):
    form = await request.form(max_files=0, max_fields=12)
    client = await auth.authenticate_client(db, form, request.headers.get("authorization", ""))
    auth.get_resource(request, str(form.get("resource", "")))
    if form.get("grant_type") == "authorization_code":
        result = await auth.exchange_code(db, client, form)
    elif form.get("grant_type") == "refresh_token":
        result = await auth.exchange_refresh(db, client, form)
    else:
        auth.oauth_error("unsupported_grant_type", "Unsupported grant")
    await commit(db)
    return JSONResponse(result, headers={"Cache-Control": "no-store", "Pragma": "no-cache"})


@router.post("/revoke")
async def revoke(request: Request, db: DBDep):
    form = await request.form(max_files=0, max_fields=5)
    client = await auth.authenticate_client(db, form, request.headers.get("authorization", ""))
    record = await db.client.oauth_tokens.find_one({"_id": auth.digest(str(form.get("token", "")))})
    if record:
        await db.client.oauth_grants.update_one({"_id": record["grant_id"], "client_id": client["client_id"]}, {"$set": {"revoked": True}})
    await commit(db)
    return JSONResponse({}, headers={"Cache-Control": "no-store"})


@router.get("/connections")
async def connections(request: Request, db: DBDep):
    user, token = await browser_identity(request, db)
    if user is None:
        if "application/json" in request.headers.get("accept", ""):
            raise HTTPException(401, "Sign in to manage app connections")
        return RedirectResponse(auth.public_base(request) + "/auth/login?" + urlencode({"return_to": request.url.path}), 302)
    csrf = auth.random_token()
    browser = request.cookies.get("wc_oauth_browser") or auth.random_token()
    await db.client.oauth_attempts.insert_one({"_id": auth.digest(csrf), "browser": auth.digest(browser),
        "session_id": token["jti"], "expires_at": auth.now() + timedelta(minutes=10), "purpose": "revoke"})
    rows = []
    async for grant in db.client.oauth_grants.find({"user_id": str(user.id), "revoked": False, "expires_at": {"$gt": auth.now()}}):
        resource = getattr(request.app.state, "oauth2_resources", {}).get(grant["audience"])
        if auth.utc(grant["expires_at"]) <= auth.now():
            continue
        rows.append({"id": grant["_id"], "client_name": grant["client_name"], "client_id": grant["client_id"],
                     "resource_name": resource.name if resource else grant["audience"],
                     "permissions": [resource.scopes.get(scope, scope) if resource else scope for scope in grant["scopes"]]})
    await commit(db)
    if "application/json" in request.headers.get("accept", ""):
        response = JSONResponse({"connections": rows, "csrf": csrf}, headers={"Cache-Control": "no-store"})
    else:
        response = render_page(request, "connections", {"user": user, "connections": rows, "csrf": csrf})
    response.headers["Vary"] = "Accept"
    response.set_cookie("wc_oauth_browser", browser, httponly=True, secure=auth.public_base(request).startswith("https:"), samesite="lax", max_age=600)
    return response


@router.post("/connections")
async def revoke_connection(request: Request, db: DBDep):
    user, token = await browser_identity(request, db)
    if user is None:
        raise HTTPException(401)
    form = await request.form(max_files=0, max_fields=3)
    valid = await db.client.oauth_attempts.find_one_and_delete({"_id": auth.digest(str(form.get("csrf", ""))),
        "browser": auth.digest(request.cookies.get("wc_oauth_browser", "")), "session_id": token["jti"],
        "purpose": "revoke", "expires_at": {"$gt": auth.now()}})
    if valid is None:
        raise HTTPException(403, "Invalid CSRF token")
    await db.client.oauth_grants.update_one({"_id": str(form.get("grant_id", "")), "user_id": str(user.id)}, {"$set": {"revoked": True}})
    await commit(db)
    if "application/json" in request.headers.get("accept", ""):
        return JSONResponse({"revoked": True}, headers={"Cache-Control": "no-store", "Vary": "Accept"})
    return RedirectResponse(request.url.path, 303)
