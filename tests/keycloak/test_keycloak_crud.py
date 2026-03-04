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

from datetime import datetime, timezone

from bson import ObjectId

from wirecloud.keycloak import crud
from wirecloud.commons.auth.schemas import UserCreate


async def test_get_user_by_idm_user_id_found_and_missing(db_session):
    user_id = ObjectId()
    await db_session.client.users.insert_one(
        UserCreate(
            username="kc-user",
            password="hashed",
            first_name="Key",
            last_name="Cloak",
            email="kc@example.com",
            is_superuser=False,
            is_staff=False,
            is_active=True,
            idm_data={"keycloak": {"idm_user": "kc-sub"}},
        ).model_dump() | {
            "_id": user_id,
            "date_joined": datetime.now(timezone.utc),
            "last_login": None,
        }
    )

    user = await crud.get_user_by_idm_user_id(db_session, "kc-sub")
    assert user is not None
    assert user.username == "kc-user"
    assert str(user.id) == str(user_id)

    assert await crud.get_user_by_idm_user_id(db_session, "missing-sub") is None
