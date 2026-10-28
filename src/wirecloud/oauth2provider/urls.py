"""Symbolic OAuth endpoint names exposed by the plugin."""

from wirecloud.platform.plugins import URLTemplate

patterns = {
    "oauth2provider.authorize": URLTemplate(urlpattern="/oauth2/authorize", defaults={}),
    "oauth2provider.token": URLTemplate(urlpattern="/oauth2/token", defaults={}),
    "oauth2provider.register": URLTemplate(urlpattern="/oauth2/register", defaults={}),
    "oauth2provider.revoke": URLTemplate(urlpattern="/oauth2/revoke", defaults={}),
    "oauth2provider.connections": URLTemplate(urlpattern="/oauth2/connections", defaults={}),
}
