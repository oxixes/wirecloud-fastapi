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
import sys

from bson import ObjectId

from wirecloud.commons.auth import crud
from wirecloud.commons.auth.models import Group, DBPlatformPreference
from wirecloud.commons.auth.schemas import Permission, UserAll, UserCreate, GroupCreate, OrganizationCreate
from wirecloud.database import Id
from unittest.mock import AsyncMock, MagicMock


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
    await crud.create_user_db(db_session, user_info)
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
            "path": [gid],
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
        {"_id": g1, "name": "G1", "codename": "g1", "users": [], "path": [g1]},
        {"_id": g2, "name": "G2", "codename": "g2", "users": [], "path": [g2]},
    ])

    await crud.add_user_to_groups_by_codename(db_session, user.id, ["g1", "g2"])
    await crud.add_user_to_groups_by_codename(db_session, user.id, ["g1"])

    user_doc = await db_session.client.users.find_one({"_id": ObjectId(user.id)})
    assert set(user_doc["groups"]) == {g1, g2}

    await crud.remove_user_from_all_groups(db_session, user.id)
    user_doc = await db_session.client.users.find_one({"_id": ObjectId(user.id)})
    assert user_doc["groups"] == []

    await crud.remove_user_from_all_groups(db_session, user.id)
    await crud.remove_user_from_all_groups(db_session, Id(str(ObjectId())))


async def test_group_creation_lookup_and_preferences(db_session):
    group_id = Id(str(ObjectId()))
    group = Group(_id=group_id, name="Team", codename="team", path=[group_id])
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
    ops_id = ObjectId()
    await db_session.client.groups.insert_one({"_id": ops_id, "name": "Ops", "codename": "ops", "path": [ops_id]})

    groups = await crud.get_all_groups(db_session)
    users = await crud.get_all_users(db_session)

    assert any(group.name == "Ops" for group in groups)
    assert any(user.username == "eve" for user in users)


def _make_groups(find_one_return, find_list):
    cursor = MagicMock()
    cursor.to_list = AsyncMock(return_value=find_list)
    groups = MagicMock()
    groups.find_one = AsyncMock(return_value=find_one_return)
    groups.find = AsyncMock(return_value=cursor)
    return groups


async def test_graph_lookup_helpers(monkeypatch, db_session):
    child_id = ObjectId()
    parent1_id = ObjectId()
    parent2_id = ObjectId()

    child_doc = {"_id": child_id, "path": [parent2_id, parent1_id, child_id]}
    parent1_doc = {"_id": parent1_id, "name": "P1", "codename": "p1", "path": [parent2_id, parent1_id], "is_organization": False}
    parent2_doc = {"_id": parent2_id, "name": "P2", "codename": "p2", "path": [parent2_id], "is_organization": True}

    fake_db = SimpleNamespace(client=SimpleNamespace(
        groups=_make_groups(find_one_return=child_doc, find_list=[parent1_doc, parent2_doc])
    ))

    parent_chain = await crud.get_all_parent_groups_from_child(fake_db, Id(str(child_id)))
    assert len(parent_chain) == 2
    assert {g.codename for g in parent_chain} == {"p1", "p2"}

    id_child = Id(str(child_id))
    id_parent2 = Id(str(parent2_id))
    child_org_group = Group(_id=id_child, name="Child", codename="child", path=[id_parent2, id_child], is_organization=True)

    fake_db.client.groups = _make_groups(find_one_return=parent2_doc, find_list=[])
    top = await crud.get_top_group_organization(fake_db, child_org_group)
    assert str(top.id) == str(parent2_id)

    id_original = Id(str(ObjectId()))
    original = Group(_id=id_original, name="Original", codename="original", path=[id_original], is_organization=False)
    assert await crud.get_top_group_organization(fake_db, original) is None

    id_root = Id(str(ObjectId()))
    root_group = Group(_id=id_root, name="Root", codename="root", path=[id_root], is_organization=True)
    top_self = await crud.get_top_group_organization(fake_db, root_group)
    assert str(top_self.id) == str(id_root)

    fake_db.client.groups = _make_groups(
        find_one_return={"_id": child_id, "path": [child_id]},
        find_list=[],
    )
    assert await crud.get_all_parent_groups_from_child(fake_db, Id(str(child_id))) == []


async def test_get_all_user_groups(monkeypatch, db_session):
    g1 = Id(str(ObjectId()))
    g2 = Id(str(ObjectId()))

    async def _parents(_db, gid):
        return [Group(_id=gid, name=str(gid), codename=str(gid), path=[gid])]

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


