"""Register MCP as an optional WireCloud plugin."""

from typing import Callable, Optional
from urllib.parse import urlsplit

from fastapi import FastAPI

from wirecloud import settings
from wirecloud.mcp.validators import validate_mcp_settings
from wirecloud.oauth2provider import OAuthResource, register_resource
from wirecloud.platform.plugins import ImproperlyConfigured, WirecloudPlugin


class WirecloudMCPPlugin(WirecloudPlugin):
    features = {"MCP": "1.0.0"}

    def __init__(self, app: Optional[FastAPI]):
        super().__init__(app)
        self.server = None
        if app is None:
            return

        # Builds and ordinary installations must not import the optional SDK.
        try:
            from wirecloud.mcp.server import create_server
            from wirecloud.mcp.routes import create_router
            from wirecloud.mcp.middleware import MCPCORSMiddleware
            from wirecloud.mcp.tools import READ, SCOPES
        except ImportError as exc:
            raise ImproperlyConfigured("Install wirecloud[mcp] to enable the MCP plugin") from exc

        audience = settings.MCP_PUBLIC_URL.rstrip("/")
        parsed = urlsplit(audience)
        origins = [f"{parsed.scheme}://{parsed.netloc}", *getattr(settings, "MCP_ALLOWED_ORIGINS", [])]

        register_resource(app, OAuthResource(audience, SCOPES, "WireCloud MCP", (READ,)))
        self.server = create_server()
        app.state.mcp_server = self.server
        app.state.mcp_audience = audience
        app.add_middleware(MCPCORSMiddleware, origins=origins)
        app.include_router(create_router(app, self.server, audience, origins), tags=["MCP"])

    def get_config_validators(self) -> tuple[Callable, ...]:
        return (validate_mcp_settings,)
