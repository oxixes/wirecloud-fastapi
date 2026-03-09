# -*- coding: utf-8 -*-

from types import SimpleNamespace

from fastapi import Response
from starlette.requests import Request

from wirecloud.commons import routes
from wirecloud.commons.exceptions import ErrorResponse
from wirecloud.commons.utils.http import NotFound, PermissionDenied


class _ValidationExc:
    def __init__(self, errors):
        self._errors = errors

    def errors(self):
        return self._errors


def _capture_error_builder(monkeypatch):
    captured = {}

    def _build_error_response(request, status, msg, details=None):
        captured["request"] = request
        captured["status"] = status
        captured["msg"] = msg
        captured["details"] = details
        return {"status": status, "msg": msg, "details": details}

    monkeypatch.setattr(routes, "build_error_response", _build_error_response)
    monkeypatch.setattr(routes, "_", lambda text: text)
    return captured


async def test_exception_handlers(monkeypatch):
    request = SimpleNamespace(path="/x")
    captured = _capture_error_builder(monkeypatch)

    payload = Response("boom", status_code=409)
    assert await routes.error_response_handler(request, ErrorResponse(payload)) is payload

    denied = await routes.permission_denied_handler(request, PermissionDenied("nope"))
    assert denied["status"] == 403
    assert denied["msg"] == "nope"

    denied_default = await routes.permission_denied_handler(request, PermissionDenied(""))
    assert denied_default["msg"] == "Permission denied"

    not_found = await routes.not_found_handler(request, NotFound("missing"))
    assert not_found["status"] == 404
    assert not_found["msg"] == "missing"

    not_found_default = await routes.not_found_handler(request, NotFound(""))
    assert not_found_default["msg"] == "Resource not found"

    validation = await routes.validation_exception_handler(
        request,
        _ValidationExc(
            [
                {"loc": ("query", "x"), "msg": "required"},
                {"loc": ("query", "x"), "msg": "invalid"},
                {"loc": ("body", "y"), "msg": "bad"},
            ]
        ),
    )
    assert validation["status"] == 422
    assert validation["details"] == {"query.x": ["required", "invalid"], "body.y": ["bad"]}

    value = await routes.value_error_handler(request, ValueError("wrong"))
    assert value["status"] == 400
    assert value["msg"] == "wrong"

    value_default = await routes.value_error_handler(request, ValueError(""))
    assert value_default["msg"] == "Invalid value"
    assert captured["request"] == request


async def test_general_exception_handler(monkeypatch):
    captured = _capture_error_builder(monkeypatch)
    request = SimpleNamespace(path="/x")

    monkeypatch.setattr(routes.settings, "DEBUG", False)
    result = await routes.general_exception_handler(request, RuntimeError("boom"))
    assert result["status"] == 500
    assert result["msg"] == "An unexpected error occurred"

    monkeypatch.setattr(routes.settings, "DEBUG", True)
    result_debug = await routes.general_exception_handler(request, RuntimeError("boom"))
    assert result_debug["msg"] == "An unexpected error occurred: boom"
    assert captured["status"] == 500


def test_get_js_catalogue_route(monkeypatch):
    monkeypatch.setattr(routes, "get_javascript_catalogue", lambda language, theme: f"{language}:{theme}")
    response = routes.get_js_catalogue("defaulttheme", "es")
    assert response.media_type == "application/javascript"
    assert response.body == b"es:defaulttheme"


async def test_search_resources_branches(db_session, monkeypatch):
    captured = _capture_error_builder(monkeypatch)
    request = Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": "GET",
            "path": "/api/search",
            "query_string": b"",
            "headers": [(b"accept", b"application/json")],
        }
    )
    user = SimpleNamespace(id="u1")

    monkeypatch.setattr(routes, "is_available_search_engine", lambda namespace: namespace != "invalid")
    monkeypatch.setattr(routes, "get_search_engine", lambda _namespace: None)
    invalid = await routes.search_resources(
        db=db_session, user=user, request=request, namespace="invalid", q="q", pagenum=1, maxresults=10, orderby=""
    )
    assert invalid["status"] == 422

    async def _workspace(_db, _user, _q, _page, _max, _orderby):
        return {"scope": "workspace"}

    async def _resource(_request, _user, _q, _page, _max, order_by=None):
        return {"scope": "resource", "order": order_by}

    async def _generic(_q, _page, _max, _orderby):
        return {"scope": "generic"}

    monkeypatch.setattr(
        routes,
        "get_search_engine",
        lambda namespace: {"workspace": _workspace, "resource": _resource}.get(namespace, _generic),
    )

    workspace = await routes.search_resources(
        db=db_session, user=user, request=request, namespace="workspace", q="q", pagenum=2, maxresults=5, orderby="-name"
    )
    assert workspace == {"scope": "workspace"}

    resource = await routes.search_resources(
        db=db_session, user=user, request=request, namespace="resource", q="q", pagenum=2, maxresults=5, orderby="-name, title"
    )
    assert resource["scope"] == "resource"
    assert resource["order"] == ("-name", "title")

    generic = await routes.search_resources(
        db=db_session, user=user, request=request, namespace="user", q="q", pagenum=2, maxresults=5, orderby=""
    )
    assert generic == {"scope": "generic"}

    unauthorized = await routes.search_resources(
        db=db_session, user=None, request=request, namespace="group", q="q", pagenum=2, maxresults=5, orderby=""
    )
    assert unauthorized["status"] == 401

    async def _none(*_args, **_kwargs):
        return None

    monkeypatch.setattr(routes, "get_search_engine", lambda _namespace: _none)
    invalid_order = await routes.search_resources(
        db=db_session, user=user, request=request, namespace="user", q="q", pagenum=2, maxresults=5, orderby=""
    )
    assert invalid_order["status"] == 422
    assert captured["msg"] == "Invalid orderby value"
