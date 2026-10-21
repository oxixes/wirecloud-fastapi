"""Optional OAuth authorization server shared by client-facing plugins."""
from contextlib import asynccontextmanager
from urllib.parse import urlsplit

from wirecloud.database import commit, get_session
from wirecloud.oauth2provider import routes, service
from wirecloud.platform.plugins import AjaxEndpoint, ImproperlyConfigured, URLTemplate, WirecloudPlugin


class OAuth2ProviderPlugin(WirecloudPlugin):
    features = {"OAuth2Provider": "1.0"}
    urls = {f"oauth2provider.{name}": URLTemplate(urlpattern=f"/oauth2/{name}", defaults={})
            for name in ("authorize", "token", "register", "revoke", "connections")}

    def __init__(self, app):
        super().__init__(app)
        if app is None:
            return
        app.include_router(routes.router, prefix="/oauth2", tags=["OAuth2"])
        app.include_router(routes.metadata_router, tags=["OAuth2"])
        app.add_exception_handler(service.OAuthError, routes.oauth_error_handler)
        app.add_middleware(routes.AuthorizationCORSMiddleware)

    def get_ajax_endpoints(self, view, request):
        if view not in ("classic", "smartphone"):
            return ()
        prefix = (request.scope.get("root_path") or "").rstrip("/")
        return (AjaxEndpoint(id="OAUTH2_CONNECTIONS", url=prefix + self.urls["oauth2provider.connections"].urlpattern),)

    def get_config_validators(self):
        def validate(settings, offline=False):
            base = getattr(settings, "OAUTH2_PUBLIC_URL", "")
            if base and (not service.valid_redirect(base) or urlsplit(base).query):
                raise ImproperlyConfigured("OAUTH2_PUBLIC_URL must be an HTTPS or loopback public base URL")
            if not isinstance(getattr(settings, "OAUTH2_DYNAMIC_REGISTRATION", True), bool):
                raise ImproperlyConfigured("OAUTH2_DYNAMIC_REGISTRATION must be a boolean")
            for client in getattr(settings, "OAUTH2_CLIENTS", []):
                service.validate_client(client)
        return (validate,)

    @asynccontextmanager
    async def lifespan(self):
        provider = self.app.dependency_overrides.get(get_session, get_session)
        async for db in provider():
            await service.ensure_indexes(db)
            await commit(db)
        yield
