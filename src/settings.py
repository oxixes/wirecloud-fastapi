# -*- coding: utf-8 -*-

# Copyright (c) 2024 Future Internet Consulting and Development Solutions S.L.

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


from os import path, pardir
from aiocache import caches

DEBUG = True
BASEDIR = path.abspath(path.join(path.dirname(path.abspath(__file__)), pardir))

# TODO If platform is installed, the proxy has to be installed too
INSTALLED_APPS = (
    'wirecloud.commons',
    'wirecloud.platform',
    'wirecloud.catalogue',
    'wirecloud.proxy'
)

DATABASE = {
    'DRIVER': 'mongodb',
    'NAME': 'wirecloud_fastapi',
    'HOST': 'localhost',
    'PORT': '',
    'USER': '',
    'PASSWORD': ''
}

LANGUAGES = (
    ('es', 'Spanish'),
    ('en', 'English'),
    ('pt', 'Portuguese'),
)

DEFAULT_LANGUAGE = 'en'

# Make this unique, and don't share it with anybody.
JWT_KEY = '15=7f)g=)&spodi3bg8%&4fqt%f3rpg%b$-aer5*#a*(rqm79e'

SESSION_AGE = 60 * 60 * 24 * 14  # 2 weeks

CATALOGUE_MEDIA_ROOT = path.join(BASEDIR, 'catalogue', 'media')
CACHE_DIR = path.join(BASEDIR, 'cache')

WIRECLOUD_HTTPS_VERIFY = True

AVAILABLE_THEMES = [
    "defaulttheme"
]
THEME_ACTIVE = "defaulttheme"

# TODO Allow to define a list of known proxies to trust the X-Forwarded-For header
PROXY_WS_MAX_MSG_SIZE = 4 * 1024 * 1024 # 4MiB

caches.set_config({
    'default': {
        'cache': 'aiocache.SimpleMemoryCache',
        'ttl': 3600
    }
})
cache = caches.get('default')

SECRET_KEY = 'NeQM1I5g)ihQ3m#u!7Q£-1Jj3LuO?O4^'

WIDGET_DEPLOYMENT_DIR = path.join(BASEDIR, 'deployment', 'widgets')