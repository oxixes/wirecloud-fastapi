# -*- coding: utf-8 -*-

from types import SimpleNamespace

from wirecloud.commons import search


class _FakeIndices:
    def __init__(self, exists_value=True):
        self.exists_value = exists_value
        self.deleted = []
        self.created = []

    async def exists(self, index):
        return self.exists_value

    async def delete(self, index):
        self.deleted.append(index)

    async def create(self, index, body):
        self.created.append((index, body))


class _FakeES:
    def __init__(self, count_value=0, search_payload=None, exists_value=True):
        self.count_value = count_value
        self.search_payload = search_payload or {"hits": {"hits": [], "total": {"value": 0}}}
        self.indices = _FakeIndices(exists_value=exists_value)
        self.index_calls = []
        self.delete_calls = []

    async def count(self, index, body):
        return {"count": self.count_value}

    async def search(self, index, body, from_, size):
        return self.search_payload

    async def index(self, index, id, document):
        self.index_calls.append((index, id, document))

    async def delete(self, index, id):
        self.delete_calls.append((index, id))


async def test_available_engines_and_getters(monkeypatch):
    import wirecloud.platform.search as platform_search
    import wirecloud.catalogue.search as catalogue_search

    monkeypatch.setattr(platform_search, "search_workspaces", "workspace_search")
    monkeypatch.setattr(catalogue_search, "search_resources", "resource_search")
    search._available_search_engines = None
    engines = search.get_available_search_engines()
    assert engines["group"] == search.search_groups
    assert engines["workspace"] == "workspace_search"
    assert search.get_available_search_engines() is engines
    assert search.is_available_search_engine("user") is True
    assert search.is_available_search_engine("missing") is False
    assert search.get_search_engine("resource") == "resource_search"
    assert search.get_search_engine("missing") is None

    monkeypatch.setattr(platform_search, "rebuild_workspace_index", "workspace_rebuild")
    monkeypatch.setattr(catalogue_search, "rebuild_resource_index", "resource_rebuild")
    search._available_rebuild_engines = None
    rebuild = search.get_available_rebuild_engines()
    assert rebuild["group"] == search.rebuild_group_index
    assert rebuild["all"] == search.rebuild_all_indexes
    assert rebuild["workspace"] == "workspace_rebuild"
    assert search.get_available_rebuild_engines() is rebuild
    assert search.is_available_rebuild_engine("user") is True
    assert search.is_available_rebuild_engine("missing") is False
    assert search.get_rebuild_engine("resource") == "resource_rebuild"
    assert search.get_rebuild_engine("missing") is None


async def test_calculate_pagination_and_build_search_response(monkeypatch):
    es = _FakeES(count_value=11)
    monkeypatch.setattr(search, "es_client", es)
    offset, pagecount, pagenum, total = await search.calculate_pagination("users", {}, pagenum=99, max_results=5)
    assert (offset, pagecount, pagenum, total) == (10, 3, 3, 11)

    offset2, pagecount2, pagenum2, total2 = await search.calculate_pagination(
        "users",
        {"query": {"term": {"x": 1}}},
        pagenum=1,
        max_results=5,
    )
    assert (offset2, pagecount2, pagenum2, total2) == (0, 3, 1, 11)
    es.count_value = 10
    assert await search.calculate_pagination("users", {}, pagenum=1, max_results=5) == (0, 2, 1, 10)

    async def _calc(*_args, **_kwargs):
        return 0, 1, 1, 2

    monkeypatch.setattr(search, "calculate_pagination", _calc)
    monkeypatch.setattr(
        search,
        "es_client",
        _FakeES(
            search_payload={
                "hits": {
                    "hits": [{"_id": "73", "_source": {"fullname": "A", "username": "u1"}}],
                    "total": {"value": 7},
                }
            }
        ),
    )
    response = await search.build_search_response(
        index=search.USERS_INDEX,
        body={},
        pagenum=1,
        max_results=5,
        clean=search.clean_user_out,
    )
    assert response.total == 7
    assert response.pagelen == 1
    assert response.results[0].type == "user"

    called = {}

    def _clean_resource(hit, request):
        called["request"] = request
        return {"fullname": hit["_source"]["name"], "username": "res", "type": "user"}

    monkeypatch.setattr(
        search,
        "es_client",
        _FakeES(search_payload={"hits": {"hits": [{"_source": {"name": "r1"}}]}}),
    )
    response_resources = await search.build_search_response(
        index=search.RESOURCES_INDEX,
        body={},
        pagenum=1,
        max_results=5,
        clean=_clean_resource,
        request="req",
    )
    assert response_resources.total == 1
    assert response_resources.results[0].fullname == "r1"
    assert called["request"] == "req"


