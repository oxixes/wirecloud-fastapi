# -*- coding: utf-8 -*-

from wirecloud.catalogue.models import XHTML


async def test_xhtml_get_cache_key_sets_and_reuses_version(monkeypatch):
    state = {"version": None}

    async def _get(key):
        return state["version"]

    async def _set(key, value):
        state["version"] = value

    monkeypatch.setattr("wirecloud.catalogue.models.cache.get", _get)
    monkeypatch.setattr("wirecloud.catalogue.models.cache.set", _set)

    xhtml = XHTML(uri="u", url="x", content_type="text/html", use_platform_style=True, cacheable=True)

    key1 = await xhtml.get_cache_key("rid", "example.org", "classic", "default")
    assert "_widget_xhtml/" in key1
    assert "/example.org/rid?mode=classic&theme=default" in key1

    current_version = state["version"]
    key2 = await xhtml.get_cache_key("rid", "example.org", "classic", "default")
    assert state["version"] == current_version
    assert key2 == key1
