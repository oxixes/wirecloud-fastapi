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


import base64
import json
from copy import deepcopy
from typing import Any, Union, Optional
from fastapi import Request, Response

import markdown
from Crypto.Cipher import AES

from src.wirecloud.catalogue.crud import get_catalogue_resource_by_id, get_catalogue_resource
from src.wirecloud.catalogue.schemas import CatalogueResource
from src.wirecloud.commons.auth.crud import get_username_by_id, get_user_by_id, get_group_by_id
from src.wirecloud.commons.auth.utils import UserDep
from src.wirecloud.commons.utils.cache import CacheableData, check_if_modified_since, patch_cache_headers
from src.wirecloud.commons.utils.db import save_alternative_tab
from src.wirecloud.commons.utils.html import clean_html
from src.wirecloud.commons.utils.http import build_error_response
from src.wirecloud.commons.utils.template.parsers import TemplateValueProcessor
from src.wirecloud.commons.utils.template.schemas.macdschemas import MACDPreference, MACDProperty
from src.wirecloud.commons.utils.urlify import URLify
from src.wirecloud.database import DBSession, Id, DBDep
from src.wirecloud.platform.context.utils import get_context_values
from src.wirecloud.platform.iwidget.schemas import WidgetVariables, WidgetInstance, IWidgetData, WidgetConfig, \
    WidgetPermissions
from src.wirecloud.platform.iwidget.utils import parse_value_from_text, get_iwidgets_from_workspace
from src.wirecloud.platform.preferences.schemas import WorkspacePreference
from src.wirecloud.platform.preferences.utils import get_workspace_preference_values, get_tab_preference_values
from src.wirecloud.platform.workspace.schemas import WorkspaceData, Tab, CacheEntry, WorkspaceForcedValues, \
    UserWorkspaceData, GroupWorkspaceData, CacheVariableData, TabData, WorkspaceGlobalData
from src.wirecloud.commons.auth.schemas import User, UserAll
from src.wirecloud.platform.workspace.schemas import Workspace
from src.settings import cache, SECRET_KEY


def _variable_values_cache_key(workspace: Workspace, user: User) -> str:
    return f'_variables_values_cache/{workspace.id}/{workspace.last_modified}/{user.id}'


def _workspace_cache_key(workspace: Workspace, user: User) -> str:
    return f'_workspace_global_data/{workspace.id}/{workspace.last_modified}/{user.id}'


def encrypt_value(value: str) -> str:
    cipher = AES.new(SECRET_KEY[:32].encode("utf-8"), mode=AES.MODE_ECB)
    json_value = json.dumps(value, ensure_ascii=False).encode('utf8')
    padded_value = json_value + (cipher.block_size - len(json_value) % cipher.block_size) * b' '
    return base64.b64encode(cipher.encrypt(padded_value)).decode('utf-8')


def decrypt_value(value: str) -> str:
    cipher = AES.new(SECRET_KEY[:32].encode('utf-8'), AES.MODE_ECB)
    try:
        value = cipher.decrypt(base64.b64decode(value))
        return json.loads(value.decode('utf-8'))
    except Exception:
        return ''


def process_forced_values(workspace: Workspace, user: Id, concept_values: dict[str, dict[str, Any]],
                          preferences: dict[str, WorkspacePreference]) -> WorkspaceForcedValues:
    forced_values = deepcopy(workspace.forced_values)

    if len(forced_values.widget) == 0 and len(forced_values.operator) == 0:
        forced_values.empty_params = []
        return WorkspaceForcedValues(
            extra_prefs=forced_values.extra_prefs,
            ioperator=forced_values.operator,
            iwidget=forced_values.widget,
            empty_params=forced_values.empty_params
        )

    param_values = {}
    empty_params = []
    for param in forced_values.extra_prefs:
        if param.name in preferences and (not param.required or preferences[param.name].value.strip() != ''):
            param_values[param.name] = preferences[param.name].value
        else:
            empty_params.append(param.name)
            param_values[param.name] = ''
    forced_values.empty_params = empty_params

    processor = TemplateValueProcessor(
        user=user,
        context=concept_values,
        params=param_values
    )

    collection = forced_values.widget
    for key in collection:
        values = collection[key]
        for var_name in values:
            collection[key][var_name].value = processor.process(values[var_name].value)

    collection = forced_values.operator
    for key in collection:
        values = collection[key]
        for var_name in values:
            collection[key][var_name].value = processor.process(values[var_name].value)

    return WorkspaceForcedValues(
        extra_prefs=forced_values.extra_prefs,
        ioperator=forced_values.operator,
        iwidget=forced_values.widget,
        empty_params=forced_values.empty_params
    )


