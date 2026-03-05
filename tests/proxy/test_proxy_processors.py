# -*- coding: utf-8 -*-

from types import SimpleNamespace

import pytest

from wirecloud.proxy import processors
from wirecloud.proxy.utils import ValidationError


@pytest.fixture(autouse=True)
def _patch_gettext(monkeypatch):
    monkeypatch.setattr(processors, "_", lambda text: text)


async def test_get_variable_value_by_ref_constant_success_and_fallback(monkeypatch, db_session):
    class _Cache:
        async def get_variable_value_from_varname(self, db, request, ctype, cid, var_name):
            assert ctype == "iwidget"
            assert cid == "c1"
            assert var_name == "token"
            return "value-1"

    value = await processors.get_variable_value_by_ref(db_session, None, "c/fixed", _Cache(), "widget", "c1")
    assert value == "fixed"

    value2 = await processors.get_variable_value_by_ref(db_session, None, "token", _Cache(), "widget", "c1")
    assert value2 == "value-1"

    class _BrokenCache:
        async def get_variable_value_from_varname(self, *_args, **_kwargs):
            raise RuntimeError("boom")

    value3 = await processors.get_variable_value_by_ref(db_session, None, "token", _BrokenCache(), "widget", "c1")
    assert value3 is None


async def test_check_helpers_raise_and_pass():
    processors.check_empty_params(a="x", b="y")
    processors.check_invalid_refs(a="x", b="y")

    with pytest.raises(ValidationError, match="missing"):
        processors.check_empty_params(a="", b="x")

    with pytest.raises(ValidationError, match="invalid"):
        processors.check_invalid_refs(a=None, b="x")


async def test_process_secure_data_data_header_and_basic_auth(monkeypatch, db_session):
    class _FakeCache:
        def __init__(self, workspace, user):
            self.workspace = workspace
            self.user = user

    async def _value_by_ref(_db, _request, ref, _cache, _ctype, _cid):
        mapping = {
            "token": "abc def",
            "user": "alice",
            "pwd": "secret",
        }
        return mapping.get(ref)

    monkeypatch.setattr(processors, "VariableValueCacheManager", _FakeCache)
    monkeypatch.setattr(processors, "get_variable_value_by_ref", _value_by_ref)

    req = SimpleNamespace(
        workspace=SimpleNamespace(),
        user=SimpleNamespace(),
        is_ws=False,
        original_request=SimpleNamespace(),
        headers={"x-auth": "Bearer {token}"},
        data=b"v={token}",
    )

    await processors.process_secure_data(db_session, "action=data,var_ref=token,encoding=url", req, "c1", "widget")
    assert req.data == b"v=abc%20def"

    req_base64 = SimpleNamespace(
        workspace=SimpleNamespace(),
        user=SimpleNamespace(),
        is_ws=False,
        original_request=SimpleNamespace(),
        headers={},
        data=b"{token}",
    )
    await processors.process_secure_data(db_session, "action=data,var_ref=token,encoding=base64", req_base64, "c1", "widget")
    assert req_base64.data == b"YWJjIGRlZg=="

    req2 = SimpleNamespace(
        workspace=SimpleNamespace(),
        user=SimpleNamespace(),
        is_ws=False,
        original_request=SimpleNamespace(),
        headers={"x-auth": "Bearer {token}"},
        data=b"x",
    )
    await processors.process_secure_data(db_session, "action=header,var_ref=token,header=x-auth,substr={token},encoding=base64", req2, "c1", "widget")
    assert req2.headers["x-auth"].startswith("Bearer ")

    req2b = SimpleNamespace(
        workspace=SimpleNamespace(),
        user=SimpleNamespace(),
        is_ws=False,
        original_request=SimpleNamespace(),
        headers={"x-auth": "Bearer {token}"},
        data=b"x",
    )
    await processors.process_secure_data(db_session, "action=header,var_ref=token,header=x-auth,substr={token},encoding=url", req2b, "c1", "widget")
    assert req2b.headers["x-auth"] == "Bearer abc%20def"

    req3 = SimpleNamespace(
        workspace=SimpleNamespace(),
        user=SimpleNamespace(),
        is_ws=False,
        original_request=SimpleNamespace(),
        headers={},
        data=b"x",
    )
    await processors.process_secure_data(db_session, "action=basic_auth,user_ref=user,pass_ref=pwd", req3, "c1", "widget")
    assert req3.headers["authorization"].startswith("Basic ")


