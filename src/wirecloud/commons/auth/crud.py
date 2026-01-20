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

from typing import Optional
from datetime import datetime, timezone

from bson import ObjectId

from wirecloud.commons.auth.schemas import User, UserWithPassword, Permission, UserAll, UserCreate
from wirecloud.commons.auth.models import DBUser as UserModel
from wirecloud.commons.auth.models import Group as GroupModel, Group
from wirecloud.commons.auth.models import DBPlatformPreference as PlatformPreferenceModel
from wirecloud.database import DBSession, Id


async def create_token(db: DBSession, expiration: datetime, user_id: Id, idm_session: Optional[str] = None) -> ObjectId:
    token = {
        "_id": ObjectId(),
        "valid": True,
        "expiration": expiration,
        "user_id": user_id
    }

    if idm_session is not None:
        token["idm_session"] = idm_session

    await db.client.tokens.insert_one(token)
    return token["_id"]


async def is_token_valid(db: DBSession, token_id: ObjectId) -> bool:
    token = await db.client.tokens.find_one({"_id": token_id})

    if token is None:
        return False

    exp_datetime = token.get("expiration")
    exp_datetime = exp_datetime.replace(tzinfo=timezone.utc)  # Ensure the expiration datetime is timezone-aware
    if exp_datetime < datetime.now(timezone.utc):
        return False

    return token["valid"]


async def set_token_expiration(db: DBSession, token_id: ObjectId, expiration: datetime) -> None:
    query = {"_id": token_id}, {"$set": {"expiration": expiration}}
    await db.client.tokens.update_one(*query)


async def invalidate_token(db: DBSession, token_id: ObjectId) -> None:
    query = {"_id": token_id}, {"$set": {"valid": False}}
    await db.client.tokens.update_one(*query)


async def invalidate_tokens_by_idm_session(db: DBSession, idm_session: str) -> None:
    query = {"idm_session": idm_session}, {"$set": {"valid": False}}
    await db.client.tokens.update_many(*query)


async def invalidate_all_user_tokens(db: DBSession, user_id: Id) -> None:
    query = {"user_id": user_id}, {"$set": {"valid": False}}
    await db.client.tokens.update_many(*query)


async def create_user(db: DBSession, user_info: UserCreate) -> None:
    user_created = UserModel(
        _id=ObjectId(),
        username=user_info.username,
        password=user_info.password,
        first_name=user_info.first_name,
        last_name=user_info.last_name,
        email=user_info.email,
        is_superuser=user_info.is_superuser,
        is_staff=user_info.is_staff,
        is_active=user_info.is_active,
        idm_data=user_info.idm_data,
        date_joined=datetime.now(timezone.utc),
        last_login=None
    )

    await db.client.users.insert_one(user_created.model_dump(by_alias=True))


async def update_user(db: DBSession, user_info: User) -> None:
    # Make sure the user_info is a User and not UserAll or similar
    user_info = User(**user_info.model_dump(include=User.model_fields.keys()))

    query = {"_id": ObjectId(user_info.id)}, {"$set": user_info.model_dump(by_alias=True, exclude={"id"})}
    await db.client.users.update_one(*query)


async def get_user_by_id(db: DBSession, user_id: Id) -> Optional[User]:
    query = {"_id": ObjectId(user_id)}
    user_data = await db.client.users.find_one(query)

    if user_data is None:
        return None

    user = UserModel.model_validate(user_data)

    return User(
        id=user.id,
        username=user.username,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        is_superuser=user.is_superuser,
        is_staff=user.is_staff,
        is_active=user.is_active,
        date_joined=user.date_joined,
        last_login=user.last_login,
        idm_data=user.idm_data
    )


async def get_all_user_permissions(db: DBSession, user_id: Id) -> list[Permission]:
    permissions = set()

    individual_permissions_query = {"user_id": ObjectId(user_id)}
    individual_permissions = await db.client.users.find_one(individual_permissions_query)

    if individual_permissions is None:
        return []

    group_ids = individual_permissions.get("groups")
    for permission in individual_permissions.get("user_permissions"):
        permissions.add(Permission(codename=permission.get("codename")))

    group_permissions_query = {"_id": {"$in": group_ids}}
    group_permissions = await db.client.groups.find(group_permissions_query).to_list()
    for group in group_permissions:
        for permission in group.get("group_permissions"):
            permissions.add(Permission(codename=permission.get("codename")))

    return list(permissions)


