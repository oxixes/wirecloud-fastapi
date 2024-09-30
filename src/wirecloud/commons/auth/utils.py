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

import jwt
from typing import Union
from secrets import compare_digest
from hashlib import pbkdf2_hmac
from base64 import b64decode
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from typing import Annotated
from src import settings
from src.wirecloud.database import DBDep, Id
from src.wirecloud.commons.auth.schemas import Session, UserAll
from src.wirecloud.commons.auth.crud import get_user_by_id, get_user_groups, get_all_user_permissions

SUPPORTED_HASHES = ['pbkdf2_sha256']


login_scheme = OAuth2PasswordBearer(scheme_name="User authentication", tokenUrl="api/auth/login/", auto_error=False)


async def get_token_contents(token: Annotated[str, Depends(login_scheme)]) -> Union[dict[str, Union[str, int, None]], None]:
    if token is None:
        return None

    try:
        token_contents = jwt.decode(token, settings.JWT_KEY, algorithms=["HS256"],
                                    require=["exp", "sub", "iat", "iss"], issuer="Wirecloud")
    except Exception:
        return None

    return token_contents


async def get_user(db: DBDep, token: Annotated[Union[dict[str, Union[str, int, None]], None], Depends(get_token_contents)]) -> Union[UserAll, None]:
    if token is None:
        return None

    user = await get_user_by_id(db, Id(token['sub']))
    if user is None or not user.is_active:
        return None

    groups = await get_user_groups(db, user.id)
    permissions = await get_all_user_permissions(db, user.id)

    return UserAll(
        **user.model_dump(),
        groups=groups,
        permissions=permissions
    )

UserDep = Annotated[UserAll, Depends(get_user)]


async def get_session(token: Annotated[Union[dict[str, Union[str, int, None]], None], Depends(get_token_contents)]) -> Union[Session, None]:
    if token is None:
        return None

    return Session(
        real_user=token.get('real_user', None),
        real_fullname=token.get('real_fullname', None)
    )

SessionDep = Annotated[Session, Depends(get_session)]


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
