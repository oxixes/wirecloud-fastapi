# -*- coding: utf-8 -*-

from copy import deepcopy
from types import SimpleNamespace

import pytest

from wirecloud.platform.wiring import routes as _wiring_routes  # noqa: F401
from wirecloud.platform.wiring import schemas, utils
from wirecloud.platform.workspace.models import WorkspaceWiring, WorkspaceWiringOperator, DBWiringOperatorPreference, WiringOperatorPreferenceValue


@pytest.fixture(autouse=True)
def _patch_gettext(monkeypatch):
    monkeypatch.setattr(utils, "_", lambda text: text)


def _operator(op_id="1", name="acme/op/1.0.0", preferences=None, properties=None):
    return WorkspaceWiringOperator(
        id=op_id,
        name=name,
        preferences=preferences or {},
        properties=properties or {},
    )


def _pref(value, readonly=False, hidden=False):
    return DBWiringOperatorPreference(readonly=readonly, hidden=hidden, value=value)


def _wiring(connections=None, operators=None):
    wiring = WorkspaceWiring()
    wiring.connections = connections or []
    wiring.operators = operators or {}
    return wiring


def _connection(readonly=False, source_id="w1", target_id="1"):
    return schemas.WiringConnection(
        readonly=readonly,
        source=schemas.WiringConnectionEndpoint(type=schemas.WiringType.widget, id=source_id, endpoint="out"),
        target=schemas.WiringConnectionEndpoint(type=schemas.WiringType.operator, id=target_id, endpoint="in"),
    )


def test_basic_wiring_utils_helpers():
    status = utils.get_wiring_skeleton()
    status.connections.append(_connection(source_id="w1", target_id="1"))
    status.visualdescription.components.widget["w1"] = schemas.WiringComponent(name="acme/widget/1.0.0")
    status.visualdescription.connections.append(
        schemas.WiringVisualDescriptionConnection(sourcename="widget/w1/out", targetname="operator/1/in")
    )
    behaviour = utils.get_behaviour_skeleton()
    behaviour.components.widget["w1"] = schemas.WiringComponent(name="acme/widget/1.0.0")
    behaviour.connections.append(
        schemas.WiringVisualDescriptionConnection(sourcename="widget/w1/out", targetname="operator/1/in")
    )
    status.visualdescription.behaviours.append(behaviour)

    cleaned = utils.remove_widget_from_wiring_status("w1", status)
    assert cleaned.connections == []
    assert cleaned.visualdescription.connections == []
    assert "w1" not in cleaned.visualdescription.components.widget
    assert cleaned.visualdescription.behaviours[0].connections == []

    endpoint = schemas.WiringConnectionEndpoint(type=schemas.WiringType.widget, id="w1", endpoint="out")
    assert utils.get_endpoint_name(endpoint) == "WiringType.widget/w1/out"
    assert utils.rename_component_type("widget") == schemas.WiringType.widget
    assert utils.rename_component_type("operator") == schemas.WiringType.operator
    with pytest.raises(ValueError, match="Invalid component type"):
        utils.rename_component_type("bad")

    skeleton = utils.get_wiring_skeleton()
    assert skeleton.version == "2.0"
    assert utils.is_empty_wiring(skeleton.visualdescription) is True
    skeleton.visualdescription.components.widget["w1"] = schemas.WiringComponent()
    assert utils.is_empty_wiring(skeleton.visualdescription) is False

    operator = SimpleNamespace(id="opid")
    assert utils.get_operator_cache_key(operator, "example.org", "classic") == "_operator_xhtml/1/example.org/opid?mode=classic"

    assert utils.check_same_wiring({"a": {"b": 1}, "value": 2}, {"a": {"b": 1}, "value": 3}) is True
    assert utils.check_same_wiring({"a": 1}, {"a": 2}) is False

    reqs = [SimpleNamespace(name="r1"), SimpleNamespace(name="r2")]
    assert utils.process_requirements(reqs) == ["r1", "r2"]


