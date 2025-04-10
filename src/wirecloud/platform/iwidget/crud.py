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


from bson import ObjectId

from src.wirecloud.catalogue.crud import get_catalogue_resource_by_id
from src.wirecloud.database import DBSession
from src.wirecloud.platform.iwidget.models import WidgetInstance
from src.wirecloud.platform.workspace.models import Tab


async def insert_widget_instance_into_tab(db: DBSession, tab: Tab, iwidget: WidgetInstance) -> None:
    if not db.in_transaction:
        db.start_transaction()

    if iwidget.resource is not None:
        resource = await get_catalogue_resource_by_id(db, iwidget.resource)
        iwidget.widget_uri = resource.local_uri_part

    tab.widgets.append(iwidget)
    (workspace_id, tab_position) = tab.id.split('-')
    await db.client.workspace.update_one(
        {
            "_id": ObjectId(workspace_id),
            f"tabs.{tab_position}": {"$exists": True},
        },
        {
            "$push": {f"tabs.{tab_position}.widgets": iwidget.model_dump()}
        }

    )