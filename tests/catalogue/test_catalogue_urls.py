# -*- coding: utf-8 -*-

from wirecloud.catalogue import urls


async def test_catalogue_url_patterns():
    assert "wirecloud_catalogue.resource_collection" in urls.patterns
    assert "wirecloud_catalogue.media" in urls.patterns

    media = urls.patterns["wirecloud_catalogue.media"]
    assert media.urlpattern == "/catalogue/media/{vendor}/{name}/{version}/{file_path:path}"
    assert media.defaults == {}
