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

# TODO Add translations

from fastapi import APIRouter, Request
import jwt
from datetime import datetime
from pydantic import ValidationError

from src.wirecloud.commons.auth.schemas import UserLogin, UserToken, UserWithPassword, UserTokenType
from src.wirecloud.commons.auth.crud import get_user_with_password, set_login_date_for_user
from src.wirecloud.commons.auth.utils import check_password
from src.wirecloud.database import DBDep, commit
from src.wirecloud.commons.utils.http import build_error_response, build_validation_error_response, produces, consumes
from src import settings
from src.wirecloud import docs

router = APIRouter()

# TODO Move docs, follow naming convention, add summary and description
@router.post(
    "/login",
    response_model=UserToken,
    response_description=docs.login_response_model_description,
    responses={
        200: {"content": {"application/json": {"example": docs.login_response_model_example}}},
        401: docs.generate_error_response_openapi_description(docs.login_error_invalid_user_pass_response_model_description,
                                                              "Invalid username or password"),
        406: docs.generate_not_acceptable_response_openapi_description("Invalid request content type",
                                                                       ["application/json"]),
        415: docs.generate_unsupported_media_type_response_openapi_description("Unsupported request content type"),
        422: docs.generate_validation_error_response_openapi_description(docs.login_error_invalid_payload_response_model_descrition)
    },
    openapi_extra={
        "requestBody": {
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/UserLogin"}
                },
                "application/x-www-form-urlencoded": {
                    "schema": {"$ref": "#/components/schemas/UserLogin"}
                }
            }
        }
    }
)
@produces(["application/json"])
@consumes(["application/json", "application/x-www-form-urlencoded", "multipart/form-data"])
async def login(request: Request, db: DBDep):
    try:
        if request.mimetype == "application/x-www-form-urlencoded" or request.mimetype == "multipart/form-data":
            login_data = UserLogin.model_validate(await request.form(max_files=0, max_fields=50))
        else:
            login_data = UserLogin.model_validate_json(await request.body())
    except (ValueError, ValidationError):
        return build_validation_error_response(request)

    user: UserWithPassword = await get_user_with_password(db, login_data.username)
    if user is None or not user.is_active or not check_password(login_data.password, user.password):
        return build_error_response(request, 401, "Invalid username or password")

    await set_login_date_for_user(db, user.id)
    await commit(db)

    duration = (hasattr(settings, 'SESSION_AGE') and settings.SESSION_AGE) or 14 * 24 * 60 * 60  # 2 weeks
    token_contents = {
        "sub": str(user.id),
        "iss": "Wirecloud",
        "exp": int(datetime.utcnow().timestamp() + duration),
        "iat": int(datetime.utcnow().timestamp())
    }
    token = jwt.encode(token_contents, settings.JWT_KEY, algorithm="HS256")
    return UserToken(access_token=token, token_type=UserTokenType.bearer)
