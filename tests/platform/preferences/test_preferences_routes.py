# -*- coding: utf-8 -*-

import json
from types import SimpleNamespace

import pytest

from wirecloud.main import app
from wirecloud import main as main_module
from wirecloud.commons.auth.utils import get_user_csrf, get_user_no_csrf
from wirecloud.platform.preferences import routes


async def _noop_close():
    return None


main_module.close = _noop_close


@pytest.fixture(autouse=True)
def _patch_gettext(monkeypatch):
    monkeypatch.setattr(routes, "_", lambda text: text)


@pytest.fixture()
def auth_state():
    user = SimpleNamespace(
        id="507f1f77bcf86cd799439011",
        username="alice",
        is_superuser=False,
        has_perm=lambda _perm: False,
    )
    return {"user": user}


@pytest.fixture(autouse=True)
def _override_auth(auth_state):
    async def _dep():
        return auth_state["user"]

    app.dependency_overrides[get_user_no_csrf] = _dep
    app.dependency_overrides[get_user_csrf] = _dep
    yield
    app.dependency_overrides.pop(get_user_no_csrf, None)
    app.dependency_overrides.pop(get_user_csrf, None)


def _workspace(editable=True, accessible=True):
    ws = SimpleNamespace(
        id="507f1f77bcf86cd799439012",
        public=False,
        requireauth=False,
        preferences=[],
        tabs={},
    )

    async def _is_editable_by(_db, _user):
        return editable

    async def _is_accessible_by(_db, _user):
        return accessible

    ws.is_editable_by = _is_editable_by
    ws.is_accessible_by = _is_accessible_by
    return ws


def _tab(tab_id="tab1"):
    return SimpleNamespace(id=tab_id, preferences=[])


async def test_platform_preferences_routes(app_client, monkeypatch, auth_state):
    monkeypatch.setattr(routes, "get_user_preferences", lambda _db, _uid: _prefs())

    async def _prefs():
        return [SimpleNamespace(name="lang", value="es"), SimpleNamespace(name="theme", value="default")]

    ok = await app_client.get("/api/preferences/platform/", headers={"accept": "application/json"})
    assert ok.status_code == 200
    assert ok.json()["lang"]["value"] == "es"

    monkeypatch.setattr(routes, "get_user_preferences", lambda _db, _uid: _none())

    async def _none():
        return None

    missing = await app_client.get("/api/preferences/platform/", headers={"accept": "application/json"})
    assert missing.status_code == 404

    auth_state["user"] = None
    anon = await app_client.get("/api/preferences/platform/", headers={"accept": "application/json"})
    assert anon.status_code == 200
    assert anon.json() == {}

    auth_state["user"] = SimpleNamespace(id="507f1f77bcf86cd799439011", username="alice", is_superuser=False, has_perm=lambda _perm: False)
    called = {"n": 0}

    async def _update_preferences(_db, _user, _create_obj):
        called["n"] += 1

    monkeypatch.setattr(routes, "update_preferences", _update_preferences)
    post = await app_client.post(
        "/api/preferences/platform/",
        json={"lang": {"value": "es"}},
        headers={"accept": "application/json", "content-type": "application/json"},
    )
    assert post.status_code == 204
    assert called["n"] == 1


async def test_get_workspace_preferences_route(app_client, monkeypatch):
    monkeypatch.setattr(routes, "get_workspace_by_id", lambda _db, _wid: _none_workspace())

    async def _none_workspace():
        return None

    missing = await app_client.get("/api/workspace/507f1f77bcf86cd799439011/preferences/", headers={"accept": "application/json"})
    assert missing.status_code == 404

    ws_inaccessible = _workspace(accessible=False)
    monkeypatch.setattr(routes, "get_workspace_by_id", lambda _db, _wid: _workspace_obj(ws_inaccessible))

    async def _workspace_obj(value):
        return value

    denied = await app_client.get("/api/workspace/507f1f77bcf86cd799439011/preferences/", headers={"accept": "application/json"})
    assert denied.status_code == 403

    ws = _workspace(accessible=True)
    monkeypatch.setattr(routes, "get_workspace_by_id", lambda _db, _wid: _workspace_obj(ws))
    monkeypatch.setattr(routes, "get_workspace_preference_values", lambda _workspace: _pref_values())

    async def _pref_values():
        return {"public": {"inherit": False, "value": "true"}}

    ok = await app_client.get("/api/workspace/507f1f77bcf86cd799439011/preferences/", headers={"accept": "application/json"})
    assert ok.status_code == 200
    assert ok.json()["public"]["value"] == "true"


