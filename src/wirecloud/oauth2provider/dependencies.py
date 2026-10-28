"""Scoped authentication for plugin endpoints; core API authentication is unaffected."""

from fastapi import HTTPException

from wirecloud.oauth2provider.service import bearer_token, get_resource, resource_metadata_url, verify_access_token


async def require_access(request, db, audience, scopes=()):
    resource = get_resource(request, audience)
    if not set(scopes).issubset(resource.scopes):
        raise ValueError("Endpoint requires scopes not declared by its OAuth resource")
    principal = await verify_access_token(db, bearer_token(request), audience)
    challenge = f'Bearer resource_metadata="{resource_metadata_url(audience)}"'
    if scopes:
        challenge += ', scope="' + " ".join(scopes) + '"'
    if principal is None:
        raise HTTPException(
            401, {"error": "invalid_token"}, headers={"WWW-Authenticate": challenge, "Cache-Control": "no-store"}
        )
    if not set(scopes).issubset(principal.scopes):
        raise HTTPException(
            403,
            {"error": "insufficient_scope"},
            headers={"WWW-Authenticate": challenge + ', error="insufficient_scope"', "Cache-Control": "no-store"},
        )
    return principal
