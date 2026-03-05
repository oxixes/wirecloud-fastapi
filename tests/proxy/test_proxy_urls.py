# -*- coding: utf-8 -*-

from wirecloud.proxy import urls


async def test_proxy_url_patterns():
    assert "wirecloud|proxy" in urls.patterns
    pattern = urls.patterns["wirecloud|proxy"]
    assert pattern.urlpattern == "/cdp/{protocol}/{domain}/{path:path}"
    assert pattern.defaults == {}
