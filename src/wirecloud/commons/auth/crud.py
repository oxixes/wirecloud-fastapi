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

from typing import Optional
from datetime import datetime, timezone
from src.wirecloud.commons.auth.schemas import User, UserWithPassword, Group, Permission
from src.wirecloud.commons.auth.models import DBUser as UserModel
from src.wirecloud.commons.auth.models import DBPermission as PermissionModel
from src.wirecloud.commons.auth.models import DBGroup as GroupModel
from src.wirecloud.database import DBSession


async def get_user_by_id(db: DBSession, user_id: int) -> Optional[User]:
    query = {"_id": user_id}
    user = await db.client.users.find_one(query)
    if user is None:
        return None

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

async def get_user_by_username(db: DBSession, username: str) -> Optional[User]:
    query = {"username": username}
    user = await db.client.users.find_one(query)
    if user is None:
        return None

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


async def get_all_user_permissions(db: DBSession, user_id: int) -> list[Permission]:
    permissions = set()

    individual_permissions_query = {"user_id": user_id}
    individual_permissions = await db.client.users.find_one(individual_permissions_query)
    group_ids = individual_permissions.get("groups")
    for permission in individual_permissions.get("user_permissions"):
        permissions.add(Permission(codename=permission.get("codename")))

    group_permissions_query = {"_id": {"$in": group_ids}}
    group_permissions = await db.client.groups.find(group_permissions_query).to_list()
    for group in group_permissions:
        for permission in group.get("group_permissions"):
            permissions.add(Permission(codename=permission.get("codename")))

    return list(permissions)


async def get_user_groups(db: DBSession, user_id: int) -> list[Group]:
    query = {"users": user_id}
    results = [GroupModel.model_validate(result) for result in await db.client.groups.find(query).to_list()]
    return results


async def get_user_with_password(db: DBSession, username: str) -> Optional[UserWithPassword]:
    query = {"username": username}
    user = await db.client.users.find_one(query)
    return user


async def set_login_date_for_user(db: DBSession, user_id: int) -> None:
    if not db.in_transaction():
        db.start_transaction()
    query = {"_id": user_id}, {"$set": {"last_login": datetime.now(timezone.utc)}}
    await db.client.users.update_one(query)
