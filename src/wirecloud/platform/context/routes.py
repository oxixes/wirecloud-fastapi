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

from fastapi import APIRouter
from typing import Optional

from src.wirecloud.platform.context.schemas import Context
from src.wirecloud.platform.context.utils import get_platform_context, get_workspace_context_definitions
from src.wirecloud.commons.auth.utils import UserDep, SessionDep

router = APIRouter()


@router.get("/", response_model=Context)
async def get_context(user: UserDep, session: SessionDep, theme: Optional[str] = None):
    # TODO Provide user and session
    context = Context(
        platform=get_platform_context(user=user, session=session),
        workspace=get_workspace_context_definitions()
    )

    if theme:
        context.platform['theme'].value = theme

    return context
