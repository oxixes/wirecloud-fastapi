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
from typing import Union

from fastapi import APIRouter, Request, Response, Body, Path

from src.wirecloud.commons.auth.crud import get_user_preferences, get_group_by_name, get_user_by_username
from src.wirecloud.commons.auth.models import DBPlatformPreference as PlatformPreferenceModel
from src.wirecloud.commons.auth.utils import UserDep, UserDepNoCSRF
from src.wirecloud.commons.utils.http import build_error_response, consumes, authentication_required
from src.wirecloud.database import DBDep, Id
from src.wirecloud.platform.preferences.crud import update_preferences, \
    update_workspace_preferences, update_tab_preferences
from src.wirecloud.platform.preferences.schemas import PlatformPreferenceCreate, WorkspacePreference, \
    ShareListPreference, ShareListEnum, TabPreference
from src.wirecloud.platform.preferences.utils import get_tab_preference_values, get_workspace_preference_values
from src.wirecloud.platform.workspace.crud import get_workspace_by_id, clear_workspace_users, \
    clear_workspace_groups, add_user_to_workspace, add_group_to_workspace, change_workspace
from src.wirecloud import docs as root_docs
from src.wirecloud.platform.preferences import docs
from src.wirecloud.translation import gettext as _

preferences_router = APIRouter()


def parse_values(preferences: list[PlatformPreferenceModel]) -> dict[str, dict[str, Union[bool, str]]]:
    return {pref.name: {'inherit': False, 'value': pref.value} for pref in preferences}


@preferences_router.get(
    "/preferences/platform/",
    summary=docs.get_platform_preference_collection_summary,
    description=docs.get_platform_preference_collection_description,
    response_model=dict[str, dict[str, Union[bool, str]]],
    response_description=docs.get_platform_preference_collection_response_description,
    responses={
        200: {"content": {"application/json": {"example": docs.get_platform_preference_collection_response_example}}},
        404: root_docs.generate_not_found_response_openapi_description(
            docs.get_platform_preference_collection_not_found_response_description
        )
    }
)
async def get_platform_preferences(db: DBDep, request: Request, user: UserDepNoCSRF):
    if user is not None:
        preferences = await get_user_preferences(db, user.id)
        if preferences is None:
            return build_error_response(request, 404, _("Platform preferences not found"))
        result = parse_values(preferences)
    else:
        result = {}

    return result


@preferences_router.post(
    "/preferences/platform/",
    summary=docs.create_platform_preference_collection_summary,
    description=docs.create_platform_preference_collection_description,
    status_code=204,
    response_class=Response,
    response_description=docs.create_platform_preference_collection_response_description,
    responses={
        401: root_docs.generate_auth_required_response_openapi_description(
            docs.create_platform_preference_collection_auth_required_response_description
        ),
        406: root_docs.generate_not_acceptable_response_openapi_description(
            docs.create_platform_preference_collection_not_acceptable_response_description,
            ["application/json"]
        ),
        422: root_docs.generate_validation_error_response_openapi_description(
            docs.create_platform_preference_collection_validation_error_response_description
        )
    }
)
@authentication_required()
@consumes(["application/json"])
async def create_platform_preferences(db: DBDep, request: Request, user: UserDep,
                                      preferences: PlatformPreferenceCreate = Body(
                                          description=docs.create_platform_preference_collection_platform_preference_create_description,
                                          example=docs.create_platform_preference_collection_platform_preference_create_example)):
    await update_preferences(db, user, preferences)
    await db.commit_transaction()


