"""Settings validation for the optional OAuth authorization server."""

from urllib.parse import urlsplit

from wirecloud.oauth2provider.service import valid_redirect, validate_client
from wirecloud.platform.plugins import ImproperlyConfigured


def validate_oauth_settings(settings, offline=False) -> None:
    public_url = getattr(settings, "OAUTH2_PUBLIC_URL", "")
    if public_url and (not valid_redirect(public_url) or urlsplit(public_url).query):
        raise ImproperlyConfigured("OAUTH2_PUBLIC_URL must be an HTTPS or loopback public base URL")

    if not isinstance(getattr(settings, "OAUTH2_DYNAMIC_REGISTRATION", True), bool):
        raise ImproperlyConfigured("OAUTH2_DYNAMIC_REGISTRATION must be a boolean")

    for client in getattr(settings, "OAUTH2_CLIENTS", []):
        validate_client(client)
