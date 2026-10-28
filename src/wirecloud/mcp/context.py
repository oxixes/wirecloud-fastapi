"""Identity and database session shared by one authenticated MCP request."""

from contextvars import ContextVar
from dataclasses import dataclass

from fastapi import Request

from wirecloud.database import DBSession
from wirecloud.oauth2provider import OAuthPrincipal


@dataclass(frozen=True)
class MCPCallContext:
    db: DBSession
    principal: OAuthPrincipal
    request: Request


call_context: ContextVar[MCPCallContext] = ContextVar("wirecloud_mcp_call")