async def test_clean_and_search_functions(monkeypatch):
    captured = {}

    async def _build(index, body, pagenum, max_results, clean, request=None):
        captured["index"] = index
        captured["body"] = body
        captured["pagenum"] = pagenum
        captured["max_results"] = max_results
        captured["request"] = request
        return {"ok": True}

    monkeypatch.setattr(search, "build_search_response", _build)

    out_user = search.clean_user_out({"_id": "42", "_source": {"fullname": "Alice", "username": "alice"}})
    assert out_user.fullname == "Alice"
    assert out_user.type == "user"

    out_group = search.clean_group_out({"_source": {"name": "Dev", "is_organization": True}})
    assert out_group.type == "organization"

    ok_users = await search.search_users("alice", 2, 5, order_by=("username", "-fullname"))
    assert ok_users == {"ok": True}
    assert captured["index"] == search.USERS_INDEX
    assert captured["body"]["sort"] == [
        {"username.keyword": {"order": "asc"}},
        {"fullname.keyword": {"order": "desc"}},
    ]

    none_users = await search.search_users("alice", 2, 5, order_by=("invalid",))
    assert none_users is None

    await search.search_users("", 1, 10, order_by=None)
    assert captured["body"] == {}

    ok_groups = await search.search_groups("dev", 2, 5, order_by=("name",))
    assert ok_groups == {"ok": True}
    assert captured["index"] == search.GROUPS_INDEX
    assert captured["body"]["query"]["multi_match"]["fields"] == search.GROUP_CONTENT_FIELDS

    none_groups = await search.search_groups("dev", 2, 5, order_by=("username",))
    assert none_groups is None

    await search.search_groups("", 1, 10, order_by=None)
    assert captured["body"] == {}

    ok_user_groups = await search.search_user_groups("al", 1, 10, order_by=("name", "-username"))
    assert ok_user_groups == {"ok": True}
    assert captured["index"] == [search.USERS_INDEX, search.GROUPS_INDEX]
    assert captured["body"]["query"]["multi_match"]["fields"] == search.USER_CONTENT_FIELDS + search.GROUP_CONTENT_FIELDS

    none_user_groups = await search.search_user_groups("al", 1, 10, order_by=("missing",))
    assert none_user_groups is None

    clean_mux = captured["clean"] if "clean" in captured else None
    if clean_mux is None:
        async def _build_with_clean(index, body, pagenum, max_results, clean, request=None):
            return clean({"_index": search.GROUPS_INDEX, "_source": {"name": "Org", "is_organization": True}})

        monkeypatch.setattr(search, "build_search_response", _build_with_clean)
        selected = await search.search_user_groups("", 1, 10, order_by=None)
        assert selected.type == "organization"


async def test_add_and_rebuild_indexes(monkeypatch):
    es = _FakeES()
    monkeypatch.setattr(search, "es_client", es)

    user = SimpleNamespace(id="u1", first_name="Alice", last_name="A", username="alice")
    group = SimpleNamespace(id="g1", name="Dev", is_organization=False, path=["g1"])
    await search.add_user_to_index(user)
    await search.add_group_to_index(group)
    assert es.index_calls[0][0] == search.USERS_INDEX
    assert es.index_calls[1][0] == search.GROUPS_INDEX
    assert es.index_calls[1][2]["type"] == "group"

    await search.delete_user_from_index(user)
    await search.delete_group_from_index(group)
    assert es.delete_calls == [
        (search.USERS_INDEX, "u1"),
        (search.GROUPS_INDEX, "g1"),
    ]

    bulk_calls = {"n": 0, "last": None}

    async def _bulk(_es, actions):
        bulk_calls["n"] += 1
        bulk_calls["last"] = actions

    monkeypatch.setattr(search, "async_bulk", _bulk)
    async def _all_users(_db):
        return [user]

    async def _all_groups(_db):
        return [group]

    monkeypatch.setattr(search, "get_all_users", _all_users)
    monkeypatch.setattr(search, "get_all_groups", _all_groups)

    await search.rebuild_user_index(SimpleNamespace())
    assert search.USERS_INDEX in es.indices.deleted
    assert es.indices.created[0][0] == search.USERS_INDEX
    assert bulk_calls["n"] == 1
    assert bulk_calls["last"][0]["_source"]["username"] == "alice"

    await search.rebuild_group_index(SimpleNamespace())
    assert search.GROUPS_INDEX in es.indices.deleted
    assert es.indices.created[1][0] == search.GROUPS_INDEX
    assert bulk_calls["n"] == 2
    assert bulk_calls["last"][0]["_source"]["type"] == "group"

    es_no_delete = _FakeES(exists_value=False)
    monkeypatch.setattr(search, "es_client", es_no_delete)
    await search.rebuild_user_index(SimpleNamespace())
    await search.rebuild_group_index(SimpleNamespace())
    assert es_no_delete.indices.deleted == []


async def test_rebuild_all_indexes(monkeypatch):
    calls = []

    async def _user(_db):
        calls.append("user")

    async def _group(_db):
        calls.append("group")

    monkeypatch.setattr(search, "rebuild_user_index", _user)
    monkeypatch.setattr(search, "rebuild_group_index", _group)

    import wirecloud.platform.search as platform_search
    import wirecloud.catalogue.search as catalogue_search

    async def _workspace(_db):
        calls.append("workspace")

    async def _resource(_db):
        calls.append("resource")

    monkeypatch.setattr(platform_search, "rebuild_workspace_index", _workspace)
    monkeypatch.setattr(catalogue_search, "rebuild_resource_index", _resource)

    await search.rebuild_all_indexes(SimpleNamespace())
    assert calls == ["user", "group", "workspace", "resource"]
