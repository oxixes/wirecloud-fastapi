# -*- coding: utf-8 -*-
# Copyright (c) 2026 Future Internet Consulting and Development Solutions S.L.

# This file is part of Wirecloud.

# Wirecloud is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# Wirecloud is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with Wirecloud.  If not, see <http://www.gnu.org/licenses/>.

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from bson import ObjectId
from fastapi.responses import Response
from httpx import ASGITransport, AsyncClient

from src import settings
from wirecloud.commons.auth import routes, utils
from wirecloud.commons.auth.schemas import Permission, Session, UserAll, UserTokenType, UserWithPassword
from wirecloud.database import Id
from wirecloud.main import app


class _CallRecorder:
    def __init__(self):
        self.calls = []

    async def __call__(self, *args, **kwargs):
        self.calls.append((args, kwargs))


async def _noop(*_args, **_kwargs):
    return None


async def _oid(*_args, **_kwargs):
    return Id(str(ObjectId()))


def _user_with_password(username="alice", active=True):
    return UserWithPassword(
        id=Id(str(ObjectId())),
        username=username,
        password="hash",
        email=f"{username}@example.com",
        first_name="A",
        last_name="B",
        is_superuser=False,
        is_staff=False,
        is_active=active,
        date_joined=datetime.now(timezone.utc),
        last_login=None,
        idm_data={"keycloak": {"idm_token": "r1"}},
    )


def _user_all(username="alice", active=True, perms=None):
    return UserAll(
        id=Id(str(ObjectId())),
        username=username,
        email=f"{username}@example.com",
        first_name="First",
        last_name="Last",
        is_superuser=False,
        is_staff=False,
        is_active=active,
        date_joined=datetime.now(timezone.utc),
        last_login=None,
        idm_data={"keycloak": {"idm_token": "r1"}},
        groups=[],
        permissions=perms or [],
    )


def _common_patches(monkeypatch):
    monkeypatch.setattr(routes, "_", lambda text: text)
    monkeypatch.setattr(routes, "build_error_response", lambda _r, status, _msg: Response(status_code=status))


@pytest.fixture()
async def app_http_client(db_session):
    from wirecloud.database import get_session

    async def _override_get_session():
        yield db_session

    app.dependency_overrides[get_session] = _override_get_session
    try:
        transport = ASGITransport(app=app, raise_app_exceptions=False)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            yield client
    finally:
        app.dependency_overrides.clear()


