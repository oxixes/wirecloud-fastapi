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
from typing import Any

from wirecloud.platform.context import docs
from wirecloud.platform.context.models import DBConstant

Constant = DBConstant


class BaseContextKey(BaseModel):
    description: str = Field(description=docs.context_key_description_description)
    label: str = Field(description=docs.context_key_label_description)


class PlatformContextKey(BaseContextKey):
    value: Any = Field(description=docs.platform_context_key_value_description)


class WorkspaceContextKey(BaseContextKey):
    pass


class Context(BaseModel):
    platform: dict[str, PlatformContextKey] = Field(description=docs.context_platform_description)
    workspace: dict[str, WorkspaceContextKey] = Field(description=docs.context_workspace_description)
