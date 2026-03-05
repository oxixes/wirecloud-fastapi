# -*- coding: utf-8 -*-

import errno
from datetime import datetime, timezone
from io import BytesIO
from types import SimpleNamespace

import pytest

from wirecloud.catalogue import utils
from wirecloud.commons.utils.template import ObsoleteFormatError, TemplateFormatError, TemplateParseException
from wirecloud.commons.utils.template.schemas.macdschemas import MACDWidget, MACType
from wirecloud.commons.utils.wgt import InvalidContents


@pytest.fixture(autouse=True)
def _patch_gettext(monkeypatch):
    monkeypatch.setattr(utils, "_", lambda text: text)


def _macd_widget_dict(name="widget", version="1.0.0"):
    return {
        "type": "widget",
        "macversion": 1,
        "name": name,
        "vendor": "acme",
        "version": version,
        "title": "Title",
        "description": "Desc",
        "contents": {"src": "index.html", "charset": "utf-8"},
        "widget_width": "4",
        "widget_height": "3",
        "wiring": {"inputs": [], "outputs": []},
    }


def _resource(public=False):
    return SimpleNamespace(
        id="507f1f77bcf86cd799439011",
        vendor="acme",
        short_name="widget",
        version="1.0.0",
        type=SimpleNamespace(name="widget"),
        public=public,
        creation_date=datetime.now(timezone.utc),
        template_uri="widget.wgt",
        get_processed_info=lambda request=None: SimpleNamespace(
            type=SimpleNamespace(name="widget"),
            title="Title",
            description="Desc",
            longdescription="docs/long.md",
            email="",
            image="img.png",
            homepage="",
            doc="docs/user.md",
            changelog="docs/changelog.md",
            authors=[],
            contributors=[],
            license="",
            licenseurl="",
            issuetracker="",
        ),
        get_template_url=lambda request=None, for_base=False: "http://testserver/catalogue/media/acme/widget/1.0.0/",
        resource_type=lambda: "widget",
    )


def test_extract_resource_media_from_package_paths():
    extracted = {"files": [], "dirs": [], "localized": []}

    resource_info = SimpleNamespace(
        image="img/logo.png",
        smartphoneimage="/absolute/smart.png",
        doc="docs/guide.md",
        longdescription="docs/long.md",
        changelog="docs/changelog.md",
    )
    template = SimpleNamespace(
        get_resource_info=lambda: resource_info,
        get_absolute_url=lambda v: f"http://base{v}",
    )

    class _Package:
        def extract_file(self, src, dst):
            extracted["files"].append((src, dst))

        def extract_dir(self, src, dst):
            extracted["dirs"].append((src, dst))

        def extract_localized_files(self, src, dst):
            extracted["localized"].append((src, dst))

    overrides = utils.extract_resource_media_from_package(template, _Package(), "/tmp/base")

    assert overrides == {"smartphoneimage": "http://base/absolute/smart.png"}
    assert extracted["files"][0][0] == "img/logo.png"
    assert extracted["dirs"][0][0] == "docs"
    assert len(extracted["localized"]) == 2


def test_extract_resource_media_overrides_and_skips():
    extracted = {"files": 0, "dirs": 0, "localized": 0}
    resource_info = SimpleNamespace(
        image="/img.png",
        smartphoneimage="simg.png",
        doc="//docs/guide.md",
        longdescription="https://example.com/long.md",
        changelog="",
    )
    template = SimpleNamespace(get_resource_info=lambda: resource_info, get_absolute_url=lambda v: f"http://base{v}")

    class _Package:
        def extract_file(self, *_args):
            extracted["files"] += 1

        def extract_dir(self, *_args):
            extracted["dirs"] += 1

        def extract_localized_files(self, *_args):
            extracted["localized"] += 1

    overrides = utils.extract_resource_media_from_package(template, _Package(), "/tmp/base")
    assert overrides == {"image": "http://base/img.png", "doc": "http://base//docs/guide.md"}
    assert extracted == {"files": 1, "dirs": 0, "localized": 0}

    resource_info_2 = SimpleNamespace(
        image="https://example.com/img.png",
        smartphoneimage="//smart.png",
        doc="/docs/guide.md",
        longdescription="",
        changelog="",
    )
    template_2 = SimpleNamespace(get_resource_info=lambda: resource_info_2, get_absolute_url=lambda v: f"http://base{v}")
    overrides_2 = utils.extract_resource_media_from_package(template_2, _Package(), "/tmp/base")
    assert overrides_2 == {"smartphoneimage": "http://base//smart.png", "doc": "http://base/docs/guide.md"}

    resource_info_3 = SimpleNamespace(
        image="",
        smartphoneimage="https://example.com/smart.png",
        doc="",
        longdescription="",
        changelog="",
    )
    template_3 = SimpleNamespace(get_resource_info=lambda: resource_info_3, get_absolute_url=lambda v: f"http://base{v}")
    overrides_3 = utils.extract_resource_media_from_package(template_3, _Package(), "/tmp/base")
    assert overrides_3 == {}

    resource_info_4 = SimpleNamespace(
        image="",
        smartphoneimage="",
        doc="https://example.com/doc.md",
        longdescription="",
        changelog="",
    )
    template_4 = SimpleNamespace(get_resource_info=lambda: resource_info_4, get_absolute_url=lambda v: f"http://base{v}")
    overrides_4 = utils.extract_resource_media_from_package(template_4, _Package(), "/tmp/base")
    assert overrides_4 == {}