async def test_operator_api_files_and_generate_xhtml(monkeypatch):
    request = SimpleNamespace()

    monkeypatch.setattr(utils, "get_current_domain", lambda _request: "example.org")
    monkeypatch.setattr("wirecloud.platform.core.plugins.get_version_hash", lambda: "v1")

    async def _none(*_args, **_kwargs):
        return None

    saved = {"n": 0}

    async def _set(*_args, **_kwargs):
        saved["n"] += 1

    monkeypatch.setattr(utils.cache, "get", _none)
    monkeypatch.setattr(utils.cache, "set", _set)
    monkeypatch.setattr(utils, "get_absolute_static_url", lambda path, **_kwargs: f"http://static/{path}")
    monkeypatch.setattr(utils.settings, "DEBUG", False)

    files = await utils.get_operator_api_files(request, "defaulttheme")
    assert len(files) == 1
    assert saved["n"] == 1

    async def _hit(*_args, **_kwargs):
        return ("http://static/a.js",)

    monkeypatch.setattr(utils.cache, "get", _hit)
    files_hit = await utils.get_operator_api_files(request, "defaulttheme")
    assert files_hit == ["http://static/a.js"]

    monkeypatch.setattr(utils.settings, "DEBUG", True)
    files_debug = await utils.get_operator_api_files(request, "defaulttheme")
    assert len(files_debug) == 1

    monkeypatch.setattr("wirecloud.platform.plugins.get_operator_api_extensions", lambda _mode, _reqs: ["static/js/ext.js"])
    monkeypatch.setattr("wirecloud.platform.routes.get_current_theme", lambda _request: "defaulttheme")
    monkeypatch.setattr(utils, "get_operator_api_files", lambda *_args, **_kwargs: _api())

    async def _api():
        return ["http://static/main.js"]

    class _TemplateResponse:
        def __init__(self, _name, context):
            self.body = (";".join(context["js_files"])).encode("utf-8")

    monkeypatch.setattr("wirecloud.commons.templates.tags.templates.TemplateResponse", _TemplateResponse)
    xhtml = await utils.generate_xhtml_operator_code(["http://custom/op.js"], "http://base", request, ["req"], "classic")
    assert "http://static/main.js" in xhtml
    assert "http://custom/op.js" in xhtml


def test_handle_multiuser(monkeypatch):
    user = SimpleNamespace(id="u1")
    old = _pref(value=WiringOperatorPreferenceValue(users={"owner": "x"}), readonly=False, hidden=False)
    new = _pref(value="v1", readonly=False, hidden=False)

    monkeypatch.setattr("wirecloud.platform.workspace.utils.encrypt_value", lambda value: f"enc:{value}")
    secure = utils.handle_multiuser(user, True, new, old)
    assert secure.value.users["u1"] == "enc:v1"

    non_secure = utils.handle_multiuser(user, False, new, old)
    assert non_secure.value.users["u1"] == "v1"

    old_plain = _pref(value="plain", readonly=False, hidden=False)
    wrapped = utils.handle_multiuser(user, False, new, old_plain)
    assert wrapped.value.users["u1"] == "v1"


def test_check_same_wiring_additional_branches():
    assert utils.check_same_wiring({"a": 1}, {"a": 1, "b": 2}) is False
    assert utils.check_same_wiring({"a": {"b": 1}}, {"a": {"b": 2}}) is False


