# -*- coding: utf-8 -*-

# Copyright (c) 2024 Future Internet Consulting and Development Solutions S.L.

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

from typing import Optional, Union
from datetime import datetime, timezone

from bson import ObjectId

from src.wirecloud.commons.auth.schemas import User, UserWithPassword, Group, Permission, UserAll
from src.wirecloud.commons.auth.models import DBUser as UserModel
from src.wirecloud.commons.auth.models import DBGroup as GroupModel
from src.wirecloud.commons.auth.models import DBPlatformPreference as PlatformPreferenceModel
from src.wirecloud.database import DBSession, Id


async def get_user_by_id(db: DBSession, user_id: Id, user_all: bool = False) -> Union[User, UserAll, None]:
    query = {"_id": ObjectId(user_id)}
    user_data = await db.client.users.find_one(query)

    if user_data is None:
        return None

    user = UserModel.model_validate(user_data)
    if not user_all:

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
            last_login=user.last_login
        )

    else:

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
            groups=user.groups,
            permissions=[Permission(**perm.model_dump()) for perm in user.user_permissions]
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
        last_login=user.last_login
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


async def get_user_groups(db: DBSession, user_id: Id) -> list[Group]:
    query = {"users": ObjectId(user_id)}
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
        password=user.password
    )


async def set_login_date_for_user(db: DBSession, user_id: Id) -> None:
    if not db.in_transaction:
        db.start_transaction()
    query = {"_id": ObjectId(user_id)}, {"$set": {"last_login": datetime.now(timezone.utc)}}
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
    if not db.in_transaction:
        db.start_transaction()

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


