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

from typing import Optional
from fastapi import APIRouter, Request, Query
from fastapi.responses import Response
from fastapi.exceptions import RequestValidationError

import src.settings as settings
from src.wirecloud.commons.auth.utils import UserDepNoCSRF
from src.wirecloud.commons.search import get_search_engine, is_available_search_engine, SearchResponse
from src.wirecloud.commons.templates.tags import get_javascript_catalogue
from src.wirecloud.commons import docs
from src.wirecloud import docs as root_docs
from src.wirecloud.commons.utils.http import produces, build_error_response, PermissionDenied, NotFound
from src.wirecloud.commons.exceptions import ErrorResponse
from src.wirecloud.database import DBDep
from src.wirecloud.translation import gettext as _

router = APIRouter()

class JSResponse(Response):
    media_type = "application/javascript"


# Exception handlers
async def error_response_handler(request: Request, exc: ErrorResponse):
    return exc.response


async def permission_denied_handler(request: Request, exc: PermissionDenied):
    error_msg = str(exc) if str(exc) else _('Permission denied')
    return build_error_response(request, 403, error_msg)


async def not_found_handler(request: Request, exc: NotFound):
    error_msg = str(exc) if str(exc) else _('Resource not found')
    return build_error_response(request, 404, error_msg)


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = {}
    for error in exc.errors():
        field = '.'.join(str(loc) for loc in error['loc'])
        if field not in errors:
            errors[field] = []
        errors[field].append(error['msg'])

    return build_error_response(
        request,
        422,
        _('Validation error'),
        details=errors
    )


async def value_error_handler(request: Request, exc: ValueError):
    error_msg = str(exc) if str(exc) else _('Invalid value')
    return build_error_response(request, 400, error_msg)


async def general_exception_handler(request: Request, exc: Exception):
    # Log the exception for debugging purposes TODO better logging
    import traceback
    traceback.print_exc()

    error_msg = _('An unexpected error occurred')

    if settings.DEBUG:
        error_msg = f"{error_msg}: {str(exc)}"

    return build_error_response(request, 500, error_msg)


@router.get(
    "/api/i18n/js_catalogue",
    response_class=JSResponse,
    summary=docs.get_js_catalogue_summary,
    description=docs.get_js_catalogue_description,
    response_description=docs.get_js_catalogue_response_description,
    responses={
        422: root_docs.generate_validation_error_response_openapi_description(
            docs.get_js_catalogue_validation_error_response_description)
    }
)
def get_js_catalogue(themeactive: str, language: str):
    return Response(get_javascript_catalogue(language, themeactive), media_type="application/javascript")


@router.get(
    '/api/search',
    summary=docs.get_search_resources_summary,
    description=docs.get_search_resources_description,
    response_model=SearchResponse,
    response_description=docs.get_search_resources_response_description,
    responses={
        200: {"content": {"application/json": {"example": docs.get_search_resources_response_example}}},
        401: root_docs.generate_auth_required_response_openapi_description(
            docs.get_search_resources_auth_required_response_description
        ),
        422: root_docs.generate_validation_error_response_openapi_description(
            docs.get_search_resources_validation_error_response_description)
    }
)
@produces(["application/json"])
async def search_resources(db: DBDep, user: UserDepNoCSRF, request: Request,
                           namespace: str = Query(description=docs.get_search_resources_namespace_description),
                           q: Optional[str] = Query(default='', description=docs.get_search_resources_q_description),
                           pagenum: int = Query(default=1, description=docs.get_search_resources_pagenum_description),
                           maxresults: int = Query(default=30, description=docs.get_search_resources_maxresults_description),
                           orderby: Optional[str] = Query(default='', description=docs.get_search_resources_orderby_description)):

    if not is_available_search_engine(namespace):
        return build_error_response(request, 422,  _(f'Invalid search namespace {namespace}'))

    orderby = tuple(f.strip() for f in orderby.split(",") if f.strip()) or None

    func = get_search_engine(namespace)

    if namespace == 'workspace':
        res = await func(db, user, q, pagenum, maxresults, orderby)
    elif namespace == 'resource':
        res = await func(request, user, q, pagenum, maxresults, order_by=orderby)
    else:
        if user:
            res = await func(q, pagenum, maxresults, orderby)
        else:
            return build_error_response(request, 401, _('Authentication required'))

    if res is None:
        return build_error_response(request, 422, _('Invalid orderby value'))
    return res