# -*- coding: utf-8 -*-

import base64
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from bson import ObjectId

from src import settings
from wirecloud.commons.auth.schemas import UserAll
from wirecloud.database import Id
from wirecloud.fiware import plugins


@pytest.fixture(autouse=True)
def _patch_gettext(monkeypatch):
    monkeypatch.setattr(plugins, "_", lambda text: text)


def _sample_user(idm_data=None, username="user1"):
    return UserAll(
        id=Id(str(ObjectId())),
        username=username,
        email=f"{username}@example.com",
        first_name="First",
        last_name="Last",
        is_superuser=False,
        is_staff=False,
        is_active=True,
        date_joined=datetime.now(timezone.utc),
        last_login=None,
        idm_data=idm_data or {},
        groups=[],
        permissions=[],
    )


async def test_fiware_module_constants():
    from wirecloud import fiware

    assert fiware.__version__ == ".".join(map(str, fiware.__version_info__))
    assert fiware.DEFAULT_FIWARE_HOME.startswith("https://")
    assert fiware.FIWARE_LAB_CLOUD_SERVER.startswith("https://")


async def test_fiware_bae_manager_create_delete_and_init_validation(monkeypatch):
    options = SimpleNamespace(name="BAE Market", url="https://bae.example.org", public=False)

    with pytest.raises(ValueError, match="User must be specified"):
        plugins.FIWAREBAEManager(None, "name", options)

    manager = plugins.FIWAREBAEManager("alice", "market", options)

    async def _wirecloud_user(_db, _username):
        return _sample_user({}, username="wirecloud")

    create_workspace = AsyncMock()
    get_workspace = AsyncMock()

    monkeypatch.setattr(plugins, "get_user_with_all_info_by_username", _wirecloud_user)
    monkeypatch.setattr(plugins, "create_workspace", create_workspace)
    monkeypatch.setattr(plugins, "get_workspace_by_username_and_name", get_workspace)

    db = SimpleNamespace()
    request = SimpleNamespace()
    user = _sample_user({}, username="alice")

    await manager.create(db, request, user)
    create_workspace.assert_awaited_once()

    _, kwargs = create_workspace.await_args
    assert kwargs["mashup"] == "CoNWeT/bae-marketplace/0.1.1"
    assert kwargs["preferences"] == {"server_url": "https://bae.example.org"}

    await manager.delete(db, request)
    get_workspace.assert_awaited_once_with(db, creator_username="alice", name="market")


async def test_plugin_accessors_and_context_paths(monkeypatch):
    plugin = plugins.FiWareWirecloudPlugin(None)

    monkeypatch.setattr(settings, "OID_CONNECT_PLUGIN", "other")
    plugins.IDM_SUPPORT_ENABLED = False

    markets = plugin.get_market_classes()
    assert markets["fiware-bae"] == plugins.FIWAREBAEManager

    defs = plugin.get_platform_context_definitions()
    assert list(defs.keys()) == ["fiware_version"]
    values = await plugin.get_platform_context_current_values(None, None, None, None)
    assert "fiware_token_available" not in values

    constants = plugin.get_constants()
    assert "FIWARE_HOME" in constants
    assert "FIWARE_OFFICIAL_PORTAL" not in constants

    assert plugin.get_widget_api_extensions("classic", []) == []
    assert plugin.get_widget_api_extensions("classic", ["NGSI", "ObjectStorage"]) == [
        "js/WirecloudAPI/NGSIAPI.js",
        "js/ObjectStorage/ObjectStorageAPI.js",
    ]
    assert plugin.get_operator_api_extensions("classic", ["NGSI", "ObjectStorage"]) == [
        "js/WirecloudAPI/NGSIAPI.js",
        "js/ObjectStorage/ObjectStorageAPI.js",
    ]
    assert plugin.get_operator_api_extensions("classic", ["ObjectStorage"]) == [
        "js/ObjectStorage/ObjectStorageAPI.js",
    ]
    assert plugin.get_operator_api_extensions("classic", ["NGSI"]) == [
        "js/WirecloudAPI/NGSIAPI.js",
    ]

    assert plugin.get_proxy_processors() == ()
    ctx = plugin.get_template_context_processors(SimpleNamespace())
    assert ctx["FIWARE_IDM_SERVER"] is None
    assert ctx["FIWARE_IDM_PUBLIC_URL"] is None

    monkeypatch.setattr(settings, "OID_CONNECT_PLUGIN", "fiware")
    monkeypatch.setattr(settings, "OID_CONNECT_CLIENT_ID", "client-id")
    monkeypatch.setattr(settings, "FIWARE_HOME", "https://home.example.org", raising=False)
    monkeypatch.setattr(settings, "FIWARE_PORTALS", ("https://portal.example.org",), raising=False)
    monkeypatch.setattr(settings, "FIWARE_OFFICIAL_PORTAL", True, raising=False)
    monkeypatch.setattr(settings, "FIWARE_IDM_SERVER", "https://idm.example.org", raising=False)
    monkeypatch.setattr(settings, "FIWARE_IDM_PUBLIC_URL", "https://public-idm.example.org", raising=False)
    monkeypatch.setattr(settings, "FIWARE_EXTENDED_PERMISSIONS", ["openid", "profile"], raising=False)

    plugins.IDM_SUPPORT_ENABLED = True

    defs2 = plugin.get_platform_context_definitions()
    assert "fiware_token_available" in defs2

    values2 = await plugin.get_platform_context_current_values(None, None, _sample_user({}), None)
    assert values2["fiware_token_available"] is False

    values3 = await plugin.get_platform_context_current_values(
        None,
        None,
        _sample_user({"fiware": {"idm_token": "token"}}),
        None,
    )
    assert values3["fiware_token_available"] is True

    constants2 = plugin.get_constants()
    assert constants2["FIWARE_OFFICIAL_PORTAL"] is True
    assert constants2["FIWARE_IDM_SERVER"] == "https://idm.example.org"

    assert plugin.get_proxy_processors() == ("src.wirecloud.fiware.proxy.IDMTokenProcessor",)
    ctx2 = plugin.get_template_context_processors(SimpleNamespace())
    assert ctx2["FIWARE_IDM_SERVER"] == "https://idm.example.org"


