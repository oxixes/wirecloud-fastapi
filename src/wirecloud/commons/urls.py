# -*- coding: utf-8 -*-

# Copyright (c) 2012-2017 CoNWeT Lab., Universidad Politécnica de Madrid

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
    # Auth
    'login': URLTemplate(urlpattern='/login', defaults={}),
    'logout': URLTemplate(urlpattern='/logout', defaults={}),
    'wirecloud.login': URLTemplate(urlpattern='/api/login', defaults={}),
    
    # i18n
    'wirecloud.javascript_translation_catalogue': URLTemplate(urlpattern='/api/i18n/js_catalogue', defaults={}),

    # OAuth2
    'oauth.default_redirect_uri': URLTemplate(urlpattern='/oauth2/default_redirect_uri', defaults={}),
}