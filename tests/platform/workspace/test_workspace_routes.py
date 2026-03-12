# -*- coding: utf-8 -*-

from types import SimpleNamespace

import pytest

from wirecloud import main as main_module
from wirecloud.commons.auth.utils import get_user_csrf, get_user_no_csrf
from wirecloud.main import app
from wirecloud.platform.workspace import routes
from wirecloud.platform.workspace.schemas import TabData, WorkspaceData


async def _noop_close():
    return None


main_module.close = _noop_close


@pytest.fixture(autouse=True)
def _patch_gettext(monkeypatch):
    monkeypatch.setattr(routes, "_", lambda text: text)


@pytest.fixture()
def auth_state():
    state = {
        "perms": set(),
        "user": SimpleNamespace(
            id="507f1f77bcf86cd799439011",
            username="alice",
            is_superuser=False,
            has_perm=lambda perm: perm in state["perms"],
        ),
    }
    return state


@pytest.fixture(autouse=True)
def _override_auth(auth_state):
    async def _dep():
        return auth_state["user"]

    app.dependency_overrides[get_user_no_csrf] = _dep
    app.dependency_overrides[get_user_csrf] = _dep
    yield
    app.dependency_overrides.pop(get_user_no_csrf, None)
    app.dependency_overrides.pop(get_user_csrf, None)


def _workspace(editable=True, accessible=True, tab_id="tab-0", creator="507f1f77bcf86cd799439011"):
    ws = SimpleNamespace(
        id="507f1f77bcf86cd799439012",
        creator=creator,
        name="workspace",
        title="Workspace",
        description="",
        longdescription="",
        tabs={tab_id: SimpleNamespace(id=tab_id, name="tab", title="Tab", visible=True, widgets={})},
    )

    async def _is_editable_by(_db, _user):
        return editable

    async def _is_accessible_by(_db, _user):
        return accessible

    ws.is_editable_by = _is_editable_by
    ws.is_accessible_by = _is_accessible_by
    return ws


class _CacheableResponse:
    def __init__(self, payload):
        self.payload = payload

    def get_response(self, status_code=200, cacheable=True):
        return routes.Response(status_code=status_code, content=self.payload, media_type="application/json")


