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

from fastapi import FastAPI

from src.wirecloud.platform.plugins import WirecloudPlugin
from src.wirecloud.proxy.urls import patterns as proxy_patterns
from src.wirecloud.proxy.routes import router as proxy_router


class WirecloudProxyPlugin(WirecloudPlugin):
    urls = proxy_patterns

    def __init__(self, app: FastAPI):
        super().__init__(app)

        app.include_router(proxy_router, prefix="/cdp", tags=["Proxy"])