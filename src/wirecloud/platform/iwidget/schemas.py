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

from typing import Any, Optional

from pydantic import BaseModel

from wirecloud.platform.iwidget.models import WidgetPermissions, WidgetConfig, WidgetVariables


class LayoutConfig(WidgetConfig):
    action: Optional[str] = None


class WidgetInstanceDataCreate(BaseModel):
    title: str
    layout: int = 0
    widget: str
    layoutConfig: list[LayoutConfig] = []
    icon_left: int = 0
    icon_top: int = 0
    read_only: bool = False
    permissions: WidgetPermissions = WidgetPermissions()
    variable_values: Optional[dict[str, WidgetVariables]] = None

class WidgetInstanceDataPreference(BaseModel):
    name: str
    secure: bool
    readonly: bool
    hidden: bool
    value: Any


WidgetInstanceDataProperty = WidgetInstanceDataPreference


class WidgetInstanceData(WidgetInstanceDataCreate):
    id: str = ''
    preferences: dict[str, WidgetInstanceDataPreference] = {}
    properties: dict[str, WidgetInstanceDataProperty] = {}


class WidgetInstanceDataUpdate(BaseModel):
    id: Optional[str] = None
    tab: Optional[str] = None
    layout: Optional[int] = None
    layoutConfig: Optional[list[LayoutConfig]] = None
    title: Optional[str] = None
    widget: Optional[str] = None
    move: Optional[bool] = None