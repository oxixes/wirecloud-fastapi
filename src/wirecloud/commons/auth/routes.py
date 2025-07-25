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
from fastapi.responses import HTMLResponse, Response
from datetime import datetime, timezone
from pydantic import ValidationError
import jwt
import asyncio

from src.wirecloud.commons.auth.models import Group
from src.wirecloud.database import Id
from src.wirecloud.commons.auth.schemas import UserLogin, UserToken, UserWithPassword, UserTokenType, User, UserCreate
from src.wirecloud.commons.auth.crud import get_user_with_password, set_login_date_for_user, get_user_by_username, \
    create_user, update_user, create_token, invalidate_token, add_user_to_groups_by_codename, \
    create_group_if_not_exists, remove_user_from_all_groups, set_token_expiration
from src.wirecloud.commons.auth.utils import check_password, SessionDepNoCSRF, SessionDep, \
    UserDep
from src.wirecloud.database import DBDep, commit
from src.wirecloud.commons.utils.http import build_error_response, build_validation_error_response, produces, consumes, \
    get_redirect_response
from src import settings
from src.wirecloud import docs as root_docs
from src.wirecloud.commons.auth import docs
from src.wirecloud.platform.plugins import get_idm_get_token_functions, get_idm_get_user_functions, \
    get_idm_backchannel_logout_functions
from src.wirecloud.platform.routes import render_wirecloud
from src.wirecloud.translation import gettext as _

router = APIRouter()
base_router = APIRouter()


@base_router.get(
    "/oidc/callback",
    summary=docs.oidc_login_summary,
    description=docs.oidc_login_description,
    response_class=HTMLResponse,
    response_description=docs.oidc_login_response_description,
    responses={
        422: root_docs.generate_validation_error_response_openapi_description(
            docs.oidc_login_validation_error_response_description)
    }
)
async def oidc_login(request: Request, db: DBDep, code: str = Query(description=docs.oidc_login_code_description)):
    if not getattr(settings, "OID_CONNECT_ENABLED", False):
        return build_error_response(request, 400, _("OIDC provider is not enabled"))

    if not getattr(settings, "OID_CONNECT_PLUGIN", "") in get_idm_get_token_functions():
        return build_error_response(request, 500, _("OIDC provider is not configured correctly! Contact your administrator."))

    if not getattr(settings, "OID_CONNECT_PLUGIN", "") in get_idm_get_user_functions():
        return build_error_response(request, 500, _("OIDC provider is not configured correctly! Contact your administrator."))

    token_data_get_func = get_idm_get_token_functions()[getattr(settings, "OID_CONNECT_PLUGIN", "")]
    user_get_func = get_idm_get_user_functions()[getattr(settings, "OID_CONNECT_PLUGIN", "")]

    try:
        if asyncio.iscoroutinefunction(token_data_get_func):
            # If the function is a coroutine, we need to await it
            token_data = await token_data_get_func(code=code, refresh_token=None, request=request)
        else:
            # If the function is a regular function, we can call it directly
            token_data = token_data_get_func(code=code, refresh_token=None, request=request)

        if asyncio.iscoroutinefunction(user_get_func):
            # If the function is a coroutine, we need to await it
            user_data = await user_get_func(token_data=token_data)
        else:
            # If the function is a regular function, we can call it directly
            user_data = user_get_func(token_data=token_data)
    except Exception as e:
        return build_error_response(request, 502, str(e))

    username = user_data["preferred_username"]

    user: User = await get_user_by_username(db, username)
    if user is not None and not user.is_active:
        return build_error_response(request, 401, _("Invalid user"))

    if user is None:
        # Register user
        await create_user(db, UserCreate(
            username=username,
            password="x",
            first_name=user_data.get("given_name", ""),
            last_name=user_data.get("family_name", ""),
            email=user_data.get("email", ""),
            is_superuser=False,
            is_staff=False,
            is_active=True
        ))

        await commit(db)

        user = await get_user_by_username(db, username)
    else:
        user.email = user_data.get("email", user.email)
        user.first_name = user_data.get("given_name", user.first_name)
        user.last_name = user_data.get("family_name", user.last_name)

        await update_user(db, user)

    if getattr(settings, "OID_CONNECT_FULLY_SYNC_GROUPS", False):
        await remove_user_from_all_groups(db, user.id)

    if 'wirecloud' in user_data and isinstance(user_data['wirecloud'], dict) and 'groups' in user_data['wirecloud']:
        # Check that groups are a list of strings
        if isinstance(user_data['wirecloud']['groups'], list) and all(isinstance(group, str) for group in user_data['wirecloud']['groups']):
            for group in user_data['wirecloud']['groups']:
                await create_group_if_not_exists(db, Group(_id=Id(), name=group, codename=group))
            await add_user_to_groups_by_codename(db, user.id, user_data['wirecloud']['groups'])

    await set_login_date_for_user(db, user.id)

    expiration = datetime.fromtimestamp(datetime.now(timezone.utc).timestamp() + token_data["refresh_expires_in"], tz=timezone.utc)

    token_id = str(await create_token(db, expiration))
    await commit(db)

    token_contents = {
        "sub": str(user.id),
        "iss": "Wirecloud",
        "jti": token_id,
        "exp": int(expiration.timestamp()),
        "iat": int(datetime.now(timezone.utc).timestamp()),
        "oidc_token": {
            "refresh": token_data["refresh_token"],
            "refresh_expiration": int(datetime.now(timezone.utc).timestamp() + token_data["refresh_expires_in"]),
        },
        "csrf_required": True
    }
    token = jwt.encode(token_contents, settings.JWT_KEY, algorithm="HS256")

    csrf_token_contents = {
        "sub": str(user.id),
        "iss": "Wirecloud",
        "jti": token_id,
        "exp": int(expiration.timestamp()),
        "iat": int(datetime.now(timezone.utc).timestamp())
    }
    csrf_token = jwt.encode(csrf_token_contents, settings.JWT_KEY, algorithm="HS256")

    response = get_redirect_response(request)
    response.set_cookie(key="token", value=token, httponly=True, secure=getattr(settings, "WIRECLOUD_HTTPS", False), samesite="strict", expires=expiration)
    response.set_cookie(key="csrf_token", value=csrf_token, httponly=False, secure=getattr(settings, "WIRECLOUD_HTTPS", False), samesite="strict", expires=expiration)
    response.set_cookie(key="token_expiration", value=str(int(expiration.timestamp())), httponly=False,
                        secure=getattr(settings, "WIRECLOUD_HTTPS", False), samesite="lax", expires=expiration)

    return response


