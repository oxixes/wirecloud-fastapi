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

from datetime import datetime, timezone

import pytest
from bson import ObjectId
from httpx import ASGITransport, AsyncClient

from src import settings
from wirecloud.commons.auth.schemas import User
from wirecloud.database import Id
from wirecloud.keycloak import routes
from wirecloud.main import app


def _user_with_keycloak_session(session_id: str) -> User:
    now = datetime.now(timezone.utc)
    return User(
        id=Id(str(ObjectId())),
        username="kc",
        email="kc@example.com",
        first_name="Key",
        last_name="Cloak",
        is_superuser=False,
        is_staff=False,
        is_active=True,
        date_joined=now,
        last_login=None,
        idm_data={"keycloak": {"idm_session": session_id}},
    )


@pytest.fixture()
async def app_http_client(db_session):
    from wirecloud.database import get_session

    async def _override_get_session():
        yield db_session

    app.dependency_overrides[get_session] = _override_get_session
    try:
        transport = ASGITransport(app=app, raise_app_exceptions=False)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            yield client
    finally:
        app.dependency_overrides.clear()


async def test_keycloak_backchannel_logout_error_paths(app_http_client, db_session, monkeypatch):
    monkeypatch.setattr(settings, "OID_CONNECT_CLIENT_ID", "wirecloud")
    monkeypatch.setattr(settings, "OID_CONNECT_DATA", {"issuer": "https://issuer", "keys": {"known": "pk"}}, raising=False)

    monkeypatch.setattr(routes.jwt, "get_unverified_header", lambda _t: {})
    res = await app_http_client.post("/oidc/k_logout", data={"logout_token": "token"})
    assert res.status_code == 400

    monkeypatch.setattr(routes.jwt, "get_unverified_header", lambda _t: {"kid": "unknown"})
    res = await app_http_client.post("/oidc/k_logout", data={"logout_token": "token"})
    assert res.status_code == 400

    monkeypatch.setattr(routes.jwt, "get_unverified_header", lambda _t: {"kid": "known", "alg": "RS256"})

    def _decode_raises(*_args, **_kwargs):
        raise RuntimeError("bad")

    monkeypatch.setattr(routes.jwt, "decode", _decode_raises)
    res = await app_http_client.post("/oidc/k_logout", data={"logout_token": "token"})
    assert res.status_code == 400

    monkeypatch.setattr(routes.jwt, "decode", lambda *_a, **_k: {"typ": "NotLogout", "sub": "u"})
    res = await app_http_client.post("/oidc/k_logout", data={"logout_token": "token"})
    assert res.status_code == 400

    monkeypatch.setattr(routes.jwt, "decode", lambda *_a, **_k: {"typ": "Logout", "sub": "u"})

    async def _no_user(*_args, **_kwargs):
        return None

    monkeypatch.setattr(routes, "get_user_by_idm_user_id", _no_user)
    res = await app_http_client.post("/oidc/k_logout", data={"logout_token": "token"})
    assert res.status_code == 400


async def test_keycloak_backchannel_logout_sid_paths(app_http_client, monkeypatch):
    monkeypatch.setattr(settings, "OID_CONNECT_CLIENT_ID", "wirecloud")
    monkeypatch.setattr(settings, "OID_CONNECT_DATA", {"issuer": "https://issuer", "keys": {"known": "pk"}}, raising=False)

    monkeypatch.setattr(routes.jwt, "get_unverified_header", lambda _t: {"kid": "known"})
    monkeypatch.setattr(routes.jwt, "decode", lambda *_a, **_k: {"typ": "Logout", "sub": "idm-u", "sid": "sid-1"})

    calls = {"invalidate_sid": 0, "update_user": 0}

    async def _invalidate(_db, sid):
        calls["invalidate_sid"] += 1
        calls["sid"] = sid

    async def _update(_db, user):
        calls["update_user"] += 1
        calls["user"] = user

    monkeypatch.setattr(routes, "invalidate_tokens_by_idm_session", _invalidate)
    monkeypatch.setattr(routes, "update_user", _update)

    async def _wrong_session(*_args, **_kwargs):
        return _user_with_keycloak_session("different")

    monkeypatch.setattr(routes, "get_user_by_idm_user_id", _wrong_session)
    res = await app_http_client.post("/oidc/k_logout", data={"logout_token": "token"})
    assert res.status_code == 204
    assert calls["invalidate_sid"] == 1
    assert calls["update_user"] == 0

    async def _matching_session(*_args, **_kwargs):
        return _user_with_keycloak_session("sid-1")

    monkeypatch.setattr(routes, "get_user_by_idm_user_id", _matching_session)
    res = await app_http_client.post("/oidc/k_logout", data={"logout_token": "token"})
    assert res.status_code == 204
    assert calls["invalidate_sid"] == 2
    assert calls["update_user"] == 1
    assert "keycloak" not in calls["user"].idm_data


async def test_keycloak_backchannel_logout_without_sid(app_http_client, monkeypatch):
    monkeypatch.setattr(settings, "OID_CONNECT_CLIENT_ID", "wirecloud")
    monkeypatch.setattr(settings, "OID_CONNECT_DATA", {"issuer": "https://issuer", "keys": {"known": "pk"}}, raising=False)

    monkeypatch.setattr(routes.jwt, "get_unverified_header", lambda _t: {"kid": "known"})
    monkeypatch.setattr(routes.jwt, "decode", lambda *_a, **_k: {"typ": "Logout", "sub": "idm-u"})

    calls = {"invalidate_all": 0, "update_user": 0}

    async def _invalidate_all(_db, user_id):
        calls["invalidate_all"] += 1
        calls["user_id"] = user_id

    async def _update(_db, user):
        calls["update_user"] += 1
        calls["user"] = user

    async def _get_user(*_args, **_kwargs):
        return _user_with_keycloak_session("sid-any")

    monkeypatch.setattr(routes, "invalidate_all_user_tokens", _invalidate_all)
    monkeypatch.setattr(routes, "update_user", _update)
    monkeypatch.setattr(routes, "get_user_by_idm_user_id", _get_user)

    res = await app_http_client.post("/oidc/k_logout", data={"logout_token": "token"})
    assert res.status_code == 204
    assert calls["invalidate_all"] == 1
    assert calls["update_user"] == 1
    assert "keycloak" not in calls["user"].idm_data