def _process_variable(component_type: str, component_id: str, vardef: Union[MACDPreference, MACDProperty],
                      value: Union[Any, WidgetVariables], forced_values: WorkspaceForcedValues,
                      values_by_varname: dict[str, dict], current_user: User, workspace_creator: User) -> None:
    varname = vardef.name
    entry = CacheEntry(
        type=vardef.type,
        secure=vardef.secure
    )

    if component_id in getattr(forced_values, component_type) and varname in getattr(forced_values, component_type)[
        component_id]:
        fv_entry = getattr(forced_values, component_type)[component_id][varname]

        entry.value = fv_entry.value
        if vardef.secure:
            entry.value = encrypt_value(entry.value)
        else:
            entry.value = parse_value_from_text(entry.model_dump(), entry.value)

        entry.readonly = True
        entry.hidden = fv_entry.hidden

    else:
        # Handle multiuser variables
        variable_user = current_user if vardef.multiuser else workspace_creator
        if value is None or value.users.get(str(variable_user.id), None) is None:
            value = parse_value_from_text(entry.model_dump(), vardef.default)
        else:
            value = value.users.get(str(variable_user.id), None)

        entry.value = value
        entry.readonly = False
        entry.hidden = False

    values_by_varname[component_type][component_id][varname] = entry


async def _populate_variables_values_cache(db: DBSession, workspace: Workspace, request: Request, user: UserAll,
                                           key: Any, forced_values=None):
    values_by_varname = {
        "ioperator": {},
        "iwidget": {}
    }
    if forced_values is None:
        context_values = await get_context_values(db, workspace, request, user)
        preferences = await get_workspace_preference_values(workspace)
        forced_values = process_forced_values(workspace, user.id, context_values, preferences)

    for iwidget in await get_iwidgets_from_workspace(workspace):
        svariwidget = str(iwidget.id)
        values_by_varname["iwidget"][svariwidget] = {}

        # if iwidget.widget is None: continue TODO check this

        resource = await get_catalogue_resource_by_id(db, iwidget.resource)
        iwidget_info = resource.get_processed_info()

        for vardef in iwidget_info.preferences:
            value = iwidget.variables.get(vardef.name, None)
            _process_variable("iwidget", svariwidget, vardef, value, forced_values, values_by_varname, user,
                              await get_user_by_id(db, workspace.creator))

        for vardef in iwidget_info.properties:
            value = iwidget.variables.get(vardef.name, None)
            _process_variable("iwidget", svariwidget, vardef, value, forced_values, values_by_varname, user,
                              await get_user_by_id(db, workspace.creator))

    for operator_id, operator in workspace.wiring_status.operators.items():
        values_by_varname["ioperator"][operator_id] = {}
        vendor, name, version = operator.name.split('/')

        resource = await get_catalogue_resource(db, vendor, name, version)
        if resource is None:
            continue
        operator_info = resource.get_processed_info()
        for vardef in operator_info.preferences:
            value = operator.preferences[vardef.name].value
            _process_variable("ioperator", operator_id, vardef, value, forced_values, values_by_varname, user,
                              await get_user_by_id(db, workspace.creator))

        for vardef in operator_info.properties:
            value = operator.properties[vardef.name].value
            _process_variable("ioperator", operator_id, vardef, value, forced_values, values_by_varname, user,
                              await get_user_by_id(db, workspace.creator))

    await cache.set(key, values_by_varname)

    return values_by_varname


class VariableValueCacheManager:
    workspace: Workspace = None
    user: UserAll = None
    values = None
    forced_values = None

    def __init__(self, workspace, user, forced_values=None):
        self.workspace = workspace
        self.user = user
        self.forced_values = forced_values

    def _process_entry(self, entry: CacheEntry):
        if entry.secure:
            value = decrypt_value(entry.value)
            return parse_value_from_text(entry.model_dump(), value)  # TODO types of parameters are missing
        else:
            return entry.value

    async def get_variable_values(self, db: DBSession, request: Request):
        if self.values is None:
            key = _variable_values_cache_key(self.workspace, self.user)
            self.values = await cache.get(key)
            if self.values is None:
                self.values = await _populate_variables_values_cache(db, self.workspace, request, self.user, key,
                                                                     self.forced_values)

        return self.values

    async def get_variable_value_from_varname(self, db: DBSession, request: Request, component_type: str,
                                              component_id: str, var_name: str) -> str:
        values = await self.get_variable_values(db, request)
        entry = values[component_type][str(component_id)][var_name]
        return self._process_entry(entry)

    async def get_variable_data(self, db: DBSession, request: Request, component_type, component_id,
                                var_name) -> CacheVariableData:
        values = await self.get_variable_values(db, request)
        entry = values[component_type][str(component_id)][var_name]
        if entry.secure and entry.value != '':
            value = '********'
        else:
            value = entry.value

        return CacheVariableData(
            name=var_name,
            secure=entry.secure,
            readonly=entry.readonly,
            hidden=entry.hidden,
            value=value
        )


