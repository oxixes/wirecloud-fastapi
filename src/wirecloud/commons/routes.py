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

from fastapi import APIRouter
from fastapi.responses import Response

from src.wirecloud.commons.templates.tags import get_javascript_catalogue
from src.wirecloud.commons import docs
from src.wirecloud import docs as root_docs

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