@router.post(
    "/login",
    summary=docs.api_login_summary,
    description=docs.api_login_description,
    response_model=UserToken,
    response_description=docs.api_login_response_model_description,
    responses={
        200: {"content": {"application/json": {"example": docs.api_login_response_model_example}}},
        401: root_docs.generate_error_response_openapi_description(
            docs.api_login_unauthorized_response_description,
            "Invalid username or password"),
        406: root_docs.generate_not_acceptable_response_openapi_description(
            docs.api_login_not_acceptable_response_description,
            ["application/json", "application/x-www-form-urlencoded", "multipart/form-data"]),
        415: root_docs.generate_unsupported_media_type_response_openapi_description(
            docs.api_login_unsupported_media_type_response_description),
        422: root_docs.generate_validation_error_response_openapi_description(
            docs.api_login_validation_error_response_descrition)
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
async def api_login(request: Request, db: DBDep):
    try:
        if request.state.mimetype == "application/x-www-form-urlencoded" or request.state.mimetype == "multipart/form-data":
            login_data = UserLogin.model_validate(await request.form(max_files=0, max_fields=50))
        else:
            login_data = UserLogin.model_validate_json(await request.body())
    except (ValueError, ValidationError):
        return build_validation_error_response(request)

    user: UserWithPassword = await get_user_with_password(db, login_data.username)
    if user is None or not user.is_active or not check_password(login_data.password, user.password):
        return build_error_response(request, 401, _("Invalid username or password"))

    await set_login_date_for_user(db, user.id)

    duration = (hasattr(settings, 'SESSION_AGE') and settings.SESSION_AGE) or 14 * 24 * 60 * 60  # 2 weeks
    expiration = datetime.fromtimestamp(int(datetime.now(timezone.utc).timestamp() + duration), tz=timezone.utc)

    token_id = str(await create_token(db, expiration))
    await commit(db)

    token_contents = {
        "sub": str(user.id),
        "iss": "Wirecloud",
        "jti": token_id,
        "exp": int(expiration.timestamp()),
        "iat": int(datetime.now(timezone.utc).timestamp()),
        "csrf_required": False
    }
    token = jwt.encode(token_contents, settings.JWT_KEY, algorithm="HS256")
    return UserToken(access_token=token, token_type=UserTokenType.bearer)


@base_router.get(
    "/login",
    summary=docs.login_page_summary,
    description=docs.login_page_description,
    response_class=HTMLResponse,
    response_description=docs.login_page_response_description
)
async def login_page(request: Request):
    return render_wirecloud(request, page="registration/login", title="Login", extra_context={"form": {"errors": False}})


@base_router.post(
    "/login",
    summary=docs.login_summary,
    description=docs.login_description,
    response_class=HTMLResponse,
    response_description=docs.login_response_description,
    responses={
        401: root_docs.generate_error_response_openapi_description(
            docs.login_unauthorized_response_description,
            "Invalid username or password"),
        406: root_docs.generate_not_acceptable_response_openapi_description(
            docs.login_not_acceptable_response_description,
            ["application/json", "application/x-www-form-urlencoded", "multipart/form-data"]),
        415: root_docs.generate_unsupported_media_type_response_openapi_description(
            docs.login_unsupported_media_type_response_description),
        422: root_docs.generate_validation_error_response_openapi_description(
            docs.login_validation_error_response_description)
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
@consumes(["application/json", "application/x-www-form-urlencoded", "multipart/form-data"])
async def login(request: Request, db: DBDep):
    try:
        if request.state.mimetype == "application/x-www-form-urlencoded" or request.state.mimetype == "multipart/form-data":
            login_data = UserLogin.model_validate(await request.form(max_files=0, max_fields=50))
        else:
            login_data = UserLogin.model_validate_json(await request.body())
    except (ValueError, ValidationError):
        return build_validation_error_response(request)

    user: UserWithPassword = await get_user_with_password(db, login_data.username)
    if user is None or not user.is_active or not check_password(login_data.password, user.password):
        return render_wirecloud(request, page="registration/login", title="Login", extra_context={"form": {"errors": True}})

    await set_login_date_for_user(db, user.id)

    duration = (hasattr(settings, 'SESSION_AGE') and settings.SESSION_AGE) or 14 * 24 * 60 * 60  # 2 weeks
    expiration = datetime.fromtimestamp(int(datetime.now(timezone.utc).timestamp() + duration), tz=timezone.utc)

    token_id = str(await create_token(db, expiration))
    await commit(db)

    token_contents = {
        "sub": str(user.id),
        "iss": "Wirecloud",
        "jti": token_id,
        "exp": int(expiration.timestamp()),
        "iat": int(datetime.now(timezone.utc).timestamp()),
        "csrf_required": True
    }

    token = jwt.encode(token_contents, settings.JWT_KEY, algorithm="HS256")

    csrf_token_contents = {
        "sub": str(user.id),
        "iss": "Wirecloud",
        "jti": token_id,
        "exp": int(expiration.timestamp()),
        "iat": int(datetime.now(timezone.utc).timestamp())
    }

    csrf_token = jwt.encode(csrf_token_contents, settings.JWT_KEY, algorithm="HS256")

    response = get_redirect_response(request)
    response.set_cookie(key="token", value=token, httponly=True, secure=getattr(settings, "WIRECLOUD_HTTPS", False), samesite="strict", expires=expiration)
    response.set_cookie(key="csrf_token", value=csrf_token, httponly=False, secure=getattr(settings, "WIRECLOUD_HTTPS", False), samesite="strict", expires=expiration)
    response.set_cookie(key="token_expiration", value=str(int(expiration.timestamp())), httponly=False,
                        secure=getattr(settings, "WIRECLOUD_HTTPS", False), samesite="lax", expires=expiration)

    return response


@base_router.get(
    "/logout",
    summary=docs.logout_summary,
    description=docs.logout_description,
    response_class=HTMLResponse,
    response_description=docs.logout_response_description
)
async def logout(request: Request, db: DBDep, session: SessionDepNoCSRF):
    if not session:
        return build_error_response(request, 401, _("You are not logged in"))

    await invalidate_token(db, session.id)
    await commit(db)

    if session.oidc_token and getattr(settings, "OID_CONNECT_ENABLED", False) and getattr(settings, "OID_CONNECT_PLUGIN", "") in get_idm_backchannel_logout_functions():
        backchannel_logout_func = get_idm_backchannel_logout_functions()[getattr(settings, "OID_CONNECT_PLUGIN", "")]
        try:
            if asyncio.iscoroutinefunction(backchannel_logout_func):
                # If the function is a coroutine, we need to await it
                await backchannel_logout_func(refresh_token=session.oidc_token.refresh)
            else:
                # If the function is a regular function, we can call it directly
                backchannel_logout_func(refresh_token=session.oidc_token.refresh)
        except Exception as e:
            pass

    response = get_redirect_response(request)

    # Remove cookies
    response.set_cookie(key="token", value="", httponly=True, secure=getattr(settings, "WIRECLOUD_HTTPS", False), samesite="strict", expires=0)
    response.set_cookie(key="csrf_token", value="", httponly=False, secure=getattr(settings, "WIRECLOUD_HTTPS", False), samesite="strict", expires=0)
    response.set_cookie(key="token_expiration", value="", httponly=False, secure=getattr(settings, "WIRECLOUD_HTTPS", False), samesite="lax", expires=0)

    return response


@router.get(
    "/refresh",
    summary=docs.token_refresh_summary,
    description=docs.token_refresh_description,
    response_model=UserToken,
    response_description=docs.token_refresh_response_model_description,
    responses={
        200: {"content": {"application/json": {"example": docs.token_refresh_response_model_example}}},
        401: root_docs.generate_error_response_openapi_description(
            docs.token_refresh_unauthorized_response_description,
            "You are not logged in")
    }
)
async def token_refresh(request: Request, db: DBDep, session: SessionDep, user: UserDep):
    if not session or not session.oidc_token:
        return build_error_response(request, 401, _("You are not logged in"))

    token_data = None
    if getattr(settings, "OID_CONNECT_ENABLED", False):
        if not getattr(settings, "OID_CONNECT_PLUGIN", "") in get_idm_get_token_functions():
            return build_error_response(request, 500, _("OIDC provider is not configured correctly! Contact your administrator."))

        try:
            token_data_get_func = get_idm_get_token_functions()[getattr(settings, "OID_CONNECT_PLUGIN", "")]
            if asyncio.iscoroutinefunction(token_data_get_func):
                # If the function is a coroutine, we need to await it
                token_data = await token_data_get_func(code=None, refresh_token=session.oidc_token.refresh, request=request)
            else:
                # If the function is a regular function, we can call it directly
                token_data = token_data_get_func(code=None, refresh_token=session.oidc_token.refresh, request=request)
        except Exception as e:
            return build_error_response(request, 502, str(e))

    duration = (hasattr(settings, 'SESSION_AGE') and settings.SESSION_AGE) or 14 * 24 * 60 * 60  # 2 weeks
    expiration = (datetime.fromtimestamp(datetime.now(timezone.utc).timestamp() + token_data["refresh_expires_in"], tz=timezone.utc)
                  if "refresh_expires_in" in token_data else datetime.fromtimestamp(session.oidc_token.refresh_expiration, tz=timezone.utc)) \
        if getattr(settings, "OID_CONNECT_ENABLED", False) else datetime.fromtimestamp(int(datetime.now(timezone.utc).timestamp() + duration), tz=timezone.utc)

    await set_token_expiration(db, session.id, expiration)
    await commit(db)

    token_contents = {
        "sub": str(user.id),
        "iss": "Wirecloud",
        "jti": str(session.id),
        "exp": int(expiration.timestamp()),
        "iat": int(datetime.now(timezone.utc).timestamp()),
        "csrf_required": session.requires_csrf
    }

    if getattr(settings, "OID_CONNECT_ENABLED", False):
        # If OIDC is enabled, we need to include the OIDC token in the response
        token_contents["oidc_token"] = {
            "refresh": token_data["refresh_token"] if "refresh_token" in token_data else session.oidc_token.refresh,
            "refresh_expiration": int(datetime.now(timezone.utc).timestamp() + token_data["refresh_expires_in"]) \
                if "refresh_expires_in" in token_data else session.oidc_token.refresh_expiration,
        }

    token = jwt.encode(token_contents, settings.JWT_KEY, algorithm="HS256")

    response = Response(status_code=200, content=UserToken(access_token=token, token_type=UserTokenType.bearer).model_dump_json())
    response.set_cookie(key="token", value=token, httponly=True, secure=getattr(settings, "WIRECLOUD_HTTPS", False),
                        samesite="strict", expires=expiration)
    response.set_cookie(key="token_expiration", value=str(int(expiration.timestamp())), httponly=False,
                        secure=getattr(settings, "WIRECLOUD_HTTPS", False), samesite="lax", expires=expiration)

    if session.requires_csrf:
        # If CSRF is required, we need to create a CSRF token
        csrf_token_contents = {
            "sub": str(user.id),
            "iss": "Wirecloud",
            "jti": str(session.id),
            "exp": int(expiration.timestamp()),
            "iat": int(datetime.now(timezone.utc).timestamp())
        }
        csrf_token = jwt.encode(csrf_token_contents, settings.JWT_KEY, algorithm="HS256")

        response.set_cookie(key="csrf_token", value=csrf_token, httponly=False,
                            secure=getattr(settings, "WIRECLOUD_HTTPS", False), samesite="strict", expires=expiration)

    return response