# -*- coding: utf-8 -*-

from types import SimpleNamespace

import pytest
from starlette.requests import Request

from wirecloud.commons.utils.http import NotFound
from wirecloud.commons.utils.template.schemas.macdschemas import MACDPreference, MACDProperty
from wirecloud.platform.iwidget import utils
from wirecloud.platform.iwidget.models import (
    WidgetConfig,
    WidgetConfigAnchor,
    WidgetInstance,
    WidgetPermissions,
    WidgetPermissionsConfig,
    WidgetPositions,
    WidgetPositionsConfig,
    WidgetVariables,
)
from wirecloud.platform.iwidget.schemas import LayoutConfig, WidgetInstanceDataCreate, WidgetInstanceDataUpdate


@pytest.fixture(autouse=True)
def _patch_gettext(monkeypatch):
    monkeypatch.setattr(utils, "_", lambda text: text)


def _request():
    req = Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": "GET",
            "scheme": "https",
            "server": ("wirecloud.example.org", 443),
            "path": "/api",
            "query_string": b"",
            "headers": [(b"host", b"wirecloud.example.org")],
        }
    )
    req.state.lang = "en"
    return req


def test_parse_and_initial_value_helpers():
    assert utils.parse_value_from_text({"type": "boolean"}, "true") is True
    assert utils.parse_value_from_text({"type": "number"}, "3.2") == 3.2
    assert utils.parse_value_from_text({"type": "number", "default": "4"}, "x") == 4.0
    assert utils.parse_value_from_text({"type": "number"}, "x") == 0
    assert utils.parse_value_from_text({"type": "text"}, 5) == "5"

    pref = MACDPreference(
        name="p1",
        type="text",
        label="P1",
        description="",
        default="d",
        readonly=False,
        required=False,
        secure=False,
        multiuser=False,
    )
    prop = MACDProperty(name="prop", type="number", label="P", description="", default="2", secure=False, multiuser=False)

    assert utils.process_initial_value(pref, "x") == "x"
    pref.readonly = True
    pref.value = "y"
    assert utils.process_initial_value(pref, "x") == "y"
    pref.value = None
    assert utils.process_initial_value(pref, None) == "d"
    pref.default = None
    assert utils.process_initial_value(pref, None) == ""
    assert utils.process_initial_value(prop, None) == 2.0


async def test_update_widget_value_and_title(monkeypatch, db_session):
    iwidget = WidgetInstance(id="ws-0-0")
    user = SimpleNamespace(id="u1")
    data = WidgetInstanceDataUpdate(widget="acme/widget/1.0.0")

    resource = SimpleNamespace(
        id="rid",
        is_available_for=lambda _user: True,
        resource_type=lambda: "widget",
        get_processed_info=lambda **_kwargs: SimpleNamespace(title="Widget title"),
    )

    monkeypatch.setattr(utils, "get_catalogue_resource", lambda *_args, **_kwargs: _resource(resource))

    async def _resource(value):
        return value

    result = await utils.update_widget_value(db_session, iwidget, data, user)
    assert result.id == "rid"
    assert iwidget.resource == "rid"

    missing = WidgetInstanceDataUpdate(widget="acme/missing/1.0.0")
    monkeypatch.setattr(utils, "get_catalogue_resource", lambda *_args, **_kwargs: _none())

    async def _none():
        return None

    with pytest.raises(ValueError):
        await utils.update_widget_value(db_session, iwidget, missing, user)

    resource_unavailable = SimpleNamespace(id="rid", is_available_for=lambda _user: False, resource_type=lambda: "widget")
    monkeypatch.setattr(utils, "get_catalogue_resource", lambda *_args, **_kwargs: _resource(resource_unavailable))
    with pytest.raises(NotFound):
        await utils.update_widget_value(db_session, iwidget, data, user)

    resource_operator = SimpleNamespace(id="rid", is_available_for=lambda _user: True, resource_type=lambda: "operator")
    monkeypatch.setattr(utils, "get_catalogue_resource", lambda *_args, **_kwargs: _resource(resource_operator))
    with pytest.raises(ValueError):
        await utils.update_widget_value(db_session, iwidget, data, user)

    with pytest.raises(ValueError):
        await utils.update_widget_value(db_session, iwidget, WidgetInstanceDataUpdate(widget=None), user, required=True)

    none_value = await utils.update_widget_value(db_session, iwidget, WidgetInstanceDataUpdate(widget=None), user, required=False)
    assert none_value is None

    iwidget.resource = "rid"
    monkeypatch.setattr(utils, "get_catalogue_resource_by_id", lambda *_args, **_kwargs: _resource(resource))
    await utils.update_title_value(db_session, iwidget, WidgetInstanceDataUpdate(title=""))
    assert iwidget.title == "Widget title"
    await utils.update_title_value(db_session, iwidget, WidgetInstanceDataUpdate(title="Custom"))
    assert iwidget.title == "Custom"
    await utils.update_title_value(db_session, iwidget, WidgetInstanceDataUpdate(title=None))
    assert iwidget.title == "Custom"