async def test_check_multiuser_wiring_paths(monkeypatch):
    request = SimpleNamespace(headers={"Accept": "*/*"})
    user = SimpleNamespace(id="u1", is_superuser=False)
    workspace = SimpleNamespace(creator="owner")

    old = _wiring()
    new = _wiring()

    monkeypatch.setattr(utils, "check_same_wiring", lambda *_args, **_kwargs: False)
    denied = await utils.check_multiuser_wiring(None, request, user, new, old, workspace, adding=False)
    assert denied.status_code == 403

    monkeypatch.setattr(utils, "check_same_wiring", lambda *_args, **_kwargs: True)
    old_op = _operator(
        preferences={"p1": _pref(WiringOperatorPreferenceValue(users={"owner": "a"}))},
        properties={"k1": _pref(WiringOperatorPreferenceValue(users={"owner": "b"}))},
    )
    new_op = deepcopy(old_op)
    old = _wiring(operators={"1": old_op})
    new = _wiring(operators={"1": new_op})

    async def _none_resource(*_args, **_kwargs):
        return None

    monkeypatch.setattr("wirecloud.catalogue.crud.get_catalogue_resource", _none_resource)
    result = await utils.check_multiuser_wiring(None, request, user, new, old, workspace, adding=False)
    assert result is True
    assert new.operators["1"].preferences == old.operators["1"].preferences

    async def _resource(*_args, **_kwargs):
        info = SimpleNamespace(
            variables=SimpleNamespace(
                preferences={"p1": SimpleNamespace(secure=False)},
                properties={"k1": SimpleNamespace(secure=False, multiuser=False)},
            )
        )
        return SimpleNamespace(get_processed_info=lambda **_kwargs: info)

    monkeypatch.setattr("wirecloud.catalogue.crud.get_catalogue_resource", _resource)
    monkeypatch.setattr("wirecloud.platform.workspace.utils.is_owner_or_has_permission", lambda *_args, **_kwargs: False)
    denied_prefs = await utils.check_multiuser_wiring(None, request, user, deepcopy(new), old, workspace, adding=False)
    assert denied_prefs.status_code == 403

    monkeypatch.setattr("wirecloud.platform.workspace.utils.is_owner_or_has_permission", lambda *_args, **_kwargs: True)
    changed_new = deepcopy(new)
    changed_new.operators["1"].preferences["p1"].value = "changed"
    denied_change = await utils.check_multiuser_wiring(None, request, user, changed_new, old, workspace, adding=False)
    assert denied_change.status_code == 403

    old_sec = _operator(properties={"k1": _pref(WiringOperatorPreferenceValue(users={"owner": "b"}), readonly=False)})
    new_sec = deepcopy(old_sec)
    old_w = _wiring(operators={"1": old_sec})
    new_w = _wiring(operators={"1": new_sec})

    async def _resource_secure(*_args, **_kwargs):
        info = SimpleNamespace(
            variables=SimpleNamespace(
                preferences={},
                properties={"k1": SimpleNamespace(secure=True, multiuser=True)},
            )
        )
        return SimpleNamespace(get_processed_info=lambda **_kwargs: info)

    monkeypatch.setattr("wirecloud.catalogue.crud.get_catalogue_resource", _resource_secure)
    ok = await utils.check_multiuser_wiring(None, request, user, new_w, old_w, workspace, adding=True, can_update_secure=False)
    assert ok is True

    old_pref = _operator(preferences={"px": _pref(WiringOperatorPreferenceValue(users={"owner": "v"}))})
    new_pref = deepcopy(old_pref)
    old_wp = _wiring(operators={"1": old_pref})
    new_wp = _wiring(operators={"1": new_pref})

    async def _resource_pref_missing(*_args, **_kwargs):
        info = SimpleNamespace(variables=SimpleNamespace(preferences={}, properties={}))
        return SimpleNamespace(get_processed_info=lambda **_kwargs: info)

    monkeypatch.setattr("wirecloud.catalogue.crud.get_catalogue_resource", _resource_pref_missing)
    monkeypatch.setattr("wirecloud.platform.workspace.utils.is_owner_or_has_permission", lambda *_args, **_kwargs: True)
    ok_pref_missing = await utils.check_multiuser_wiring(None, request, user, new_wp, old_wp, workspace, adding=True)
    assert ok_pref_missing is True

    old_prop_perm = _operator(properties={"k1": _pref(WiringOperatorPreferenceValue(users={"owner": "b"}))})
    new_prop_perm = deepcopy(old_prop_perm)
    monkeypatch.setattr("wirecloud.platform.workspace.utils.is_owner_or_has_permission", lambda *_args, **_kwargs: False)
    denied_props = await utils.check_multiuser_wiring(
        None,
        request,
        user,
        _wiring(operators={"1": new_prop_perm}),
        _wiring(operators={"1": old_prop_perm}),
        workspace,
        adding=False,
    )
    assert denied_props.status_code == 403

    monkeypatch.setattr("wirecloud.platform.workspace.utils.is_owner_or_has_permission", lambda *_args, **_kwargs: True)
    old_prop = _operator(properties={"k1": _pref(WiringOperatorPreferenceValue(users={"owner": "b"}), readonly=False)})
    new_prop = deepcopy(old_prop)
    new_prop.properties["k1"].readonly = True
    new_prop.properties["k1"].value = "changed"
    denied_readonly = await utils.check_multiuser_wiring(
        None,
        request,
        user,
        _wiring(operators={"1": new_prop}),
        _wiring(operators={"1": old_prop}),
        workspace,
        adding=True,
    )
    assert denied_readonly.status_code == 403

    old_non_multi = _operator(properties={"k1": _pref(WiringOperatorPreferenceValue(users={"owner": "b"}), readonly=False)})
    new_non_multi = deepcopy(old_non_multi)
    new_non_multi.properties["k1"].value = "changed"

    async def _resource_non_multi(*_args, **_kwargs):
        info = SimpleNamespace(
            variables=SimpleNamespace(preferences={}, properties={"k1": SimpleNamespace(secure=False, multiuser=False)})
        )
        return SimpleNamespace(get_processed_info=lambda **_kwargs: info)

    monkeypatch.setattr("wirecloud.catalogue.crud.get_catalogue_resource", _resource_non_multi)
    denied_non_multi = await utils.check_multiuser_wiring(
        None,
        request,
        user,
        _wiring(operators={"1": new_non_multi}),
        _wiring(operators={"1": old_non_multi}),
        workspace,
        adding=True,
    )
    assert denied_non_multi.status_code == 403

    old_multi = _operator(properties={"k1": _pref(WiringOperatorPreferenceValue(users={"owner": "b"}), readonly=False)})
    new_multi = deepcopy(old_multi)
    new_multi.properties["k1"].value = WiringOperatorPreferenceValue(users={"u1": "new-v"})

    async def _resource_multi(*_args, **_kwargs):
        info = SimpleNamespace(
            variables=SimpleNamespace(preferences={}, properties={"k1": SimpleNamespace(secure=False, multiuser=True)})
        )
        return SimpleNamespace(get_processed_info=lambda **_kwargs: info)

    monkeypatch.setattr("wirecloud.catalogue.crud.get_catalogue_resource", _resource_multi)
    monkeypatch.setattr(utils, "handle_multiuser", lambda *_args, **_kwargs: _pref(WiringOperatorPreferenceValue(users={"u1": "handled"})))
    ok_multi = await utils.check_multiuser_wiring(
        None,
        request,
        user,
        _wiring(operators={"1": new_multi}),
        _wiring(operators={"1": old_multi}),
        workspace,
        adding=True,
    )
    assert ok_multi is True

    new_multi_missing = deepcopy(old_multi)
    new_multi_missing.properties["k1"].value = WiringOperatorPreferenceValue(users={})
    ok_multi_missing = await utils.check_multiuser_wiring(
        None,
        request,
        user,
        _wiring(operators={"1": new_multi_missing}),
        _wiring(operators={"1": old_multi}),
        workspace,
        adding=True,
    )
    assert ok_multi_missing is True

    new_multi_attr_err = deepcopy(old_multi)
    new_multi_attr_err.properties["k1"].value = "plain"
    ok_multi_attr = await utils.check_multiuser_wiring(
        None,
        request,
        user,
        _wiring(operators={"1": new_multi_attr_err}),
        _wiring(operators={"1": old_multi}),
        workspace,
        adding=True,
    )
    assert ok_multi_attr is True


