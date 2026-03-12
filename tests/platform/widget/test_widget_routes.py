# -*- coding: utf-8 -*-

from datetime import datetime, timezone
from types import SimpleNamespace

from fastapi import Response
from starlette.requests import Request

from wirecloud import main as main_module
from wirecloud.platform.widget import routes


async def _noop_close():
    return None


main_module.close = _noop_close


def _request(path="/api/widget/missing_widget", query=""):
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


def _resource(resource_type="widget"):
    return SimpleNamespace(
        creation_date=datetime.now(timezone.utc),
        resource_type=lambda: resource_type,
    )


async def test_get_widget_html_branches(app_client, monkeypatch):
    async def _none(*_args, **_kwargs):
        return None

    monkeypatch.setattr(routes, "get_catalogue_resource_with_xhtml", _none)
    not_found = await app_client.get("/api/widget/acme/test/1.0/html")
    assert not_found.status_code == 404

    async def _operator(*_args, **_kwargs):
        return _resource("operator")

    monkeypatch.setattr(routes, "get_catalogue_resource_with_xhtml", _operator)
    wrong_type = await app_client.get("/api/widget/acme/test/1.0/html")
    assert wrong_type.status_code == 404

    async def _widget(*_args, **_kwargs):
        return _resource("widget")

    monkeypatch.setattr(routes, "get_catalogue_resource_with_xhtml", _widget)
    monkeypatch.setattr(routes, "check_if_modified_since", lambda *_args, **_kwargs: False)
    patched = {"n": 0}

    def _patch_headers(response, _creation_date):
        patched["n"] += 1
        response.headers["x-cache"] = "patched"

    monkeypatch.setattr(routes, "patch_cache_headers", _patch_headers)
    not_modified = await app_client.get("/api/widget/acme/test/1.0/html")
    assert not_modified.status_code == 304
    assert patched["n"] == 1

    monkeypatch.setattr(routes, "check_if_modified_since", lambda *_args, **_kwargs: True)

    async def _process(*_args, **_kwargs):
        return Response(status_code=200, content="ok-widget")

    monkeypatch.setattr(routes, "process_widget_code", _process)
    ok = await app_client.get("/api/widget/acme/test/1.0/html")
    assert ok.status_code == 200
    assert ok.text == "ok-widget"


async def test_get_widget_file_branches(app_client, monkeypatch):
    monkeypatch.setattr(routes, "build_error_response", lambda _request, status, _message: Response(status_code=status))

    blocked = await app_client.get("/showcase/media/acme/test/1.0/%2E%2E")
    assert blocked.status_code == 404

    async def _none(*_args, **_kwargs):
        return None

    monkeypatch.setattr(routes, "get_catalogue_resource_with_xhtml", _none)
    missing = await app_client.get("/showcase/media/acme/test/1.0/index.html")
    assert missing.status_code == 404

    async def _invalid(*_args, **_kwargs):
        return _resource("mashup")

    monkeypatch.setattr(routes, "get_catalogue_resource_with_xhtml", _invalid)
    invalid = await app_client.get("/showcase/media/acme/test/1.0/index.html")
    assert invalid.status_code == 404

    async def _widget(*_args, **_kwargs):
        return _resource("widget")

    monkeypatch.setattr(routes, "get_catalogue_resource_with_xhtml", _widget)
    monkeypatch.setattr(routes, "check_if_modified_since", lambda *_args, **_kwargs: False)
    not_modified = await app_client.get("/showcase/media/acme/test/1.0/index.html")
    assert not_modified.status_code == 304

    monkeypatch.setattr(routes, "check_if_modified_since", lambda *_args, **_kwargs: True)

    async def _process(*_args, **_kwargs):
        return Response(status_code=206, content="entrypoint")

    monkeypatch.setattr(routes, "process_widget_code", _process)
    entrypoint = await app_client.get("/showcase/media/acme/test/1.0/index.html?entrypoint=true")
    assert entrypoint.status_code == 206

    monkeypatch.setattr(routes, "process_widget_code", lambda *_args, **_kwargs: Response(status_code=500))
    monkeypatch.setattr(routes, "build_downloadfile_response", lambda *_args, **_kwargs: Response(status_code=200))
    monkeypatch.setattr(routes.showcase_utils.wgt_deployer, "get_base_dir", lambda *_args, **_kwargs: "/tmp/deploy")
    plain = await app_client.get("/showcase/media/acme/test/1.0/assets/logo.png")
    assert plain.status_code == 200

    class _CatalogueDeployer:
        @staticmethod
        def get_base_dir(*_args, **_kwargs):
            return "/tmp/catalogue"

    monkeypatch.setattr("wirecloud.catalogue.utils.wgt_deployer", _CatalogueDeployer)
    monkeypatch.setattr(
        routes,
        "build_downloadfile_response",
        lambda *_args, **_kwargs: Response(status_code=302, headers={"Location": "bundle.wgt"}),
    )
    monkeypatch.setattr(routes, "get_absolute_reverse_url", lambda *_args, **_kwargs: "https://wirecloud.example.org/showcase/media/acme/test/1.0/bundle.wgt")
    redirect = await app_client.get("/showcase/media/acme/test/1.0/package.wgt")
    assert redirect.status_code == 302
    assert redirect.headers["location"].endswith("/bundle.wgt")


async def test_get_missing_widget_html(app_client, monkeypatch):
    class _Templates:
        def TemplateResponse(self, name, context):
            return Response(status_code=200, content=f"{name}|{context['THEME']}".encode("utf-8"))

    monkeypatch.setattr(routes, "get_current_theme", lambda _request: "wirecloud.defaulttheme")
    monkeypatch.setattr(routes, "get_current_view", lambda _request: "classic")
    monkeypatch.setattr(routes, "get_jinja2_templates", lambda _theme: _Templates())
    monkeypatch.setattr(routes, "get_widget_platform_style", lambda *_args, **_kwargs: ("style.css",))
    monkeypatch.setattr(routes, "get_translation", lambda *_args, **_kwargs: "translated")
    monkeypatch.setattr(routes, "get_static_path", lambda *_args, **_kwargs: "/static/path")
    monkeypatch.setattr(routes, "get_url_from_view", lambda *_args, **_kwargs: "/view/url")
    monkeypatch.setattr("wirecloud.platform.core.plugins.get_version_hash", lambda: "vhash")

    auto_theme = await app_client.get("/api/widget/missing_widget")
    assert auto_theme.status_code == 200
    assert "wirecloud.defaulttheme" in auto_theme.text

    explicit_theme = await app_client.get("/api/widget/missing_widget?theme=custom.theme")
    assert explicit_theme.status_code == 200
    assert "custom.theme" in explicit_theme.text
