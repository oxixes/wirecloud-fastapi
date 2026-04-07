# -*- coding: utf-8 -*-

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from bson import ObjectId

from wirecloud import settings
from wirecloud.commons.auth.schemas import UserAll
from wirecloud.database import Id
from wirecloud.fiware import openstack_token_manager as otm


class _FakeResponse:
    def __init__(self, status=200, headers=None, payload=None, text_data=""):
        self.status = status
        self.headers = headers or {}
        self._payload = payload or {}
        self._text_data = text_data

    async def json(self):
        return self._payload

    async def text(self):
        return self._text_data


class _FakeRequestContext:
    def __init__(self, response):
        self.response = response

    async def __aenter__(self):
        return self.response

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _FakeClientSession:
    def __init__(self, post_response=None, get_response=None, capture=None):
        self.post_response = post_response
        self.get_response = get_response
        self.capture = capture if capture is not None else {}

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def post(self, url, **kwargs):
        self.capture["post"] = {"url": url, **kwargs}
        return _FakeRequestContext(self.post_response)

    def get(self, url, **kwargs):
        self.capture["get"] = {"url": url, **kwargs}
        return _FakeRequestContext(self.get_response)


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


async def test_first_step_openstack_success_and_errors(monkeypatch):
    monkeypatch.setattr(settings, "WIRECLOUD_HTTPS_VERIFY", False)

    capture = {}
    ok_response = _FakeResponse(status=201, headers={"X-Subject-Token": "os-token"})
    monkeypatch.setattr(otm.aiohttp, "ClientSession", lambda: _FakeClientSession(post_response=ok_response, capture=capture))

    token = await otm.first_step_openstack("https://cloud/keystone/v3/auth/tokens", "idm-token")
    assert token == "os-token"
    assert capture["post"]["json"]["auth"]["identity"]["oauth2"]["access_token_id"] == "idm-token"

    no_token_response = _FakeResponse(status=200, headers={})
    monkeypatch.setattr(otm.aiohttp, "ClientSession", lambda: _FakeClientSession(post_response=no_token_response))
    with pytest.raises(Exception, match="No token received from OpenStack"):
        await otm.first_step_openstack("https://cloud/keystone/v3/auth/tokens", "idm-token")

    error_response = _FakeResponse(status=500, text_data="failure")
    monkeypatch.setattr(otm.aiohttp, "ClientSession", lambda: _FakeClientSession(post_response=error_response))
    with pytest.raises(Exception, match="Error in OpenStack authentication"):
        await otm.first_step_openstack("https://cloud/keystone/v3/auth/tokens", "idm-token")


async def test_get_projects_and_permissions(monkeypatch):
    monkeypatch.setattr(settings, "WIRECLOUD_HTTPS_VERIFY", True)

    capture = {}
    projects_response = _FakeResponse(status=200, payload={"role_assignments": [{"x": 1}]})
    monkeypatch.setattr(otm.aiohttp, "ClientSession", lambda: _FakeClientSession(get_response=projects_response, capture=capture))

    projects = await otm.get_projects("https://cloud/role_assignments", "general-token", "alice")
    assert projects["role_assignments"] == [{"x": 1}]
    assert capture["get"]["params"] == {"user.id": "alice"}

    permissions_response = _FakeResponse(status=200, payload={"project": {"is_cloud_project": True}})
    monkeypatch.setattr(otm.aiohttp, "ClientSession", lambda: _FakeClientSession(get_response=permissions_response))

    permissions = await otm.get_project_permissions("https://cloud/projects/p1", "general-token")
    assert permissions["project"]["is_cloud_project"] is True

    bad_projects = _FakeResponse(status=403, text_data="forbidden")
    monkeypatch.setattr(otm.aiohttp, "ClientSession", lambda: _FakeClientSession(get_response=bad_projects))
    with pytest.raises(Exception, match="Error retrieving projects"):
        await otm.get_projects("https://cloud/role_assignments", "general-token", "alice")

    bad_permissions = _FakeResponse(status=404, text_data="missing")
    monkeypatch.setattr(otm.aiohttp, "ClientSession", lambda: _FakeClientSession(get_response=bad_permissions))
    with pytest.raises(Exception, match="Error retrieving project permissions"):
        await otm.get_project_permissions("https://cloud/projects/p1", "general-token")


async def test_get_openstack_project_token(monkeypatch):
    ok_response = _FakeResponse(status=200, headers={"X-Subject-Token": "project-token"})
    monkeypatch.setattr(otm.aiohttp, "ClientSession", lambda: _FakeClientSession(post_response=ok_response))

    token = await otm.get_openstack_project_token("https://cloud/auth/tokens", "p1", "idm-token")
    assert token == "project-token"

    no_token = _FakeResponse(status=201, headers={})
    monkeypatch.setattr(otm.aiohttp, "ClientSession", lambda: _FakeClientSession(post_response=no_token))
    with pytest.raises(Exception, match="No project token received from OpenStack"):
        await otm.get_openstack_project_token("https://cloud/auth/tokens", "p1", "idm-token")

    bad_response = _FakeResponse(status=400, text_data="bad")
    monkeypatch.setattr(otm.aiohttp, "ClientSession", lambda: _FakeClientSession(post_response=bad_response))
    with pytest.raises(Exception, match="Error in OpenStack project authentication"):
        await otm.get_openstack_project_token("https://cloud/auth/tokens", "p1", "idm-token")


