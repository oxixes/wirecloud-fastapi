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

import asyncio

from src import settings
from src.wirecloud.platform.plugins import get_config_validators


async def validate_settings():
    if getattr(settings, "OID_CONNECT_ENABLED", False):
        if not getattr(settings, "OID_CONNECT_CLIENT_ID", None):
            raise ValueError("OID_CONNECT_CLIENT_ID is required when OID_CONNECT_ENABLED is True")

    validators = get_config_validators()
    for validator in validators:
        # Check if its synchronous
        if hasattr(validator, "__call__") and not asyncio.iscoroutinefunction(validator):
            validator(settings)
        elif asyncio.iscoroutinefunction(validator):
            await validator(settings)