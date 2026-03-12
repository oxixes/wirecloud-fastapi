# -*- coding: utf-8 -*-

import json as pyjson

from wirecloud import docs


def test_wirecloud_docs_error_response_helpers(monkeypatch):
    monkeypatch.setattr(docs, "get_xml_error_response", lambda *_args, **_kwargs: "<error/>")
    monkeypatch.setattr(docs, "get_json_error_response", lambda *_args, **_kwargs: "{\"error_msg\":\"bad\"}")

    xml = docs.generate_error_response_xml_example("bad", details={"x": 1})
    json_body = docs.generate_error_response_json_example("bad", details={"x": 1})
    assert xml == "<error/>"
    assert pyjson.loads(json_body)["error_msg"] == "bad"

    full = docs.generate_error_response_openapi_description("desc", "bad", details={"x": 1}, include_schema=True)
    assert full["description"] == "desc"
    assert full["model"].__name__ == "HTTPError"
    assert full["content"]["text/plain"]["example"] == "bad"

    no_schema = docs.generate_error_response_openapi_description("desc", "bad", include_schema=False)
    assert "model" not in no_schema

    not_found = docs.generate_not_found_response_openapi_description("nf")
    assert not_found["content"]["text/plain"]["example"] == "Page Not Found"

    validation = docs.generate_validation_error_response_openapi_description("ve")
    assert validation["content"]["text/plain"]["example"] == "Invalid payload"

    not_acceptable = docs.generate_not_acceptable_response_openapi_description("na", ["application/json"])
    assert "only capable of generating content" in not_acceptable["content"]["text/plain"]["example"]

    unsupported = docs.generate_unsupported_media_type_response_openapi_description("um")
    assert unsupported["content"]["text/plain"]["example"] == "Unsupported request media type"

    auth = docs.generate_auth_required_response_openapi_description("ar")
    assert auth["content"]["text/plain"]["example"] == "Authentication required"

    denied_default = docs.generate_permission_denied_response_openapi_description("pd", None)
    assert denied_default["content"]["text/plain"]["example"] == "Permission denied"

    denied_custom = docs.generate_permission_denied_response_openapi_description("pd", "custom")
    assert denied_custom["content"]["text/plain"]["example"] == "custom"
