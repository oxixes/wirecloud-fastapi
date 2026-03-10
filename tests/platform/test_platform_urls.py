# -*- coding: utf-8 -*-

from wirecloud.platform import urls
from wirecloud.platform.plugins import URLTemplate


def test_platform_url_patterns_shape():
    assert "wirecloud.root" in urls.patterns
    assert "wirecloud.workspace_view" in urls.patterns
    assert "wirecloud.search_service" in urls.patterns

    root = urls.patterns["wirecloud.root"]
    workspace = urls.patterns["wirecloud.workspace_view"]

    assert isinstance(root, URLTemplate)
    assert root.urlpattern == "/"
    assert root.defaults == {}
    assert workspace.urlpattern == "/workspace/{owner}/{name}"
