# -*- coding: utf-8 -*-

from types import SimpleNamespace

import pytest

from wirecloud.commons.utils.http import PermissionDenied
from wirecloud.platform.localcatalogue import utils


class _Wgt:
    def __init__(self, template=None):
        self._template = template or '{"version":"1.0.0"}'
        self.updated = None

    def get_underlying_file(self):
        return b"zip-bytes"

    def get_template(self):
        return self._template

    def update_config(self, template_string):
        self.updated = template_string


async def test_install_resource_branches(monkeypatch, db_session):
    with pytest.raises(TypeError):
        await utils.install_resource(db_session, object(), None)
    monkeypatch.setattr(utils, "WgtFile", _Wgt)

    user = SimpleNamespace(username="alice")
    template = SimpleNamespace(get_resource_version=lambda: "1.0.0-dev", get_resource_vendor=lambda: "acme", get_resource_name=lambda: "x")
    monkeypatch.setattr(utils, "TemplateParser", lambda _template_contents: template)
    with pytest.raises(PermissionDenied, match="dev versions cannot be published"):
        await utils.install_resource(db_session, _Wgt(), user, restricted=True)

    template = SimpleNamespace(get_resource_version=lambda: "1.0.0", get_resource_vendor=lambda: "acme", get_resource_name=lambda: "x")
    monkeypatch.setattr(utils, "TemplateParser", lambda _template_contents: template)
    monkeypatch.setattr(utils, "check_vendor_permissions", lambda *_args, **_kwargs: _false())

    async def _false():
        return False

    with pytest.raises(PermissionDenied, match="publish in name of acme"):
        await utils.install_resource(db_session, _Wgt(), user, restricted=True)

    monkeypatch.setattr(utils, "check_vendor_permissions", lambda *_args, **_kwargs: _true())

    async def _true():
        return True

    created = SimpleNamespace(id="rid", vendor="acme", short_name="x", version="1.0.0")

    async def _none_resource(*_args, **_kwargs):
        return None

    async def _add(*_args, **_kwargs):
        return created

    monkeypatch.setattr(utils, "get_catalogue_resource", _none_resource)
    monkeypatch.setattr(utils, "add_packaged_resource", _add)
    restricted_ok = await utils.install_resource(db_session, _Wgt(), user, restricted=True)
    assert restricted_ok.id == "rid"
    added = await utils.install_resource(db_session, _Wgt(), user, restricted=False)
    assert added.id == "rid"

    existing = SimpleNamespace(id="rid2", vendor="acme", short_name="x", version="1.0.0-dev")
    deleted = {"n": 0}
    committed = {"n": 0}

    async def _existing(*_args, **_kwargs):
        return existing

    async def _delete(*_args, **_kwargs):
        deleted["n"] += 1

    async def _commit(*_args, **_kwargs):
        committed["n"] += 1

    monkeypatch.setattr(utils, "TemplateParser", lambda _template_contents: SimpleNamespace(
        get_resource_version=lambda: "1.0.0-devalice",
        get_resource_vendor=lambda: "acme",
        get_resource_name=lambda: "x",
    ))
    monkeypatch.setattr(utils, "get_catalogue_resource", _existing)
    monkeypatch.setattr(utils, "delete_catalogue_resources", _delete)
    monkeypatch.setattr(utils, "commit", _commit)
    overwritten = await utils.install_resource(db_session, _Wgt(), user, restricted=False)
    assert overwritten.id == "rid"
    assert deleted["n"] == 1
    assert committed["n"] == 1

    monkeypatch.setattr(utils, "TemplateParser", lambda _template_contents: SimpleNamespace(
        get_resource_version=lambda: "1.0.0",
        get_resource_vendor=lambda: "acme",
        get_resource_name=lambda: "x",
    ))
    kept = await utils.install_resource(db_session, _Wgt(), user, restricted=False)
    assert kept.id == "rid2"


