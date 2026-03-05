# -*- coding: utf-8 -*-

import sys
import types
from types import SimpleNamespace

import pytest

if "elasticsearch._async.helpers" not in sys.modules:
    _helpers = types.ModuleType("elasticsearch._async.helpers")

    async def _async_bulk(*_args, **_kwargs):
        return (0, [])

    _helpers.async_bulk = _async_bulk
    _helpers.async_reindex = _async_bulk
    _helpers.async_scan = _async_bulk
    _helpers.async_streaming_bulk = _async_bulk
    sys.modules["elasticsearch._async.helpers"] = _helpers

from wirecloud.catalogue import plugins


class _FakeFastAPI:
    def __init__(self):
        self.calls = []

    def include_router(self, *args, **kwargs):
        self.calls.append((args, kwargs))


async def test_catalogue_plugin_init_and_urls():
    plugin = plugins.WirecloudCataloguePlugin(None)
    assert plugin.urls == plugins.catalogue_patterns

    app = _FakeFastAPI()
    plugins.WirecloudCataloguePlugin(app)
    assert len(app.calls) == 1
    assert app.calls[0][1]["prefix"] == "/catalogue"


async def test_catalogue_plugin_validator_defaults_and_type(monkeypatch, tmp_path):
    plugin = plugins.WirecloudCataloguePlugin(None)
    validate = plugin.get_config_validators()[0]

    settings_obj = SimpleNamespace(BASEDIR=str(tmp_path))
    validate(settings_obj, False)
    assert settings_obj.CATALOGUE_MEDIA_ROOT.endswith("catalogue/media")

    monkeypatch.setattr(plugins.os.path, "exists", lambda _path: True)
    validate(settings_obj, False)

    settings_obj2 = SimpleNamespace(BASEDIR=str(tmp_path), CATALOGUE_MEDIA_ROOT=123)
    with pytest.raises(ValueError, match="CATALOGUE_MEDIA_ROOT must be a string"):
        validate(settings_obj2, False)


async def test_catalogue_plugin_validator_makedirs_error(monkeypatch, tmp_path):
    plugin = plugins.WirecloudCataloguePlugin(None)
    validate = plugin.get_config_validators()[0]

    settings_obj = SimpleNamespace(BASEDIR=str(tmp_path), CATALOGUE_MEDIA_ROOT=str(tmp_path / "x"))

    monkeypatch.setattr(plugins.os.path, "exists", lambda _path: False)

    def _boom(*_args, **_kwargs):
        raise RuntimeError("nope")

    monkeypatch.setattr(plugins.os, "makedirs", _boom)

    with pytest.raises(ValueError, match="Failed to create CATALOGUE_MEDIA_ROOT"):
        validate(settings_obj, False)
