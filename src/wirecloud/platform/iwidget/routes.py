#  -*- coding: utf-8 -*-
#
#  Copyright (c) 2024 Future Internet Consulting and Development Solutions S.L.
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
from typing import Any

from fastapi import APIRouter, Request, Body, Path, Response

from src.wirecloud.catalogue.crud import get_catalogue_resource_by_id
from src.wirecloud.commons.auth.utils import UserDep, UserDepNoCSRF
from src.wirecloud.commons.utils.http import authentication_required, build_error_response, consumes, NotFound
from src.wirecloud.database import DBDep, Id
from src.wirecloud import docs as root_docs
from src.wirecloud.platform.iwidget import docs
from src.wirecloud.platform.iwidget.schemas import WidgetInstanceData, WidgetInstanceDataCreate, \
    WidgetInstanceDataUpdate
from src.wirecloud.platform.iwidget.utils import save_widget_instance, update_widget_instance
from src.wirecloud.platform.workspace.crud import get_workspace_by_id, change_workspace
from src.wirecloud.platform.workspace.utils import VariableValueCacheManager, get_widget_instance_data
from src.wirecloud.translation import gettext as _

iwidget_router = APIRouter()


@iwidget_router.get(
    "/{workspace_id}/tab/{tab_id}/widget_instances/",
    summary=docs.get_widget_instance_collection_summary,
    description=docs.get_widget_instance_collection_description,
    response_model=list[WidgetInstanceData],
    response_description=docs.get_widget_instance_collection_response_description,
    responses={
        200: {"content": {"application/json": {"example": docs.get_widget_instance_collection_response_example}}},
        401: root_docs.generate_auth_required_response_openapi_description(
            docs.get_widget_instance_collection_auth_required_response_description
        ),
        403: root_docs.generate_permission_denied_response_openapi_description(
            docs.get_widget_instance_collection_permission_denied_response_description,
            "You don't have permission to access this workspace"
        ),
        404: root_docs.generate_not_found_response_openapi_description(
            docs.get_widget_instance_collection_not_found_response_description
        ),
    }
)
@authentication_required(csrf=False)
async def get_widget_instance_collection(db: DBDep, user: UserDepNoCSRF, request: Request, workspace_id: Id = Path(
    description=docs.get_widget_instance_collection_workspace_id_description),
                                 tab_id: str = Path(description=docs.get_widget_instance_collection_tab_id_description)):
    workspace = await get_workspace_by_id(db, workspace_id)
    if workspace is None:
        return build_error_response(request, 404, _("Workspace not found"))

    try:
        tab = workspace.tabs[tab_id]
    except KeyError:
        return build_error_response(request, 404, _("Tab not found"))

    if not await workspace.is_accessible_by(db, user):
        return build_error_response(request, 403, _("You don't have permission to access this workspace"))

    cache_manager = VariableValueCacheManager(workspace, user)
    iwidgets = tab.widgets.values()
    data = [await get_widget_instance_data(db, request, iwidget, workspace, cache_manager) for
            iwidget in
            iwidgets]
    return data


