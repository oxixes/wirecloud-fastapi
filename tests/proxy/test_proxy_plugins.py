# -*- coding: utf-8 -*-

from types import SimpleNamespace

import pytest

from wirecloud.proxy import plugins


class _FakeFastAPI:
    def __init__(self):
        self.calls = []

    def include_router(self, *args, **kwargs):
        self.calls.append((args, kwargs))


async def test_proxy_plugin_init_urls_and_router_registration():
    plugin = plugins.WirecloudProxyPlugin(None)
    assert plugin.urls == plugins.proxy_patterns

    app = _FakeFastAPI()
    plugins.WirecloudProxyPlugin(app)
    assert len(app.calls) == 1
    assert app.calls[0][1]["prefix"] == "/cdp"


async def test_proxy_plugin_validator_happy_path_and_warnings(monkeypatch):
    plugin = plugins.WirecloudProxyPlugin(None)
    validate = plugin.get_config_validators()[0]

    settings_obj = SimpleNamespace(
        PROXY_WS_MAX_MSG_SIZE=4 * 1024 * 1024,
        PROXY_WHITELIST_ENABLED=True,
        PROXY_WHITELIST=[],
        PROXY_BLACKLIST_ENABLED=True,
        PROXY_BLACKLIST=[],
    )

    defaults = []

    def _set_default(name, value):
        defaults.append((name, value))

    warnings = []

    monkeypatch.setattr(plugins, "_set_default_if_missing", _set_default)
    monkeypatch.setattr(plugins.logger, "warning", lambda msg: warnings.append(msg))

    validate(settings_obj, False)

    assert ("PROXY_WS_MAX_MSG_SIZE", 4 * 1024 * 1024) in defaults
    assert ("PROXY_WHITELIST_ENABLED", False) in defaults
    assert ("PROXY_WHITELIST", []) in defaults
    assert ("PROXY_BLACKLIST_ENABLED", False) in defaults
    assert ("PROXY_BLACKLIST", []) in defaults
    assert len(warnings) >= 2


@pytest.mark.parametrize(
    "settings_obj,error",
    [
        (SimpleNamespace(PROXY_WS_MAX_MSG_SIZE="bad"), "PROXY_WS_MAX_MSG_SIZE must be an integer"),
        (SimpleNamespace(PROXY_WS_MAX_MSG_SIZE=0), "PROXY_WS_MAX_MSG_SIZE must be a positive integer"),
        (SimpleNamespace(PROXY_WS_MAX_MSG_SIZE=1, PROXY_WHITELIST_ENABLED="x"), "PROXY_WHITELIST_ENABLED must be a boolean"),
        (SimpleNamespace(PROXY_WS_MAX_MSG_SIZE=1, PROXY_WHITELIST_ENABLED=False, PROXY_WHITELIST="x"), "PROXY_WHITELIST must be a list or tuple"),
        (SimpleNamespace(PROXY_WS_MAX_MSG_SIZE=1, PROXY_WHITELIST_ENABLED=False, PROXY_WHITELIST=[1]), "Each item in PROXY_WHITELIST must be a string"),
        (SimpleNamespace(PROXY_WS_MAX_MSG_SIZE=1, PROXY_WHITELIST_ENABLED=False, PROXY_WHITELIST=[" "]), "PROXY_WHITELIST cannot contain empty strings"),
        (SimpleNamespace(PROXY_WS_MAX_MSG_SIZE=1, PROXY_WHITELIST_ENABLED=False, PROXY_WHITELIST=[], PROXY_BLACKLIST_ENABLED="x"), "PROXY_BLACKLIST_ENABLED must be a boolean"),
        (SimpleNamespace(PROXY_WS_MAX_MSG_SIZE=1, PROXY_WHITELIST_ENABLED=False, PROXY_WHITELIST=[], PROXY_BLACKLIST_ENABLED=False, PROXY_BLACKLIST="x"), "PROXY_BLACKLIST must be a list or tuple"),
        (SimpleNamespace(PROXY_WS_MAX_MSG_SIZE=1, PROXY_WHITELIST_ENABLED=False, PROXY_WHITELIST=[], PROXY_BLACKLIST_ENABLED=False, PROXY_BLACKLIST=[1]), "Each item in PROXY_BLACKLIST must be a string"),
        (SimpleNamespace(PROXY_WS_MAX_MSG_SIZE=1, PROXY_WHITELIST_ENABLED=False, PROXY_WHITELIST=[], PROXY_BLACKLIST_ENABLED=False, PROXY_BLACKLIST=[" "]), "PROXY_BLACKLIST cannot contain empty strings"),
    ],
)
async def test_proxy_plugin_validator_errors(monkeypatch, settings_obj, error):
    plugin = plugins.WirecloudProxyPlugin(None)
    validate = plugin.get_config_validators()[0]

    monkeypatch.setattr(plugins, "_set_default_if_missing", lambda *_args, **_kwargs: None)

    with pytest.raises(ValueError, match=error):
        validate(settings_obj, False)


