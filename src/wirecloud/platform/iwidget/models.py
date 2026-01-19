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

from pydantic import BaseModel, Field, field_serializer, model_serializer, model_validator
from typing import Annotated, Any, Optional
from enum import Enum

from src.wirecloud.catalogue.crud import get_catalogue_resource_by_id
from src.wirecloud.commons.auth.schemas import User
from src.wirecloud.database import Id, DBSession


class WidgetConfigAnchor(Enum):
    top_left = "top-left"
    top_center = "top-center"
    top_right = "top-right"
    bottom_left = "bottom-left"
    bottom_center = "bottom-center"
    bottom_right = "bottom-right"


class WidgetConfig(BaseModel, use_enum_values=True):
    id: int = 0
    top: Annotated[Optional[float], Field(ge=0)] = None
    left: Annotated[Optional[float], Field(ge=0)] = None
    zIndex: Annotated[Optional[int], Field(ge=0)] = None
    height: Annotated[Optional[float], Field(ge=0)] = None
    width: Annotated[Optional[float], Field(ge=0)] = None
    minimized: Optional[bool] = None
    titlevisible: Optional[bool] = None
    fulldragboard: Optional[bool] = None
    relx: Optional[bool] = None
    rely: Optional[bool] = None
    relwidth: Optional[bool] = None
    relheight: Optional[bool] = None
    anchor: Optional[WidgetConfigAnchor] = None
    moreOrEqual: Optional[int] = None
    lessOrEqual: Optional[int] = None

    @field_serializer("anchor")
    def serialize_enum(self, value, _info) -> str:
        if isinstance(value, WidgetConfigAnchor):
            return value.value
        return value


class WidgetPositionsConfig(BaseModel):
    id: int
    moreOrEqual: Annotated[int, Field(ge=0)]
    lessOrEqual: Annotated[int, Field(ge=-1)]
    widget: WidgetConfig = WidgetConfig()

    @model_validator(mode='after')
    def set_widget_bounds(self):
        self.widget.moreOrEqual = self.moreOrEqual
        self.widget.lessOrEqual = self.lessOrEqual
        return self


class WidgetPositions(BaseModel):
    configurations: list[WidgetPositionsConfig]


class WidgetPermissionsConfig(BaseModel):
    close: Optional[bool] = None
    configure: Optional[bool] = None
    move: Optional[bool] = None
    rename: Optional[bool] = None
    resize: Optional[bool] = None
    minimize: Optional[bool] = None
    upgrade: Optional[bool] = None

    def filtered_dict(self):
        return {k: v for k, v in self.model_dump().items() if v is not None}


class WidgetPermissions(BaseModel):
    editor: Optional[WidgetPermissionsConfig] = None
    viewer: Optional[WidgetPermissionsConfig] = {}

    @model_serializer()
    def serialize(self):
        return {
            "editor": self.editor.filtered_dict() if self.editor else {},
            "viewer": self.viewer.filtered_dict() if self.viewer else {}
        }



class WidgetVariables(BaseModel):
    users: dict[str, Any] = {}


class WidgetInstance(BaseModel):
    id: str
    resource: Id = None
    widget_uri: str = ''
    title: str = ''
    layout: int = 0
    positions: WidgetPositions = {}
    read_only: bool = False
    variables: dict[str, WidgetVariables] = {}
    permissions: WidgetPermissions = WidgetPermissions()

    async def set_variable_value(self, db: DBSession, var_name: str, value: Any, user: User):
        resource = await get_catalogue_resource_by_id(db, self.resource)
        if resource is None:
            raise ValueError('Widget not found')

        iwidget_info = resource.get_processed_info(translate=False, process_variables=True)

        vardef = iwidget_info.variables.all[var_name]
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
            self.variables[var_name] = WidgetVariables(users={str(user.id): value})