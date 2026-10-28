"""Configuration checks that do not import the optional MCP SDK."""

import sys
from urllib.parse import urlsplit

from wirecloud.platform.plugins import ImproperlyConfigured


def validate_mcp_settings(settings, offline=False) -> None:
    if sys.version_info < (3, 11):
        raise ImproperlyConfigured("The MCP plugin requires Python 3.11 or newer")

    public_url = getattr(settings, "MCP_PUBLIC_URL", "")
    parsed = urlsplit(public_url)
    if (
        not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or not parsed.path.endswith("/mcp")
    ):
        raise ImproperlyConfigured("MCP_PUBLIC_URL must be the absolute public URL ending in /mcp")

    local_http = parsed.scheme == "http" and parsed.hostname in ("localhost", "127.0.0.1", "::1")
    if parsed.scheme != "https" and not local_http:
        raise ImproperlyConfigured("MCP requires HTTPS (HTTP is allowed only on loopback for development)")