@iwidget_router.post(
    "/{workspace_id}/tab/{tab_id}/widget_instances/",
    summary=docs.create_widget_instance_collection_summary,
    description=docs.create_widget_instance_collection_description,
    status_code=201,
    response_model=WidgetInstanceData,
    response_description=docs.create_widget_instance_collection_response_description,
    responses={
        201: {"content": {"application/json": {"example": docs.create_widget_instance_collection_response_example}}},
        401: root_docs.generate_auth_required_response_openapi_description(
            docs.create_widget_instance_collection_auth_required_response_description
        ),
        403: root_docs.generate_permission_denied_response_openapi_description(
            docs.create_widget_instance_collection_permission_denied_response_description,
            "You have not enough permission for adding iwidgets to the workspace"
        ),
        406: root_docs.generate_not_acceptable_response_openapi_description(
            docs.create_widget_instance_collection_not_acceptable_response_description,
            ["application/json"]
        ),
        404: root_docs.generate_not_found_response_openapi_description(
            docs.create_widget_instance_collection_not_found_response_description
        ),
        422: root_docs.generate_validation_error_response_openapi_description(
            docs.create_widget_instance_collection_validation_error_response_description
        )
    }
)
@authentication_required()
@consumes(["application/json"])
async def create_widget_instance_collection(db: DBDep, user: UserDep, request: Request, workspace_id: Id = Path(
    description=docs.create_widget_instance_collection_workspace_id_description), tab_id: str = Path(
    description=docs.create_widget_instance_collection_tab_id_description),
                                    iwidget: WidgetInstanceDataCreate = Body(
                                        example=docs.create_widget_instance_collection_widget_instance_example,
                                        description=docs.create_widget_instance_collection_widget_instance_description)):
    initial_variable_values = iwidget.variable_values
    workspace = await get_workspace_by_id(db, workspace_id)
    if workspace is None:
        return build_error_response(request, 404, _("Workspace not found"))
    try:
        tab = workspace.tabs[tab_id]
    except KeyError:
        return build_error_response(request, 404, _("Tab not found"))

    if not workspace.is_editable_by(user):
        return build_error_response(request, 403, _("You have not enough permission for adding iwidgets to the workspace"))
    try:
        iwidget = await save_widget_instance(db, workspace, iwidget, user, tab, initial_variable_values)

        iwidget_data = await get_widget_instance_data(db, request, iwidget, workspace, user=user)

        return Response(content=iwidget_data.model_dump_json(), media_type="application/json", status_code=201)

    except NotFound:
        return build_error_response(request, 422, _(f"Referred widget {iwidget.resource} does not exist."))
    except TypeError as e:
        return build_error_response(request, 400, str(e))
    except ValueError as e:
        return build_error_response(request, 422, str(e))


@iwidget_router.put(
    "/{workspace_id}/tab/{tab_id}/widget_instances/",
    summary=docs.update_widget_instance_collection_summary,
    description=docs.update_widget_instance_collection_description,
    status_code=204,
    response_class=Response,
    response_description=docs.update_widget_instance_collection_response_description,
    responses={
        400: root_docs.generate_error_response_openapi_description(
            docs.update_widget_instance_collection_bad_request_response_description,
            "Malformed JSON data"
        ),
        401: root_docs.generate_auth_required_response_openapi_description(
            docs.update_widget_instance_collection_auth_required_response_description
        ),
        403: root_docs.generate_permission_denied_response_openapi_description(
            docs.update_widget_instance_collection_permission_denied_response_description,
            "You have not enough permission for updating the iwidgets of this workspace"
        ),
        404: root_docs.generate_not_found_response_openapi_description(
            docs.update_widget_instance_collection_not_found_response_description
        ),
        422: root_docs.generate_validation_error_response_openapi_description(
            docs.update_widget_instance_collection_validation_error_response_description
        )
    }
)
@authentication_required()
@consumes(["application/json"])
async def update_widget_instance_collection(db: DBDep, user: UserDep, request: Request, workspace_id: Id = Path(
    description=docs.update_widget_instance_collection_workspace_id_description),
                                    tab_id: str = Path(
                                        description=docs.update_widget_instance_collection_tab_id_description),
                                    iwidgets: list[WidgetInstanceDataUpdate] = Body(
                                        description=docs.update_widget_instance_collection_widget_instance_description,
                                        example=docs.update_widget_instance_collection_widget_instance_example)):
    workspace = await get_workspace_by_id(db, workspace_id)
    if workspace is None:
        return build_error_response(request, 404, _("Workspace not found"))

    try:
        tab = workspace.tabs[tab_id]
    except KeyError:
        return build_error_response(request, 404, _("Tab not found"))

    if not workspace.is_editable_by(user):
        return build_error_response(request, 403,
                                    _("You have not enough permission for updating the iwidgets of this workspace"))

    for iwidget in iwidgets:
        try:
            response = await update_widget_instance(db, request, iwidget, user, workspace, tab, update_cache=False)
            if response is not None:
                return response
        except TypeError as e:
            return build_error_response(request, 400, str(e))
        except ValueError as e:
            return build_error_response(request, 422, str(e))

    if len(iwidgets) > 0:
        await change_workspace(db, workspace, user)

    return Response(status_code=204)


