# -*- coding: utf-8 -*-

from datetime import datetime, timezone
from types import SimpleNamespace

from wirecloud.catalogue import search


async def test_build_version_sortable_variants():
    stable = search.build_version_sortable("1.2.3")
    alpha = search.build_version_sortable("1.2.3a1")
    beta = search.build_version_sortable("1.2.3b2")
    rc = search.build_version_sortable("1.2.3rc3")

    assert stable > rc > beta > alpha


async def test_clean_resource_out_with_inner_hits(monkeypatch):
    monkeypatch.setattr(search, "get_template_url", lambda *args, **kwargs: "http://base/")

    hit = {
        "_id": "rid",
        "_source": {
            "vendor_name": "acme/widget",
            "vendor": "acme",
            "name": "widget",
            "version": "1.0.0",
            "description_url": "desc.json",
            "type": "widget",
            "creation_date": datetime.now(timezone.utc),
            "public": True,
            "title": "Title",
            "description": "Desc",
            "image": "img.png",
            "smartphoneimage": "simg.png",
            "input_friendcodes": ["a"],
            "output_friendcodes": ["b"],
        },
        "inner_hits": {
            "others": {
                "hits": {
                    "hits": [
                        {"_source": {"version": "0.9.0"}},
                        {"_source": {"version": "1.0.0"}},
                    ]
                }
            }
        },
    }

    out = search.clean_resource_out(hit, SimpleNamespace())
    assert out.vendor == "acme"
    assert out.others == ["0.9.0"]
    assert out.uri == "acme/widget/1.0.0"

    hit_no_inner = dict(hit)
    hit_no_inner.pop("inner_hits")
    out_no_inner = search.clean_resource_out(hit_no_inner, SimpleNamespace())
    assert out_no_inner.others == []


async def test_search_resources_body_and_ordering(monkeypatch):
    captured = {}

    async def _build_search_response(index, body, pagenum, max_results, clean, request):
        captured["index"] = index
        captured["body"] = body
        captured["pagenum"] = pagenum
        captured["max_results"] = max_results
        return {"ok": True}

    monkeypatch.setattr("wirecloud.commons.search.build_search_response", _build_search_response)

    class _User:
        id = "507f1f77bcf86cd799439011"
        groups = ["507f1f77bcf86cd799439012"]

        def has_perm(self, codename):
            return False

    request = SimpleNamespace()

    ok = await search.search_resources(request, _User(), "temp", pagenum=2, maxresults=5, scope="widget", order_by=("vendor", "-name"))
    assert ok == {"ok": True}
    assert captured["index"] == search.RESOURCES_INDEX
    assert {"type": "widget"} in [term.get("term") for term in captured["body"]["query"]["bool"]["filter"]]
    assert captured["pagenum"] == 2
    assert captured["max_results"] == 5

    bad = await search.search_resources(request, _User(), "", order_by=("unknown_field",))
    assert bad is None

    captured.clear()
    ok_default = await search.search_resources(request, _User(), "temp", order_by=None)
    assert ok_default == {"ok": True}
    assert captured["body"]["query"]["bool"]["must"][0]["multi_match"]["query"] == "temp"

    class _GlobalUser(_User):
        def has_perm(self, codename):
            return codename == "COMPONENT.VIEW"

    await search.search_resources(request, _GlobalUser(), "temp", order_by=("-creation_date",))
    assert "should" not in captured["body"]["query"]["bool"]

    await search.search_resources(request, None, "", order_by=("-creation_date",))
    assert captured["body"]["query"]["bool"]["should"] == [{"term": {"public": True}}]


async def test_prepare_rebuild_add_delete_index(monkeypatch):
    fake_info = SimpleNamespace(
        title="Title",
        description="Desc",
        image="img.png",
        smartphoneimage="simg.png",
        wiring=SimpleNamespace(
            inputs=[SimpleNamespace(description="i1", friendcode="a b")],
            outputs=[SimpleNamespace(description="o1", friendcode="c")],
        ),
    )

    class _Resource:
        id = "507f1f77bcf86cd799439011"
        vendor = "acme"
        short_name = "widget"
        version = "1.2.3"
        type = SimpleNamespace(name="widget")
        users = []
        groups = []
        template_uri = "widget.wgt"
        creation_date = datetime.now(timezone.utc)
        public = True

        def get_processed_info(self, process_urls=False):
            return fake_info

    prepared = search.prepare_resource_for_indexing(_Resource())
    assert prepared.vendor_name == "acme/widget"
    assert "a" in prepared.input_friendcodes

    class _Indices:
        def __init__(self):
            self.exists_called = False
            self.deleted = False
            self.created = False

        async def exists(self, index):
            self.exists_called = True
            return True

        async def delete(self, index):
            self.deleted = True

        async def create(self, index, body):
            self.created = True

    class _ES:
        def __init__(self):
            self.indices = _Indices()
            self.index_calls = []
            self.delete_calls = []

        async def index(self, index, id, document):
            self.index_calls.append((index, id, document))

        async def delete(self, index, id):
            self.delete_calls.append((index, id))

    es = _ES()
    monkeypatch.setattr("wirecloud.commons.search.es_client", es)

    async def _all_resources(_db):
        return [_Resource()]

    async def _by_id(_db, _id):
        return _Resource()

    bulk_calls = {}

    async def _bulk(_es_client, actions):
        bulk_calls["actions"] = actions

    monkeypatch.setattr(search, "get_all_catalogue_resources", _all_resources)
    monkeypatch.setattr(search, "get_catalogue_resource_by_id", _by_id)
    monkeypatch.setattr(search, "async_bulk", _bulk)

    await search.rebuild_resource_index(SimpleNamespace())
    assert es.indices.exists_called is True
    assert es.indices.deleted is True
    assert es.indices.created is True
    assert len(bulk_calls["actions"]) == 1

    await search.add_resource_to_index(SimpleNamespace(), _Resource())
    assert len(es.index_calls) == 1

    await search.delete_resource_from_index(_Resource())
    assert len(es.delete_calls) == 1

    class _IndicesNoExists(_Indices):
        async def exists(self, index):
            self.exists_called = True
            return False

    es2 = _ES()
    es2.indices = _IndicesNoExists()
    monkeypatch.setattr("wirecloud.commons.search.es_client", es2)
    await search.rebuild_resource_index(SimpleNamespace())
    assert es2.indices.deleted is False
