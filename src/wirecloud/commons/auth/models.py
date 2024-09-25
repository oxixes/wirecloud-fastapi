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


from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

from src.wirecloud.database import Id


class DBPermission(BaseModel):
    codename: str


class DBUser(BaseModel, populate_by_name=True):
    id: Id = Field(alias="_id")
    password: Optional[str]
    last_login: Optional[datetime]
    is_superuser: bool
    username: str
    first_name: str
    last_name: str
    email: str
    is_staff: bool
    is_active: bool
    date_joined: datetime

    user_permissions: list[DBPermission] = []
    groups: list[Id] = []


class DBGroup(BaseModel, populate_by_name=True):
    id: Id = Field(alias="_id")
    name: str
    codename: str

    group_permissions: list[DBPermission] = []
    users: list[Id] = []
