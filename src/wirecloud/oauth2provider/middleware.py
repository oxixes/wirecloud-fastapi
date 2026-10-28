"""CORS for public OAuth protocol endpoints, without browser credentials."""

from starlette.middleware.cors import CORSMiddleware


class AuthorizationCORSMiddleware:
    def __init__(self, app):
        self.app = app
        self.cors = CORSMiddleware(
            app,
            allow_origins=["*"],
            allow_methods=["GET", "POST"],
            allow_headers=["Authorization", "Content-Type"],
            expose_headers=["WWW-Authenticate"],
        )

    async def __call__(self, scope, receive, send):
        path = scope.get("path", "")
        prefix = scope.get("root_path", "").rstrip("/")
        if prefix and path.startswith(prefix + "/"):
            path = path[len(prefix) :]

        public_endpoint = path.startswith("/.well-known/oauth-") or path in (
            "/oauth2/token",
            "/oauth2/register",
            "/oauth2/revoke",
        )
        if scope["type"] == "http" and public_endpoint:
            return await self.cors(scope, receive, send)
        return await self.app(scope, receive, send)