def test_check_invalid_doc_entry_variants(monkeypatch):
    class _Wgt:
        def __init__(self, payload):
            self.payload = payload

        def read(self, _path):
            if isinstance(self.payload, Exception):
                raise self.payload
            return self.payload

    with pytest.raises(InvalidContents):
        utils.check_invalid_doc_entry(_Wgt(Exception("missing")), "doc.md")

    with pytest.raises(InvalidContents):
        utils.check_invalid_doc_entry(_Wgt(b"\xff"), "doc.md")

    monkeypatch.setattr(utils.markdown, "markdown", lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("bad")))
    with pytest.raises(InvalidContents):
        utils.check_invalid_doc_entry(_Wgt(b"# ok"), "doc.md")


def test_check_invalid_doc_content_and_image(monkeypatch):
    calls = []
    monkeypatch.setattr(utils, "check_invalid_doc_entry", lambda _wgt, p: calls.append(p))

    info = SimpleNamespace(doc="docs/guide.md")
    wgt = SimpleNamespace(namelist=lambda: ["docs/guide.en.md", "other.txt"])
    utils.check_invalid_doc_content(wgt, info, "doc")
    assert calls == ["docs/guide.md", "docs/guide.en.md"]

    with pytest.raises(InvalidContents):
        utils.check_invalid_image(SimpleNamespace(read=lambda _p: (_ for _ in ()).throw(KeyError("no"))), SimpleNamespace(image="img/x.png"), "image")

    utils.check_invalid_doc_content(SimpleNamespace(namelist=lambda: []), SimpleNamespace(doc="http://example.com/doc.md"), "doc")
    utils.check_invalid_image(SimpleNamespace(read=lambda _p: b"x"), SimpleNamespace(image="https://example.com/image.png"), "image")


def test_check_invalid_embedded_resources(monkeypatch):
    utils.check_invalid_embedded_resources(SimpleNamespace(), SimpleNamespace(type=MACType.widget))
    utils.check_invalid_embedded_resources(SimpleNamespace(namelist=lambda: []), SimpleNamespace(type=MACType.mashup, embedded=[]))

    mashup_info = SimpleNamespace(type=MACType.mashup, embedded=[SimpleNamespace(src="inner.wgt")])
    with pytest.raises(InvalidContents):
        utils.check_invalid_embedded_resources(SimpleNamespace(namelist=lambda: []), mashup_info)

    class _InnerWgt:
        def __init__(self, _io):
            pass

    monkeypatch.setattr(utils, "WgtFile", _InnerWgt)
    monkeypatch.setattr(utils, "check_packaged_resource", lambda _wgt: (_ for _ in ()).throw(RuntimeError("bad")))
    with pytest.raises(InvalidContents):
        utils.check_invalid_embedded_resources(
            SimpleNamespace(namelist=lambda: ["inner.wgt"], read=lambda _p: b"payload"),
            mashup_info,
        )


def test_check_packaged_resource_template_parse_errors(monkeypatch):
    wgt = SimpleNamespace(get_template=lambda: "<xml/>")

    def _obsolete(_tpl):
        raise ObsoleteFormatError()

    def _bad_format(_tpl):
        raise TemplateFormatError("bad")

    def _bad_parse(_tpl):
        raise TemplateParseException("bad")

    monkeypatch.setattr(utils, "TemplateParser", _obsolete)
    with pytest.raises(InvalidContents):
        utils.check_packaged_resource(wgt)

    monkeypatch.setattr(utils, "TemplateParser", _bad_format)
    with pytest.raises(InvalidContents):
        utils.check_packaged_resource(wgt)

    monkeypatch.setattr(utils, "TemplateParser", _bad_parse)
    with pytest.raises(InvalidContents):
        utils.check_packaged_resource(wgt)


