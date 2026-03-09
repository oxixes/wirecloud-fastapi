# -*- coding: utf-8 -*-

from wirecloud.commons import urls
from wirecloud.platform.plugins import URLTemplate


def test_get_urlpatterns_default_and_oidc(monkeypatch):
    original_login = urls.patterns["login"]
    try:
        monkeypatch.setattr(urls.settings, "OID_CONNECT_ENABLED", False)
        monkeypatch.setattr(urls.settings, "OID_CONNECT_PLUGIN", "")
        monkeypatch.setattr(urls, "get_idm_get_authorization_url_functions", lambda: {})
        plain = urls.get_urlpatterns()
        assert plain["login"].urlpattern == "/login"

        monkeypatch.setattr(urls.settings, "OID_CONNECT_ENABLED", True)
        monkeypatch.setattr(urls.settings, "OID_CONNECT_PLUGIN", "keycloak")
        monkeypatch.setattr(
            urls,
            "get_idm_get_authorization_url_functions",
            lambda: {"keycloak": (lambda: URLTemplate(urlpattern="/oidc/login", defaults={"x": "1"}))},
        )
        updated = urls.get_urlpatterns()
        assert updated["login"].urlpattern == "/oidc/login"

        monkeypatch.setattr(urls.settings, "OID_CONNECT_PLUGIN", "missing")
        unchanged = urls.get_urlpatterns()
        assert unchanged["login"].urlpattern == "/oidc/login"
    finally:
        urls.patterns["login"] = original_login

