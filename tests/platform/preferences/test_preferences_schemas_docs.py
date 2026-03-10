# -*- coding: utf-8 -*-

from wirecloud.platform.preferences import docs, schemas


def test_docs_strings_and_examples():
    assert isinstance(docs.get_platform_preference_collection_summary, str)
    assert isinstance(docs.create_platform_preference_collection_platform_preference_create_example, dict)
    assert isinstance(docs.get_workspace_preference_collection_response_example, dict)
    assert isinstance(docs.get_tab_preference_collection_response_example, dict)


def test_schemas_roundtrip():
    entry = schemas.SelectEntry(value="v1", label="Value 1")
    key = schemas.PreferenceKey(name="p1", label="Pref 1", type="text", initialEntries=[entry], defaultValue="x")
    tab_key = schemas.TabPreferenceKey(name="t1", label="Tab 1", type="text")
    value = schemas.PlatformPreferenceCreateValue(value="abc")
    create = schemas.PlatformPreferenceCreate(preferences={"name": "wirecloud", "k": value})
    wp = schemas.WorkspacePreference(inherit=True, value="1")
    tp = schemas.TabPreference(inherit=False, value="2")
    share = schemas.ShareListPreference(type=schemas.ShareListEnum.user, name="alice", value="2")

    assert key.initialEntries[0].value == "v1"
    assert tab_key.inheritable is True
    assert create.preferences["name"] == "wirecloud"
    assert create.preferences["k"].value == "abc"
    assert wp.inherit is True
    assert tp.value == "2"
    assert share.type == "user"
