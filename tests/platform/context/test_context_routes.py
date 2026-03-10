# -*- coding: utf-8 -*-

import pytest

from wirecloud import main as main_module
from wirecloud.platform.context import routes
from wirecloud.platform.context.schemas import PlatformContextKey, WorkspaceContextKey


async def _noop_close():
    return None


main_module.close = _noop_close


@pytest.fixture(autouse=True)
def _patch_dependencies(monkeypatch):
    monkeypatch.setattr(routes, "get_platform_context", lambda *args, **kwargs: _platform_context())
    monkeypatch.setattr(
        routes,
        "get_workspace_context_definitions",
        lambda: {"workspace_title": WorkspaceContextKey(label="Workspace title", description="Workspace title desc")},
    )


async def _platform_context():
    return {
        "theme": PlatformContextKey(label="Theme", description="Theme desc", value="wirecloud.defaulttheme"),
        "username": PlatformContextKey(label="Username", description="Username desc", value="anonymous"),
    }


async def test_get_context_route_default_and_theme_override(app_client):
    response = await app_client.get("/api/context/")
    assert response.status_code == 200
    payload = response.json()
    assert payload["platform"]["theme"]["value"] == "wirecloud.defaulttheme"
    assert payload["platform"]["username"]["value"] == "anonymous"
    assert payload["workspace"]["workspace_title"]["label"] == "Workspace title"

    response_theme = await app_client.get("/api/context/?theme=custom-theme")
    assert response_theme.status_code == 200
    payload_theme = response_theme.json()
    assert payload_theme["platform"]["theme"]["value"] == "custom-theme"
