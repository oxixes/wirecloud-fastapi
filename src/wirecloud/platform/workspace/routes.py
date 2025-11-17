# -*- coding: utf-8 -*-
# Copyright (c) 2012-2016 CoNWeT Lab., Universidad Politécnica de Madrid

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


import os.path
import zipfile
from typing import Optional
from io import BytesIO

from fastapi import APIRouter, Response, Request, Body, Form, UploadFile, File, Path

from src.wirecloud import docs as root_docs
from src.wirecloud.catalogue.utils import wgt_deployer
from src.wirecloud.catalogue.crud import get_catalogue_resource
from src.wirecloud.commons.utils.http import produces, authentication_required, consumes, build_error_response
from src.wirecloud.commons.utils.template import TemplateParser, is_valid_vendor, is_valid_name, is_valid_version
from src.wirecloud.commons.utils.template.schemas.macdschemas import MACDMashupWithParametrization, MACType, MACD
from src.wirecloud.commons.utils.wgt import WgtFile
from src.wirecloud.platform.markets.utils import get_local_catalogue
from src.wirecloud.platform.preferences.crud import update_workspace_preferences
from src.wirecloud.platform.search import add_workspace_to_index
from src.wirecloud.platform.workspace.crud import get_workspace_list, create_empty_workspace, get_workspace_by_id, \
    create_workspace, get_workspace_by_username_and_name, is_a_workspace_with_that_name, change_workspace, \
    delete_workspace, change_tab, set_visible_tab
from src.wirecloud.commons.auth.utils import UserDep, UserDepNoCSRF
from src.wirecloud.platform.workspace.mashupTemplateGenerator import build_json_template_from_workspace, \
    build_xml_template_from_workspace
from src.wirecloud.platform.workspace.mashupTemplateParser import check_mashup_dependencies, MissingDependencies, \
    fill_workspace_using_template
from src.wirecloud.platform.workspace.schemas import WorkspaceData, WorkspaceCreate, WorkspaceGlobalData, \
    WorkspaceEntry, TabCreate, TabData, TabCreateEntry, MashupMergeService
from src.wirecloud.database import DBDep, Id, commit
from src.wirecloud.platform.workspace.utils import get_workspace_data, get_global_workspace_data, create_tab, \
    get_tab_data, get_workspace_entry
from src.wirecloud.platform.workspace import docs
from src.wirecloud.translation import gettext as _

workspace_router = APIRouter()
workspaces_router = APIRouter()


@workspaces_router.get(
    "/",
    summary=docs.get_workspace_collection_summary,
    description=docs.get_workspace_collection_description,
    response_model=list[WorkspaceData],
    response_description=docs.get_workspace_collection_response_description,
    responses={
        200: {"content": {"application/json": {"example": docs.get_workspace_collection_response_example}}},
        401: root_docs.generate_auth_required_response_openapi_description(
            docs.get_workspace_collection_auth_required_response_description
        )
    }
)
@produces(["application/json"])
async def get_workspace_list_route(db: DBDep, user: UserDepNoCSRF) -> list[WorkspaceData]:
    workspaces = await get_workspace_list(db, user)
    data_list = [await get_workspace_data(db, workspace, user) for workspace in workspaces]
    return data_list


