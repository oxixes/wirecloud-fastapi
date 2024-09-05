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

from src.wirecloud.commons.utils.template.schemas.macdschemas import MACD
from src.wirecloud.commons.auth.utils import UserDep
from src.wirecloud.commons.utils.http import produces
from src.wirecloud.catalogue.crud import get_catalogue_resource_versions_for_user
from src.wirecloud.platform.localcatalogue import docs
from src.wirecloud.database import DBDep
from src.wirecloud import docs as root_docs

router = APIRouter()
resources_router = APIRouter()


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
async def get_resource_collection(db: DBDep, user: UserDep, request: Request,
                                  process_urls: bool = Query(True, description=docs.get_resource_collection_process_urls_description)):
    resources = {}
    results = await get_catalogue_resource_versions_for_user(db, user=user)
    for resource in results:
        options = resource.get_processed_info(request, process_urls=process_urls,
                                              url_pattern_name="wirecloud.showcase_media")
        resources[resource.local_uri_part] = options

    return resources
