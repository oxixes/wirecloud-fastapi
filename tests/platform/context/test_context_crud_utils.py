# -*- coding: utf-8 -*-

from types import SimpleNamespace

from bson import ObjectId
from starlette.requests import Request

from wirecloud.platform.context import crud, utils
from wirecloud.platform.context.schemas import BaseContextKey, PlatformContextKey


def _request(path="/api/context/", query=""):
    req = Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": "GET",
            "scheme": "https",
            "server": ("wirecloud.example.org", 443),
            "path": path,
            "query_string": query.encode("utf-8"),
            "headers": [(b"host", b"wirecloud.example.org"), (b"user-agent", b"Mozilla/5.0")],
        }
    )
    req.state.lang = "en"
    return req


async def test_get_all_constants(db_session):
    await db_session.client.constants.insert_many(
        [
            {"_id": ObjectId(), "concept": "A", "value": "1"},
            {"_id": ObjectId(), "concept": "B", "value": "2"},
        ]
    )
    constants = await crud.get_all_constants(db_session)
    concepts = {item.concept: item.value for item in constants}
    assert concepts["A"] == "1"
    assert concepts["B"] == "2"


async def test_platform_workspace_context_helpers(monkeypatch, db_session):
    class _PluginA:
        def get_platform_context_definitions(self):
            return {"a": BaseContextKey(label="A", description="A desc")}

        async def get_platform_context_current_values(self, _db, _request, _user, session=None):
            return {"a": "va", "x": 1}

        def get_workspace_context_definitions(self):
            return {"wa": BaseContextKey(label="WA", description="WA desc")}

        def get_workspace_context_current_values(self, _workspace, _user):
            return {"wa": "vwa"}

    class _PluginB:
        def get_platform_context_definitions(self):
            return {"b": BaseContextKey(label="B", description="B desc")}

        async def get_platform_context_current_values(self, _db, _request, _user, session=None):
            return {"b": "vb"}

        def get_workspace_context_definitions(self):
            return {"wb": BaseContextKey(label="WB", description="WB desc")}

        def get_workspace_context_current_values(self, _workspace, _user):
            return {"wb": "vwb"}

    monkeypatch.setattr(utils, "get_plugins", lambda: (_PluginA(), _PluginB()))

    definitions = utils.get_platform_context_definitions()
    assert set(definitions.keys()) == {"a", "b"}

    current = await utils.get_platform_context_current_values(db_session, _request(), SimpleNamespace(id="u1"))
    assert current["a"] == "va"
    assert current["b"] == "vb"
    assert current["x"] == 1

    platform_ctx = await utils.get_platform_context(db_session, _request(), SimpleNamespace(id="u1"))
    assert isinstance(platform_ctx["a"], PlatformContextKey)
    assert platform_ctx["a"].value == "va"
    assert platform_ctx["b"].value == "vb"

    workspace_definitions = utils.get_workspace_context_definitions()
    assert set(workspace_definitions.keys()) == {"wa", "wb"}

    workspace_current = utils.get_workspace_context_current_values(SimpleNamespace(), SimpleNamespace(id="u1"))
    assert workspace_current == {"wa": "vwa", "wb": "vwb"}


async def test_constant_and_context_values_with_cache(monkeypatch, db_session):
    class _FakeCache:
        def __init__(self):
            self.store = {}
            self.get_calls = []
            self.set_calls = []

        async def get(self, key):
            self.get_calls.append(key)
            return self.store.get(key)

        async def set(self, key, value):
            self.set_calls.append((key, value))
            self.store[key] = value

    fake_cache = _FakeCache()
    monkeypatch.setattr(utils, "cache", fake_cache)

    calls = {"constants": 0}

    async def _constants(_db):
        calls["constants"] += 1
        return {"constA": "1"}

    async def _platform(_db, _request, _user, session=None):
        return {"dynamic": "2"}

    monkeypatch.setattr(utils, "get_constant_context_values", _constants)
    monkeypatch.setattr(utils, "get_platform_context_current_values", _platform)
    monkeypatch.setattr(utils, "get_workspace_context_current_values", lambda _workspace, _user: {"ws": "3"})

    user = SimpleNamespace(id="507f1f77bcf86cd799439011")
    first = await utils.get_context_values(db_session, SimpleNamespace(), _request(), user)
    second = await utils.get_context_values(db_session, SimpleNamespace(), _request(), user)

    assert first["platform"]["constA"] == "1"
    assert first["platform"]["dynamic"] == "2"
    assert first["workspace"] == {"ws": "3"}
    assert second["platform"]["constA"] == "1"
    assert calls["constants"] == 1
    assert len(fake_cache.set_calls) == 1

    anon = await utils.get_context_values(db_session, SimpleNamespace(), _request(), None)
    assert anon["platform"]["constA"] == "1"
    assert "constant_context/anonymous" in fake_cache.get_calls


async def test_get_constant_context_values(monkeypatch, db_session):
    async def _all_constants(_db):
        return [
            SimpleNamespace(concept="A", value="1"),
            SimpleNamespace(concept="B", value="2"),
        ]

    monkeypatch.setattr(utils, "get_all_constants", _all_constants)
    values = await utils.get_constant_context_values(db_session)
    assert values == {"A": "1", "B": "2"}
