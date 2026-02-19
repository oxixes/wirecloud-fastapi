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

import os

from bson import ObjectId
from fastapi import APIRouter, Request, Body, Path, Response

from wirecloud.platform.markets.schemas import MarketData, MarketCreate, Market, PublishData, MarketPermissions
from wirecloud.platform.markets import docs
from wirecloud.platform.markets.crud import (get_markets_for_user, get_market_user, create_market,
                                                 delete_market_by_name)
from wirecloud.platform.markets.utils import get_market_managers
from wirecloud.commons.auth.crud import get_user_by_username, get_user_with_all_info_by_username
from wirecloud.commons.utils.http import produces, consumes, authentication_required, build_error_response
from wirecloud.commons.auth.utils import UserDep, UserDepNoCSRF
from wirecloud.commons.utils.wgt import WgtFile
from wirecloud.catalogue.crud import get_catalogue_resource
from wirecloud.catalogue import utils as catalogue
from wirecloud import docs as root_docs
from wirecloud.database import DBDep
from wirecloud.translation import gettext as _

router = APIRouter()
markets_router = APIRouter()


@markets_router.get(
    "/",
    summary=docs.get_market_collection_summary,
    description=docs.get_market_collection_description,
    response_model=list[MarketData],
    response_description=docs.get_market_collection_response_description,
    responses={
        200: {"content": {"application/json": {"example": docs.get_market_collection_response_example}}},
        401: root_docs.generate_auth_required_response_openapi_description(
            docs.get_market_collection_auth_required_response_description),
        406: root_docs.generate_not_acceptable_response_openapi_description(
            docs.get_market_collection_not_acceptable_response_description, ["application/json"])
    }
)
@produces(["application/json"])
@authentication_required(csrf=False)
async def get_market_collection(db: DBDep, user: UserDepNoCSRF, _request: Request):
    result = []

    for market in await get_markets_for_user(db, user):
        market_data = MarketData(**market.options.model_dump(), permissions=MarketPermissions(
            delete=user.is_superuser or market.user_id == user.id
        ))
        market_data.name = market.name
        market_data.user = (await get_market_user(db, market)).username
        market_data.public = market.public

        result.append(market_data)

    return result

@markets_router.post(
    "/",
    summary=docs.create_market_collection_summary,
    description=docs.create_market_collection_description,
    status_code=201,
    response_class=Response,
    response_description=docs.create_market_collection_response_description,
    responses={
        401: root_docs.generate_auth_required_response_openapi_description(
            docs.create_market_collection_auth_required_response_description),
        403: root_docs.generate_permission_denied_response_openapi_description(
            docs.create_market_collection_permission_denied_response_description,
            "You don't have permissions for adding marketplaces in name of other user"),
        406: root_docs.generate_not_acceptable_response_openapi_description(
            docs.create_market_collection_not_acceptable_response_description, ["application/json"]),
        409: root_docs.generate_error_response_openapi_description(
            docs.create_market_collection_conflict_response_description,
            "Resource already exists"),
        415: root_docs.generate_unsupported_media_type_response_openapi_description(
            docs.create_market_collection_unsupported_media_type_response_description),
        422: root_docs.generate_validation_error_response_openapi_description(
            docs.create_market_collection_validation_error_response_description)
    }
)
@authentication_required()
@consumes(["application/json"])
@produces(["application/json"])
async def create_market_collection(db: DBDep, user: UserDep, request: Request,
                                   market: MarketCreate = Body(
                                       description=docs.create_market_collection_market_description,
                                       examples=[docs.create_market_collection_market_example])):
    # TODO More complex user permissions

    if market.user is None or market.user == user.username:
        target_user = user
    else:
        target_user = await get_user_with_all_info_by_username(db, market.user)
        if target_user is None:
            return build_error_response(request, 422, _("invalid user option"))

    if target_user.id != user.id and (not user.is_superuser and not user.has_perm("MARKETPLACE.CREATE")):
        return build_error_response(request, 403, _("You don't have permissions for adding marketplaces in name of other user"))

    market.user = target_user.username

    success = await create_market(db, Market(
        id=ObjectId(),
        user_id=target_user.id,
        name=market.name,
        public=market.public,
        options=market
    ))

    if not success:
        return build_error_response(request, 409, _("Market name already in use"))

    market_managers = await get_market_managers(db, target_user)
    await market_managers[target_user.username + '/' + market.name].create(db, request, target_user)

    return Response(status_code=201)

