# -*- coding: utf-8 -*-

from types import SimpleNamespace

import pytest
from fastapi import Request

from wirecloud import translation


def _request_with_lang(lang="en"):
    req = Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "server": ("testserver", 80),
            "path": "/",
            "query_string": b"",
            "headers": [],
        }
    )
    req.state.lang = lang
    return req


def test_generate_translations(monkeypatch, tmp_path):
    plugin_root = tmp_path / "wirecloud" / "wirecloud" / "commons"
    locale = plugin_root / "locale"
    locale.mkdir(parents=True)

    monkeypatch.setattr(translation.settings, "INSTALLED_APPS", ["wirecloud.commons"], raising=False)
    monkeypatch.setattr(translation.settings, "LANGUAGES", [("es", "Spanish")], raising=False)
    monkeypatch.setattr(translation.os.path, "dirname", lambda *_args, **_kwargs: str(tmp_path / "wirecloud"))
    monkeypatch.setattr(translation.gt, "translation", lambda *_args, **_kwargs: SimpleNamespace(gettext=lambda text: f"tr:{text}"))

    translation.translations = {}
    translation.generate_translations()
    assert ("wirecloud.commons", "es") in translation.translations

    monkeypatch.setattr(translation.settings, "INSTALLED_APPS", ["wirecloud.missing"], raising=False)
    translation.translations = {}
    translation.generate_translations()
    assert translation.translations == {}

    monkeypatch.setattr(translation.gt, "translation", lambda *_args, **_kwargs: (_ for _ in ()).throw(FileNotFoundError()))
    translation.translations = {}
    translation.generate_translations()
    assert translation.translations == {}

    monkeypatch.setattr(translation.os.path, "exists", lambda *_args, **_kwargs: False)
    monkeypatch.setattr(translation.os.path, "isdir", lambda *_args, **_kwargs: False)
    translation.translations = {}
    translation.generate_translations()
    assert translation.translations == {}


def test_find_request_language_and_gettext_paths(monkeypatch, tmp_path):
    req = _request_with_lang("es")
    fake_frame_a = SimpleNamespace(frame=SimpleNamespace(f_locals={"x": 1}))
    fake_frame_b = SimpleNamespace(frame=SimpleNamespace(f_locals={"request": req}))
    monkeypatch.setattr(translation.inspect, "stack", lambda: [fake_frame_a, fake_frame_b])
    assert translation.find_request_language() == "es"

    monkeypatch.setattr(translation.inspect, "stack", lambda: [])
    assert translation.find_request_language() is None

    with pytest.raises(ValueError, match="request language"):
        translation.gettext("hello", lang=None, translation=None)

    assert translation.gettext("hello", lang="en", translation=None) == "hello"
    assert translation.gettext("hello", lang="en-GB", translation=None) == "hello"

    monkeypatch.setattr(translation.settings, "INSTALLED_APPS", ["wirecloud.commons"], raising=False)
    caller_frame = SimpleNamespace(frame=SimpleNamespace(f_globals={"__name__": "other.module"}))
    monkeypatch.setattr(translation.inspect, "stack", lambda: [None, caller_frame])
    with pytest.raises(ValueError, match="plugin name"):
        translation.gettext("hello", lang="es", translation=None)

    caller_frame_ok = SimpleNamespace(frame=SimpleNamespace(f_globals={"__name__": "wirecloud.commons.foo"}))
    monkeypatch.setattr(translation.inspect, "stack", lambda: [None, caller_frame_ok])
    monkeypatch.setattr(translation.os.path, "dirname", lambda *_args, **_kwargs: str(tmp_path))
    monkeypatch.setattr(translation.os.path, "exists", lambda *_args, **_kwargs: False)
    with pytest.raises(ValueError, match="Could not find the locale directory"):
        translation.gettext("hello", lang="es", translation=None)

    monkeypatch.setattr(translation.os.path, "exists", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(translation.os.path, "isdir", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(translation.logger, "warning", lambda *_args, **_kwargs: None)
    translation.translations = {}
    assert translation.gettext("hello", lang="es", translation=None) == "hello"

    translation.translations = {("wirecloud.commons", "es"): SimpleNamespace(gettext=lambda text: f"cached:{text}")}
    assert translation.gettext("hello", lang="es", translation=None) == "cached:hello"

    assert translation.gettext("hello", lang="es", translation=SimpleNamespace(gettext=lambda text: f"tr:{text}")) == "tr:hello"


def test_gettext_lazy(monkeypatch):
    monkeypatch.setattr(translation, "gettext", lambda text, lang=None, translation=None: f"{lang}:{text}")
    lazy = translation.gettext_lazy("hello")
    assert lazy(lang="es") == "es:hello"
