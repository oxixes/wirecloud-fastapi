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

import re

import jsonpatch

from fastapi import APIRouter, Request, Path, Body, Response, Query

from wirecloud.settings import cache
from wirecloud import docs as root_docs
from wirecloud.catalogue.crud import get_catalogue_resource
from wirecloud.catalogue.schemas import CatalogueResourceType
from wirecloud.commons.auth.crud import get_user_with_all_info
from wirecloud.commons.auth.utils import UserDep, UserDepNoCSRF
from wirecloud.commons.utils.cache import CacheableData
from wirecloud.commons.utils.http import authentication_required, consumes, build_error_response, \
    get_current_domain, get_absolute_reverse_url
from wirecloud.database import DBDep, Id
from wirecloud.platform.wiring.schemas import WiringEntryPatch, WiringOperatorVariables
from wirecloud.platform.wiring import docs
from wirecloud.platform.wiring.utils import check_wiring, check_multiuser_wiring, get_operator_cache_key, \
    generate_xhtml_operator_code, process_requirements
from wirecloud.platform.workspace.crud import get_workspace_by_id, change_workspace
from wirecloud.platform.workspace.models import WorkspaceWiring
from wirecloud.platform.workspace.utils import VariableValueCacheManager
from wirecloud.translation import gettext as _

wiring_router = APIRouter()
operator_router = APIRouter()

OPERATOR_PATH_RE = re.compile(r'^/?operators/(?P<operator_id>[0-9]+)/(preferences/|properties/)', re.S)


@wiring_router.put(
    "/{workspace_id}/wiring",
    summary=docs.update_wiring_entry_summary,
    description=docs.update_wiring_entry_description,
    status_code=204,
    response_class=Response,
    response_description=docs.update_wiring_entry_response_description,
    responses={
        401: root_docs.generate_auth_required_response_openapi_description(
            docs.update_wiring_entry_auth_required_response_description
        ),
        403: root_docs.generate_permission_denied_response_openapi_description(
            docs.update_wiring_entry_permission_denied_response_description,
            "You are not allowed to update this workspace"
        ),
        404: root_docs.generate_not_found_response_openapi_description(
            docs.update_wiring_entry_not_found_response_description
        ),
        422: root_docs.generate_validation_error_response_openapi_description(
            docs.update_wiring_entry_validation_error_response_description
        )
    }
)
@authentication_required()
@consumes(["application/json"])
async def update_wiring_entry(db: DBDep, request: Request, user: UserDep,
                              workspace_id: Id = Path(description=docs.update_wiring_entry_workspace_id_description),
                              new_wiring_status: WorkspaceWiring = Body(
                                  description=docs.update_wiring_entry_wiring_description,
                                  example=docs.update_wiring_entry_wiring_example)):
    workspace = await get_workspace_by_id(db, workspace_id)
    if workspace is None:
        return build_error_response(request, 404, _('Workspace not found'))

    old_wiring_status = workspace.wiring_status

    if workspace.is_editable_by(user):
        result = await check_wiring(db, request, user, new_wiring_status, old_wiring_status, can_update_secure=False)
    elif await workspace.is_accessible_by(db, user):
        result = await check_multiuser_wiring(db, request, user, new_wiring_status, old_wiring_status,
                                              workspace.creator, can_update_secure=False)
    else:
        return build_error_response(request, 403, _('You are not allowed to update this workspace'))

    if not result or isinstance(result, Response):
        return result

    workspace.wiring_status = new_wiring_status
    await change_workspace(db, workspace, user)

    return Response(status_code=204)


@wiring_router.patch(
    "/{workspace_id}/wiring",
    summary=docs.patch_wiring_entry_summary,
    description=docs.patch_wiring_entry_description,
    status_code=204,
    response_class=Response,
    response_description=docs.patch_wiring_entry_response_description,
    responses={
        401: root_docs.generate_auth_required_response_openapi_description(
            docs.patch_wiring_entry_auth_required_response_description
        ),
        403: root_docs.generate_permission_denied_response_openapi_description(
            docs.patch_wiring_entry_permission_denied_response_description,
            "You are not allowed to update this workspace"
        ),
        404: root_docs.generate_not_found_response_openapi_description(
            docs.patch_wiring_entry_not_found_response_description
        ),
        422: root_docs.generate_validation_error_response_openapi_description(
            docs.patch_wiring_entry_validation_error_response_description
        )
    }
)
@authentication_required()
@consumes(['application/json-patch+json'])
async def patch_wiring_entry(db: DBDep, request: Request, user: UserDep,
                             workspace_id: Id = Path(description=docs.patch_wiring_entry_workspace_id_description),
                             req: list[WiringEntryPatch] = Body(description=docs.patch_wiring_entry_wiring_description,
                                                                example=docs.patch_wiring_entry_wiring_example,
                                                                media_type='application/json-patch+json')):
    workspace = await get_workspace_by_id(db, workspace_id)
    if workspace is None:
        return build_error_response(request, 404, _('Workspace not found'))
    old_wiring_status = workspace.wiring_status

    # Can't explicitly update missing operator preferences / properties
    # Check if it's modifying directly a preference / property
    for p in req:
        result = OPERATOR_PATH_RE.match(p.path)
        if result is not None:
            try:
                vendor, name, version = workspace.wiring_status.operators[result.group("operator_id")].name.split("/")
            except ValueError:
                return build_error_response(request, 404, _('Operator not found'))

            # If the operator is missing -> 403
            resource = await get_catalogue_resource(db, vendor, name, version)
            if resource is None:
                return build_error_response(request, 403, _('Missing operators variables cannot be updated'))

    try:
        patches = [p.model_dump() for p in req]
        res_js = jsonpatch.apply_patch(old_wiring_status.model_dump(), patches)
        new_wiring_status = WorkspaceWiring.model_validate(res_js)
    except jsonpatch.JsonPointerException:
        return build_error_response(request, 422, _('Failed to apply patch'))
    except jsonpatch.InvalidJsonPatch:
        return build_error_response(request, 400, _('Invalid JSON patch'))

    if workspace.is_editable_by(user):
        result = await check_wiring(db, request, user, new_wiring_status, old_wiring_status, can_update_secure=True)
    elif await workspace.is_accessible_by(db, user):
        result = await check_multiuser_wiring(db, request, user, new_wiring_status, old_wiring_status,
                                              workspace.creator,
                                              can_update_secure=True)
    else:
        return build_error_response(request, 403, _('You are not allowed to update this workspace'))

    if not result:
        return result

    workspace.wiring_status = new_wiring_status
    await change_workspace(db, workspace, user)

    return Response(status_code=204)


