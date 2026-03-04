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

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from bson import ObjectId

from wirecloud.commons.auth import crud
from wirecloud.commons.auth.models import Group, DBPlatformPreference
from wirecloud.commons.auth.schemas import Permission, UserAll, UserCreate
from wirecloud.database import Id


async def _seed_user(db_session, username="alice"):
    user_info = UserCreate(
        username=username,
        password="hashed",
        first_name="Alice",
        last_name="Example",
        email=f"{username}@example.com",
        is_superuser=False,
        is_staff=False,
        is_active=True,
        idm_data={"keycloak": {"idm_token": "tok"}},
    )
    await crud.create_user(db_session, user_info)
    return await crud.get_user_by_username(db_session, username)


async def test_token_crud_expiration_and_bulk_invalidation(db_session):
    user_id = Id(str(ObjectId()))

    token_id = await crud.create_token(db_session, datetime.now(timezone.utc) - timedelta(minutes=1), user_id)
    assert await crud.is_token_valid(db_session, token_id) is False

    token1 = await crud.create_token(db_session, datetime.now(timezone.utc) + timedelta(minutes=30), user_id)
    token2 = await crud.create_token(db_session, datetime.now(timezone.utc) + timedelta(minutes=30), user_id)

    await crud.invalidate_all_user_tokens(db_session, user_id)

    assert (await db_session.client.tokens.find_one({"_id": token1}))["valid"] is False
    assert (await db_session.client.tokens.find_one({"_id": token2}))["valid"] is False

    new_exp = datetime.now(timezone.utc) + timedelta(hours=1)
    old_exp = (await db_session.client.tokens.find_one({"_id": token1}))["expiration"]
    await crud.set_token_expiration(db_session, token1, new_exp)
    stored_exp = (await db_session.client.tokens.find_one({"_id": token1}))["expiration"]
    assert stored_exp != old_exp


async def test_is_token_valid_returns_false_for_missing_token(db_session):
    assert await crud.is_token_valid(db_session, ObjectId()) is False


async def test_get_user_none_branches(db_session):
    unknown_id = Id(str(ObjectId()))
    assert await crud.get_user_by_id(db_session, unknown_id) is None
    assert await crud.get_user_by_username(db_session, "missing") is None
    assert await crud.get_user_with_password(db_session, "missing") is None
    assert await crud.get_user_with_all_info(db_session, unknown_id) is None
    assert await crud.get_user_with_all_info_by_username(db_session, "missing") is None
    assert await crud.get_all_user_permissions(db_session, unknown_id) == []


async def test_update_user_and_user_info_with_permissions(db_session):
    user = await _seed_user(db_session, "bob")

    gid = ObjectId()
    await db_session.client.groups.insert_one(
        {
            "_id": gid,
            "name": "Editors",
            "codename": "editors",
            "group_permissions": [{"codename": "widgets.edit"}],
            "users": [ObjectId(user.id)],
        }
    )
    await db_session.client.users.update_one(
        {"_id": ObjectId(user.id)},
        {"$set": {"groups": [gid], "user_permissions": [{"codename": "widgets.view"}]}}
    )

    user.first_name = "Robert"
    await crud.update_user(db_session, user)

    updated = await crud.get_user_by_id(db_session, user.id)
    assert updated.first_name == "Robert"

    user_all = await crud.get_user_with_all_info(db_session, user.id)
    assert {p.codename for p in user_all.permissions} == {"widgets.view", "widgets.edit"}

    user_all_username = await crud.get_user_with_all_info_by_username(db_session, "bob")
    assert user_all_username.username == "bob"

    groups = await crud.get_user_groups(db_session, Id(str(ObjectId())))
    assert groups == []


async def test_group_assignment_and_removal(db_session):
    user = await _seed_user(db_session, "carol")
    g1 = ObjectId()
    g2 = ObjectId()

    await db_session.client.groups.insert_many([
        {"_id": g1, "name": "G1", "codename": "g1", "users": []},
        {"_id": g2, "name": "G2", "codename": "g2", "users": []},
    ])

    await crud.add_user_to_groups_by_codename(db_session, user.id, ["g1", "g2"])
    await crud.add_user_to_groups_by_codename(db_session, user.id, ["g1"])  # no duplicates path

    user_doc = await db_session.client.users.find_one({"_id": ObjectId(user.id)})
    assert set(user_doc["groups"]) == {g1, g2}

    await crud.remove_user_from_all_groups(db_session, user.id)
    user_doc = await db_session.client.users.find_one({"_id": ObjectId(user.id)})
    assert user_doc["groups"] == []

    await crud.remove_user_from_all_groups(db_session, user.id)
    await crud.remove_user_from_all_groups(db_session, Id(str(ObjectId())))


