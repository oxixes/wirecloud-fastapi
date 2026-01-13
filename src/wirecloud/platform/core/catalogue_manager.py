# -*- coding: utf-8 -*-

# Copyright (c) 2012-2017 CoNWeT Lab., Universidad Politécnica de Madrid
# Copyright (c) 2019-2021 Future Internet Consulting and Development Solutions S.L.

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

from fastapi import Request
from typing import Optional

from src.wirecloud.catalogue.search import add_resource_to_index
from src.wirecloud.commons.utils.wgt import WgtFile
from src.wirecloud.commons.utils.template.schemas.macdschemas import MACD
from src.wirecloud.commons.auth.schemas import User
from src.wirecloud.platform.localcatalogue.utils import install_component
from src.wirecloud.platform.markets.utils import MarketManager
from src.wirecloud.platform.markets.schemas import MarketOptions, MarketEndpoint
from src.wirecloud.database import DBSession
from src.wirecloud.translation import gettext as _


class WirecloudCatalogueManager(MarketManager):
    _user: str = None
    _name: str = None
    _options: MarketOptions = None

    def __init__(self, user: Optional[str], name: str, options: MarketOptions):
        super().__init__(user, name, options)
        self._user = user
        self._name = name
        self._options = options

    # TODO Type of endpoint
    async def publish(self, db: DBSession, endpoint: Optional[MarketEndpoint], wgt_file: WgtFile, user: User,
                      request: Request = None, template: Optional[MACD] = None):
        if self._name == 'local':
            added, resource = await install_component(db, wgt_file, users=[user])
            if not added:
                raise Exception(_('Resource already exists %(resource_id)s') % {'resource_id': resource.local_uri_part})

            await add_resource_to_index(db, resource)

            return resource
        else:
            raise Exception('TODO')
