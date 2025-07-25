# -*- coding: utf-8 -*-

# Copyright (c) 2013 CoNWeT Lab., Universidad Politécnica de Madrid

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

from typing import Optional, Any
from urllib.request import Request

from src.settings import cache
from src.wirecloud.platform.context.crud import get_all_constants
from src.wirecloud.platform.plugins import get_plugins
from src.wirecloud.platform.context.schemas import BaseContextKey, PlatformContextKey
from src.wirecloud.commons.auth.schemas import UserAll, Session
from src.wirecloud.database import DBSession

_wirecloud_platform_context_definitions: Optional[dict[str, BaseContextKey]] = None
_wirecloud_workspace_context_definitions: Optional[dict[str, BaseContextKey]] = None


# TODO Add type hints to these functions


def get_platform_context_definitions() -> dict[str, BaseContextKey]:
    global _wirecloud_platform_context_definitions

    if _wirecloud_platform_context_definitions is None:
        plugins = get_plugins()
        context = {}

        for plugin in plugins:
            context.update(plugin.get_platform_context_definitions())

        _wirecloud_platform_context_definitions = context

    return _wirecloud_platform_context_definitions


async def get_platform_context_current_values(db: DBSession, request: Request, user: Optional[UserAll], session: Optional[Session] = None) -> dict[str, Any]:
    plugins = get_plugins()
    values = {}

    for plugin in plugins:
        values.update(await plugin.get_platform_context_current_values(db, request, user, session=session))

    return values


async def get_platform_context(db: DBSession, request: Request, user: Optional[UserAll], session: Optional[Session] = None) -> dict[str, PlatformContextKey]:
    context = get_platform_context_definitions()
    values = await get_platform_context_current_values(db, request, user, session=session)
    result = {}
    for key in context:
        result[key] = PlatformContextKey(
            label=context[key].label,
            description=context[key].description,
            value=values.get(key, None)
        )

    return result


def get_workspace_context_definitions() -> dict[str, BaseContextKey]:
    global _wirecloud_workspace_context_definitions

    if _wirecloud_workspace_context_definitions is None:
        plugins = get_plugins()
        context = {}

        for plugin in plugins:
            context.update(plugin.get_workspace_context_definitions())

        _wirecloud_workspace_context_definitions = context

    return _wirecloud_workspace_context_definitions


def get_workspace_context_current_values(workspace, user):
    plugins = get_plugins()
    values = {}

    for plugin in plugins:
        values.update(plugin.get_workspace_context_current_values(workspace, user))

    return values


async def get_constant_context_values(db: DBSession) -> dict[str, str]:
    res = {}

    constants = await get_all_constants(db)
    for constant in constants:
        res[constant.concept] = constant.value

    return res


async def get_context_values(db: DBSession, workspace, request: Request, user: Optional[UserAll], session: Session = None) -> dict[str, dict[str, Any]]:
    cache_key = f'constant_context/{str(user.id) if user else "anonymous"}'
    constant_context = await cache.get(cache_key)
    if constant_context is None:
        constant_context = await get_constant_context_values(db)
        await cache.set(cache_key, constant_context)

    platform_context = constant_context
    platform_context.update(await get_platform_context_current_values(db, request, user, session=session))

    return {
        'platform': platform_context,
        'workspace': get_workspace_context_current_values(workspace, user),
    }