@preferences_router.get(
    "/workspace/{workspace_id}/preferences/",
    summary=docs.get_workspace_preference_collection_summary,
    description=docs.get_workspace_preference_collection_description,
    response_model=dict[str, WorkspacePreference],
    response_description=docs.get_workspace_preference_collection_response_description,
    responses={
        200: {"content": {"application/json": {"example": docs.get_workspace_preference_collection_response_example}}},
        401: root_docs.generate_auth_required_response_openapi_description(
            docs.get_workspace_preference_collection_auth_required_response_description
        ),
        403: root_docs.generate_permission_denied_response_openapi_description(
            docs.get_workspace_preference_collection_permission_denied_response_description,
            "You are not allowed to read this workspace"
        ),
        404: root_docs.generate_not_found_response_openapi_description(
            docs.get_workspace_preference_collection_not_found_response_description
        )
    }
)
@authentication_required(csrf=False)
async def get_workspace_preferences(db: DBDep, request: Request, user: UserDepNoCSRF, workspace_id: Id = Path(
    description=docs.get_workspace_preference_collection_workspace_id_description)):
    workspace = await get_workspace_by_id(db, workspace_id)
    if workspace is None:
        return build_error_response(request, 404, _("Workspace not found"))
    if not await workspace.is_accsessible_by(db, user):
        return build_error_response(request, 403, _("You are not allowed to read this workspace"))

    return await get_workspace_preference_values(workspace)


@preferences_router.post(
    "/workspace/{workspace_id}/preferences/",
    summary=docs.create_workspace_preference_collection_summary,
    description=docs.create_workspace_preference_collection_description,
    status_code=204,
    response_class=Response,
    response_description=docs.create_workspace_preference_collection_response_description,
    responses={
        401: root_docs.generate_auth_required_response_openapi_description(
            docs.create_workspace_preference_collection_auth_required_response_description
        ),
        403: root_docs.generate_permission_denied_response_openapi_description(
            docs.create_workspace_preference_collection_permission_denied_response_description,
            "You are not allowed to read this workspace"
        ),
        406: root_docs.generate_not_acceptable_response_openapi_description(
            docs.create_workspace_preference_collection_not_acceptable_response_description,
            ["application/json"]
        ),
        422: root_docs.generate_validation_error_response_openapi_description(
            docs.create_workspace_preference_collection_validation_error_response_description
        )
    }
)
@authentication_required()
@consumes(["application/json"])
async def create_workspace_preferences(db: DBDep, request: Request, user: UserDep, workspace_id: Id = Path(
    description=docs.create_workspace_preference_collection_workspace_id_description),
                                       preferences: dict[str, Union[str, WorkspacePreference]] = Body(
                                           description=docs.create_workspace_preference_collection_platform_preference_create_description,
                                           example=docs.create_workspace_preference_collection_platform_preference_create_example)):
    workspace = await get_workspace_by_id(db, workspace_id)
    if workspace is None:
        return build_error_response(request, 404, _("Workspace not found"))
    if not workspace.is_editable_by(user):
        return build_error_response(request, 403, _("You are not allowed to update this workspace"))

    save_workspace = False
    save_public = False

    if 'sharelist' in preferences:
        await clear_workspace_users(db, workspace)
        await clear_workspace_groups(db, workspace)
        if isinstance(preferences['sharelist'], WorkspacePreference):
            sharelist = json.loads(preferences['sharelist'].value)
        else:
            sharelist = json.loads(preferences['sharelist'])

        for item in sharelist:
            entrytype = ShareListPreference.model_validate(item)
            if entrytype.type in (ShareListEnum.user, ShareListEnum.organization):
                user = await get_user_by_username(db, entrytype.name)
                if user is None:
                    continue
                await add_user_to_workspace(db, workspace, user)
                # TODO: Add organization support

            elif entrytype.type == ShareListEnum.group:
                group = await get_group_by_name(db, entrytype.name)
                if group is None:
                    continue
                await add_group_to_workspace(db, workspace, group)

        del preferences['sharelist']

    if 'public' in preferences:
        save_workspace = True
        save_public = True
        if type(preferences['public']) == str:
            workspace.public = preferences['public'].strip().lower() == 'true'
        else:
            workspace.public = preferences['public'].value.strip().lower() == 'true'
        del preferences['public']

    if 'requireauth' in preferences:
        save_workspace = True
        if type(preferences['requireauth']) == str:
            workspace.requireauth =  preferences['requireauth'].strip().lower() == 'true'
        else:
            workspace.requireauth = preferences['requireauth'].value.strip().lower() == 'true'
        del preferences['requireauth']

    if save_workspace:
        await change_workspace(db, workspace, user)
        if save_public:
            prefs = {'public': str(workspace.public).strip().lower()}
            await update_workspace_preferences(db, user, workspace, prefs, invalidate_cache=False)
        await db.commit_transaction()

    await update_workspace_preferences(db, user, workspace, preferences)
    await db.commit_transaction()