@workspaces_router.post(
    "/",
    summary=docs.create_workspace_collection_summary,
    description=docs.create_workspace_collection_description,
    response_model=WorkspaceGlobalData,
    response_description=docs.create_workspace_collection_response_description,
    responses={
        201: {"content": {"application/json": {"example": docs.create_workspace_collection_response_example}}},
        401: root_docs.generate_auth_required_response_openapi_description(
            docs.create_workspace_collection_auth_required_response_description
        ),
        403: root_docs.generate_permission_denied_response_openapi_description(
            docs.create_workspace_collection_permission_denied_response_description,
            "You are not allowed to read from workspace"
        ),
        406: root_docs.generate_not_acceptable_response_openapi_description(
            docs.create_workspace_collection_not_acceptable_response_description, ["application/json"]
        ),
        409: root_docs.generate_error_response_openapi_description(
            docs.create_workspace_collection_conflict_response_description,
            "A workspace with the given name already exists"
        ),
        422: root_docs.generate_validation_error_response_openapi_description(
            docs.create_workspace_collection_validation_error_response_description
        )
    }
)
@authentication_required()
@consumes(["application/json"])
@produces(["application/json"])
async def create_workspace_collection(db: DBDep, user: UserDep, request: Request, workspace: WorkspaceCreate = Body(
    description=docs.create_workspace_collection_workspace_description,
    examples=docs.create_workspace_collection_workspace_example)):
    workspace_name = workspace.name
    workspace_title = workspace.title
    workspace_id = workspace.workspace
    mashup_id = workspace.mashup
    initial_pref_values = workspace.preferences
    allow_renaming = workspace.allow_renaming
    dry_run = workspace.dry_run

    if mashup_id == '' and workspace_id == '':
        if workspace_title == '':
            workspace_title = workspace_name

        if dry_run:
            return Response(status_code=204)

        workspace = await create_empty_workspace(db, workspace_title, user, name=workspace_name,
                                                 allow_renaming=allow_renaming)
        if workspace is None:
            return build_error_response(request, 409, _("A workspace with the given name already exists"))
    else:
        if mashup_id != '':
            mashup = mashup_id
        else:
            mashup = await get_workspace_by_id(db, Id(workspace_id))
            if mashup is None:
                return build_error_response(request, 404, _("Workspace not found"))
            if not await mashup.is_accsessible_by(db, user):
                return build_error_response(request, 403, _("You are not allowed to read from workspace"))

        try:
            workspace = await create_workspace(db, request, user, mashup, allow_renaming=allow_renaming,
                                               new_name=workspace_name,
                                               new_title=workspace_title, dry_run=dry_run)
        except ValueError as e:
            return build_error_response(request, 422, str(e))
        except MissingDependencies as e:
            details = {
                'missingDependencies': e.missing_dependencies,
            }
            return build_error_response(request, 422, str(e), details=details)
        if workspace is None:
            return build_error_response(request, 409,
                                        _("A workspace with the given name already exists"))

        if dry_run:
            return Response(status_code=204)

    if len(initial_pref_values) > 0:
        await update_workspace_preferences(db, user, workspace, initial_pref_values, invalidate_cache=False)

    workspace_data = await get_global_workspace_data(db, request, workspace, user)

    await add_workspace_to_index(user, workspace)
    await commit(db)
    return workspace_data.get_response(status_code=201, cacheable=False)


@workspace_router.get(
    "/{workspace_id}/",
    summary=docs.get_workspace_entry_id_summary,
    description=docs.get_workspace_entry_id_description,
    response_model=WorkspaceGlobalData,
    response_description=docs.get_workspace_entry_id_response_description,
    responses={
        200: {"content": {"application/json": {"example": docs.get_workspace_entry_id_response_example}}},
        403: root_docs.generate_permission_denied_response_openapi_description(
            docs.get_workspace_entry_id_permission_denied_response_description,
            "You don't have permission to access this workspace"
        ),
        404: root_docs.generate_not_found_response_openapi_description(
            docs.get_workspace_entry_id_not_found_response_description)
    }
)
@produces(["application/json"])
async def get_workspace_entry_with_id(db: DBDep, user: UserDepNoCSRF, request: Request, workspace_id: Id = Path(
    description=docs.get_workspace_entry_id_workspace_id_description)):
    workspace = await get_workspace_by_id(db, workspace_id)

    return await get_workspace_entry(db, user, request, workspace)


@workspace_router.get(
    "/{owner}/{name}/",
    summary=docs.get_workspace_entry_owner_name_summary,
    description=docs.get_workspace_entry_owner_name_description,
    response_model=WorkspaceGlobalData,
    response_description=docs.get_workspace_entry_owner_name_response_description,
    responses={
        200: {"content": {"application/json": {"example": docs.get_workspace_entry_owner_name_response_example}}},
        403: root_docs.generate_permission_denied_response_openapi_description(
            docs.get_workspace_entry_owner_name_permission_denied_response_description,
            "You don't have permission to access this workspace"
        ),
        404: root_docs.generate_not_found_response_openapi_description(
            docs.get_workspace_entry_owner_name_not_found_response_description)
    }
)
async def get_workspace_entry_with_owner_and_name(db: DBDep, user: UserDepNoCSRF, request: Request, owner: str = Path(
    description=docs.get_workspace_entry_owner_name_owner_description), name: str = Path(
    description=docs.get_workspace_entry_owner_name_name_description)):
    workspace = await get_workspace_by_username_and_name(db, owner, name)
    return await get_workspace_entry(db, user, request, workspace)


