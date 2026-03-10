# -*- coding: utf-8 -*-

from datetime import datetime, timezone
from types import SimpleNamespace

from bson import ObjectId

from wirecloud.platform.markets import crud, utils
from wirecloud.platform.markets.models import MarketOptions


async def test_get_markets_for_user_and_create_delete(db_session, monkeypatch):
    user_id = ObjectId()
    other_id = ObjectId()
    market_1 = {
        "_id": ObjectId(),
        "name": "m1",
        "public": True,
        "user_id": user_id,
        "options": {"name": "m1", "type": "wirecloud", "url": "https://m1.example.org"},
    }
    market_2 = {
        "_id": ObjectId(),
        "name": "m2",
        "public": False,
        "user_id": user_id,
        "options": {"name": "m2", "type": "wirecloud", "url": "https://m2.example.org"},
    }
    market_3 = {
        "_id": ObjectId(),
        "name": "m3",
        "public": False,
        "user_id": other_id,
        "options": {"name": "m3", "type": "wirecloud", "url": "https://m3.example.org"},
    }
    await db_session.client.markets.insert_many([market_1, market_2, market_3])

    anon = await crud.get_markets_for_user(db_session, None)
    assert [m.name for m in anon] == ["m1"]

    user_no_perm = SimpleNamespace(id=str(user_id), has_perm=lambda _perm: False)
    visible = await crud.get_markets_for_user(db_session, user_no_perm)
    assert {m.name for m in visible} == {"m1", "m2"}

    user_with_perm = SimpleNamespace(id=str(user_id), has_perm=lambda perm: perm == "MARKETPLACE.VIEW")
    all_markets = await crud.get_markets_for_user(db_session, user_with_perm)
    assert {m.name for m in all_markets} == {"m1", "m2", "m3"}

    duplicate = await crud.create_market(db_session, visible[0])
    assert duplicate is False

    new_market = visible[0].model_copy(update={"id": ObjectId(), "name": "m4"})
    created = await crud.create_market(db_session, new_market)
    assert created is True
    stored = await db_session.client.markets.find_one({"name": "m4"})
    assert stored is not None

    committed = {"n": 0}

    async def _commit(_db):
        committed["n"] += 1

    monkeypatch.setattr(crud, "commit", _commit)
    missing_delete = await crud.delete_market_by_name(db_session, SimpleNamespace(id=user_id), "missing")
    assert missing_delete is False
    ok_delete = await crud.delete_market_by_name(db_session, SimpleNamespace(id=user_id), "m1")
    assert ok_delete is True
    assert committed["n"] == 2


async def test_get_market_user(db_session):
    user_id = ObjectId()
    await db_session.client.users.insert_one(
        {
            "_id": user_id,
            "password": None,
            "last_login": None,
            "is_superuser": False,
            "username": "alice",
            "first_name": "Alice",
            "last_name": "Doe",
            "email": "alice@example.org",
            "is_staff": False,
            "is_active": True,
            "date_joined": datetime.now(timezone.utc),
            "idm_data": {},
            "user_permissions": [],
            "groups": [],
            "preferences": [],
        }
    )
    market = SimpleNamespace(user_id=user_id)
    user = await crud.get_market_user(db_session, market)
    assert user.username == "alice"
    assert await crud.get_market_user(db_session, SimpleNamespace(user_id=ObjectId())) is None


async def test_utils_market_classes_local_catalogue_and_managers(monkeypatch, db_session):
    utils._market_classes = None
    utils._local_catalogue = None

    class _Manager:
        def __init__(self, user, name, options):
            self.user = user
            self.name = name
            self.options = options

    class _PluginA:
        def get_market_classes(self):
            return {"wirecloud": _Manager}

    class _PluginB:
        def get_market_classes(self):
            return {"other": _Manager}

    monkeypatch.setattr(utils, "get_plugins", lambda: (_PluginA(), _PluginB()))
    classes = utils.get_market_classes()
    assert set(classes.keys()) == {"wirecloud", "other"}
    assert utils.get_market_classes() is classes

    local = utils.get_local_catalogue()
    assert local.name == "local"
    assert local.options.type == "wirecloud"
    assert utils.get_local_catalogue() is local

    markets = [
        SimpleNamespace(name="m1", options=MarketOptions(name="m1", type="wirecloud", url="https://m1"), user_id=ObjectId()),
        SimpleNamespace(name="m2", options=MarketOptions(name="m2", type="missing", url="https://m2"), user_id=ObjectId()),
    ]
    monkeypatch.setattr(utils, "get_markets_for_user", lambda _db, _user: _markets(markets))
    monkeypatch.setattr(utils, "get_market_user", lambda _db, _market: _market_user())

    async def _markets(values):
        return values

    async def _market_user():
        return SimpleNamespace(username="alice")

    managers = await utils.get_market_managers(db_session, SimpleNamespace(id="u1"))
    assert "alice/m1" in managers
    assert "alice/m2" not in managers


async def test_market_manager_base_methods_noop(db_session):
    manager = utils.MarketManager(None, "m", MarketOptions(name="m", type="wirecloud"))
    assert await manager.create(db_session, None, None) is None
    assert await manager.delete(db_session, None) is None
    assert await manager.publish(db_session, None, None, None) is None
