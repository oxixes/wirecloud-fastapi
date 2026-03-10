# -*- coding: utf-8 -*-

from datetime import datetime, timezone
from types import SimpleNamespace

from wirecloud.commons.auth.models import DBPlatformPreference
from wirecloud.platform.preferences import crud, routes, utils
from wirecloud.platform.preferences.schemas import PlatformPreferenceCreate, PlatformPreferenceCreateValue, WorkspacePreference
from wirecloud.platform.workspace.models import DBWorkspacePreference, DBTabPreference


def _workspace():
    return SimpleNamespace(
        id="507f1f77bcf86cd799439011",
        last_modified=datetime.now(timezone.utc),
        preferences=[],
        tabs={},
    )


def _tab():
    return SimpleNamespace(
        id="tab1",
        last_modified=datetime.now(timezone.utc),
        preferences=[],
    )


def test_parse_values_and_simple_utils():
    parsed = routes.parse_values([DBPlatformPreference(name="lang", value="es"), DBPlatformPreference(name="theme", value="default")])
    assert parsed["lang"]["inherit"] is False
    assert parsed["theme"]["value"] == "default"

    workspace = _workspace()
    tab = _tab()
    assert utils.make_workspace_preferences_cache_key(workspace).startswith("_workspace_preferences_cache/")
    assert utils.make_tab_preferences_cache_key(tab).startswith("_tab_preferences_cache/")
    assert utils.serialize_default_value("x") == "x"
    assert utils.serialize_default_value({"a": 1}) == '{"a": 1}'

    inheritable = utils.parse_inheritable_values(
        [
            DBWorkspacePreference(name="public", inherit=False, value="true"),
            DBWorkspacePreference(name="requireauth", inherit=True, value="false"),
        ]
    )
    assert inheritable["public"].value == "true"
    assert inheritable["requireauth"].inherit is True


async def test_get_workspace_and_tab_preference_values(monkeypatch):
    class _FakeCache:
        def __init__(self):
            self.store = {}

        async def get(self, key):
            return self.store.get(key)

        async def set(self, key, value):
            self.store[key] = value

    fake_cache = _FakeCache()
    monkeypatch.setattr(utils, "cache", fake_cache)
    monkeypatch.setattr(
        utils,
        "get_workspace_preferences",
        lambda: [
            SimpleNamespace(name="public", inheritByDefault=False, defaultValue=False),
            SimpleNamespace(name="screenSizes", inheritByDefault=True, defaultValue=[{"id": 0}]),
        ],
    )
    monkeypatch.setattr(
        utils,
        "get_tab_preferences",
        lambda: [
            SimpleNamespace(name="initiallayout", inheritByDefault=True, defaultValue={"type": "columnlayout"}),
            SimpleNamespace(name="tabTheme", inheritByDefault=False, defaultValue="classic"),
        ],
    )

    workspace = _workspace()
    workspace.preferences = [DBWorkspacePreference(name="public", inherit=False, value="true")]
    tab = _tab()
    tab.preferences = [DBTabPreference(name="initiallayout", inherit=False, value='{"type": "fixed"}')]

    workspace_values = await utils.get_workspace_preference_values(workspace)
    assert workspace_values["public"].value == "true"
    assert workspace_values["screenSizes"].inherit is True
    workspace_values_cached = await utils.get_workspace_preference_values(workspace)
    assert workspace_values_cached["public"].value == "true"

    tab_values = await utils.get_tab_preference_values(tab)
    assert tab_values["initiallayout"].value == '{"type": "fixed"}'
    assert tab_values["tabTheme"].value == "classic"
    tab_values_cached = await utils.get_tab_preference_values(tab)
    assert tab_values_cached["initiallayout"].value == '{"type": "fixed"}'


async def test_update_preferences(monkeypatch, db_session):
    captured = {}

    async def _get_user_preferences(_db, _user_id):
        return [DBPlatformPreference(name="lang", value="en"), DBPlatformPreference(name="theme", value="default")]

    async def _set_user_preferences(_db, _user_id, preferences):
        captured["prefs"] = preferences

    committed = {"n": 0}

    async def _commit(_db):
        committed["n"] += 1

    monkeypatch.setattr(crud, "get_user_preferences", _get_user_preferences)
    monkeypatch.setattr(crud, "set_user_preferences", _set_user_preferences)
    monkeypatch.setattr(crud, "commit", _commit)

    create = PlatformPreferenceCreate(preferences={"lang": "es", "font": PlatformPreferenceCreateValue(value="large")})
    await crud.update_preferences(db_session, SimpleNamespace(id="u1"), create)
    names = {p.name for p in captured["prefs"]}
    assert names == {"lang", "theme", "font"}
    assert committed["n"] == 1

    create_no_changes = PlatformPreferenceCreate(preferences={"lang": "es", "theme": "default"})
    await crud.update_preferences(db_session, SimpleNamespace(id="u1"), create_no_changes)
    assert committed["n"] == 2


async def test_update_workspace_preferences(monkeypatch, db_session):
    workspace = _workspace()
    workspace.preferences = [DBWorkspacePreference(name="public", inherit=True, value="false")]

    called = {"change": 0, "delete": 0, "commit": 0}

    async def _change_workspace(_db, _workspace, _user):
        called["change"] += 1

    class _FakeCache:
        async def delete(self, _key):
            called["delete"] += 1

    async def _commit(_db):
        called["commit"] += 1

    monkeypatch.setattr(crud, "change_workspace", _change_workspace)
    monkeypatch.setattr(crud, "cache", _FakeCache())
    monkeypatch.setattr(crud, "commit", _commit)

    await crud.update_workspace_preferences(
        db_session,
        SimpleNamespace(id="u1"),
        workspace,
        {"public": WorkspacePreference(inherit=False, value="true"), "newpref": "x"},
        invalidate_cache=True,
    )
    assert any(p.name == "newpref" for p in workspace.preferences)
    assert called["change"] == 2
    assert called["delete"] == 1
    assert called["commit"] == 1

    called["change"] = called["delete"] = called["commit"] = 0
    await crud.update_workspace_preferences(
        db_session,
        SimpleNamespace(id="u1"),
        workspace,
        {"public": WorkspacePreference(inherit=False, value="true")},
        invalidate_cache=False,
    )
    assert called["change"] == 1
    assert called["delete"] == 0
    assert called["commit"] == 0


