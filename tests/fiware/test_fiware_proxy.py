# -*- coding: utf-8 -*-

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from bson import ObjectId

from wirecloud import settings
from wirecloud.commons.auth.schemas import UserAll
from wirecloud.database import Id
from wirecloud.fiware import proxy
from wirecloud.proxy.utils import ValidationError


def _sample_user(idm_data=None, username="user1"):
    return UserAll(
        id=Id(str(ObjectId())),
        username=username,
        email=f"{username}@example.com",
        first_name="First",
        last_name="Last",
        is_superuser=False,
        is_staff=False,
        is_active=True,
        date_joined=datetime.now(timezone.utc),
        last_login=None,
        idm_data=idm_data or {},
        groups=[],
        permissions=[],
    )


def _request(headers=None, url="https://api.example.org/path", data=None, user=None, workspace_creator="owner"):
    return SimpleNamespace(
        workspace=SimpleNamespace(creator=workspace_creator),
        component_id="wid-1",
        component_type="widget",
        headers=headers or {},
        url=url,
        data=data,
        user=user,
    )


async def test_get_header_or_query_and_replacers_basic_paths():
    req = _request(headers={"fiware-oauth-token": "1", "X-A": "hello"}, url="https://a/b?__x_auth_token=qv&x=1")

    assert proxy.get_header_or_query(req, "X-A") == "hello"
    assert proxy.get_header_or_query(req, "missing") is None

    assert proxy.get_header_or_query(req, "X-A", delete=True) == "hello"
    assert "X-A" not in req.headers

    req_query_only = _request(headers={}, url="https://a/b?__x_auth_token=qv&x=1")
    assert proxy.get_header_or_query(req_query_only, "x-auth-token", delete=False) == "qv"
    assert "__x_auth_token=qv" in req_query_only.url

    assert proxy.get_header_or_query(req, "x-auth-token", delete=True) == "qv"
    assert "__x_auth_token" not in req.url

    req2 = _request(url="https://a/b")
    proxy.replace_get_parameter(req2, ["fiware-oauth-get-parameter"], "tok")
    assert req2.url == "https://a/b"

    req3 = _request(headers={"fiware-oauth-get-parameter": "access_key"}, url="https://a/b?x=1")
    proxy.replace_get_parameter(req3, ["fiware-oauth-get-parameter"], "tok")
    assert "access_key=tok" in req3.url

    req4 = _request(headers={"fiware-oauth-header-name": "Authorization"})
    proxy.replace_header_name(req4, ["fiware-oauth-header-name"], "token-x")
    assert req4.headers["Authorization"] == "Bearer token-x"

    req5 = _request(headers={"fiware-openstack-header-name": "X-Auth-Token"})
    proxy.replace_header_name(req5, ["fiware-openstack-header-name"], "token-y")
    assert req5.headers["X-Auth-Token"] == "token-y"

    req6 = _request(headers={})
    proxy.replace_header_name(req6, ["fiware-oauth-header-name"], "token-z")
    assert req6.headers == {}


async def test_replace_body_pattern_bytes_generator_and_error(monkeypatch):
    monkeypatch.setattr(proxy, "_", lambda text: text)

    req_none = _request(headers={}, data=b"abc")
    await proxy.replace_body_pattern(req_none, ["fiware-oauth-body-pattern"], "token")
    assert req_none.data == b"abc"

    req_bytes = _request(headers={"fiware-oauth-body-pattern": "__TOKEN__"}, data=b"a=__TOKEN__")
    await proxy.replace_body_pattern(req_bytes, ["fiware-oauth-body-pattern"], "XYZ")
    assert req_bytes.data == b"a=XYZ"
    assert req_bytes.headers["content-length"] == str(len(b"a=XYZ"))

    async def _chunks():
        yield b"left-"
        yield b"__TOKEN__"

    req_gen = _request(headers={"fiware-openstack-body-pattern": "__TOKEN__"}, data=_chunks())
    await proxy.replace_body_pattern(req_gen, ["fiware-openstack-body-pattern"], "RIGHT")
    assert req_gen.data == b"left-RIGHT"

    class _EmptyAsyncData:
        def __aiter__(self):
            return self

        async def __anext__(self):
            raise StopAsyncIteration

    req_empty_gen = _request(headers={"fiware-openstack-body-pattern": "__TOKEN__"}, data=_EmptyAsyncData())
    await proxy.replace_body_pattern(req_empty_gen, ["fiware-openstack-body-pattern"], "RIGHT")
    assert req_empty_gen.data == b""
    assert req_empty_gen.headers["content-length"] == "0"

    async def _empty_async_generator():
        return
        yield b"never"

    req_empty_gen2 = _request(headers={"fiware-openstack-body-pattern": "__TOKEN__"}, data=_empty_async_generator())
    await proxy.replace_body_pattern(req_empty_gen2, ["fiware-openstack-body-pattern"], "RIGHT")
    assert req_empty_gen2.data == b""
    assert req_empty_gen2.headers["content-length"] == "0"

    req_error = _request(headers={"fiware-oauth-body-pattern": "__TOKEN__"}, data=None)
    with pytest.raises(ValidationError, match="No body data to replace pattern"):
        await proxy.replace_body_pattern(req_error, ["fiware-oauth-body-pattern"], "abc")


