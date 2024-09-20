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
from typing import Optional, Annotated, Any
from datetime import datetime

from wirecloud.platform.iwidget.models import DBWidget
from wirecloud.platform.wiring.schemas import Wiring


# Class to handle ObjectId from mongodb, allow pydantic to convert ObjectId to string
'''
class Id(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(type="string")
'''


Id = str
IntegerStr = Annotated[str, StringConstraints(pattern=r'^\d+$')]


class DBWorkspaceAccessPermissions(BaseModel):
    id: Id
    accesslevel: int


class DBTab(BaseModel, populate_by_name=True):
    id: Optional[Id] = Field(alias="_id")
    name: str
    title: str
    visible: bool
    position: Optional[int]
    widgets: Optional[list[DBWidget]] = []


class DBWorkspaceExtraPreference(BaseModel):
    name: str
    inheritable: bool
    label: str
    type: str
    description: str
    required: bool


class DBWorkspaceForcedValue(BaseModel):
    value: Any
    hidden: bool


class DBWorkspaceForcedValues(BaseModel):
    extra_prefs: list[DBWorkspaceExtraPreference] = []
    operator: dict[IntegerStr, dict[str, DBWorkspaceForcedValue]] = []
    widget: dict[IntegerStr, dict[str, DBWorkspaceForcedValue]] = []


class DBWorkspace(BaseModel, populate_by_name=True):
    id: Id = Field(alias="_id")
    name: str
    title: str
    creation_date: datetime
    last_modified: Optional[datetime]
    searchable: bool
    public: bool
    description: str
    longdescription: str
    forced_values: DBWorkspaceForcedValues
    wiring_status: Wiring
    requireauth: bool

    # Relationships
    users: list[DBWorkspaceAccessPermissions] = []
    groups: list[DBWorkspaceAccessPermissions] = []
    tabs: list[DBTab] = []