@operator_router.get(
    "/{vendor}/{name}/{version}/html",
    summary=docs.get_operator_summary,
    description=docs.get_operator_description,
    response_description=docs.get_operator_response_description,
    responses={
        200: {"content": {"application/xhtml+xml": {"example": docs.get_operator_response_example}}},
        404: root_docs.generate_not_found_response_openapi_description(
            docs.get_operator_not_found_response_description
        )
    }
)
async def get_operator_html(db: DBDep, request: Request,
                            vendor: str = Path(description=docs.get_operator_vendor_description),
                            name: str = Path(description=docs.get_operator_name_description),
                            version: str = Path(description=docs.get_operator_version_description),
                            mode: str = Query(default='classic', description=docs.get_operator_mode_description)):
    operator = await get_catalogue_resource(db, vendor, name, version, CatalogueResourceType.operator)
    if operator is None:
        return build_error_response(request, 404, _('Operator not found'))

    key = get_operator_cache_key(operator, get_current_domain(request), mode)
    cached_response = await cache.get(key)
    if cached_response is None:
        options = operator.description
        js_files = options.js_files

        base_url = get_absolute_reverse_url('wirecloud.showcase_media', request=request, vendor=operator.vendor, name=operator.short_name, version=operator.version, path=operator.template_uri)
        xhtml = await generate_xhtml_operator_code(js_files, base_url, request,
                                                   process_requirements(options.requirements), mode)
        cache_timeout = 31536000  # 1 year
        cached_response = CacheableData(data=xhtml, timeout=cache_timeout,
                                        content_type='application/xhtml+xml; charset=utf-8')

        await cache.set(key, cached_response, cache_timeout)

    return cached_response.get_response()


# TODO Check this, why is it needed?
from wirecloud.platform.workspace.schemas import CacheVariableData

WiringOperatorVariables.model_rebuild()


@wiring_router.get(
    "/{workspace_id}/operators/{operator_id}/variables",
    summary=docs.get_operator_variables_entry_summary,
    description=docs.get_operator_variables_entry_description,
    response_model=WiringOperatorVariables,
    response_description=docs.get_operator_variables_entry_response_description,
    responses={
        200: {"content": {"application/json": {"example": docs.get_operator_variables_entry_response_example}}},
        401: root_docs.generate_auth_required_response_openapi_description(
            docs.get_operator_variables_entry_auth_required_response_description
        ),
        403: root_docs.generate_permission_denied_response_openapi_description(
            docs.get_operator_variables_entry_permission_denied_response_description,
            "You are not allowed to access this workspace"
        ),
        404: root_docs.generate_not_found_response_openapi_description(
            docs.get_operator_variables_entry_not_found_response_description
        )
    }
)
@authentication_required(csrf=False)
async def get_operator_variables_entry(db: DBDep, request: Request, user: UserDepNoCSRF, workspace_id: Id = Path(
    description=docs.get_operator_variables_entry_workspace_id_description),
                                       operator_id: str = Path(
                                           description=docs.get_operator_variables_entry_operator_id_description)):
    workspace = await get_workspace_by_id(db, workspace_id)
    if workspace is None:
        return build_error_response(request, 404, _('Workspace not found'))

    if not await workspace.is_accessible_by(db, user):
        return build_error_response(request, 403, _("You don't have permission to access this workspace"))

    cache_manager = VariableValueCacheManager(workspace, user)

    try:
        operator = workspace.wiring_status.operators[operator_id]
        vendor, name, version = operator.name.split("/")
    except (KeyError, ValueError):
        return build_error_response(request, 404, _('Operator not found'))

    data = WiringOperatorVariables()
    resource = await get_catalogue_resource(db, vendor, name, version)

    if resource is None:
        return data
    elif not await resource.is_available_for(db, await get_user_with_all_info(db, workspace.creator)):
        return build_error_response(request, 404, _('Operator not found'))

    for preference_name, preference in operator.preferences.items():
        data.preferences[preference_name] = await cache_manager.get_variable_data(db, request, 'ioperator', operator_id,
                                                                                  preference_name)

    for property_name, prop in operator.properties.items():
        data.properties[property_name] = await cache_manager.get_variable_data(db, request, 'ioperator', operator_id,
                                                                               property_name)

    return data
