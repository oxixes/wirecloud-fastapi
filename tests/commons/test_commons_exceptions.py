# -*- coding: utf-8 -*-

from wirecloud.commons.exceptions import ErrorResponse


def test_error_response_stores_response():
    payload = {"status": 400, "message": "bad"}
    exc = ErrorResponse(payload)
    assert exc.response == payload