@iwidget_router.get(
    "/{workspace_id}/tab/{tab_id}/widget_instances/{iwidget_id}",
    summary=docs.get_widget_instance_entry_summary,
    description=docs.get_widget_instance_entry_description,
    response_model=WidgetInstanceData,
    response_description=docs.get_widget_instance_entry_response_description,
    responses={
        200: {"content": {"application/json": {"example": docs.get_widget_instance_entry_response_example}}},
        401: root_docs.generate_auth_required_response_openapi_description(
            docs.get_widget_instance_entry_auth_required_response_description
        ),
        404: root_docs.generate_not_found_response_openapi_description(
            docs.get_widget_instance_entry_not_found_response_description
        ),
    }
)
@authentication_required(csrf=False)
async def get_widget_instance_entry(db: DBDep, user: UserDepNoCSRF, request: Request,
                            workspace_id: Id = Path(description=docs.get_widget_instance_entry_workspace_id_description),
                            tab_id: str = Path(description=docs.get_widget_instance_entry_tab_id_description),
                            iwidget_id: str = Path(
                                description=docs.get_widget_instance_entry_widget_instance_id_description)):
    workspace = await get_workspace_by_id(db, workspace_id)
    if workspace is None:
        return build_error_response(request, 404, _("Workspace not found"))

    try:
        tab = workspace.tabs[tab_id]
    except KeyError:
        return build_error_response(request, 404, _("Tab not found"))

    try:
        iwidget = tab.widgets[iwidget_id]
    except KeyError:
        return build_error_response(request, 404, _("IWidget not found"))

    return await get_widget_instance_data(db, request, iwidget, workspace, user=user)


@iwidget_router.post(
    "/{workspace_id}/tab/{tab_id}/widget_instances/{iwidget_id}",
    summary=docs.update_widget_instance_entry_summary,
    description=docs.update_widget_instance_entry_description,
    status_code=204,
    response_class=Response,
    response_description=docs.update_widget_instance_entry_response_description,
    responses={
        400: root_docs.generate_error_response_openapi_description(
            docs.update_widget_instance_entry_bad_request_response_description,
            "Malformed JSON data"
        ),
        401: root_docs.generate_auth_required_response_openapi_description(
            docs.update_widget_instance_entry_auth_required_response_description
        ),
        403: root_docs.generate_permission_denied_response_openapi_description(
            docs.update_widget_instance_entry_permission_denied_response_description,
            "You have not enough permission for updating the iwidget"
        ),
        404: root_docs.generate_not_found_response_openapi_description(
            docs.update_widget_instance_entry_not_found_response_description
        ),
        422: root_docs.generate_validation_error_response_openapi_description(
            docs.update_widget_instance_entry_validation_error_response_description
        )
    }
)
@authentication_required()
@consumes(["application/json"])
async def update_widget_instance_entry(db: DBDep, user: UserDep, request: Request,
                               workspace_id: Id = Path(description=docs.update_widget_instance_entry_workspace_id_description),
                               tab_id: str = Path(description=docs.update_widget_instance_entry_tab_id_description),
                               iwidget_id: str = Path(
                                   description=docs.update_widget_instance_entry_widget_instance_id_description),
                               iwidget_data: WidgetInstanceDataUpdate = Body(
                                   description=docs.update_widget_instance_entry_widget_instance_description,
                                   example=docs.update_widget_instance_entry_widget_instance_example)):
    workspace = await get_workspace_by_id(db, workspace_id)
    if workspace is None:
        return build_error_response(request, 404, _("Workspace not found"))

    try:
        tab = workspace.tabs[tab_id]
    except KeyError:
        return build_error_response(request, 404, _("Tab not found"))

    if not workspace.is_editable_by(user):
        return build_error_response(request, 403, _("You have not enough permission for updating the iwidget"))

    iwidget_data.id = iwidget_id
    try:
        response = await update_widget_instance(db, request, iwidget_data, user, workspace, tab)
        if response is not None:
            return response
    except TypeError as e:
        return build_error_response(request, 400, str(e))
    except ValueError as e:
        return build_error_response(request, 422, str(e))