async def test_update_user_with_all_info_updates_db_and_index(monkeypatch, db_session):
    user = await _seed_user(db_session, "frank")
    user_all = await crud.get_user_with_all_info(db_session, user.id)
    user_all.first_name = "Franklin"
    user_all.permissions = [Permission(codename="USER.EDIT")]

    add_user_to_index = AsyncMock()
    monkeypatch.setitem(sys.modules, "wirecloud.commons.search", SimpleNamespace(add_user_to_index=add_user_to_index))

    await crud.update_user_with_all_info(db_session, user_all)
    updated = await db_session.client.users.find_one({"_id": ObjectId(user.id)})
    assert updated["first_name"] == "Franklin"
    add_user_to_index.assert_awaited_once()


async def test_group_crud_helpers_and_organization_queries(monkeypatch, db_session):
    await db_session.client.users.delete_many({})
    await db_session.client.groups.delete_many({})

    u1 = await _seed_user(db_session, "guser1")
    u2 = await _seed_user(db_session, "guser2")

    group_info = GroupCreate(name="Dev", codename="dev", users=[u1.id])
    created_group = await crud.create_group_db(db_session, group_info)
    assert created_group.name == "Dev"
    assert created_group.is_organization is False
    assert len(created_group.path) == 1
    assert str(created_group.path[0]) == str(created_group.id)

    await crud.add_group_to_users(db_session, created_group.id, [u1.id, u2.id])
    u1_doc = await db_session.client.users.find_one({"_id": ObjectId(u1.id)})
    u2_doc = await db_session.client.users.find_one({"_id": ObjectId(u2.id)})
    assert created_group.id in u1_doc["groups"]
    assert created_group.id in u2_doc["groups"]

    await crud.remove_group_to_users(db_session, created_group.id, [u1.id])
    u1_doc = await db_session.client.users.find_one({"_id": ObjectId(u1.id)})
    u2_doc = await db_session.client.users.find_one({"_id": ObjectId(u2.id)})
    assert created_group.id not in u1_doc["groups"]
    assert created_group.id in u2_doc["groups"]

    add_group_to_index = AsyncMock()
    monkeypatch.setitem(sys.modules, "wirecloud.commons.search", SimpleNamespace(add_group_to_index=add_group_to_index))
    created_group.codename = "dev-updated"
    await crud.update_group(db_session, created_group)
    group_doc = await db_session.client.groups.find_one({"_id": ObjectId(created_group.id)})
    assert group_doc["codename"] == "dev-updated"
    add_group_to_index.assert_awaited_once()

    org_info = OrganizationCreate(name="Org", codename="org", users=[u2.id])
    created_org = await crud.create_organization_db(db_session, org_info)
    assert created_org.is_organization is True
    assert len(created_org.path) == 1
    assert str(created_org.path[0]) == str(created_org.id)

    child_id = ObjectId()
    grandchild_id = ObjectId()
    await db_session.client.groups.insert_many([
        {"_id": child_id, "name": "Child", "codename": "child", "users": [ObjectId(u2.id)], "is_organization": True, "path": [ObjectId(created_org.id), child_id]},
        {"_id": grandchild_id, "name": "Grand", "codename": "grand", "users": [], "is_organization": True, "path": [ObjectId(created_org.id), child_id, grandchild_id]},
    ])

    groups = await crud.get_all_organization_groups(db_session, created_org)
    assert len(groups) == 3


