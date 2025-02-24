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

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, FileResponse
from typing import Optional
import os
import user_agents
import jinja2

from src import settings
from src.wirecloud.commons.templates.tags import get_wirecloud_bootstrap, get_translation, get_static_path, \
    get_url_from_view
from src.wirecloud.commons.utils.http import NotFound
from src.wirecloud.commons.utils.theme import get_theme_static_path, get_available_themes, get_jinja2_templates
from src.wirecloud.platform import docs
from src.wirecloud import docs as root_docs

router = APIRouter()

# TODO Error pages
# TODO Theme data

def get_current_theme(request: Request) -> str:
    if "themeactive" in request.query_params and request.query_params["themeactive"] in settings.AVAILABLE_THEMES:
        return request.query_params["themeactive"]

    return settings.THEME_ACTIVE

def get_current_view(request: Request, ignore_query: bool = False) -> str:
    if "mode" in request.query_params and not ignore_query:
        return request.query_params["mode"]

    user_agent = user_agents.parse(request.headers["User-Agent"])
    return "smartphone" if user_agent.is_mobile else "classic"

@router.get(
    "/",
    response_class=HTMLResponse,
    summary=docs.get_root_page_summary,
    description=docs.get_root_page_description,
    response_description=docs.get_root_page_response_description,
)
def render_root_page(request: Request):
    return render_wirecloud(request, title="landing")

@router.get(
    "/static/{path:path}",
    response_class=FileResponse,
    summary=docs.get_static_file_summary,
    description=docs.get_static_file_description,
    response_description=docs.get_static_file_response_description,
    responses={
        404: root_docs.generate_error_response_openapi_description(
            docs.get_static_file_not_found_response_description,
            "File not found"),
        422: root_docs.generate_validation_error_response_openapi_description(
            docs.get_static_file_validation_error_response_description)
    }
)
def serve_static(path: str, themeactive: str = settings.THEME_ACTIVE, view: str = "classic", context: str = "platform"):
    if path == "css/cache.css":
        try:
            return FileResponse(get_theme_static_path(themeactive, f"css/{themeactive}_{view}_{context}.css"))
        except NotFound:
            raise NotFound(f"File not found. If you're an admin, compile CSS by running npm run build:css.")
    elif path == "js/cache.js":
        try:
            return FileResponse(get_theme_static_path(themeactive, f"js/main-{themeactive}-{view}.js"))
        except NotFound:
            raise NotFound(f"File not found. If you're an admin, compile JS by running npm run build:js.")

    return FileResponse(get_theme_static_path(themeactive, path))

def render_wirecloud(request: Request, view: Optional[str] = None, title: str = "", description: str = ""):
    from src.wirecloud.platform.core.plugins import get_version_hash

    templates = get_jinja2_templates(get_current_theme(request))
    if view is None:
        view = get_current_view(request)

    context = {
        "title": title,
        "description": description,
        "uri": request.url.scheme + "://" + request.url.netloc + request.url.path + "?" + request.url.query,
        "LANGUAGE_CODE": request.state.lang,
        'WIRECLOUD_VERSION_HASH': get_version_hash(),
        "THEME": get_current_theme(request),
        "VIEW_MODE": view,
        "LANG": request.state.lang,
        'environ': os.environ,
        'request': request,

        "trans": lambda text, **kwargs: get_translation(get_current_theme(request), request.state.lang, text, **kwargs),
        "static": lambda path: get_static_path(get_current_theme(request), view, request, path),
        "url": lambda viewname, **kwargs: get_url_from_view(request, viewname, **kwargs)
    }

    context["wirecloud_bootstrap"] = lambda view_name, plain=False: get_wirecloud_bootstrap(context,
                                                                                            get_available_themes(request.state.lang),
                                                                                            view_name, plain)

    try:
        return templates.TemplateResponse(
            request=request, name=f"wirecloud/views/{view}.html", context=context,
        )
    except jinja2.exceptions.TemplateNotFound:
        view = get_current_view(request, True)
        context["VIEW_MODE"] = view

        return templates.TemplateResponse(
            request=request, name=f"wirecloud/views/{view}.html", context=context,
        )