async def test_workspace_collection_routes(app_client, db_session, monkeypatch, auth_state):
    async def _list(*_args, **_kwargs):
        return [_workspace()]

    async def _data(*_args, **_kwargs):
        return WorkspaceData(
            id="507f1f77bcf86cd799439012",
            name="workspace",
            title="Workspace",
            public=False,
            shared=False,
            requireauth=False,
            owner="alice",
            removable=True,
            lastmodified="2026-03-12T00:00:00Z",
            description="",
            longdescription="",
        )

    monkeypatch.setattr(routes, "get_workspace_list", _list)
    monkeypatch.setattr(routes, "get_workspace_data", _data)
    listed = await app_client.get("/api/workspaces/")
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    payload = {"name": "new-workspace", "title": "", "workspace": "", "mashup": "", "preferences": {}}
    denied = await app_client.post("/api/workspaces/", json=payload)
    assert denied.status_code == 403

    auth_state["perms"].add("WORKSPACE.CREATE")

    dry = await app_client.post("/api/workspaces/", json={**payload, "dry_run": True})
    assert dry.status_code == 204

    async def _empty_none(*_args, **_kwargs):
        return None

    monkeypatch.setattr(routes, "create_empty_workspace", _empty_none)
    conflict = await app_client.post("/api/workspaces/", json=payload)
    assert conflict.status_code == 409

    async def _empty_workspace(*_args, **_kwargs):
        return _workspace()

    monkeypatch.setattr(routes, "create_empty_workspace", _empty_workspace)
    monkeypatch.setattr(routes, "get_global_workspace_data", lambda *_args, **_kwargs: _ok_data())
    monkeypatch.setattr(routes, "add_workspace_to_index", lambda *_args, **_kwargs: _none())

    async def _ok_data():
        return _CacheableResponse("{\"id\":\"ok\"}")

    async def _none():
        return None

    created = await app_client.post("/api/workspaces/", json=payload)
    assert created.status_code == 201

    monkeypatch.setattr(routes, "get_workspace_by_id", lambda *_args, **_kwargs: _none())
    missing_source = await app_client.post(
        "/api/workspaces/",
        json={"name": "clone", "title": "", "workspace": "507f1f77bcf86cd799439012", "mashup": "", "preferences": {}},
    )
    assert missing_source.status_code == 404

    source = _workspace(accessible=False)
    monkeypatch.setattr(routes, "get_workspace_by_id", lambda *_args, **_kwargs: _src(source))
    monkeypatch.setattr(routes, "is_owner_or_has_permission", lambda *_args, **_kwargs: False)

    async def _src(value):
        return value

    forbidden_clone = await app_client.post(
        "/api/workspaces/",
        json={"name": "clone", "title": "", "workspace": "507f1f77bcf86cd799439012", "mashup": "", "preferences": {}},
    )
    assert forbidden_clone.status_code == 403

    source = _workspace(accessible=True)
    monkeypatch.setattr(routes, "get_workspace_by_id", lambda *_args, **_kwargs: _src(source))
    monkeypatch.setattr(routes, "is_owner_or_has_permission", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(routes, "create_workspace", lambda *_args, **_kwargs: _value_error())

    async def _value_error():
        raise ValueError("bad")

    bad_create = await app_client.post(
        "/api/workspaces/",
        json={"name": "clone", "title": "", "workspace": "507f1f77bcf86cd799439012", "mashup": "", "preferences": {}},
    )
    assert bad_create.status_code == 422

    monkeypatch.setattr(routes, "create_workspace", lambda *_args, **_kwargs: _missing_deps())

    async def _missing_deps():
        raise routes.MissingDependencies(["acme/widget/1.0.0"])

    missing_dep = await app_client.post(
        "/api/workspaces/",
        json={"name": "clone", "title": "", "workspace": "507f1f77bcf86cd799439012", "mashup": "", "preferences": {}},
    )
    assert missing_dep.status_code == 422


async def test_workspace_entry_routes(app_client, db_session, monkeypatch):
    ws = _workspace()

    async def _ws(*_args, **_kwargs):
        return ws

    async def _none(*_args, **_kwargs):
        return None

    monkeypatch.setattr(routes, "get_workspace_by_id", _ws)
    monkeypatch.setattr(routes, "get_workspace_entry", lambda *_args, **_kwargs: _ok())

    async def _ok():
        return routes.Response(status_code=200, content="{}", media_type="application/json")

    by_id = await app_client.get("/api/workspace/507f1f77bcf86cd799439012/")
    assert by_id.status_code == 200

    monkeypatch.setattr(routes, "get_workspace_by_username_and_name", _ws)
    by_name = await app_client.get("/api/workspace/alice/workspace/")
    assert by_name.status_code == 200

    monkeypatch.setattr(routes, "get_workspace_by_id", _none)
    missing = await app_client.post("/api/workspace/507f1f77bcf86cd799439012/", json={"name": "new"})
    assert missing.status_code == 404

    ws = _workspace(editable=False)
    monkeypatch.setattr(routes, "get_workspace_by_id", lambda *_args, **_kwargs: _ws_val(ws))

    async def _ws_val(v):
        return v

    forbidden = await app_client.post("/api/workspace/507f1f77bcf86cd799439012/", json={"name": "new"})
    assert forbidden.status_code == 403

    ws = _workspace(editable=True)
    monkeypatch.setattr(routes, "get_workspace_by_id", lambda *_args, **_kwargs: _ws_val(ws))
    monkeypatch.setattr(routes, "is_a_workspace_with_that_name", lambda *_args, **_kwargs: _true())

    async def _true():
        return True

    conflict = await app_client.post("/api/workspace/507f1f77bcf86cd799439012/", json={"name": "new"})
    assert conflict.status_code == 409

    calls = {"n": 0}

    async def _change_workspace(*_args, **_kwargs):
        calls["n"] += 1

    monkeypatch.setattr(routes, "is_a_workspace_with_that_name", lambda *_args, **_kwargs: _none())
    monkeypatch.setattr(routes, "change_workspace", _change_workspace)
    updated = await app_client.post(
        "/api/workspace/507f1f77bcf86cd799439012/",
        json={"title": "New title", "description": "d", "longdescription": "ld"},
    )
    assert updated.status_code == 204
    assert calls["n"] == 1

    monkeypatch.setattr(routes, "get_workspace_by_id", _none)
    del_missing = await app_client.delete("/api/workspace/507f1f77bcf86cd799439012/")
    assert del_missing.status_code == 404

    ws = _workspace(editable=False)
    monkeypatch.setattr(routes, "get_workspace_by_id", lambda *_args, **_kwargs: _ws_val(ws))
    monkeypatch.setattr(routes, "is_owner_or_has_permission", lambda *_args, **_kwargs: True)
    del_forbidden = await app_client.delete("/api/workspace/507f1f77bcf86cd799439012/")
    assert del_forbidden.status_code == 403

    deleted = {"n": 0}

    async def _delete_workspace(*_args, **_kwargs):
        deleted["n"] += 1

    ws = _workspace(editable=True)
    monkeypatch.setattr(routes, "get_workspace_by_id", lambda *_args, **_kwargs: _ws_val(ws))
    monkeypatch.setattr(routes, "is_owner_or_has_permission", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(routes, "delete_workspace", _delete_workspace)
    del_ok = await app_client.delete("/api/workspace/507f1f77bcf86cd799439012/")
    assert del_ok.status_code == 204
    assert deleted["n"] == 1


async def test_tab_routes(app_client, db_session, monkeypatch):
    async def _none(*_args, **_kwargs):
        return None

    monkeypatch.setattr(routes, "get_workspace_by_id", _none)
    missing_ws = await app_client.post("/api/workspace/507f1f77bcf86cd799439012/tabs/", json={"name": "", "title": ""})
    assert missing_ws.status_code == 404

    ws = _workspace(editable=True)
    monkeypatch.setattr(routes, "get_workspace_by_id", lambda *_args, **_kwargs: _ws_val(ws))

    async def _ws_val(v):
        return v

    malformed = await app_client.post("/api/workspace/507f1f77bcf86cd799439012/tabs/", json={"name": "", "title": ""})
    assert malformed.status_code == 422

    ws = _workspace(editable=False)
    monkeypatch.setattr(routes, "get_workspace_by_id", lambda *_args, **_kwargs: _ws_val(ws))
    monkeypatch.setattr(routes, "is_owner_or_has_permission", lambda *_args, **_kwargs: True)
    forbidden = await app_client.post("/api/workspace/507f1f77bcf86cd799439012/tabs/", json={"name": "t2", "title": "T2"})
    assert forbidden.status_code == 403

    ws = _workspace(editable=True)
    ws.tabs["tab-1"] = SimpleNamespace(id="tab-1", name="dup", title="Dup", visible=False, widgets={})
    monkeypatch.setattr(routes, "get_workspace_by_id", lambda *_args, **_kwargs: _ws_val(ws))
    monkeypatch.setattr(routes, "is_owner_or_has_permission", lambda *_args, **_kwargs: True)
    conflict = await app_client.post("/api/workspace/507f1f77bcf86cd799439012/tabs/", json={"name": "dup", "title": "Dup"})
    assert conflict.status_code == 409

    async def _create_tab(*_args, **_kwargs):
        return ws.tabs["tab-0"]

    async def _tab_data(*_args, **_kwargs):
        return TabData(id="tab-0", name="tab", title="Tab")

    monkeypatch.setattr(routes, "create_tab", _create_tab)
    monkeypatch.setattr(routes, "get_tab_data", _tab_data)
    created = await app_client.post("/api/workspace/507f1f77bcf86cd799439012/tabs/", json={"name": "new-tab", "title": ""})
    assert created.status_code == 200

    monkeypatch.setattr(routes, "get_workspace_by_id", _none)
    get_missing = await app_client.get("/api/workspace/507f1f77bcf86cd799439012/tab/tab-0/")
    assert get_missing.status_code == 404

    ws = _workspace(accessible=False)
    monkeypatch.setattr(routes, "get_workspace_by_id", lambda *_args, **_kwargs: _ws_val(ws))
    get_forbidden = await app_client.get("/api/workspace/507f1f77bcf86cd799439012/tab/tab-0/")
    assert get_forbidden.status_code == 403

    ws = _workspace(accessible=True)
    ws.tabs = {}
    monkeypatch.setattr(routes, "get_workspace_by_id", lambda *_args, **_kwargs: _ws_val(ws))
    get_missing_tab = await app_client.get("/api/workspace/507f1f77bcf86cd799439012/tab/tab-0/")
    assert get_missing_tab.status_code == 404

    ws = _workspace(accessible=True)
    monkeypatch.setattr(routes, "get_workspace_by_id", lambda *_args, **_kwargs: _ws_val(ws))
    monkeypatch.setattr(routes, "get_tab_data", _tab_data)
    get_ok = await app_client.get("/api/workspace/507f1f77bcf86cd799439012/tab/tab-0/")
    assert get_ok.status_code == 200

    monkeypatch.setattr(routes, "get_workspace_by_id", _none)
    upd_missing = await app_client.post("/api/workspace/507f1f77bcf86cd799439012/tab/tab-0/", json={"name": "x", "title": "x"})
    assert upd_missing.status_code == 404

    ws = _workspace(editable=False)
    monkeypatch.setattr(routes, "get_workspace_by_id", lambda *_args, **_kwargs: _ws_val(ws))
    monkeypatch.setattr(routes, "is_owner_or_has_permission", lambda *_args, **_kwargs: True)
    upd_forbidden = await app_client.post("/api/workspace/507f1f77bcf86cd799439012/tab/tab-0/", json={"name": "x", "title": "x"})
    assert upd_forbidden.status_code == 403

    ws = _workspace(editable=True)
    ws.tabs = {}
    monkeypatch.setattr(routes, "get_workspace_by_id", lambda *_args, **_kwargs: _ws_val(ws))
    upd_missing_tab = await app_client.post("/api/workspace/507f1f77bcf86cd799439012/tab/tab-0/", json={"name": "x", "title": "x"})
    assert upd_missing_tab.status_code == 404

    ws = _workspace(editable=True)
    ws.tabs["tab-1"] = SimpleNamespace(id="tab-1", name="dup", title="Dup", visible=False, widgets={})
    monkeypatch.setattr(routes, "get_workspace_by_id", lambda *_args, **_kwargs: _ws_val(ws))
    upd_conflict = await app_client.post("/api/workspace/507f1f77bcf86cd799439012/tab/tab-0/", json={"name": "dup", "title": "x"})
    assert upd_conflict.status_code == 409

    visible_calls = {"n": 0}

    async def _set_visible(*_args, **_kwargs):
        visible_calls["n"] += 1

    async def _change_tab(*_args, **_kwargs):
        return None

    monkeypatch.setattr(routes, "set_visible_tab", _set_visible)
    monkeypatch.setattr(routes, "change_tab", _change_tab)
    upd_ok = await app_client.post("/api/workspace/507f1f77bcf86cd799439012/tab/tab-0/", json={"name": "renamed", "title": "Renamed", "visible": True})
    assert upd_ok.status_code == 204
    assert visible_calls["n"] == 1

    monkeypatch.setattr(routes, "get_workspace_by_id", _none)
    del_missing_ws = await app_client.delete("/api/workspace/507f1f77bcf86cd799439012/tab/tab-0/")
    assert del_missing_ws.status_code == 404

    ws = _workspace(editable=True)
    ws.tabs = {}
    monkeypatch.setattr(routes, "get_workspace_by_id", lambda *_args, **_kwargs: _ws_val(ws))
    del_missing_tab = await app_client.delete("/api/workspace/507f1f77bcf86cd799439012/tab/tab-0/")
    assert del_missing_tab.status_code == 404

    ws = _workspace(editable=False)
    monkeypatch.setattr(routes, "get_workspace_by_id", lambda *_args, **_kwargs: _ws_val(ws))
    monkeypatch.setattr(routes, "is_owner_or_has_permission", lambda *_args, **_kwargs: True)
    del_forbidden = await app_client.delete("/api/workspace/507f1f77bcf86cd799439012/tab/tab-0/")
    assert del_forbidden.status_code == 403

    ws = _workspace(editable=True)
    ws.tabs = {"tab-0": ws.tabs["tab-0"]}
    monkeypatch.setattr(routes, "get_workspace_by_id", lambda *_args, **_kwargs: _ws_val(ws))
    monkeypatch.setattr(routes, "is_owner_or_has_permission", lambda *_args, **_kwargs: True)
    del_single = await app_client.delete("/api/workspace/507f1f77bcf86cd799439012/tab/tab-0/")
    assert del_single.status_code == 403

    ws = _workspace(editable=True)
    ws.tabs["tab-0"].widgets = {"w1": SimpleNamespace(read_only=True)}
    ws.tabs["tab-1"] = SimpleNamespace(id="tab-1", name="tab1", title="Tab1", visible=False, widgets={})
    monkeypatch.setattr(routes, "get_workspace_by_id", lambda *_args, **_kwargs: _ws_val(ws))
    del_readonly = await app_client.delete("/api/workspace/507f1f77bcf86cd799439012/tab/tab-0/")
    assert del_readonly.status_code == 403

    ws = _workspace(editable=True)
    ws.tabs["tab-1"] = SimpleNamespace(id="tab-1", name="tab1", title="Tab1", visible=False, widgets={})
    changed = {"n": 0}

    async def _change_workspace(*_args, **_kwargs):
        changed["n"] += 1

    monkeypatch.setattr(routes, "get_workspace_by_id", lambda *_args, **_kwargs: _ws_val(ws))
    monkeypatch.setattr(routes, "change_workspace", _change_workspace)
    del_ok = await app_client.delete("/api/workspace/507f1f77bcf86cd799439012/tab/tab-0/")
    assert del_ok.status_code == 204
    assert changed["n"] == 1


async def test_merge_publish_and_helpers_routes(app_client, db_session, monkeypatch, auth_state):
    assert routes.check_json_fields({"a": 1}, ("a", "b")) == ["b"]

    async def _none(*_args, **_kwargs):
        return None

    monkeypatch.setattr(routes, "get_workspace_by_id", _none)
    missing = await app_client.post("/api/workspace/507f1f77bcf86cd799439012/merge/", json={"workspace": "", "mashup": "a/b/1.0.0"})
    assert missing.status_code == 404

    ws = _workspace(editable=False)
    monkeypatch.setattr(routes, "get_workspace_by_id", lambda *_args, **_kwargs: _ws_val(ws))

    async def _ws_val(v):
        return v

    monkeypatch.setattr(routes, "is_owner_or_has_permission", lambda *_args, **_kwargs: True)
    forbidden = await app_client.post("/api/workspace/507f1f77bcf86cd799439012/merge/", json={"workspace": "", "mashup": "a/b/1.0.0"})
    assert forbidden.status_code == 403

    ws = _workspace(editable=True)
    monkeypatch.setattr(routes, "get_workspace_by_id", lambda *_args, **_kwargs: _ws_val(ws))
    monkeypatch.setattr(routes, "is_owner_or_has_permission", lambda *_args, **_kwargs: True)
    missing_params = await app_client.post("/api/workspace/507f1f77bcf86cd799439012/merge/", json={"workspace": "", "mashup": ""})
    assert missing_params.status_code == 422
    both_params = await app_client.post("/api/workspace/507f1f77bcf86cd799439012/merge/", json={"workspace": "x", "mashup": "a/b/1.0.0"})
    assert both_params.status_code == 422
    invalid_mashup = await app_client.post("/api/workspace/507f1f77bcf86cd799439012/merge/", json={"workspace": "", "mashup": "invalid"})
    assert invalid_mashup.status_code == 422

    monkeypatch.setattr(routes, "get_catalogue_resource", _none)
    mashup_not_found = await app_client.post("/api/workspace/507f1f77bcf86cd799439012/merge/", json={"workspace": "", "mashup": "a/b/1.0.0"})
    assert mashup_not_found.status_code == 404

    async def _resource():
        return SimpleNamespace(is_available_for=lambda _user: False, resource_type=lambda: "mashup")

    monkeypatch.setattr(routes, "get_catalogue_resource", lambda *_args, **_kwargs: _resource())
    mashup_unavailable = await app_client.post("/api/workspace/507f1f77bcf86cd799439012/merge/", json={"workspace": "", "mashup": "a/b/1.0.0"})
    assert mashup_unavailable.status_code == 404

    auth_state["perms"] = set()
    denied_publish = await app_client.post(
        "/api/workspace/507f1f77bcf86cd799439012/publish/",
        files={"json": (None, "{\"type\":\"mashup\",\"name\":\"x\",\"vendor\":\"v\",\"version\":\"1.0\"}")},
    )
    assert denied_publish.status_code == 403

    auth_state["perms"] = {"WORKSPACE.PUBLISH"}
    monkeypatch.setattr(routes, "is_valid_vendor", lambda _v: False)
    invalid_vendor = await app_client.post(
        "/api/workspace/507f1f77bcf86cd799439012/publish/",
        files={"json": (None, "{\"type\":\"mashup\",\"name\":\"x\",\"vendor\":\"v\",\"version\":\"1.0\"}")},
    )
    assert invalid_vendor.status_code == 400

    monkeypatch.setattr(routes, "is_valid_vendor", lambda _v: True)
    monkeypatch.setattr(routes, "is_valid_name", lambda _v: False)
    invalid_name = await app_client.post(
        "/api/workspace/507f1f77bcf86cd799439012/publish/",
        files={"json": (None, "{\"type\":\"mashup\",\"name\":\"x\",\"vendor\":\"v\",\"version\":\"1.0\"}")},
    )
    assert invalid_name.status_code == 400

    monkeypatch.setattr(routes, "is_valid_name", lambda _v: True)
    monkeypatch.setattr(routes, "is_valid_version", lambda _v: False)
    invalid_version = await app_client.post(
        "/api/workspace/507f1f77bcf86cd799439012/publish/",
        files={"json": (None, "{\"type\":\"mashup\",\"name\":\"x\",\"vendor\":\"v\",\"version\":\"1.0\"}")},
    )
    assert invalid_version.status_code == 400

    monkeypatch.setattr(routes, "is_valid_version", lambda _v: True)
    monkeypatch.setattr(routes, "get_workspace_by_id", _none)
    missing_workspace = await app_client.post(
        "/api/workspace/507f1f77bcf86cd799439012/publish/",
        files={"json": (None, "{\"type\":\"mashup\",\"name\":\"x\",\"vendor\":\"v\",\"version\":\"1.0\"}")},
    )
    assert missing_workspace.status_code == 404

    ws = _workspace(editable=False, creator="another-user")
    monkeypatch.setattr(routes, "get_workspace_by_id", lambda *_args, **_kwargs: _ws_val(ws))
    forbidden_workspace = await app_client.post(
        "/api/workspace/507f1f77bcf86cd799439012/publish/",
        files={"json": (None, "{\"type\":\"mashup\",\"name\":\"x\",\"vendor\":\"v\",\"version\":\"1.0\"}")},
    )
    assert forbidden_workspace.status_code == 403

    # Merge success using mashup source
    ws_merge = _workspace(editable=True)
    monkeypatch.setattr(routes, "get_workspace_by_id", lambda *_args, **_kwargs: _ws_val(ws_merge))
    monkeypatch.setattr(routes, "is_owner_or_has_permission", lambda *_args, **_kwargs: True)

    async def _mashup_resource(*_args, **_kwargs):
        return SimpleNamespace(
            is_available_for=lambda _user: True,
            resource_type=lambda: "mashup",
            template_uri="mashup.wgt",
        )

    class _FakeWgtFile:
        def __init__(self, *_args, **_kwargs):
            pass

        def get_template(self):
            return {}

    class _FakeTemplateParser:
        def __init__(self, *_args, **_kwargs):
            self.data = {}

    async def _deps_ok(*_args, **_kwargs):
        return None

    async def _fill_ok(*_args, **_kwargs):
        return None

    monkeypatch.setattr(routes, "get_catalogue_resource", _mashup_resource)
    monkeypatch.setattr(routes.wgt_deployer, "get_base_dir", lambda *_args, **_kwargs: "/tmp")
    monkeypatch.setattr(routes, "WgtFile", _FakeWgtFile)
    monkeypatch.setattr(routes, "TemplateParser", _FakeTemplateParser)
    monkeypatch.setattr(routes, "check_mashup_dependencies", _deps_ok)
    monkeypatch.setattr(routes, "fill_workspace_using_template", _fill_ok)
    merge_ok = await app_client.post("/api/workspace/507f1f77bcf86cd799439012/merge/", json={"workspace": "", "mashup": "a/b/1.0.0"})
    assert merge_ok.status_code == 204

    # Merge success using workspace source
    source_ws = _workspace(accessible=True)

    async def _workspace_lookup(_db, wid):
        if str(wid) == "507f1f77bcf86cd799439099":
            return source_ws
        return ws_merge

    monkeypatch.setattr(routes, "get_workspace_by_id", _workspace_lookup)
    monkeypatch.setattr(routes, "build_json_template_from_workspace", lambda *_args, **_kwargs: _template_obj())

    async def _template_obj():
        return SimpleNamespace(model_dump_json=lambda: "{}")

    merge_workspace_ok = await app_client.post(
        "/api/workspace/507f1f77bcf86cd799439012/merge/",
        json={"workspace": "507f1f77bcf86cd799439099", "mashup": ""},
    )
    assert merge_workspace_ok.status_code == 204

    # Publish success
    auth_state["perms"] = {"WORKSPACE.PUBLISH"}
    ws_publish = _workspace(editable=True, creator=auth_state["user"].id)
    monkeypatch.setattr(routes, "get_workspace_by_id", lambda *_args, **_kwargs: _ws_val(ws_publish))
    monkeypatch.setattr(routes, "build_xml_template_from_workspace", lambda *_args, **_kwargs: _xml())

    async def _xml():
        return "<xml/>"

    class _FakeZip:
        def __init__(self, *_args, **_kwargs):
            self.files = []

        def writestr(self, *_args, **_kwargs):
            return None

        def write(self, *_args, **_kwargs):
            return None

        def close(self):
            return None

    class _FakeWgtOut:
        def __init__(self, *_args, **_kwargs):
            pass

    class _Processed:
        def model_dump_json(self):
            return "{\"id\":\"resource\"}"

    class _Published:
        def get_processed_info(self, _request):
            return _Processed()

    class _LocalCatalogue:
        async def publish(self, *_args, **_kwargs):
            return _Published()

    async def _embedded_resource(*_args, **_kwargs):
        return SimpleNamespace(template_uri="embedded.wgt")

    monkeypatch.setattr(routes.zipfile, "ZipFile", _FakeZip)
    monkeypatch.setattr(routes, "WgtFile", _FakeWgtOut)
    monkeypatch.setattr(routes, "get_local_catalogue", lambda: _LocalCatalogue())
    monkeypatch.setattr(routes, "get_catalogue_resource", _embedded_resource)
    monkeypatch.setattr(routes.wgt_deployer, "get_base_dir", lambda *_args, **_kwargs: "/tmp")

    json_payload = (
        "{\"type\":\"mashup\",\"name\":\"x\",\"vendor\":\"v\",\"version\":\"1.0\","
        "\"longdescription\":\"Long desc\",\"embedded\":[{\"vendor\":\"v\",\"name\":\"e\",\"version\":\"1.0\",\"src\":\"macs/v_e_1.0.wgt\"}]}"
    )
    publish_ok = await app_client.post(
        "/api/workspace/507f1f77bcf86cd799439012/publish/",
        files={
            "json": (None, json_payload),
            "image": ("img.png", b"img", "image/png"),
            "smartphoneimage": ("phone.png", b"img", "image/png"),
        },
    )
    assert publish_ok.status_code == 201


async def test_routes_remaining_branches(app_client, db_session, monkeypatch, auth_state):
    auth_state["perms"] = {"WORKSPACE.CREATE"}

    async def _ws_val(v):
        return v

    async def _none(*_args, **_kwargs):
        return None

    monkeypatch.setattr(routes, "update_workspace_preferences", lambda *_args, **_kwargs: _none())
    monkeypatch.setattr(routes, "add_workspace_to_index", lambda *_args, **_kwargs: _none())
    monkeypatch.setattr(routes, "get_global_workspace_data", lambda *_args, **_kwargs: _ok_data())

    async def _ok_data():
        return _CacheableResponse("{\"id\":\"ok\"}")

    async def _create_ok(*_args, **_kwargs):
        return _workspace()

    monkeypatch.setattr(routes, "create_workspace", _create_ok)
    mashup_create = await app_client.post(
        "/api/workspaces/",
        json={"name": "new", "title": "", "workspace": "", "mashup": "acme/mashup/1.0.0", "preferences": {"x": {"value": "1", "inherit": False}}},
    )
    assert mashup_create.status_code == 201

    async def _create_none(*_args, **_kwargs):
        return None

    monkeypatch.setattr(routes, "create_workspace", _create_none)
    conflict = await app_client.post(
        "/api/workspaces/",
        json={"name": "new", "title": "", "workspace": "", "mashup": "acme/mashup/1.0.0", "preferences": {}},
    )
    assert conflict.status_code == 409

    monkeypatch.setattr(routes, "create_workspace", _create_ok)
    dry_run = await app_client.post(
        "/api/workspaces/",
        json={"name": "new", "title": "", "workspace": "", "mashup": "acme/mashup/1.0.0", "preferences": {}, "dry_run": True},
    )
    assert dry_run.status_code == 204

    ws = _workspace(editable=True)
    monkeypatch.setattr(routes, "get_workspace_by_id", lambda *_args, **_kwargs: _ws_val(ws))
    monkeypatch.setattr(routes, "is_a_workspace_with_that_name", lambda *_args, **_kwargs: _none())
    monkeypatch.setattr(routes, "change_workspace", lambda *_args, **_kwargs: _none())
    renamed = await app_client.post(
        "/api/workspace/507f1f77bcf86cd799439012/",
        json={"name": "renamed", "title": "", "description": "", "longdescription": ""},
    )
    assert renamed.status_code == 204

    ws = _workspace(editable=True)
    monkeypatch.setattr(routes, "get_workspace_by_id", lambda *_args, **_kwargs: _ws_val(ws))
    monkeypatch.setattr(routes, "change_tab", lambda *_args, **_kwargs: _none())
    tab_hide = await app_client.post(
        "/api/workspace/507f1f77bcf86cd799439012/tab/tab-0/",
        json={"name": "", "title": "", "visible": False},
    )
    assert tab_hide.status_code == 204
    assert ws.tabs["tab-0"].visible is False

    ws_merge = _workspace(editable=True)

    async def _workspace_lookup(_db, wid):
        if str(wid) == "507f1f77bcf86cd799439099":
            return None
        return ws_merge

    monkeypatch.setattr(routes, "get_workspace_by_id", _workspace_lookup)
    missing_from = await app_client.post(
        "/api/workspace/507f1f77bcf86cd799439012/merge/",
        json={"workspace": "507f1f77bcf86cd799439099", "mashup": ""},
    )
    assert missing_from.status_code == 404

    source_ws = _workspace(accessible=False)

    async def _workspace_lookup_forbidden(_db, wid):
        if str(wid) == "507f1f77bcf86cd799439099":
            return source_ws
        return ws_merge

    monkeypatch.setattr(routes, "get_workspace_by_id", _workspace_lookup_forbidden)
    forbidden_from = await app_client.post(
        "/api/workspace/507f1f77bcf86cd799439012/merge/",
        json={"workspace": "507f1f77bcf86cd799439099", "mashup": ""},
    )
    assert forbidden_from.status_code == 403

    async def _workspace_lookup_ok(_db, wid):
        if str(wid) == "507f1f77bcf86cd799439099":
            return _workspace(accessible=True)
        return ws_merge

    monkeypatch.setattr(routes, "get_workspace_by_id", _workspace_lookup_ok)
    monkeypatch.setattr(routes, "build_json_template_from_workspace", lambda *_args, **_kwargs: _template_obj())
    monkeypatch.setattr(routes, "TemplateParser", lambda *_args, **_kwargs: SimpleNamespace())

    async def _template_obj():
        return SimpleNamespace(model_dump_json=lambda: "{}")

    async def _missing_deps(*_args, **_kwargs):
        raise routes.MissingDependencies(["a/b/1.0.0"])

    monkeypatch.setattr(routes, "check_mashup_dependencies", _missing_deps)
    merge_missing_deps = await app_client.post(
        "/api/workspace/507f1f77bcf86cd799439012/merge/",
        json={"workspace": "507f1f77bcf86cd799439099", "mashup": ""},
    )
    assert merge_missing_deps.status_code == 422

    auth_state["perms"] = {"WORKSPACE.PUBLISH"}
    monkeypatch.setattr(routes, "check_json_fields", lambda *_args, **_kwargs: ["name"])
    malformed_json = await app_client.post(
        "/api/workspace/507f1f77bcf86cd799439012/publish/",
        files={"json": (None, "{\"type\":\"mashup\",\"name\":\"x\",\"vendor\":\"v\",\"version\":\"1.0\"}")},
    )
    assert malformed_json.status_code == 400


async def test_routes_branch_only_paths(app_client, db_session, monkeypatch, auth_state):
    auth_state["perms"] = {"WORKSPACE.CREATE", "WORKSPACE.PUBLISH"}

    async def _none(*_args, **_kwargs):
        return None

    async def _empty_workspace(*_args, **_kwargs):
        return _workspace()

    monkeypatch.setattr(routes, "create_empty_workspace", _empty_workspace)
    monkeypatch.setattr(routes, "add_workspace_to_index", lambda *_args, **_kwargs: _none())
    monkeypatch.setattr(routes, "get_global_workspace_data", lambda *_args, **_kwargs: _ok_data())

    async def _ok_data():
        return _CacheableResponse("{\"id\":\"ok\"}")

    title_given = await app_client.post(
        "/api/workspaces/",
        json={"name": "new-workspace", "title": "Title", "workspace": "", "mashup": "", "preferences": {}},
    )
    assert title_given.status_code == 201

    ws = _workspace(editable=True)
    changed = {"n": 0}

    async def _ws(*_args, **_kwargs):
        return ws

    async def _change_workspace(*_args, **_kwargs):
        changed["n"] += 1

    monkeypatch.setattr(routes, "get_workspace_by_id", _ws)
    monkeypatch.setattr(routes, "change_workspace", _change_workspace)
    no_change = await app_client.post(
        "/api/workspace/507f1f77bcf86cd799439012/",
        json={"name": "", "title": "", "description": "", "longdescription": ""},
    )
    assert no_change.status_code == 204
    assert changed["n"] == 0

    ws_del = _workspace(editable=True)
    ws_del.tabs["tab-0"].visible = False
    ws_del.tabs["tab-0"].widgets = {
        "w1": SimpleNamespace(read_only=False),
        "w2": SimpleNamespace(read_only=False),
    }
    ws_del.tabs["tab-1"] = SimpleNamespace(id="tab-1", name="tab1", title="Tab1", visible=False, widgets={})
    monkeypatch.setattr(routes, "get_workspace_by_id", lambda *_args, **_kwargs: _ws_del())
    monkeypatch.setattr(routes, "is_owner_or_has_permission", lambda *_args, **_kwargs: True)

    async def _ws_del():
        return ws_del

    del_calls = {"n": 0}

    async def _change_ws_del(*_args, **_kwargs):
        del_calls["n"] += 1

    monkeypatch.setattr(routes, "change_workspace", _change_ws_del)
    deleted = await app_client.delete("/api/workspace/507f1f77bcf86cd799439012/tab/tab-0/")
    assert deleted.status_code == 204
    assert del_calls["n"] == 1

    monkeypatch.setattr(routes, "check_json_fields", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(routes, "is_valid_vendor", lambda _v: True)
    monkeypatch.setattr(routes, "is_valid_name", lambda _v: True)
    monkeypatch.setattr(routes, "is_valid_version", lambda _v: True)

    async def _xml():
        return "<xml/>"

    class _FakeZip:
        def __init__(self, *_args, **_kwargs):
            pass

        def writestr(self, *_args, **_kwargs):
            return None

        def write(self, *_args, **_kwargs):
            return None

        def close(self):
            return None

    class _FakeWgtOut:
        def __init__(self, *_args, **_kwargs):
            pass

    class _Processed:
        def model_dump_json(self):
            return "{\"id\":\"resource\"}"

    class _Published:
        def get_processed_info(self, _request):
            return _Processed()

    class _LocalCatalogue:
        async def publish(self, *_args, **_kwargs):
            return _Published()

    async def _publish_ws(*_args, **_kwargs):
        return _workspace(editable=True)

    monkeypatch.setattr(routes, "get_workspace_by_id", _publish_ws)
    monkeypatch.setattr(routes, "build_xml_template_from_workspace", lambda *_args, **_kwargs: _xml())
    monkeypatch.setattr(routes.zipfile, "ZipFile", _FakeZip)
    monkeypatch.setattr(routes, "WgtFile", _FakeWgtOut)
    monkeypatch.setattr(routes, "get_local_catalogue", lambda: _LocalCatalogue())

    publish_no_optional = await app_client.post(
        "/api/workspace/507f1f77bcf86cd799439012/publish/",
        files={"json": (None, "{\"type\":\"mashup\",\"name\":\"x\",\"vendor\":\"v\",\"version\":\"1.0\",\"longdescription\":\"\"}")},
    )
    assert publish_no_optional.status_code == 201
