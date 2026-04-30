# -*- coding: utf-8 -*-

from types import SimpleNamespace

import pytest
from fastapi import Response
from starlette.requests import Request

from wirecloud.commons.utils.template import UnsupportedFeature
from wirecloud.platform.widget import utils


def _request(path="/api/widget/acme/test/1.0/html", query=""):
    req = Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": "GET",
            "scheme": "https",
            "server": ("wirecloud.example.org", 443),
            "path": path,
            "query_string": query.encode("utf-8"),
            "headers": [(b"host", b"wirecloud.example.org")],
        }
    )
    req.state.lang = "en"
    return req


def test_get_html_error_response(monkeypatch):
    monkeypatch.setattr("wirecloud.platform.routes.render_wirecloud", lambda *_args, **_kwargs: SimpleNamespace(body=b"<html>err</html>"))
    html = utils.get_html_error_response(_request(), "text/html; charset=utf-8", 500, {"error_msg": "boom"})
    assert html == "<html>err</html>"


def test_small_helpers():
    requirements = [SimpleNamespace(name="featureA"), SimpleNamespace(name="featureB")]
    assert utils.process_requirements(requirements) == {"featureA": {}, "featureB": {}}
    assert utils.add_query_param("https://example.org/file.js?a=1", "context", "widget").endswith("a=1&context=widget")


async def test_get_or_add_widget_from_catalogue(monkeypatch, db_session):
    available_resource = SimpleNamespace(id="r1", is_available_for=lambda _user: True)
    blocked_resource = SimpleNamespace(id="r2", is_available_for=lambda _user: False)

    async def _resources(*_args, **_kwargs):
        return [blocked_resource, available_resource]

    async def _widget(*_args, **_kwargs):
        return SimpleNamespace(resource="r1")

    monkeypatch.setattr(utils, "get_catalogue_resources_with_regex", _resources)
    monkeypatch.setattr(utils, "get_widget_from_resource", _widget)

    found = await utils.get_or_add_widget_from_catalogue(db_session, "acme", "test", "1.0", object())
    assert found[0].resource == "r1"
    assert found[1].id == "r1"

    async def _blocked_only(*_args, **_kwargs):
        return [blocked_resource]

    monkeypatch.setattr(utils, "get_catalogue_resources_with_regex", _blocked_only)
    missing = await utils.get_or_add_widget_from_catalogue(db_session, "acme", "test", "1.0", object())
    assert missing is None


def test_xpath_with_and_without_namespace():
    tree_no_ns = utils.etree.parse(utils.BytesIO(b"<html><head><title>X</title></head></html>"), utils.etree.HTMLParser())
    title_no_ns = utils.xpath(tree_no_ns, "/xhtml:html/xhtml:head/xhtml:title/text()", None)
    assert title_no_ns[0] == "X"

    xml = b'<html xmlns="http://www.w3.org/1999/xhtml"><head><title>Y</title></head></html>'
    tree_ns = utils.etree.parse(utils.BytesIO(xml), utils.etree.XMLParser())
    title_ns = utils.xpath(tree_ns, "/xhtml:html/xhtml:head/xhtml:title/text()", "http://www.w3.org/1999/xhtml")
    assert title_ns[0] == "Y"


def test_get_widget_platform_style(monkeypatch):
    monkeypatch.setattr(utils.settings, "DEBUG", False)
    monkeypatch.setattr(utils, "get_static_path", lambda theme, *_args, **_kwargs: f"/static/{theme}/css/cache.css")
    utils._widget_platform_style.clear()

    request = _request()
    first = utils.get_widget_platform_style(request, "wirecloud.defaulttheme")
    second = utils.get_widget_platform_style(request, "wirecloud.defaulttheme")
    assert first == second
    assert first[0].endswith("context=widget")

    monkeypatch.setattr(utils.settings, "DEBUG", True)
    refreshed = utils.get_widget_platform_style(request, "wirecloud.defaulttheme")
    assert refreshed[0].endswith("context=widget")