@iwidget_router.delete(
    "/{workspace_id}/tab/{tab_id}/widget_instances/{iwidget_id}",
    summary=docs.delete_widget_instance_entry_summary,
    description=docs.delete_widget_instance_entry_description,
    status_code=204,
    response_class=Response,
    response_description=docs.delete_widget_instance_entry_response_description,
    responses={
        401: root_docs.generate_auth_required_response_openapi_description(
            docs.delete_widget_instance_entry_auth_required_response_description
        ),
        403: root_docs.generate_permission_denied_response_openapi_description(
            docs.delete_widget_instance_entry_permission_denied_response_description,
            "You have not enough permission for deleting this iwidget"
        ),
        404: root_docs.generate_not_found_response_openapi_description(
            docs.delete_widget_instance_entry_not_found_response_description
        ),
    }
)
@authentication_required()
async def delete_widget_instance_entry(db: DBDep, user: UserDep, request: Request,
                               workspace_id: Id = Path(description=docs.delete_widget_instance_entry_workspace_id_description),
                               tab_id: str = Path(description=docs.delete_widget_instance_entry_tab_id_description),
                               iwidget_id: str = Path(
                                   description=docs.delete_widget_instance_entry_widget_instance_id_description)):
    workspace = await get_workspace_by_id(db, workspace_id)
    if workspace is None:
        return build_error_response(request, 404, _("Workspace not found"))

    try:
        tab = workspace.tabs[tab_id]
    except KeyError:
        return build_error_response(request, 404, _("Tab not found"))

    try:
        iwidget = tab.widgets[iwidget_id]
    except KeyError:
        return build_error_response(request, 404, _("IWidget not found"))

    if not workspace.is_editable_by(user):
        return build_error_response(request, 403, _("You have not enough permission for deleting this iwidget"))

    if iwidget.read_only:
        return build_error_response(request, 403, _("Iwidget cannot be deleted"))

    del workspace.tabs[tab_id].widgets[iwidget_id]
    await change_workspace(db, workspace, user)

    return Response(status_code=204)


@iwidget_router.post(
    "/{workspace_id}/tab/{tab_id}/widget_instances/{iwidget_id}/preferences",
    summary=docs.update_widget_instance_preferences_summary,
    description=docs.update_widget_instance_preferences_description,
    status_code=204,
    response_class=Response,
    response_description=docs.update_widget_instance_preferences_response_description,
    responses={
        400: root_docs.generate_error_response_openapi_description(
            docs.update_widget_instance_preferences_bad_request_response_description,
            "Malformed JSON data"
        ),
        401: root_docs.generate_auth_required_response_openapi_description(
            docs.update_widget_instance_preferences_auth_required_response_description
        ),
        403: root_docs.generate_permission_denied_response_openapi_description(
            docs.update_widget_instance_preferences_permission_denied_response_description,
            "You have not enough permission for updating this iwidget"
        ),
        404: root_docs.generate_not_found_response_openapi_description(
            docs.update_widget_instance_preferences_not_found_response_description
        ),
        422: root_docs.generate_validation_error_response_openapi_description(
            docs.update_widget_instance_preferences_validation_error_response_description
        )
    }
)
@authentication_required()
@consumes(["application/json"])
async def update_widget_instance_preferences(db: DBDep, user: UserDep, request: Request, workspace_id: Id = Path(
    description=docs.update_widget_instance_preferences_workspace_id_description), tab_id: str = Path(
    description=docs.update_widget_instance_preferences_tab_id_description), iwidget_id: str = Path(
    description=docs.update_widget_instance_preferences_widget_instance_id_description), new_values: dict[str, str] = Body(
    description=docs.update_widget_instance_preferences_new_values_description,
    example=docs.update_widget_instance_preferences_new_values_example)):
    workspace = await get_workspace_by_id(db, workspace_id)
    if workspace is None:
        return build_error_response(request, 404, _("Workspace not found"))

    try:
        tab = workspace.tabs[tab_id]
    except KeyError:
        return build_error_response(request, 404, _("Tab not found"))

    try:
        iwidget = tab.widgets[iwidget_id]
    except KeyError:
        return build_error_response(request, 404, _("IWidget not found"))

    resource = await get_catalogue_resource_by_id(db, iwidget.resource)
    if resource is None:
        return build_error_response(request, 404, _("Resource not found"))

    iwidget_info = resource.get_processed_info(translate=True, process_variables=True)

    for var_name in new_values:
        try:
            vardef = iwidget_info.variables.preferences[var_name]
        except KeyError:
            return build_error_response(request, 422, _(f"Invalid preference: {var_name}"))

        if vardef.readonly:
            return build_error_response(request, 403, _(f"{var_name} preference is read only."))

        if not vardef.multiuser:
            # No multiuser -> User must have editing permissisons over the workspace
            if not workspace.is_editable_by(user):
                return build_error_response(request, 403,
                                            _(f"You have not enough permission for updating the preferences of the iwidget"))
        elif not await workspace.is_accessible_by(db, user):
            return build_error_response(request, 403,
                                        _("You have not enough permission for updating the preferences of the iwidget"))

        await iwidget.set_variable_value(db, var_name, new_values[var_name], user)

    workspace.tabs[tab_id].widgets[iwidget_id] = iwidget
    await change_workspace(db, workspace, user)

    return Response(status_code=204)