async def test_process_secure_data_errors_and_ws(monkeypatch, db_session):
    class _FakeCache:
        def __init__(self, workspace, user):
            self.workspace = workspace
            self.user = user

    async def _none_value(*_args, **_kwargs):
        return None

    monkeypatch.setattr(processors, "VariableValueCacheManager", _FakeCache)
    monkeypatch.setattr(processors, "get_variable_value_by_ref", _none_value)

    req = SimpleNamespace(
        workspace=SimpleNamespace(),
        user=SimpleNamespace(),
        is_ws=False,
        original_request=SimpleNamespace(),
        headers={},
        data=b"body",
    )

    with pytest.raises(ValidationError, match="missing"):
        await processors.process_secure_data(db_session, "action=data,var_ref=", req, "c1", "widget")

    with pytest.raises(ValidationError, match="invalid"):
        await processors.process_secure_data(db_session, "action=data,var_ref=token", req, "c1", "widget")

    req_none_data = SimpleNamespace(
        workspace=SimpleNamespace(),
        user=SimpleNamespace(),
        is_ws=False,
        original_request=SimpleNamespace(),
        headers={},
        data=None,
    )
    async def _value_present(*_args, **_kwargs):
        return "token"

    monkeypatch.setattr(processors, "get_variable_value_by_ref", _value_present)
    with pytest.raises(ValidationError, match="does not contain any data"):
        await processors.process_secure_data(db_session, "action=data,var_ref=token", req_none_data, "c1", "widget")

    req_ws = SimpleNamespace(
        workspace=SimpleNamespace(),
        user=SimpleNamespace(),
        is_ws=True,
        original_request=SimpleNamespace(),
        headers={},
        data=b"body",
    )
    with pytest.raises(ValidationError, match="not supported for WebSocket"):
        await processors.process_secure_data(db_session, "action=data,var_ref=token", req_ws, "c1", "widget")

    with pytest.raises(ValidationError, match="Unknown action"):
        await processors.process_secure_data(db_session, "action=unknown", req, "c1", "widget")


async def test_secure_data_processor_header_query_and_early_return(monkeypatch, db_session):
    processor = processors.SecureDataProcessor()

    called = {}

    async def _process(_db, text, request, component_id, component_type):
        called["text"] = text
        called["component_id"] = component_id
        called["component_type"] = component_type

    monkeypatch.setattr(processors, "process_secure_data", _process)

    request_missing = SimpleNamespace(workspace=None, component_id=None, component_type=None, headers={}, url="https://a/b", is_ws=False)
    await processor.process_request(db_session, request_missing)

    req_header = SimpleNamespace(
        workspace=SimpleNamespace(),
        component_id="c1",
        component_type="widget",
        headers={processors.WIRECLOUD_SECURE_DATA_HEADER: "action=header,var_ref=t,header=x-auth"},
        url="https://a/b?x=1",
        is_ws=False,
    )
    await processor.process_request(db_session, req_header)
    assert called["component_id"] == "c1"
    assert processors.WIRECLOUD_SECURE_DATA_HEADER not in req_header.headers

    req_query = SimpleNamespace(
        workspace=SimpleNamespace(),
        component_id="c2",
        component_type="operator",
        headers={},
        url="https://a/b?x=1&__wirecloud_secure_data=action%3Dheader%2Cvar_ref%3Dt%2Cheader%3Dx-auth&z=2",
        is_ws=False,
    )
    await processor.process_request(db_session, req_query)
    assert "__wirecloud_secure_data" not in req_query.url

    req_none = SimpleNamespace(
        workspace=SimpleNamespace(),
        component_id="c3",
        component_type="widget",
        headers={},
        url="https://a/b?x=1",
        is_ws=False,
    )
    await processor.process_request(db_session, req_none)


async def test_process_secure_data_skips_empty_definition_and_reads_async_body(monkeypatch, db_session):
    class _FakeCache:
        def __init__(self, workspace, user):
            self.workspace = workspace
            self.user = user

    async def _value_by_ref(_db, _request, ref, _cache, _ctype, _cid):
        return "abc"

    monkeypatch.setattr(processors, "VariableValueCacheManager", _FakeCache)
    monkeypatch.setattr(processors, "get_variable_value_by_ref", _value_by_ref)

    async def _chunks():
        yield b"{token}"

    req = SimpleNamespace(
        workspace=SimpleNamespace(),
        user=SimpleNamespace(),
        is_ws=False,
        original_request=SimpleNamespace(),
        headers={},
        data=_chunks(),
    )
    await processors.process_secure_data(db_session, "&action=data,var_ref=token", req, "c1", "widget")
    assert req.data == b"abc"

    req_header_none_encoding = SimpleNamespace(
        workspace=SimpleNamespace(),
        user=SimpleNamespace(),
        is_ws=False,
        original_request=SimpleNamespace(),
        headers={"x-auth": "Bearer {token}"},
        data=b"x",
    )
    await processors.process_secure_data(
        db_session,
        "action=header,var_ref=token,header=x-auth,substr={token},encoding=none",
        req_header_none_encoding,
        "c1",
        "widget",
    )
    assert req_header_none_encoding.headers["x-auth"] == "Bearer abc"

    class _EmptyAsyncData:
        def __aiter__(self):
            return self

        async def __anext__(self):
            raise StopAsyncIteration

    req_empty = SimpleNamespace(
        workspace=SimpleNamespace(),
        user=SimpleNamespace(),
        is_ws=False,
        original_request=SimpleNamespace(),
        headers={},
        data=_EmptyAsyncData(),
    )
    await processors.process_secure_data(db_session, "action=data,var_ref=token", req_empty, "c1", "widget")
    assert req_empty.data == b""