def test_check_packaged_resource_widget_errors_and_success(monkeypatch):
    resource_info = MACDWidget.model_validate(_macd_widget_dict())

    with pytest.raises(InvalidContents):
        utils.check_packaged_resource(SimpleNamespace(read=lambda _p: (_ for _ in ()).throw(KeyError("missing"))), resource_info)

    resource_info_bad_charset = MACDWidget.model_validate(_macd_widget_dict())
    resource_info_bad_charset.contents.charset = "ascii"
    with pytest.raises(InvalidContents):
        utils.check_packaged_resource(SimpleNamespace(read=lambda _p: b"\xff"), resource_info_bad_charset)

    calls = {"img": 0, "doc": 0, "embedded": 0}
    monkeypatch.setattr(utils, "check_invalid_image", lambda *_a, **_k: calls.__setitem__("img", calls["img"] + 1))
    monkeypatch.setattr(utils, "check_invalid_doc_content", lambda *_a, **_k: calls.__setitem__("doc", calls["doc"] + 1))
    monkeypatch.setattr(utils, "check_invalid_embedded_resources", lambda *_a, **_k: calls.__setitem__("embedded", calls["embedded"] + 1))

    utils.check_packaged_resource(SimpleNamespace(read=lambda _p: b"ok"), resource_info)
    assert calls == {"img": 2, "doc": 3, "embedded": 1}

    calls = {"img": 0, "doc": 0, "embedded": 0}
    http_code = MACDWidget.model_validate(_macd_widget_dict())
    http_code.contents.src = "https://example.com/widget.html"
    utils.check_packaged_resource(SimpleNamespace(read=lambda _p: b"unused"), http_code)
    assert calls == {"img": 2, "doc": 3, "embedded": 1}


def test_check_packaged_resource_none_resource_info_success(monkeypatch):
    info = MACDWidget.model_validate(_macd_widget_dict())
    monkeypatch.setattr(utils, "TemplateParser", lambda _tpl: SimpleNamespace(get_resource_info=lambda: info))
    monkeypatch.setattr(utils, "check_invalid_image", lambda *_a, **_k: None)
    monkeypatch.setattr(utils, "check_invalid_doc_content", lambda *_a, **_k: None)
    monkeypatch.setattr(utils, "check_invalid_embedded_resources", lambda *_a, **_k: None)
    utils.check_packaged_resource(SimpleNamespace(get_template=lambda: "<tpl/>", read=lambda _p: b"ok"))


def test_check_packaged_resource_non_widget_skips_code_read(monkeypatch):
    monkeypatch.setattr(utils, "check_invalid_image", lambda *_a, **_k: None)
    monkeypatch.setattr(utils, "check_invalid_doc_content", lambda *_a, **_k: None)
    monkeypatch.setattr(utils, "check_invalid_embedded_resources", lambda *_a, **_k: None)
    utils.check_packaged_resource(SimpleNamespace(read=lambda _p: b"unused"), SimpleNamespace(type=MACType.operator))


async def test_add_packaged_resource_variants(monkeypatch, tmp_path):
    resource_info = MACDWidget.model_validate(_macd_widget_dict())
    template = SimpleNamespace(get_resource_info=lambda: resource_info)

    class _Wgt:
        def __init__(self, _f):
            self.closed = False

        def get_template(self):
            return "tpl"

        def close(self):
            self.closed = True

    created = {}

    async def _create(_db, payload):
        created["payload"] = payload
        return SimpleNamespace(id="507f1f77bcf86cd799439011")

    monkeypatch.setattr(utils, "WgtFile", _Wgt)
    monkeypatch.setattr(utils, "TemplateParser", lambda _tpl: template)
    monkeypatch.setattr(utils, "check_packaged_resource", lambda *_a, **_k: None)
    monkeypatch.setattr(utils, "extract_resource_media_from_package", lambda *_a, **_k: {"image": "http://external/img"})
    monkeypatch.setattr(utils, "create_catalogue_resource", _create)
    monkeypatch.setattr(utils.wgt_deployer, "get_base_dir", lambda *_a: str(tmp_path / "cat"))

    file_obj = BytesIO(b"zip-bytes")
    result = await utils.add_packaged_resource(SimpleNamespace(), file_obj, user=None)
    assert result is not None
    assert created["payload"].description.image == "http://external/img"

    file_obj_2 = BytesIO(b"zip-bytes")
    no_db_entry = await utils.add_packaged_resource(SimpleNamespace(), file_obj_2, user=None, deploy_only=True)
    assert no_db_entry is None

    explicit = await utils.add_packaged_resource(
        SimpleNamespace(),
        BytesIO(b"zip-bytes"),
        user=None,
        wgt_file=SimpleNamespace(close=lambda: (_ for _ in ()).throw(RuntimeError("should not close"))),
        template=template,
        deploy_only=True,
    )
    assert explicit is None