async def test_idm_processor_init_and_early_paths(monkeypatch):
    monkeypatch.setattr(settings, "OID_CONNECT_ENABLED", False)
    processor = proxy.IDMTokenProcessor()
    assert not hasattr(processor, "openstack_manager")

    req_missing = SimpleNamespace(workspace=None, component_id=None, component_type=None, headers={}, url="https://a", data=None, user=None)
    await processor.process_request(SimpleNamespace(), req_missing)

    req_no_headers = _request(user=_sample_user({"fiware": {"idm_token": "refresh"}}), headers={})
    await processor.process_request(SimpleNamespace(), req_no_headers)

    req_openstack_disabled = _request(headers={"fiware-openstack-token": "1"}, user=_sample_user({"fiware": {"idm_token": "refresh"}}))
    await processor.process_request(SimpleNamespace(), req_openstack_disabled, enable_openstack=False)


async def test_idm_processor_validation_errors(monkeypatch):
    monkeypatch.setattr(proxy, "_", lambda text: text)
    monkeypatch.setattr(settings, "OID_CONNECT_ENABLED", False)
    processor = proxy.IDMTokenProcessor()

    req_disabled = _request(headers={"fiware-oauth-token": "1"}, user=_sample_user({"fiware": {"idm_token": "refresh"}}))
    with pytest.raises(ValidationError, match="IdM support not enabled"):
        await processor.process_request(SimpleNamespace(), req_disabled)

    monkeypatch.setattr(settings, "OID_CONNECT_ENABLED", True)
    monkeypatch.setattr(settings, "OID_CONNECT_PLUGIN", "fiware")

    req_invalid_source = _request(headers={"fiware-oauth-token": "1", "fiware-oauth-source": "invalid"}, user=_sample_user({"fiware": {"idm_token": "refresh"}}))
    with pytest.raises(ValidationError, match="Invalid FIWARE OAuth token source"):
        await processor.process_request(SimpleNamespace(), req_invalid_source)

    req_no_profile = _request(headers={"fiware-oauth-token": "1"}, user=_sample_user({"fiware": {}}))
    with pytest.raises(ValidationError, match="User has not an active FIWARE profile"):
        await processor.process_request(SimpleNamespace(), req_no_profile)

    owner = _sample_user({"fiware": {"idm_token": "refresh-owner"}}, username="owner")

    async def _owner_user(_db, _creator):
        return owner

    async def _owner_prefs(_db, _uid):
        return [
            SimpleNamespace(name="allow_external_token_use", value="false"),
            SimpleNamespace(name="external_token_domain_whitelist", value="allowed.example.org"),
            SimpleNamespace(name="unused", value="x"),
        ]

    monkeypatch.setattr(proxy, "get_user_with_all_info", _owner_user)
    monkeypatch.setattr(proxy, "get_user_preferences", _owner_prefs)

    req_workspace_forbidden = _request(
        headers={"fiware-oauth-token": "1", "fiware-oauth-source": "workspace"},
        user=_sample_user({"fiware": {"idm_token": "refresh-user"}}),
        url="https://api.example.org/resource",
        workspace_creator="owner",
    )

    with pytest.raises(ValidationError, match="Workspace owner does not have permission"):
        await processor.process_request(SimpleNamespace(), req_workspace_forbidden)


