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

from fastapi import APIRouter, Request, Query

from src.wirecloud.commons.auth.crud import get_user_with_all_info
from src.wirecloud.commons.auth.schemas import UserAll
from src.wirecloud.commons.utils.template.schemas.macdschemas import MACD
from src.wirecloud.commons.auth.utils import UserDepNoCSRF
from src.wirecloud.commons.utils.http import produces, NotFound, build_error_response
from src.wirecloud.catalogue.crud import get_catalogue_resource_versions_for_user, get_catalogue_resource_by_id, \
    is_resource_available_for_user, get_catalogue_resource
from src.wirecloud.platform.localcatalogue import docs
from src.wirecloud.database import DBDep, Id
from src.wirecloud.platform.workspace.crud import get_workspace_by_id
from src.wirecloud.platform.workspace.models import Workspace
from src.wirecloud.translation import gettext as _
from src.wirecloud import docs as root_docs

router = APIRouter()
resources_router = APIRouter()
workspace_router = APIRouter()


@resources_router.get(
    "/",
    response_model=dict[str, MACD],
    summary=docs.get_resource_collection_summary,
    description=docs.get_resource_collection_description,
    response_description=docs.get_resource_collection_response_description,
    responses={
        # TODO Add example
        200: {"content": {"application/json": {"example": docs.get_resource_collection_response_example}}},
        406: root_docs.generate_not_acceptable_response_openapi_description(
                    docs.get_resource_collection_not_acceptable_response_description, ["application/json"]),
        422: root_docs.generate_validation_error_response_openapi_description(
            docs.get_resource_entry_group_validation_error_response_description)
    }
)
@produces(["application/json"])
async def get_resource_collection(db: DBDep, user: UserDepNoCSRF, request: Request,
                                  process_urls: bool = Query(True, description=docs.get_resource_collection_process_urls_description)):
    resources = {}
    results = await get_catalogue_resource_versions_for_user(db, user=user)
    for resource in results:
        options = resource.get_processed_info(request, process_urls=process_urls,
                                              url_pattern_name="wirecloud.showcase_media")
        resources[resource.local_uri_part] = options

    return resources

@workspace_router.get(
    "/{workspace_id}/resources",
    response_model=dict[str, MACD]
)
@produces(["application/json"])
async def get_workspace_resource_collection(db: DBDep, user: UserDepNoCSRF, request: Request, workspace_id: str, process_urls: bool = Query(True)):
    workspace: Workspace = await get_workspace_by_id(db, Id(workspace_id))
    if not workspace:
        raise NotFound("Workspace not found")

    if not await workspace.is_accsessible_by(db, user):
        return build_error_response(request, 403, _("You don't have access to this workspace"))

    creator: UserAll = await get_user_with_all_info(db, workspace.creator)

    widgets = set()
    result = {}
    for tab in workspace.tabs.values():
        for widget in tab.widgets.values():
            if not widget.id in widgets:
                resource = await get_catalogue_resource_by_id(db, widget.resource)
                if resource and await is_resource_available_for_user(db, resource, creator):
                    options = resource.get_processed_info(request, process_urls=process_urls,
                                                          url_pattern_name="wirecloud.showcase_media")
                    result[resource.local_uri_part] = options

                widgets.add(widget.id)

    for operator_id, operator in workspace.wiring_status.operators.items():
        vendor, name, version = operator.name.split('/')
        resource = await get_catalogue_resource(db, vendor, name, version)
        if resource and await is_resource_available_for_user(db, resource, creator):
            options = resource.get_processed_info(request, process_urls=process_urls,
                                                  url_pattern_name="wirecloud.showcase_media")
            result[resource.local_uri_part] = options

    return result