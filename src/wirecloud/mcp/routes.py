"""MCP's ASGI endpoint, binary upload API, and native FastAPI lifespan."""

from contextlib import asynccontextmanager
from urllib.parse import urlsplit

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from mcp.server.transport_security import TransportSecuritySettings
from starlette.routing import Route

from wirecloud.database import DBDep, commit, get_session
from wirecloud.mcp import packages
from wirecloud.mcp.middleware import MCPAuthenticationMiddleware
from wirecloud.mcp.tools import INSTALL
from wirecloud.oauth2provider import require_access

upload_router = APIRouter()


@asynccontextmanager
async def lifespan(app):
    provider = app.dependency_overrides.get(get_session, get_session)
    async for db in provider():
        await packages.ensure_upload_indexes(db)
        await commit(db)

    async with app.state.mcp_server.session_manager.run():
        yield


def create_router(app, server, audience, origins):
    """Keep the SDK endpoint at /mcp without a mount's trailing-slash redirect."""
    sdk_app = server.streamable_http_app(
        streamable_http_path="/mcp",
        json_response=True,
        stateless_http=True,
        transport_security=TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=[urlsplit(audience).netloc],
            allowed_origins=origins,
        ),
    )
    transport = MCPAuthenticationMiddleware(sdk_app, app, audience)
    router = APIRouter(lifespan=lifespan)
    router.routes.append(Route("/mcp", endpoint=transport))
    router.include_router(upload_router)
    return router


@upload_router.post("/mcp/uploads", status_code=201)
async def upload_package(request: Request, db: DBDep):
    audience = request.app.state.mcp_audience
    principal = await require_access(request, db, audience, (INSTALL,))
    if not (principal.user.has_perm("COMPONENT.INSTALL") or principal.user.is_superuser):
        raise HTTPException(403, "Component install permission is required")

    content = bytearray()
    async for chunk in request.stream():
        content.extend(chunk)
        if len(content) > packages.PACKAGE_LIMIT:
            raise HTTPException(413, "Package exceeds 100 MiB")

    result = await packages.store_upload(db, principal, bytes(content))
    await commit(db)
    return JSONResponse(result, status_code=201, headers={"Cache-Control": "no-store"})
