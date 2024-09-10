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
from sqlalchemy import select, update
from sqlalchemy.orm import aliased
from src.wirecloud.commons.auth.schemas import User, UserWithPassword, Group, Permission
from src.wirecloud.commons.auth.models import User as UserModel
from src.wirecloud.commons.auth.models import Permission as PermissionModel
from src.wirecloud.commons.auth.models import Group as GroupModel
from src.wirecloud.database import DBSession


async def get_user_by_id(db: DBSession, user_id: int) -> Optional[User]:
    user = await db.scalar(select(UserModel).filter(UserModel.id == user_id))
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
    user = await db.scalar(select(UserModel).filter(UserModel.username == username))
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
    GroupAlias = aliased(GroupModel)

    individual_permissions_query = select(PermissionModel.codename)\
        .join(UserModel.permissions)\
        .filter(UserModel.id == user_id)

    group_permissions_query = select(PermissionModel.codename)\
        .join(GroupAlias.permissions)\
        .join(GroupModel.users)\
        .filter(UserModel.id == user_id)

    combined_query = individual_permissions_query.union(group_permissions_query)

    permissions = await db.execute(combined_query)
    permissions = permissions.scalars().all()

    return [Permission(codename=permission) for permission in permissions]


async def get_user_groups(db: DBSession, user_id: int) -> list[Group]:
    groups_query = select(GroupModel)\
        .join(UserModel.groups)\
        .filter(UserModel.id == user_id)

    groups = await db.execute(groups_query)
    groups = groups.scalars().all()

    return [Group(id=group.id, name=group.name) for group in groups]


async def get_user_with_password(db: DBSession, username: str) -> Optional[UserWithPassword]:
    user = await db.scalar(select(UserModel).filter(UserModel.username == username))
    if user is None:
        return None

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


async def set_login_date_for_user(db: DBSession, user_id: int) -> None:
    await db.execute(update(UserModel).filter(UserModel.id == user_id).values(last_login=datetime.now(timezone.utc)))
