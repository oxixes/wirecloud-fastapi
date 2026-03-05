# -*- coding: utf-8 -*-

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from bson import ObjectId

from wirecloud.catalogue import crud
from wirecloud.catalogue.models import XHTML
from wirecloud.catalogue.schemas import CatalogueResourceCreate, CatalogueResourceType
from wirecloud.commons.auth.schemas import Permission, User, UserAll
from wirecloud.commons.utils.template.schemas.macdschemas import MACDWidget
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


def _user(uid=None):
    uid = uid or ObjectId()
    now = datetime.now(timezone.utc)
    return User(
        id=Id(str(uid)),
        username="u",
        email="u@example.com",
        first_name="U",
        last_name="Ser",
        is_superuser=False,
        is_staff=False,
        is_active=True,
        date_joined=now,
        last_login=None,
        idm_data={},
    )


def _user_all(uid=None, perms=()):
    uid = uid or ObjectId()
    now = datetime.now(timezone.utc)
    return UserAll(
        id=Id(str(uid)),
        username="u",
        email="u@example.com",
        first_name="U",
        last_name="Ser",
        is_superuser=False,
        is_staff=False,
        is_active=True,
        date_joined=now,
        last_login=None,
        idm_data={},
        groups=[],
        permissions=[Permission(codename=p) for p in perms],
    )


async def _insert_resource(db_session, *, vendor="acme", short_name="widget", version="1.0.0", public=True, users=None, groups=None, creator_id=None):
    rid = ObjectId()
    doc = {
        "_id": rid,
        "vendor": vendor,
        "short_name": short_name,
        "version": version,
        "type": 0,
        "public": public,
        "creation_date": datetime.now(timezone.utc),
        "template_uri": "widget.wgt",
        "popularity": 0,
        "description": _macd_widget_dict(short_name),
        "creator_id": creator_id,
        "users": users or [],
        "groups": groups or [],
    }
    await db_session.client.catalogue_resources.insert_one(doc)
    return rid


async def test_create_and_get_catalogue_resources(db_session, monkeypatch):
    commit_calls = {"n": 0}

    async def _commit(_db):
        commit_calls["n"] += 1

    monkeypatch.setattr(crud, "commit", _commit)

    creator = _user()
    create = CatalogueResourceCreate(
        vendor="acme",
        short_name="widget",
        version="1.0.0",
        type=CatalogueResourceType.widget,
        public=True,
        creation_date=datetime.now(timezone.utc),
        template_uri="widget.wgt",
        popularity=0,
        description=_macd_widget_dict(),
        creator=creator,
    )

    created = await crud.create_catalogue_resource(db_session, create)
    assert created.vendor == "acme"
    assert commit_calls["n"] == 1

    found = await crud.get_catalogue_resource(db_session, "acme", "widget", "1.0.0")
    assert found is not None

    found_typed = await crud.get_catalogue_resource(db_session, "acme", "widget", "1.0.0", type=CatalogueResourceType.widget)
    assert found_typed is not None

    missing = await crud.get_catalogue_resource(db_session, "acme", "widget", "9.9.9")
    assert missing is None


async def test_create_catalogue_resource_insert_none_raises(db_session, monkeypatch):
    class _Collection:
        async def insert_one(self, _payload):
            return SimpleNamespace(inserted_id=None)

    db = SimpleNamespace(client=SimpleNamespace(catalogue_resources=_Collection()))

    async def _commit(_db):
        return None

    monkeypatch.setattr(crud, "commit", _commit)

    create = CatalogueResourceCreate(
        vendor="acme",
        short_name="widget",
        version="1.0.0",
        type=CatalogueResourceType.widget,
        public=True,
        creation_date=datetime.now(timezone.utc),
        template_uri="widget.wgt",
        popularity=0,
        description=_macd_widget_dict(),
        creator=None,
    )

    with pytest.raises(ValueError):
        await crud.create_catalogue_resource(db, create)


async def test_get_resource_by_user_group_id_and_xhtml(db_session):
    uid = ObjectId()
    gid = ObjectId()
    rid = await _insert_resource(db_session, users=[uid], groups=[gid], creator_id=uid)

    user = _user(uid)

    by_user = await crud.get_user_catalogue_resource(db_session, user, "acme", "widget", "1.0.0")
    assert by_user is not None

    by_user_many = await crud.get_user_catalogue_resources(db_session, user, "acme", "widget")
    assert len(by_user_many) == 1

    by_id = await crud.get_catalogue_resource_by_id(db_session, Id(str(rid)))
    assert by_id is not None

    assert await crud.has_resource_user(db_session, Id(str(rid)), Id(str(uid))) is True
    assert await crud.has_resource_user(db_session, Id(str(rid)), Id(str(ObjectId()))) is False

    xhtml = XHTML(uri="u", url="x", content_type="text/html", use_platform_style=True, cacheable=True)
    await crud.save_catalogue_resource_xhtml(db_session, Id(str(rid)), xhtml)
    doc = await db_session.client.catalogue_resources.find_one({"_id": rid})
    assert doc["xhtml"]["uri"] == "u"
    with_xhtml = await crud.get_catalogue_resource_with_xhtml(db_session, "acme", "widget", "1.0.0")
    assert with_xhtml is not None


