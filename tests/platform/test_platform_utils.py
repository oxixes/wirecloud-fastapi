# -*- coding: utf-8 -*-

from starlette.requests import Request

from wirecloud.platform import utils


def _request(query_string=b"", headers=None):
    return Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": "GET",
            "path": "/",
            "query_string": query_string,
            "headers": headers or [],
        }
    )


def test_get_current_theme_uses_query_when_available(monkeypatch):
    monkeypatch.setattr(utils.settings, "AVAILABLE_THEMES", ("wirecloud.defaulttheme", "other"))
    monkeypatch.setattr(utils.settings, "THEME_ACTIVE", "wirecloud.defaulttheme")

    req = _request(query_string=b"themeactive=other")
    assert utils.get_current_theme(req) == "other"

    req2 = _request(query_string=b"themeactive=missing")
    assert utils.get_current_theme(req2) == "wirecloud.defaulttheme"


def test_get_current_view_prefers_mode_and_falls_back_to_user_agent(monkeypatch):
    req = _request(query_string=b"mode=embedded", headers=[(b"user-agent", b"Desktop")])
    assert utils.get_current_view(req) == "embedded"
    assert utils.get_current_view(req, ignore_query=True) == "classic"

    monkeypatch.setattr(utils.user_agents, "parse", lambda _ua: type("UA", (), {"is_mobile": True})())
    mobile = _request(headers=[(b"user-agent", b"Mobile")])
    assert utils.get_current_view(mobile) == "smartphone"