async def test_idm_processor_token_fetch_error(monkeypatch):
    monkeypatch.setattr(proxy, "_", lambda text: text)
    monkeypatch.setattr(settings, "OID_CONNECT_ENABLED", True)
    monkeypatch.setattr(settings, "OID_CONNECT_PLUGIN", "fiware")

    processor = proxy.IDMTokenProcessor()

    async def _prefs(_db, _uid):
        return []

    def _broken_token_getter(*_args, **_kwargs):
        raise ValueError("boom")

    monkeypatch.setattr(proxy, "get_user_preferences", _prefs)
    monkeypatch.setattr(proxy, "get_idm_get_token_functions", lambda: {"fiware": _broken_token_getter})

    req = _request(headers={"fiware-oauth-token": "1"}, user=_sample_user({"fiware": {"idm_token": "refresh"}}))
    with pytest.raises(Exception, match="Failed to get token from IdM"):
        await processor.process_request(SimpleNamespace(), req)


async def test_idm_processor_success_oauth_and_openstack(monkeypatch):
    monkeypatch.setattr(proxy, "_", lambda text: text)
    monkeypatch.setattr(settings, "OID_CONNECT_ENABLED", True)
    monkeypatch.setattr(settings, "OID_CONNECT_PLUGIN", "fiware")

    processor = proxy.IDMTokenProcessor()

    async def _prefs(_db, _uid):
        return []

    def _token_getter(refresh_token, code, redirect_uri):
        assert refresh_token == "refresh-a"
        assert code is None
        assert redirect_uri is None
        return {"access_token": "access-a", "refresh_token": "refresh-b"}

    monkeypatch.setattr(proxy, "get_user_preferences", _prefs)
    monkeypatch.setattr(proxy, "get_idm_get_token_functions", lambda: {"fiware": _token_getter})
    monkeypatch.setattr(proxy, "update_user", AsyncMock())

    db = SimpleNamespace(commit=AsyncMock())
    req = _request(
        headers={
            "fiware-oauth-token": "1",
            "fiware-oauth-get-parameter": "auth",
            "fiware-oauth-header-name": "Authorization",
            "fiware-oauth-body-pattern": "__TOKEN__",
        },
        url="https://api.example.org/resource",
        data=b"v=__TOKEN__",
        user=_sample_user({"fiware": {"idm_token": "refresh-a"}}),
    )

    await processor.process_request(db, req)

    assert "auth=access-a" in req.url
    assert req.headers["Authorization"] == "Bearer access-a"
    assert req.data == b"v=access-a"
    assert req.user.idm_data["fiware"]["idm_token"] == "refresh-b"
    proxy.update_user.assert_awaited_once()
    db.commit.assert_awaited_once()

    owner = _sample_user({"fiware": {"idm_token": "refresh-owner"}}, username="owner")

    async def _owner_user(_db, _creator):
        return owner

    async def _owner_prefs(_db, _uid):
        return [
            SimpleNamespace(name="allow_external_token_use", value="true"),
            SimpleNamespace(name="external_token_domain_whitelist", value="api.example.org"),
        ]

    async def _async_token_getter(refresh_token, code, redirect_uri):
        assert refresh_token == "refresh-owner"
        return {"access_token": "access-owner", "refresh_token": "refresh-owner-2"}

    fake_openstack = SimpleNamespace(get_token=AsyncMock(return_value="openstack-token"))
    processor.openstack_manager = fake_openstack

    monkeypatch.setattr(proxy, "get_user_with_all_info", _owner_user)
    monkeypatch.setattr(proxy, "get_user_preferences", _owner_prefs)
    monkeypatch.setattr(proxy, "get_idm_get_token_functions", lambda: {"fiware": _async_token_getter})
    monkeypatch.setattr(proxy, "update_user", AsyncMock())

    db2 = SimpleNamespace(commit=AsyncMock())
    req2 = _request(
        headers={
            "fiware-openstack-token": "1",
            "fiware-openstack-header-name": "X-Auth-Token",
            "fiware-openstack-source": "workspace",
            "fiware-oauth-source": "workspace",
            "fiware-openstack-tenant-id": "tenant-1",
        },
        url="https://api.example.org/resource",
        data=b"ignored",
        user=_sample_user({"fiware": {"idm_token": "refresh-user"}}),
        workspace_creator="owner",
    )

    await processor.process_request(db2, req2)

    assert req2.headers["X-Auth-Token"] == "openstack-token"
    fake_openstack.get_token.assert_awaited_once_with(db2, owner, "tenant-1")
    db2.commit.assert_awaited_once()
