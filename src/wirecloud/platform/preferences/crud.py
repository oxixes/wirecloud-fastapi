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

from typing import Union

from wirecloud.settings import cache
from wirecloud.commons.auth.crud import get_user_preferences, set_user_preferences
from wirecloud.commons.auth.schemas import User
from wirecloud.database import DBSession, commit
from wirecloud.platform.preferences.schemas import PlatformPreferenceCreate, WorkspacePreference, TabPreference, \
    WorkspacePreferenceWithName
from wirecloud.commons.auth.models import DBPlatformPreference as PlatformPreferenceModel
from wirecloud.platform.preferences.utils import make_workspace_preferences_cache_key, \
    make_tab_preferences_cache_key
from wirecloud.platform.workspace.crud import change_workspace
from wirecloud.platform.workspace.models import DBTabPreference, Workspace, Tab


async def update_preferences(db: DBSession, user: User, preferences: PlatformPreferenceCreate):
    new_preferences = []
    current_preferences = {pref.name: pref for pref in await get_user_preferences(db, user.id)}
    modified_prefs = set()
    for name in preferences.preferences.keys():
        preference_data = preferences.preferences[name]

        if name in current_preferences:
            preference = current_preferences[name]
        else:
            preference = PlatformPreferenceModel(
                name=name
            )
        if type(preference_data) == str:
            new_value = preference_data
        else:
            new_value = preference_data.value

        if preference.value != new_value:
            preference.value = new_value

        new_preferences.append(preference)
        modified_prefs.add(name)

    for name in current_preferences.keys():
        if name not in modified_prefs:
            new_preferences.append(current_preferences[name])

    await set_user_preferences(db, user.id, new_preferences)

    await commit(db)


async def update_workspace_preferences(db: DBSession, user: User, workspace: Workspace,
                                       preferences: dict[str, Union[str, WorkspacePreference]],
                                       invalidate_cache: bool = True) -> None:

    changes = False
    current_preferences = {}
    for current_preference in workspace.preferences:
        current_preferences[current_preference.name] = current_preference

    for name in preferences.keys():
        preference_data = preferences[name]
        pref_changes = False

        if name in current_preferences:
            preference = current_preferences[name]
        else:
            preference = WorkspacePreferenceWithName(
                name=name
            )
            changes = pref_changes = True

        if isinstance(preference_data, WorkspacePreference):
            if preference_data.value is not None and preference.value != preference_data.value:
                preference.value = preference_data.value
                changes = pref_changes = True

            if preference_data.inherit is not None and preference.inherit != preference_data.inherit:
                preference.inherit = preference_data.inherit
                changes = pref_changes = True
        else:
            if preference.value != preference_data:
                preference.value = preference_data
                changes = pref_changes = True

            if preference.inherit:
                preference.inherit = False
                changes = pref_changes = True

        if pref_changes and name in current_preferences:
            current_preferences[name].value = preference.value
            current_preferences[name].inherit = preference.inherit
        elif pref_changes:
            workspace.preferences.append(preference)

    await change_workspace(db, workspace, user)
    if invalidate_cache and changes:
        cache_key = make_workspace_preferences_cache_key(workspace)
        await cache.delete(cache_key)
        await change_workspace(db, workspace, user)
        await commit(db)


async def update_tab_preferences(db: DBSession, user: User, workspace: Workspace, tab: Tab,
                                 preferences: dict[str, Union[str, TabPreference]]):
    changes = False
    current_preferences = {}
    for current_preference in tab.preferences:
        current_preferences[current_preference.name] = current_preference

    for name in preferences.keys():
        preference_data = preferences[name]
        pref_changes = False

        if name in current_preferences:
            preference = current_preferences[name]
        else:
            preference = DBTabPreference(
                name=name
            )
            changes = pref_changes = True

        if isinstance(preference_data, TabPreference):
            if preference_data.value is not None and preference.value != preference_data.value:
                preference.value = preference_data.value
                changes = pref_changes = True

            if preference_data.inherit is not None and preference.inherit != preference_data.inherit:
                preference.inherit = preference_data.inherit
                changes = pref_changes = True
        else:
            if preference.value != preference_data:
                preference.value = preference_data
                changes = pref_changes = True

            if preference.inherit:
                preference.inherit = False
                changes = pref_changes = True

        if pref_changes:
            if name in current_preferences:
                current_preferences[name].value = preference.value
                current_preferences[name].inherit = preference.inherit
            else:
                workspace.tabs[tab.id].preferences.append(preference)

    if changes:
        cache_key = make_tab_preferences_cache_key(tab)
        await cache.delete(cache_key)
        await change_workspace(db, workspace, user)
        await commit(db)
