# -*- coding: utf-8 -*-

# Copyright (c) 2012-2016 CoNWeT Lab., Universidad Politécnica de Madrid

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


from pydantic import BaseModel, Field, field_serializer, model_serializer
from typing import Annotated, Any, Optional
from enum import Enum

from src.wirecloud.database import Id


class DBWidgetConfigAnchor(Enum):
    top_left = "top-left"
    top_center = "top-center"
    top_right = "top-right"
    bottom_left = "bottom-left"
    bottom_center = "bottom-center"
    bottom_right = "bottom-right"


class DBWidgetConfig(BaseModel, use_enum_values=True):
    id: int = 0
    top: Annotated[float, Field(ge=0)] = 0
    left: Annotated[float, Field(ge=0)] = 0
    zIndex: Annotated[int, Field(ge=0)] = 0
    height: Annotated[float, Field(ge=0)] = 1
    width: Annotated[float, Field(ge=0)] = 1
    minimized: bool = False
    titlevisible: bool = True
    fulldragboard: bool = False
    relx: bool = True
    rely: bool = False
    relwidth: bool = True
    relheight: bool = False
    anchor: DBWidgetConfigAnchor = DBWidgetConfigAnchor.top_left
    moreOrEqual: int = 0
    lessOrEqual: int = -1

    @field_serializer("anchor")
    def serialize_enum(self, value, _info) -> str:
        if isinstance(value, DBWidgetConfigAnchor):
            return value.value
        return value


class DBWidgetPositionsConfig(BaseModel):
    id: int
    moreOrEqual: Annotated[int, Field(ge=0)]
    lessOrEqual: Annotated[int, Field(ge=-1)]
    widget: DBWidgetConfig = DBWidgetConfig()


class DBWidgetPositions(BaseModel):
    configurations: list[DBWidgetPositionsConfig]


class DBWidgetPermissionsConfig(BaseModel):
    close: Optional[bool] = None
    configure: Optional[bool] = None
    move: Optional[bool] = None
    rename: Optional[bool] = None
    resize: Optional[bool] = None
    minimize: Optional[bool] = None
    upgrade: Optional[bool] = None

    def filtered_dict(self):
        return {k: v for k, v in self.model_dump().items() if v is not None}


class DBWidgetPermissions(BaseModel):
    editor: Optional[DBWidgetPermissionsConfig] = None
    viewer: Optional[DBWidgetPermissionsConfig] = {}

    @model_serializer()
    def serialize(self):
        return {
            "editor": self.editor.filtered_dict() if self.editor else {},
            "viewer": self.viewer.filtered_dict() if self.viewer else {}
        }



class DBWidgetVariables(BaseModel):
    users: dict[str, Any] = {}


class DBWidgetInstance(BaseModel):
    id: str
    resource: Id = None
    widget_uri: str = ''
    name: str = ''
    layout: int = 0
    positions: DBWidgetPositions = {}
    read_only: bool = False
    variables: dict[str, DBWidgetVariables] = {}
    permissions: DBWidgetPermissions = DBWidgetPermissions()