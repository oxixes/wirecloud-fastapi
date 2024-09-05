# -*- coding: utf-8 -*-

# Copyright (c) 2011-2016 CoNWeT Lab., Universidad Politécnica de Madrid

# This file is part of Wirecloud.

# Wirecloud is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# Wirecloud is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with Wirecloud.  If not, see <http://www.gnu.org/licenses/>.

from src.wirecloud.platform.plugins import URLTemplate

patterns: dict[str, URLTemplate] = {
    # Resources
    'wirecloud_catalogue.unversioned_resource_entry': URLTemplate(urlpattern='/catalogue/resource/{vendor}/{name}',
                                                                  defaults={}),
    'wirecloud_catalogue.resource_entry': URLTemplate(urlpattern='/catalogue/resource/{vendor}/{name}/{version}',
                                                      defaults={}),
    'wirecloud_catalogue.resource_changelog_entry': URLTemplate(urlpattern='/catalogue/resource/{vendor}/{name}/{version}/changelog',
                                                                defaults={}),
    'wirecloud_catalogue.resource_userguide_entry': URLTemplate(urlpattern='/catalogue/resource/{vendor}/{name}/{version}/userguide',
                                                                defaults={}),
    'wirecloud_catalogue.resource_versions_collection': URLTemplate(urlpattern='/catalogue/resource/{vendor}/{name}',
                                                                    defaults={}),
    'wirecloud_catalogue.resource_collection': URLTemplate(urlpattern='/catalogue/resources', defaults={}),

    # Version check
    # FIXME: The version check does not seem to be used. It could be removed
    'wirecloud_catalogue.resource_versions': URLTemplate(urlpattern='/catalogue/versions', defaults={}),
    'wirecloud_catalogue.media': URLTemplate(urlpattern='/catalogue/media/{vendor}/{name}/{version}/{file_path}',
                                             defaults={})
}