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

from http.cookies import BaseCookie, SimpleCookie

from pydantic import BaseModel
from fastapi import Request
from typing_extensions import Optional

from src.wirecloud.commons.auth.schemas import User


class ProxyRequestData(BaseModel, arbitrary_types_allowed=True):
    workspace: Optional[str]
    component_type: Optional[str]
    component_id: Optional[str]
    headers: dict[str, str] = {}
    data: Optional[bytes] = None
    method: str = "GET"
    url: Optional[str] = None
    original_request: Optional[Request] = None
    cookies: BaseCookie = SimpleCookie()
    user: Optional[User] = None