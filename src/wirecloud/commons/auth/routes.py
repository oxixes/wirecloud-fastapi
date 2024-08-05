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
from json import JSONDecodeError
from pydantic import ValidationError

from src.wirecloud.commons.auth.schemas import UserLogin, UserToken, UserWithPassword, UserTokenType
from src.wirecloud.commons.auth.crud import get_user_with_password, set_login_date_for_user
from src.wirecloud.commons.auth.utils import check_password
from src.wirecloud.database import DBDep, commit
from src.wirecloud.commons.utils.http import build_error_response
from src import settings
from src import docs

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
        422: docs.generate_error_response_openapi_description(docs.login_error_invalid_payload_response_model_descrition,
                                                              "Invalid payload")
    },
    openapi_extra={
        "requestBody": {
            "content": {
                "application/json": {
                    "schema": UserLogin.model_json_schema()
                },
                "application/x-www-form-urlencoded": {
                    "schema": UserLogin.model_json_schema()
                }
            }
        }
    }
)
async def login(req: Request, db: DBDep):
    try:
        if req.headers.get("Content-Type") == "application/x-www-form-urlencoded" or \
                req.headers.get("Content-Type") == "multipart/form-data":
            login_data = UserLogin.model_validate(await req.form())
        else:
            login_data = UserLogin.model_validate(await req.json())
    except (JSONDecodeError, ValidationError):
        return build_error_response(req, 422, "Invalid payload")

    user: UserWithPassword = await get_user_with_password(db, login_data.username)
    if user is None or not user.is_active or not check_password(login_data.password, user.password):
        return build_error_response(req, 401, "Invalid username or password")

    await set_login_date_for_user(db, user.id)
    await commit(db)

    duration = (hasattr(settings, 'SESSION_AGE') and settings.SESSION_AGE) or 14 * 24 * 60 * 60  # 2 weeks
    token_contents = {
        "sub": user.id,
        "iss": "Wirecloud",
        "exp": int(datetime.utcnow().timestamp() + duration),
        "iat": int(datetime.utcnow().timestamp())
    }
    token = jwt.encode(token_contents, settings.JWT_KEY, algorithm="HS256")
    return UserToken(access_token=token, token_type=UserTokenType.bearer)