async def test_get_user_and_id_queries_return_none_when_missing(db_session):
    user = _user()
    assert await crud.get_user_catalogue_resource(db_session, user, "acme", "missing", "1.0.0") is None
    assert await crud.get_catalogue_resource_with_xhtml(db_session, "acme", "missing", "1.0.0") is None
    assert await crud.get_catalogue_resource_by_id(db_session, Id(str(ObjectId()))) is None


async def test_get_versions_and_visibility_queries(db_session):
    uid = ObjectId()
    gid = ObjectId()
    await _insert_resource(db_session, vendor="acme", short_name="w1", version="1.0.0", public=True)
    await _insert_resource(db_session, vendor="acme", short_name="w1", version="1.1.0", public=False, users=[uid])
    await _insert_resource(db_session, vendor="acme", short_name="w1", version="1.2.0", public=False, groups=[gid])

    versions = await crud.get_all_catalogue_resource_versions(db_session, "acme", "w1")
    assert len(versions) == 3

    anon = await crud.get_catalogue_resource_versions_for_user(db_session, "acme", "w1", None)
    assert len(anon) == 1

    user = _user_all(uid)
    user.groups = [Id(str(gid))]
    own = await crud.get_catalogue_resource_versions_for_user(db_session, "acme", "w1", user)
    assert len(own) == 3

    admin = _user_all(uid, perms=("COMPONENT.VIEW",))
    all_visible = await crud.get_catalogue_resource_versions_for_user(db_session, "acme", "w1", admin)
    assert len(all_visible) == 3

    all_resources = await crud.get_all_catalogue_resources(db_session)
    assert len(all_resources) >= 3

    only_vendor = await crud.get_catalogue_resource_versions_for_user(db_session, vendor="acme", user=None)
    only_name = await crud.get_catalogue_resource_versions_for_user(db_session, short_name="w1", user=None)
    assert len(only_vendor) >= 1
    assert len(only_name) >= 1


async def test_update_delete_and_install_uninstall_paths(db_session, monkeypatch):
    uid = ObjectId()
    gid = ObjectId()
    rid = await _insert_resource(db_session, public=False, creator_id=uid)

    commit_calls = {"n": 0}

    async def _commit(_db):
        commit_calls["n"] += 1

    monkeypatch.setattr(crud, "commit", _commit)

    await crud.update_catalogue_resource_description(
        db_session, Id(str(rid)), MACDWidget.model_validate(_macd_widget_dict("updated"))
    )
    updated = await db_session.client.catalogue_resources.find_one({"_id": rid})
    assert "updated" in updated["description"]

    res_obj = SimpleNamespace(id=Id(str(rid)))
    await crud.mark_resources_as_not_available(db_session, [res_obj])
    doc = await db_session.client.catalogue_resources.find_one({"_id": rid})
    assert doc["template_uri"] == ""

    await crud.change_resource_publicity(db_session, res_obj, True)
    doc2 = await db_session.client.catalogue_resources.find_one({"_id": rid})
    assert doc2["public"] is True

    user = _user(uid)
    installed = await crud.install_resource_to_user(db_session, res_obj, user)
    assert installed is True
    installed_again = await crud.install_resource_to_user(db_session, res_obj, user)
    assert installed_again is True  # current query checks different collection/field

    await db_session.client.catalogue_resource_users.insert_one({"_id": rid, "user_id": uid})
    already_installed = await crud.install_resource_to_user(db_session, res_obj, user)
    assert already_installed is False

    await db_session.client.catalogue_resources.update_one({"_id": rid}, {"$set": {"groups": []}})
    group = SimpleNamespace(id=Id(str(gid)))
    g1 = await crud.install_resource_to_group(db_session, res_obj, group)
    g2 = await crud.install_resource_to_group(db_session, res_obj, group)
    assert g1 is True
    assert g2 is False

    u1 = await crud.uninstall_resource_to_user(db_session, res_obj, user)
    u2 = await crud.uninstall_resource_to_user(db_session, res_obj, user)
    assert u1 is True
    assert u2 is False

    await db_session.client.catalogue_resources.update_one({"_id": rid}, {"$set": {"users": [], "groups": [], "public": False}})
    deleted_unused = await crud.delete_resource_if_not_used(db_session, res_obj)
    assert deleted_unused is True

    rid2 = await _insert_resource(db_session, public=True)
    not_deleted = await crud.delete_resource_if_not_used(db_session, SimpleNamespace(id=Id(str(rid2))))
    assert not_deleted is False

    rid3 = await _insert_resource(db_session, short_name="name@extra", version="2.0.0")
    rid4 = await _insert_resource(db_session, short_name="name", version="2.0.0")
    regex = await crud.get_catalogue_resources_with_regex(db_session, "acme", "name", "2.0.0")
    assert len(regex) == 2

    await crud.delete_catalogue_resources(db_session, [Id(str(rid3)), Id(str(rid4))])
    assert await db_session.client.catalogue_resources.count_documents({"_id": {"$in": [rid3, rid4]}}) == 0

    assert commit_calls["n"] >= 4