@router.delete(
    "/{user}/{market}",
    summary=docs.delete_market_entry_summary,
    description=docs.delete_market_entry_description,
    status_code=204,
    response_class=Response,
    response_description=docs.delete_market_entry_response_description,
    responses={
        401: root_docs.generate_auth_required_response_openapi_description(
            docs.delete_market_entry_auth_required_response_description),
        403: root_docs.generate_permission_denied_response_openapi_description(
            docs.delete_market_entry_permission_denied_response_description,
            "You don't have permissions for deleting marketplaces in name of other user"),
        404: root_docs.generate_error_response_openapi_description(
            docs.delete_market_entry_not_found_response_description,
            "Resource not found"),
        422: root_docs.generate_validation_error_response_openapi_description(
            docs.delete_market_entry_validation_error_response_description)
    }
)
@authentication_required()
async def delete_market_entry(db: DBDep, user: UserDep, request: Request,
                              username: str = Path(alias="user", description=docs.delete_market_entry_user_description),
                              market: str = Path(description=docs.delete_market_entry_market_description)):

    if username != user.username and (not user.is_superuser and not user.has_perm("MARKETPLACE.DELETE")):
        return build_error_response(request, 403, _("You are not allowed to delete this market"))

    if username == user.username:
        target_user = user
    else:
        target_user = await get_user_by_username(db, username)
        if target_user is None:
            return build_error_response(request, 404, _("User not found"))

    market_managers = await get_market_managers(db, target_user)

    if not await delete_market_by_name(db, target_user, market):
        return build_error_response(request, 404, _("Market not found"))

    await market_managers[target_user.username + '/' + market].delete(db, request)

    return Response(status_code=204)

@markets_router.post(
    "/publish",
    summary=docs.publish_service_process_summary,
    description=docs.publish_service_process_description,
    status_code=204,
    response_class=Response,
    response_description=docs.publish_service_process_response_description,
    responses={
        401: root_docs.generate_auth_required_response_openapi_description(
            docs.publish_service_process_auth_required_response_description),
        403: root_docs.generate_permission_denied_response_openapi_description(
            docs.publish_service_process_permission_denied_response_description,
            "Resource not available for user"),
        404: root_docs.generate_not_found_response_openapi_description(
            docs.publish_service_process_not_found_response_description),
        406: root_docs.generate_not_acceptable_response_openapi_description(
            docs.publish_service_process_not_acceptable_response_description, ["application/json"]),
        422: root_docs.generate_validation_error_response_openapi_description(
            docs.publish_service_process_validation_error_response_description),
        502: root_docs.generate_error_response_openapi_description(
            docs.publish_service_process_error_response_description,
            "Something went wrong (see details for more info)",
            {"market1": "Error message 1", "market2": "Error message 2"})
    }
)
@authentication_required()
@consumes(["application/json"])
async def publish_service_process(db: DBDep, user: UserDep, request: Request,
                                  data: PublishData = Body(description=docs.publish_service_process_data_description,
                                                           examples=[docs.publish_service_process_data_example])):
    (resource_vendor, resource_name, resource_version) = data.resource.split('/')
    resource = await get_catalogue_resource(db, resource_vendor, resource_name, resource_version)
    if resource is None:
        return build_error_response(request, 404, "Resource not found")

    can_publish = resource.is_available_for(user) and (user.is_superuser or user.has_perm("MARKETPLACE.PUBLISH"))
    if not can_publish:
        return build_error_response(request, 403, "Resource not available for user")

    base_dir = catalogue.wgt_deployer.get_base_dir(resource_vendor, resource_name, resource_version)
    wgt_file = WgtFile(os.path.join(base_dir, resource.template_uri))

    market_managers = await get_market_managers(db, user)
    errors = {}
    for market_endpoint in data.marketplaces:
        try:
            await market_managers[market_endpoint.market].publish(db, market_endpoint, wgt_file, user, request=request)
        except Exception as e:
            errors[market_endpoint.market] = str(e)

    if len(errors) == len(data.marketplaces) and len(errors) != 0:
        return build_error_response(request, 502, _('Something went wrong (see details for more info)'),
                                    details=errors)
    elif len(errors) != 0:
        return build_error_response(request, 200, _('Something went wrong (see details for more info)'),
                                    details=errors)