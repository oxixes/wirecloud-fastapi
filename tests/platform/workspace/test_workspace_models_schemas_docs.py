# -*- coding: utf-8 -*-

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from bson import ObjectId

from wirecloud.platform.workspace import docs, models, schemas


def test_workspace_docs_constants_present():
    assert isinstance(docs.get_workspace_collection_summary, str)
    assert isinstance(docs.create_workspace_collection_workspace_example, list)
    assert isinstance(docs.workspace_data, dict)
    assert isinstance(docs.tab_data, dict)


def test_workspace_schema_serializers_and_validators(monkeypatch):
    monkeypatch.setattr(schemas, "_", lambda text: text)

    now = datetime(2026, 3, 12, tzinfo=timezone.utc)
    tab_data = schemas.TabData(id="w-0", name="tab", title="Tab", last_modified=now)
    assert tab_data.model_dump()["last_modified"] == int(now.timestamp() * 1000)
    assert tab_data.serialize_last_modified(now, None) == int(now.timestamp() * 1000)

    workspace_data = schemas.WorkspaceData(
        id="wid",
        name="w",
        title="W",
        public=False,
        shared=False,
        requireauth=False,
        owner="alice",
        removable=True,
        lastmodified=now,
        description="d",
        longdescription="ld",
    )
    assert workspace_data.model_dump()["lastmodified"] == int(now.timestamp() * 1000)
    assert workspace_data.serialize_lastmodified(now, None) == int(now.timestamp() * 1000)

    with pytest.raises(ValueError, match="Missing name or title parameter"):
        schemas.WorkspaceCreate()

    with pytest.raises(ValueError, match="cannot be used at the same time"):
        schemas.WorkspaceCreate(name="x", title="", workspace="1", mashup="m/v/1.0.0")

    valid = schemas.WorkspaceCreate(name="x", title="", workspace="", mashup="")
    assert valid.name == "x"


async def test_workspace_model_access_and_editability(monkeypatch):
    user_id = ObjectId()
    creator_id = ObjectId()
    group_id = ObjectId()
    workspace = models.Workspace(
        _id=ObjectId(),
        name="w",
        title="W",
        creator=creator_id,
        users=[models.WorkspaceAccessPermissions(id=user_id, accesslevel=1)],
        groups=[models.WorkspaceAccessPermissions(id=group_id, accesslevel=1)],
    )

    async def _groups(_db, _user):
        return [SimpleNamespace(id=group_id)]

    monkeypatch.setattr(models, "get_all_user_groups", _groups)

    anonymous_access = await workspace.is_accessible_by(None, None)
    assert anonymous_access is False

    workspace.public = True
    workspace.requireauth = False
    assert await workspace.is_accessible_by(None, None) is True

    view_user = SimpleNamespace(id=ObjectId(), has_perm=lambda perm: perm == "WORKSPACE.VIEW", is_superuser=False)
    assert await workspace.is_accessible_by(None, view_user) is True

    workspace.public = False
    workspace.requireauth = True
    owner_user = SimpleNamespace(id=creator_id, has_perm=lambda _perm: False, is_superuser=False)
    assert await workspace.is_accessible_by(None, owner_user) is True

    listed_user = SimpleNamespace(id=user_id, has_perm=lambda _perm: False, is_superuser=False)
    assert await workspace.is_accessible_by(None, listed_user) is True

    workspace.users = []
    grouped_user = SimpleNamespace(id=ObjectId(), has_perm=lambda _perm: False, is_superuser=False)
    assert await workspace.is_accessible_by(None, grouped_user) is True

    workspace.groups = []
    workspace.public = False
    assert await workspace.is_accessible_by(None, grouped_user) is False

    workspace.users = [models.WorkspaceAccessPermissions(id=ObjectId(), accesslevel=2)]
    superuser = SimpleNamespace(id=ObjectId(), has_perm=lambda _perm: False, is_superuser=True)
    assert await workspace.is_editable_by(None, superuser) is True
    assert await workspace.is_editable_by(None, owner_user) is True

    direct_editor = SimpleNamespace(id=workspace.users[0].id, has_perm=lambda _perm: False, is_superuser=False)
    assert await workspace.is_editable_by(None, direct_editor) is True

    workspace.users = [models.WorkspaceAccessPermissions(id=direct_editor.id, accesslevel=1)]
    fallback_editor = SimpleNamespace(
        id=direct_editor.id,
        has_perm=lambda perm: perm == "WORKSPACE.EDIT",
        is_superuser=False,
    )
    workspace.public = True
    workspace.requireauth = False
    assert await workspace.is_editable_by(None, fallback_editor) is True

    workspace.users = []
    workspace.groups = [models.WorkspaceAccessPermissions(id=group_id, accesslevel=2)]
    assert await workspace.is_editable_by(None, grouped_user) is True

    workspace.groups = [models.WorkspaceAccessPermissions(id=group_id, accesslevel=1)]
    assert await workspace.is_editable_by(None, grouped_user) is False

    workspace.groups = []
    workspace.public = True
    workspace.requireauth = False
    perm_editor = SimpleNamespace(
        id=ObjectId(),
        has_perm=lambda perm: perm == "WORKSPACE.EDIT",
        is_superuser=False,
    )
    assert await workspace.is_editable_by(None, perm_editor) is True

    workspace.public = False
    assert workspace.is_shared() is False
    workspace.public = True
    assert workspace.is_shared() is True
