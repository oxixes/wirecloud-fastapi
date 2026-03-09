# -*- coding: utf-8 -*-

from fastapi import Response
from starlette.requests import Request

from wirecloud.commons import middleware


def _http_request(path="/", query="", headers=None, cookies=None):
    raw_headers = []
    for key, value in (headers or {}).items():
        raw_headers.append((key.lower().encode("latin-1"), value.encode("latin-1")))
    req = Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": "GET",
            "path": path,
            "query_string": query.encode("latin-1"),
            "headers": raw_headers,
        }
    )
    req._cookies = cookies or {}
    return req


def test_get_language_from_req_data_branches(monkeypatch):
    monkeypatch.setattr(middleware, "DEFAULT_LANGUAGE", "en")
    monkeypatch.setattr(middleware, "AVAILABLE_LANGUAGES", ["en", "es", "pt"])

    assert middleware.get_language_from_req_data(None, None, None) == "en"
    assert middleware.get_language_from_req_data("fr;q=1.0,es;q=0.4,pt;q=0.9", None, None) == "pt"
    assert middleware.get_language_from_req_data("es;q=oops,en;q=0.7", None, None) == "es"
    assert middleware.get_language_from_req_data("en;foo=1", None, None) == "en"
    assert middleware.get_language_from_req_data("fr;q=0.9", None, None) == "en"
    assert middleware.get_language_from_req_data("pt;q=0.9", "es", "pt") == "es"
    assert middleware.get_language_from_req_data("pt;q=0.9", None, "es") == "es"
    assert middleware.get_language_from_req_data("en,fr", None, None) == "en"

    class _FlipList(list):
        def __init__(self, *args):
            super().__init__(*args)
            self._calls = 0

        def __contains__(self, item):
            self._calls += 1
            if self._calls <= 2:
                return True
            return item == "pt"

    monkeypatch.setattr(middleware, "AVAILABLE_LANGUAGES", _FlipList(["en", "pt"]))
    assert middleware.get_language_from_req_data("en;q=0.9,pt;q=0.8", None, None) == "pt"


async def test_locale_middleware_dispatch_sets_language(monkeypatch):
    monkeypatch.setattr(middleware, "get_language_from_req_data", lambda *_args: "es")
    req = _http_request(query="lang=pt", headers={"accept-language": "en"}, cookies={"lang": "pt"})
    mw = middleware.LocaleMiddleware(app=lambda *_a, **_k: None)

    async def _call_next(_request):
        return Response("ok", media_type="text/plain")

    response = await mw.dispatch(req, _call_next)
    assert req.state.lang == "es"
    assert response.headers["Content-Language"] == "es"


async def test_locale_ws_middleware_handles_non_ws_and_ws(monkeypatch):
    calls = {"n": 0, "lang": None}

    async def _app(scope, _receive, _send):
        calls["n"] += 1
        calls["lang"] = scope.get("state", {}).get("lang")

    mw = middleware.LocaleWSMiddleware(_app)
    monkeypatch.setattr(middleware, "get_language_from_req_data", lambda *_args: "pt")

    scope_http = {"type": "http", "state": {}}
    await mw(scope_http, None, None)
    assert calls["n"] == 1
    assert calls["lang"] is None

    scope_ws = {
        "type": "websocket",
        "headers": [(b"accept-language", b"es"), (b"cookie", b"lang=es")],
        "query_string": b"lang=pt",
        "state": {},
    }
    await mw(scope_ws, None, None)
    assert calls["n"] == 2
    assert calls["lang"] == "pt"

    scope_ws_no_cookie = {
        "type": "websocket",
        "headers": [(b"accept-language", b"es")],
        "query_string": b"",
        "state": {},
    }
    await mw(scope_ws_no_cookie, None, None)
    assert calls["n"] == 3


async def test_content_type_utf8_middleware_dispatch_branches():
    req = _http_request()
    mw = middleware.ContentTypeUTF8Middleware(app=lambda *_a, **_k: None)

    async def _no_header(_request):
        return Response("ok")

    async def _already_charset(_request):
        return Response("ok", media_type="text/plain; charset=utf-8")

    async def _append(_request):
        return Response("ok", media_type="text/plain")

    r1 = await mw.dispatch(req, _no_header)
    assert "Content-Type" not in r1.headers

    r2 = await mw.dispatch(req, _already_charset)
    assert r2.headers["Content-Type"] == "text/plain; charset=utf-8"

    r3 = await mw.dispatch(req, _append)
    assert r3.headers["Content-Type"] == "text/plain; charset=utf-8"


def test_install_all_middlewares():
    added = []

    class _App:
        def add_middleware(self, middleware_cls):
            added.append(middleware_cls)

    middleware.install_all_middlewares(_App())
    assert added == [
        middleware.LocaleMiddleware,
        middleware.LocaleWSMiddleware,
        middleware.GZipMiddleware,
        middleware.ContentTypeUTF8Middleware,
    ]