async def get_user_with_all_info(db: DBSession, user_id: Id) -> Optional[UserAll]:
    query = {"_id": ObjectId(user_id)}
    user_data = await db.client.users.find_one(query)

    if user_data is None:
        return None

    user = UserModel.model_validate(user_data)
    return UserAll(
        id=user.id,
        username=user.username,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        is_superuser=user.is_superuser,
        is_staff=user.is_staff,
        is_active=user.is_active,
        date_joined=user.date_joined,
        last_login=user.last_login,
        idm_data=user.idm_data,
        groups=user.groups,
        permissions=await get_all_user_permissions(db, user.id)
    )


async def get_user_with_all_info_by_username(db: DBSession, username: str) -> Optional[UserAll]:
    query = {"username": username}
    user_data = await db.client.users.find_one(query)

    if user_data is None:
        return None

    user = UserModel.model_validate(user_data)
    return UserAll(
        id=user.id,
        username=user.username,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        is_superuser=user.is_superuser,
        is_staff=user.is_staff,
        is_active=user.is_active,
        date_joined=user.date_joined,
        last_login=user.last_login,
        idm_data=user.idm_data,
        groups=user.groups,
        permissions=await get_all_user_permissions(db, user.id)
    )


async def get_user_by_username(db: DBSession, username: str) -> Optional[User]:
    query = {"username": username}
    user = await db.client.users.find_one(query)

    if user is None:
        return None

    user = UserModel.model_validate(user)

    return User(
        id=user.id,
        username=user.username,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        is_superuser=user.is_superuser,
        is_staff=user.is_staff,
        is_active=user.is_active,
        date_joined=user.date_joined,
        last_login=user.last_login,
        idm_data=user.idm_data
    )


async def get_user_groups(db: DBSession, user_id: Id) -> list[Group]:
    query = {"users": user_id}
    results = [GroupModel.model_validate(result) for result in await db.client.groups.find(query).to_list()]
    return results


async def get_user_with_password(db: DBSession, username: str) -> Optional[UserWithPassword]:
    query = {"username": username}
    user = await db.client.users.find_one(query)

    if user is None:
        return None

    user = UserModel.model_validate(user)

    return UserWithPassword(
        id=user.id,
        username=user.username,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        is_superuser=user.is_superuser,
        is_staff=user.is_staff,
        is_active=user.is_active,
        date_joined=user.date_joined,
        last_login=user.last_login,
        idm_data=user.idm_data,
        password=user.password
    )


async def add_user_to_groups_by_codename(db: DBSession, user_id: Id, group_names: list[str]) -> None:
    query = {"codename": {"$in": group_names}}
    groups = await db.client.groups.find(query).to_list()

    user_query = {"_id": ObjectId(user_id)}
    user = await db.client.users.find_one(user_query, {"groups": 1})
    current_group_ids = set(user.get("groups", []))

    new_group_ids = [group["_id"] for group in groups if group["_id"] not in current_group_ids]

    if new_group_ids:
        await db.client.groups.update_many(
            {"_id": {"$in": new_group_ids}},
            {"$addToSet": {"users": ObjectId(user_id)}}
        )

        updated_group_ids = list(current_group_ids.union(new_group_ids))
        await db.client.users.update_one(user_query, {"$set": {"groups": updated_group_ids}})


async def create_group_if_not_exists(db: DBSession, group_info: Group) -> None:
    query = {"name": group_info.name}
    group = await db.client.groups.find_one(query)

    if group is None:
        await db.client.groups.insert_one(group_info.model_dump(by_alias=True))


async def remove_user_from_all_groups(db: DBSession, user_id: Id) -> None:
    query = {"_id": ObjectId(user_id)}
    user = await db.client.users.find_one(query, {"groups": 1})

    if user is None:
        return

    group_ids = user.get("groups", [])
    if not group_ids:
        return

    await db.client.groups.update_many(
        {"_id": {"$in": group_ids}},
        {"$pull": {"users": ObjectId(user_id)}}
    )

    await db.client.users.update_one(query, {"$set": {"groups": []}})