async def test_get_widget_api_files(monkeypatch):
    class _Cache:
        def __init__(self):
            self.data = {}

        async def get(self, key):
            return self.data.get(key)

        async def set(self, key, value):
            self.data[key] = value

    cache = _Cache()
    monkeypatch.setattr(utils, "cache", cache)
    monkeypatch.setattr("wirecloud.platform.core.plugins.get_version_hash", lambda: "vhash")
    monkeypatch.setattr(utils, "get_current_domain", lambda _request: "wirecloud.example.org")
    monkeypatch.setattr(
        utils,
        "get_absolute_static_url",
        lambda path, request=None, versioned=False: f"https://wirecloud.example.org/{path}?v=1" if versioned else f"https://wirecloud.example.org/{path}",
    )
    monkeypatch.setattr(utils.settings, "DEBUG", False)

    request = _request()
    generated = await utils.get_widget_api_files(request, "defaulttheme")
    assert generated[0].startswith("https://wirecloud.example.org/")

    cached = await utils.get_widget_api_files(request, "defaulttheme")
    assert cached == generated

    monkeypatch.setattr(utils.settings, "DEBUG", True)
    refreshed = await utils.get_widget_api_files(request, "defaulttheme")
    assert refreshed == generated


@pytest.mark.parametrize(
    "content_type",
    ["text/plain", "application/json"],
)
async def test_fix_widget_code_non_markup_passthrough(content_type):
    request = _request()
    raw = b'{"a":1}'
    processed = await utils.fix_widget_code(raw, content_type, request, "utf-8", False, "", {}, "classic", "defaulttheme", 1, "acme", "test", "1.0")
    assert processed == raw


async def test_fix_widget_code_html_and_xhtml_branches(monkeypatch):
    request = _request()
    monkeypatch.setattr(utils, "get_absolute_reverse_url", lambda *_args, **_kwargs: "https://wirecloud.example.org/showcase/media/acme/test/1.0/")
    monkeypatch.setattr(
        utils,
        "get_absolute_static_url",
        lambda path, request=None, versioned=False: f"https://wirecloud.example.org/{path}",
    )
    monkeypatch.setattr(utils, "get_widget_api_extensions", lambda *_args, **_kwargs: ["js/ext-a.js", "js/ext-b.js"])

    async def _api_files(*_args, **_kwargs):
        return ["https://wirecloud.example.org/static/js/widget-api.js"]

    monkeypatch.setattr(utils, "get_widget_api_files", _api_files)
    monkeypatch.setattr(utils, "get_widget_platform_style", lambda *_args, **_kwargs: ("https://wirecloud.example.org/static/css/widget.css",))

    html = b"<html><head><base href='x'><base href='y'><script src='a.js'></script><script>inline</script></head><body>ok</body></html>"
    fixed_html = await utils.fix_widget_code(
        html,
        "text/html",
        request,
        "utf-8",
        True,
        "index.html",
        {"feature": {}},
        "classic",
        "defaulttheme",
        1,
        "acme",
        "test",
        "1.0",
    )
    decoded = fixed_html.decode("utf-8")
    assert "WirecloudAPIClosure.js" in decoded
    assert "widget.css" in decoded
    assert "showcase/media/acme/test/1.0" in decoded
    assert "href=\"x\"" not in decoded
    assert "href=\"y\"" not in decoded
    assert decoded.count("<base ") == 1

    xhtml = b'<html xmlns="http://www.w3.org/1999/xhtml"><body/></html>'
    fixed_xhtml = await utils.fix_widget_code(
        xhtml,
        "application/xhtml+xml",
        request,
        "utf-8",
        False,
        "",
        {},
        "classic",
        "defaulttheme",
        2,
        "acme",
        "test",
        "1.0",
    )
    assert b"<head" in fixed_xhtml

    empty_markup = await utils.fix_widget_code(
        b"",
        "text/html",
        request,
        "utf-8",
        False,
        "",
        {},
        "classic",
        "defaulttheme",
        2,
        "acme",
        "test",
        "1.0",
    )
    assert b"<html" in empty_markup.lower()


async def test_process_widget_code_cache_hit(monkeypatch, db_session):
    class _Cache:
        async def get(self, _key):
            return {"code": b"<html/>", "content_type": "text/html; charset=utf-8", "timestamp": 1, "timeout": 10}

        async def set(self, *_args, **_kwargs):
            raise AssertionError("cache.set should not be called")

    patched = {"n": 0}

    def _patch_headers(response, *_args):
        patched["n"] += 1
        response.headers["x-cache"] = "hit"

    monkeypatch.setattr(utils, "cache", _Cache())
    monkeypatch.setattr(utils, "patch_cache_headers", _patch_headers)
    monkeypatch.setattr(utils, "get_current_domain", lambda _request: "wirecloud.example.org")

    resource = SimpleNamespace(
        id="rid",
        description=SimpleNamespace(contents=SimpleNamespace(cacheable=True, contenttype="text/html", charset="utf-8"), requirements=[]),
        xhtml=SimpleNamespace(get_cache_key=lambda *_args: "key", code="ignored", cacheable=True, code_timestamp=1, use_platform_style=False, url="widget.html"),
    )
    response = await utils.process_widget_code(db_session, _request(), resource, "classic", None)
    assert response.status_code == 200
    assert patched["n"] == 1