async def test_install_component_branches(monkeypatch, db_session):
    monkeypatch.setattr(utils, "WgtFile", _Wgt)
    executor = SimpleNamespace(id="u1")
    user_a = SimpleNamespace(id="u2")
    group_a = SimpleNamespace(id="g1")

    resource_initial = SimpleNamespace(
        id="rid",
        vendor="acme",
        short_name="x",
        version="1.0.0",
        public=False,
        is_installed_for=lambda user: False,
    )
    resource_final = SimpleNamespace(
        id="rid",
        vendor="acme",
        short_name="x",
        version="1.0.0",
        public=True,
        is_installed_for=lambda user: True,
    )

    async def _install_resource(*_args, **_kwargs):
        return resource_initial

    async def _change_publicity(*_args, **_kwargs):
        return None

    async def _install_user(*_args, **_kwargs):
        return True

    async def _install_group(*_args, **_kwargs):
        return False

    async def _get_resource(*_args, **_kwargs):
        return resource_final

    async def _create_widget(*_args, **_kwargs):
        return None

    monkeypatch.setattr(utils, "install_resource", _install_resource)
    monkeypatch.setattr(utils, "change_resource_publicity", _change_publicity)
    monkeypatch.setattr(utils, "install_resource_to_user", _install_user)
    monkeypatch.setattr(utils, "install_resource_to_group", _install_group)
    monkeypatch.setattr(utils, "get_catalogue_resource", _get_resource)
    monkeypatch.setattr(utils.catalogue_utils, "create_widget_on_resource_creation", _create_widget)
    monkeypatch.setattr(utils.catalogue_utils, "deploy_operators_on_resource_creation", lambda *_args, **_kwargs: None)

    added, resource = await utils.install_component(
        db_session,
        _Wgt(),
        executor_user=executor,
        public=True,
        users=[user_a],
        groups=[group_a],
    )
    assert added is True
    assert resource.public is True

    installed_to_someone = SimpleNamespace(
        id="rid2",
        vendor="acme",
        short_name="x",
        version="2.0.0",
        public=False,
        is_installed_for=lambda user: False,
    )

    async def _install_resource2(*_args, **_kwargs):
        return installed_to_someone

    monkeypatch.setattr(utils, "install_resource", _install_resource2)
    monkeypatch.setattr(utils, "install_resource_to_user", lambda *_args, **_kwargs: _false())
    monkeypatch.setattr(utils, "install_resource_to_group", lambda *_args, **_kwargs: _true())

    async def _false():
        return False

    async def _true():
        return True

    changed, _ = await utils.install_component(db_session, _Wgt(), executor_user=None, public=False, users=[], groups=[group_a])
    assert changed is True

    monkeypatch.setattr(utils, "install_resource_to_user", lambda *_args, **_kwargs: _true())
    changed_user, _ = await utils.install_component(db_session, _Wgt(), executor_user=None, public=False, users=[user_a], groups=[])
    assert changed_user is True


def test_fix_dev_version(monkeypatch):
    dev_resource_info = SimpleNamespace(version="1.2.3-dev")
    non_dev_resource_info = SimpleNamespace(version="1.2.3")
    parser = SimpleNamespace(get_resource_info=lambda: dev_resource_info)
    monkeypatch.setattr(utils, "TemplateParser", lambda _template_contents: parser)
    monkeypatch.setattr(utils, "write_json_description", lambda resource_info: f'{{"version":"{resource_info.version}"}}')

    wgt = _Wgt()
    utils.fix_dev_version(wgt, SimpleNamespace(username="alice"))
    assert "devalice" in wgt.updated

    parser2 = SimpleNamespace(get_resource_info=lambda: non_dev_resource_info)
    monkeypatch.setattr(utils, "TemplateParser", lambda _template_contents: parser2)
    wgt2 = _Wgt()
    utils.fix_dev_version(wgt2, SimpleNamespace(username="alice"))
    assert wgt2.updated is None