async def test_create_workspace_preferences_route(app_client, monkeypatch):
    ws = _workspace(editable=True, accessible=True)
    ws.tabs = {"tab1": _tab()}
    monkeypatch.setattr(routes, "get_workspace_by_id", lambda _db, _wid: _workspace_obj(ws))

    async def _workspace_obj(value):
        return value

    monkeypatch.setattr(routes, "is_owner_or_has_permission", lambda _user, _ws, perm: perm in ("WORKSPACE.PREFERENCES.EDIT", "WORKSPACE.SHARE"))

    calls = {"clear_users": 0, "clear_groups": 0, "add_user": 0, "add_group": 0, "change": 0, "commit": 0, "update_ws": 0}

    async def _clear_users(_db, _ws):
        calls["clear_users"] += 1

    async def _clear_groups(_db, _ws):
        calls["clear_groups"] += 1

    async def _get_user(_db, name):
        if name == "missing-user":
            return None
        return SimpleNamespace(username=name)

    async def _get_group(_db, name):
        if name == "missing-group":
            return None
        return SimpleNamespace(name=name)

    async def _add_user(_db, _ws, _user):
        calls["add_user"] += 1

    async def _add_group(_db, _ws, _group):
        calls["add_group"] += 1

    async def _change_ws(_db, _ws, _user):
        calls["change"] += 1

    async def _commit(_db):
        calls["commit"] += 1

    async def _update_ws(_db, _user, _ws, _prefs, invalidate_cache=True):
        calls["update_ws"] += 1

    monkeypatch.setattr(routes, "clear_workspace_users", _clear_users)
    monkeypatch.setattr(routes, "clear_workspace_groups", _clear_groups)
    monkeypatch.setattr(routes, "get_user_by_username", _get_user)
    monkeypatch.setattr(routes, "get_group_by_name", _get_group)
    monkeypatch.setattr(routes, "add_user_to_workspace", _add_user)
    monkeypatch.setattr(routes, "add_group_to_workspace", _add_group)
    monkeypatch.setattr(routes, "change_workspace", _change_ws)
    monkeypatch.setattr(routes, "commit", _commit)
    monkeypatch.setattr(routes, "update_workspace_preferences", _update_ws)
    original_validate = routes.ShareListPreference.model_validate

    call_index = {"n": 0}

    def _validate(item):
        call_index["n"] += 1
        if call_index["n"] == 1:
            return SimpleNamespace(type=routes.ShareListEnum.user, name="missing-user")
        if call_index["n"] == 2:
            return SimpleNamespace(type=routes.ShareListEnum.user, name="alice")
        if call_index["n"] == 3:
            return SimpleNamespace(type=routes.ShareListEnum.group, name="missing-group")
        if call_index["n"] == 4:
            return SimpleNamespace(type=routes.ShareListEnum.organization, name="org1")
        if call_index["n"] == 5:
            return SimpleNamespace(type="skip", name="noop")
        return original_validate(item)

    monkeypatch.setattr(routes.ShareListPreference, "model_validate", staticmethod(_validate))

    payload = {
        "sharelist": json.dumps(
            [
                {"type": "user", "name": "missing-user"},
                {"type": "user", "name": "alice"},
                {"type": "group", "name": "missing-group"},
                {"type": "organization", "name": "org1"},
                {"type": "user", "name": "noop"},
            ]
        ),
        "public": {"inherit": False, "value": "true"},
        "requireauth": "true",
        "title": "new-title",
    }

    ok = await app_client.post(
        "/api/workspace/507f1f77bcf86cd799439011/preferences/",
        json=payload,
        headers={"accept": "application/json", "content-type": "application/json"},
    )
    assert ok.status_code == 204
    assert calls["clear_users"] == 1
    assert calls["clear_groups"] == 1
    assert calls["add_user"] == 1
    assert calls["add_group"] == 1
    assert calls["change"] >= 1
    assert calls["commit"] == 1
    assert calls["update_ws"] >= 1
    assert ws.public is True
    assert ws.requireauth is True

    ws_public_string = _workspace(editable=True, accessible=True)
    monkeypatch.setattr(routes, "get_workspace_by_id", lambda _db, _wid: _workspace_obj(ws_public_string))
    monkeypatch.setattr(routes, "is_owner_or_has_permission", lambda _user, _ws, perm: perm in ("WORKSPACE.PREFERENCES.EDIT", "WORKSPACE.SHARE"))
    calls["change"] = calls["commit"] = calls["update_ws"] = 0
    ok_public_string = await app_client.post(
        "/api/workspace/507f1f77bcf86cd799439011/preferences/",
        json={"public": "false"},
        headers={"accept": "application/json", "content-type": "application/json"},
    )
    assert ok_public_string.status_code == 204
    assert calls["change"] == 1
    assert calls["commit"] == 1
    assert calls["update_ws"] == 2
    assert ws_public_string.public is False

    ws_non_shareable = _workspace(editable=True, accessible=True)
    monkeypatch.setattr(routes, "get_workspace_by_id", lambda _db, _wid: _workspace_obj(ws_non_shareable))
    monkeypatch.setattr(routes, "is_owner_or_has_permission", lambda _user, _ws, perm: perm == "WORKSPACE.PREFERENCES.EDIT")
    denied = await app_client.post(
        "/api/workspace/507f1f77bcf86cd799439011/preferences/",
        json={"sharelist": "[]"},
        headers={"accept": "application/json", "content-type": "application/json"},
    )
    assert denied.status_code == 403

    denied_public = await app_client.post(
        "/api/workspace/507f1f77bcf86cd799439011/preferences/",
        json={"public": "true"},
        headers={"accept": "application/json", "content-type": "application/json"},
    )
    assert denied_public.status_code == 403

    ws_non_editable = _workspace(editable=False, accessible=True)
    monkeypatch.setattr(routes, "get_workspace_by_id", lambda _db, _wid: _workspace_obj(ws_non_editable))
    denied_edit = await app_client.post(
        "/api/workspace/507f1f77bcf86cd799439011/preferences/",
        json={"title": "x"},
        headers={"accept": "application/json", "content-type": "application/json"},
    )
    assert denied_edit.status_code == 403

    monkeypatch.setattr(routes, "get_workspace_by_id", lambda _db, _wid: _none())

    async def _none():
        return None

    missing = await app_client.post(
        "/api/workspace/507f1f77bcf86cd799439011/preferences/",
        json={"title": "x"},
        headers={"accept": "application/json", "content-type": "application/json"},
    )
    assert missing.status_code == 404

    ws_requireauth = _workspace(editable=True, accessible=True)
    monkeypatch.setattr(routes, "get_workspace_by_id", lambda _db, _wid: _workspace_obj(ws_requireauth))
    monkeypatch.setattr(routes, "is_owner_or_has_permission", lambda _user, _ws, perm: perm == "WORKSPACE.PREFERENCES.EDIT")
    calls["change"] = calls["commit"] = calls["update_ws"] = 0
    ok_requireauth = await app_client.post(
        "/api/workspace/507f1f77bcf86cd799439011/preferences/",
        json={"requireauth": {"inherit": False, "value": "false"}},
        headers={"accept": "application/json", "content-type": "application/json"},
    )
    assert ok_requireauth.status_code == 204
    assert calls["change"] == 1
    assert calls["commit"] == 1
    assert calls["update_ws"] == 1
    assert ws_requireauth.requireauth is False

    ws_only_sharelist_obj = _workspace(editable=True, accessible=True)
    monkeypatch.setattr(routes, "get_workspace_by_id", lambda _db, _wid: _workspace_obj(ws_only_sharelist_obj))
    monkeypatch.setattr(routes, "is_owner_or_has_permission", lambda _user, _ws, perm: perm in ("WORKSPACE.PREFERENCES.EDIT", "WORKSPACE.SHARE"))
    calls["change"] = calls["commit"] = calls["clear_users"] = calls["clear_groups"] = calls["update_ws"] = 0
    sharelist_object = await app_client.post(
        "/api/workspace/507f1f77bcf86cd799439011/preferences/",
        json={"sharelist": {"inherit": False, "value": "[]"}},
        headers={"accept": "application/json", "content-type": "application/json"},
    )
    assert sharelist_object.status_code == 204
    assert calls["clear_users"] == 1
    assert calls["clear_groups"] == 1
    assert calls["change"] == 0
    assert calls["commit"] == 0
    assert calls["update_ws"] == 1

    ws_simple = _workspace(editable=True, accessible=True)
    monkeypatch.setattr(routes, "get_workspace_by_id", lambda _db, _wid: _workspace_obj(ws_simple))
    monkeypatch.setattr(routes, "is_owner_or_has_permission", lambda _user, _ws, perm: perm in ("WORKSPACE.PREFERENCES.EDIT", "WORKSPACE.SHARE"))
    calls["change"] = calls["commit"] = calls["update_ws"] = 0
    simple_update = await app_client.post(
        "/api/workspace/507f1f77bcf86cd799439011/preferences/",
        json={"title": "plain"},
        headers={"accept": "application/json", "content-type": "application/json"},
    )
    assert simple_update.status_code == 204
    assert calls["change"] == 0
    assert calls["commit"] == 0
    assert calls["update_ws"] == 1