async def test_update_tab_preferences(monkeypatch, db_session):
    workspace = _workspace()
    tab = _tab()
    tab.preferences = [DBTabPreference(name="initiallayout", inherit=True, value="{}")]
    workspace.tabs = {tab.id: tab}

    called = {"change": 0, "delete": 0, "commit": 0}

    async def _change_workspace(_db, _workspace, _user):
        called["change"] += 1

    class _FakeCache:
        async def delete(self, _key):
            called["delete"] += 1

    async def _commit(_db):
        called["commit"] += 1

    monkeypatch.setattr(crud, "change_workspace", _change_workspace)
    monkeypatch.setattr(crud, "cache", _FakeCache())
    monkeypatch.setattr(crud, "commit", _commit)

    await crud.update_tab_preferences(
        db_session,
        SimpleNamespace(id="u1"),
        workspace,
        tab,
        {"initiallayout": WorkspacePreference(inherit=False, value='{"type":"fixed"}'), "new": "x"},
    )
    assert any(p.name == "new" for p in workspace.tabs[tab.id].preferences)
    assert called["change"] == 1
    assert called["delete"] == 1
    assert called["commit"] == 1


async def test_update_workspace_preferences_no_changes(monkeypatch, db_session):
    workspace = _workspace()
    workspace.preferences = [DBWorkspacePreference(name="public", inherit=False, value="true")]

    called = {"change": 0, "delete": 0, "commit": 0}

    async def _change_workspace(_db, _workspace, _user):
        called["change"] += 1

    class _FakeCache:
        async def delete(self, _key):
            called["delete"] += 1

    async def _commit(_db):
        called["commit"] += 1

    monkeypatch.setattr(crud, "change_workspace", _change_workspace)
    monkeypatch.setattr(crud, "cache", _FakeCache())
    monkeypatch.setattr(crud, "commit", _commit)

    await crud.update_workspace_preferences(
        db_session,
        SimpleNamespace(id="u1"),
        workspace,
        {"public": "true"},
        invalidate_cache=True,
    )
    assert called["change"] == 1
    assert called["delete"] == 0
    assert called["commit"] == 0

    workspace.preferences[0].inherit = True
    called["change"] = called["delete"] = called["commit"] = 0
    await crud.update_workspace_preferences(
        db_session,
        SimpleNamespace(id="u1"),
        workspace,
        {"public": "true"},
        invalidate_cache=True,
    )
    assert workspace.preferences[0].inherit is False
    assert called["change"] == 2
    assert called["delete"] == 1
    assert called["commit"] == 1


async def test_update_tab_preferences_string_branch_and_noop(monkeypatch, db_session):
    workspace = _workspace()
    tab = _tab()
    tab.preferences = [DBTabPreference(name="initiallayout", inherit=True, value="same")]
    workspace.tabs = {tab.id: tab}

    called = {"change": 0, "delete": 0, "commit": 0}

    async def _change_workspace(_db, _workspace, _user):
        called["change"] += 1

    class _FakeCache:
        async def delete(self, _key):
            called["delete"] += 1

    async def _commit(_db):
        called["commit"] += 1

    monkeypatch.setattr(crud, "change_workspace", _change_workspace)
    monkeypatch.setattr(crud, "cache", _FakeCache())
    monkeypatch.setattr(crud, "commit", _commit)

    await crud.update_tab_preferences(
        db_session,
        SimpleNamespace(id="u1"),
        workspace,
        tab,
        {"initiallayout": "same"},
    )
    assert tab.preferences[0].inherit is False
    assert called["change"] == 1
    assert called["delete"] == 1
    assert called["commit"] == 1

    called["change"] = called["delete"] = called["commit"] = 0
    await crud.update_tab_preferences(
        db_session,
        SimpleNamespace(id="u1"),
        workspace,
        tab,
        {"initiallayout": "same"},
    )
    assert called["change"] == 0
    assert called["delete"] == 0
    assert called["commit"] == 0


async def test_update_tab_preferences_model_noop(monkeypatch, db_session):
    workspace = _workspace()
    tab = _tab()
    tab.preferences = [DBTabPreference(name="initiallayout", inherit=True, value="same")]
    workspace.tabs = {tab.id: tab}

    called = {"change": 0, "delete": 0, "commit": 0}

    async def _change_workspace(_db, _workspace, _user):
        called["change"] += 1

    class _FakeCache:
        async def delete(self, _key):
            called["delete"] += 1

    async def _commit(_db):
        called["commit"] += 1

    monkeypatch.setattr(crud, "change_workspace", _change_workspace)
    monkeypatch.setattr(crud, "cache", _FakeCache())
    monkeypatch.setattr(crud, "commit", _commit)

    await crud.update_tab_preferences(
        db_session,
        SimpleNamespace(id="u1"),
        workspace,
        tab,
        {"initiallayout": WorkspacePreference(inherit=True, value=None)},
    )
    assert called["change"] == 0
    assert called["delete"] == 0
    assert called["commit"] == 0
