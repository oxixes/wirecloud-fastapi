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

from typing import Optional, Callable
import logging
from fastapi import FastAPI

from wirecloud.platform.plugins import WirecloudPlugin
from wirecloud.proxy.urls import patterns as proxy_patterns
from wirecloud.proxy.routes import router as proxy_router
from wirecloud.settings_validator import _set_default_if_missing

logger = logging.getLogger(__name__)


class WirecloudProxyPlugin(WirecloudPlugin):
    urls = proxy_patterns

    def __init__(self, app: Optional[FastAPI]):
        super().__init__(app)

        if app is None:
            return

        app.include_router(proxy_router, prefix="/cdp", tags=["Proxy"])

    def get_config_validators(self) -> tuple[Callable, ...]:
        def validate_proxy_settings(settings, _offline: bool) -> None:
            # PROXY_WS_MAX_MSG_SIZE (default: 4 MiB)
            if not hasattr(settings, 'PROXY_WS_MAX_MSG_SIZE'):
                setattr(settings, 'PROXY_WS_MAX_MSG_SIZE', 4 * 1024 * 1024)

            if not isinstance(settings.PROXY_WS_MAX_MSG_SIZE, int):
                raise ValueError("PROXY_WS_MAX_MSG_SIZE must be an integer")

            if settings.PROXY_WS_MAX_MSG_SIZE <= 0:
                raise ValueError("PROXY_WS_MAX_MSG_SIZE must be a positive integer")

            # Warn if the size is too large (> 100MB)
            if settings.PROXY_WS_MAX_MSG_SIZE > 100 * 1024 * 1024:
                logger.warning(f"PROXY_WS_MAX_MSG_SIZE is very large ({settings.PROXY_WS_MAX_MSG_SIZE} bytes). This may cause memory issues.")

            _set_default_if_missing('PROXY_WS_MAX_MSG_SIZE', 4 * 1024 * 1024)
            if not isinstance(settings.PROXY_WS_MAX_MSG_SIZE, int):
                raise ValueError("PROXY_WS_MAX_MSG_SIZE must be an integer")

            if settings.PROXY_WS_MAX_MSG_SIZE <= 0:
                raise ValueError("PROXY_WS_MAX_MSG_SIZE must be a positive integer")

            _set_default_if_missing('PROXY_WHITELIST_ENABLED', False)
            if not isinstance(settings.PROXY_WHITELIST_ENABLED, bool):
                raise ValueError("PROXY_WHITELIST_ENABLED must be a boolean")

            _set_default_if_missing('PROXY_WHITELIST', [])
            if not isinstance(settings.PROXY_WHITELIST, (list, tuple)):
                raise ValueError("PROXY_WHITELIST must be a list or tuple")

            if len(settings.PROXY_WHITELIST) == 0 and settings.PROXY_WHITELIST_ENABLED:
                logger.warning(
                    "PROXY_WHITELIST is empty but PROXY_WHITELIST_ENABLED is True. This will prevent the proxy from connecting to any domain.")

            for ip in settings.PROXY_WHITELIST:
                if not isinstance(ip, str):
                    raise ValueError("Each item in PROXY_WHITELIST must be a string")

                if not ip.strip():
                    raise ValueError("PROXY_WHITELIST cannot contain empty strings")

            _set_default_if_missing('PROXY_BLACKLIST_ENABLED', False)
            if not isinstance(settings.PROXY_BLACKLIST_ENABLED, bool):
                raise ValueError("PROXY_BLACKLIST_ENABLED must be a boolean")

            _set_default_if_missing('PROXY_BLACKLIST', [])
            if not isinstance(settings.PROXY_BLACKLIST, (list, tuple)):
                raise ValueError("PROXY_BLACKLIST must be a list or tuple")

            if len(settings.PROXY_BLACKLIST) == 0 and settings.PROXY_BLACKLIST_ENABLED:
                logger.warning(
                    "PROXY_BLACKLIST is empty but PROXY_BLACKLIST_ENABLED is True. This does nothing as no domain is blocked.")

            for ip in settings.PROXY_BLACKLIST:
                if not isinstance(ip, str):
                    raise ValueError("Each item in PROXY_BLACKLIST must be a string")

                if not ip.strip():
                    raise ValueError("PROXY_BLACKLIST cannot contain empty strings")

        return (validate_proxy_settings,)
