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

from typing import AsyncIterator, Annotated
from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine, create_async_engine, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from fastapi import Depends

if importlib.util.find_spec('src') is None:
    from settings import DATABASE
else:
    from src.settings import DATABASE


def get_db_url() -> str:
    database_url = f"{DATABASE['DRIVER']}://{DATABASE['USER']}:{DATABASE['PASSWORD']}@{DATABASE['HOST']}"
    if DATABASE['PORT']:
        database_url += f":{DATABASE['PORT']}"
    database_url += f"/{DATABASE['NAME']}"

    if 'sqlite' in DATABASE['DRIVER']:
        database_url = f"{DATABASE['DRIVER']}:///{DATABASE['NAME']}"

    return database_url


engine: AsyncEngine = create_async_engine(get_db_url(), echo=DATABASE['ECHO'])
sessionmaker = async_sessionmaker(autocommit=False, bind=engine)


async def close() -> None:
    if engine:
        await engine.dispose()


async def commit(session: AsyncSession) -> None:
    await session.commit()


async def get_session() -> AsyncIterator[AsyncSession]:
    session = sessionmaker()
    try:
        yield session
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()

DBDep = Annotated[AsyncSession, Depends(get_session)]
DBSession = AsyncSession

Base = declarative_base()
