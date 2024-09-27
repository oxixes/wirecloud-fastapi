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
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorClientSession
from typing import AsyncIterator, Annotated, Any

from pydantic_core import core_schema

from src.settings import DATABASE
from bson import ObjectId


class MotorSession:
    def __init__(self, db: AsyncIOMotorClientSession):
        self.db = db

    def __getattr__(self, item: str):
        if item == "client":
            return self.db.client[DATABASE['NAME']]
        else:
            return getattr(self.db, item)


class PyObjectId(ObjectId):
    @classmethod
    def __get_pydantic_core_schema__(cls, _source_type: Any, _handler: Any) -> core_schema.CoreSchema:
        return core_schema.json_or_python_schema(
            json_schema=core_schema.str_schema(),
            python_schema=core_schema.union_schema([
                core_schema.is_instance_schema(ObjectId),
                core_schema.chain_schema([
                    core_schema.str_schema(),
                    core_schema.no_info_plain_validator_function(cls.validate),
                ])
            ]),
            serialization=core_schema.plain_serializer_function_ser_schema(
                lambda x: x if isinstance(x, ObjectId) else ObjectId(x)
            ),
        )

    @classmethod
    def validate(cls, value) -> ObjectId:
        if not ObjectId.is_valid(value):
            raise ValueError("Invalid ObjectId")
        return ObjectId(value)


Id = PyObjectId


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


async def get_session() -> AsyncIterator[MotorSession]:
    session = await client.start_session()
    try:
        yield MotorSession(session)
    except Exception:
        if session.in_transaction:
            await session.abort_transaction()
        raise
    finally:
        await session.end_session()


async def commit(session: AsyncIOMotorClientSession) -> None:
    await session.commit_transaction()


DBSession = MotorSession
DBDep = Annotated[MotorSession, Depends(get_session)]
