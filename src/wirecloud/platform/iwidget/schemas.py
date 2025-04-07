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


from typing import Any, Optional

from pydantic import BaseModel

from src.wirecloud.catalogue.crud import get_catalogue_resource_by_id
from src.wirecloud.commons.auth.schemas import User
from src.wirecloud.database import DBSession
from src.wirecloud.platform.iwidget.models import DBWidgetPositions, DBWidgetInstance, DBWidgetConfig, \
    DBWidgetVariables, DBWidgetConfigAnchor, DBWidgetPermissions, DBWidgetPositionsConfig, DBWidgetPermissionsConfig


WidgetPositions = DBWidgetPositions
WidgetPositionsConfig = DBWidgetPositionsConfig
WidgetConfig = DBWidgetConfig
WidgetVariables = DBWidgetVariables
WidgetAnchor = DBWidgetConfigAnchor
WidgetPermissions = DBWidgetPermissions
WidgetPermissionsConfig = DBWidgetPermissionsConfig


class LayoutConfig(WidgetConfig):
    action: Optional[str] = None


class IWidgetDataCreate(BaseModel):
    title: str
    layout: int = 0
    widget: str
    layout_config: list[LayoutConfig] = []
    icon_left: int = 0
    icon_top: int = 0
    read_only: bool = False
    permissions: WidgetPermissions = WidgetPermissions()
    variable_values: Optional[dict[str, WidgetVariables]] = None

class IwidgetDataPreference(BaseModel):
    name: str
    secure: bool
    readonly: bool
    hidden: bool
    value: Any


IwidgetDataProperty = IwidgetDataPreference


class IWidgetData(IWidgetDataCreate):
    id: str = ''
    preferences: dict[str, IwidgetDataPreference] = {}
    properties: dict[str, IwidgetDataProperty] = {}


class WidgetInstance(DBWidgetInstance):
    async def set_variable_value(self, db: DBSession, var_name: str, value: Any, user: User):
        resource = await get_catalogue_resource_by_id(db, self.resource)
        if resource is None:
            raise ValueError('Widget not found')

        iwidget_info = resource.get_processed_info(translate=False, process_variables=True)

        vardef = iwidget_info.variables.all[var_name]
        print(vardef)
        if vardef.secure:
            from src.wirecloud.platform.workspace.utils import encrypt_value
            value = encrypt_value(value)
        elif vardef.type == 'boolean':
            if isinstance(value, str):
                value = value.strip().lower() == 'true'
            else:
                value = bool(value)
        elif vardef.type == 'number':
            value = float(value)

        if "users" in self.variables.get(var_name, ""):
            self.variables[var_name].users = {"%s" % user.id: value}
        else:
            print(self.variables)
            self.variables[var_name] = WidgetVariables(users={str(user.id): value})
            print()
            print(self.variables)


class IWidgetDataUpdate(BaseModel):
    id: Optional[int] = None
    tab: Optional[int] = None
    layout: Optional[int] = None
    layout_config: Optional[list[LayoutConfig]] = None
    title: Optional[str] = None
    widget: Optional[str] = None
    move: Optional[bool] = None