async def test_proxy_plugin_validator_large_ws_warning(monkeypatch):
    plugin = plugins.WirecloudProxyPlugin(None)
    validate = plugin.get_config_validators()[0]

    settings_obj = SimpleNamespace(
        PROXY_WS_MAX_MSG_SIZE=101 * 1024 * 1024,
        PROXY_WHITELIST_ENABLED=False,
        PROXY_WHITELIST=[],
        PROXY_BLACKLIST_ENABLED=False,
        PROXY_BLACKLIST=[],
    )

    warnings = []

    monkeypatch.setattr(plugins, "_set_default_if_missing", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(plugins.logger, "warning", lambda msg: warnings.append(msg))

    validate(settings_obj, False)
    assert any("very large" in msg for msg in warnings)


async def test_proxy_plugin_validator_default_and_second_pass_checks(monkeypatch):
    plugin = plugins.WirecloudProxyPlugin(None)
    validate = plugin.get_config_validators()[0]

    settings_obj = SimpleNamespace(
        PROXY_WHITELIST_ENABLED=False,
        PROXY_WHITELIST=[],
        PROXY_BLACKLIST_ENABLED=False,
        PROXY_BLACKLIST=[],
    )

    def _set_default(name, value):
        if not hasattr(settings_obj, name):
            setattr(settings_obj, name, value)

    monkeypatch.setattr(plugins, "_set_default_if_missing", _set_default)
    validate(settings_obj, False)
    assert settings_obj.PROXY_WS_MAX_MSG_SIZE == 4 * 1024 * 1024

    settings_obj2 = SimpleNamespace(
        PROXY_WS_MAX_MSG_SIZE=1,
        PROXY_WHITELIST_ENABLED=False,
        PROXY_WHITELIST=[],
        PROXY_BLACKLIST_ENABLED=False,
        PROXY_BLACKLIST=[],
    )

    def _set_bad_type(name, value):
        if name == "PROXY_WS_MAX_MSG_SIZE":
            settings_obj2.PROXY_WS_MAX_MSG_SIZE = "bad"

    monkeypatch.setattr(plugins, "_set_default_if_missing", _set_bad_type)
    with pytest.raises(ValueError, match="must be an integer"):
        validate(settings_obj2, False)

    settings_obj3 = SimpleNamespace(
        PROXY_WS_MAX_MSG_SIZE=1,
        PROXY_WHITELIST_ENABLED=False,
        PROXY_WHITELIST=[],
        PROXY_BLACKLIST_ENABLED=False,
        PROXY_BLACKLIST=[],
    )

    def _set_bad_value(name, value):
        if name == "PROXY_WS_MAX_MSG_SIZE":
            settings_obj3.PROXY_WS_MAX_MSG_SIZE = 0

    monkeypatch.setattr(plugins, "_set_default_if_missing", _set_bad_value)
    with pytest.raises(ValueError, match="must be a positive integer"):
        validate(settings_obj3, False)


async def test_proxy_plugin_validator_valid_multiple_entries(monkeypatch):
    plugin = plugins.WirecloudProxyPlugin(None)
    validate = plugin.get_config_validators()[0]

    settings_obj = SimpleNamespace(
        PROXY_WS_MAX_MSG_SIZE=1024,
        PROXY_WHITELIST_ENABLED=True,
        PROXY_WHITELIST=["a.example.org", "b.example.org"],
        PROXY_BLACKLIST_ENABLED=True,
        PROXY_BLACKLIST=["x.example.org", "y.example.org"],
    )

    monkeypatch.setattr(plugins, "_set_default_if_missing", lambda *_args, **_kwargs: None)
    validate(settings_obj, False)
