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
from src.wirecloud.commons.auth.utils import UserDep
from src.wirecloud.commons.utils.http import authentication_required, build_error_response, consumes, NotFound
from src.wirecloud.database import DBDep, Id
from src.wirecloud import docs as root_docs
from src.wirecloud.platform.iwidget import docs
from src.wirecloud.platform.iwidget.schemas import WidgetInstance, IWidgetData, IWidgetDataCreate, IWidgetDataUpdate
from src.wirecloud.platform.iwidget.utils import save_iwidget, update_iwidget, update_iwidget_ids
from src.wirecloud.platform.workspace.crud import get_workspace_by_id, change_workspace
from src.wirecloud.platform.workspace.utils import VariableValueCacheManager, get_iwidget_data

iwidget_router = APIRouter()


@iwidget_router.get(
    "/{workspace_id}/tab/{tab_position}/iwidgets/",
    summary=docs.get_iwidget_collection_summary,
    description=docs.get_iwidget_collection_description,
    response_model=list[IWidgetData],
    response_description=docs.get_iwidget_collection_response_description,
    responses={
        200: {"content": {"application/json": {"example": docs.get_iwidget_collection_response_example}}},
        401: root_docs.generate_auth_required_response_openapi_description(
            docs.get_iwidget_collection_auth_required_response_description
        ),
        403: root_docs.generate_permission_denied_response_openapi_description(
            docs.get_iwidget_collection_permission_denied_response_description,
            "You don't have permission to access this workspace"
        ),
        404: root_docs.generate_not_found_response_openapi_description(
            docs.get_iwidget_collection_not_found_response_description
        ),
    }
)
@authentication_required
async def get_iwidget_collection(db: DBDep, user: UserDep, request: Request, workspace_id: Id = Path(
    description=docs.get_iwidget_collection_workspace_id_description),
                                 tab_position: int = docs.get_iwidget_collection_tab_position_description):
    workspace = await get_workspace_by_id(db, workspace_id)
    if workspace is None:
        return build_error_response(request, 404, "Workspace not found")

    try:
        tab = workspace.tabs[tab_position]
    except IndexError:
        return build_error_response(request, 404, "Tab not found")

    if not await workspace.is_accsessible_by(db, user):
        return build_error_response(request, 403, "You don't have permission to access this workspace")

    cache_manager = VariableValueCacheManager(workspace, user)
    iwidgets = tab.widgets
    data = [await get_iwidget_data(db, request, WidgetInstance(**iwidget.model_dump()), workspace, cache_manager) for
            iwidget in
            iwidgets]
    return data


@iwidget_router.post(
    "/{workspace_id}/tab/{tab_position}/iwidgets/",
    summary=docs.create_iwidget_collection_summary,
    description=docs.create_iwidget_collection_description,
    response_model=IWidgetData,
    response_description=docs.create_iwidget_collection_response_description,
    responses={
        200: {"content": {"application/json": {"example": docs.create_iwidget_collection_response_example}}},
        401: root_docs.generate_auth_required_response_openapi_description(
            docs.create_iwidget_collection_auth_required_response_description
        ),
        403: root_docs.generate_permission_denied_response_openapi_description(
            docs.create_iwidget_collection_permission_denied_response_description,
            "You have not enough permission for adding iwidgets to the workspace"
        ),
        406: root_docs.generate_not_acceptable_response_openapi_description(
            docs.create_iwidget_collection_not_acceptable_response_description,
            ["application/json"]
        ),
        404: root_docs.generate_not_found_response_openapi_description(
            docs.create_iwidget_collection_not_found_response_description
        ),
        422: root_docs.generate_validation_error_response_openapi_description(
            docs.create_iwidget_collection_validation_error_response_description
        )
    }
)
@authentication_required
@consumes(["application/json"])
async def create_iwidget_collection(db: DBDep, user: UserDep, request: Request, workspace_id: Id = Path(
    description=docs.create_iwidget_collection_workspace_id_description), tab_position: int = Path(
    description=docs.create_iwidget_collection_tab_position_description),
                                    iwidget: IWidgetDataCreate = Body(
                                        example=docs.create_iwidget_collection_iwidget_example,
                                        description=docs.create_iwidget_collection_iwidget_description)):
    initial_variable_values = iwidget.variable_values
    workspace = await get_workspace_by_id(db, workspace_id)
    if workspace is None:
        return build_error_response(request, 404, "Workspace not found")
    try:
        tab = workspace.tabs[tab_position]
    except IndexError:
        return build_error_response(request, 404, "Tab not found")

    if not workspace.is_editable_by(user):
        return build_error_response(request, 403, "You have not enough permission for adding iwidgets to the workspace")
    try:
        iwidget = await save_iwidget(db, workspace, iwidget, user, tab, initial_variable_values)

        iwidget_data = await get_iwidget_data(db, request, iwidget, workspace, user=user)

        return iwidget_data
    except NotFound:
        return build_error_response(request, 422, f"Referred widget {iwidget.resource} does not exist.")
    except TypeError as e:
        return build_error_response(request, 400, str(e))
    except ValueError as e:
        return build_error_response(request, 422, str(e))


