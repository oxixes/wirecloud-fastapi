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


from typing import Any

from src.wirecloud.database import DBSession, Id
from src.wirecloud.platform.workspace.models import Tab
from src.wirecloud.platform.workspace.utils import is_there_a_tab_with_that_name


async def save_alternative(db: DBSession, collection: str, variant_field: str, instance: Any) -> None:
    db_collection = db.client[collection]

    index = 1
    field = getattr(instance, variant_field)
    new_field = field
    while (await db_collection.find_one({variant_field: new_field})) is not None:
        index += 1
        new_field = f'{field}-{index}'

    setattr(instance, variant_field, new_field)
    await db_collection.insert_one(instance.model_dump(by_alias=True))


async def save_alternative_tab(db: DBSession, tab: Tab) -> Tab:
    workspace_id = tab.id.split('-')[0]
    from src.wirecloud.platform.workspace.crud import get_workspace_by_id
    workspace = await get_workspace_by_id(db, Id(workspace_id))
    if workspace is None:
        raise ValueError('Workspace not found')
    index = 1
    new_tab_name = tab.name
    while is_there_a_tab_with_that_name(new_tab_name, workspace.tabs):
        index += 1
        new_tab_name = f'{tab.name}-{index}'
    tab.name = new_tab_name
    return tab