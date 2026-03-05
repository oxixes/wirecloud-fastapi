# -*- coding: utf-8 -*-

from datetime import datetime, timezone
from types import SimpleNamespace

from wirecloud.catalogue import schemas
from wirecloud.catalogue.schemas import CatalogueResource, CatalogueResourceType
from wirecloud.commons.auth.schemas import Permission
from wirecloud.database import Id


def _macd_widget_dict(name="widget"):
    return {
        "type": "widget",
        "macversion": 1,
        "name": name,
        "vendor": "acme",
        "version": "1.0.0",
        "title": "Title",
        "description": "Desc",
        "contents": {"src": "index.html"},
        "widget_width": "4",
        "widget_height": "3",
        "wiring": {"inputs": [], "outputs": []},
    }


def _resource(users=None, groups=None, public=True):
    return CatalogueResource(
        _id=Id("507f1f77bcf86cd799439011"),
        vendor="acme",
        short_name="widget",
        version="1.0.0",
        type=CatalogueResourceType.widget,
        public=public,
        creation_date=datetime.now(timezone.utc),
        template_uri="widget.wgt",
        popularity=0,
        description=_macd_widget_dict(),
        users=users or [],
        groups=groups or [],
    )


def _user(uid="507f1f77bcf86cd799439012", perms=(), groups=None, superuser=False):
    group_ids = groups or []
    permissions = [Permission(codename=p) for p in perms]

    class _User:
        def __init__(self):
            self.id = Id(uid)
            self.username = "user"
            self.is_superuser = superuser
            self.groups = group_ids
            self.permissions = permissions

        def has_perm(self, codename):
            return any(p.codename == codename for p in self.permissions)

    return _User()


async def test_catalogue_resource_base_helpers_and_permissions(monkeypatch, db_session):
    r = _resource()
    assert r.local_uri_part == "acme/widget/1.0.0"
    assert r.resource_type() == "widget"
    assert r.mimetype == schemas.RESOURCE_MIMETYPES[0]
    assert str(r) == "acme/widget/1.0.0"

    superuser = _user(superuser=True)
    assert await r.is_removable_by(db_session, superuser, vendor=True) is True

    no_perm = _user(perms=())
    assert await r.is_removable_by(db_session, no_perm, vendor=True) is False

    monkeypatch.setattr("wirecloud.catalogue.utils.check_vendor_permissions", lambda *_args, **_kwargs: _async_true())
    with_perm = _user(perms=("COMPONENT.UNINSTALL",))
    assert await r.is_removable_by(db_session, with_perm, vendor=True) is True
    assert await r.is_removable_by(db_session, with_perm, vendor=False) is True


async def _async_true():
    return True


async def test_template_url_template_processed_info_and_global_function(monkeypatch):
    r = _resource()

    monkeypatch.setattr(schemas, "get_absolute_reverse_url", lambda *_args, **kwargs: "http://testserver/catalogue/media/acme/widget/1.0.0/widget.wgt")
    url = r.get_template_url(request=SimpleNamespace())
    assert "catalogue/media" in url

    monkeypatch.setattr(schemas, "TemplateParser", lambda *_args, **_kwargs: SimpleNamespace(get_resource_processed_info=lambda **__kwargs: "processed"))
    assert r.get_template(SimpleNamespace()) is not None
    assert r.get_processed_info(SimpleNamespace()) == "processed"

    abs_url = schemas.get_template_url("acme", "widget", "1.0.0", "http://external/x")
    rel_url = schemas.get_template_url("acme", "widget", "1.0.0", "file.js", request=SimpleNamespace())
    assert abs_url == "http://external/x"
    assert "catalogue/media" in rel_url


async def test_availability_installation_and_cache(monkeypatch):
    uid = "507f1f77bcf86cd799439012"
    gid = "507f1f77bcf86cd799439013"
    r = _resource(users=[uid], groups=[gid], public=False)

    assert r.is_available_for(None) is False
    assert r.is_available_for(_user(uid=uid)) is True
    assert r.is_available_for(_user(uid="507f1f77bcf86cd799439014", groups=[Id(gid)])) is True

    global_view = _user(perms=("COMPONENT.VIEW",))
    assert r.is_available_for(global_view) is True

    assert r.is_installed_for(None) is False
    assert r.is_installed_for(_user(uid=uid)) is True
    assert r.is_installed_for(_user(uid="507f1f77bcf86cd799439014", groups=[Id(gid)])) is True

    state = {"version": None}

    async def _get(_key):
        return state["version"]

    async def _set(_key, value):
        state["version"] = value

    monkeypatch.setattr(schemas, "cache", SimpleNamespace(get=_get, set=_set))

    v1 = await r.cache_version
    v2 = await r.cache_version
    assert v1 == v2


async def test_field_validator_objectid_conversion():
    oid = Id("507f1f77bcf86cd799439012")
    r = _resource(users=[oid], groups=[oid])
    assert isinstance(r.users[0], str)
    assert isinstance(r.groups[0], str)


async def test_availability_public_resource_short_circuit():
    r = _resource(public=True)
    assert r.is_available_for(_user()) is True


async def test_availability_false_when_not_public_and_no_membership():
    r = _resource(public=False, users=["507f1f77bcf86cd799439099"], groups=["507f1f77bcf86cd799439098"])
    assert r.is_available_for(_user(uid="507f1f77bcf86cd799439012", groups=[Id("507f1f77bcf86cd799439097")])) is False
