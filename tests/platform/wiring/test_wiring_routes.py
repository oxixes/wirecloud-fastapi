# -*- coding: utf-8 -*-

import json
from types import SimpleNamespace

import pytest

from wirecloud import main as main_module
from wirecloud.main import app
from wirecloud.commons.auth.utils import get_user_csrf, get_user_no_csrf
from wirecloud.commons.utils.cache import CacheableData
from wirecloud.platform.wiring import routes


async def _noop_close():
    return None


main_module.close = _noop_close


@pytest.fixture(autouse=True)
def _patch_gettext(monkeypatch):
    monkeypatch.setattr(routes, "_", lambda text: text)


@pytest.fixture()
def auth_state():
    state = {"perms": set()}
    state["user"] = SimpleNamespace(
        id="507f1f77bcf86cd799439011",
        username="alice",
        is_superuser=False,
        has_perm=lambda perm: perm in state["perms"],
    )
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


def _workspace(editable=True, accessible=True):
    ws = SimpleNamespace(
        id="507f1f77bcf86cd799439012",
        creator="507f1f77bcf86cd799439011",
        wiring_status=routes.WorkspaceWiring(),
    )

    async def _is_editable_by(_db, _user):
        return editable

    async def _is_accessible_by(_db, _user):
        return accessible

    ws.is_editable_by = _is_editable_by
    ws.is_accessible_by = _is_accessible_by
    return ws


def _wiring_payload():
    return {
        "version": "2.0",
        "connections": [],
        "operators": {},
        "visualdescription": {"behaviours": [], "components": {"widget": {}, "operator": {}}, "connections": []},
    }


