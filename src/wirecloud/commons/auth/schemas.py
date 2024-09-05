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
from typing import Optional
from enum import Enum
from src.wirecloud import docs
from datetime import datetime


class Permission(BaseModel):
    codename: str = Field(description=docs.permission_codename_description, min_length=1, max_length=255)


class Group(BaseModel):
    id: int = Field(description=docs.group_id_description)
    name: str = Field(description=docs.group_name_description, min_length=1, max_length=150)


class UserBase(BaseModel):
    username: str = Field(description=docs.user_username_description, min_length=1, max_length=150)


class UserLogin(UserBase):
    password: str = Field(description=docs.user_login_password_description, min_length=1)


class User(UserBase):
    id: int = Field(description=docs.user_id_description)
    email: str = Field(description=docs.user_email_description)
    first_name: str = Field(description=docs.user_first_name_description, max_length=30)
    last_name: str = Field(description=docs.user_last_name_description, max_length=150)
    is_superuser: bool = Field(description=docs.user_is_superuser_description)
    is_staff: bool = Field(description=docs.user_is_staff_description)
    is_active: bool = Field(description=docs.user_is_active_description)
    date_joined: datetime = Field(description=docs.user_date_joined_description)
    last_login: Optional[datetime] = Field(description=docs.user_last_login_description, default=None)

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()


class UserWithPassword(User):
    password: str = Field(description=docs.user_login_password_description, min_length=1)


class UserAll(User):
    groups: list[Group] = Field(default=[])
    permissions: list[Permission] = Field(default=[])


class Session(BaseModel):
    real_user: Optional[str] = Field(default=None)
    real_fullname: Optional[str] = Field(default=None)


class UserTokenType(str, Enum):
    bearer = 'bearer'


class UserToken(BaseModel):
    access_token: str = Field(description=docs.user_token_token_description)
    token_type: UserTokenType = Field(description=docs.user_token_token_type_description)
