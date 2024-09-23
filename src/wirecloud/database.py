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


from fastapi import Depends
from motor.motor_asyncio import AsyncIOMotorClient
from typing import AsyncIterator, Annotated
from src.settings import DATABASE


ID = str


def get_db_url() -> str:
    driver = "mongodb"
    if DATABASE['USER'] and DATABASE['PASSWORD'] and DATABASE['USER'] != "" and DATABASE["PASSWORD"] != "":
        database_url = f"{driver}://{DATABASE['USER']}:{DATABASE['PASSWORD']}@{DATABASE['HOST']}"
    elif DATABASE['USER'] and DATABASE['USER'] != "":
        database_url = f"{driver}://{DATABASE['USER']}@{DATABASE['HOST']}"
    else:
        database_url = f"{driver}://{DATABASE['HOST']}"

    if DATABASE['PORT']:
        database_url += f":{DATABASE['PORT']}"

    return database_url


client = AsyncIOMotorClient(get_db_url())
database = client[DATABASE['NAME']]


def close() -> None:
    client.close()


async def get_session() -> AsyncIterator[AsyncIOMotorClient]:
    session = await client.start_session()
    try:
        yield session
    except Exception:
        await session.abort_transaction()
        raise
    finally:
        await session.end_session()




DBDep = Annotated[AsyncIOMotorClient, Depends(get_session)]
