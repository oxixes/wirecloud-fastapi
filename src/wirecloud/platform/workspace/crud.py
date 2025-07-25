#  -*- coding: utf-8 -*-
#
#  Copyright (c) 2012-2016 CoNWeT Lab., Universidad Politécnica de Madrid
#  Copyright (c) 2016-2025 Future Internet Consulting and Development Solutions S.L.
#
#  This file is part of Wirecloud.
#
#  Wirecloud is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Affero General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  Wirecloud is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Affero General Public License for more details.
#
#  You should have received a copy of the GNU Affero General Public License
#  along with Wirecloud.  If not, see <http://www.gnu.org/licenses/>.
from datetime import timezone, datetime
from urllib.request import Request

from bson import ObjectId
from typing import Optional, Union
import os
from io import BytesIO

from src.settings import cache
from src.wirecloud.catalogue import utils as catalogue
from src.wirecloud.catalogue.crud import get_catalogue_resource, get_catalogue_resource_by_id
from src.wirecloud.commons.auth.crud import get_user_by_username
from src.wirecloud.commons.utils.db import save_alternative
from src.wirecloud.commons.utils.downloader import download_http_content
from src.wirecloud.commons.utils.template import TemplateParser
from src.wirecloud.commons.utils.template.schemas.macdschemas import MACDMashupWithParametrization, MACType
from src.wirecloud.commons.utils.urlify import URLify
from src.wirecloud.commons.utils.wgt import WgtFile
from src.wirecloud.database import DBSession, Id
from src.wirecloud.commons.auth.schemas import User, UserAll
from src.wirecloud.platform.localcatalogue.utils import install_component
from src.wirecloud.platform.preferences.schemas import WorkspacePreference
from src.wirecloud.commons.auth.models import Group as GroupModel, Group
from src.wirecloud.platform.workspace.models import Workspace, WorkspaceAccessPermissions, Tab
from src.wirecloud.platform.workspace.utils import create_tab, _workspace_cache_key, _variable_values_cache_key
from src.wirecloud.translation import gettext as _


async def get_workspace_list(db: DBSession, user: Optional[User]) -> list[Workspace]:
    if user is not None:
        query = { "$or": [
            {'public': True, 'searchable': True},
            {'users.id': ObjectId(user.id)}
        ]}
    else:
        query = {"public": True, "searchable": True}
    workspaces = await db.client.workspace.find(query).to_list()
    results = []
    for workspace in workspaces:
        results.append(Workspace.model_validate(workspace))

    return results


async def create_empty_workspace(db: DBSession, title: str, user: User, allow_renaming: bool = False,
                                 name: str = None) -> Optional[Workspace]:
    if name is None or name == '':
        name = URLify(title)

    workspace = Workspace(
        id=ObjectId(),
        title=title,
        name=name,
        creator=ObjectId(user.id),
        users=[WorkspaceAccessPermissions(id=Id(user.id))]
    )
    tab = await create_tab(db, user, _('Tab'), workspace)

    if allow_renaming:
        await save_alternative(db, 'workspace', 'name', workspace)
    else:
        if await is_a_workspace_with_that_name(db, name):
            return None
        await insert_workspace(db, workspace)

    return workspace


async def get_workspace_by_id(db: DBSession, workspace_id: Id) -> Optional[Workspace]:
    query = {"_id": ObjectId(workspace_id)}
    workspace = await db.client.workspace.find_one(query)
    if workspace is None:
        return None

    return Workspace.model_validate(workspace)


async def get_workspace_groups(db: DBSession, workspace: Workspace) -> list[Group]:
    query = {"_id": {"$in": workspace.get("groups")}}
    results = [GroupModel.model_validate(result) for result in await db.client.groups.find(query).to_list()]
    return results


async def create_workspace(db: DBSession, request: Request, owner: UserAll, mashup: Union[str, WgtFile, Workspace],
                           new_name: str = None,
                           new_title: str = None, preferences: dict[str, Union[str, WorkspacePreference]] = {},
                           searchable: bool = True, public: bool = False,
                           allow_renaming: bool = False, dry_run: bool = False) -> Optional[Workspace]:
    if not db.in_transaction:
        db.start_transaction()

    if type(mashup) == str:
        values = mashup.split('/', 3)
        if len(values) != 3:
            raise ValueError(_('Invalid mashup id'))

        (mashup_vendor, mashup_name, mashup_version) = values
        resource = await get_catalogue_resource(db, mashup_vendor, mashup_name, mashup_version)
        if resource is None or not await resource.is_available_for(db, owner) or resource.resource_type() != 'mashup':
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
        from src.wirecloud.platform.workspace.mashupTemplateGenerator import build_json_template_from_workspace
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

    from src.wirecloud.platform.workspace.mashupTemplateParser import check_mashup_dependencies, \
        build_workspace_from_template
    await check_mashup_dependencies(db, template, owner)

    if dry_run:
        # TODO check name conflict
        return None

    workspace = await build_workspace_from_template(db, request, template, owner, allow_renaming=allow_renaming,
                                                    new_name=new_name, new_title=new_title,
                                                    searchable=searchable, public=public)
    if workspace is None:
        return None

    if len(preferences) > 0:
        from src.wirecloud.platform.preferences.crud import update_workspace_preferences
        await update_workspace_preferences(db, owner, workspace, preferences, invalidate_cache=False)

    return workspace