async def test_plugin_authorization_token_user_and_logout_functions(monkeypatch):
    plugin = plugins.FiWareWirecloudPlugin(None)

    monkeypatch.setattr(settings, "OID_CONNECT_CLIENT_ID", "wc-client")
    monkeypatch.setattr(settings, "FIWARE_IDM_SERVER", "https://idm.example.org/", raising=False)
    monkeypatch.setattr(settings, "FIWARE_EXTENDED_PERMISSIONS", ["perm a", "perm-b"], raising=False)

    auth_fn = plugin.get_idm_get_authorization_url_functions()["fiware"]
    url_template = auth_fn()
    assert "oauth2/authorize" in url_template.urlpattern
    assert "client_id=wc-client" in url_template.urlpattern
    assert "response_type=code" in url_template.urlpattern
    assert "scope=perm%20a%20perm-b" in url_template.urlpattern

    monkeypatch.setattr(settings, "FIWARE_EXTENDED_PERMISSIONS", [])
    url_template2 = auth_fn()
    assert "scope=" not in url_template2.urlpattern

    monkeypatch.setattr(plugins, "FIWARE_AUTHORIZATION_ENDPOINT", "oauth2/authorize?existing=1")
    url_template3 = auth_fn()
    assert "existing=1&" in url_template3.urlpattern

    plugin.AUTH_TOKEN = "auth-b64"

    token_fn = plugin.get_idm_get_token_functions()["fiware"]
    with pytest.raises(ValueError, match="Either code or refresh_token"):
        await token_fn(code=None, refresh_token=None, redirect_uri="http://cb")

    async def _request_ok(_url, data, **_kwargs):
        if data.get("grant_type") == "authorization_code":
            return {"access_token": "a1", "refresh_token": "r1"}
        return {"access_token": "a2", "refresh_token": "r2"}

    monkeypatch.setattr(plugins, "make_oidc_provider_request", _request_ok)

    by_code = await token_fn(code="code-a", refresh_token=None, redirect_uri="http://cb")
    assert by_code["access_token"] == "a1"

    by_refresh = await token_fn(code=None, refresh_token="refresh-a", redirect_uri=None)
    assert by_refresh["access_token"] == "a2"

    async def _request_bad(*_args, **_kwargs):
        raise RuntimeError("provider down")

    monkeypatch.setattr(plugins, "make_oidc_provider_request", _request_bad)
    with pytest.raises(ValueError, match="Exception while requesting OIDC access token"):
        await token_fn(code="code-a", refresh_token=None, redirect_uri="http://cb")
    with pytest.raises(ValueError, match="Exception while requesting OIDC access token"):
        await token_fn(code=None, refresh_token="refresh-a", redirect_uri=None)

    async def _request_missing_tokens(*_args, **_kwargs):
        return {"access_token": "only"}

    monkeypatch.setattr(plugins, "make_oidc_provider_request", _request_missing_tokens)
    with pytest.raises(ValueError, match="missing access_token or refresh_token"):
        await token_fn(code="code-a", refresh_token=None, redirect_uri="http://cb")

    monkeypatch.setattr(settings, "OID_CONNECT_DATA", {"userinfo_endpoint": "https://idm.example.org/user"}, raising=False)
    user_fn = plugin.get_idm_get_user_functions()["fiware"]

    with pytest.raises(ValueError, match="Access token must be provided"):
        await user_fn({})

    async def _request_user_ok(_url, data, auth):
        assert data is None
        assert auth == "acc"
        return {
            "id": "sub-1",
            "username": "alice",
            "email": "alice@example.org",
            "displayName": "Alice Bob",
            "roles": [{"name": "admin"}, {"name": "dev"}],
        }

    monkeypatch.setattr(plugins, "make_oidc_provider_request", _request_user_ok)
    user_data = await user_fn({"access_token": "acc"})
    assert user_data["sub"] == "sub-1"
    assert user_data["preferred_username"] == "alice"
    assert user_data["given_name"] == "Alice"
    assert user_data["family_name"] == "Bob"
    assert user_data["wirecloud"]["groups"] == ["admin", "dev"]

    async def _request_user_no_display(*_args, **_kwargs):
        return {"id": "sub-2", "username": "bob"}

    monkeypatch.setattr(plugins, "make_oidc_provider_request", _request_user_no_display)
    user_data2 = await user_fn({"access_token": "acc"})
    assert user_data2["given_name"] == ""
    assert user_data2["family_name"] == ""

    async def _request_user_error(*_args, **_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(plugins, "make_oidc_provider_request", _request_user_error)
    with pytest.raises(ValueError, match="Exception while requesting OIDC access token"):
        await user_fn({"access_token": "acc"})

    async def _request_user_missing(*_args, **_kwargs):
        return {"id": "sub-3"}

    monkeypatch.setattr(plugins, "make_oidc_provider_request", _request_user_missing)
    with pytest.raises(ValueError, match="missing username"):
        await user_fn({"access_token": "acc"})

    logout_fn = plugin.get_idm_backchannel_logout_functions()["fiware"]

    with pytest.raises(ValueError, match="Access token must be provided"):
        await logout_fn("")

    monkeypatch.setattr(settings, "OID_CONNECT_BACKCHANNEL_LOGOUT", False)
    await logout_fn("refresh-1")

    monkeypatch.setattr(settings, "OID_CONNECT_BACKCHANNEL_LOGOUT", True)
    call = {}

    async def _request_logout_ok(url, data, **kwargs):
        call["url"] = url
        call["data"] = data
        call["kwargs"] = kwargs

    monkeypatch.setattr(plugins, "make_oidc_provider_request", _request_logout_ok)
    await logout_fn("refresh-2")
    assert "oauth2/revoke" in call["url"]
    assert call["data"]["token"] == "refresh-2"

    logger_error = Mock()
    monkeypatch.setattr(plugins.logger, "error", logger_error)

    async def _request_logout_fail(*_args, **_kwargs):
        raise RuntimeError("down")

    monkeypatch.setattr(plugins, "make_oidc_provider_request", _request_logout_fail)
    await logout_fn("refresh-3")
    logger_error.assert_called_once()


async def test_plugin_config_validator_and_populate(monkeypatch):
    plugin = plugins.FiWareWirecloudPlugin(None)
    validate = plugin.get_config_validators()[0]

    plugins.IDM_SUPPORT_ENABLED = False

    not_fiware = SimpleNamespace(OID_CONNECT_PLUGIN="other", OID_CONNECT_ENABLED=True)
    await validate(not_fiware, False)
    assert plugins.IDM_SUPPORT_ENABLED is False

    fiware_disabled = SimpleNamespace(OID_CONNECT_PLUGIN="fiware", OID_CONNECT_ENABLED=False)
    await validate(fiware_disabled, False)
    assert plugins.IDM_SUPPORT_ENABLED is False

    with pytest.raises(ValueError, match="FIWARE IDM server"):
        await validate(SimpleNamespace(OID_CONNECT_PLUGIN="fiware", OID_CONNECT_ENABLED=True), False)

    with pytest.raises(ValueError, match="FIWARE App ID"):
        await validate(
            SimpleNamespace(OID_CONNECT_PLUGIN="fiware", OID_CONNECT_ENABLED=True, FIWARE_IDM_SERVER="https://idm"),
            False,
        )

    with pytest.raises(ValueError, match="FIWARE App Secret"):
        await validate(
            SimpleNamespace(
                OID_CONNECT_PLUGIN="fiware",
                OID_CONNECT_ENABLED=True,
                FIWARE_IDM_SERVER="https://idm",
                FIWARE_APP_ID="app",
            ),
            False,
        )

    config = SimpleNamespace(
        OID_CONNECT_PLUGIN="fiware",
        OID_CONNECT_ENABLED=True,
        FIWARE_IDM_SERVER="https://idm",
        FIWARE_APP_ID="app",
        FIWARE_APP_SECRET="secret",
    )
    await validate(config, False)
    expected_auth = base64.urlsafe_b64encode(b"app:secret").decode()
    assert plugin.AUTH_TOKEN == expected_auth

    populate_calls = []

    async def _populate(_db, _user, vendor, name, version, path):
        populate_calls.append((vendor, name, version, path))
        return name in {"bae-details", "bae-marketplace"}

    monkeypatch.setattr(plugins, "populate_component", _populate)
    updated = await plugin.populate(SimpleNamespace(), _sample_user({}, username="wirecloud"))

    assert updated is True
    assert len(populate_calls) == 4
    assert {name for _, name, _, _ in populate_calls} == {
        "bae-browser",
        "bae-details",
        "bae-search-filters",
        "bae-marketplace",
    }