async def test_process_widget_code_error_paths(monkeypatch, db_session):
    class _Cache:
        async def get(self, _key):
            return None

        async def set(self, *_args, **_kwargs):
            return None

    monkeypatch.setattr(utils, "cache", _Cache())
    monkeypatch.setattr(utils, "get_current_domain", lambda _request: "wirecloud.example.org")
    monkeypatch.setattr(utils, "get_current_theme", lambda _request: "defaulttheme")
    monkeypatch.setattr(utils, "build_response", lambda _request, status, payload, _formatters: Response(status_code=status, content=str(payload)))

    resource = SimpleNamespace(
        id="rid",
        get_processed_info=lambda **_kwargs: SimpleNamespace(macversion=1, vendor="acme", name="test", version="1.0", contents=SimpleNamespace(src="index.html")),
        description=SimpleNamespace(contents=SimpleNamespace(cacheable=True, contenttype="text/html", charset="utf-8"), requirements=[]),
        xhtml=SimpleNamespace(
            get_cache_key=lambda *_args: "key",
            code="",
            cacheable=True,
            code_timestamp=None,
            use_platform_style=False,
            url="missing.html",
        ),
    )

    err = IOError("missing")
    err.errno = utils.errno.ENOENT
    monkeypatch.setattr(utils, "download_local_file", lambda *_args, **_kwargs: (_ for _ in ()).throw(err))
    not_found = await utils.process_widget_code(db_session, _request(), resource, "classic", None)
    assert not_found.status_code == 404

    monkeypatch.setattr(utils, "download_local_file", lambda *_args, **_kwargs: b"\xff")
    bad_charset = await utils.process_widget_code(db_session, _request(), resource, "classic", None)
    assert bad_charset.status_code == 502

    monkeypatch.setattr(utils, "download_local_file", lambda *_args, **_kwargs: b"<html></html>")
    async def _save_xhtml(*_args, **_kwargs):
        return None

    monkeypatch.setattr(utils, "save_catalogue_resource_xhtml", _save_xhtml)

    async def _raise_unicode(*_args, **_kwargs):
        raise UnicodeDecodeError("utf-8", b"\xff", 0, 1, "boom")

    monkeypatch.setattr(utils, "fix_widget_code", _raise_unicode)
    unicode_err = await utils.process_widget_code(db_session, _request(), resource, "classic", None)
    assert unicode_err.status_code == 502

    async def _raise_generic(*_args, **_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(utils, "fix_widget_code", _raise_generic)
    generic_err = await utils.process_widget_code(db_session, _request(), resource, "classic", None)
    assert generic_err.status_code == 502

    non_cacheable = SimpleNamespace(
        id="rid-non-cache",
        get_processed_info=lambda **_kwargs: SimpleNamespace(macversion=1, vendor="acme", name="test", version="1.0", contents=SimpleNamespace(src="index.html")),
        description=SimpleNamespace(contents=SimpleNamespace(cacheable=False, contenttype="text/html", charset="utf-8"), requirements=[]),
        xhtml=SimpleNamespace(
            get_cache_key=lambda *_args: "unused",
            code="",
            cacheable=False,
            code_timestamp=None,
            use_platform_style=False,
            url="missing.html",
        ),
    )

    monkeypatch.setattr(utils, "download_local_file", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("boom")))

    async def _fixed_non_enoent(*_args, **_kwargs):
        return b"<html>fallback</html>"

    monkeypatch.setattr(utils, "fix_widget_code", _fixed_non_enoent)
    non_enoent = await utils.process_widget_code(db_session, _request(), non_cacheable, "classic", None)
    assert non_enoent.status_code == 200