async def get_workspace_description(db: DBSession, workspace: Workspace) -> str:
    query = {"_id": ObjectId(workspace.id)}
    workspaces = [Workspace.model_validate(workspace).widgets for workspace in
                  await db.client.workspace.find(query).to_list()]

    resources = []
    for workspace in workspaces:
        for tab in workspace.tabs:
            for widget in tab.widgets:
                resources.append(await get_catalogue_resource_by_id(db, widget.widget_id))

    description = 'Wirecloud Mashup composed of: '
    for resource in resources:
        description += resource.title + ', '

    return description[:-2]


async def clear_workspace_users(db: DBSession, workspace: Workspace) -> None:
    if not db.in_transaction:
        db.start_transaction()
    query = {"_id": ObjectId(workspace.id)}
    await db.client.workspace.update_one(query, {"$set": {"users": []}})


async def clear_workspace_groups(db: DBSession, workspace: Workspace) -> None:
    if not db.in_transaction:
        db.start_transaction()
    query = {"_id": ObjectId(workspace.id)}
    await db.client.workspace.update_one(query, {"$set": {"groups": []}})


async def add_group_to_workspace(db: DBSession, workspace: Workspace, group: Group) -> None:
    if not db.in_transaction:
        db.start_transaction()
    query = {"_id": ObjectId(workspace.id)}
    await db.client.workspace.update_one(query, {"$push": {"groups": ObjectId(group.id)}})


async def add_user_to_workspace(db: DBSession, workspace: Workspace, user: User) -> None:
    if not db.in_transaction:
        db.start_transaction()
    query = {"_id": ObjectId(workspace.id)}
    await db.client.workspace.update_one(query, {"$push": {"users": ObjectId(user.id)}})


async def get_tabs_from_workspace(db: DBSession, workspace: Workspace) -> list[Tab]:
    query = {"_id": ObjectId(workspace.id)}
    workspace = await db.client.workspace.find_one(query)
    if workspace is None:
        return []

    workspace = Workspace.model_validate(workspace)
    return workspace.tabs


async def insert_workspace(db: DBSession, workspace: Workspace) -> None:
    if not db.in_transaction:
        db.start_transaction()

    await db.client.workspace.insert_one(workspace.model_dump(by_alias=True))


async def change_workspace(db: DBSession, workspace: Workspace, user: Optional[User]) -> None:
    if not db.in_transaction:
        db.start_transaction()

    await cache.delete(_workspace_cache_key(workspace, user))
    await cache.delete(_variable_values_cache_key(workspace, user))

    workspace.last_modified = datetime.now(timezone.utc)
    query = {"_id": ObjectId(workspace.id)}
    await db.client.workspace.replace_one(query, workspace.model_dump(by_alias=True))


async def get_workspace_by_username_and_name(db: DBSession, creator__username: str, name: str) -> Optional[Workspace]:
    creator = await get_user_by_username(db, creator__username)
    if creator is None:
        return None
    query = {"creator": ObjectId(creator.id), "name": name}
    workspace = await db.client.workspace.find_one(query)
    if workspace is None:
        return None

    return Workspace.model_validate(workspace)


async def is_a_workspace_with_that_name(db: DBSession, name: str) -> bool:
    query = {"name": name}
    workspace = await db.client.workspace.find_one(query)
    return workspace is not None


async def delete_workspace(db: DBSession, workspace: Workspace) -> None:
    if not db.in_transaction:
        db.start_transaction()
    query = {"_id": ObjectId(workspace.id)}
    await db.client.workspace.delete_one(query)


async def change_tab(db: DBSession, user: User, workspace: Workspace, tab: Tab) -> None:
    if not db.in_transaction:
        db.start_transaction()

    tab_position = int(tab.id.split('-')[1])
    workspace.tabs[tab_position] = tab
    await change_workspace(db, workspace, user)


async def set_visible_tab(db: DBSession, user: User, workspace: Workspace, tab: Tab) -> None:
    if not db.in_transaction:
        db.start_transaction()

    for visible_tab in workspace.tabs:
        visible_tab.visible = False
        await change_tab(db, user, workspace, visible_tab)

    tab.visible = True
    await change_tab(db, user, workspace, tab)