@workspace_router.post(
    "/{workspace_id}/",
    summary=docs.update_workspace_entry_summary,
    description=docs.update_workspace_entry_description,
    status_code=204,
    response_class=Response,
    response_description=docs.update_workspace_entry_response_description,
    responses={
        401: root_docs.generate_auth_required_response_openapi_description(
            docs.update_workspace_entry_auth_required_response_description
        ),
        403: root_docs.generate_permission_denied_response_openapi_description(
            docs.update_workspace_entry_permission_denied_response_description,
            "You are not allowed to update this workspace"
        ),
        404: root_docs.generate_not_found_response_openapi_description(
            docs.update_workspace_entry_not_found_response_description
        ),
        406: root_docs.generate_not_acceptable_response_openapi_description(
            docs.update_workspace_entry_not_acceptable_response_description,
            ["application/json"]
        ),
        409: root_docs.generate_error_response_openapi_description(
            docs.update_workspace_entry_conflict_response_description,
            "A workspace with the given name already exists"
        )
    }
)
@authentication_required()
@consumes(["application/json"])
async def create_workspace_entry(db: DBDep, user: UserDep, request: Request, workspace_id: Id = Path(
    description=docs.update_workspace_entry_workspace_id_description),
                                 workspace_entry: WorkspaceEntry = Body(
                                     description=docs.update_workspace_entry_workspace_entry_description,
                                     examples=docs.update_workspace_entry_workspace_entry_example)):
    workspace = await get_workspace_by_id(db, workspace_id)
    change = False
    if workspace is None:
        return build_error_response(request, 404, _("Workspace not found"))

    if not workspace.is_editable_by(user):
        return build_error_response(request, 403, _("You are not allowed to update this workspace"))

    if workspace_entry.name != '':
        workspace.name = workspace_entry.name
        if await is_a_workspace_with_that_name(db, workspace.name):
            return build_error_response(request, 409, _("A workspace with the given name already exists"))
        change = True

    if workspace_entry.title != '':
        workspace.title = workspace_entry.title
        change = True

    if workspace_entry.description != '':
        workspace.description = workspace_entry.description
        change = True

    if workspace_entry.longdescription != '':
        workspace.longdescription = workspace_entry.longdescription
        change = True

    if change:
        await change_workspace(db, workspace, user)

    await commit(db)
    return Response(status_code=204)


@workspace_router.delete(
    "/{workspace_id}/",
    summary=docs.delete_workspace_entry_summary,
    description=docs.delete_workspace_entry_description,
    status_code=204,
    response_class=Response,
    response_description=docs.delete_workspace_entry_response_description,
    responses={
        401: root_docs.generate_auth_required_response_openapi_description(
            docs.delete_workspace_entry_auth_required_response_description
        ),
        403: root_docs.generate_permission_denied_response_openapi_description(
            docs.delete_workspace_entry_permission_denied_response_description,
            "You are not allowed to delete this workspace"
        ),
        404: root_docs.generate_not_found_response_openapi_description(
            docs.delete_workspace_entry_not_found_response_description
        )
    }
)
@authentication_required()
async def delete_workspace_entry(db: DBDep, user: UserDep, request: Request, workspace_id: Id = Path(
    description=docs.delete_workspace_entry_workspace_id_description)):
    workspace = await get_workspace_by_id(db, workspace_id)
    if workspace is None:
        return build_error_response(request, 404, _("Workspace not found"))

    if not workspace.is_editable_by(user):
        return build_error_response(request, 403, _("You are not allowed to delete this workspace"))

    await delete_workspace(db, workspace)
    await commit(db)
    return Response(status_code=204)


