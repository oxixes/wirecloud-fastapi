# -*- coding: utf-8 -*-

import builtins
import types
from pathlib import Path

from wirecloud import settings as imported_settings


def _load_settings_bootstrap(monkeypatch, import_impl):
    source_path = imported_settings.__file__
    with open(source_path, "r", encoding="utf-8") as f:
        source = f.read()

    original_import = builtins.__import__
    fake_sys = types.SimpleNamespace(path=[])

    def _import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "sys":
            return fake_sys
        return import_impl(name, globals, locals, fromlist, level, original_import)

    monkeypatch.setattr(builtins, "__import__", _import)
    g = {"__file__": source_path, "__name__": "wirecloud.settings"}
    exec(compile(source, source_path, "exec"), g, g)
    return g, fake_sys


def test_settings_imports_external_settings_directly(monkeypatch):
    fake_settings_module = types.ModuleType("settings")
    fake_settings_module.MY_SETTING = 1

    def _import_impl(name, globals, locals, fromlist, level, original_import):
        if name == "settings":
            return fake_settings_module
        return original_import(name, globals, locals, fromlist, level)

    g, fake_sys = _load_settings_bootstrap(monkeypatch, _import_impl)
    assert g["MY_SETTING"] == 1
    assert fake_sys.path == []


def test_settings_imports_after_path_insertion(monkeypatch):
    fake_settings_module = types.ModuleType("settings")
    fake_settings_module.MY_SETTING = 2
    calls = {"settings_imports": 0}

    def _import_impl(name, globals, locals, fromlist, level, original_import):
        if name == "settings":
            calls["settings_imports"] += 1
            if calls["settings_imports"] == 1:
                raise ImportError("settings not found")
            return fake_settings_module
        return original_import(name, globals, locals, fromlist, level)

    g, fake_sys = _load_settings_bootstrap(monkeypatch, _import_impl)
    assert g["MY_SETTING"] == 2
    assert calls["settings_imports"] == 2

    expected_root = str(Path(imported_settings.__file__).parent.parent.resolve())
    assert fake_sys.path[0] == expected_root
