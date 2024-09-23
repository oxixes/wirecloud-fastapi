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

from src.wirecloud.commons.utils.template.schemas.macdschemas import MACD


Id = str


class DBXhtml(BaseModel):
    uri: str
    code: str
    code_timestamp: Optional[datetime]
    url: str
    content_type: Optional[str]
    use_platform_style: bool
    cacheable: bool


class DBCatalogueResource(BaseModel, populate_by_name=True):
    id: Id = Field(alias="_id")
    vendor: str
    short_name: str
    version: str
    type: int
    public: bool
    creation_date: datetime
    template_uri: str
    popularity: float
    json_description: MACD
    creator_id: Id

    xhtml: list[DBXhtml] = []
    users: list[Id] = []
    groups: list[Id] = []