async def test_check_wiring_paths(monkeypatch):
    request = SimpleNamespace(headers={"Accept": "*/*"})
    user = SimpleNamespace(id="u1", is_superuser=False)
    workspace = SimpleNamespace(creator="owner")

    old = _wiring(connections=[_connection(readonly=True)])
    new = _wiring(connections=[])
    denied_ro_conn = await utils.check_wiring(None, request, user, new, old, workspace, adding=False)
    assert denied_ro_conn.status_code == 403

    old = _wiring(connections=[_connection(readonly=True)])
    new = _wiring(connections=[_connection(readonly=True, source_id="other")])
    denied_ro_conn_mismatch = await utils.check_wiring(None, request, user, new, old, workspace, adding=False)
    assert denied_ro_conn_mismatch.status_code == 403

    old = _wiring(connections=[_connection(readonly=True)])
    new = _wiring(connections=[_connection(readonly=True), _connection(readonly=False)])

    old_op = _operator(
        preferences={"p1": _pref(WiringOperatorPreferenceValue(users={"owner": "a"}), readonly=True)},
        properties={"k1": _pref(WiringOperatorPreferenceValue(users={"owner": "b"}), readonly=True)},
    )
    new_op = deepcopy(old_op)
    new_op.preferences["p2"] = _pref("new", readonly=True)
    new_op.properties["k2"] = _pref("new", readonly=True)

    old.operators = {"1": old_op}
    new.operators = {"1": new_op}

    async def _resource(*_args, **_kwargs):
        info = SimpleNamespace(
            variables=SimpleNamespace(
                preferences={"p1": SimpleNamespace(secure=False), "p2": SimpleNamespace(secure=False)},
                properties={"k1": SimpleNamespace(secure=False), "k2": SimpleNamespace(secure=False)},
            )
        )
        return SimpleNamespace(get_processed_info=lambda **_kwargs: info)

    monkeypatch.setattr("wirecloud.catalogue.crud.get_catalogue_resource", _resource)
    monkeypatch.setattr("wirecloud.platform.workspace.utils.is_owner_or_has_permission", lambda *_args, **_kwargs: True)
    denied_add_ro_pref = await utils.check_wiring(None, request, user, new, old, workspace, adding=True)
    assert denied_add_ro_pref.status_code == 403

    new_op = deepcopy(old_op)
    old2 = _wiring(operators={"1": old_op})
    new2 = _wiring(operators={"1": new_op})
    new2.operators["1"].preferences["p1"].value = "changed"
    denied_update_ro_pref = await utils.check_wiring(None, request, user, new2, old2, workspace, adding=False)
    assert denied_update_ro_pref.status_code == 403

    old3 = _wiring(operators={"1": _operator(preferences={"p1": _pref(WiringOperatorPreferenceValue(users={"owner": "a"}))})})
    new3 = deepcopy(old3)
    new3.operators["1"].preferences["p1"].value = "new-value"
    ok = await utils.check_wiring(None, request, user, new3, old3, workspace, adding=False, can_update_secure=True)
    assert ok is True

    async def _missing_resource(*_args, **_kwargs):
        return None

    old4 = _wiring(operators={"1": _operator(preferences={"p1": _pref("a")}, properties={"k1": _pref("b")})})
    new4 = deepcopy(old4)
    monkeypatch.setattr("wirecloud.catalogue.crud.get_catalogue_resource", _missing_resource)
    res = await utils.check_wiring(None, request, user, new4, old4, workspace, adding=False)
    assert res is True

    old_perm = _wiring(operators={"1": _operator(preferences={"p1": _pref("a")})})
    new_perm = deepcopy(old_perm)
    new_perm.operators["1"].preferences["p1"].value = "b"
    monkeypatch.setattr("wirecloud.catalogue.crud.get_catalogue_resource", _resource)
    monkeypatch.setattr("wirecloud.platform.workspace.utils.is_owner_or_has_permission", lambda *_args, **_kwargs: False)
    denied_perm = await utils.check_wiring(None, request, user, new_perm, old_perm, workspace, adding=False)
    assert denied_perm.status_code == 403

    monkeypatch.setattr("wirecloud.platform.workspace.utils.is_owner_or_has_permission", lambda *_args, **_kwargs: True)
    old_removed = _wiring(operators={"1": _operator(preferences={"p1": _pref("a", readonly=True)})})
    new_removed = _wiring(operators={"1": _operator(preferences={})})
    denied_remove_ro_pref = await utils.check_wiring(None, request, user, new_removed, old_removed, workspace, adding=True)
    assert denied_remove_ro_pref.status_code == 403

    old_status_change = _wiring(operators={"1": _operator(preferences={"p1": _pref(WiringOperatorPreferenceValue(users={"owner": "a"}), readonly=False)})})
    new_status_change = deepcopy(old_status_change)
    new_status_change.operators["1"].preferences["p1"].hidden = True
    denied_status_change = await utils.check_wiring(None, request, user, new_status_change, old_status_change, workspace, adding=True)
    assert denied_status_change.status_code == 403

    old_secure_pref = _wiring(operators={"1": _operator(preferences={"p1": _pref(WiringOperatorPreferenceValue(users={"owner": "a"}), readonly=False)})})
    new_secure_pref = deepcopy(old_secure_pref)
    new_secure_pref.operators["1"].preferences["p1"].value = "new"

    async def _resource_secure_pref(*_args, **_kwargs):
        info = SimpleNamespace(variables=SimpleNamespace(preferences={"p1": SimpleNamespace(secure=True)}, properties={}))
        return SimpleNamespace(get_processed_info=lambda **_kwargs: info)

    monkeypatch.setattr("wirecloud.catalogue.crud.get_catalogue_resource", _resource_secure_pref)
    ok_secure_pref = await utils.check_wiring(None, request, user, new_secure_pref, old_secure_pref, workspace, adding=True, can_update_secure=False)
    assert ok_secure_pref is True

    old_prop_perm = _wiring(operators={"1": _operator(properties={"k1": _pref("a")})})
    new_prop_perm = deepcopy(old_prop_perm)
    new_prop_perm.operators["1"].properties["k1"].value = "b"
    monkeypatch.setattr("wirecloud.platform.workspace.utils.is_owner_or_has_permission", lambda *_args, **_kwargs: False)
    denied_prop_perm = await utils.check_wiring(None, request, user, new_prop_perm, old_prop_perm, workspace, adding=False)
    assert denied_prop_perm.status_code == 403

    monkeypatch.setattr("wirecloud.platform.workspace.utils.is_owner_or_has_permission", lambda *_args, **_kwargs: True)
    old_add_prop = _wiring(operators={"1": _operator(properties={})})
    new_add_prop = _wiring(operators={"1": _operator(properties={"k1": _pref("x", readonly=True)})})
    denied_add_ro_prop = await utils.check_wiring(None, request, user, new_add_prop, old_add_prop, workspace, adding=True)
    assert denied_add_ro_prop.status_code == 403

    old_add_prop_ok = _wiring(operators={"1": _operator(properties={})})
    new_add_prop_ok = _wiring(operators={"1": _operator(properties={"k1": _pref("x", readonly=False)})})
    ok_add_prop = await utils.check_wiring(None, request, user, new_add_prop_ok, old_add_prop_ok, workspace, adding=True)
    assert ok_add_prop is True

    old_remove_prop = _wiring(operators={"1": _operator(properties={"k1": _pref("x", readonly=True)})})
    new_remove_prop = _wiring(operators={"1": _operator(properties={})})
    denied_remove_ro_prop = await utils.check_wiring(None, request, user, new_remove_prop, old_remove_prop, workspace, adding=True)
    assert denied_remove_ro_prop.status_code == 403

    old_update_prop = _wiring(operators={"1": _operator(properties={"k1": _pref(WiringOperatorPreferenceValue(users={"owner": "a"}), readonly=False)})})
    new_update_prop = deepcopy(old_update_prop)
    new_update_prop.operators["1"].properties["k1"].hidden = True
    denied_update_prop_status = await utils.check_wiring(None, request, user, new_update_prop, old_update_prop, workspace, adding=True)
    assert denied_update_prop_status.status_code == 403

    old_update_prop_ro = _wiring(operators={"1": _operator(properties={"k1": _pref("a", readonly=True)})})
    new_update_prop_ro = deepcopy(old_update_prop_ro)
    new_update_prop_ro.operators["1"].properties["k1"].value = "b"
    denied_update_prop_ro = await utils.check_wiring(None, request, user, new_update_prop_ro, old_update_prop_ro, workspace, adding=True)
    assert denied_update_prop_ro.status_code == 403

    old_secure_prop = _wiring(operators={"1": _operator(properties={"k1": _pref(WiringOperatorPreferenceValue(users={"owner": "a"}), readonly=False)})})
    new_secure_prop = deepcopy(old_secure_prop)
    new_secure_prop.operators["1"].properties["k1"].value = "new"

    async def _resource_secure_prop(*_args, **_kwargs):
        info = SimpleNamespace(variables=SimpleNamespace(preferences={}, properties={"k1": SimpleNamespace(secure=True)}))
        return SimpleNamespace(get_processed_info=lambda **_kwargs: info)

    monkeypatch.setattr("wirecloud.catalogue.crud.get_catalogue_resource", _resource_secure_prop)
    ok_secure_prop = await utils.check_wiring(None, request, user, new_secure_prop, old_secure_prop, workspace, adding=True, can_update_secure=False)
    assert ok_secure_prop is True

    old_new_operator = _wiring(operators={})
    new_new_operator = _wiring(operators={"2": _operator(op_id="2", preferences={"p1": _pref("x")}, properties={"k1": _pref("y")})})

    async def _resource_with_keyerror(*_args, **_kwargs):
        info = SimpleNamespace(variables=SimpleNamespace(preferences={}, properties={}))
        return SimpleNamespace(get_processed_info=lambda **_kwargs: info)

    monkeypatch.setattr("wirecloud.catalogue.crud.get_catalogue_resource", _resource_with_keyerror)
    ok_new_operator = await utils.check_wiring(None, request, user, new_new_operator, old_new_operator, workspace, adding=True)
    assert ok_new_operator is True


