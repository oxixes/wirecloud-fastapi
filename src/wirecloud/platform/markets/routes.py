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

from fastapi import APIRouter, Request, Body, Path, Response

from src.wirecloud.platform.markets.schemas import MarketData, MarketCreate, Market
from src.wirecloud.platform.markets import docs
from src.wirecloud.platform.markets.crud import (get_markets_for_user, get_market_user, create_market,
                                                 delete_market_by_name)
from src.wirecloud.platform.markets.utils import get_market_managers
from src.wirecloud.commons.auth.crud import get_user_by_username
from src.wirecloud.commons.utils.http import produces, consumes, authentication_required, build_error_response
from src.wirecloud.commons.auth.utils import UserDep
from src.wirecloud import docs as root_docs
from src.wirecloud.database import DBDep

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
@authentication_required
async def get_market_collection(db: DBDep, user: UserDep, _request: Request):
    result = []

    for market in await get_markets_for_user(db, user):
        market_data = MarketData(**market.options.model_dump(), permissions={
            'delete': user.is_superuser or market.user_id == user.id
        })
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
@authentication_required
@consumes(["application/json"])
@produces(["application/json"])
async def create_market_collection(db: DBDep, user: UserDep, request: Request,
                                   market: MarketCreate = Body(
                                       description=docs.create_market_collection_market_description,
                                       examples=[docs.create_market_collection_market_example])):
    # TODO Translate strings
    # TODO More complex user permissions

    if market.user is None or market.user == user.username:
        target_user = user
    else:
        target_user = await get_user_by_username(db, market.user)
        if target_user is None:
            return build_error_response(request, 422, "invalid user option")

    if target_user.id != user.id and not user.is_superuser:
        return build_error_response(request, 403, "You don't have permissions for adding marketplaces in name of other user")

    market.user = target_user.username

    success = await create_market(db, Market(
        id=-1,
        user_id=target_user.id,
        name=market.name,
        public=market.public,
        options=market
    ))

    if not success:
        return build_error_response(request, 409, "Market name already in use")

    market_managers = await get_market_managers(db, target_user)
    market_managers[target_user.username + '/' + market.name].create(target_user)

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
@authentication_required
async def delete_market_entry(db: DBDep, user: UserDep, request: Request,
                              username: str = Path(alias="user", description=docs.delete_market_entry_user_description),
                              market: str = Path(description=docs.delete_market_entry_market_description)):
    # TODO Translate strings
    # TODO More complex user permissions

    if username != user.username and not user.is_superuser:
        return build_error_response(request, 403, "You are not allowed to delete this market")

    if username == user.username:
        target_user = user
    else:
        target_user = await get_user_by_username(db, username)
        if target_user is None:
            return build_error_response(request, 404, "User not found")

    market_managers = await get_market_managers(db, target_user)

    if not await delete_market_by_name(db, target_user, market):
        return build_error_response(request, 404, "Market not found")

    market_managers[target_user.username + '/' + market].delete()

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
            "You are not allowed to publish in this market"),
        404: root_docs.generate_not_found_response_openapi_description(
            docs.publish_service_process_not_found_response_description),
        406: root_docs.generate_not_acceptable_response_openapi_description(
            docs.publish_service_process_not_acceptable_response_description, ["application/json"]),
        422: root_docs.generate_validation_error_response_openapi_description(
            docs.publish_service_process_validation_error_response_description)
    }
)
@authentication_required
@consumes(["application/json"])
def publish_service_process(db: DBDep, user: UserDep, request: Request):
    pass