@iwidget_router.put(
    "/{workspace_id}/tab/{tab_position}/iwidgets/",
    summary=docs.update_iwidget_collection_summary,
    description=docs.update_iwidget_collection_description,
    status_code=204,
    response_class=Response,
    response_description=docs.update_iwidget_collection_response_description,
    responses={
        400: root_docs.generate_error_response_openapi_description(
            docs.update_iwidget_collection_bad_request_response_description,
            "Malformed JSON data"
        ),
        401: root_docs.generate_auth_required_response_openapi_description(
            docs.update_iwidget_collection_auth_required_response_description
        ),
        403: root_docs.generate_permission_denied_response_openapi_description(
            docs.update_iwidget_collection_permission_denied_response_description,
            "You have not enough permission for updating the iwidgets of this workspace"
        ),
        404: root_docs.generate_not_found_response_openapi_description(
            docs.update_iwidget_collection_not_found_response_description
        ),
        422: root_docs.generate_validation_error_response_openapi_description(
            docs.update_iwidget_collection_validation_error_response_description
        )
    }
)
@authentication_required
@consumes(["application/json"])
async def update_iwidget_collection(db: DBDep, user: UserDep, request: Request, workspace_id: Id = Path(
    description=docs.update_iwidget_collection_workspace_id_description),
                                    tab_position: int = Path(
                                        description=docs.update_iwidget_collection_tab_position_description),
                                    iwidgets: list[IWidgetDataUpdate] = Body(
                                        description=docs.update_iwidget_collection_iwidget_description,
                                        example=docs.update_iwidget_collection_iwidget_example)):
    workspace = await get_workspace_by_id(db, workspace_id)
    if workspace is None:
        return build_error_response(request, 404, "Workspace not found")

    try:
        tab = workspace.tabs[tab_position]
    except IndexError:
        return build_error_response(request, 404, "Tab not found")

    if not workspace.is_editable_by(user):
        return build_error_response(request, 403,
                                    "You have not enough permission for updating the iwidgets of this workspace")

    for iwidget in iwidgets:
        try:
            await update_iwidget(db, iwidget, user, workspace, tab, update_cache=False)
        except TypeError as e:
            return build_error_response(request, 400, str(e))
        except ValueError as e:
            return build_error_response(request, 422, str(e))

    if len(iwidgets) > 0:
        await change_workspace(db, workspace, user)

    await db.commit_transaction()

    return Response(status_code=204)


