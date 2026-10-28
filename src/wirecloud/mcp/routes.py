# -*- coding: utf-8 -*-
# Copyright (c) 2026 Future Internet Consulting and Development Solutions S.L.

# This file is part of Wirecloud.

# Wirecloud is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# Wirecloud is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with Wirecloud.  If not, see <http://www.gnu.org/licenses/>.

from contextlib import asynccontextmanager
from typing import AsyncIterator, Sequence
from urllib.parse import urlsplit

from fastapi import APIRouter, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from mcp.server import MCPServer
from mcp.server.transport_security import TransportSecuritySettings
from starlette.routing import Route

from wirecloud.database import DBDep, commit, get_session
from wirecloud.mcp import packages
from wirecloud.mcp.middleware import MCPAuthenticationMiddleware
from wirecloud.mcp.tools import INSTALL
from wirecloud.oauth2provider import require_access

upload_router = APIRouter()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    provider = app.dependency_overrides.get(get_session, get_session)
    async for db in provider():
        await packages.ensure_upload_indexes(db)
        await commit(db)

    async with app.state.mcp_server.session_manager.run():
        yield


def create_router(app: FastAPI, server: MCPServer, audience: str, origins: Sequence[str]) -> APIRouter:
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
async def upload_package(request: Request, db: DBDep) -> JSONResponse:
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
