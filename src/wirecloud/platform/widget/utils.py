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

from src.wirecloud.catalogue.crud import get_catalogues_with_regex
from src.wirecloud.catalogue.schemas import CatalogueResource
from src.wirecloud.commons.auth.schemas import UserAll
from src.wirecloud.commons.utils.template.schemas.macdschemas import Vendor, Name, Version
from src.wirecloud.database import DBSession
from src.wirecloud.platform.widget.crud import get_widget_from_resource
from src.wirecloud.platform.widget.schemas import Widget


async def get_or_add_widget_from_catalogue(db: DBSession, vendor: Vendor, name: Name, version: Version,
                                           user: UserAll) -> Optional[tuple[Widget, CatalogueResource]]:
    resource_list = await get_catalogues_with_regex(db, vendor, name, version)
    for resource in resource_list:
        if await resource.is_available_for(db, user):
            return await get_widget_from_resource(db, resource.id), resource

    return None
