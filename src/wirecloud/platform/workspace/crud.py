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

from datetime import timezone, datetime
from urllib.request import Request

from bson import ObjectId
from typing import Optional, Union
import os
from io import BytesIO

from wirecloud.settings import cache
from wirecloud.catalogue import utils as catalogue
from wirecloud.catalogue.crud import get_catalogue_resource, get_catalogue_resource_by_id
from wirecloud.commons.auth.crud import get_user_by_username, get_all_user_groups
from wirecloud.commons.utils.db import save_alternative
from wirecloud.commons.utils.downloader import download_http_content
from wirecloud.commons.utils.template import TemplateParser
from wirecloud.commons.utils.template.schemas.macdschemas import MACDMashupWithParametrization, MACType
from wirecloud.commons.utils.urlify import URLify
from wirecloud.commons.utils.wgt import WgtFile
from wirecloud.database import DBSession, Id
from wirecloud.commons.auth.schemas import User, UserAll
from wirecloud.platform.localcatalogue.utils import install_component
from wirecloud.platform.preferences.schemas import WorkspacePreference
from wirecloud.commons.auth.models import Group as GroupModel, Group
from wirecloud.platform.search import delete_workspace_from_index, update_workspace_in_index
from wirecloud.platform.workspace.models import Workspace, WorkspaceAccessPermissions, Tab
from wirecloud.platform.workspace.utils import create_tab, _workspace_cache_key, _variable_values_cache_key
from wirecloud.translation import gettext as _


def _sanitize_widget_layout_config(workspace_data: dict) -> None:
    tabs = workspace_data.get('tabs') or {}
    for tab in tabs.values():
        widgets = tab.get('widgets') or {}
        for widget in widgets.values():
            lcs = widget.get('positions', {}).get('configurations', [])
            for lc in lcs:
                widget = lc.get('widget', {})
                if isinstance(widget, dict):
                    widget.pop('moreOrEqual', None)
                    widget.pop('lessOrEqual', None)


async def get_workspace_list(db: DBSession, user: Optional[UserAll]) -> list[Workspace]:
    if user is not None:
        user_groups = await get_all_user_groups(db, user)

        query = { "$or": [
            {'public': True, 'searchable': True},
            {'users.id': ObjectId(user.id)},
            {'groups.id': {"$in": [group.id for group in user_groups]}},
        ]}
    else:
        query = {"public": True, "searchable": True}
    workspaces = await db.client.workspaces.find(query).to_list()
    results = []
    for workspace in workspaces:
        results.append(Workspace.model_validate(workspace))

    return results


async def create_empty_workspace(db: DBSession, title: str, user: User, allow_renaming: bool = False,
                                 name: str = None, translate: bool = True) -> Optional[Workspace]:
    if name is None or name == '':
        name = URLify(title)

    workspace = Workspace(
        id=ObjectId(),
        title=title,
        name=name,
        creator=ObjectId(user.id),
        users=[WorkspaceAccessPermissions(id=Id(user.id))]
    )
    await create_tab(db, user, _('Tab') if translate else 'Tab', workspace)

    if allow_renaming:
        await save_alternative(db, 'workspace', 'name', workspace)
    else:
        if await is_a_workspace_with_that_name(db, name, workspace.creator):
            return None
        await insert_workspace(db, workspace)

    return workspace


async def get_workspace_by_id(db: DBSession, workspace_id: Id) -> Optional[Workspace]:
    query = {"_id": ObjectId(workspace_id)}
    workspace = await db.client.workspaces.find_one(query)
    if workspace is None:
        return None

    return Workspace.model_validate(workspace)


async def create_workspace(db: DBSession, request: Optional[Request], owner: UserAll, mashup: Union[str, WgtFile, Workspace],
                           mashup_user: Optional[UserAll] = None,
                           new_name: str = None,
                           new_title: str = None, preferences: dict[str, Union[str, WorkspacePreference]] = {},
                           searchable: bool = True, public: bool = False,
                           allow_renaming: bool = False, dry_run: bool = False) -> Optional[Workspace]:
    if type(mashup) == str:
        values = mashup.split('/', 3)
        if len(values) != 3:
            raise ValueError(_('Invalid mashup id'))

        (mashup_vendor, mashup_name, mashup_version) = values
        resource = await get_catalogue_resource(db, mashup_vendor, mashup_name, mashup_version)
        if resource is None or not await resource.is_available_for(db, mashup_user if mashup_user is not None else owner) or resource.resource_type() != 'mashup':
            raise ValueError(_("Mashup not found %(mashup)s") % {'mashup': mashup})

        base_dir = catalogue.wgt_deployer.get_base_dir(mashup_vendor, mashup_name, mashup_version)
        wgt_file = WgtFile(os.path.join(base_dir, resource.template_uri))
        template = TemplateParser(wgt_file.get_template())

    elif isinstance(mashup, Workspace):
        options = MACDMashupWithParametrization(
            type=MACType.mashup,
            vendor='api',
            name=mashup.name,
            version='1.0',
            title=mashup.title if mashup.title is not None and mashup.title.strip() != "" else mashup.name,
            description='Temporal mashup for the workspace copy operation',
            email='a@example.com'
        )
        from wirecloud.platform.workspace.mashupTemplateGenerator import build_json_template_from_workspace
        parser = await build_json_template_from_workspace(db, request, options, mashup)

        template = TemplateParser(parser.model_dump())

    else:
        wgt = mashup if isinstance(mashup, WgtFile) else WgtFile(mashup)
        template = TemplateParser(wgt.get_template())

        resource_info = template.get_resource_processed_info(process_urls=False)
        if resource_info.type != MACType.mashup:
            raise ValueError("WgtFile is not a mashup")

        for embedded_resource in resource_info.embedded:
            if embedded_resource.src.startswith('https://'):
                resource_file = download_http_content(embedded_resource.src)
            else:
                resource_file = BytesIO(wgt.read(embedded_resource.src))

            extra_resource_contents = WgtFile(resource_file)
            await install_component(db, extra_resource_contents, executor_user=owner, users=[owner])

    from wirecloud.platform.workspace.mashupTemplateParser import check_mashup_dependencies, \
        build_workspace_from_template
    await check_mashup_dependencies(db, template, mashup_user if mashup_user is not None else owner)

    if dry_run:
        # TODO check name conflict
        return None

    workspace = await build_workspace_from_template(db, request, template, owner, allow_renaming=allow_renaming,
                                                    new_name=new_name, new_title=new_title,
                                                    searchable=searchable, public=public, resource_owner=mashup_user)
    if workspace is None:
        return None

    if len(preferences) > 0:
        from wirecloud.platform.preferences.crud import update_workspace_preferences
        await update_workspace_preferences(db, owner, workspace, preferences, invalidate_cache=False)

    return workspace


