# -*- coding: utf-8 -*-

import sys
from types import SimpleNamespace

import pytest

sys.modules.setdefault("wirecloud.catalogue.search", SimpleNamespace(add_resource_to_index=None))

from wirecloud.platform.core.catalogue_manager import WirecloudCatalogueManager


async def test_publish_local_success(monkeypatch, db_session):
    manager = WirecloudCatalogueManager("wirecloud", "local", options=SimpleNamespace())
    resource = SimpleNamespace(local_uri_part="acme/widget/1.0.0")
    calls = {}

    async def _install(_db, _wgt, users):
        calls["install"] = users
        return True, resource

    async def _index(_db, _resource):
        calls["index"] = _resource

    monkeypatch.setattr("wirecloud.platform.core.catalogue_manager.install_component", _install)
    monkeypatch.setattr("wirecloud.platform.core.catalogue_manager.add_resource_to_index", _index)
    out = await manager.publish(db_session, None, "wgt-file", user=SimpleNamespace(username="u"))
    assert out is resource
    assert len(calls["install"]) == 1
    assert calls["index"] is resource


async def test_publish_local_existing_and_non_local(monkeypatch, db_session):
    manager = WirecloudCatalogueManager("wirecloud", "local", options=SimpleNamespace())
    existing_resource = SimpleNamespace(local_uri_part="acme/widget/1.0.0")
    monkeypatch.setattr("wirecloud.platform.core.catalogue_manager._", lambda text: text)

    async def _install_exists(_db, _wgt, users):
        return False, existing_resource

    monkeypatch.setattr("wirecloud.platform.core.catalogue_manager.install_component", _install_exists)
    with pytest.raises(Exception, match="Resource already exists"):
        await manager.publish(db_session, None, "wgt-file", user=SimpleNamespace(username="u"))

    remote_manager = WirecloudCatalogueManager("wirecloud", "remote", options=SimpleNamespace())
    with pytest.raises(Exception, match="TODO"):
        await remote_manager.publish(db_session, None, "wgt-file", user=SimpleNamespace(username="u"))