async def get_workspace_data(db: DBSession, workspace: Workspace, user: User) -> WorkspaceData:
    longdescription = workspace.longdescription
    if longdescription != '':
        longdescription = clean_html(markdown.markdown(longdescription, output_format='xhtml'))
    else:
        longdescription = workspace.description

    return WorkspaceData(
        id=str(workspace.id),
        name=workspace.name,
        title=workspace.title,
        public=workspace.public,
        shared=workspace.is_shared(),
        requireauth=workspace.requireauth,
        owner=await get_username_by_id(db, workspace.creator),
        removable=workspace.is_editable_by(user),
        lastmodified=workspace.last_modified,
        description=workspace.description,
        longdescription=longdescription,
    )


async def create_tab(db: DBSession, user: User, title: str, workspace: Workspace, name: str = None,
                     allow_renaming: bool = False) -> Tab:
    if name is None or name.strip() == '':
        name = URLify(title)

    visible = False
    from src.wirecloud.platform.workspace.crud import get_tabs_from_workspace
    tabs = await get_tabs_from_workspace(db, workspace)
    if len(tabs) == 0:
        visible = True

    # Creating tab
    tab = Tab(
        id=str(workspace.id) + '-' + str(len(tabs)),
        name=name,
        title=title,
        visible=visible
    )

    if allow_renaming:
        tab = await save_alternative_tab(db, tab)

    workspace.tabs.append(tab)
    from src.wirecloud.platform.workspace.crud import change_workspace
    await change_workspace(db, workspace, user)

    return tab


async def get_iwidget_data(db: DBSession, request: Request, iwidget: WidgetInstance, workspace: Workspace,
                           cache_manager: VariableValueCacheManager = None, user: UserAll = None) -> IWidgetData:

    data_ret = IWidgetData(
        id=iwidget.id,
        title=iwidget.name,
        layout=iwidget.layout,
        widget=iwidget.widget_uri,
        layout_config=[],
        read_only=iwidget.read_only,
        permissions=iwidget.permissions
    )

    for layout_configuration in iwidget.positions.configurations:
        widget_position = layout_configuration.widget
        data_layout = WidgetConfig(
            top=widget_position.top,
            left=widget_position.left,
            anchor=widget_position.anchor,
            relx=True if iwidget.layout != 1 else widget_position.relx,
            rely=True if iwidget.layout != 1 else widget_position.rely,
            relheight=True if iwidget.layout != 1 else widget_position.relheight,
            relwidth=True if iwidget.layout != 1 else widget_position.relwidth,
            zIndex=widget_position.zIndex,
            width=widget_position.width,
            height=widget_position.height,
            fulldragboard=widget_position.fulldragboard,
            minimized=widget_position.minimized,
            titlevisible=widget_position.titlevisible,
            id=widget_position.id,
            moreOrEqual=widget_position.moreOrEqual,
            lessOrEqual=widget_position.lessOrEqual
        )

        data_ret.layout_config.append(data_layout)

    resource = await get_catalogue_resource_by_id(db, iwidget.resource)
    if resource is None or not await resource.is_available_for(db, user):
        # The widget used by this iwidget is missing
        return data_ret

    if cache_manager is None:
        cache_manager = VariableValueCacheManager(workspace, user)

    iwidget_info = resource.get_processed_info()
    data_ret.preferences = {
        preference.name: await cache_manager.get_variable_data(db, request, "iwidget", iwidget.id, preference.name) for
        preference in iwidget_info.preferences}
    data_ret.properties = {
        proper.name: await cache_manager.get_variable_data(db, request, "iwidget", iwidget.id, proper.name) for proper
        in iwidget_info.properties}

    return data_ret


async def get_tab_data(db: DBSession, request: Request, tab: Tab, workspace: Workspace = None,
                       cache_manager: VariableValueCacheManager = None, user: User = None) -> TabData:
    if workspace is None:
        from src.wirecloud.platform.workspace.crud import get_workspace_by_id
        workspace = await get_workspace_by_id(db, Id(tab.id.split('-')[0]))

    if cache_manager is None:
        cache_manager = VariableValueCacheManager(workspace, user)

    return TabData(
        id=tab.id,
        name=tab.name,
        title=tab.title,
        visible=tab.visible,
        preferences=await get_tab_preference_values(tab),
        widgets=[
            await get_iwidget_data(db, request, WidgetInstance(**widget.model_dump()), workspace, cache_manager, user)
            for widget in tab.widgets]
    )