@workspace_router.post(
    "/{workspace_id}/tabs/",
    summary=docs.create_tab_collection_summary,
    description=docs.create_tab_collection_description,
    response_model=TabData,
    response_description=docs.create_tab_collection_response_description,
    responses={
        200: {"content": {"application/json": {"example": docs.create_tab_collection_response_example}}},
        401: root_docs.generate_auth_required_response_openapi_description(
            docs.create_tab_collection_auth_required_response_description
        ),
        403: root_docs.generate_permission_denied_response_openapi_description(
            docs.create_tab_collection_permission_denied_response_description,
            "You are not allowed to create new tabs for this workspace"
        ),
        404: root_docs.generate_not_found_response_openapi_description(
            docs.create_tab_collection_not_found_response_description
        ),
        406: root_docs.generate_not_acceptable_response_openapi_description(
            docs.create_tab_collection_not_acceptable_response_description,
            ["application/json"]
        ),
        409: root_docs.generate_error_response_openapi_description(
            docs.create_tab_collection_conflict_response_description,
            "A tab with the given name already exists"
        ),
        422: root_docs.generate_validation_error_response_openapi_description(
            docs.create_tab_collection_validation_error_response_description
        )
    }
)
@authentication_required()
@consumes(["application/json"])
@produces(["application/json"])
async def create_tab_collection(db: DBDep, user: UserDep, request: Request, workspace_id: Id = Path(
    description=docs.create_tab_collection_workspace_id_description),
                                tab_create: TabCreate = Body(
                                    description=docs.create_tab_collection_tab_create_description,
                                    examples=docs.create_tab_collection_tab_create_example)):
    workspace = await get_workspace_by_id(db, workspace_id)
    if workspace is None:
        return build_error_response(request, 404, _("Workspace not found"))

    tab_name = tab_create.name
    tab_title = tab_create.title

    if tab_name == '' and tab_title == '':
        return build_error_response(request, 422, _("Malformed tab JSON: expecting tab name or title"))

    if not workspace.is_editable_by(user):
        return build_error_response(request, 403, _("You are not allowed to create new tabs for this workspace"))

    if tab_title == '':
        tab_title = tab_name

    for aux_tab in workspace.tabs.values():
        if aux_tab.name == tab_name:
            return build_error_response(request, 409, _("A tab with the given name already exists"))

    tab = await create_tab(db, user, tab_title, workspace, name=tab_name)
    await commit(db)
    return await get_tab_data(db, request, tab, user=user)


@workspace_router.get(
    "/{workspace_id}/tab/{tab_id}/",
    summary=docs.get_tab_entry_summary,
    description=docs.get_tab_entry_description,
    response_model=TabData,
    response_description=docs.get_tab_entry_response_description,
    responses={
        200: {"content": {"application/json": {"example": docs.get_tab_entry_response_example}}},
        403: root_docs.generate_permission_denied_response_openapi_description(
            docs.get_tab_entry_permission_denied_response_description,
            "You don't have permission to access this workspace"
        ),
        404: root_docs.generate_not_found_response_openapi_description(
            docs.get_tab_entry_not_found_response_description
        )
    }
)
@produces(["application/json"])
async def get_tab_entry(db: DBDep, user: UserDepNoCSRF, request: Request,
                        workspace_id: Id = Path(description=docs.get_tab_entry_workspace_id_description),
                        tab_id: str = Path(description=docs.get_tab_entry_tab_id_description)):
    workspace = await get_workspace_by_id(db, workspace_id)
    if workspace is None:
        return build_error_response(request, 404, _("Workspace not found"))

    if not await workspace.is_accsessible_by(db, user):
        return build_error_response(request, 403, _("You don't have permission to access this workspace"))

    try:
        tab = workspace.tabs[tab_id]
    except KeyError:
        return build_error_response(request, 404, _("Tab not found"))

    return await get_tab_data(db, request, tab, user=user)