@iwidget_router.get(
    "/{workspace_id}/tab/{tab_position}/iwidgets/{iwidget_position}",
    summary=docs.get_iwidget_entry_summary,
    description=docs.get_iwidget_entry_description,
    response_model=IWidgetData,
    response_description=docs.get_iwidget_entry_response_description,
    responses={
        200: {"content": {"application/json": {"example": docs.get_iwidget_entry_response_example}}},
        401: root_docs.generate_auth_required_response_openapi_description(
            docs.get_iwidget_entry_auth_required_response_description
        ),
        404: root_docs.generate_not_found_response_openapi_description(
            docs.get_iwidget_entry_not_found_response_description
        ),
    }
)
@authentication_required
async def get_iwidget_entry(db: DBDep, user: UserDep, request: Request,
                            workspace_id: Id = Path(description=docs.get_iwidget_entry_workspace_id_description),
                            tab_position: int = Path(description=docs.get_iwidget_entry_tab_position_description),
                            iwidget_position: int = Path(
                                description=docs.get_iwidget_entry_iwidget_position_description)):
    workspace = await get_workspace_by_id(db, workspace_id)
    if workspace is None:
        return build_error_response(request, 404, "Workspace not found")

    try:
        tab = workspace.tabs[tab_position]
    except IndexError:
        return build_error_response(request, 404, "Tab not found")

    try:
        iwidget = tab.widgets[iwidget_position]
    except IndexError:
        return build_error_response(request, 404, "IWidget not found")

    return await get_iwidget_data(db, request, WidgetInstance(**iwidget.model_dump()), workspace, user=user)


@iwidget_router.post(
    "/{workspace_id}/tab/{tab_position}/iwidgets/{iwidget_position}",
    summary=docs.update_iwidget_entry_summary,
    description=docs.update_iwidget_entry_description,
    status_code=204,
    response_class=Response,
    response_description=docs.update_iwidget_entry_response_description,
    responses={
        400: root_docs.generate_error_response_openapi_description(
            docs.update_iwidget_entry_bad_request_response_description,
            "Malformed JSON data"
        ),
        401: root_docs.generate_auth_required_response_openapi_description(
            docs.update_iwidget_entry_auth_required_response_description
        ),
        403: root_docs.generate_permission_denied_response_openapi_description(
            docs.update_iwidget_entry_permission_denied_response_description,
            "You have not enough permission for updating this iwidget"
        ),
        404: root_docs.generate_not_found_response_openapi_description(
            docs.update_iwidget_entry_not_found_response_description
        ),
        422: root_docs.generate_validation_error_response_openapi_description(
            docs.update_iwidget_entry_validation_error_response_description
        )
    }
)
@authentication_required
@consumes(["application/json"])
async def update_iwidget_entry(db: DBDep, user: UserDep, request: Request,
                               workspace_id: Id = Path(description=docs.update_iwidget_entry_workspace_id_description),
                               tab_position: int = Path(description=docs.update_iwidget_entry_tab_position_description),
                               iwidget_position: int = Path(
                                   description=docs.update_iwidget_entry_iwidget_position_description),
                               iwidget_data: IWidgetDataUpdate = Body(
                                   description=docs.update_iwidget_entry_iwidget_description,
                                   example=docs.update_iwidget_entry_iwidget_example)):
    workspace = await get_workspace_by_id(db, workspace_id)
    if workspace is None:
        return build_error_response(request, 404, "Workspace not found")

    try:
        tab = workspace.tabs[tab_position]
    except IndexError:
        return build_error_response(request, 404, "Tab not found")

    try:
        iwidget = tab.widgets[iwidget_position]
    except IndexError:
        return build_error_response(request, 404, "IWidget not found")

    if not workspace.is_editable_by(user):
        return build_error_response(request, 403, "You have not enough permission for updating the iwidget")

    iwidget_data.id = iwidget_position
    try:
        await update_iwidget(db, iwidget_data, user, workspace, tab)
    except TypeError as e:
        return build_error_response(request, 400, str(e))
    except ValueError as e:
        return build_error_response(request, 422, str(e))

    await db.commit_transaction()


