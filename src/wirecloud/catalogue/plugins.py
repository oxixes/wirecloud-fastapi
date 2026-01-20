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

import os
import logging
from typing import Optional, Callable
from fastapi import FastAPI

from wirecloud.platform.plugins import WirecloudPlugin
from wirecloud.catalogue.urls import patterns as catalogue_patterns
from wirecloud.catalogue.routes import router as catalogue_router


logger = logging.getLogger(__name__)


class WirecloudCataloguePlugin(WirecloudPlugin):
    urls = catalogue_patterns

    def __init__(self, app: Optional[FastAPI]):
        super().__init__(app)

        if app is None:
            return

        app.include_router(catalogue_router, prefix="/catalogue", tags=["Catalogue"])

    def get_config_validators(self) -> tuple[Callable, ...]:
        def validate_catalogue_settings(settings, _offline: bool) -> None:
            from os import path

            # CATALOGUE_MEDIA_ROOT (default: BASEDIR/catalogue/media)
            if not hasattr(settings, 'CATALOGUE_MEDIA_ROOT'):
                setattr(settings, 'CATALOGUE_MEDIA_ROOT', path.join(settings.BASEDIR, 'catalogue', 'media'))

            if not isinstance(settings.CATALOGUE_MEDIA_ROOT, str):
                raise ValueError("CATALOGUE_MEDIA_ROOT must be a string")

            # Create directory if it doesn't exist
            if not os.path.exists(settings.CATALOGUE_MEDIA_ROOT):
                try:
                    os.makedirs(settings.CATALOGUE_MEDIA_ROOT, exist_ok=True)
                    logger.info(f"Created CATALOGUE_MEDIA_ROOT directory: {settings.CATALOGUE_MEDIA_ROOT}")
                except Exception as e:
                    raise ValueError(f"Failed to create CATALOGUE_MEDIA_ROOT directory: {e}")

        return (validate_catalogue_settings,)