@workspace_router.post(
    "/{workspace_id}/tab/{tab_id}/",
    summary=docs.update_tab_entry_summary,
    description=docs.update_tab_entry_description,
    status_code=204,
    response_class=Response,
    response_description=docs.update_tab_entry_response_description,
    responses={
        401: root_docs.generate_auth_required_response_openapi_description(
            docs.update_tab_entry_auth_required_response_description
        ),
        403: root_docs.generate_permission_denied_response_openapi_description(
            docs.update_tab_entry_permission_denied_response_description,
            "You are not allowed to update this workspace"
        ),
        404: root_docs.generate_not_found_response_openapi_description(
            docs.update_tab_entry_not_found_response_description
        ),
        406: root_docs.generate_not_acceptable_response_openapi_description(
            docs.update_tab_entry_not_acceptable_response_description,
            ["application/json"]
        ),
        409: root_docs.generate_error_response_openapi_description(
            docs.update_tab_entry_conflict_response_description,
            "A tab with the given name already exists"
        )
    }
)
@authentication_required()
@consumes(["application/json"])
async def create_tab_entry(db: DBDep, user: UserDep, request: Request,
                           workspace_id: Id = Path(description=docs.update_tab_entry_workspace_id_description),
                           tab_id: str = Path(description=docs.update_tab_entry_tab_id_description),
                           tab_entry: TabCreateEntry = Body(
                               description=docs.update_tab_entry_tab_create_entry_description,
                               example=docs.update_tab_entry_tab_create_entry_example)):
    workspace = await get_workspace_by_id(db, workspace_id)
    if workspace is None:
        return build_error_response(request, 404, _("Workspace not found"))
    if not workspace.is_editable_by(user):
        return build_error_response(request, 403, _("You are not allowed to update this workspace"))

    try:
        tab = workspace.tabs[tab_id]
    except KeyError:
        return build_error_response(request, 404, _("Tab not found"))

    if tab_entry.visible is not None:
        visible = tab_entry.visible
        if visible:
            await set_visible_tab(db, user, workspace, tab)
        else:
            tab.visible = False

    for aux_tab in workspace.tabs.values():
        if aux_tab.name == tab_entry.name:
            return build_error_response(request, 409, _("A tab with the given name already exists"))

    if tab_entry.name != '':
        tab.name = tab_entry.name

    if tab_entry.title != '':
        tab.title = tab_entry.title

    await change_tab(db, user, workspace, tab)

    await commit(db)
    return Response(status_code=204)


@workspace_router.delete(
    "/{workspace_id}/tab/{tab_id}/",
    summary=docs.delete_tab_entry_summary,
    description=docs.delete_tab_entry_description,
    status_code=204,
    response_class=Response,
    response_description=docs.delete_tab_entry_response_description,
    responses={
        401: root_docs.generate_auth_required_response_openapi_description(
            docs.delete_tab_entry_auth_required_response_description
        ),
        403: root_docs.generate_permission_denied_response_openapi_description(
            docs.delete_tab_entry_permission_denied_response_description,
            "You cannot remove this tab"
        ),
        404: root_docs.generate_not_found_response_openapi_description(
            docs.delete_tab_entry_not_found_response_description
        )
    }
)
@authentication_required()
async def delete_tab_entry(db: DBDep, user: UserDep, request: Request,
                           workspace_id: Id = Path(description=docs.delete_tab_entry_workspace_id_description),
                           tab_id: str = Path(description=docs.delete_tab_entry_tab_id_description)):
    workspace = await get_workspace_by_id(db, workspace_id)
    if workspace is None:
        return build_error_response(request, 404, _("Workspace not found"))

    try:
        tab = workspace.tabs[tab_id]
    except KeyError:
        return build_error_response(request, 404, _("Tab not found"))

    if not workspace.is_editable_by(user):
        return build_error_response(request, 403, _("You are not allowed to remove this tab"))

    if len(workspace.tabs) == 1:
        return build_error_response(request, 403, _("Tab cannot be deleted as workspaces need at least one tab"))

    for widget in tab.widgets.values():
        if widget.read_only:
            return build_error_response(request, 403,
                                        _("Tab cannot be deleted as it contains widgets that cannot be deleted"))

    del workspace.tabs[tab_id]
    if tab.visible:
        await set_visible_tab(db, user, workspace, workspace.tabs[next(iter(workspace.tabs))])

    await change_workspace(db, workspace, user)
    await commit(db)
    return Response(status_code=204)


