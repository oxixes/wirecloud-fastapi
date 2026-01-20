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

import aiohttp
import jwt
from urllib.parse import urlencode
from bson import ObjectId
from typing import Union, Optional
from secrets import compare_digest
from hashlib import pbkdf2_hmac
from base64 import b64decode
from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer
from typing import Annotated
from src import settings
from wirecloud.database import DBDep, Id
from wirecloud.commons.auth.schemas import Session, UserAll
from wirecloud.commons.auth.crud import is_token_valid, get_user_with_all_info
from wirecloud.translation import gettext as _

SUPPORTED_HASHES = ['pbkdf2_sha256']


login_scheme = OAuth2PasswordBearer(scheme_name="User authentication", tokenUrl="api/auth/login/", auto_error=False)


async def get_token_contents(token: Annotated[str, Depends(login_scheme)], request: Request, db: DBDep, csrf: bool) -> Union[dict[str, Union[str, int, bool, None]], None]:
    if token is None:
        token = request.query_params.get('token')
    if token is None:
        token = request.cookies.get('token')
    if token is None:
        return None

    try:
        token_contents = jwt.decode(token, settings.JWT_KEY, algorithms=["HS256"],
                                    require=["exp", "sub", "iat", "iss"], issuer="Wirecloud",
                                    options={"verify_exp": True, "verify_iss": True})
    except Exception:
        return None

    if 'jti' not in token_contents:
        return None

    token_valid = await is_token_valid(db, ObjectId(token_contents['jti']))
    if not token_valid:
        return None

    if token_contents["csrf_required"] and csrf:
        csrf_token = request.headers["X-CSRF-Token"] if "X-CSRF-Token" in request.headers else None
        if csrf_token is None:
            csrf_token = request.query_params.get('csrf_token')
        if csrf_token is None:
            return None

        try:
            csrf_token_contents = jwt.decode(csrf_token, settings.JWT_KEY, algorithms=["HS256"],
                                             require=["exp", "sub", "iat", "iss"], issuer="Wirecloud",
                                             options={"verify_exp": True, "verify_iss": True})
            if csrf_token_contents.get("sub") != "csrf":
                return None

            if csrf_token_contents.get('jti') != token_contents.get('jti'):
                return None
        except Exception:
            return None

    return token_contents


async def get_token_contents_csrf(token: Annotated[str, Depends(login_scheme)], request: Request, db: DBDep) -> Union[dict[str, Union[str, int, bool, None]], None]:
    return await get_token_contents(token, request, db, csrf=True)


async def get_token_contents_no_csrf(token: Annotated[str, Depends(login_scheme)], request: Request, db: DBDep) -> Union[dict[str, Union[str, int, bool, None]], None]:
    return await get_token_contents(token, request, db, csrf=False)


async def get_user(db: DBDep, token: Union[dict[str, Union[str, int, bool, None]], None]) -> Union[UserAll, None]:
    if token is None:
        return None

    user = await get_user_with_all_info(db, Id(token['sub']))
    if user is None or not user.is_active:
        return None

    return user


async def get_user_csrf(db: DBDep, token: Annotated[Union[dict[str, Union[str, int, bool, None]], None], Depends(get_token_contents_csrf)]) -> Union[UserAll, None]:
    return await get_user(db, token)


async def get_user_no_csrf(db: DBDep, token: Annotated[Union[dict[str, Union[str, int, bool, None]], None], Depends(get_token_contents_no_csrf)]) -> Union[UserAll, None]:
    return await get_user(db, token)


UserDep = Annotated[UserAll, Depends(get_user_csrf)]
UserDepNoCSRF = Annotated[UserAll, Depends(get_user_no_csrf)]


async def get_session(db: DBDep, request: Request, token: Union[dict[str, Union[str, int, bool, None]], None]) -> Union[Session, None]:
    if token is None:
        return None

    return Session(
        id=Id(token.get("jti")),
        real_user=token.get('real_user', None),
        real_fullname=token.get('real_fullname', None),
        requires_csrf=token.get('csrf_required', True)
    )


async def get_session_csrf(db: DBDep, request: Request, token: Annotated[Union[dict[str, Union[str, int, bool, None]], None], Depends(get_token_contents_csrf)]) -> Union[Session, None]:
    return await get_session(db, request, token)


async def get_session_no_csrf(db: DBDep, request: Request, token: Annotated[Union[dict[str, Union[str, int, bool, None]], None], Depends(get_token_contents_no_csrf)]) -> Union[Session, None]:
    return await get_session(db, request, token)


SessionDep = Annotated[Session, Depends(get_session_csrf)]
SessionDepNoCSRF = Annotated[Session, Depends(get_session_no_csrf)]


def check_password(password: str, password_hash: str) -> bool:
    used_hash = None
    for hash_name in SUPPORTED_HASHES:
        if hash_name in password_hash:
            used_hash = hash_name
            break

    if used_hash is None:
        return False

    if used_hash == 'pbkdf2_sha256':
        _, iterations, salt, expected_password_hash = password_hash.split('$')
        hashed_password = pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('ascii'), int(iterations))
        return compare_digest(hashed_password, b64decode(expected_password_hash))

    return False


async def make_oidc_provider_request(endpoint: str, data: Optional[dict] = None, auth: Optional[str] = None,
                                     auth_type: str = "Bearer", query: Optional[dict] = None) -> dict:
    headers = {
        'Accept': 'application/json'
    }

    if data:
        headers['Content-Type'] = 'application/x-www-form-urlencoded'

    if auth:
        headers['Authorization'] = f'{auth_type} {auth}'

    encoded_data = urlencode(data) if data else None

    session = aiohttp.ClientSession()
    try:
        res = await session.request(
            method='POST' if data else 'GET',
            url=endpoint,
            timeout=5,
            headers=headers,
            allow_redirects=True,
            data=encoded_data,
            params=query,
            ssl=getattr(settings, "WIRECLOUD_HTTPS_VERIFY", True),
        )
    except:
        await session.close()
        raise Exception(_("OIDC provider is not reachable"))

    if res.status != 200 and res.status != 204:
        await session.close()
        raise Exception(_("OIDC provider has not returned a valid response"))

    response_data = None

    if res.status != 204:  # 204 No Content
        try:
            response_data = await res.json()
        except:
            await session.close()
            raise Exception(_("OIDC provider has not returned a valid response"))

    await session.close()
    return response_data