async def set_login_date_for_user(db: DBSession, user_id: Id) -> None:
    query = {"_id": ObjectId(user_id)}, {"$set": {"last_login": datetime.now(timezone.utc)}}
    await db.client.users.update_one(*query)


async def remove_user_idm_data(db: DBSession, user_id: Id, provider: str) -> None:
    query = {"_id": ObjectId(user_id)}, {"$unset": {f"idm_data.{provider}": ""}}
    await db.client.users.update_one(*query)


async def get_username_by_id(db: DBSession, user_id: Id) -> Optional[str]:
    query = {"_id": ObjectId(user_id)}
    user = await db.client.users.find_one(query, {"username": 1})

    if user is None:
        return None

    return user.get("username")


async def get_user_preferences(db: DBSession, user_id: Id, name: str = None) -> Optional[list[PlatformPreferenceModel]]:
    query = {"_id": ObjectId(user_id)}
    user = await db.client.users.find_one(query)

    if user is None:
        return None

    if name is None:
        return UserModel.model_validate(user).preferences
    else:
        for preference in UserModel.model_validate(user).preferences:
            if preference.name == name:
                preference = PlatformPreferenceModel(**preference.model_dump())
                return [preference]


async def set_user_preferences(db: DBSession, user_id: Id, preferences: list[PlatformPreferenceModel]) -> None:
    query = {"_id": ObjectId(user_id)}, {"$set": {"preferences": [pref.model_dump() for pref in preferences]}}
    await db.client.users.update_one(*query)


async def get_group_by_name(db: DBSession, name: str) -> Optional[Group]:
    query = {"name": name}
    group = await db.client.groups.find_one(query)
    if group is None:
        return None

    return GroupModel.model_validate(group)


async def get_group_by_id(db: DBSession, group_id: Id) -> Optional[Group]:
    query = {"_id": ObjectId(group_id)}
    group = await db.client.groups.find_one(query)
    if group is None:
        return None

    return GroupModel.model_validate(group)


async def get_all_groups(db: DBSession) -> list[Group]:
    groups = await db.client.groups.find().to_list()
    return [GroupModel.model_validate(group) for group in groups]


async def get_all_users(db: DBSession):
    users = await db.client.users.find().to_list()
    return [UserModel.model_validate(user) for user in users]


async def get_all_parent_groups_from_child(db: DBSession, child_group_id: Id):
    pipeline = [
        {"$match": {"_id": ObjectId(child_group_id)}},
        {
            "$graphLookup": {
                "from": "groups",
                "startWith": "$parent",
                "connectFromField": "parent",
                "connectToField": "_id",
                "as": "parents",
                "depthField": "depth"
            }
        }
    ]

    cursor = await db.client.groups.aggregate(pipeline)
    result = await cursor.to_list(length=1)

    if not result:
        return []

    root = result[0]

    groups = [GroupModel.model_validate(root)]
    for parent in root.get("parents", []):
        groups.append(GroupModel.model_validate(parent))

    return groups


async def get_all_user_groups(db: DBSession, user: UserAll) -> list[Group]:
    groups = []
    for group_id in user.groups:
        groups += await get_all_parent_groups_from_child(db, group_id)

    return groups


async def get_top_group_organization(db: DBSession, group: Group) -> Group:
    pipeline = [
        {"$match": {"_id": ObjectId(group.id)}},
        {
            "$graphLookup": {
                "from": "groups",
                "startWith": "$parent",
                "connectFromField": "parent",
                "connectToField": "_id",
                "as": "parents",
                "depthField": "depth"
            }
        }
    ]

    cursor = await db.client.groups.aggregate(pipeline)
    result = await cursor.to_list(length=1)

    if not result:
        return group

    root = result[0]

    if not root.get("parents"):
        return GroupModel.model_validate(root)

    top_parent = max(root["parents"], key=lambda x: x.get("depth", 0))

    return GroupModel.model_validate(top_parent)