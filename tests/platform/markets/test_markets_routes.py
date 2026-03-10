# -*- coding: utf-8 -*-

import os
from types import SimpleNamespace

import pytest

from wirecloud.main import app
from wirecloud import main as main_module
from wirecloud.platform.markets import routes
from wirecloud.commons.auth.utils import get_user_csrf, get_user_no_csrf


async def _noop_close():
    return None


main_module.close = _noop_close


@pytest.fixture(autouse=True)
def _patch_gettext(monkeypatch):
    monkeypatch.setattr(routes, "_", lambda text: text)


def _user(username="alice", is_superuser=False, can_create=False, can_delete=False, can_publish=False):
    def _has_perm(codename):
        return (
            (codename == "MARKETPLACE.CREATE" and can_create)
            or (codename == "MARKETPLACE.DELETE" and can_delete)
            or (codename == "MARKETPLACE.PUBLISH" and can_publish)
        )

    return SimpleNamespace(
        id=routes.ObjectId(),
        username=username,
        is_superuser=is_superuser,
        has_perm=_has_perm,
    )


@pytest.fixture()
def auth_user():
    return _user()


@pytest.fixture(autouse=True)
def _override_auth(auth_user):
    async def _user_dep():
        return auth_user

    app.dependency_overrides[get_user_no_csrf] = _user_dep
    app.dependency_overrides[get_user_csrf] = _user_dep
    yield
    app.dependency_overrides.pop(get_user_no_csrf, None)
    app.dependency_overrides.pop(get_user_csrf, None)


async def test_get_market_collection(app_client, monkeypatch, auth_user):
    market = SimpleNamespace(
        id=routes.ObjectId(),
        user_id=auth_user.id,
        name="local",
        public=True,
        options=SimpleNamespace(
            model_dump=lambda: {"name": "local", "type": "wirecloud", "title": "Local", "url": "https://example.org", "public": True, "user": "alice"}
        ),
    )

    async def _markets(_db, _user):
        return [market]

    async def _market_user(_db, _market):
        return SimpleNamespace(username="alice")

    monkeypatch.setattr(routes, "get_markets_for_user", _markets)
    monkeypatch.setattr(routes, "get_market_user", _market_user)

    response = await app_client.get("/api/markets/", headers={"accept": "application/json"})
    assert response.status_code == 200
    payload = response.json()
    assert payload[0]["name"] == "local"
    assert payload[0]["user"] == "alice"
    assert payload[0]["permissions"]["delete"] is True


async def test_create_market_collection_branches(app_client, monkeypatch, auth_user):
    monkeypatch.setattr("wirecloud.platform.markets.utils.get_market_classes", lambda: {"wirecloud": object})

    monkeypatch.setattr(routes, "build_error_response", lambda _request, status, msg, details=None: routes.Response(status_code=status, content=str(msg)))

    async def _missing_target(_db, _username):
        return None

    monkeypatch.setattr(routes, "get_user_with_all_info_by_username", _missing_target)
    invalid = await app_client.post(
        "/api/markets/",
        json={"name": "local", "type": "wirecloud", "title": "Local", "url": "https://example.org", "public": True, "user": "other"},
        headers={"accept": "application/json", "content-type": "application/json"},
    )
    assert invalid.status_code == 422

    target_user = _user(username="other")

    async def _target(_db, _username):
        return target_user

    monkeypatch.setattr(routes, "get_user_with_all_info_by_username", _target)
    denied = await app_client.post(
        "/api/markets/",
        json={"name": "local", "type": "wirecloud", "title": "Local", "url": "https://example.org", "public": True, "user": "other"},
        headers={"accept": "application/json", "content-type": "application/json"},
    )
    assert denied.status_code == 403

    auth_user.is_superuser = True

    async def _create_false(_db, _market):
        return False

    monkeypatch.setattr(routes, "create_market", _create_false)
    conflict = await app_client.post(
        "/api/markets/",
        json={"name": "local", "type": "wirecloud", "title": "Local", "url": "https://example.org", "public": True, "user": "other"},
        headers={"accept": "application/json", "content-type": "application/json"},
    )
    assert conflict.status_code == 409

    created = {"n": 0}

    async def _create_true(_db, _market):
        return True

    class _Manager:
        async def create(self, _db, _request, _user):
            created["n"] += 1

    async def _managers(_db, _target_user):
        return {f"{target_user.username}/local": _Manager()}

    monkeypatch.setattr(routes, "create_market", _create_true)
    monkeypatch.setattr(routes, "get_market_managers", _managers)
    ok = await app_client.post(
        "/api/markets/",
        json={"name": "local", "type": "wirecloud", "title": "Local", "url": "https://example.org", "public": True, "user": "other"},
        headers={"accept": "application/json", "content-type": "application/json"},
    )
    assert ok.status_code == 201
    assert created["n"] == 1

    async def _managers_own(_db, _target_user):
        return {f"{auth_user.username}/own": _Manager()}

    monkeypatch.setattr(routes, "get_market_managers", _managers_own)
    own = await app_client.post(
        "/api/markets/",
        json={"name": "own", "type": "wirecloud", "title": "Own", "url": "https://own.example.org", "public": False},
        headers={"accept": "application/json", "content-type": "application/json"},
    )
    assert own.status_code == 201