async def _get_global_workspace_data(db: DBSession, request: Request, workspaceDAO: Workspace,
                                     user: UserAll) -> WorkspaceGlobalData:
    workspace_data = await get_workspace_data(db, workspaceDAO, user)
    data_ret = WorkspaceGlobalData(**workspace_data.model_dump())

    # Workspace preferences
    preferences = await get_workspace_preference_values(workspaceDAO)
    data_ret.preferences = preferences

    if workspaceDAO.creator == user.id:
        for u in workspaceDAO.users:
            u_all = await get_user_by_id(db, u.id, user_all=True)
            # TODO: organization
            data_ret.users.append(UserWorkspaceData(
                fullname=u_all.get_full_name(),
                username=u_all.username,
                organization=False,  # TODO: check this
                accesslevel="owner" if u.id == workspaceDAO.creator else "read"
            ))

        for g in workspaceDAO.groups:
            # TODO: organization
            group = await get_group_by_id(db, g.id)
            data_ret.groups.append(GroupWorkspaceData(
                name=group.name,
                accesslevel="read"
            ))

    concept_values = await get_context_values(db, workspaceDAO, request, user)
    forced_values = process_forced_values(workspaceDAO, user.id, concept_values, preferences)
    data_ret.empty_params = forced_values.empty_params
    data_ret.extra_prefs = forced_values.extra_prefs
    if len(forced_values.empty_params) > 0:
        return data_ret

    cache_manager = VariableValueCacheManager(workspaceDAO, user, forced_values)

    # Tabs processing
    tabs = workspaceDAO.tabs
    if tabs.count == 0:
        tabs = [await create_tab(db, user, 'Tab', workspaceDAO)]  # TODO: translate this

    data_ret.tabs = [
        await get_tab_data(db, request, tab, workspace=workspaceDAO, cache_manager=cache_manager, user=user) for tab in
        tabs]
    data_ret.wiring = deepcopy(workspaceDAO.wiring_status)
    for operator_id, operator in data_ret.wiring.operators.items():
        try:
            (vendor, name, version) = operator.name.split('/')
        except ValueError:
            continue

        try:
            resource = await get_catalogue_resource(db, vendor, name, version)
            operator_info = resource.get_processed_info(process_variables=True)
            if not resource.is_available_for(db, await get_user_by_id(db, workspaceDAO.creator, user_all=True)):
                raise CatalogueResource.DoesNotExist
        except CatalogueResource.DoesNotExist:
            operator.preferences = {}
            operator.properties = {}
            continue

        operator_forced_values = forced_values.operator.get(operator_id, {})
        for preference_name, preference in operator.preferences.items():
            vardef = operator_info.variables.preferences.get(preference_name)
            value = preference.value

            variable_user = user if vardef is not None and vardef.multiuser else workspaceDAO.creator

            if preference_name in operator_forced_values:
                preference.value = operator_forced_values[preference_name].value
            elif value is None or value.users.get(str(variable_user), None) is None:
                preference.value = parse_value_from_text(vardef.model_dump(), vardef.default)
            else:
                preference.value = value.users.get(str(variable_user))

            if vardef is not None and vardef.secure:
                preference.value = '' if preference.value is None or decrypt_value(
                    preference.value) == '' else '********'

        for property_name, property in operator.properties.items():
            vardef = operator_info.variables.properties.get(property_name)
            value = property.value

            variable_user = user if vardef is not None and vardef.multiuser else workspaceDAO.creator

            if property_name in operator_forced_values:
                property.value = operator_forced_values[property_name].value
            elif value is None or value.users.get(str(variable_user), None) is None:
                property.value = parse_value_from_text(vardef.model_dump(), vardef.default)
            else:
                property.value = value.users.get(str(variable_user))

            if vardef is not None and vardef.secure:
                property.value = '' if property.value is None or decrypt_value(property.value) == '' else '********'

    return data_ret


async def get_global_workspace_data(db: DBSession, request: Request, workspace: Workspace,
                                    user: UserAll) -> CacheableData:
    key = _workspace_cache_key(workspace, user)
    data = await cache.get(key)
    if data is None:
        workspace_data = await _get_global_workspace_data(db, request, workspace, user)
        data = CacheableData(data=workspace_data, timestamp=workspace.last_modified)
        key = _workspace_cache_key(workspace, user)
        await cache.set(key, data)

    return data


async def get_workspace_entry(db: DBDep, user: UserDep, request: Request, workspace: Optional[Workspace]) -> Response:
    if workspace is None:
        return build_error_response(request, 404, "Workspace not found")

    if not await workspace.is_accsessible_by(db, user):
        return build_error_response(request, 403, "You don't have permission to access this workspace")

    last_modified = workspace.last_modified

    if not check_if_modified_since(request, last_modified):
        response = Response(status_code=304)
        patch_cache_headers(response, last_modified)
        return response

    workspace_data = await get_global_workspace_data(db, request, workspace, user)

    return workspace_data.get_response()