def test_field_update_helpers():
    model = WidgetPositionsConfig(id=0, moreOrEqual=0, lessOrEqual=-1)
    data = LayoutConfig(id=0, moreOrEqual=10, lessOrEqual=20)
    utils.update_screen_size_value(model, data, "moreOrEqual")
    assert model.moreOrEqual == 10
    utils.update_screen_size_value(model, LayoutConfig(id=0), "moreOrEqual")
    assert model.moreOrEqual == 10
    with pytest.raises(TypeError):
        utils.update_screen_size_value(model, SimpleNamespace(moreOrEqual="x"), "moreOrEqual")
    with pytest.raises(ValueError):
        utils.update_screen_size_value(model, SimpleNamespace(moreOrEqual=-2), "moreOrEqual")

    widget_cfg = WidgetConfig()
    utils.update_position_value(widget_cfg, LayoutConfig(id=0), "top")
    assert widget_cfg.top is None
    utils.update_position_value(widget_cfg, LayoutConfig(id=0, top=3), "top")
    assert widget_cfg.top == 3
    utils.update_position_value(widget_cfg, LayoutConfig(id=0, top=5), "left", "top")
    assert widget_cfg.left == 5
    with pytest.raises(TypeError):
        utils.update_position_value(widget_cfg, SimpleNamespace(top="x"), "top")
    with pytest.raises(ValueError):
        utils.update_position_value(widget_cfg, SimpleNamespace(top=-1), "top")

    utils.update_size_value(widget_cfg, LayoutConfig(id=0), "width")
    assert widget_cfg.width is None
    utils.update_size_value(widget_cfg, LayoutConfig(id=0, width=5), "width")
    assert widget_cfg.width == 5
    with pytest.raises(TypeError):
        utils.update_size_value(widget_cfg, SimpleNamespace(width="x"), "width")
    with pytest.raises(ValueError):
        utils.update_size_value(widget_cfg, SimpleNamespace(width=0), "width")

    perms = WidgetPermissionsConfig()
    utils.update_boolean_value(perms, WidgetInstanceDataUpdate(), "move")
    assert perms.move is None
    utils.update_boolean_value(perms, WidgetInstanceDataUpdate(move=True), "move")
    assert perms.move is True
    with pytest.raises(TypeError):
        utils.update_boolean_value(perms, SimpleNamespace(move="x"), "move")

    utils.update_anchor_value(widget_cfg, LayoutConfig(id=0))
    assert widget_cfg.anchor is None
    utils.update_anchor_value(widget_cfg, LayoutConfig(id=0, anchor=WidgetConfigAnchor.bottom_left))
    assert widget_cfg.anchor == "bottom-left"

    iwidget = WidgetInstance(id="x", permissions=WidgetPermissions(viewer=WidgetPermissionsConfig()))
    utils.update_permissions(iwidget, WidgetInstanceDataUpdate())
    assert iwidget.permissions.viewer.move is None
    utils.update_permissions(iwidget, WidgetInstanceDataUpdate(move=True))
    assert iwidget.permissions.viewer.move is True


async def test_set_initial_values(monkeypatch, db_session):
    calls = []
    class _FakeWidget:
        async def set_variable_value(self, _db, name, value, _user):
            calls.append((name, value))

    iwidget = _FakeWidget()
    info = SimpleNamespace(
        preferences=[MACDPreference(name="p", type="text", label="P", description="", default="d", readonly=False, required=False, secure=False, multiuser=False)],
        properties=[MACDProperty(name="n", type="number", label="N", description="", default="1", secure=False, multiuser=False)],
    )
    await utils.set_initial_values(
        db_session,
        iwidget,
        {"p": "x"},
        info,
        SimpleNamespace(id="u1"),
    )
    assert ("p", "x") in calls
    assert ("n", 1.0) in calls