async def test_manager_get_token_paths(monkeypatch):
    manager = otm.OpenStackTokenManager("https://cloud")

    cached_user = _sample_user({"openstack_token": {"__default__": "cached-token"}})
    assert await manager.get_token(SimpleNamespace(), cached_user, None) == "cached-token"

    monkeypatch.setattr(settings, "OID_CONNECT_ENABLED", False)
    with pytest.raises(Exception, match="OIDC is not enabled"):
        await manager.get_token(SimpleNamespace(), _sample_user({}), "tenant-a")

    monkeypatch.setattr(settings, "OID_CONNECT_ENABLED", True)
    monkeypatch.setattr(settings, "OID_CONNECT_PLUGIN", "fiware")
    monkeypatch.setattr(otm, "get_idm_get_token_functions", lambda: {})
    with pytest.raises(Exception, match="OIDC provider is not configured correctly"):
        await manager.get_token(SimpleNamespace(), _sample_user({"fiware": {"idm_token": "r0"}}), "tenant-a")


async def test_manager_get_token_sync_async_and_value_error(monkeypatch):
    manager = otm.OpenStackTokenManager("https://cloud")
    monkeypatch.setattr(settings, "OID_CONNECT_ENABLED", True)
    monkeypatch.setattr(settings, "OID_CONNECT_PLUGIN", "fiware")

    updated = {"called": False}

    async def _update_user(_db, _user):
        updated["called"] = True

    monkeypatch.setattr(otm, "update_user", _update_user)

    async def _fake_openstack_token(_username, _access_token, _tenant):
        return "openstack-token"

    monkeypatch.setattr(manager, "get_openstack_token", _fake_openstack_token)

    async def _async_token_getter(refresh_token, code, redirect_uri):
        assert refresh_token == "r1"
        assert code is None
        assert redirect_uri is None
        return {"access_token": "a1", "refresh_token": "r2"}

    monkeypatch.setattr(otm, "get_idm_get_token_functions", lambda: {"fiware": _async_token_getter})
    user = _sample_user({"fiware": {"idm_token": "r1"}})
    token = await manager.get_token(SimpleNamespace(), user, None)
    assert token == "openstack-token"
    assert user.idm_data["fiware"]["openstack_token"] == "openstack-token"
    assert user.idm_data["fiware"]["idm_token"] == "r2"
    assert updated["called"] is True

    def _sync_token_getter(refresh_token, code, redirect_uri):
        assert refresh_token == "r3"
        return {"access_token": "a2", "refresh_token": "r4"}

    monkeypatch.setattr(otm, "get_idm_get_token_functions", lambda: {"fiware": _sync_token_getter})
    user2 = _sample_user({"fiware": {"idm_token": "r3"}})
    token2 = await manager.get_token(SimpleNamespace(), user2, "tenant-b")
    assert token2 == "openstack-token"
    assert user2.idm_data["fiware"]["idm_token"] == "r4"

    def _broken_token_getter(*_args, **_kwargs):
        raise ValueError("broken")

    monkeypatch.setattr(otm, "get_idm_get_token_functions", lambda: {"fiware": _broken_token_getter})
    with pytest.raises(Exception, match="Error retrieving token from IDM"):
        await manager.get_token(SimpleNamespace(), _sample_user({"fiware": {"idm_token": "r5"}}), "tenant-c")


async def test_manager_get_openstack_token_paths(monkeypatch):
    manager = otm.OpenStackTokenManager("https://cloud")

    async def _first_step(_url, _idm_token):
        return "general"

    async def _get_projects(_url, _general, _username):
        return {
            "role_assignments": [
                {"scope": {"project": {"id": "p1"}}},
                {"scope": {"project": {"id": "p2"}}},
            ]
        }

    async def _project_permissions(url, _general):
        if url.endswith("/p1"):
            return {"project": {"is_cloud_project": False, "id": "p1"}}
        return {"project": {"is_cloud_project": True, "id": "p2"}}

    captured = {}

    async def _project_token(url, project_id, idm_token):
        captured["url"] = url
        captured["project_id"] = project_id
        captured["idm_token"] = idm_token
        return "project-token"

    monkeypatch.setattr(otm, "first_step_openstack", _first_step)
    monkeypatch.setattr(otm, "get_projects", _get_projects)
    monkeypatch.setattr(otm, "get_project_permissions", _project_permissions)
    monkeypatch.setattr(otm, "get_openstack_project_token", _project_token)

    token = await manager.get_openstack_token("alice", "idm-1", "__default__")
    assert token == "project-token"
    assert captured["project_id"] == "p2"

    token2 = await manager.get_openstack_token("alice", "idm-2", "p2")
    assert token2 == "project-token"

    async def _projects_without_match(_url, _general, _username):
        return {"role_assignments": [{"scope": {}}, {"scope": {"project": {"id": "p3"}}}]}

    async def _permissions_without_cloud(_url, _general):
        return {"project": {"is_cloud_project": False, "id": "p3"}}

    monkeypatch.setattr(otm, "get_projects", _projects_without_match)
    monkeypatch.setattr(otm, "get_project_permissions", _permissions_without_cloud)

    with pytest.raises(Exception, match="No OpenStack cloud project found for the user"):
        await manager.get_openstack_token("alice", "idm-3", "p2")
