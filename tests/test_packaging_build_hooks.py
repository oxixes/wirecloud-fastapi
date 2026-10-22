import gettext
import importlib.util
import json
import os
import runpy
import subprocess
import sys
import types
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SETUP_PATH = PROJECT_ROOT / "setup.py"
WEBPACK_SETTINGS_SCRIPT = PROJECT_ROOT / "src" / "generate_webpack_settings.py"


def _load_setup_module(monkeypatch):
    captured = {}

    def fake_setup(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return kwargs

    monkeypatch.setattr("setuptools.setup", fake_setup)

    spec = importlib.util.spec_from_file_location("wirecloud_setup_test", SETUP_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)

    return module, captured


class _FakeCommand:
    def __init__(self):
        self.messages = []

    def announce(self, message, level=2):
        self.messages.append((message, level))


def test_frontend_build_skip_branch(monkeypatch):
    module, _ = _load_setup_module(monkeypatch)
    module._NPM_BUILD_DONE = False

    fake = _FakeCommand()
    fake.__class__ = type("MixedCmd", (module._FrontendBuildMixin, _FakeCommand), {})

    monkeypatch.setenv("WIRECLOUD_SKIP_NPM_BUILD", "1")
    fake._run_frontend_build()

    assert module._NPM_BUILD_DONE is True
    assert any("Skipping frontend build" in msg for msg, _ in fake.messages)


def test_frontend_build_requires_npm(monkeypatch):
    module, _ = _load_setup_module(monkeypatch)
    module._NPM_BUILD_DONE = False

    fake = _FakeCommand()
    fake.__class__ = type("MixedCmd", (module._FrontendBuildMixin, _FakeCommand), {})

    monkeypatch.delenv("WIRECLOUD_SKIP_NPM_BUILD", raising=False)

    def missing_npm(*_args, **_kwargs):
        raise FileNotFoundError("npm")

    monkeypatch.setattr(module.subprocess, "check_call", missing_npm)

    with pytest.raises(RuntimeError, match="npm is required"):
        fake._run_frontend_build()


def test_frontend_build_runs_npm_once(monkeypatch):
    module, _ = _load_setup_module(monkeypatch)
    module._NPM_BUILD_DONE = False

    fake = _FakeCommand()
    fake.__class__ = type("MixedCmd", (module._FrontendBuildMixin, _FakeCommand), {})

    calls = []

    monkeypatch.delenv("WIRECLOUD_SKIP_NPM_BUILD", raising=False)

    def fake_check_call(cmd, cwd, env):
        calls.append((cmd, cwd, env.get("WIRECLOUD_SKIP_NPM_BUILD")))

    monkeypatch.setattr(module.subprocess, "check_call", fake_check_call)

    fake._run_frontend_build()
    fake._run_frontend_build()

    assert len(calls) == 1
    expected_npm = "npm.cmd" if os.name == "nt" else "npm"
    assert calls[0][0] == [expected_npm, "run", "build"]
    assert calls[0][1] == str(PROJECT_ROOT)


def test_frontend_build_propagates_npm_failure(monkeypatch):
    module, _ = _load_setup_module(monkeypatch)
    module._NPM_BUILD_DONE = False

    fake = _FakeCommand()
    fake.__class__ = type("MixedCmd", (module._FrontendBuildMixin, _FakeCommand), {})

    monkeypatch.delenv("WIRECLOUD_SKIP_NPM_BUILD", raising=False)

    def failing_check_call(*_args, **_kwargs):
        raise subprocess.CalledProcessError(returncode=7, cmd=["npm", "run", "build"])

    monkeypatch.setattr(module.subprocess, "check_call", failing_check_call)

    with pytest.raises(RuntimeError, match="npm run build failed with exit code 7"):
        fake._run_frontend_build()


def test_setup_registers_command_classes(monkeypatch):
    module, captured = _load_setup_module(monkeypatch)

    assert "cmdclass" in captured["kwargs"]
    assert captured["kwargs"]["cmdclass"]["build_py"] is module.build_py
    assert captured["kwargs"]["cmdclass"]["sdist"] is module.sdist


def test_build_py_and_sdist_run_call_frontend_and_super(monkeypatch):
    module, _ = _load_setup_module(monkeypatch)
    from setuptools import Distribution

    build_py_calls = []
    sdist_calls = []

    monkeypatch.setattr(module.build_py, "_run_frontend_build", lambda self: build_py_calls.append("frontend"))
    monkeypatch.setattr(module._build_py, "run", lambda self: build_py_calls.append("super"))
    monkeypatch.setattr(module.build_py, "_compile_translations", lambda self: build_py_calls.append("translations"))

    cmd = module.build_py(Distribution())
    cmd.run()
    assert build_py_calls == ["frontend", "super", "translations"]

    monkeypatch.setattr(module.sdist, "_run_frontend_build", lambda self: sdist_calls.append("frontend"))
    monkeypatch.setattr(module._sdist, "run", lambda self: sdist_calls.append("super"))

    cmd = module.sdist(Distribution())
    cmd.run()
    assert sdist_calls == ["frontend", "super"]


def test_build_py_compiles_all_catalogs_into_build_tree(monkeypatch, tmp_path):
    from babel.messages.pofile import read_po
    from setuptools import Distribution

    module, _ = _load_setup_module(monkeypatch)
    cmd = module.build_py(Distribution())
    cmd.build_lib = str(tmp_path)
    cmd._compile_translations()

    source = PROJECT_ROOT / "src"
    catalogs = sorted(source.glob("**/locale/*/LC_MESSAGES/*.po"))
    assert catalogs
    assert len(list(tmp_path.rglob("*.mo"))) == len(catalogs)
    for po_file in catalogs:
        mo_file = (tmp_path / po_file.relative_to(source)).with_suffix(".mo")
        with mo_file.open("rb") as stream:
            compiled = gettext.GNUTranslations(stream)
        with po_file.open("rb") as stream:
            catalog = read_po(stream, locale=po_file.parent.parent.name)
        for message in catalog:
            if message.id and isinstance(message.id, str) and message.string and not message.fuzzy:
                assert compiled.gettext(message.id) == message.string


def test_compiler_rejects_invalid_placeholders(tmp_path):
    compiler = runpy.run_path(str(PROJECT_ROOT / "src" / "wirecloud" / "commons" / "utils" / "translation.py"))
    source = tmp_path / "source"
    po_file = source / "plugin" / "locale" / "es" / "LC_MESSAGES" / "plugin.po"
    po_file.parent.mkdir(parents=True)
    po_file.write_text(
        'msgid ""\nmsgstr ""\n"Content-Type: text/plain; charset=UTF-8\\n"\n\n'
        '#, python-format\nmsgid "Hello %(name)s"\nmsgstr "Hola %(other)s"\n',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Invalid catalog"):
        compiler["compile_catalog"](po_file, tmp_path / "output" / "plugin.mo")
    assert not list(tmp_path.rglob("*.mo"))


def test_generate_webpack_settings_with_settings_module(monkeypatch, tmp_path):
    out_file = tmp_path / "webpack_settings.json"

    called = {"validated": False}

    fake_validator = types.ModuleType("wirecloud.settings_validator")

    async def fake_validate_settings(_offline):
        called["validated"] = True

    fake_validator.validate_settings = fake_validate_settings
    monkeypatch.setitem(sys.modules, "wirecloud.settings_validator", fake_validator)

    fake_src = types.ModuleType("src")
    fake_src_settings = types.ModuleType("src.settings")
    fake_src_settings.INSTALLED_APPS = [
        "wirecloud.commons",
        "wirecloud.commons",
        "wirecloud.platform",
    ]
    fake_src.settings = fake_src_settings

    monkeypatch.setitem(sys.modules, "src", fake_src)
    monkeypatch.setitem(sys.modules, "src.settings", fake_src_settings)

    monkeypatch.setenv("WEBPACK_SETTINGS_JSON", str(out_file))

    runpy.run_path(str(WEBPACK_SETTINGS_SCRIPT), run_name="__main__")

    assert called["validated"] is True
    payload = json.loads(out_file.read_text(encoding="utf-8"))

    assert "installedApps" in payload
    assert [item["name"] for item in payload["installedApps"]] == ["commons", "platform"]
    assert all(item["module"].startswith("wirecloud.") for item in payload["installedApps"])


def test_generate_webpack_settings_fallback_paths(monkeypatch, tmp_path):
    out_file = tmp_path / "webpack_settings_fallback.json"

    fake_validator = types.ModuleType("wirecloud.settings_validator")
    monkeypatch.setitem(sys.modules, "wirecloud.settings_validator", fake_validator)

    original_import = __import__

    def raising_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name in {"src", "settings"}:
            raise ImportError(name)
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr("builtins.__import__", raising_import)
    monkeypatch.setenv("WEBPACK_SETTINGS_JSON", str(out_file))

    runpy.run_path(str(WEBPACK_SETTINGS_SCRIPT), run_name="__main__")

    payload = json.loads(out_file.read_text(encoding="utf-8"))

    expected_names = ["commons", "platform", "catalogue", "proxy", "fiware", "keycloak"]
    assert [item["name"] for item in payload["installedApps"]] == expected_names
    assert all(Path(item["path"]).exists() for item in payload["installedApps"] if item["path"] is not None)


def test_generate_webpack_settings_edge_branches(monkeypatch, tmp_path):
    out_file_name = "edge_settings.json"

    fake_validator = types.ModuleType("wirecloud.settings_validator")

    async def fake_validate_settings(_offline):
        return None

    fake_validator.validate_settings = fake_validate_settings
    monkeypatch.setitem(sys.modules, "wirecloud.settings_validator", fake_validator)

    fake_src = types.ModuleType("src")
    fake_src_settings = types.ModuleType("src.settings")
    fake_src_settings.INSTALLED_APPS = [
        123,  # non-string branch
        "wirecloud.commons",
        "wirecloud.platform",
        "wirecloud.catalogue",
        "wirecloud.notfound",
        "wirecloud.nopath",
    ]
    fake_src.settings = fake_src_settings
    monkeypatch.setitem(sys.modules, "src", fake_src)
    monkeypatch.setitem(sys.modules, "src.settings", fake_src_settings)

    import importlib

    real_import_module = importlib.import_module

    def fake_import_module(name):
        if name == "wirecloud.platform":
            raise ImportError("forced platform import error")
        if name == "wirecloud.catalogue":
            mod = types.ModuleType(name)
            mod.__file__ = str(tmp_path / "catalogue_mod.py")
            return mod
        if name == "wirecloud.notfound":
            raise ImportError("forced missing package")
        if name == "wirecloud.nopath":
            return types.ModuleType(name)
        return real_import_module(name)

    monkeypatch.setattr(importlib, "import_module", fake_import_module)

    import os.path as ospath

    real_abspath = ospath.abspath

    def fake_abspath(value):
        if str(value).endswith("wirecloud/commons"):
            raise RuntimeError("forced abspath error")
        return real_abspath(value)

    monkeypatch.setattr(ospath, "abspath", fake_abspath)

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("WEBPACK_SETTINGS_JSON", out_file_name)

    runpy.run_path(str(WEBPACK_SETTINGS_SCRIPT), run_name="__main__")

    payload = json.loads((tmp_path / out_file_name).read_text(encoding="utf-8"))
    assert [item["name"] for item in payload["installedApps"]] == [
        "commons",
        "platform",
        "catalogue",
        "notfound",
        "nopath",
    ]
    assert payload["installedApps"][0]["path"] is not None
    assert payload["installedApps"][1]["path"].endswith("src/wirecloud/platform")
    assert payload["installedApps"][2]["path"] == str(tmp_path)
    assert payload["installedApps"][3]["path"] is None
    assert payload["installedApps"][4]["path"] is None
