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

from typing import Optional
from fastapi import APIRouter, Request, Query, Path
from fastapi.responses import Response

from src.wirecloud.commons.auth.utils import UserDep, UserDepNoCSRF
from src.wirecloud.commons.search import get_search_engine, is_available_search_engine, get_rebuild_engine, \
    is_available_rebuild_engine, SearchResponse
from src.wirecloud.commons.templates.tags import get_javascript_catalogue
from src.wirecloud.commons import docs
from src.wirecloud import docs as root_docs
from src.wirecloud.commons.utils.http import produces, build_error_response, authentication_required
from src.wirecloud.database import DBDep
from src.wirecloud.translation import gettext as _

router = APIRouter()

class JSResponse(Response):
    media_type = "application/javascript"

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
async def search_resources(user: UserDepNoCSRF, request: Request,
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
        res = await func(user, q, pagenum, maxresults, orderby)
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


@router.post(
    '/api/search/rebuild/{namespace}',
    summary=docs.rebuild_index_resources_summary,
    description=docs.rebuild_index_resources_description,
    response_class=Response,
    status_code=204,
    response_description=docs.rebuild_index_resources_response_description,
    responses={
        401: root_docs.generate_auth_required_response_openapi_description(
                docs.rebuild_index_resources_auth_required_response_description
        ),
        403: root_docs.generate_permission_denied_response_openapi_description(
                docs.rebuild_index_resources_permission_denied_response_description,
            'Only superusers can rebuild the search index'
        ),
        422: root_docs.generate_validation_error_response_openapi_description(
                docs.rebuild_index_resources_validation_error_response_description)
        }
)
@authentication_required()
async def rebuild_index_resources(db: DBDep, user: UserDep, request: Request,
                                  namespace: str = Path(description=docs.rebuild_index_resources_namespace_description)):
    if not user.is_superuser:
        return build_error_response(request, 403, _('Only superusers can rebuild the search index'))

    if not is_available_rebuild_engine(namespace):
        return build_error_response(request, 422, _(f'Invalid search namespace {namespace}'))

    await get_rebuild_engine(namespace)(db)

    return Response(status_code=204)