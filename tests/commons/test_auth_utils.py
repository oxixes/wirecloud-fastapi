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

from datetime import datetime, timedelta, timezone

import jwt
from bson import ObjectId

from wirecloud import settings
from wirecloud.commons.auth import utils
from wirecloud.commons.auth.schemas import UserAll
from wirecloud.database import Id


def _request_with_token(token: str = None, csrf_token: str = None, header_csrf: str = None):
    from starlette.requests import Request

    query_parts = []
    if token is not None:
        query_parts.append(f"token={token}")
    if csrf_token is not None:
        query_parts.append(f"csrf_token={csrf_token}")
    query = "&".join(query_parts)

    headers = []
    if header_csrf is not None:
        headers.append((b"x-csrf-token", header_csrf.encode("latin-1")))

    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "GET",
        "path": "/",
        "query_string": query.encode("latin-1"),
        "headers": headers,
    }
    req = Request(scope)
    if token is not None:
        req._cookies = {"token": token}
    return req


def _make_access_token(token_id: ObjectId, csrf_required=True):
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "sub": str(ObjectId()),
            "iss": "Wirecloud",
            "jti": str(token_id),
            "exp": int((now + timedelta(minutes=10)).timestamp()),
            "iat": int(now.timestamp()),
            "csrf_required": csrf_required,
        },
        settings.JWT_KEY,
        algorithm="HS256",
    )


def _make_csrf_token(token_id: ObjectId, sub="csrf"):
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "sub": sub,
            "iss": "Wirecloud",
            "jti": str(token_id),
            "exp": int((now + timedelta(minutes=10)).timestamp()),
            "iat": int(now.timestamp()),
        },
        settings.JWT_KEY,
        algorithm="HS256",
    )


async def test_get_token_contents_handles_invalid_token_and_invalid_csrf(db_session, monkeypatch):
    async def _valid(_db, _token):
        return True

    monkeypatch.setattr(utils, "is_token_valid", _valid)

    invalid_req = _request_with_token("not-a-jwt")
    assert await utils.get_token_contents(None, invalid_req, db_session, csrf=False) is None

    token_id = ObjectId()
    access = _make_access_token(token_id, csrf_required=True)
    wrong_sub_csrf = _make_csrf_token(token_id, sub="not-csrf")
    req_wrong_sub = _request_with_token(access, wrong_sub_csrf)
    assert await utils.get_token_contents(None, req_wrong_sub, db_session, csrf=True) is None

    other_csrf = _make_csrf_token(ObjectId())
    req_wrong_jti = _request_with_token(access, other_csrf)
    assert await utils.get_token_contents(None, req_wrong_jti, db_session, csrf=True) is None


async def test_get_token_contents_returns_none_without_any_token(db_session):
    req = _request_with_token(token=None)
    req._cookies = {}
    assert await utils.get_token_contents(None, req, db_session, csrf=False) is None


async def test_get_token_contents_csrf_missing_or_invalid_csrf_token(db_session, monkeypatch):
    token_id = ObjectId()
    access = _make_access_token(token_id, csrf_required=True)

    async def _valid(_db, _token):
        return True

    monkeypatch.setattr(utils, "is_token_valid", _valid)

    req_missing_csrf = _request_with_token(access)
    assert await utils.get_token_contents(None, req_missing_csrf, db_session, csrf=True) is None

    req_bad_csrf = _request_with_token(access, "not-a-jwt")
    assert await utils.get_token_contents(None, req_bad_csrf, db_session, csrf=True) is None


async def test_get_token_contents_with_direct_token_and_header_csrf(db_session, monkeypatch):
    token_id = ObjectId()
    access = _make_access_token(token_id, csrf_required=True)
    csrf = _make_csrf_token(token_id)

    async def _valid(_db, _token):
        return True

    monkeypatch.setattr(utils, "is_token_valid", _valid)

    req = _request_with_token(token=None, header_csrf=csrf)
    token_contents = await utils.get_token_contents(access, req, db_session, csrf=True)
    assert token_contents is not None

    token_no_csrf = _make_access_token(ObjectId(), csrf_required=False)
    req2 = _request_with_token(token=None)
    assert await utils.get_token_contents(token_no_csrf, req2, db_session, csrf=True) is not None


async def test_get_token_contents_uses_cookie_and_rejects_invalid_db_token(db_session, monkeypatch):
    token_id = ObjectId()
    access = _make_access_token(token_id, csrf_required=False)

    async def _invalid(_db, _token):
        return False

    monkeypatch.setattr(utils, "is_token_valid", _invalid)
    req = _request_with_token(token=None)
    req._cookies = {"token": access}

    assert await utils.get_token_contents(None, req, db_session, csrf=False) is None


async def test_get_token_contents_wrappers_and_user_wrappers(db_session, monkeypatch):
    async def _token_contents(_token, _request, _db, csrf):
        return {"sub": str(ObjectId()), "csrf_required": csrf}

    async def _user(_db, token, real_user):
        return {"token": token, "real_user": real_user}

    monkeypatch.setattr(utils, "get_token_contents", _token_contents)
    monkeypatch.setattr(utils, "get_user", _user)

    req = _request_with_token()
    assert (await utils.get_token_contents_csrf(None, req, db_session))["csrf_required"] is True
    assert (await utils.get_token_contents_no_csrf(None, req, db_session))["csrf_required"] is False

    token = {"sub": str(ObjectId())}
    assert (await utils.get_user_csrf(db_session, token))["real_user"] is False
    assert (await utils.get_user_no_csrf(db_session, token))["real_user"] is False
    assert (await utils.get_real_user_csrf(db_session, token))["real_user"] is True
    assert (await utils.get_real_user_no_csrf(db_session, token))["real_user"] is True


