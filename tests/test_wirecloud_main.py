# -*- coding: utf-8 -*-

from types import SimpleNamespace

import pytest

from wirecloud import main


async def test_wirecloud_main_lifespan_calls_validate_and_close(monkeypatch):
    calls = {"validate": 0, "close": 0}

    async def _validate():
        calls["validate"] += 1

    async def _close():
        calls["close"] += 1

    monkeypatch.setattr(main, "validate_settings", _validate)
    monkeypatch.setattr(main, "close", _close)

    async with main.lifespan(main.app):
        assert calls["validate"] == 1
        assert calls["close"] == 0

    assert calls["close"] == 1


def test_wirecloud_main_custom_openapi(monkeypatch):
    calls = {"openapi": 0}
    main.app.openapi_schema = None

    def _get_openapi(**_kwargs):
        calls["openapi"] += 1
        return {"info": {}, "components": {"schemas": {}}}

    monkeypatch.setattr(main, "get_openapi", _get_openapi)
    monkeypatch.setattr(main, "get_extra_openapi_schemas", lambda: {"Extra": {"type": "object"}})

    schema = main.custom_openapi()
    assert "x-logo" in schema["info"]
    assert "Extra" in schema["components"]["schemas"]
    assert calls["openapi"] == 1

    schema_cached = main.custom_openapi()
    assert schema_cached is schema
    assert calls["openapi"] == 1

    assert main.app.openapi == main.custom_openapi


def test_wirecloud_main_bootstrap_guards(monkeypatch):
    source_path = main.__file__
    with open(source_path, "r", encoding="utf-8") as f:
        source = f.read()

    start = source.index("import sys")
    end = source.index("from contextlib import asynccontextmanager")
    padding = "\n" * source[:start].count("\n")
    bootstrap = padding + source[start:end]

    import builtins
    import types

    original_import = builtins.__import__
    fake_sys_low = types.SimpleNamespace(version_info=(3, 8), path=[])

    def _import_low(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "sys":
            return fake_sys_low
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", _import_low)
    g = {"__file__": source_path}
    with pytest.raises(Exception, match="Python 3.9"):
        exec(compile(bootstrap, source_path, "exec"), g, g)

    fake_sys = types.SimpleNamespace(version_info=(3, 9), path=[])

    def _import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "sys":
            return fake_sys
        if name == "wirecloud":
            raise ImportError("no wirecloud")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", _import)
    g2 = {"__file__": source_path}
    exec(compile(bootstrap, source_path, "exec"), g2, g2)
    assert len(fake_sys.path) == 1
