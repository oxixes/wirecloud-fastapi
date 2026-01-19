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

from src.wirecloud.platform.plugins import WirecloudPlugin
from src.wirecloud.proxy.urls import patterns as proxy_patterns
from src.wirecloud.proxy.routes import router as proxy_router


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

        return (validate_proxy_settings,)