def test_intervals_and_positions():
    with pytest.raises(ValueError):
        utils.check_intervals([WidgetPositionsConfig(id=1, moreOrEqual=1, lessOrEqual=-1)])
    with pytest.raises(ValueError):
        utils.check_intervals(
            [
                WidgetPositionsConfig(id=0, moreOrEqual=0, lessOrEqual=1),
                WidgetPositionsConfig(id=1, moreOrEqual=3, lessOrEqual=-1),
            ]
        )
    with pytest.raises(ValueError):
        utils.check_intervals(
            [
                WidgetPositionsConfig(id=0, moreOrEqual=0, lessOrEqual=1),
                WidgetPositionsConfig(id=1, moreOrEqual=2, lessOrEqual=4),
            ]
        )

    iwidget = WidgetInstance(id="w1", positions=WidgetPositions(configurations=[WidgetPositionsConfig(id=0, moreOrEqual=0, lessOrEqual=-1)]))
    with pytest.raises(ValueError):
        utils.update_position(iwidget, "widget", WidgetInstanceDataUpdate(layoutConfig=[LayoutConfig(id=0), LayoutConfig(id=0)]))
    with pytest.raises(ValueError):
        utils.update_position(iwidget, "widget", WidgetInstanceDataUpdate(layoutConfig=[LayoutConfig(id=0, action="invalid")]))

    utils.update_position(
        iwidget,
        "widget",
        WidgetInstanceDataUpdate(
            layoutConfig=[
                LayoutConfig(id=0, action="delete"),
                LayoutConfig(id=1, action="update", moreOrEqual=0, lessOrEqual=-1, top=1, left=2, zIndex=0, height=2, width=3, minimized=False, titlevisible=True, fulldragboard=False, relx=True, rely=True, relwidth=True, relheight=True, anchor=WidgetConfigAnchor.top_left),
            ]
        ),
    )
    assert len(iwidget.positions.configurations) == 1
    assert iwidget.positions.configurations[0].id == 1

    iwidget_existing = WidgetInstance(
        id="w2",
        positions=WidgetPositions(configurations=[WidgetPositionsConfig(id=0, moreOrEqual=0, lessOrEqual=-1)]),
    )
    utils.update_position(
        iwidget_existing,
        "widget",
        WidgetInstanceDataUpdate(layoutConfig=[LayoutConfig(id=0, action="update", top=9)]),
    )
    assert iwidget_existing.positions.configurations[0].widget.top == 9


def test_first_id_widget_instance():
    widgets = {
        "tab-0-0": WidgetInstance(id="tab-0-0"),
        "tab-0-2": WidgetInstance(id="tab-0-2"),
    }
    assert utils.first_id_widget_instance(widgets) == 1


