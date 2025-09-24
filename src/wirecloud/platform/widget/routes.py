#  -*- coding: utf-8 -*-
#
#  Copyright (c) 2024 Future Internet Consulting and Development Solutions S.L.
#
#  This file is part of Wirecloud.
#
#  Wirecloud is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Affero General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  Wirecloud is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Affero General Public License for more details.
#
#  You should have received a copy of the GNU Affero General Public License
#  along with Wirecloud.  If not, see <http://www.gnu.org/licenses/>.
import os
from typing import Optional

from fastapi import APIRouter, Request, Path, Response, Query
from fastapi.responses import HTMLResponse

from src.wirecloud import docs as root_docs
from src.wirecloud.catalogue.crud import get_catalogue_resource_with_xhtml
import src.wirecloud.platform.widget.utils as showcase_utils
from src.wirecloud.commons.templates.tags import get_translation, get_url_from_view, get_static_path
from src.wirecloud.commons.utils.cache import check_if_modified_since, patch_cache_headers
from src.wirecloud.commons.utils.http import NotFound, build_downloadfile_response, get_absolute_reverse_url, \
    build_error_response
from src.wirecloud.commons.utils.template.schemas.macdschemas import Vendor, Name, Version
from src.wirecloud.commons.utils.theme import get_jinja2_templates
from src.wirecloud.database import DBDep
from src.wirecloud.platform.routes import get_current_theme, get_current_view
from src.wirecloud.platform.widget.utils import get_widget_platform_style, process_widget_code
from src.wirecloud.platform.widget import docs
from src.wirecloud.translation import gettext as _

widget_router = APIRouter()
showcase_router = APIRouter()


@widget_router.get(
    "/{vendor}/{name}/{version}/html",
    summary=docs.get_widget_html_summary,
    description=docs.get_widget_html_description,
    status_code=200,
    response_class=HTMLResponse,
    response_description=docs.get_widget_html_response_description,
    responses={
        304: {"description": docs.get_widget_html_not_modified_response_description},
        404: root_docs.generate_not_found_response_openapi_description(
            docs.get_widget_html_not_found_response_description
        ),
        502: root_docs.generate_error_response_openapi_description(
            docs.get_widget_html_bad_gateway_response_description,
            "Widget code was not encoded using the specified charset"
        )
    },
)
async def get_widget_html(db: DBDep, request: Request, vendor: Vendor = Path(pattern=r"^[^/]+$",
                                                                             description=docs.get_widget_html_vendor_description),
                          name: Name = Path(pattern=r"^[^/]+$", description=docs.get_widget_html_name_description),
                          version: Version = Path(
                              pattern=r"^(?:[1-9]\d*\.|0\.)*(?:[1-9]\d*|0)(?:(?:a|b|rc)[1-9]\d*)?(-dev.*)?$",
                              description=docs.get_widget_html_version_description),
                          mode: str = Query(default='classic', description=docs.get_widget_html_mode_description),
                          theme: Optional[str] = Query(default=None,
                                                       description=docs.get_widget_html_theme_description)):
    resource = await get_catalogue_resource_with_xhtml(db, vendor, name, version)
    if resource.resource_type() != 'widget':
        raise NotFound()

    creation_date = resource.creation_date.timestamp()
    if not check_if_modified_since(request, creation_date * 1000):
        response = Response(status_code=304)
        patch_cache_headers(response, creation_date)
        return response

    return await process_widget_code(db, request, resource, mode, theme)


@showcase_router.get(
    "/{vendor}/{name}/{version}/{file_path:path}",
    summary=docs.get_widget_file_summary,
    description=docs.get_widget_file_description,
    status_code=200,
    response_class=Response,
    response_description=docs.get_widget_file_response_description,
    responses={
        302: {"description": docs.get_widget_file_found_response_description},
        304: {"description": docs.get_widget_file_not_modified_response_description},
        404: root_docs.generate_not_found_response_openapi_description(
            docs.get_widget_file_not_found_response_description
        )
    }
)
async def get_widget_file(db: DBDep, request: Request, vendor: Vendor = Path(pattern=r"^[^/]+$",
                                                                             description=docs.get_widget_file_vendor_description),
                          name: Name = Path(pattern=r"^[^/]+$", description=docs.get_widget_file_name_description),
                          version: Version = Path(
                              pattern=r"^(?:[1-9]\d*\.|0\.)*(?:[1-9]\d*|0)(?:(?:a|b|rc)[1-9]\d*)?(-dev.*)?$",
                              description=docs.get_widget_file_version_description),
                          file_path: str = Path(description=docs.get_widget_file_path_description)):

    if ".." in file_path:
        return build_error_response(request, 404, _("Page not found"))
    resource = await get_catalogue_resource_with_xhtml(db, vendor, name, version)
    if resource.resource_type() not in ['widget', 'operator']:
        raise NotFound()
    # For now, all widgets and operators are freely accessible/distributable
    # if not resource.is_available_for(request.user):
    #     return build_error_response(request, 403, "Forbidden")

    # send fast 304 if possible
    creation_date = resource.creation_date.timestamp()
    if not check_if_modified_since(request, creation_date * 1000):
        response = Response(status_code=304)
        patch_cache_headers(response, creation_date)
        return response

    if file_path.endswith(".wgt"):
        from src.wirecloud.catalogue.utils import wgt_deployer as wgt_deployer_catalogue
        base_dir = wgt_deployer_catalogue.get_base_dir(vendor, name, version)
    else:
        base_dir = showcase_utils.wgt_deployer.get_base_dir(vendor, name, version)

    response = build_downloadfile_response(request, file_path, base_dir)
    if response.status_code == 302:
        response.headers['Location'] = get_absolute_reverse_url('wirecloud.showcase_media', request=request,
                                                                vendor=vendor, name=name, version=version,
                                                                path=response.headers['Location'])

    # TODO cache
    return response


@widget_router.get(
    "/missing_widget",
    summary=docs.get_missing_widget_html_summary,
    description=docs.get_missing_widget_html_description,
    response_description=docs.get_missing_widget_html_response_description,
    status_code=200,
    response_class=HTMLResponse
)
async def get_missing_widget_html(request: Request, theme: Optional[str] = Query(default=None,
                                                                                 description=docs.get_missing_widget_html_theme_description)):
    templates = get_jinja2_templates(get_current_theme(request))
    style = get_widget_platform_style(request, theme)
    if theme is None:
        theme = get_current_theme(request)
    from src.wirecloud.platform.core.plugins import get_version_hash
    context = {
        "uri": request.url.scheme + "://" + request.url.netloc + request.url.path + "?" + request.url.query,
        "LANGUAGE_CODE": request.state.lang,
        'WIRECLOUD_VERSION_HASH': get_version_hash(),
        "THEME": theme,
        "VIEW_MODE": get_current_view(request),
        "LANG": request.state.lang,
        'environ': os.environ,
        'request': request,

        "trans": lambda text, **kwargs: get_translation(get_current_theme(request), request.state.lang, text, **kwargs),
        "static": lambda path: get_static_path(get_current_theme(request), get_current_view(request), request, path),
        "url": lambda viewname, **kwargs: get_url_from_view(request, viewname, **kwargs),
        'style': style,
    }

    return templates.TemplateResponse(name="wirecloud/workspace/missing_widget.html", context=context)
