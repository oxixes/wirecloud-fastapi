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


import json
from typing import Any

from src.wirecloud.platform.plugins import get_workspace_preferences, get_tab_preferences
from src.wirecloud.platform.preferences.schemas import WorkspacePreference
from src.wirecloud.platform.workspace.models import DBWorkspacePreference
from src.wirecloud.platform.workspace.schemas import Workspace, Tab
from src.settings import cache

def make_workspace_preferences_cache_key(workspace: Workspace):
    return f'_workspace_preferences_cache/{workspace.id}/{workspace.last_modified}'

def make_tab_preferences_cache_key(tab: Tab):
    return f'_tab_preferences_cache/{tab.id}/{tab.last_modified}'


def parse_inheritable_values(values: list[DBWorkspacePreference]) -> dict[str, WorkspacePreference]:
    result = {}
    for value in values:
        result[value.name] = WorkspacePreference(
            inherit=value.inherit,
            value=value.value
        )

    return result


def serialize_default_value(value: Any) -> str:
    if isinstance(value, str):
        return value
    else:
        return json.dumps(value)


async def get_workspace_preference_values(workspace: Workspace) -> dict[str, WorkspacePreference]:
    cache_key = make_workspace_preferences_cache_key(workspace)
    values = await cache.get(cache_key)
    if values is None:
        values = parse_inheritable_values(workspace.preferences)
        for preference in get_workspace_preferences():
            if preference.name not in values:
                values[preference.name] = WorkspacePreference(
                    inherit=preference.inheritByDefault,
                    value=serialize_default_value(preference.defaultValue)
                )

        await cache.set(cache_key, values)

    return values


async def get_tab_preference_values(tab: Tab) -> dict[str, WorkspacePreference]:
    cache_key = make_tab_preferences_cache_key(tab)
    values = await cache.get(cache_key)
    if values is None:
        values = parse_inheritable_values(tab.preferences)
        for preference in get_tab_preferences():
            if preference.name not in values:
                values[preference.name] = WorkspacePreference(
                    inherit=preference.inheritByDefault,
                    value=serialize_default_value(preference.defaultValue)
                )

        await cache.set(cache_key, values)

    return values
