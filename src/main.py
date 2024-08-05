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

import sys

# Wirecloud is only compatible with Python 3.9 or higher
if sys.version_info < (3, 9):
    raise Exception("Wirecloud is only compatible with Python 3.9 or higher")

from contextlib import asynccontextmanager
from fastapi import FastAPI

from .wirecloud.database import close, engine
from .wirecloud.platform.plugins import get_plugins
from . import docs


# TODO Validate settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    if engine is not None:
        await close()


app = FastAPI(title=docs.title,
              version=docs.version,
              summary=docs.summary,
              description=docs.description,
              license_info=docs.license_info,
              contact=docs.contact,
              lifespan=lifespan)

get_plugins(app)