@iwidget_router.get(
    "/{workspace_id}/tab/{tab_id}/widget_instances/{iwidget_id}/preferences",
    summary=docs.get_widget_instance_preferences_summary,
    description=docs.get_widget_instance_preferences_description,
    response_model=dict[str, Any],
    response_description=docs.get_widget_instance_preferences_response_description,
    responses={
        200: {"content": {"application/json": {"example": docs.get_widget_instance_preferences_response_example}}},
        401: root_docs.generate_auth_required_response_openapi_description(
            docs.get_widget_instance_preferences_auth_required_response_description
        ),
        403: root_docs.generate_permission_denied_response_openapi_description(
            docs.get_widget_instance_preferences_permission_denied_response_description,
            "You don't have permission to access this workspace"
        ),
        404: root_docs.generate_not_found_response_openapi_description(
            docs.get_widget_instance_preferences_not_found_response_description
        ),
    }
)
@authentication_required(csrf=False)
async def get_widget_instance_preferences(db: DBDep, user: UserDepNoCSRF, request: Request, workspace_id: Id = Path(
    description=docs.get_widget_instance_preferences_workspace_id_description), tab_id: str = Path(
    description=docs.get_widget_instance_preferences_tab_id_description), iwidget_id: str = Path(
    description=docs.get_widget_instance_preferences_widget_instance_id_description)):
    workspace = await get_workspace_by_id(db, workspace_id)
    if workspace is None:
        return build_error_response(request, 404, _("Workspace not found"))

    try:
        tab = workspace.tabs[tab_id]
    except KeyError:
        return build_error_response(request, 404, _("Tab not found"))

    try:
        iwidget = tab.widgets[iwidget_id]
    except KeyError:
        return build_error_response(request, 404, _("IWidget not found"))

    if not await workspace.is_accessible_by(db, user):
        return build_error_response(request, 403, _("You don't have permission to access this workspace"))

    if iwidget.resource is None:
        return {}

    resource = await get_catalogue_resource_by_id(db, iwidget.resource)
    if resource is None:
        return build_error_response(request, 404, _("Resource not found"))

    iwidget_info = resource.get_processed_info(translate=True, process_variables=True)
    cache_manager = VariableValueCacheManager(workspace, user)
    prefs = iwidget_info.variables.preferences

    data = {var: await cache_manager.get_variable_data(db, request, "iwidget", iwidget.id, var) for var in prefs}

    return data