@iwidget_router.delete(
    "/{workspace_id}/tab/{tab_position}/iwidgets/{iwidget_position}",
    summary=docs.delete_iwidget_entry_summary,
    description=docs.delete_iwidget_entry_description,
    status_code=204,
    response_class=Response,
    response_description=docs.delete_iwidget_entry_response_description,
    responses={
        401: root_docs.generate_auth_required_response_openapi_description(
            docs.delete_iwidget_entry_auth_required_response_description
        ),
        403: root_docs.generate_permission_denied_response_openapi_description(
            docs.delete_iwidget_entry_permission_denied_response_description,
            "You have not enough permission for deleting this iwidget"
        ),
        404: root_docs.generate_not_found_response_openapi_description(
            docs.delete_iwidget_entry_not_found_response_description
        ),
    }
)
@authentication_required
async def delete_iwidget_entry(db: DBDep, user: UserDep, request: Request,
                               workspace_id: Id = Path(description=docs.delete_iwidget_entry_workspace_id_description),
                               tab_position: int = Path(description=docs.delete_iwidget_entry_tab_position_description),
                               iwidget_position: int = Path(
                                   description=docs.delete_iwidget_entry_iwidget_position_description)):
    workspace = await get_workspace_by_id(db, workspace_id)
    if workspace is None:
        return build_error_response(request, 404, "Workspace not found")

    try:
        tab = workspace.tabs[tab_position]
    except IndexError:
        return build_error_response(request, 404, "Tab not found")

    try:
        iwidget = tab.widgets[iwidget_position]
    except IndexError:
        return build_error_response(request, 404, "IWidget not found")

    if not workspace.is_editable_by(user):
        return build_error_response(request, 403, "You have not enough permission for deleting this iwidget")

    if iwidget.read_only:
        return build_error_response(request, 403, "Iwidget cannot be deleted")

    tab.widgets.pop(iwidget_position)
    update_iwidget_ids(workspace, tab)
    await change_workspace(db, workspace, user)
    await db.commit_transaction()

    return Response(status_code=204)


@iwidget_router.post(
    "/{workspace_id}/tab/{tab_position}/iwidgets/{iwidget_position}/preferences",
    summary=docs.update_iwidget_preferences_summary,
    description=docs.update_iwidget_preferences_description,
    status_code=204,
    response_class=Response,
    response_description=docs.update_iwidget_preferences_response_description,
    responses={
        400: root_docs.generate_error_response_openapi_description(
            docs.update_iwidget_preferences_bad_request_response_description,
            "Malformed JSON data"
        ),
        401: root_docs.generate_auth_required_response_openapi_description(
            docs.update_iwidget_preferences_auth_required_response_description
        ),
        403: root_docs.generate_permission_denied_response_openapi_description(
            docs.update_iwidget_preferences_permission_denied_response_description,
            "You have not enough permission for updating this iwidget"
        ),
        404: root_docs.generate_not_found_response_openapi_description(
            docs.update_iwidget_preferences_not_found_response_description
        ),
        422: root_docs.generate_validation_error_response_openapi_description(
            docs.update_iwidget_preferences_validation_error_response_description
        )
    }
)
@authentication_required
@consumes(["application/json"])
async def update_iwidget_preferences(db: DBDep, user: UserDep, request: Request, workspace_id: Id = Path(
    description=docs.update_iwidget_preferences_workspace_id_description), tab_position: int = Path(
    description=docs.update_iwidget_preferences_tab_position_description), iwidget_position: int = Path(
    description=docs.update_iwidget_preferences_iwidget_position_description), new_values: dict[str, Any] = Body(
    description=docs.update_iwidget_preferences_new_values_description,
    example=docs.update_iwidget_preferences_new_values_example)):
    workspace = await get_workspace_by_id(db, workspace_id)
    if workspace is None:
        return build_error_response(request, 404, "Workspace not found")

    try:
        tab = workspace.tabs[tab_position]
    except IndexError:
        return build_error_response(request, 404, "Tab not found")

    try:
        iwidget = WidgetInstance(**tab.widgets[iwidget_position].model_dump())
    except IndexError:
        return build_error_response(request, 404, "IWidget not found")

    resource = await get_catalogue_resource_by_id(db, iwidget.resource)
    if resource is None:
        return build_error_response(request, 404, "Resource not found")

    iwidget_info = resource.get_processed_info(translate=True, process_variables=True)

    for var_name in new_values:
        try:
            vardef = iwidget_info.variables.preferences[var_name]
        except KeyError:
            return build_error_response(request, 422, f"Invalid preference: {var_name}")

        if vardef.readonly:
            return build_error_response(request, 403, f"{var_name} preference is read only.")

        if not vardef.multiuser:
            # No multiuser -> User must have editing permissisons over the workspace
            if not workspace.is_editable_by(user):
                return build_error_response(request, 403,
                                            f"You have not enough permission for updating the preferences of the iwidget")
        elif not await workspace.is_accsessible_by(db, user):
            return build_error_response(request, 403,
                                        "You have not enough permission for updating the preferences of the iwidget")

        print(f"Setting {var_name} to {new_values[var_name]}")
        print(iwidget.variables)
        await iwidget.set_variable_value(db, var_name, new_values[var_name], user)
        print()
        print(iwidget.variables)

    workspace.tabs[tab_position].widgets[iwidget_position] = iwidget
    await change_workspace(db, workspace, user)
    await db.commit_transaction()

    return Response(status_code=204)


