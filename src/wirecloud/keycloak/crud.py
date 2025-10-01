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

from typing import Optional

from src.wirecloud.commons.auth.models import DBUser as UserModel
from src.wirecloud.commons.auth.schemas import User
from src.wirecloud.database import DBSession

async def get_user_by_idm_user_id(db: DBSession, idm_user_id: str) -> Optional[User]:
    user_data = await db.client.users.find_one({"idm_data.keycloak.idm_user": idm_user_id})

    if user_data is None:
        return None

    user = UserModel.model_validate(user_data)

    return User(
        id=user.id,
        username=user.username,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        is_superuser=user.is_superuser,
        is_staff=user.is_staff,
        is_active=user.is_active,
        date_joined=user.date_joined,
        last_login=user.last_login,
        idm_data=user.idm_data
    )