@iwidget_router.post(
    "/{workspace_id}/tab/{tab_id}/widget_instances/{iwidget_id}/properties",
    summary=docs.update_widget_instance_properties_summary,
    description=docs.update_widget_instance_properties_description,
    status_code=204,
    response_class=Response,
    response_description=docs.update_widget_instance_properties_response_description,
    responses={
        400: root_docs.generate_error_response_openapi_description(
            docs.update_widget_instance_properties_bad_request_response_description,
            "Malformed JSON data"
        ),
        401: root_docs.generate_auth_required_response_openapi_description(
            docs.update_widget_instance_properties_auth_required_response_description
        ),
        403: root_docs.generate_permission_denied_response_openapi_description(
            docs.update_widget_instance_properties_permission_denied_response_description,
            "You have not enough permission for updating this iwidget"
        ),
        404: root_docs.generate_not_found_response_openapi_description(
            docs.update_widget_instance_properties_not_found_response_description
        ),
        422: root_docs.generate_validation_error_response_openapi_description(
            docs.update_widget_instance_properties_validation_error_response_description
        )
    }
)
@authentication_required()
@consumes(["application/json"])
async def update_widget_instance_properties(db: DBDep, user: UserDep, request: Request, workspace_id: Id = Path(description=docs.update_widget_instance_properties_workspace_id_description),
                                    tab_id: str = Path(description=docs.update_widget_instance_properties_tab_id_description), iwidget_id: str = Path(description=docs.update_widget_instance_properties_widget_instance_id_description),
                                    new_values: dict[str, Any] = Body(description=docs.update_widget_instance_properties_new_values_description, example=docs.update_widget_instance_properties_new_values_example)):
    workspace = await get_workspace_by_id(db, workspace_id)
    if workspace is None:
        return build_error_response(request, 404, _("Workspace not found"))

    try:
        tab = workspace.tabs[tab_id]
    except KeyError:
        return build_error_response(request, 404, _("Tab not found"))

    try:
        iwidget = tab.widgets[iwidget_id]
    except KeyError:
        return build_error_response(request, 404, _("IWidget not found"))

    resource = await get_catalogue_resource_by_id(db, iwidget.resource)
    if resource is None:
        return build_error_response(request, 404, _("Resource not found"))

    iwidget_info = resource.get_processed_info(translate=True, process_variables=True)

    for var_name in new_values:
        if var_name not in iwidget_info.variables.properties:
            return build_error_response(request, 422, _(f"Invalid persistent variable: {var_name}"))

        if not iwidget_info.variables.properties[var_name].multiuser:
            # No multiuser -> User must have editing permissisons over the workspace
            if not workspace.is_editable_by(user):
                return build_error_response(request, 403,
                                            _(f"You have not enough permission for updating the persistent variables of this iwidget"))
        elif not await workspace.is_accessible_by(db, user):
            return build_error_response(request, 403,
                                        _("You have not enough permission for updating the persistent variables of this iwidget"))

        await iwidget.set_variable_value(db, var_name, new_values[var_name], user)

    workspace.tabs[tab_id].widgets[iwidget_id] = iwidget
    await change_workspace(db, workspace, user)
    return Response(status_code=204)


@iwidget_router.get(
    "/{workspace_id}/tab/{tab_id}/widget_instances/{iwidget_id}/properties",
    summary=docs.get_widget_instance_properties_summary,
    description=docs.get_widget_instance_properties_description,
    response_model=dict[str, Any],
    response_description=docs.get_widget_instance_properties_response_description,
    responses={
        200: {"content": {"application/json": {"example": docs.get_widget_instance_properties_response_example}}},
        401: root_docs.generate_auth_required_response_openapi_description(
            docs.get_widget_instance_properties_auth_required_response_description
        ),
        404: root_docs.generate_not_found_response_openapi_description(
            docs.get_widget_instance_properties_not_found_response_description
        ),
    }
)
@authentication_required(csrf=False)
async def get_widget_instance_properties(db: DBDep, user: UserDepNoCSRF, request: Request, workspace_id: Id = Path(description=docs.get_widget_instance_properties_workspace_id_description),
                                 tab_id: str = Path(description=docs.get_widget_instance_properties_tab_id_description), iwidget_id: str = Path(description=docs.get_widget_instance_properties_widget_instance_id_description)):
    workspace = await get_workspace_by_id(db, workspace_id)
    if workspace is None:
        return build_error_response(request, 404, _("Workspace not found"))

    if not await workspace.is_accessible_by(db, user):
        return build_error_response(request, 403, _("You don't have permission to access this workspace"))

    try:
        tab = workspace.tabs[tab_id]
    except KeyError:
        return build_error_response(request, 404, _("Tab not found"))

    try:
        iwidget = tab.widgets[iwidget_id]
    except KeyError:
        return build_error_response(request, 404, _("IWidget not found"))

    if iwidget.resource is None:
        return {}

    resource = await get_catalogue_resource_by_id(db, iwidget.resource)
    if resource is None:
        return build_error_response(request, 404, _("Resource not found"))

    iwidget_info = resource.get_processed_info(translate=True, process_variables=True)
    cache_manager = VariableValueCacheManager(workspace, user)
    props = iwidget_info.variables.properties

    data = {var: await cache_manager.get_variable_data(db, request, "iwidget", iwidget_id, var) for var in props}

    return data