@iwidget_router.get(
    "/{workspace_id}/tab/{tab_position}/iwidgets/{iwidget_position}/preferences",
    summary=docs.get_iwidget_preferences_summary,
    description=docs.get_iwidget_preferences_description,
    response_model=dict[str, Any],
    response_description=docs.get_iwidget_preferences_response_description,
    responses={
        200: {"content": {"application/json": {"example": docs.get_iwidget_preferences_response_example}}},
        401: root_docs.generate_auth_required_response_openapi_description(
            docs.get_iwidget_preferences_auth_required_response_description
        ),
        403: root_docs.generate_permission_denied_response_openapi_description(
            docs.get_iwidget_preferences_permission_denied_response_description,
            "You don't have permission to access this workspace"
        ),
        404: root_docs.generate_not_found_response_openapi_description(
            docs.get_iwidget_preferences_not_found_response_description
        ),
    }
)
@authentication_required
async def get_iwidget_preferences(db: DBDep, user: UserDep, request: Request, workspace_id: Id = Path(
    description=docs.get_iwidget_preferences_workspace_id_description), tab_position: int = Path(
    description=docs.get_iwidget_preferences_tab_position_description), iwidget_position: int = Path(
    description=docs.get_iwidget_preferences_iwidget_position_description)):
    workspace = await get_workspace_by_id(db, workspace_id)
    if workspace is None:
        return build_error_response(request, 404, "Workspace not found")

    try:
        tab = workspace.tabs[tab_position]
    except IndexError:
        return build_error_response(request, 404, "Tab not found")

    try:
        iwidget = WidgetInstance(**tab.widgets[iwidget_position].model_dump())
    except IndexError:
        return build_error_response(request, 404, "IWidget not found")

    if not await workspace.is_accsessible_by(db, user):
        return build_error_response(request, 403, "You don't have permission to access this workspace")

    resource = await get_catalogue_resource_by_id(db, iwidget.resource)
    if resource is None:
        return build_error_response(request, 404, "Resource not found")

    iwidget_info = resource.get_processed_info(translate=True, process_variables=True)
    cache_manager = VariableValueCacheManager(workspace, user)
    prefs = iwidget_info.variables.preferences

    data = {var: await cache_manager.get_variable_data(db, request, "iwidget", iwidget.id, var) for var in prefs}


    return data