async def test_oidc_login_error_paths_http(app_http_client, monkeypatch):
    _common_patches(monkeypatch)

    monkeypatch.setattr(settings, "OID_CONNECT_ENABLED", False)
    assert (await app_http_client.get("/oidc/callback", params={"code": "abc"})).status_code == 400

    monkeypatch.setattr(settings, "OID_CONNECT_ENABLED", True)
    monkeypatch.setattr(settings, "OID_CONNECT_PLUGIN", "keycloak")
    monkeypatch.setattr(routes, "get_idm_get_token_functions", lambda: {})
    assert (await app_http_client.get("/oidc/callback", params={"code": "abc"})).status_code == 500

    monkeypatch.setattr(routes, "get_idm_get_token_functions", lambda: {"keycloak": lambda **_k: {}})
    monkeypatch.setattr(routes, "get_idm_get_user_functions", lambda: {})
    assert (await app_http_client.get("/oidc/callback", params={"code": "abc"})).status_code == 500

    async def _boom(**_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(routes, "get_idm_get_token_functions", lambda: {"keycloak": _boom})
    monkeypatch.setattr(routes, "get_idm_get_user_functions", lambda: {"keycloak": lambda **_k: {"preferred_username": "a"}})
    monkeypatch.setattr(routes, "get_absolute_reverse_url", lambda *_args, **_kwargs: "http://cb")
    assert (await app_http_client.get("/oidc/callback", params={"code": "abc"})).status_code == 502


async def test_oidc_login_success_branches_http(app_http_client, monkeypatch):
    _common_patches(monkeypatch)
    monkeypatch.setattr(settings, "OID_CONNECT_ENABLED", True)
    monkeypatch.setattr(settings, "OID_CONNECT_PLUGIN", "keycloak")
    monkeypatch.setattr(settings, "OID_CONNECT_FULLY_SYNC_GROUPS", True)

    monkeypatch.setattr(routes, "get_absolute_reverse_url", lambda *_args, **_kwargs: "http://cb")
    monkeypatch.setattr(routes, "get_redirect_response", lambda _r: Response(status_code=302))
    monkeypatch.setattr(routes, "commit", _noop)

    created = _CallRecorder()
    updated = _CallRecorder()
    group_created = _CallRecorder()
    grouped = _CallRecorder()
    removed_groups = _CallRecorder()

    monkeypatch.setattr(routes, "create_user", created)
    monkeypatch.setattr(routes, "update_user", updated)
    monkeypatch.setattr(routes, "create_group_if_not_exists", group_created)
    monkeypatch.setattr(routes, "add_user_to_groups_by_codename", grouped)
    monkeypatch.setattr(routes, "remove_user_from_all_groups", removed_groups)
    monkeypatch.setattr(routes, "set_login_date_for_user", _noop)
    monkeypatch.setattr(routes, "create_token", _oid)

    token_data = {"refresh_token": "r1", "session_state": "s1"}
    user_data = {
        "preferred_username": "oidcuser",
        "given_name": "OIDC",
        "family_name": "User",
        "email": "oidc@example.com",
        "sub": "sub-id",
        "wirecloud": {"groups": ["dev", "ops"]},
    }

    async def _token_async(**_kwargs):
        return token_data

    async def _user_async(**_kwargs):
        return user_data

    monkeypatch.setattr(routes, "get_idm_get_token_functions", lambda: {"keycloak": _token_async})
    monkeypatch.setattr(routes, "get_idm_get_user_functions", lambda: {"keycloak": _user_async})

    created_user = _user_all("oidcuser")
    calls = {"n": 0}

    async def _get_user(_db, _username):
        calls["n"] += 1
        return None if calls["n"] == 1 else created_user

    monkeypatch.setattr(routes, "get_user_by_username", _get_user)

    assert (await app_http_client.get("/oidc/callback", params={"code": "abc"})).status_code == 302
    assert len(created.calls) == 1
    assert len(group_created.calls) == 2
    assert len(grouped.calls) == 1
    assert len(removed_groups.calls) == 1

    existing = _user_all("oidcuser")

    async def _get_existing(_db, _username):
        return existing

    monkeypatch.setattr(routes, "get_idm_get_token_functions", lambda: {"keycloak": (lambda **_k: token_data)})
    monkeypatch.setattr(routes, "get_idm_get_user_functions", lambda: {"keycloak": (lambda **_k: user_data)})
    monkeypatch.setattr(routes, "get_user_by_username", _get_existing)
    assert (await app_http_client.get("/oidc/callback", params={"code": "def"})).status_code == 302
    assert len(updated.calls) == 1

    monkeypatch.setattr(settings, "OID_CONNECT_FULLY_SYNC_GROUPS", False)
    monkeypatch.setattr(routes, "get_idm_get_token_functions", lambda: {"keycloak": (lambda **_k: {"session_state": "s1"})})
    monkeypatch.setattr(routes, "get_idm_get_user_functions", lambda: {"keycloak": (lambda **_k: {"preferred_username": "u1", "wirecloud": {"groups": [1, 2]}})})
    assert (await app_http_client.get("/oidc/callback", params={"code": "third"})).status_code == 302

    # Cover branch where only `sub` is present (no refresh token or session state)
    monkeypatch.setattr(routes, "get_idm_get_token_functions", lambda: {"keycloak": (lambda **_k: {})})
    monkeypatch.setattr(routes, "get_idm_get_user_functions", lambda: {"keycloak": (lambda **_k: {"preferred_username": "u1", "sub": "sub-only"})})
    assert (await app_http_client.get("/oidc/callback", params={"code": "fourth"})).status_code == 302


async def test_oidc_login_rejects_inactive_user_http(app_http_client, monkeypatch):
    _common_patches(monkeypatch)
    monkeypatch.setattr(settings, "OID_CONNECT_ENABLED", True)
    monkeypatch.setattr(settings, "OID_CONNECT_PLUGIN", "keycloak")
    monkeypatch.setattr(routes, "get_absolute_reverse_url", lambda *_args, **_kwargs: "http://cb")
    monkeypatch.setattr(routes, "get_idm_get_token_functions", lambda: {"keycloak": (lambda **_k: {})})
    monkeypatch.setattr(routes, "get_idm_get_user_functions", lambda: {"keycloak": (lambda **_k: {"preferred_username": "x"})})

    async def _inactive(_db, _username):
        return _user_all("x", active=False)

    monkeypatch.setattr(routes, "get_user_by_username", _inactive)
    assert (await app_http_client.get("/oidc/callback", params={"code": "abc"})).status_code == 401


async def test_api_login_and_login_http(app_http_client, monkeypatch):
    _common_patches(monkeypatch)
    monkeypatch.setattr(routes, "build_validation_error_response", lambda _r: Response(status_code=422))
    monkeypatch.setattr(routes, "get_redirect_response", lambda _r: Response(status_code=302))
    monkeypatch.setattr(routes, "render_wirecloud", lambda *_a, **_k: Response(status_code=200))
    monkeypatch.setattr(routes, "commit", _noop)
    monkeypatch.setattr(routes, "set_login_date_for_user", _noop)
    monkeypatch.setattr(routes, "create_token", _oid)
    monkeypatch.setattr(routes, "remove_user_idm_data", _noop)

    async def _none_user(_db, _username):
        return None

    monkeypatch.setattr(routes, "get_user_with_password", _none_user)
    monkeypatch.setattr(routes, "check_password", lambda *_a, **_k: False)

    json_headers = {"content-type": "application/json", "accept": "application/json"}
    assert (await app_http_client.post("/api/auth/login", content="not-json", headers=json_headers)).status_code == 422
    assert (await app_http_client.post("/login", content="not-json", headers={"content-type": "application/json"})).status_code == 422

    assert (await app_http_client.post("/api/auth/login", data={"username": "x", "password": "y"}, headers={"accept": "application/json"})).status_code == 401
    assert (await app_http_client.post("/login", data={"username": "x", "password": "y"})).status_code == 200

    good_user = _user_with_password("good")

    async def _good_user(_db, _username):
        return good_user

    monkeypatch.setattr(routes, "get_user_with_password", _good_user)
    monkeypatch.setattr(routes, "check_password", lambda *_a, **_k: True)

    response = await app_http_client.post("/api/auth/login", json={"username": "good", "password": "ok"}, headers={"accept": "application/json"})
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == UserTokenType.bearer

    assert (await app_http_client.post("/login", json={"username": "good", "password": "ok"})).status_code == 302

    monkeypatch.setattr(settings, "OID_CONNECT_PLUGIN", None)
    assert (await app_http_client.post("/login", json={"username": "good", "password": "ok"})).status_code == 302


async def test_login_page_and_logout_http(app_http_client, monkeypatch):
    _common_patches(monkeypatch)
    monkeypatch.setattr(routes, "render_wirecloud", lambda *_a, **_k: Response(status_code=200))
    assert (await app_http_client.get("/login")).status_code == 200

    monkeypatch.setattr(routes, "get_redirect_response", lambda _r: Response(status_code=302))
    monkeypatch.setattr(routes, "commit", _noop)

    async def _none_session():
        return None

    async def _none_user():
        return None

    app.dependency_overrides[utils.get_session_no_csrf] = _none_session
    app.dependency_overrides[utils.get_user_no_csrf] = _none_user
    assert (await app_http_client.get("/logout")).status_code == 401

    invalidated = _CallRecorder()
    monkeypatch.setattr(routes, "invalidate_token", invalidated)

    user = _user_all("logout")
    session = Session(id=Id(str(ObjectId())), requires_csrf=True, token_data={})

    async def _session_dep():
        return session

    async def _user_dep():
        return user

    app.dependency_overrides[utils.get_session_no_csrf] = _session_dep
    app.dependency_overrides[utils.get_user_no_csrf] = _user_dep

    monkeypatch.setattr(settings, "OID_CONNECT_ENABLED", False)
    assert (await app_http_client.get("/logout")).status_code == 302
    assert len(invalidated.calls) == 1

    monkeypatch.setattr(settings, "OID_CONNECT_ENABLED", True)
    monkeypatch.setattr(settings, "OID_CONNECT_PLUGIN", "keycloak")
    user.idm_data = {"keycloak": {"idm_token": "r1"}}

    async def _backchannel_async(**_kwargs):
        return None

    def _backchannel_sync(**_kwargs):
        raise RuntimeError("ignore")

    monkeypatch.setattr(routes, "get_idm_backchannel_logout_functions", lambda: {"keycloak": _backchannel_async})
    assert (await app_http_client.get("/logout")).status_code == 302

    monkeypatch.setattr(routes, "get_idm_backchannel_logout_functions", lambda: {"keycloak": _backchannel_sync})
    assert (await app_http_client.get("/logout")).status_code == 302


async def test_token_refresh_http(app_http_client, monkeypatch):
    _common_patches(monkeypatch)
    monkeypatch.setattr(routes, "commit", _noop)
    monkeypatch.setattr(routes, "set_token_expiration", _noop)

    user = _user_all("refresh")
    session = SimpleNamespace(id=Id(str(ObjectId())), oidc_token="exists", requires_csrf=True, token_data={"real_user": {"id": "x"}})

    async def _none_session():
        return None

    async def _user_dep():
        return user

    app.dependency_overrides[utils.get_session_csrf] = _none_session
    app.dependency_overrides[utils.get_user_csrf] = _user_dep
    assert (await app_http_client.get("/api/auth/refresh")).status_code == 401

    async def _session_dep():
        return session

    app.dependency_overrides[utils.get_session_csrf] = _session_dep

    monkeypatch.setattr(settings, "OID_CONNECT_ENABLED", True)
    monkeypatch.setattr(settings, "OID_CONNECT_PLUGIN", "keycloak")
    monkeypatch.setattr(routes, "get_idm_get_token_functions", lambda: {})
    assert (await app_http_client.get("/api/auth/refresh")).status_code == 500

    async def _boom(**_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(routes, "get_idm_get_token_functions", lambda: {"keycloak": _boom})
    assert (await app_http_client.get("/api/auth/refresh")).status_code == 502

    async def _token_async(**_kwargs):
        return {"refresh_token": "new-refresh"}

    updated = _CallRecorder()
    monkeypatch.setattr(routes, "update_user", updated)
    monkeypatch.setattr(routes, "get_idm_get_token_functions", lambda: {"keycloak": _token_async})

    assert (await app_http_client.get("/api/auth/refresh")).status_code == 200
    assert len(updated.calls) == 1

    monkeypatch.setattr(settings, "OID_CONNECT_ENABLED", False)
    session_no_csrf = SimpleNamespace(id=Id(str(ObjectId())), oidc_token="exists", requires_csrf=False, token_data={})

    async def _session_dep_no_csrf():
        return session_no_csrf

    app.dependency_overrides[utils.get_session_csrf] = _session_dep_no_csrf
    assert (await app_http_client.get("/api/auth/refresh")).status_code == 200

    # Cover sync token provider branch
    monkeypatch.setattr(settings, "OID_CONNECT_ENABLED", True)
    session_sync = SimpleNamespace(id=Id(str(ObjectId())), oidc_token="exists", requires_csrf=True, token_data={})

    async def _session_dep_sync():
        return session_sync

    app.dependency_overrides[utils.get_session_csrf] = _session_dep_sync
    user.idm_data["keycloak"] = {"idm_token": "refresh-sync"}
    monkeypatch.setattr(routes, "get_idm_get_token_functions", lambda: {"keycloak": (lambda **_k: {"refresh_token": "sync-refresh"})})
    assert (await app_http_client.get("/api/auth/refresh")).status_code == 200

    # Cover path where provider entry is None (route currently raises TypeError -> handled as 500)
    user.idm_data["keycloak"] = None
    assert (await app_http_client.get("/api/auth/refresh")).status_code == 500


async def test_switch_user_http(app_http_client, monkeypatch):
    _common_patches(monkeypatch)
    monkeypatch.setattr(routes, "commit", _noop)
    monkeypatch.setattr(routes, "create_token", _oid)

    async def _idm_session(*_args, **_kwargs):
        return "sess"

    monkeypatch.setattr(routes, "get_token_idm_session", _idm_session)

    session = Session(id=Id(str(ObjectId())), requires_csrf=True, token_data={})

    async def _none_user():
        return None

    app.dependency_overrides[utils.get_real_user_csrf] = _none_user
    app.dependency_overrides[utils.get_user_csrf] = _none_user
    async def _session_override():
        return session

    app.dependency_overrides[utils.get_session_csrf] = _session_override

    assert (await app_http_client.post("/api/admin/switchuser", json={"username": "target"})).status_code == 401

    real = _user_all("real", perms=[])
    actual = _user_all("actual")

    async def _real_user():
        return real

    async def _actual_user():
        return actual

    async def _session_dep():
        return session

    app.dependency_overrides[utils.get_real_user_csrf] = _real_user
    app.dependency_overrides[utils.get_user_csrf] = _actual_user
    app.dependency_overrides[utils.get_session_csrf] = _session_dep

    assert (await app_http_client.post("/api/admin/switchuser", json={"username": "target"})).status_code == 403

    real.permissions = [Permission(codename="SWITCH_USER")]

    async def _none_target(*_a, **_k):
        return None

    monkeypatch.setattr(routes, "get_user_with_all_info_by_username", _none_target)
    assert (await app_http_client.post("/api/admin/switchuser", json={"username": "target"})).status_code == 404

    async def _inactive_target(*_a, **_k):
        return _user_all("target", active=False)

    monkeypatch.setattr(routes, "get_user_with_all_info_by_username", _inactive_target)
    assert (await app_http_client.post("/api/admin/switchuser", json={"username": "target"})).status_code == 404

    async def _same_target(*_a, **_k):
        return actual

    monkeypatch.setattr(routes, "get_user_with_all_info_by_username", _same_target)
    assert (await app_http_client.post("/api/admin/switchuser", json={"username": "target"})).status_code == 204

    target = _user_all("target")

    async def _target(*_a, **_k):
        return target

    monkeypatch.setattr(routes, "get_user_with_all_info_by_username", _target)
    monkeypatch.setattr(routes, "resolve_url_name", lambda *_a, **_k: ("wirecloud.workspace_view", {"owner": "o", "name": "w"}))

    class _Workspace:
        async def is_accessible_by(self, _db, _user):
            return False

    async def _workspace(*_a, **_k):
        return _Workspace()

    monkeypatch.setattr(routes, "get_workspace_by_username_and_name", _workspace)

    blocked = await app_http_client.post("/api/admin/switchuser", json={"username": "target"}, headers={"Referer": "http://testserver/workspace/o/w"})
    assert blocked.status_code == 204
    assert "Location" not in blocked.headers

    monkeypatch.setattr(routes, "resolve_url_name", lambda *_a, **_k: None)
    ok = await app_http_client.post("/api/admin/switchuser", json={"username": "target"}, headers={"Referer": "http://testserver/some/path"})
    assert ok.status_code == 204
    assert ok.headers.get("Location") == "/some/path"

    other_host = await app_http_client.post("/api/admin/switchuser", json={"username": "target"}, headers={"Referer": "http://otherserver/some/path"})
    assert other_host.status_code == 204
    assert "Location" not in other_host.headers

    monkeypatch.setattr(routes, "resolve_url_name", lambda *_a, **_k: ("wirecloud.workspace_view", {"owner": "o", "name": "w"}))

    class _WorkspaceAllowed:
        async def is_accessible_by(self, _db, _user):
            return True

    async def _workspace_allowed(*_a, **_k):
        return _WorkspaceAllowed()

    monkeypatch.setattr(routes, "get_workspace_by_username_and_name", _workspace_allowed)
    allowed = await app_http_client.post("/api/admin/switchuser", json={"username": "target"}, headers={"Referer": "http://testserver/workspace/o/w"})
    assert allowed.status_code == 204
    assert allowed.headers.get("Location") == "/workspace/o/w"

    session_no_csrf = Session(id=Id(str(ObjectId())), requires_csrf=False, token_data={})

    async def _session_dep_no_csrf():
        return session_no_csrf

    app.dependency_overrides[utils.get_session_csrf] = _session_dep_no_csrf

    async def _real_target(*_a, **_k):
        return real

    monkeypatch.setattr(routes, "get_user_with_all_info_by_username", _real_target)
    resp_real = await app_http_client.post("/api/admin/switchuser", json={"username": real.username})
    assert resp_real.status_code == 204
