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

from base64 import b64encode
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from bson import ObjectId
from starlette.requests import Request

from wirecloud import settings
from wirecloud.commons.auth import crud, utils
from wirecloud.commons.auth.schemas import UserAll, UserCreate
from wirecloud.database import Id


def _make_request(*, query: str = "", headers: Optional[dict[str, str]] = None) -> Request:
    scope_headers = []
    for key, value in (headers or {}).items():
        scope_headers.append((key.lower().encode("latin-1"), value.encode("latin-1")))

    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "GET",
        "path": "/",
        "query_string": query.encode("latin-1"),
        "headers": scope_headers,
    }
    return Request(scope)


def _build_token(payload: dict) -> str:
    return jwt.encode(payload, settings.JWT_KEY, algorithm="HS256")


async def test_check_password_pbkdf2_sha256_valid_and_invalid():
    password = "correct-horse-battery-staple"
    salt = "testsalt"
    iterations = 120000

    derived = utils.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("ascii"), iterations)
    password_hash = f"pbkdf2_sha256${iterations}${salt}${b64encode(derived).decode('ascii')}"

    assert utils.check_password(password, password_hash) is True
    assert utils.check_password("wrong-password", password_hash) is False
    assert utils.check_password(password, "md5$123$salt$hash") is False


async def test_get_token_contents_reads_query_token_and_validates_csrf(db_session, monkeypatch):
    token_id = ObjectId()
    now = datetime.now(timezone.utc)

    access_token = _build_token({
        "sub": str(ObjectId()),
        "iss": "Wirecloud",
        "jti": str(token_id),
        "exp": int((now + timedelta(minutes=10)).timestamp()),
        "iat": int(now.timestamp()),
        "csrf_required": True,
    })
    csrf_token = _build_token({
        "sub": "csrf",
        "iss": "Wirecloud",
        "jti": str(token_id),
        "exp": int((now + timedelta(minutes=10)).timestamp()),
        "iat": int(now.timestamp()),
    })

    async def _valid_token(_db, _token_id):
        return True

    monkeypatch.setattr(utils, "is_token_valid", _valid_token)

    request = _make_request(query=f"token={access_token}&csrf_token={csrf_token}")
    token_contents = await utils.get_token_contents(None, request, db_session, csrf=True)

    assert token_contents is not None
    assert token_contents["jti"] == str(token_id)
    assert token_contents["csrf_required"] is True


async def test_get_token_contents_rejects_missing_jti(db_session, monkeypatch):
    now = datetime.now(timezone.utc)
    access_token = _build_token({
        "sub": str(ObjectId()),
        "iss": "Wirecloud",
        "exp": int((now + timedelta(minutes=10)).timestamp()),
        "iat": int(now.timestamp()),
        "csrf_required": False,
    })

    async def _valid_token(_db, _token_id):
        return True

    monkeypatch.setattr(utils, "is_token_valid", _valid_token)

    request = _make_request(query=f"token={access_token}")
    token_contents = await utils.get_token_contents(None, request, db_session, csrf=False)

    assert token_contents is None


async def test_get_user_uses_real_user_and_requires_active(db_session, monkeypatch):
    real_user_id = ObjectId()

    async def _fake_get_user_with_all_info(_db, user_id):
        return UserAll(
            id=Id(str(user_id)),
            username="real-user",
            email="real@example.com",
            first_name="Real",
            last_name="User",
            is_superuser=False,
            is_staff=False,
            is_active=True,
            date_joined=datetime.now(timezone.utc),
            last_login=None,
            idm_data={},
            groups=[],
            permissions=[],
        )

    monkeypatch.setattr(utils, "get_user_with_all_info", _fake_get_user_with_all_info)

    token = {
        "sub": str(ObjectId()),
        "real_user": {"id": str(real_user_id)},
    }

    user = await utils.get_user(db_session, token, real_user=True)

    assert user is not None
    assert str(user.id) == str(real_user_id)


async def test_get_session_builds_session_from_token(db_session):
    session_id = ObjectId()
    token = {
        "jti": str(session_id),
        "csrf_required": False,
        "real_user": {
            "username": "admin",
            "fullname": "Admin User",
        },
    }

    session = await utils.get_session(db_session, _make_request(), token)

    assert session is not None
    assert str(session.id) == str(session_id)
    assert session.real_user == "admin"
    assert session.real_fullname == "Admin User"
    assert session.requires_csrf is False


async def test_token_crud_lifecycle(db_session):
    user_id = Id(str(ObjectId()))
    expiration = datetime.now(timezone.utc) + timedelta(minutes=15)

    token_id = await crud.create_token(db_session, expiration, user_id)
    assert await crud.is_token_valid(db_session, token_id) is True

    await crud.invalidate_token(db_session, token_id)
    assert await crud.is_token_valid(db_session, token_id) is False


async def test_invalidate_tokens_by_idm_session_and_get_idm_session(db_session):
    user_id = Id(str(ObjectId()))
    expiration = datetime.now(timezone.utc) + timedelta(minutes=15)

    token1 = await crud.create_token(db_session, expiration, user_id, idm_session="session-a")
    token2 = await crud.create_token(db_session, expiration, user_id, idm_session="session-a")
    token3 = await crud.create_token(db_session, expiration, user_id, idm_session="session-b")

    assert await crud.get_token_idm_session(db_session, token1) == "session-a"

    await crud.invalidate_tokens_by_idm_session(db_session, "session-a")

    token1_doc = await db_session.client.tokens.find_one({"_id": token1})
    token2_doc = await db_session.client.tokens.find_one({"_id": token2})
    token3_doc = await db_session.client.tokens.find_one({"_id": token3})

    assert token1_doc["valid"] is False
    assert token2_doc["valid"] is False
    assert token3_doc["valid"] is True


async def test_create_user_and_lookup_functions(db_session):
    user_info = UserCreate(
        username="alice",
        password="hashed-password",
        first_name="Alice",
        last_name="Example",
        email="alice@example.com",
        is_superuser=False,
        is_staff=False,
        is_active=True,
        idm_data={},
    )

    await crud.create_user(db_session, user_info)

    user = await crud.get_user_by_username(db_session, "alice")
    assert user is not None
    assert user.username == "alice"
    assert user.email == "alice@example.com"

    user_by_id = await crud.get_user_by_id(db_session, user.id)
    assert user_by_id is not None
    assert user_by_id.username == "alice"

    user_with_password = await crud.get_user_with_password(db_session, "alice")
    assert user_with_password is not None
    assert user_with_password.password == "hashed-password"


async def test_get_all_user_permissions_merges_user_and_group_permissions(db_session):
    user_id = ObjectId()
    group_id = ObjectId()

    await db_session.client.groups.insert_one({
        "_id": group_id,
        "name": "Editors",
        "codename": "editors",
        "group_permissions": [
            {"codename": "widgets.view"},
            {"codename": "widgets.edit"},
        ],
    })

    await db_session.client.users.insert_one({
        "_id": user_id,
        "groups": [group_id],
        "user_permissions": [
            {"codename": "widgets.view"},
            {"codename": "workspace.manage"},
        ],
    })

    permissions = await crud.get_all_user_permissions(db_session, Id(str(user_id)))
    codenames = {permission.codename for permission in permissions}

    assert codenames == {"widgets.view", "widgets.edit", "workspace.manage"}
