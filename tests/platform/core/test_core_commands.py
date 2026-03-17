# -*- coding: utf-8 -*-

import argparse
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from wirecloud.platform.core import commands


async def test_runserver_cmd_success_and_keyboard_interrupt(monkeypatch):
    calls = {}

    class _Config:
        def __init__(self, **kwargs):
            calls["config"] = kwargs

    class _Server:
        def __init__(self, config):
            self.config = config

        async def serve(self):
            calls["served"] = True

    monkeypatch.setitem(sys.modules, "uvicorn", SimpleNamespace(Config=_Config, Server=_Server))
    monkeypatch.setitem(sys.modules, "wirecloud.main", SimpleNamespace(app="APP"))
    args = SimpleNamespace(host="127.0.0.1", port=9000, reload=True, workers=2, debug=True)
    await commands.runserver_cmd(args)
    assert calls["config"]["app"] == "APP"
    assert calls["config"]["host"] == "127.0.0.1"
    assert calls["served"] is True

    class _ServerInterrupt(_Server):
        async def serve(self):
            raise KeyboardInterrupt()

    monkeypatch.setitem(sys.modules, "uvicorn", SimpleNamespace(Config=_Config, Server=_ServerInterrupt))
    await commands.runserver_cmd(args)


async def test_runserver_cmd_import_error(monkeypatch):
    monkeypatch.setitem(sys.modules, "uvicorn", SimpleNamespace(Config=lambda **kwargs: kwargs, Server=lambda _config: SimpleNamespace(serve=lambda: None)))
    monkeypatch.setitem(sys.modules, "wirecloud.main", SimpleNamespace())
    with pytest.raises(Exception):
        await commands.runserver_cmd(SimpleNamespace(host="h", port=1, reload=False, workers=1, debug=False))


def test_get_modules_to_process(tmp_path):
    wirecloud_path = tmp_path / "wirecloud"
    (wirecloud_path / "platform").mkdir(parents=True)
    (wirecloud_path / "themes" / "theme1").mkdir(parents=True)
    (wirecloud_path / "themes" / "_hidden").mkdir(parents=True)
    (wirecloud_path / "themes" / "__pycache__").mkdir(parents=True)

    settings = SimpleNamespace(INSTALLED_APPS=["wirecloud.platform", "wirecloud.missing"])
    modules = commands._get_modules_to_process(wirecloud_path, settings)
    names = [m["name"] for m in modules]
    assert "wirecloud.platform" in names
    assert "wirecloud.themes.theme1" in names
    assert "wirecloud.themes._hidden" not in names
    assert "wirecloud.themes.__pycache__" not in names


def test_get_modules_to_process_without_themes(tmp_path):
    wirecloud_path = tmp_path / "wirecloud"
    (wirecloud_path / "platform").mkdir(parents=True)
    settings = SimpleNamespace(INSTALLED_APPS=["wirecloud.platform"])
    modules = commands._get_modules_to_process(wirecloud_path, settings)
    assert modules == [{"name": "wirecloud.platform", "path": wirecloud_path / "platform", "domain": "wirecloud.platform"}]


def test_extract_messages_and_error(monkeypatch, tmp_path, capsys):
    def _extract_ok(dirname, method_map, keywords, comment_tags):
        yield ("a.py", 1, "hello", [], None)
        yield ("b.py", 2, "", [], None)
        yield ("c.py", 3, ("world", "worlds"), [], None)

    monkeypatch.setattr("babel.messages.extract.extract_from_dir", _extract_ok)
    messages = commands._extract_messages(tmp_path, [], {}, "Python")
    assert "hello" in messages
    assert "world" in messages
    assert "" not in messages

    def _extract_fail(**_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr("babel.messages.extract.extract_from_dir", _extract_fail)
    commands._extract_messages(tmp_path, [], {}, "Python")
    assert "Warning: Error extracting messages" in capsys.readouterr().out


def test_extract_messages_skips_and_duplicate_locations(monkeypatch, tmp_path):
    def _extract(dirname, method_map, keywords, comment_tags):
        yield ("a.py", 1, ("", "x"), [], None)
        yield ("a.py", 2, "same", [], None)
        yield ("b.py", 3, "same", [], None)

    monkeypatch.setattr("babel.messages.extract.extract_from_dir", _extract)
    out = commands._extract_messages(tmp_path, [], {}, "Python")
    assert "" not in out
    assert len(out["same"]) == 2
    assert out["same"][0][0].endswith("a.py")
    assert out["same"][1][0].endswith("b.py")


def test_process_po_file_create_and_update(tmp_path):
    po_file = tmp_path / "x.po"
    extracted = {"hello": [("a.py", 1)], "world": [("b.py", 2)]}
    commands._process_po_file(po_file, extracted, "es", "wirecloud.platform")
    assert po_file.exists()

    extracted2 = {"hello": [("a.py", 10)], "new": [("c.py", 3)]}
    commands._process_po_file(po_file, extracted2, "es", "wirecloud.platform")
    assert po_file.exists()
    assert "new" in po_file.read_text(encoding="utf-8")


def test_process_po_file_fallback_read_and_write_error(monkeypatch, tmp_path, capsys):
    po_file = tmp_path / "broken.po"
    po_file.write_bytes(b"not-a-po")
    monkeypatch.setattr("babel.messages.pofile.read_po", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("read boom")))
    commands._process_po_file(po_file, {"k": [("a.py", 1)]}, "es", "wirecloud.platform")
    assert po_file.exists()

    def _write_po_fail(*_args, **_kwargs):
        raise RuntimeError("write boom")

    monkeypatch.setattr("babel.messages.pofile.write_po", _write_po_fail)
    commands._process_po_file(po_file, {"k2": [("b.py", 2)]}, "es", "wirecloud.platform")
    assert "Error writing file" in capsys.readouterr().out


