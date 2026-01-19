# -*- coding: utf-8 -*-
# Copyright (c) 2026 Future Internet Consulting and Development Solutions S.L.

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

import asyncio
import os
from os import path

from src import settings
from src.wirecloud.platform.plugins import get_config_validators


def _set_default_if_missing(attr: str, default_value):
    if not hasattr(settings, attr):
        setattr(settings, attr, default_value)


def _validate_and_set_defaults():
    # DEBUG (default: False)
    _set_default_if_missing('DEBUG', False)
    if not isinstance(settings.DEBUG, bool):
        raise ValueError("DEBUG must be a boolean")

    # BASEDIR (required)
    if not hasattr(settings, 'BASEDIR') or not settings.BASEDIR:
        raise ValueError("BASEDIR is required and must not be empty")

    if not isinstance(settings.BASEDIR, str):
        raise ValueError("BASEDIR must be a string")

    if not os.path.exists(settings.BASEDIR):
        raise ValueError(f"BASEDIR directory does not exist: {settings.BASEDIR}")

    # ALLOW_ANONYMOUS_ACCESS (default: False)
    _set_default_if_missing('ALLOW_ANONYMOUS_ACCESS', False)
    if not isinstance(settings.ALLOW_ANONYMOUS_ACCESS, bool):
        raise ValueError("ALLOW_ANONYMOUS_ACCESS must be a boolean")

    # INSTALLED_APPS (required)
    if not hasattr(settings, 'INSTALLED_APPS') or not settings.INSTALLED_APPS:
        raise ValueError("INSTALLED_APPS is required and must not be empty")

    if not isinstance(settings.INSTALLED_APPS, (list, tuple)):
        raise ValueError("INSTALLED_APPS must be a list or tuple")

    # DATABASE (required)
    if not hasattr(settings, 'DATABASE') or not settings.DATABASE:
        raise ValueError("DATABASE configuration is required")

    if not isinstance(settings.DATABASE, dict):
        raise ValueError("DATABASE must be a dictionary")

    required_db_fields = ['DRIVER', 'NAME', 'HOST']
    for field in required_db_fields:
        if field not in settings.DATABASE:
            raise ValueError(f"DATABASE.{field} is required")
        if not settings.DATABASE[field]:
            raise ValueError(f"DATABASE.{field} must not be empty")

    # Set default values for optional DATABASE fields
    if 'PORT' not in settings.DATABASE:
        settings.DATABASE['PORT'] = ''
    if 'USER' not in settings.DATABASE:
        settings.DATABASE['USER'] = ''
    if 'PASSWORD' not in settings.DATABASE:
        settings.DATABASE['PASSWORD'] = ''
    if 'USE_TRANSACTIONS' not in settings.DATABASE:
        settings.DATABASE['USE_TRANSACTIONS'] = True

    if not isinstance(settings.DATABASE['USE_TRANSACTIONS'], bool):
        raise ValueError("DATABASE.USE_TRANSACTIONS must be a boolean")

    # Validate DRIVER
    valid_drivers = ['mongodb', 'postgresql', 'mysql']
    if settings.DATABASE['DRIVER'] not in valid_drivers:
        raise ValueError(f"DATABASE.DRIVER must be one of: {', '.join(valid_drivers)}")

    # ELASTICSEARCH (required)
    if not hasattr(settings, 'ELASTICSEARCH') or not settings.ELASTICSEARCH:
        raise ValueError("ELASTICSEARCH configuration is required")

    if not isinstance(settings.ELASTICSEARCH, dict):
        raise ValueError("ELASTICSEARCH must be a dictionary")

    required_es_fields = ['HOST', 'PORT']
    for field in required_es_fields:
        if field not in settings.ELASTICSEARCH:
            raise ValueError(f"ELASTICSEARCH.{field} is required when ELASTICSEARCH is configured")

    if not isinstance(settings.ELASTICSEARCH['PORT'], int):
        raise ValueError("ELASTICSEARCH.PORT must be an integer")

    if settings.ELASTICSEARCH['PORT'] <= 0 or settings.ELASTICSEARCH['PORT'] > 65535:
        raise ValueError("ELASTICSEARCH.PORT must be between 1 and 65535")

    # Set defaults for optional fields
    if 'USER' not in settings.ELASTICSEARCH:
        settings.ELASTICSEARCH['USER'] = ''
    if 'PASSWORD' not in settings.ELASTICSEARCH:
        settings.ELASTICSEARCH['PASSWORD'] = ''
    if 'SECURE' not in settings.ELASTICSEARCH:
        settings.ELASTICSEARCH['SECURE'] = False

    if not isinstance(settings.ELASTICSEARCH['SECURE'], bool):
        raise ValueError("ELASTICSEARCH.SECURE must be a boolean")

    # LANGUAGES (required)
    if not hasattr(settings, 'LANGUAGES') or not settings.LANGUAGES:
        raise ValueError("LANGUAGES is required and must not be empty")

    if not isinstance(settings.LANGUAGES, (list, tuple)):
        raise ValueError("LANGUAGES must be a list or tuple")

    if len(settings.LANGUAGES) == 0:
        raise ValueError("LANGUAGES must contain at least one language")

    for lang in settings.LANGUAGES:
        if not isinstance(lang, tuple) or len(lang) != 2:
            raise ValueError("Each language in LANGUAGES must be a tuple of (code, name)")
        if not isinstance(lang[0], str) or not isinstance(lang[1], str):
            raise ValueError("Language code and name must be strings")

    # DEFAULT_LANGUAGE (required)
    if not hasattr(settings, 'DEFAULT_LANGUAGE') or not settings.DEFAULT_LANGUAGE:
        raise ValueError("DEFAULT_LANGUAGE is required")

    language_codes = [lang[0] for lang in settings.LANGUAGES]
    if settings.DEFAULT_LANGUAGE not in language_codes:
        raise ValueError(f"DEFAULT_LANGUAGE '{settings.DEFAULT_LANGUAGE}' is not in LANGUAGES")

    # JWT_KEY (required)
    if not hasattr(settings, 'JWT_KEY') or not settings.JWT_KEY:
        raise ValueError("JWT_KEY is required and must not be empty")

    if len(settings.JWT_KEY) < 32:
        print("WARNING: JWT_KEY should be at least 32 characters long for security")

    # SESSION_AGE (default: 2 weeks)
    _set_default_if_missing('SESSION_AGE', 60 * 60 * 24 * 14)

    if not isinstance(settings.SESSION_AGE, int) or settings.SESSION_AGE <= 0:
        raise ValueError("SESSION_AGE must be a positive integer")

    # SECRET_KEY (required)
    if not hasattr(settings, 'SECRET_KEY') or not settings.SECRET_KEY:
        raise ValueError("SECRET_KEY is required and must not be empty")

    if len(settings.SECRET_KEY) < 32:
        print("WARNING: SECRET_KEY should be at least 32 characters long for security")

    # === OpenID Connect Settings ===

    _set_default_if_missing('OID_CONNECT_ENABLED', False)
    if not isinstance(settings.OID_CONNECT_ENABLED, bool):
        raise ValueError("OID_CONNECT_ENABLED must be a boolean")

    if settings.OID_CONNECT_ENABLED:
        # Required when OIDC is enabled
        if not hasattr(settings, 'OID_CONNECT_CLIENT_ID') or not settings.OID_CONNECT_CLIENT_ID:
            raise ValueError("OID_CONNECT_CLIENT_ID is required when OID_CONNECT_ENABLED is True")

        if not hasattr(settings, 'OID_CONNECT_CLIENT_SECRET') or not settings.OID_CONNECT_CLIENT_SECRET:
            raise ValueError("OID_CONNECT_CLIENT_SECRET is required when OID_CONNECT_ENABLED is True")

        if not hasattr(settings, 'OID_CONNECT_PLUGIN') or not settings.OID_CONNECT_PLUGIN:
            raise ValueError("OID_CONNECT_PLUGIN is required when OID_CONNECT_ENABLED is True")

        # Validate plugin is in installed apps
        plugin_name = f"wirecloud.{settings.OID_CONNECT_PLUGIN}"
        if plugin_name not in settings.INSTALLED_APPS:
            raise ValueError(f"OID_CONNECT_PLUGIN '{settings.OID_CONNECT_PLUGIN}' plugin must be in INSTALLED_APPS")

        # Optional OIDC settings with defaults
        _set_default_if_missing('OID_CONNECT_FULLY_SYNC_GROUPS', False)
        _set_default_if_missing('OID_CONNECT_BACKCHANNEL_LOGOUT', False)

        if not isinstance(settings.OID_CONNECT_FULLY_SYNC_GROUPS, bool):
            raise ValueError("OID_CONNECT_FULLY_SYNC_GROUPS must be a boolean")

        if not isinstance(settings.OID_CONNECT_BACKCHANNEL_LOGOUT, bool):
            raise ValueError("OID_CONNECT_BACKCHANNEL_LOGOUT must be a boolean")

    # === Security Settings ===

    _set_default_if_missing('WIRECLOUD_HTTPS_VERIFY', True)
    if not isinstance(settings.WIRECLOUD_HTTPS_VERIFY, bool):
        raise ValueError("WIRECLOUD_HTTPS_VERIFY must be a boolean")

    # === Cache Settings ===

    # CACHE_DIR (default: BASEDIR/cache)
    _set_default_if_missing('CACHE_DIR', path.join(settings.BASEDIR, 'cache'))

    if not isinstance(settings.CACHE_DIR, str):
        raise ValueError("CACHE_DIR must be a string")

    # Validate cache configuration if present
    if hasattr(settings, 'cache'):
        # Cache configuration is validated by aiocache library itself
        pass


async def validate_settings(offline: bool = False):
    # Validate core settings and set defaults
    _validate_and_set_defaults()

    # Run plugin-specific validators
    validators = get_config_validators()
    for validator in validators:
        # Check if its synchronous
        if hasattr(validator, "__call__") and not asyncio.iscoroutinefunction(validator):
            validator(settings, offline)
        elif asyncio.iscoroutinefunction(validator):
            await validator(settings, offline)


def validate_plugins():
    # Validate core apps are installed
    required_apps = ['wirecloud.commons', 'wirecloud.catalogue']
    for app in required_apps:
        if app not in settings.INSTALLED_APPS:
            raise ValueError(f"Required app '{app}' must be in INSTALLED_APPS")

    if 'wirecloud.platform' in settings.INSTALLED_APPS and 'wirecloud.proxy' not in settings.INSTALLED_APPS:
        settings.INSTALLED_APPS = list(settings.INSTALLED_APPS) + ['wirecloud.proxy']