async def test_get_resource_data_and_group_data(monkeypatch, tmp_path):
    r = _resource(public=False)
    monkeypatch.setattr(utils.wgt_deployer, "get_base_dir", lambda *_a: str(tmp_path))
    monkeypatch.setattr(utils.os.path, "getsize", lambda _p: 42)
    monkeypatch.setattr(utils, "get_absolute_reverse_url", lambda *_a, **_k: "http://testserver/catalogue/media/acme/widget/1.0.0/widget.wgt")
    monkeypatch.setattr(utils, "force_trailing_slash", lambda url: url if url.endswith("/") else url + "/")
    monkeypatch.setattr(utils.markdown, "markdown", lambda *_a, **_k: "<p>md</p>")
    monkeypatch.setattr(utils, "clean_html", lambda html, base_url=None: f"clean:{base_url}:{html}")
    monkeypatch.setattr(utils, "download_local_file", lambda _path: b"# Long")

    async def _has_user(_db, _rid, _uid):
        return True

    monkeypatch.setattr(utils, "has_resource_user", _has_user)

    user = SimpleNamespace(id="507f1f77bcf86cd799439012", is_superuser=True)
    data = await utils.get_resource_data(SimpleNamespace(), r, user, request=SimpleNamespace())
    assert data.size == 42
    assert data.permissions.delete is True
    assert data.permissions.uninstall is True
    assert data.longdescription.startswith("clean:")

    async def _data(_db, _resource, _user, _request):
        return data

    original_get_resource_data = utils.get_resource_data
    monkeypatch.setattr(utils, "get_resource_data", _data)
    group = await utils.get_resource_group_data(SimpleNamespace(), [r], user, request=SimpleNamespace())
    assert group.vendor == "acme"
    assert len(group.versions) == 1
    monkeypatch.setattr(utils, "get_resource_data", original_get_resource_data)

    r2 = _resource(public=True)
    info2 = r2.get_processed_info()
    info2.longdescription = ""
    r2.get_processed_info = lambda request=None: info2
    none_user_data = await utils.get_resource_data(SimpleNamespace(), r2, None, request=SimpleNamespace())
    assert none_user_data.permissions.uninstall is False

    r3 = _resource(public=True)
    info3 = r3.get_processed_info()
    info3.longdescription = "docs/missing.md"
    r3.get_processed_info = lambda request=None: info3
    monkeypatch.setattr(utils, "download_local_file", lambda _path: (_ for _ in ()).throw(IOError("missing")))
    fallback_data = await utils.get_resource_data(SimpleNamespace(), r3, None, request=SimpleNamespace())
    assert fallback_data.longdescription == "Desc"

    r4 = _resource(public=True)
    info4 = r4.get_processed_info()
    info4.longdescription = "docs/existing.md"
    r4.get_processed_info = lambda request=None: info4

    def _localized_then_default(path):
        if path.endswith(".en.md"):
            raise IOError("localized missing")
        return b"# default"

    monkeypatch.setattr(utils, "download_local_file", _localized_then_default)
    second_path_data = await utils.get_resource_data(SimpleNamespace(), r4, None, request=SimpleNamespace())
    assert second_path_data.longdescription.startswith("clean:")


async def test_get_latest_resource_version_and_vendor_perms(monkeypatch):
    resources = [
        SimpleNamespace(version="1.0.0"),
        SimpleNamespace(version="2.0.0"),
        SimpleNamespace(version="1.5.0"),
    ]
    monkeypatch.setattr(utils, "get_all_catalogue_resource_versions", lambda *_a, **_k: _async_value(resources))
    latest = await utils.get_latest_resource_version(SimpleNamespace(), "widget", "acme")
    assert latest.version == "2.0.0"

    monkeypatch.setattr(utils, "get_all_catalogue_resource_versions", lambda *_a, **_k: _async_value([]))
    assert await utils.get_latest_resource_version(SimpleNamespace(), "widget", "acme") is None

    assert await utils.check_vendor_permissions(SimpleNamespace(), None, " acme ") is False
    assert await utils.check_vendor_permissions(SimpleNamespace(), SimpleNamespace(username="AcMe"), " acme ") is True


async def _async_value(value):
    return value