async def test_update_path_for_descendants_and_delete_group(monkeypatch, db_session):
    await db_session.client.groups.delete_many({})

    root_id = ObjectId()
    child_id = ObjectId()
    sibling_id = ObjectId()
    await db_session.client.groups.insert_many([
        {"_id": root_id, "name": "Root", "codename": "root", "users": [], "is_organization": True, "path": [root_id]},
        {"_id": child_id, "name": "Child", "codename": "child", "users": [], "is_organization": True, "path": [root_id, child_id]},
        {"_id": sibling_id, "name": "Sibling", "codename": "sibling", "users": [], "is_organization": True, "path": [sibling_id]},
    ])

    root_group = Group(_id=Id(str(root_id)), name="Root", codename="root", users=[], is_organization=True, path=[Id(str(root_id))])
    await crud.update_path_for_descendants(db_session, root_group)

    child_doc = await db_session.client.groups.find_one({"_id": child_id})
    sibling_doc = await db_session.client.groups.find_one({"_id": sibling_id})
    assert child_doc["path"] == [child_id]
    assert sibling_doc["path"] == [sibling_id]

    to_delete_id = ObjectId()
    await db_session.client.groups.insert_one({"_id": to_delete_id, "name": "Del", "codename": "del", "users": [], "is_organization": False, "path": [to_delete_id]})
    to_delete = Group(_id=Id(str(to_delete_id)), name="Del", codename="del", users=[], is_organization=False, path=[Id(str(to_delete_id))])

    remove_users = AsyncMock()
    update_desc = AsyncMock()
    delete_group_from_index = AsyncMock()
    monkeypatch.setattr(crud, "remove_group_to_users", remove_users)
    monkeypatch.setattr(crud, "update_path_for_descendants", update_desc)
    monkeypatch.setitem(sys.modules, "wirecloud.commons.search", SimpleNamespace(delete_group_from_index=delete_group_from_index))

    await crud.delete_group(db_session, to_delete)
    assert await db_session.client.groups.find_one({"_id": to_delete_id}) is None
    remove_users.assert_awaited_once()
    update_desc.assert_awaited_once()
    delete_group_from_index.assert_awaited_once()

    to_delete2_id = ObjectId()
    await db_session.client.groups.insert_one({"_id": to_delete2_id, "name": "Del2", "codename": "del2", "users": [], "is_organization": False, "path": [to_delete2_id]})
    to_delete2 = Group(_id=Id(str(to_delete2_id)), name="Del2", codename="del2", users=[], is_organization=False, path=[Id(str(to_delete2_id))])
    update_desc.reset_mock()
    await crud.delete_group(db_session, to_delete2, skip_descendants=True)
    update_desc.assert_not_called()


async def test_delete_organization_branches(monkeypatch, db_session):
    await db_session.client.groups.delete_many({})

    org_id = ObjectId()
    org = Group(_id=Id(str(org_id)), name="Org", codename="org", users=[], is_organization=True, path=[Id(str(org_id))])
    remove_users = AsyncMock()
    delete_group_from_index = AsyncMock()
    monkeypatch.setattr(crud, "remove_group_to_users", remove_users)
    monkeypatch.setitem(sys.modules, "wirecloud.commons.search", SimpleNamespace(delete_group_from_index=delete_group_from_index))

    await crud.delete_organization(db_session, org)
    remove_users.assert_not_called()
    delete_group_from_index.assert_not_called()

    child_id = ObjectId()
    await db_session.client.groups.insert_many([
        {"_id": org_id, "name": "Org", "codename": "org", "users": [], "is_organization": True, "path": [org_id]},
        {"_id": child_id, "name": "Child", "codename": "child", "users": [ObjectId()], "is_organization": True, "path": [org_id, child_id]},
    ])

    await crud.delete_organization(db_session, org)
    assert await db_session.client.groups.find_one({"_id": org_id}) is None
    assert await db_session.client.groups.find_one({"_id": child_id}) is None
    assert remove_users.await_count == 2
    assert delete_group_from_index.await_count == 2


async def test_delete_user_removes_db_tokens_groups_and_index(monkeypatch, db_session):
    user = await _seed_user(db_session, "zara")
    gid = ObjectId()
    await db_session.client.groups.insert_one({"_id": gid, "name": "Team", "codename": "team", "users": [ObjectId(user.id)], "path": [gid]})
    await db_session.client.users.update_one({"_id": ObjectId(user.id)}, {"$set": {"groups": [gid]}})
    await crud.create_token(db_session, datetime.now(timezone.utc) + timedelta(minutes=30), user.id)

    delete_user_from_index = AsyncMock()
    monkeypatch.setitem(sys.modules, "wirecloud.commons.search", SimpleNamespace(delete_user_from_index=delete_user_from_index))

    await crud.delete_user(db_session, user)

    assert await db_session.client.users.find_one({"_id": ObjectId(user.id)}) is None
    group_doc = await db_session.client.groups.find_one({"_id": gid})
    assert ObjectId(user.id) not in group_doc.get("users", [])
    token_doc = await db_session.client.tokens.find_one({"user_id": user.id})
    assert token_doc is not None
    assert token_doc["valid"] is False
    delete_user_from_index.assert_awaited_once()


async def test_get_all_parent_groups_from_child_returns_empty_when_child_missing_or_without_path(monkeypatch):
    missing_db = SimpleNamespace(client=SimpleNamespace(groups=SimpleNamespace(find_one=AsyncMock(return_value=None))))
    assert await crud.get_all_parent_groups_from_child(missing_db, Id(str(ObjectId()))) == []

    no_path_db = SimpleNamespace(client=SimpleNamespace(groups=SimpleNamespace(find_one=AsyncMock(return_value={"_id": ObjectId()}))))
    assert await crud.get_all_parent_groups_from_child(no_path_db, Id(str(ObjectId()))) == []