async def test_get_user_and_session_wrappers(db_session, monkeypatch):
    user_id = ObjectId()

    async def _all_info(_db, _uid):
        return UserAll(
            id=Id(str(user_id)),
            username="u",
            email="u@example.com",
            first_name="U",
            last_name="Ser",
            is_superuser=False,
            is_staff=False,
            is_active=False,
            date_joined=datetime.now(timezone.utc),
            last_login=None,
            idm_data={},
            groups=[],
            permissions=[],
        )

    monkeypatch.setattr(utils, "get_user_with_all_info", _all_info)

    assert await utils.get_user(db_session, None, real_user=False) is None
    assert await utils.get_user(db_session, {"sub": str(user_id)}, real_user=False) is None

    req = _request_with_token()
    assert await utils.get_session(db_session, req, None) is None
    token_without_real = {"jti": str(ObjectId()), "csrf_required": True}
    session_plain = await utils.get_session(db_session, req, token_without_real)
    assert session_plain.real_user is None

    async def _session(_db, _request, token):
        return {"token": token}

    monkeypatch.setattr(utils, "get_session", _session)
    token = {"jti": str(ObjectId())}
    assert (await utils.get_session_csrf(db_session, req, token))["token"] == token
    assert (await utils.get_session_no_csrf(db_session, req, token))["token"] == token


async def test_check_password_fallback_branch(monkeypatch):
    monkeypatch.setattr(utils, "SUPPORTED_HASHES", ["unsupported_hash"])
    assert utils.check_password("x", "unsupported_hash$1$salt$abcd") is False


async def test_hash_password_generates_checkable_pbkdf2_hash():
    raw = "my-secret-password"
    hashed = utils.hash_password(raw)

    assert hashed.startswith("pbkdf2_sha256$")
    parts = hashed.split("$")
    assert len(parts) == 4
    assert utils.check_password(raw, hashed) is True
    assert utils.check_password("wrong-password", hashed) is False


class _FakeAiohttpResponse:
    def __init__(self, status, payload=None, json_error=False):
        self.status = status
        self._payload = payload
        self._json_error = json_error

    async def json(self):
        if self._json_error:
            raise ValueError("invalid json")
        return self._payload


class _FakeAiohttpSession:
    def __init__(self, response=None, request_error=False, capture=None):
        self.response = response
        self.request_error = request_error
        self.capture = capture if capture is not None else {}
        self.closed = False

    async def request(self, **kwargs):
        self.capture.update(kwargs)
        if self.request_error:
            raise RuntimeError("boom")
        return self.response

    async def close(self):
        self.closed = True


async def test_make_oidc_provider_request_success_and_no_content(monkeypatch):
    capture = {}
    fake_session = _FakeAiohttpSession(response=_FakeAiohttpResponse(200, {"ok": True}), capture=capture)
    monkeypatch.setattr(utils.aiohttp, "ClientSession", lambda: fake_session)

    payload = await utils.make_oidc_provider_request(
        "https://idp.example/token",
        data={"a": "b"},
        auth="secret",
        auth_type="Basic",
        query={"x": "1"},
    )

    assert payload == {"ok": True}
    assert capture["method"] == "POST"
    assert capture["headers"]["Authorization"] == "Basic secret"
    assert capture["data"] == "a=b"
    assert fake_session.closed is True

    fake_204 = _FakeAiohttpSession(response=_FakeAiohttpResponse(204), capture={})
    monkeypatch.setattr(utils.aiohttp, "ClientSession", lambda: fake_204)
    assert await utils.make_oidc_provider_request("https://idp.example/userinfo") is None


async def test_make_oidc_provider_request_error_paths(monkeypatch):
    monkeypatch.setattr(utils, "_", lambda text: text)
    unreachable = _FakeAiohttpSession(request_error=True)
    monkeypatch.setattr(utils.aiohttp, "ClientSession", lambda: unreachable)
    try:
        await utils.make_oidc_provider_request("https://idp.example/token")
        assert False, "Expected exception"
    except Exception as exc:
        assert "not reachable" in str(exc)

    bad_status = _FakeAiohttpSession(response=_FakeAiohttpResponse(500))
    monkeypatch.setattr(utils.aiohttp, "ClientSession", lambda: bad_status)
    try:
        await utils.make_oidc_provider_request("https://idp.example/token")
        assert False, "Expected exception"
    except Exception as exc:
        assert "valid response" in str(exc)

    bad_json = _FakeAiohttpSession(response=_FakeAiohttpResponse(200, json_error=True))
    monkeypatch.setattr(utils.aiohttp, "ClientSession", lambda: bad_json)
    try:
        await utils.make_oidc_provider_request("https://idp.example/token")
        assert False, "Expected exception"
    except Exception as exc:
        assert "valid response" in str(exc)
