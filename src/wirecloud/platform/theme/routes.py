# -*- coding: utf-8 -*-
# Copyright (c) 2024 Future Internet Consulting and Development Solutions S.L.
from urllib.request import Request

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

import os
import jinja2
from fastapi import APIRouter, Request, Path, Query

from src.wirecloud.commons.templates.tags import get_translation, get_static_path, get_url_from_view
from src.wirecloud.platform.plugins import get_templates
from src.wirecloud.commons.utils.http import NotFound
from src.wirecloud.commons.utils.theme import get_available_themes, get_jinja2_templates
from src.wirecloud.platform.theme import docs
import src.wirecloud.docs as root_docs
from src.wirecloud.platform.theme.schemas import ThemeInfo

router = APIRouter()

@router.get(
    "/{theme}",
    response_model=ThemeInfo,
    summary=docs.get_theme_info_summary,
    description=docs.get_theme_info_description,
    response_description=docs.get_theme_info_response_description,
    responses={
        404: root_docs.generate_error_response_openapi_description(
            docs.get_theme_info_not_found_response_description,
            "Theme not found"),
        422: root_docs.generate_validation_error_response_openapi_description(
            docs.get_theme_info_validation_error_response_description)
    }
)
def get_theme_info(request: Request, theme: str = Path(..., description=docs.get_theme_info_theme_param_description),
                   view: str = Query("classic", description=docs.get_theme_info_view_param_description)):
    # TODO Cache response. This will never change while the server is running, or at least it shouldn't, but just in case
    # TODO disable cache for development

    themes = get_available_themes(request.state.lang)
    theme_metadata = None
    for theme_metadata in themes:
        if theme_metadata["value"] == theme:
            break

    if theme_metadata is None:
        raise NotFound("Theme not found")

    info = ThemeInfo(
        name=theme_metadata["value"],
        label=theme_metadata["label"],
        templates={}
    )

    templates = get_jinja2_templates(theme)

    for template_id in get_templates(view):
        template_file = template_id + '.html'

        context = {
            "VIEW_MODE": view,
            "LANG": request.state.lang,
            'environ': os.environ,
            'request': request,

            "trans": lambda text, **kwargs: get_translation(theme, request.state.lang, text, **kwargs),
            "static": lambda path: get_static_path(theme, view, request, path),
            "url": lambda viewname, **kwargs: get_url_from_view(request, viewname, **kwargs)
        }

        try:
            info.templates[template_id] = templates.TemplateResponse(
                request=request, name=template_file, context=context
            ).body.decode('utf-8')
        except jinja2.exceptions.TemplateNotFound:
            raise NotFound(f"Template {template_id} expected but not found. Check the theme's templates.")

    return info