async def test_tab_preferences_routes(app_client, monkeypatch):
    ws = _workspace(editable=True, accessible=True)
    ws.tabs = {"tab1": _tab("tab1")}

    monkeypatch.setattr(routes, "get_workspace_by_id", lambda _db, _wid: _workspace_obj(ws))

    async def _workspace_obj(value):
        return value

    monkeypatch.setattr(routes, "get_tab_preference_values", lambda _tab: _tab_values())

    async def _tab_values():
        return {"initiallayout": {"inherit": True, "value": "{}"}}

    ok_get = await app_client.get(
        "/api/workspace/507f1f77bcf86cd799439011/tab/tab1/preferences/",
        headers={"accept": "application/json"},
    )
    assert ok_get.status_code == 200
    assert ok_get.json()["initiallayout"]["inherit"] is True

    ws_inaccessible = _workspace(editable=True, accessible=False)
    ws_inaccessible.tabs = {"tab1": _tab("tab1")}
    monkeypatch.setattr(routes, "get_workspace_by_id", lambda _db, _wid: _workspace_obj(ws_inaccessible))
    denied_get = await app_client.get(
        "/api/workspace/507f1f77bcf86cd799439011/tab/tab1/preferences/",
        headers={"accept": "application/json"},
    )
    assert denied_get.status_code == 403

    ws_missing_tab = _workspace(editable=True, accessible=True)
    ws_missing_tab.tabs = {}
    monkeypatch.setattr(routes, "get_workspace_by_id", lambda _db, _wid: _workspace_obj(ws_missing_tab))
    missing_tab = await app_client.get(
        "/api/workspace/507f1f77bcf86cd799439011/tab/tab1/preferences/",
        headers={"accept": "application/json"},
    )
    assert missing_tab.status_code == 404

    monkeypatch.setattr(routes, "get_workspace_by_id", lambda _db, _wid: _none_workspace())

    async def _none_workspace():
        return None

    missing_ws = await app_client.get(
        "/api/workspace/507f1f77bcf86cd799439011/tab/tab1/preferences/",
        headers={"accept": "application/json"},
    )
    assert missing_ws.status_code == 404

    ws_update = _workspace(editable=True, accessible=True)
    ws_update.tabs = {"tab1": _tab("tab1")}
    monkeypatch.setattr(routes, "get_workspace_by_id", lambda _db, _wid: _workspace_obj(ws_update))
    monkeypatch.setattr(routes, "is_owner_or_has_permission", lambda _user, _ws, perm: perm == "WORKSPACE.TAB.PREFERENCES.EDIT")
    called = {"n": 0}

    async def _update_tab(_db, _user, _workspace, _tab, _preferences):
        called["n"] += 1

    monkeypatch.setattr(routes, "update_tab_preferences", _update_tab)
    ok_post = await app_client.post(
        "/api/workspace/507f1f77bcf86cd799439011/tab/tab1/preferences/",
        json={"initiallayout": {"inherit": False, "value": "{}"}},
        headers={"accept": "application/json", "content-type": "application/json"},
    )
    assert ok_post.status_code == 204
    assert called["n"] == 1

    monkeypatch.setattr(routes, "is_owner_or_has_permission", lambda _user, _ws, perm: False)
    denied_post = await app_client.post(
        "/api/workspace/507f1f77bcf86cd799439011/tab/tab1/preferences/",
        json={"initiallayout": {"inherit": False, "value": "{}"}},
        headers={"accept": "application/json", "content-type": "application/json"},
    )
    assert denied_post.status_code == 403


async def test_create_tab_preferences_missing_branches(app_client, monkeypatch):
    async def _none_workspace():
        return None

    monkeypatch.setattr(routes, "get_workspace_by_id", lambda _db, _wid: _none_workspace())
    missing_ws = await app_client.post(
        "/api/workspace/507f1f77bcf86cd799439011/tab/tab1/preferences/",
        json={"initiallayout": {"inherit": False, "value": "{}"}},
        headers={"accept": "application/json", "content-type": "application/json"},
    )
    assert missing_ws.status_code == 404

    ws = _workspace(editable=True, accessible=True)
    ws.tabs = {}

    async def _workspace_obj():
        return ws

    monkeypatch.setattr(routes, "get_workspace_by_id", lambda _db, _wid: _workspace_obj())
    missing_tab = await app_client.post(
        "/api/workspace/507f1f77bcf86cd799439011/tab/tab1/preferences/",
        json={"initiallayout": {"inherit": False, "value": "{}"}},
        headers={"accept": "application/json", "content-type": "application/json"},
    )
    assert missing_tab.status_code == 404