@workspace_router.post(
    "/{to_ws_id}/merge/",
    summary=docs.process_mashup_merge_service_summary,
    description=docs.process_mashup_merge_service_description,
    status_code=204,
    response_class=Response,
    response_description=docs.process_mashup_merge_service_response_description,
    responses={
        401: root_docs.generate_auth_required_response_openapi_description(
            docs.process_mashup_merge_service_auth_required_response_description
        ),
        403: root_docs.generate_permission_denied_response_openapi_description(
            docs.process_mashup_merge_service_permission_denied_response_description,
            "You are not allowed to read or update this workspace"
        ),
        404: root_docs.generate_not_found_response_openapi_description(
            docs.process_mashup_merge_service_not_found_response_description
        ),
        406: root_docs.generate_not_acceptable_response_openapi_description(
            docs.process_mashup_merge_service_not_acceptable_response_description,
            ["application/json"]
        ),
        422: root_docs.generate_validation_error_response_openapi_description(
            docs.process_mashup_merge_service_validation_error_response_description
        )
    }
)
@authentication_required()
@consumes(["application/json"])
async def process_mashup(db: DBDep, user: UserDep, request: Request,
                         to_ws_id: Id = Path(description=docs.process_mashup_merge_service_to_ws_id_description),
                         mashup_data: MashupMergeService = Body(
                             description=docs.process_mashup_merge_service_response_description,
                             examples=docs.process_mashup_merge_service_mashup_merge_service_example)):
    to_ws = await get_workspace_by_id(db, to_ws_id)
    if to_ws is None:
        return build_error_response(request, 404, _("Workspace not found"))

    if not to_ws.is_editable_by(user):
        return build_error_response(request, 403, _("You are not allowed to update this workspace"))

    mashup_id = mashup_data.mashup
    workspace_id = mashup_data.workspace

    if mashup_id == '' and workspace_id == '':
        return build_error_response(request, 422, _("Missing workspace or mashup parameter"))
    elif mashup_id != '' and workspace_id != '':
        return build_error_response(request, 422, _("Workspace and mashup parameters cannot be used at the same time"))

    if mashup_id != '':
        values = mashup_id.split('/', 3)
        if len(values) != 3:
            return build_error_response(request, 422, _("Invalid mashup id"))

        (mashup_vendor, mashup_name, mashup_version) = values
        resource = await get_catalogue_resource(db, mashup_vendor, mashup_name, mashup_version)
        if resource is None or (not await resource.is_available_for(db, user) or resource.resource_type() != 'mashup'):
            return build_error_response(request, 404, _(f"Mashup not found: {mashup_id}"))

        base_dir = wgt_deployer.get_base_dir(mashup_vendor, mashup_name, mashup_version)
        wgt_file = WgtFile(os.path.join(base_dir, resource.template_uri))
        template = TemplateParser(wgt_file.get_template())

    else:
        from_ws = await get_workspace_by_id(db, Id(workspace_id))
        if from_ws is None:
            return build_error_response(request, 404, _("Workspace not found"))
        if not await from_ws.is_accsessible_by(db, user):
            return build_error_response(request, 403,
                                        _("You are not allowed to read from workspace %(workspace_id)s") % {
                                            'workspace_id': workspace_id})

        options = MACDMashupWithParametrization(
            type=MACType.mashup,
            vendor='api',
            name='merge_op',
            version='1.0',
            title='',
            description='Temporal mashup for merging operation',
            email='a@example.com'
        )

        template = TemplateParser(
            (await build_json_template_from_workspace(db, request, options, from_ws)).model_dump_json())

    try:
        await check_mashup_dependencies(db, template, user)
    except MissingDependencies as e:
        details = {
            'missingDependencies': e.missing_dependencies,
        }
        return build_error_response(request, 422, _("Missing dependencies"), details=details)

    await fill_workspace_using_template(db, request, user, to_ws, template)

    await commit(db)
    return Response(status_code=204)


