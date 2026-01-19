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

from fastapi import Request
import user_agents

from src import settings


def get_current_theme(request: Request) -> str:
    if "themeactive" in request.query_params and request.query_params["themeactive"] in settings.AVAILABLE_THEMES:
        return request.query_params["themeactive"]

    return settings.THEME_ACTIVE


def get_current_view(request: Request, ignore_query: bool = False) -> str:
    if "mode" in request.query_params and not ignore_query:
        return request.query_params["mode"]

    user_agent = user_agents.parse(request.headers["User-Agent"])
    return "smartphone" if user_agent.is_mobile else "classic"