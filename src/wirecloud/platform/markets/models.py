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

from pydantic import BaseModel, Field
from typing import Optional
from wirecloud.database import Id
from wirecloud.platform.markets import docs


class MarketOptions(BaseModel):
    name: str = Field(description=docs.market_options_name_description)
    type: str = Field(description=docs.market_options_type_description)
    title: Optional[str] = Field(None, description=docs.market_options_title_description)
    url: Optional[str] = Field(None, description=docs.market_options_url_description)
    public: Optional[bool] = Field(None, description=docs.market_options_public_description)
    user: Optional[str] = Field(None, description=docs.market_options_user_description)


class DBMarket(BaseModel, populate_by_name=True):
    id: Id = Field(alias="_id")
    name: str
    public: bool
    options: MarketOptions
    user_id: Id
