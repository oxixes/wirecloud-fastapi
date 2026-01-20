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
from fastapi import Request

from wirecloud.platform.plugins import get_plugins
from wirecloud.platform.markets.schemas import MarketOptions
from wirecloud.platform.markets.crud import get_markets_for_user, get_market_user
from wirecloud.platform.markets.schemas import MarketEndpoint
from wirecloud.commons.auth.schemas import User, UserAll
from wirecloud.commons.utils.template.schemas.macdschemas import MACD
from wirecloud.commons.utils.wgt import WgtFile
from wirecloud.database import DBSession


class MarketManager:
    def __init__(self, user: Optional[str], name: str, options: MarketOptions):
        pass

    async def create(self, db: DBSession, request: Request, user: UserAll):
        pass

    async def delete(self, db: DBSession, request: Request):
        pass

    async def publish(self, db: DBSession, endpoint: Optional[MarketEndpoint], wgt_file: WgtFile, user: User,
                      request: Request = None, template: Optional[MACD] = None):
        pass


_market_classes: Optional[dict[str, type]] = None
_local_catalogue: Optional[MarketManager] = None


def get_market_classes() -> dict[str, type]:
    global _market_classes

    if _market_classes is None:
        _market_classes = {}
        plugins = get_plugins()

        for plugin in plugins:
            _market_classes.update(plugin.get_market_classes())

    return _market_classes


def get_local_catalogue() -> MarketManager:
    global _local_catalogue

    if _local_catalogue is None:
        manager_classes = get_market_classes()
        _local_catalogue = manager_classes['wirecloud'](None, 'local', MarketOptions(name='local', type='wirecloud'))

    return _local_catalogue


async def get_market_managers(db: DBSession, user: User) -> dict[str, MarketManager]:
    manager_classes = get_market_classes()

    managers = {}
    for market in await get_markets_for_user(db, user):
        user = await get_market_user(db, market)
        market_id = user.username + "/" + market.name

        if market.options.type in manager_classes:
            managers[market_id] = manager_classes[market.options.type](user.username, market.name, market.options)

    return managers