async def get_workspace_description(db: DBSession, workspace: Workspace) -> str:
    query = {"_id": ObjectId(workspace.id)}
    workspaces = [Workspace.model_validate(workspace) for workspace in
                  await db.client.workspaces.find(query).to_list()]

    resources = []
    for workspace in workspaces:
        for tab in workspace.tabs.values():
            for widget in tab.widgets.values():
                resources.append(widget)

    description = 'Wirecloud Mashup composed of: '
    for resource in resources:
        description += resource.title + ', '

    return description[:-2]


async def clear_workspace_users(db: DBSession, workspace: Workspace) -> None:
    query = {"_id": ObjectId(workspace.id)}
    await db.client.workspaces.update_one(query, {"$set": {"users": []}})


async def clear_workspace_groups(db: DBSession, workspace: Workspace) -> None:
    query = {"_id": ObjectId(workspace.id)}
    await db.client.workspaces.update_one(query, {"$set": {"groups": []}})


async def add_group_to_workspace(db: DBSession, workspace: Workspace, group: Group) -> None:
    query = {"_id": ObjectId(workspace.id)}
    await db.client.workspaces.update_one(query, {"$push": {"groups": ObjectId(group.id)}})


async def add_user_to_workspace(db: DBSession, workspace: Workspace, user: User) -> None:
    query = {"_id": ObjectId(workspace.id)}
    await db.client.workspaces.update_one(query, {"$push": {"users": ObjectId(user.id)}})


async def insert_workspace(db: DBSession, workspace: Workspace) -> None:
    # Create a dict representation and remove unwanted keys from layout configurations
    data = workspace.model_dump(by_alias=True)
    _sanitize_widget_layout_config(data)

    await db.client.workspaces.insert_one(data)


async def change_workspace(db: DBSession, workspace: Workspace, user: Optional[User]) -> None:
    await cache.delete(_workspace_cache_key(workspace, user))
    await cache.delete(_variable_values_cache_key(workspace, user))

    workspace.last_modified = datetime.now(timezone.utc)
    query = {"_id": ObjectId(workspace.id)}

    # Create a dict representation and remove unwanted keys from layout configurations
    data = workspace.model_dump(by_alias=True)
    _sanitize_widget_layout_config(data)

    await db.client.workspaces.replace_one(query, data)
    await update_workspace_in_index(db, workspace)


async def get_workspace_by_username_and_name(db: DBSession, creator_username: str, name: str) -> Optional[Workspace]:
    creator = await get_user_by_username(db, creator_username)
    if creator is None:
        return None
    query = {"creator": ObjectId(creator.id), "name": name}
    workspace = await db.client.workspaces.find_one(query)
    if workspace is None:
        return None

    return Workspace.model_validate(workspace)


async def is_a_workspace_with_that_name(db: DBSession, name: str, creator_id: Id) -> bool:
    query = {"name": name, "creator": creator_id}
    workspace = await db.client.workspaces.find_one(query)
    return workspace is not None


async def delete_workspace(db: DBSession, workspace: Workspace) -> None:
    query = {"_id": ObjectId(workspace.id)}
    await db.client.workspaces.delete_one(query)
    await delete_workspace_from_index(workspace)


async def change_tab(db: DBSession, user: User, workspace: Workspace, tab: Tab, save_workspace: bool = True) -> None:
    workspace.tabs[tab.id] = tab

    if save_workspace:
        await change_workspace(db, workspace, user)


async def set_visible_tab(db: DBSession, user: User, workspace: Workspace, tab: Tab) -> None:
    for visible_tab in workspace.tabs.values():
        visible_tab.visible = False
        await change_tab(db, user, workspace, visible_tab, save_workspace=False)

    tab.visible = True
    await change_tab(db, user, workspace, tab)


async def get_all_workspaces(db: DBSession) -> list[Workspace]:
    workspaces = await db.client.workspaces.find().to_list()
    results = []
    for workspace in workspaces:
        results.append(Workspace.model_validate(workspace))

    return results