def check_json_fields(json_data, fields):
    missing_fields = []

    for field in fields:
        if field not in json_data:
            missing_fields.append(field)

    return missing_fields


@workspace_router.post(
    "/{workspace_id}/publish/",
    summary=docs.process_publish_service_summary,
    description=docs.process_publish_service_description,
    response_model=MACD,
    response_description=docs.process_publish_service_response_description,
    responses={
        201: {"content": {"application/json": {"example": docs.process_publish_service_response_example}}},
        400: root_docs.generate_error_response_openapi_description(
            docs.process_publish_service_bad_request_response_description,
            "Malformed JSON data"
        ),
        401: root_docs.generate_auth_required_response_openapi_description(
            docs.process_publish_service_auth_required_response_description
        ),
        404: root_docs.generate_not_found_response_openapi_description(
            docs.process_publish_service_not_found_response_description
        ),
        406: root_docs.generate_not_acceptable_response_openapi_description(
            docs.process_publish_service_not_acceptable_response_description,
            ["application/json"]
        )
    }
)
@authentication_required()
@consumes(["application/json", "multipart/form-data"])
async def publish_workspace(db: DBDep, user: UserDep, request: Request,
                            workspace_id: Id = Path(description=docs.process_publish_service_workspace_id_description),
                            json_data: str = Form(description=docs.process_publish_service_json_data_description,
                                                  example=docs.process_publish_service_json_data_example),
                            image_file: Optional[UploadFile] = File(None,
                                                                    description=docs.process_publish_service_image_file_description),
                            smartphoneimage_file: Optional[UploadFile] = File(None,
                                                                              description=docs.process_publish_service_smartphoneimage_file_description)):  # TODO: put schema in json_data
    extra_files = []

    json_data = MACDMashupWithParametrization.model_validate_json(json_data)

    missing_fields = check_json_fields(json_data.model_dump_json(), ('name', 'vendor', 'version'))
    if len(missing_fields) > 0:
        return build_error_response(request, 400,
                                    _("Malformed JSON. The following field(s) are missing %(missing_fields)s") % {
                                        'missing_fields': missing_fields})

    if not is_valid_vendor(json_data.vendor):
        return build_error_response(request, 400, _("Invalid vendor"))

    if not is_valid_name(json_data.name):
        return build_error_response(request, 400, _("Invalid name"))

    if not is_valid_version(json_data.version):
        return build_error_response(request, 400, _("Invalid version number"))

    workspace = await get_workspace_by_id(db, workspace_id)
    if workspace is None:
        return build_error_response(request, 404, _("Workspace not found"))

    if image_file is not None:
        json_data.image = 'images/catalogue' + os.path.splitext(image_file.filename)[1]
        extra_files.append((json_data.image, image_file.file))
    if smartphoneimage_file is not None:
        json_data.smartphoneimage = 'images/smartphone' + os.path.splitext(smartphoneimage_file.filename)[1]
        extra_files.append((json_data.smartphoneimage, smartphoneimage_file.file))
    if json_data.longdescription != '':
        extra_files.append(('DESCRIPTION.md', BytesIO(json_data.longdescription.encode('utf-8'))))
        json_data.longdescription = 'DESCRIPTION.md'

    description = await build_xml_template_from_workspace(db, request, json_data, workspace)

    # Build mashup wgt file
    f = BytesIO()
    zf = zipfile.ZipFile(f, 'w')
    zf.writestr('config.xml', description.encode('utf-8'))
    for filename, extra_file in extra_files:
        zf.writestr(filename, extra_file.read())
    for resource_info in json_data.embedded:
        (vendor, name, version) = (resource_info.vendor, resource_info.name, resource_info.version)
        resource = await get_catalogue_resource(db, vendor, name, version)
        base_dir = wgt_deployer.get_base_dir(vendor, name, version)
        zf.write(os.path.join(base_dir, resource.template_uri), resource_info.src)
    zf.close()
    wgt_file = WgtFile(f)

    resource = await get_local_catalogue().publish(db, None, wgt_file, user, request, json_data)

    await commit(db)
    return resource.get_processed_info(request)
