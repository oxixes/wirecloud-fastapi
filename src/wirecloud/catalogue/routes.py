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

from fastapi import APIRouter, Path

from src.wirecloud.database import DBDep
from src.wirecloud.commons.auth.utils import UserDep
from src.wirecloud.commons.utils.template.schemas.macdschemas import Vendor, Name, Version
from src.wirecloud.catalogue import docs
from src.wirecloud.catalogue.schemas import CatalogueResourceDataSummaryGroup

router = APIRouter()


@router.get(
    "/resource/{vendor}/{name}",
    summary=docs.get_resource_entry_group_summary,
    description=docs.get_resource_entry_group_description,
    response_model=CatalogueResourceDataSummaryGroup,
    response_description=docs.get_resource_entry_group_response_description,
)
async def get_resource_versions(db: DBDep,
                                user: UserDep,
                                vendor: Vendor = Path(description=docs.get_resource_entry_group_vendor_description),
                                name: Name = Path(description=docs.get_resource_entry_group_name_description)):
    pass
