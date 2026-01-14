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

from src.wirecloud.commons.auth.routes import router as auth_router
from src.wirecloud.commons.auth.routes import base_router as auth_base_router
from src.wirecloud.commons.urls import get_urlpatterns
from src.wirecloud.platform.plugins import WirecloudPlugin, URLTemplate
from src.wirecloud.commons.auth.schemas import UserLogin
from src.wirecloud.commons.routes import router as commons_router
from src.wirecloud.commons.routes import (
    error_response_handler,
    permission_denied_handler,
    not_found_handler,
    validation_exception_handler,
    value_error_handler,
    general_exception_handler
)
from src.wirecloud.commons.exceptions import ErrorResponse
from src.wirecloud.commons.utils.http import PermissionDenied, NotFound
from fastapi.exceptions import RequestValidationError

from fastapi import FastAPI
from typing import Any, Optional


class WirecloudCommonsPlugin(WirecloudPlugin):
    def __init__(self, app: Optional[FastAPI]):
        super().__init__(app)

        if app is None:
            return

        app.include_router(auth_router, prefix="/api/auth", tags=["Auth"])
        app.include_router(auth_base_router, prefix="", tags=["Auth"])
        app.include_router(commons_router, prefix="", tags=["Other"])

        # Register exception handlers
        app.add_exception_handler(ErrorResponse, error_response_handler)
        app.add_exception_handler(PermissionDenied, permission_denied_handler)
        app.add_exception_handler(NotFound, not_found_handler)
        app.add_exception_handler(RequestValidationError, validation_exception_handler)
        app.add_exception_handler(ValueError, value_error_handler)
        app.add_exception_handler(Exception, general_exception_handler)

    def get_urls(self) -> dict[str, URLTemplate]:
        return get_urlpatterns()

    def get_openapi_extra_schemas(self) -> dict[str, dict[str, Any]]:
        return {
            "UserLogin": UserLogin.model_json_schema()
        }
