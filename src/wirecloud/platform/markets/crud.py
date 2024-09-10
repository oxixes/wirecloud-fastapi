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
from sqlalchemy import select, insert, delete
from sqlalchemy.exc import IntegrityError

from src.wirecloud.database import DBSession
from src.wirecloud.commons.auth.schemas import User
from src.wirecloud.platform.markets.models import Market as MarketModel
from src.wirecloud.commons.auth.models import User as UserModel
from src.wirecloud.platform.markets.schemas import Market, MarketOptions


async def get_markets_for_user(db: DBSession, user: Optional[User]) -> list[Market]:
    if user is not None:
        query = select(MarketModel).where(MarketModel.public == True or MarketModel.user_id == user.id)
    else:
        query = select(MarketModel).where(MarketModel.public == True)

    result = await db.execute(query)
    resources = result.scalars().all()

    return [Market(
        id=resource.id,
        name=resource.name,
        public=resource.public,
        options=MarketOptions.model_validate_json(resource.options),
        user_id=resource.user_id
    ) for resource in resources]


async def get_market_user(db: DBSession, market: Market) -> Optional[User]:
    query = select(UserModel).where(UserModel.id == market.user_id)

    result = await db.execute(query)
    user = result.scalar()

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
    ) if user else None


async def create_market(db: DBSession, market: Market) -> bool:
    # Check integrity
    try:
        query = insert(MarketModel).values(
            name=market.name,
            public=market.public,
            options=market.options.model_dump_json(),
            user_id=market.user_id
        )

        await db.execute(query)
        await db.commit()
    except IntegrityError:
        await db.rollback()
        return False

    return True


async def delete_market_by_name(db: DBSession, user: User, name: str) -> bool:
    query = delete(MarketModel).where(MarketModel.name == name and MarketModel.user_id == user.id)

    result = await db.execute(query)
    await db.commit()

    if result.rowcount == 0:
        return False

    return True