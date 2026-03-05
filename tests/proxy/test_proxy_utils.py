# -*- coding: utf-8 -*-

from types import SimpleNamespace

from wirecloud.proxy import utils


async def test_validation_error_get_response_and_header_validation(monkeypatch):
    captured = {}

    def _build_error_response(request, status, msg):
        captured["request"] = request
        captured["status"] = status
        captured["msg"] = msg
        return {"ok": False, "status": status, "msg": msg}

    monkeypatch.setattr(utils, "build_error_response", _build_error_response)

    request = SimpleNamespace(path="/")
    exc = utils.ValidationError("bad input")
    response = exc.get_response(request)

    assert response["status"] == 422
    assert captured["request"] == request
    assert captured["msg"] == "bad input"

    assert utils.is_valid_response_header("content-type") is True
    assert utils.is_valid_response_header("transfer-encoding") is False