async def test_wiring_utils_remaining_branches(monkeypatch):
    request = SimpleNamespace(headers={"Accept": "*/*"})
    user = SimpleNamespace(id="u1")
    workspace = SimpleNamespace(creator="owner")

    old_m = _wiring(
        operators={
            "1": _operator(
                preferences={"p1": _pref(WiringOperatorPreferenceValue(users={"owner": "a"}))},
                properties={"k1": _pref(WiringOperatorPreferenceValue(users={"owner": "b"}), readonly=False)},
            )
        }
    )
    new_m = deepcopy(old_m)

    async def _resource_multi_pref_secure(*_args, **_kwargs):
        info = SimpleNamespace(
            variables=SimpleNamespace(
                preferences={"p1": SimpleNamespace(secure=True)},
                properties={"k1": SimpleNamespace(secure=False, multiuser=False)},
            )
        )
        return SimpleNamespace(get_processed_info=lambda **_kwargs: info)

    monkeypatch.setattr("wirecloud.catalogue.crud.get_catalogue_resource", _resource_multi_pref_secure)
    monkeypatch.setattr("wirecloud.platform.workspace.utils.is_owner_or_has_permission", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(utils, "check_same_wiring", lambda *_args, **_kwargs: True)
    ok_m = await utils.check_multiuser_wiring(None, request, user, new_m, old_m, workspace, adding=True, can_update_secure=False)
    assert ok_m is True

    old_multi_none = _wiring(
        operators={
            "1": _operator(
                properties={"k1": _pref(WiringOperatorPreferenceValue(users={"owner": "b"}), readonly=False)}
            )
        }
    )
    new_multi_none = deepcopy(old_multi_none)
    new_multi_none.operators["1"].properties["k1"].value = SimpleNamespace(users=None)

    async def _resource_property_multi(*_args, **_kwargs):
        info = SimpleNamespace(
            variables=SimpleNamespace(
                preferences={},
                properties={"k1": SimpleNamespace(secure=False, multiuser=True)},
            )
        )
        return SimpleNamespace(get_processed_info=lambda **_kwargs: info)

    monkeypatch.setattr("wirecloud.catalogue.crud.get_catalogue_resource", _resource_property_multi)
    monkeypatch.setattr(utils, "handle_multiuser", lambda *_args, **_kwargs: _pref(WiringOperatorPreferenceValue(users={"u1": "v"})))
    ok_multi_none = await utils.check_multiuser_wiring(
        None, request, user, new_multi_none, old_multi_none, workspace, adding=True
    )
    assert ok_multi_none is True

    old_w = _wiring(
        operators={
            "1": _operator(
                preferences={
                    "same": _pref(WiringOperatorPreferenceValue(users={"owner": "x"})),
                    "upd": _pref(WiringOperatorPreferenceValue(users={"owner": "x"})),
                    "remove": _pref("old-remove", readonly=False),
                },
                properties={
                    "samek": _pref(WiringOperatorPreferenceValue(users={"owner": "y"})),
                    "updk": _pref(WiringOperatorPreferenceValue(users={"owner": "y"})),
                    "removek": _pref("old-remove-k", readonly=False),
                },
            )
        }
    )
    new_w = _wiring(
        operators={
            "1": _operator(
                preferences={
                    "same": _pref(WiringOperatorPreferenceValue(users={"owner": "x"})),
                    "upd": _pref("new-upd", readonly=False),
                    "added_secure": _pref("sec"),
                },
                properties={
                    "samek": _pref(WiringOperatorPreferenceValue(users={"owner": "y"})),
                    "updk": _pref("new-updk", readonly=False),
                    "addedk": _pref("new-k", readonly=False),
                },
            )
        }
    )

    async def _resource_for_wiring(*_args, **_kwargs):
        info = SimpleNamespace(
            variables=SimpleNamespace(
                preferences={"added_secure": SimpleNamespace(secure=True)},
                properties={},
            )
        )
        return SimpleNamespace(get_processed_info=lambda **_kwargs: info)

    monkeypatch.setattr("wirecloud.catalogue.crud.get_catalogue_resource", _resource_for_wiring)
    monkeypatch.setattr("wirecloud.platform.workspace.utils.is_owner_or_has_permission", lambda *_args, **_kwargs: True)
    monkeypatch.setattr("wirecloud.platform.workspace.utils.encrypt_value", lambda v: f"enc:{v}")
    monkeypatch.setattr(utils, "handle_multiuser", lambda *_args, **_kwargs: _pref(WiringOperatorPreferenceValue(users={"u1": "handled"})))
    ok_w = await utils.check_wiring(None, request, user, new_w, old_w, workspace, adding=True, can_update_secure=True)
    assert ok_w is True
    assert new_w.operators["1"].preferences["added_secure"].value.users["u1"] == "enc:sec"