async def test_group_creation_lookup_and_preferences(db_session):
    group = Group(_id=Id(str(ObjectId())), name="Team", codename="team")
    await crud.create_group_if_not_exists(db_session, group)
    await crud.create_group_if_not_exists(db_session, group)

    by_name = await crud.get_group_by_name(db_session, "Team")
    assert by_name is not None

    by_id = await crud.get_group_by_id(db_session, group.id)
    assert by_id is not None

    assert await crud.get_group_by_name(db_session, "Nope") is None
    assert await crud.get_group_by_id(db_session, Id(str(ObjectId()))) is None

    user = await _seed_user(db_session, "dave")

    await crud.set_login_date_for_user(db_session, user.id)
    assert (await db_session.client.users.find_one({"_id": ObjectId(user.id)}))["last_login"] is not None

    await crud.remove_user_idm_data(db_session, user.id, "keycloak")
    idm_data = (await db_session.client.users.find_one({"_id": ObjectId(user.id)}))["idm_data"]
    assert "keycloak" not in idm_data

    assert await crud.get_username_by_id(db_session, user.id) == "dave"
    assert await crud.get_username_by_id(db_session, Id(str(ObjectId()))) is None

    prefs = [DBPlatformPreference(name="theme", value="dark")]
    await crud.set_user_preferences(db_session, user.id, prefs)

    all_prefs = await crud.get_user_preferences(db_session, user.id)
    assert all_prefs[0].name == "theme"

    named_pref = await crud.get_user_preferences(db_session, user.id, name="theme")
    assert named_pref[0].value == "dark"

    missing_named_pref = await crud.get_user_preferences(db_session, user.id, name="missing")
    assert missing_named_pref is None

    assert await crud.get_user_preferences(db_session, Id(str(ObjectId()))) is None


async def test_get_all_groups_and_users(db_session):
    await db_session.client.users.delete_many({})
    await db_session.client.groups.delete_many({})

    await _seed_user(db_session, "eve")
    await db_session.client.groups.insert_one({"_id": ObjectId(), "name": "Ops", "codename": "ops"})

    groups = await crud.get_all_groups(db_session)
    users = await crud.get_all_users(db_session)

    assert any(group.name == "Ops" for group in groups)
    assert any(user.username == "eve" for user in users)


class _FakeCursor:
    def __init__(self, result):
        self.result = result

    async def to_list(self, length=None):
        return self.result


async def test_graph_lookup_helpers(monkeypatch, db_session):
    child_id = ObjectId()
    parent1 = ObjectId()
    parent2 = ObjectId()

    class _FakeGroups:
        def __init__(self, result):
            self.result = result

        async def aggregate(self, _pipeline):
            return _FakeCursor(self.result)

    fake_db = SimpleNamespace(client=SimpleNamespace(groups=_FakeGroups([
        {
            "_id": child_id,
            "name": "Child",
            "codename": "child",
            "parents": [
                {"_id": parent1, "name": "P1", "codename": "p1", "depth": 0},
                {"_id": parent2, "name": "P2", "codename": "p2", "depth": 2},
            ],
        }
    ])))

    parent_chain = await crud.get_all_parent_groups_from_child(fake_db, Id(str(child_id)))
    assert len(parent_chain) == 3

    root_group = Group(_id=Id(str(child_id)), name="Child", codename="child")
    top = await crud.get_top_group_organization(fake_db, root_group)
    assert str(top.id) == str(parent2)

    fake_db.client.groups = _FakeGroups([])
    assert await crud.get_all_parent_groups_from_child(fake_db, Id(str(child_id))) == []

    original = Group(_id=Id(str(ObjectId())), name="Original", codename="original")
    assert await crud.get_top_group_organization(fake_db, original) == original

    fake_db.client.groups = _FakeGroups([
        {"_id": child_id, "name": "Child", "codename": "child", "parents": []}
    ])
    top_self = await crud.get_top_group_organization(fake_db, root_group)
    assert str(top_self.id) == str(child_id)


async def test_get_all_user_groups(monkeypatch, db_session):
    g1 = Id(str(ObjectId()))
    g2 = Id(str(ObjectId()))

    async def _parents(_db, gid):
        return [Group(_id=gid, name=str(gid), codename=str(gid))]

    monkeypatch.setattr(crud, "get_all_parent_groups_from_child", _parents)

    user = UserAll(
        id=Id(str(ObjectId())),
        username="u",
        email="u@example.com",
        first_name="U",
        last_name="X",
        is_superuser=False,
        is_staff=False,
        is_active=True,
        date_joined=datetime.now(timezone.utc),
        last_login=None,
        idm_data={},
        groups=[g1, g2],
        permissions=[Permission(codename="p")],
    )

    groups = await crud.get_all_user_groups(db_session, user)
    assert len(groups) == 2