def test_gentranslations_and_compiletranslations(monkeypatch, tmp_path):
    module_path = tmp_path / "wirecloud" / "platform"
    module_path.mkdir(parents=True)
    locale_dir = module_path / "locale" / "es" / "LC_MESSAGES"
    locale_dir.mkdir(parents=True)
    po_file = locale_dir / "platform.po"
    po_file.write_text('msgid ""\nmsgstr ""\n\nmsgid "hello"\nmsgstr "hola"\n', encoding="utf-8")

    fake_settings = SimpleNamespace(LANGUAGES=[("es", "Spanish")], INSTALLED_APPS=["wirecloud.platform"])
    monkeypatch.setitem(sys.modules, "src.settings", fake_settings)

    monkeypatch.setattr(commands, "_get_modules_to_process", lambda _wirecloud_path, _settings: [{"name": "wirecloud.platform", "path": module_path, "domain": "platform"}])
    monkeypatch.setattr(commands, "_extract_messages", lambda *_args, **_kwargs: {"hello": [("a.py", 1)]})

    processed = []
    monkeypatch.setattr(commands, "_process_po_file", lambda path, extracted, lang, domain: processed.append((Path(path).name, lang, domain, len(extracted))))
    commands.gentranslations_cmd(SimpleNamespace(language=None))
    assert processed

    commands.compiletranslations_cmd(SimpleNamespace(language=None, verbose=False))
    assert (locale_dir / "platform.mo").exists()


def test_gentranslations_specific_language_and_skip_paths(monkeypatch, tmp_path, capsys):
    module_path = tmp_path / "wirecloud" / "platform"
    module_path.mkdir(parents=True)

    fake_settings = SimpleNamespace(LANGUAGES=[("en", "English"), ("es", "Spanish")], INSTALLED_APPS=["wirecloud.platform"])
    monkeypatch.setitem(sys.modules, "src.settings", fake_settings)
    monkeypatch.setattr(commands, "_get_modules_to_process", lambda _wirecloud_path, _settings: [{"name": "wirecloud.platform", "path": module_path, "domain": "platform"}])

    monkeypatch.setattr(commands, "_extract_messages", lambda *_args, **_kwargs: {})
    commands.gentranslations_cmd(SimpleNamespace(language="fr"))
    out = capsys.readouterr().out
    assert "not in LANGUAGES setting" in out
    assert "No translatable messages found, skipping" in out

    processed = []

    def _extract_py_only(_module_path, _methods, _keywords, file_type):
        return {"hello": [("a.py", 1)]} if file_type == "Python" else {}

    monkeypatch.setattr(commands, "_extract_messages", _extract_py_only)
    monkeypatch.setattr(commands, "_process_po_file", lambda path, extracted, lang, domain: processed.append(Path(path).name))
    commands.gentranslations_cmd(SimpleNamespace(language=None))
    assert any(name.endswith(".po") for name in processed)

    processed.clear()

    def _extract_js_only(_module_path, _methods, _keywords, file_type):
        return {} if file_type == "Python" else {"hola": [("a.js", 1)]}

    monkeypatch.setattr(commands, "_extract_messages", _extract_js_only)
    commands.gentranslations_cmd(SimpleNamespace(language=None))
    assert any(name.endswith(".js.po") for name in processed)
    assert all(name.endswith(".js.po") for name in processed)

    monkeypatch.setattr(commands, "_extract_messages", _extract_py_only)
    commands.gentranslations_cmd(SimpleNamespace(language="es"))


