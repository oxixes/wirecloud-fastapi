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

import importlib.util

from fastapi import Depends
from motor.motor_asyncio import AsyncIOMotorClient
from typing import AsyncIterator, Annotated

if importlib.util.find_spec('src') is None:
    from settings import DATABASE
else:
    from src.settings import DATABASE


def get_db_url() -> str:
    database_url = f"{DATABASE['DRIVER']}://{DATABASE['USER']}:{DATABASE['PASSWORD']}@{DATABASE['HOST']}"
    if DATABASE['PORT']:
        database_url += f":{DATABASE['PORT']}"

    return database_url


client = AsyncIOMotorClient()
database = client[DATABASE['NAME']]


def close() -> None:
    client.close()


async def get_session() -> AsyncIterator[AsyncIOMotorClient]:
    try:
        yield database
    finally:
        close()


DBDep = Annotated[AsyncIOMotorClient, Depends(get_session)]