async def test_process_widget_code_success_paths(monkeypatch, db_session):
    class _Cache:
        def __init__(self):
            self.saved = []

        async def get(self, _key):
            return None

        async def set(self, key, value, timeout=None):
            self.saved.append((key, value, timeout))

    cache = _Cache()
    patched = {"n": 0}

    monkeypatch.setattr(utils, "cache", cache)
    monkeypatch.setattr(utils, "get_current_domain", lambda _request: "wirecloud.example.org")
    monkeypatch.setattr(utils, "patch_cache_headers", lambda *_args, **_kwargs: patched.__setitem__("n", patched["n"] + 1))
    monkeypatch.setattr(utils, "get_current_theme", lambda _request: "defaulttheme")
    monkeypatch.setattr(utils, "save_catalogue_resource_xhtml", lambda *_args, **_kwargs: None)

    async def _fixed(code, *_args, **_kwargs):
        return code

    monkeypatch.setattr(utils, "fix_widget_code", _fixed)

    resource = SimpleNamespace(
        id="rid",
        get_processed_info=lambda **_kwargs: SimpleNamespace(macversion=1, vendor="acme", name="test", version="1.0", contents=SimpleNamespace(src="index.html")),
        description=SimpleNamespace(contents=SimpleNamespace(cacheable=True, contenttype="text/html", charset="utf-8"), requirements=[]),
        xhtml=SimpleNamespace(
            get_cache_key=lambda *_args: "cache-key",
            code="<html>cached</html>",
            cacheable=True,
            code_timestamp=123,
            use_platform_style=False,
            url="widget.html",
        ),
    )
    response = await utils.process_widget_code(db_session, _request(), resource, "classic", None)
    assert response.status_code == 200
    assert len(cache.saved) == 1
    assert patched["n"] == 1

    non_cacheable = SimpleNamespace(
        id="rid2",
        get_processed_info=lambda **_kwargs: SimpleNamespace(macversion=1, vendor="acme", name="test", version="1.0", contents=SimpleNamespace(src="index.html")),
        description=SimpleNamespace(contents=SimpleNamespace(cacheable=False, contenttype="text/html", charset="utf-8"), requirements=[]),
        xhtml=SimpleNamespace(
            get_cache_key=lambda *_args: "unused",
            code="",
            cacheable=False,
            code_timestamp=321,
            use_platform_style=False,
            url="widget.html",
        ),
    )
    monkeypatch.setattr(utils, "download_local_file", lambda *_args, **_kwargs: b"<html>from-file</html>")
    response_non_cacheable = await utils.process_widget_code(db_session, _request(), non_cacheable, "classic", "defaulttheme")
    assert response_non_cacheable.status_code == 200


def test_check_requirements(monkeypatch):
    monkeypatch.setattr(utils, "get_active_features", lambda: {"featureA"})
    ok_resource = SimpleNamespace(requirements=[SimpleNamespace(type="feature", name="featureA")])
    utils.check_requirements(ok_resource)

    missing_resource = SimpleNamespace(requirements=[SimpleNamespace(type="feature", name="featureB")])
    with pytest.raises(UnsupportedFeature, match="featureB"):
        utils.check_requirements(missing_resource)

    unsupported_type = SimpleNamespace(requirements=[SimpleNamespace(type="other", name="x")])
    with pytest.raises(UnsupportedFeature, match="Unsupported requirement type"):
        utils.check_requirements(unsupported_type)


async def test_create_widget_from_wgt(monkeypatch, db_session):
    class _Template:
        def __init__(self, resource_type):
            self.resource_type = resource_type

        def get_resource_type(self):
            return self.resource_type

        def get_resource_info(self):
            return SimpleNamespace(contents=SimpleNamespace(src="index.html", contenttype="text/html", useplatformstyle=True, cacheable=True))

        def get_resource_vendor(self):
            return "acme"

        def get_resource_name(self):
            return "test"

        def get_resource_version(self):
            return "1.0"

        def get_absolute_url(self, _src):
            return "/widgets/acme/test/1.0/index.html"

    monkeypatch.setattr(utils.wgt_deployer, "deploy", lambda _wgt_file: _Template("other"))
    with pytest.raises(Exception):
        await utils.create_widget_from_wgt(db_session, object())

    monkeypatch.setattr(utils.wgt_deployer, "deploy", lambda _wgt_file: _Template(utils.MACType.widget))
    deploy_only = await utils.create_widget_from_wgt(db_session, object(), deploy_only=True)
    assert deploy_only is None

    saved = {"n": 0}
    monkeypatch.setattr(utils, "check_requirements", lambda *_args, **_kwargs: None)

    async def _get_catalogue(*_args, **_kwargs):
        return SimpleNamespace(id="rid", xhtml=None)

    monkeypatch.setattr(utils, "get_catalogue_resource_with_xhtml", _get_catalogue)

    async def _save(*_args, **_kwargs):
        saved["n"] += 1

    monkeypatch.setattr(utils, "save_catalogue_resource_xhtml", _save)
    widget = await utils.create_widget_from_wgt(db_session, object(), deploy_only=False)
    assert widget.id == "rid"
    assert saved["n"] == 1