def test_compiletranslations_language_specific_verbose_and_errors(monkeypatch, tmp_path, capsys):
    module_with_locale = tmp_path / "wirecloud" / "platform"
    module_without_locale = tmp_path / "wirecloud" / "no_locale"
    locale_dir = module_with_locale / "locale" / "zz" / "LC_MESSAGES"
    locale_dir.mkdir(parents=True)
    module_without_locale.mkdir(parents=True)
    ok_po = locale_dir / "ok.po"
    bad_po = locale_dir / "bad.po"
    ok_po.write_text('msgid ""\nmsgstr ""\n', encoding="utf-8")
    bad_po.write_text('msgid ""\nmsgstr ""\n', encoding="utf-8")

    fake_settings = SimpleNamespace(LANGUAGES=[("es", "Spanish")], INSTALLED_APPS=["wirecloud.platform"])
    monkeypatch.setitem(sys.modules, "src.settings", fake_settings)
    monkeypatch.setattr(
        commands,
        "_get_modules_to_process",
        lambda _wirecloud_path, _settings: [
            {"name": "wirecloud.platform", "path": module_with_locale, "domain": "platform"},
            {"name": "wirecloud.no_locale", "path": module_without_locale, "domain": "no_locale"},
        ],
    )

    def _read_po(_f, locale):
        return object()

    def _write_mo(f, catalog):
        if f.name.endswith("bad.mo"):
            raise RuntimeError("compile boom")

    monkeypatch.setattr("babel.messages.pofile.read_po", _read_po)
    monkeypatch.setattr("babel.messages.mofile.write_mo", _write_mo)
    commands.compiletranslations_cmd(SimpleNamespace(language="zz", verbose=True))
    out = capsys.readouterr().out
    assert "Language: zz (zz)" in out
    assert "Error compiling" in out
    assert "Total errors: 1" in out
    assert (locale_dir / "ok.mo").exists()
    commands.compiletranslations_cmd(SimpleNamespace(language="es", verbose=True))


async def test_rebuildsearchindexes_and_populate(monkeypatch):
    class _Session:
        pass

    session = _Session()

    async def _get_session():
        yield session

    called = {"rebuild": 0, "populate": 0, "create_user_db": 0, "commit": 0}

    async def _rebuild_all_indexes(db):
        called["rebuild"] += 1
        assert db is session

    monkeypatch.setattr("wirecloud.database.get_session", _get_session)
    monkeypatch.setitem(sys.modules, "wirecloud.commons.search", SimpleNamespace(rebuild_all_indexes=_rebuild_all_indexes))
    await commands.rebuildsearchindexes_cmd(SimpleNamespace())
    assert called["rebuild"] == 1

    class _Plugin:
        async def populate(self, db, user):
            called["populate"] += 1
            assert db is session
            assert user is not None

    monkeypatch.setattr(commands, "get_plugins", lambda: [_Plugin()])

    user_calls = {"n": 0}

    async def _user_lookup(_db, _username):
        user_calls["n"] += 1
        if user_calls["n"] == 1:
            return None
        return SimpleNamespace(username="wirecloud")

    async def _create_user_db(_db, _data):
        called["create_user_db"] += 1

    async def _commit(_db):
        called["commit"] += 1

    monkeypatch.setattr("wirecloud.commons.auth.crud.get_user_with_all_info_by_username", _user_lookup)
    monkeypatch.setattr("wirecloud.commons.auth.crud.create_user_db", _create_user_db)
    monkeypatch.setattr("wirecloud.database.commit", _commit)
    await commands.populate_cmd(SimpleNamespace())
    assert called["create_user_db"] == 1
    assert called["commit"] == 1

    await commands.populate_cmd(SimpleNamespace())
    assert called["populate"] == 2


async def test_rebuild_and_populate_no_sessions_and_plugin_without_populate(monkeypatch):
    class _EmptySessionIter:
        def __aiter__(self):
            return self

        async def __anext__(self):
            raise StopAsyncIteration

    monkeypatch.setattr("wirecloud.database.get_session", lambda: _EmptySessionIter())
    monkeypatch.setitem(sys.modules, "wirecloud.commons.search", SimpleNamespace(rebuild_all_indexes=lambda _s: None))
    await commands.rebuildsearchindexes_cmd(SimpleNamespace())

    await commands.populate_cmd(SimpleNamespace())

    async def _one_session():
        yield object()

    monkeypatch.setattr("wirecloud.database.get_session", _one_session)
    monkeypatch.setattr("wirecloud.commons.auth.crud.get_user_with_all_info_by_username", lambda _db, _u: _user())

    async def _user():
        return SimpleNamespace(username="wirecloud")

    called = {"n": 0}

    class _NoPopulate:
        pass

    class _WithPopulate:
        async def populate(self, _db, _user):
            called["n"] += 1

    monkeypatch.setattr(commands, "get_plugins", lambda: [_NoPopulate(), _WithPopulate()])
    await commands.populate_cmd(SimpleNamespace())
    assert called["n"] == 1


async def test_rebuildsearchindexes_cmd_with_empty_async_generator(monkeypatch):
    async def _empty_gen():
        if False:
            yield None

    monkeypatch.setattr("wirecloud.database.get_session", _empty_gen)
    monkeypatch.setitem(sys.modules, "wirecloud.commons.search", SimpleNamespace(rebuild_all_indexes=lambda _s: None))
    await commands.rebuildsearchindexes_cmd(SimpleNamespace())


async def test_populate_cmd_with_empty_async_generator(monkeypatch):
    async def _empty_gen():
        if False:
            yield None

    monkeypatch.setattr("wirecloud.database.get_session", _empty_gen)
    await commands.populate_cmd(SimpleNamespace())


def test_setup_commands():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="cmd")
    mapping = commands.setup_commands(subparsers)
    assert set(mapping.keys()) == {
        "runserver",
        "gentranslations",
        "compiletranslations",
        "rebuildsearchindexes",
        "populate",
    }