async def test_update_wiring_entry_route(app_client, db_session, monkeypatch):
    async def _none(*_args, **_kwargs):
        return None

    monkeypatch.setattr(routes, "get_workspace_by_id", _none)
    missing = await app_client.put("/api/workspace/507f1f77bcf86cd799439012/wiring", json=_wiring_payload())
    assert missing.status_code == 404

    ws = _workspace(editable=True, accessible=True)
    ws.wiring_status.connections = [SimpleNamespace(readonly=False)]
    monkeypatch.setattr(routes, "get_workspace_by_id", lambda *_args, **_kwargs: _value(ws))
    monkeypatch.setattr(routes, "is_owner_or_has_permission", lambda *_args, **_kwargs: False)

    async def _value(v):
        return v

    forbidden_conn_delete = await app_client.put("/api/workspace/507f1f77bcf86cd799439012/wiring", json=_wiring_payload())
    assert forbidden_conn_delete.status_code == 403

    ws = _workspace(editable=True, accessible=True)
    ws.wiring_status.operators = {"1": SimpleNamespace()}
    monkeypatch.setattr(routes, "get_workspace_by_id", lambda *_args, **_kwargs: _value(ws))
    monkeypatch.setattr(routes, "is_owner_or_has_permission", lambda _user, _ws, perm: perm != "WORKSPACE.OPERATOR.DELETE")
    forbidden_op_delete = await app_client.put("/api/workspace/507f1f77bcf86cd799439012/wiring", json=_wiring_payload())
    assert forbidden_op_delete.status_code == 403

    ws = _workspace(editable=True, accessible=True)
    monkeypatch.setattr(routes, "get_workspace_by_id", lambda *_args, **_kwargs: _value(ws))
    monkeypatch.setattr(routes, "is_owner_or_has_permission", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(routes, "check_wiring", lambda *_args, **_kwargs: _resp())

    async def _resp():
        return routes.Response(status_code=422)

    check_resp = await app_client.put("/api/workspace/507f1f77bcf86cd799439012/wiring", json=_wiring_payload())
    assert check_resp.status_code == 422

    ws = _workspace(editable=False, accessible=True)
    changed = {"n": 0}

    async def _change(*_args, **_kwargs):
        changed["n"] += 1

    monkeypatch.setattr(routes, "get_workspace_by_id", lambda *_args, **_kwargs: _value(ws))
    monkeypatch.setattr(routes, "is_owner_or_has_permission", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(routes, "check_multiuser_wiring", lambda *_args, **_kwargs: _true())
    monkeypatch.setattr(routes, "change_workspace", _change)

    async def _true():
        return True

    multi_ok = await app_client.put("/api/workspace/507f1f77bcf86cd799439012/wiring", json=_wiring_payload())
    assert multi_ok.status_code == 204
    assert changed["n"] == 1

    ws = _workspace(editable=False, accessible=False)
    monkeypatch.setattr(routes, "get_workspace_by_id", lambda *_args, **_kwargs: _value(ws))
    monkeypatch.setattr(routes, "is_owner_or_has_permission", lambda *_args, **_kwargs: True)
    forbidden = await app_client.put("/api/workspace/507f1f77bcf86cd799439012/wiring", json=_wiring_payload())
    assert forbidden.status_code == 403

    ws = _workspace(editable=True, accessible=True)
    changed = {"n": 0}
    monkeypatch.setattr(routes, "get_workspace_by_id", lambda *_args, **_kwargs: _value(ws))
    monkeypatch.setattr(routes, "is_owner_or_has_permission", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(routes, "check_wiring", lambda *_args, **_kwargs: _true())
    monkeypatch.setattr(routes, "change_workspace", _change)
    ok = await app_client.put("/api/workspace/507f1f77bcf86cd799439012/wiring", json=_wiring_payload())
    assert ok.status_code == 204
    assert changed["n"] == 1


async def test_patch_wiring_entry_route(app_client, db_session, monkeypatch):
    async def _none(*_args, **_kwargs):
        return None

    payload = [{"op": "replace", "path": "/connections/0", "value": {}}]

    monkeypatch.setattr(routes, "get_workspace_by_id", _none)
    missing = await app_client.patch(
        "/api/workspace/507f1f77bcf86cd799439012/wiring",
        content=json.dumps(payload),
        headers={"content-type": "application/json-patch+json"},
    )
    assert missing.status_code == 404

    ws = _workspace(editable=True, accessible=True)
    monkeypatch.setattr(routes, "get_workspace_by_id", lambda *_args, **_kwargs: _value(ws))
    monkeypatch.setattr(routes, "is_owner_or_has_permission", lambda *_args, **_kwargs: False)

    async def _value(v):
        return v

    no_add_conn_perm = await app_client.patch(
        "/api/workspace/507f1f77bcf86cd799439012/wiring",
        content=json.dumps([{"op": "add", "path": "/connections/0", "value": {"readonly": False, "source": {"type": "widget", "id": "w1", "endpoint": "o"}, "target": {"type": "operator", "id": "1", "endpoint": "i"}}}]),
        headers={"content-type": "application/json-patch+json"},
    )
    assert no_add_conn_perm.status_code == 403

    monkeypatch.setattr(routes, "is_owner_or_has_permission", lambda _user, _ws, perm: perm != "WORKSPACE.OPERATOR.CREATE")
    no_add_op_perm = await app_client.patch(
        "/api/workspace/507f1f77bcf86cd799439012/wiring",
        content=json.dumps([{"op": "add", "path": "/operators/1", "value": {"id": "1", "name": "acme/op/1.0.0", "preferences": {}, "properties": {}}}]),
        headers={"content-type": "application/json-patch+json"},
    )
    assert no_add_op_perm.status_code == 403

    ws = _workspace(editable=True, accessible=True)
    ws.wiring_status.operators = {"1": SimpleNamespace(name="invalid")}
    monkeypatch.setattr(routes, "get_workspace_by_id", lambda *_args, **_kwargs: _value(ws))
    monkeypatch.setattr(routes, "is_owner_or_has_permission", lambda *_args, **_kwargs: True)
    bad_operator_name = await app_client.patch(
        "/api/workspace/507f1f77bcf86cd799439012/wiring",
        content=json.dumps([{"op": "replace", "path": "/operators/1/preferences/p1", "value": {"readonly": False, "hidden": False, "value": "x"}}]),
        headers={"content-type": "application/json-patch+json"},
    )
    assert bad_operator_name.status_code == 404

    ws.wiring_status.operators = {"1": SimpleNamespace(name="acme/op/1.0.0")}
    monkeypatch.setattr(routes, "get_catalogue_resource", _none)
    missing_resource = await app_client.patch(
        "/api/workspace/507f1f77bcf86cd799439012/wiring",
        content=json.dumps([{"op": "replace", "path": "/operators/1/preferences/p1", "value": {"readonly": False, "hidden": False, "value": "x"}}]),
        headers={"content-type": "application/json-patch+json"},
    )
    assert missing_resource.status_code == 403

    ws = _workspace(editable=True, accessible=True)
    monkeypatch.setattr(routes, "get_workspace_by_id", lambda *_args, **_kwargs: _value(ws))
    monkeypatch.setattr(routes, "is_owner_or_has_permission", lambda *_args, **_kwargs: True)
    bad_pointer = await app_client.patch(
        "/api/workspace/507f1f77bcf86cd799439012/wiring",
        content=json.dumps([{"op": "replace", "path": "/foo/bar", "value": 1}]),
        headers={"content-type": "application/json-patch+json"},
    )
    assert bad_pointer.status_code in (400, 422)

    invalid_patch = await app_client.patch(
        "/api/workspace/507f1f77bcf86cd799439012/wiring",
        content=json.dumps([{"op": "badop", "path": "/connections/0", "value": 1}]),
        headers={"content-type": "application/json-patch+json"},
    )
    assert invalid_patch.status_code == 400

    async def _resp():
        return routes.Response(status_code=422)

    monkeypatch.setattr(routes, "check_wiring", lambda *_args, **_kwargs: _resp())
    check_resp = await app_client.patch(
        "/api/workspace/507f1f77bcf86cd799439012/wiring",
        content=json.dumps([]),
        headers={"content-type": "application/json-patch+json"},
    )
    assert check_resp.status_code == 422

    ws = _workspace(editable=False, accessible=True)
    changed = {"n": 0}

    async def _change(*_args, **_kwargs):
        changed["n"] += 1

    monkeypatch.setattr(routes, "get_workspace_by_id", lambda *_args, **_kwargs: _value(ws))
    async def _true():
        return True

    monkeypatch.setattr(routes, "check_multiuser_wiring", lambda *_args, **_kwargs: _true())
    monkeypatch.setattr(routes, "change_workspace", _change)
    multi_ok = await app_client.patch(
        "/api/workspace/507f1f77bcf86cd799439012/wiring",
        content=json.dumps([]),
        headers={"content-type": "application/json-patch+json"},
    )
    assert multi_ok.status_code == 204
    assert changed["n"] == 1

    ws = _workspace(editable=False, accessible=False)
    monkeypatch.setattr(routes, "get_workspace_by_id", lambda *_args, **_kwargs: _value(ws))
    forbidden = await app_client.patch(
        "/api/workspace/507f1f77bcf86cd799439012/wiring",
        content=json.dumps([]),
        headers={"content-type": "application/json-patch+json"},
    )
    assert forbidden.status_code == 403

    ws = _workspace(editable=True, accessible=True)
    changed = {"n": 0}
    monkeypatch.setattr(routes, "get_workspace_by_id", lambda *_args, **_kwargs: _value(ws))
    monkeypatch.setattr(routes, "check_wiring", lambda *_args, **_kwargs: _true())
    monkeypatch.setattr(routes, "change_workspace", _change)
    ok = await app_client.patch(
        "/api/workspace/507f1f77bcf86cd799439012/wiring",
        content=json.dumps([]),
        headers={"content-type": "application/json-patch+json"},
    )
    assert ok.status_code == 204
    assert changed["n"] == 1

    ws = _workspace(editable=True, accessible=True)
    ws.wiring_status.operators = {"1": SimpleNamespace(name="acme/op/1.0.0")}
    monkeypatch.setattr(routes, "get_workspace_by_id", lambda *_args, **_kwargs: _value(ws))
    monkeypatch.setattr(routes, "get_catalogue_resource", lambda *_args, **_kwargs: _op_res())
    monkeypatch.setattr(routes, "check_wiring", lambda *_args, **_kwargs: _true())

    async def _op_res():
        return SimpleNamespace()

    op_patch_ok = await app_client.patch(
        "/api/workspace/507f1f77bcf86cd799439012/wiring",
        content=json.dumps([{"op": "replace", "path": "/operators/1/preferences/p1", "value": {"readonly": False, "hidden": False, "value": "x"}}]),
        headers={"content-type": "application/json-patch+json"},
    )
    assert op_patch_ok.status_code in (204, 400, 422)


async def test_operator_html_route(app_client, db_session, monkeypatch):
    async def _none(*_args, **_kwargs):
        return None

    monkeypatch.setattr(routes, "get_catalogue_resource", _none)
    missing = await app_client.get("/api/operator/acme/op/1.0.0/html")
    assert missing.status_code == 404

    operator = SimpleNamespace(
        id="opid",
        vendor="acme",
        short_name="op",
        version="1.0.0",
        template_uri="acme_op_1.0.0.wgt",
        description=SimpleNamespace(js_files=["js/main.js"], requirements=[]),
    )

    async def _resource(*_args, **_kwargs):
        return operator

    monkeypatch.setattr(routes, "get_catalogue_resource", _resource)

    cached = CacheableData(data="<xhtml/>", content_type="application/xhtml+xml; charset=utf-8", timeout=30)
    monkeypatch.setattr(routes.cache, "get", lambda *_args, **_kwargs: _cached())

    async def _cached():
        return cached

    hit = await app_client.get("/api/operator/acme/op/1.0.0/html")
    assert hit.status_code == 200

    async def _none_cache(*_args, **_kwargs):
        return None

    saved = {"n": 0}

    async def _set_cache(*_args, **_kwargs):
        saved["n"] += 1

    monkeypatch.setattr(routes.cache, "get", _none_cache)
    monkeypatch.setattr(routes.cache, "set", _set_cache)
    monkeypatch.setattr(routes, "get_absolute_reverse_url", lambda *_args, **_kwargs: "http://testserver/showcase")
    monkeypatch.setattr(routes, "generate_xhtml_operator_code", lambda *_args, **_kwargs: _xhtml())

    async def _xhtml():
        return "<xhtml/>"

    miss = await app_client.get("/api/operator/acme/op/1.0.0/html?mode=classic")
    assert miss.status_code == 200
    assert saved["n"] == 1


@pytest.mark.filterwarnings("ignore:Pydantic serializer warnings:UserWarning")
async def test_get_operator_variables_entry_route(app_client, db_session, monkeypatch):
    async def _none(*_args, **_kwargs):
        return None

    monkeypatch.setattr(routes, "get_workspace_by_id", _none)
    missing = await app_client.get("/api/workspace/507f1f77bcf86cd799439012/operators/1/variables")
    assert missing.status_code == 404

    ws = _workspace(editable=True, accessible=False)
    monkeypatch.setattr(routes, "get_workspace_by_id", lambda *_args, **_kwargs: _value(ws))

    async def _value(v):
        return v

    forbidden = await app_client.get("/api/workspace/507f1f77bcf86cd799439012/operators/1/variables")
    assert forbidden.status_code == 403

    ws = _workspace(editable=True, accessible=True)
    ws.wiring_status.operators = {}
    monkeypatch.setattr(routes, "get_workspace_by_id", lambda *_args, **_kwargs: _value(ws))
    missing_operator = await app_client.get("/api/workspace/507f1f77bcf86cd799439012/operators/1/variables")
    assert missing_operator.status_code == 404

    ws.wiring_status.operators = {"1": SimpleNamespace(name="invalid", preferences={}, properties={})}
    bad_operator_name = await app_client.get("/api/workspace/507f1f77bcf86cd799439012/operators/1/variables")
    assert bad_operator_name.status_code == 404

    ws.wiring_status.operators = {"1": SimpleNamespace(name="acme/op/1.0.0", preferences={}, properties={})}
    monkeypatch.setattr(routes, "get_catalogue_resource", _none)
    empty = await app_client.get("/api/workspace/507f1f77bcf86cd799439012/operators/1/variables")
    assert empty.status_code == 200
    assert empty.json() == {"preferences": {}, "properties": {}}

    async def _unavailable_resource(*_args, **_kwargs):
        return SimpleNamespace(is_available_for=lambda _user: False)

    monkeypatch.setattr(routes, "get_catalogue_resource", _unavailable_resource)
    monkeypatch.setattr(routes, "get_user_with_all_info", lambda *_args, **_kwargs: _creator())

    async def _creator():
        return SimpleNamespace(id=ws.creator)

    unavailable = await app_client.get("/api/workspace/507f1f77bcf86cd799439012/operators/1/variables")
    assert unavailable.status_code == 404

    ws.wiring_status.operators = {
        "1": SimpleNamespace(
            name="acme/op/1.0.0",
            preferences={"p1": SimpleNamespace(value="a")},
            properties={"k1": SimpleNamespace(value="b")},
        )
    }

    async def _resource(*_args, **_kwargs):
        return SimpleNamespace(is_available_for=lambda _user: True)

    class _CacheManager:
        async def get_variable_data(self, *_args, **_kwargs):
            return routes.CacheVariableData(name="x", secure=False, readonly=False, hidden=False, value="v")

    monkeypatch.setattr(routes, "get_catalogue_resource", _resource)
    monkeypatch.setattr(routes, "VariableValueCacheManager", lambda *_args, **_kwargs: _CacheManager())
    ok = await app_client.get("/api/workspace/507f1f77bcf86cd799439012/operators/1/variables")
    assert ok.status_code == 200
    assert "p1" in ok.json()["preferences"]
    assert "k1" in ok.json()["properties"]