async def test_save_widget_instance_and_update_widget_instance(monkeypatch, db_session):
    tab = SimpleNamespace(id="tab-0", widgets={})
    workspace = SimpleNamespace(tabs={"tab-0": tab, "tab-1": SimpleNamespace(id="tab-1", widgets={})})
    user = SimpleNamespace(id="u1")
    iwidget_data = WidgetInstanceDataCreate(title="x", widget="acme/widget/1.0.0", layoutConfig=[])

    resource = SimpleNamespace(get_processed_info=lambda **_kwargs: SimpleNamespace(title="Default", preferences=[], properties=[]))

    async def _update_widget_value(_db, new_iwidget, _data, _user, required=False):
        new_iwidget.resource = "rid"
        return resource

    monkeypatch.setattr(utils, "update_widget_value", _update_widget_value)
    monkeypatch.setattr(utils, "update_title_value", lambda *_args, **_kwargs: _none())
    monkeypatch.setattr("wirecloud.platform.workspace.crud.change_tab", lambda *_args, **_kwargs: _none())

    async def _none():
        return None

    created = await utils.save_widget_instance(db_session, workspace, iwidget_data, user, tab, commit=True)
    assert created.id == "tab-0-0"
    assert created.positions.configurations[0].widget.width == 1
    assert "tab-0-0" in tab.widgets

    created2 = await utils.save_widget_instance(db_session, workspace, iwidget_data, user, tab, commit=False)
    assert created2.id == "tab-0-1"

    called = {"init": 0, "update": 0}

    async def _set_initial_values(*_args, **_kwargs):
        called["init"] += 1

    def _update_position(*_args, **_kwargs):
        called["update"] += 1

    monkeypatch.setattr(utils, "set_initial_values", _set_initial_values)
    monkeypatch.setattr(utils, "update_position", _update_position)
    iwidget_layout = WidgetInstanceDataCreate(
        title="x",
        widget="acme/widget/1.0.0",
        layoutConfig=[LayoutConfig(id=0, action="update")],
        variable_values={"p": WidgetVariables(users={"u1": "v"})},
    )
    await utils.save_widget_instance(db_session, workspace, iwidget_layout, user, tab, commit=False)
    await utils.save_widget_instance(
        db_session,
        workspace,
        iwidget_layout,
        user,
        tab,
        initial_variable_values=iwidget_layout.variable_values,
        commit=False,
    )
    assert called["init"] == 1
    assert called["update"] == 2

    iwidget = tab.widgets["tab-0-0"]
    request = _request()

    with pytest.raises(ValueError):
        await utils.update_widget_instance(db_session, request, WidgetInstanceDataUpdate(), user, workspace, tab)

    missing_resp = await utils.update_widget_instance(db_session, request, WidgetInstanceDataUpdate(id="missing"), user, workspace, tab)
    assert missing_resp.status_code == 404

    monkeypatch.setattr(utils, "update_widget_value", lambda *_args, **_kwargs: _none())
    monkeypatch.setattr(utils, "update_title_value", lambda *_args, **_kwargs: _none())

    with pytest.raises(ValueError):
        await utils.update_widget_instance(db_session, request, WidgetInstanceDataUpdate(id=iwidget.id, layout=-1), user, workspace, tab)

    tab_not_found = await utils.update_widget_instance(
        db_session,
        request,
        WidgetInstanceDataUpdate(id=iwidget.id, tab="missing"),
        user,
        workspace,
        tab,
    )
    assert tab_not_found.status_code == 404

    await utils.update_widget_instance(
        db_session,
        request,
        WidgetInstanceDataUpdate(id=iwidget.id, tab="tab-1"),
        user,
        workspace,
        tab,
        update_cache=False,
    )
    assert len(workspace.tabs["tab-1"].widgets) == 1

    iwidget_moved = next(iter(workspace.tabs["tab-1"].widgets.values()))
    await utils.update_widget_instance(
        db_session,
        request,
        WidgetInstanceDataUpdate(id=iwidget_moved.id, tab="tab-1"),
        user,
        workspace,
        workspace.tabs["tab-1"],
        update_cache=False,
    )
    assert iwidget_moved.id in workspace.tabs["tab-1"].widgets

    ws_called = {"n": 0}

    async def _change_workspace(*_args, **_kwargs):
        ws_called["n"] += 1

    monkeypatch.setattr("wirecloud.platform.workspace.crud.change_workspace", _change_workspace)
    await utils.update_widget_instance(
        db_session,
        request,
        WidgetInstanceDataUpdate(id=iwidget_moved.id, layout=2, layoutConfig=[LayoutConfig(id=0, action="update")]),
        user,
        workspace,
        workspace.tabs["tab-1"],
        update_cache=False,
    )
    assert iwidget_moved.layout == 2

    await utils.update_widget_instance(
        db_session,
        request,
        WidgetInstanceDataUpdate(id=iwidget_moved.id),
        user,
        workspace,
        workspace.tabs["tab-1"],
        update_cache=True,
    )
    assert ws_called["n"] == 1


def test_get_widget_instances_from_workspace():
    workspace = SimpleNamespace(
        tabs={
            "t1": SimpleNamespace(widgets={"a": WidgetInstance(id="a")}),
            "t2": SimpleNamespace(widgets={"b": WidgetInstance(id="b")}),
        }
    )
    instances = utils.get_widget_instances_from_workspace(workspace)
    assert {w.id for w in instances} == {"a", "b"}
