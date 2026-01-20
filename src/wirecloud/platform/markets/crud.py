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

from bson import ObjectId

from wirecloud.database import DBSession, commit
from wirecloud.commons.auth.schemas import User
from wirecloud.commons.auth.models import DBUser as UserModel
from wirecloud.platform.markets.models import DBMarket as MarketModel
from wirecloud.platform.markets.schemas import Market


async def get_markets_for_user(db: DBSession, user: Optional[User]) -> list[Market]:
    query = {"public": True}
    if user is not None:
        query = {"$or": [{"public": True}, {"user_id": ObjectId(user.id)}]}

    resources = [MarketModel.model_validate(resource) for resource in await db.client.markets.find(query).to_list()]
    return resources


async def get_market_user(db: DBSession, market: Market) -> Optional[User]:
    query = {"_id": ObjectId(market.user_id)}
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


async def create_market(db: DBSession, market: Market) -> bool:
    query = {"name": market.name, "user_id": ObjectId(market.user_id)}
    found_market = await db.client.markets.find_one(query)
    if found_market is not None:
        return False

    created_market = MarketModel(**market.model_dump())
    await db.client.markets.insert_one(created_market.model_dump(by_alias=True))

    return True


async def delete_market_by_name(db: DBSession, user: User, name: str) -> bool:
    query = {"name": name, "user_id": user.id}
    result = await db.client.markets.delete_one(query)

    await commit(db)

    if result.deleted_count == 0:
        return False

    return True