@preferences_router.get(
    "/workspace/{workspace_id}/tab/{tab_id}/preferences/",
    summary=docs.get_tab_preference_collection_summary,
    description=docs.get_tab_preference_collection_description,
    response_model=dict[str, WorkspacePreference],
    response_description=docs.get_tab_preference_collection_response_description,
    responses={
        200: {"content": {"application/json": {"example": docs.get_tab_preference_collection_response_example}}},
        401: root_docs.generate_auth_required_response_openapi_description(
            docs.get_tab_preference_collection_auth_required_response_description
        ),
        403: root_docs.generate_permission_denied_response_openapi_description(
            docs.get_tab_preference_collection_permission_denied_response_description,
            "You are not allowed to read this workspace"
        ),
        404: root_docs.generate_not_found_response_openapi_description(
            docs.get_tab_preference_collection_not_found_response_description
        )
    }
)
@authentication_required(csrf=False)
async def get_tab_preferences(db: DBDep, request: Request, user: UserDepNoCSRF, workspace_id: Id = Path(
    description=docs.get_tab_preference_collection_workspace_id_description), tab_id: str = Path(
    description=docs.get_tab_preference_collection_tab_id_description)):
    workspace = await get_workspace_by_id(db, workspace_id)
    if workspace is None:
        return build_error_response(request, 404, _("Workspace not found"))

    try:
        tab = workspace.tabs[tab_id]
    except KeyError:
        return build_error_response(request, 404, _("Tab not found"))

    if not await workspace.is_accsessible_by(db, user):
        return build_error_response(request, 403, _("You are not allowed to read this workspace"))

    result = await get_tab_preference_values(tab)

    return result


@preferences_router.post(
    "/workspace/{workspace_id}/tab/{tab_id}/preferences/",
    summary=docs.create_tab_preference_collection_summary,
    description=docs.create_tab_preference_collection_description,
    status_code=204,
    response_class=Response,
    response_description=docs.create_tab_preference_collection_response_description,
    responses={
        403: root_docs.generate_permission_denied_response_openapi_description(
            docs.create_tab_preference_collection_permission_denied_response_description,
            "You are not allowed to read this workspace"
        ),
        406: root_docs.generate_not_acceptable_response_openapi_description(
            docs.create_tab_preference_collection_not_acceptable_response_description,
            ["application/json"]
        ),
        422: root_docs.generate_validation_error_response_openapi_description(
            docs.create_tab_preference_collection_validation_error_response_description
        )
    }
)
async def create_tab_preferences(db: DBDep, request: Request, user: UserDep, workspace_id: Id = Path(
    description=docs.create_tab_preference_collection_workspace_id_description), tab_id: str = Path(
    description=docs.create_tab_preference_collection_tab_id_description),
                                 preferences: dict[str, Union[str, TabPreference]] = Body(
                                     description=docs.create_tab_preference_collection_platform_preference_create_description,
                                     example=docs.create_tab_preference_collection_platform_preference_create_example)):
    workspace = await get_workspace_by_id(db, workspace_id)
    if workspace is None:
        return build_error_response(request, 404, _("Workspace not found"))

    try:
        tab = workspace.tabs[tab_id]
    except KeyError:
        return build_error_response(request, 404, _("Tab not found"))

    if not await workspace.is_accsessible_by(db, user):
        return build_error_response(request, 403, _("You are not allowed to read this workspace"))

    await update_tab_preferences(db, user, workspace, tab, preferences)
    await db.commit_transaction()
