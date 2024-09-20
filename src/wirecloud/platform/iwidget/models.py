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


from pydantic import BaseModel, Field, StringConstraints
from typing import Annotated, Any
from enum import Enum


Id = str
IntegerStr = Annotated[str, StringConstraints(pattern=r'^\d+$')]


class DBWidgetConfigAnchor(Enum):
    top_left = "top-left"
    top_center = "top-center"
    top_right = "top-right"
    bottom_left = "bottom-left"
    bottom_center = "bottom-center"
    bottom_right = "bottom-right"


class DBWidgetConfig(BaseModel):
    top: Annotated[float, Field(ge=0)]
    left: Annotated[float, Field(ge=0)]
    zIndex: Annotated[int, Field(ge=0)]
    height: Annotated[float, Field(ge=0)]
    width: Annotated[float, Field(ge=0)]
    minimized: bool
    titlevisible: bool
    fulldragboard: bool
    relx: bool
    rely: bool
    relwidth: bool
    relheight: bool
    anchor: DBWidgetConfigAnchor


class DBWidgetPositions(BaseModel):
    id: int
    moreOrEqual: Annotated[int, Field(ge=0)]
    lessOrEqual: Annotated[int, Field(ge=-1)]
    widget: DBWidgetConfig


class DBWidgetPermissionsConfig(BaseModel):
    close: bool
    configure: bool
    move: bool
    rename: bool
    resize: bool
    minimize: bool
    upgrade: bool


class DBWidgetPermissions(BaseModel):
    editor: DBWidgetPermissionsConfig = {}
    viewer: DBWidgetPermissionsConfig = {}


class DBWidgetVariables(BaseModel):
    users: dict[IntegerStr, Any] = {}


class DBWidget(BaseModel):
    widget_uri: str
    name: str
    layout: int
    positions: DBWidgetPositions
    read_only: bool
    variables: dict[str, DBWidgetVariables] = {}
    widget_id: Id
    permissions: DBWidgetPermissions = {}