@iwidget_router.post(
    "/{workspace_id}/tab/{tab_position}/iwidgets/{iwidget_position}/properties",
    summary=docs.update_iwidget_properties_summary,
    description=docs.update_iwidget_properties_description,
    status_code=204,
    response_class=Response,
    response_description=docs.update_iwidget_properties_response_description,
    responses={
        400: root_docs.generate_error_response_openapi_description(
            docs.update_iwidget_properties_bad_request_response_description,
            "Malformed JSON data"
        ),
        401: root_docs.generate_auth_required_response_openapi_description(
            docs.update_iwidget_properties_auth_required_response_description
        ),
        403: root_docs.generate_permission_denied_response_openapi_description(
            docs.update_iwidget_properties_permission_denied_response_description,
            "You have not enough permission for updating this iwidget"
        ),
        404: root_docs.generate_not_found_response_openapi_description(
            docs.update_iwidget_properties_not_found_response_description
        ),
        422: root_docs.generate_validation_error_response_openapi_description(
            docs.update_iwidget_properties_validation_error_response_description
        )
    }
)
@authentication_required
@consumes(["application/json"])
async def update_iwidget_properties(db: DBDep, user: UserDep, request: Request, workspace_id: Id = Path(),
                                    tab_position: int = Path(), iwidget_position: int = Path(),
                                    new_values: dict[str, Any] = Body()):
    workspace = await get_workspace_by_id(db, workspace_id)
    if workspace is None:
        return build_error_response(request, 404, "Workspace not found")

    try:
        tab = workspace.tabs[tab_position]
    except IndexError:
        return build_error_response(request, 404, "Tab not found")

    try:
        iwidget = WidgetInstance(**tab.widgets[iwidget_position].model_dump())
    except IndexError:
        return build_error_response(request, 404, "IWidget not found")

    resource = await get_catalogue_resource_by_id(db, iwidget.resource)
    if resource is None:
        return build_error_response(request, 404, "Resource not found")

    iwidget_info = resource.get_processed_info(translate=True, process_variables=True)

    for var_name in new_values:
        if var_name not in iwidget_info.variables.properties:
            return build_error_response(request, 422, f"Invalid persistent variable: {var_name}")

        if not iwidget_info.variables.properties[var_name].multiuser:
            # No multiuser -> User must have editing permissisons over the workspace
            if not workspace.is_editable_by(user):
                return build_error_response(request, 403,
                                            f"You have not enough permission for updating the persistent variables of this iwidget")
        elif not await workspace.is_accsessible_by(db, user):
            return build_error_response(request, 403,
                                        "You have not enough permission for updating the persistent variables of this iwidget")

        await iwidget.set_variable_value(db, var_name, new_values[var_name], user)

    workspace.tabs[tab_position].widgets[iwidget_position] = iwidget
    await change_workspace(db, workspace, user)
    await db.commit_transaction()
    return Response(status_code=204)


@iwidget_router.get(
    "/{workspace_id}/tab/{tab_position}/iwidgets/{iwidget_position}/properties",
    summary=docs.get_iwidget_properties_summary,
    description=docs.get_iwidget_properties_description,
    response_model=dict[str, Any],
    response_description=docs.get_iwidget_properties_response_description,
    responses={
        200: {"content": {"application/json": {"example": docs.get_iwidget_properties_response_example}}},
        401: root_docs.generate_auth_required_response_openapi_description(
            docs.get_iwidget_properties_auth_required_response_description
        ),
        404: root_docs.generate_not_found_response_openapi_description(
            docs.get_iwidget_properties_not_found_response_description
        ),
    }
)
@authentication_required
async def get_iwidget_properties(db: DBDep, user: UserDep, request: Request, workspace_id: Id = Path(),
                                 tab_position: int = Path(), iwidget_position: int = Path()):
    workspace = await get_workspace_by_id(db, workspace_id)
    if workspace is None:
        return build_error_response(request, 404, "Workspace not found")

    if not await workspace.is_accsessible_by(db, user):
        return build_error_response(request, 403, "You don't have permission to access this workspace")

    try:
        tab = workspace.tabs[tab_position]
    except IndexError:
        return build_error_response(request, 404, "Tab not found")

    try:
        iwidget = WidgetInstance(**tab.widgets[iwidget_position].model_dump())
    except IndexError:
        return build_error_response(request, 404, "IWidget not found")

    resource = await get_catalogue_resource_by_id(db, iwidget.resource)
    if resource is None:
        return build_error_response(request, 404, "Resource not found")

    iwidget_info = resource.get_processed_info(translate=True, process_variables=True)
    cache_manager = VariableValueCacheManager(workspace, user)
    props = iwidget_info.variables.properties

    data = {}
    data = {var: await cache_manager.get_variable_data(db, request, "iwidget", iwidget_position, var) for var in props}

    return data