async def test_delete_market_entry_branches(app_client, monkeypatch, auth_user):
    monkeypatch.setattr(routes, "build_error_response", lambda _request, status, msg, details=None: routes.Response(status_code=status, content=str(msg)))

    denied = await app_client.delete("/api/market/bob/local", headers={"accept": "application/json"})
    assert denied.status_code == 403

    auth_user.is_superuser = True

    async def _missing_user(_db, _username):
        return None

    monkeypatch.setattr(routes, "get_user_by_username", _missing_user)
    missing_user = await app_client.delete("/api/market/bob/local", headers={"accept": "application/json"})
    assert missing_user.status_code == 404

    target = _user(username="bob")

    async def _target_user(_db, _username):
        return target

    async def _delete_false(_db, _target, _name):
        return False

    monkeypatch.setattr(routes, "get_user_by_username", _target_user)
    monkeypatch.setattr(routes, "delete_market_by_name", _delete_false)
    monkeypatch.setattr(routes, "get_market_managers", lambda _db, _u: _managers())

    async def _managers():
        return {"bob/local": SimpleNamespace(delete=lambda *_args, **_kwargs: _noop())}

    async def _noop():
        return None

    missing_market = await app_client.delete("/api/market/bob/local", headers={"accept": "application/json"})
    assert missing_market.status_code == 404

    deleted = {"n": 0}

    async def _delete_true(_db, _target, _name):
        return True

    class _Manager:
        async def delete(self, _db, _request):
            deleted["n"] += 1

    monkeypatch.setattr(routes, "delete_market_by_name", _delete_true)
    monkeypatch.setattr(routes, "get_market_managers", lambda _db, _u: _managers2())

    async def _managers2():
        return {"bob/local": _Manager()}

    ok = await app_client.delete("/api/market/bob/local", headers={"accept": "application/json"})
    assert ok.status_code == 204
    assert deleted["n"] == 1

    auth_user.username = "alice"
    monkeypatch.setattr(routes, "get_market_managers", lambda _db, _u: _own_managers())

    async def _own_managers():
        return {"alice/local": _Manager()}

    own = await app_client.delete("/api/market/alice/local", headers={"accept": "application/json"})
    assert own.status_code == 204


async def test_publish_service_process_branches(app_client, monkeypatch, auth_user):
    monkeypatch.setattr(routes, "build_error_response", lambda _request, status, msg, details=None: routes.Response(status_code=status, content=str(msg)))

    async def _missing_resource(*_args, **_kwargs):
        return None

    monkeypatch.setattr(routes, "get_catalogue_resource", _missing_resource)
    not_found = await app_client.post(
        "/api/markets/publish",
        json={"resource": "wirecloud/example/1.0.0", "marketplaces": [{"market": "alice/local"}]},
        headers={"accept": "application/json", "content-type": "application/json"},
    )
    assert not_found.status_code == 404

    resource = SimpleNamespace(template_uri="component.wgt", is_available_for=lambda _user: False)

    async def _resource(*_args, **_kwargs):
        return resource

    monkeypatch.setattr(routes, "get_catalogue_resource", _resource)
    denied = await app_client.post(
        "/api/markets/publish",
        json={"resource": "wirecloud/example/1.0.0", "marketplaces": [{"market": "alice/local"}]},
        headers={"accept": "application/json", "content-type": "application/json"},
    )
    assert denied.status_code == 403

    auth_user.is_superuser = True
    resource.is_available_for = lambda _user: True
    monkeypatch.setattr(routes.catalogue.wgt_deployer, "get_base_dir", lambda *_args, **_kwargs: "/tmp/base")
    monkeypatch.setattr(routes, "WgtFile", lambda path: f"WGT:{path}")

    class _ManagerError:
        async def publish(self, _db, _endpoint, _wgt_file, _user, request=None):
            raise RuntimeError("boom")

    async def _managers_all_error(_db, _user):
        return {"alice/local": _ManagerError()}

    monkeypatch.setattr(routes, "get_market_managers", _managers_all_error)
    all_error = await app_client.post(
        "/api/markets/publish",
        json={"resource": "wirecloud/example/1.0.0", "marketplaces": [{"market": "alice/local"}]},
        headers={"accept": "application/json", "content-type": "application/json"},
    )
    assert all_error.status_code == 502

    class _ManagerOk:
        async def publish(self, _db, _endpoint, _wgt_file, _user, request=None):
            return None

    async def _managers_partial(_db, _user):
        return {"alice/local": _ManagerError(), "alice/other": _ManagerOk()}

    monkeypatch.setattr(routes, "get_market_managers", _managers_partial)
    partial = await app_client.post(
        "/api/markets/publish",
        json={"resource": "wirecloud/example/1.0.0", "marketplaces": [{"market": "alice/local"}, {"market": "alice/other"}]},
        headers={"accept": "application/json", "content-type": "application/json"},
    )
    assert partial.status_code == 200

    async def _managers_ok(_db, _user):
        return {"alice/local": _ManagerOk()}

    monkeypatch.setattr(routes, "get_market_managers", _managers_ok)
    success = await app_client.post(
        "/api/markets/publish",
        json={"resource": "wirecloud/example/1.0.0", "marketplaces": [{"market": "alice/local"}]},
        headers={"accept": "application/json", "content-type": "application/json"},
    )
    assert success.status_code == 204