async def test_update_resource_catalogue_cache_and_creation_helpers(monkeypatch, tmp_path):
    updated = {"count": 0, "deleted": 0, "commits": 0, "widgets": 0}

    resource_wgt = SimpleNamespace(
        id="507f1f77bcf86cd799439011",
        vendor="acme",
        short_name="widget",
        version="1.0.0",
        template_uri="widget.wgt",
        fromWGT=True,
        resource_type=lambda: "widget",
    )
    resource_http = SimpleNamespace(
        id="507f1f77bcf86cd799439012",
        vendor="acme",
        short_name="operator",
        version="2.0.0",
        template_uri="http://example.com/template.xml",
        fromWGT=False,
        resource_type=lambda: "operator",
    )

    monkeypatch.setattr(utils, "get_all_catalogue_resources", lambda _db: _async_value([resource_wgt, resource_http]))
    monkeypatch.setattr(utils.wgt_deployer, "get_base_dir", lambda *_a: str(tmp_path))

    class _Wgt:
        def __init__(self, _path):
            pass

        def get_template(self):
            return "tpl"

        def close(self):
            return None

    monkeypatch.setattr(utils, "WgtFile", _Wgt)
    monkeypatch.setattr(utils, "download_http_content", lambda _url: "tpl-http")
    monkeypatch.setattr(utils, "TemplateParser", lambda _tpl: SimpleNamespace(get_resource_info=lambda: MACDWidget.model_validate(_macd_widget_dict())))

    async def _update_desc(_db, _rid, _desc):
        updated["count"] += 1

    async def _delete(_db, _ids):
        updated["deleted"] = len(_ids)

    async def _commit(_db):
        updated["commits"] += 1

    async def _create_widget(_db, _wgt):
        updated["widgets"] += 1

    monkeypatch.setattr(utils, "update_catalogue_resource_description", _update_desc)
    monkeypatch.setattr(utils, "delete_catalogue_resources", _delete)
    monkeypatch.setattr(utils, "commit", _commit)
    monkeypatch.setattr(utils, "create_widget_from_wgt", _create_widget)

    await utils.update_resource_catalogue_cache(SimpleNamespace())
    assert updated["count"] == 2
    assert updated["deleted"] == 0
    assert updated["commits"] == 1

    await utils.create_widget_on_resource_creation(SimpleNamespace(), resource_wgt)
    assert updated["widgets"] == 1
    await utils.create_widget_on_resource_creation(SimpleNamespace(), SimpleNamespace(resource_type=lambda: "operator"))

    deployed = {"n": 0}
    monkeypatch.setattr("wirecloud.platform.widget.utils.wgt_deployer", SimpleNamespace(deploy=lambda _wgt: deployed.__setitem__("n", deployed["n"] + 1)))
    utils.deploy_operators_on_resource_creation(resource_http)
    assert deployed["n"] == 1
    utils.deploy_operators_on_resource_creation(SimpleNamespace(resource_type=lambda: "widget"))


async def test_update_resource_catalogue_cache_removal_paths(monkeypatch):
    bad_resource = SimpleNamespace(
        id="507f1f77bcf86cd799439099",
        vendor="acme",
        short_name="bad",
        version="9.9.9",
        template_uri="missing.wgt",
        fromWGT=True,
    )

    monkeypatch.setattr(utils, "get_all_catalogue_resources", lambda _db: _async_value([bad_resource]))
    monkeypatch.setattr(utils.wgt_deployer, "get_base_dir", lambda *_a: "/tmp")

    class _WgtErr:
        def __init__(self, _path):
            err = IOError("missing")
            err.errno = errno.ENOENT
            raise err

    monkeypatch.setattr(utils, "WgtFile", _WgtErr)
    monkeypatch.setattr(utils.settings, "WIRECLOUD_REMOVE_UNSUPPORTED_RESOURCES_MIGRATION", False, raising=False)

    with pytest.raises(Exception):
        await utils.update_resource_catalogue_cache(SimpleNamespace())

    removed = {"n": 0}

    async def _delete(_db, ids):
        removed["n"] = len(ids)

    async def _commit(_db):
        return None

    monkeypatch.setattr(utils.settings, "WIRECLOUD_REMOVE_UNSUPPORTED_RESOURCES_MIGRATION", True, raising=False)
    monkeypatch.setattr(utils, "delete_catalogue_resources", _delete)
    monkeypatch.setattr(utils, "commit", _commit)

    await utils.update_resource_catalogue_cache(SimpleNamespace())
    assert removed["n"] == 1

    class _WgtErrOther:
        def __init__(self, _path):
            err = IOError("other")
            err.errno = errno.EPERM
            raise err

    monkeypatch.setattr(utils, "WgtFile", _WgtErrOther)
    with pytest.raises(IOError):
        await utils.update_resource_catalogue_cache(SimpleNamespace())
