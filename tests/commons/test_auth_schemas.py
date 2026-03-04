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

from wirecloud.commons.auth.schemas import Permission, UserAll, UserDetails
from wirecloud.database import Id


def _make_user_all(permissions):
    return UserAll(
        id=Id(str(ObjectId())),
        username="john",
        email="john@example.com",
        first_name="John",
        last_name="Doe",
        is_superuser=False,
        is_staff=False,
        is_active=True,
        date_joined=datetime.now(timezone.utc),
        last_login=None,
        idm_data={},
        groups=[],
        permissions=permissions,
    )


async def test_user_details_get_full_name_strips_whitespace():
    details = UserDetails(
        username="u",
        email="u@example.com",
        first_name="John",
        last_name="",
        is_superuser=False,
        is_staff=False,
        is_active=True,
        idm_data={},
    )

    assert details.get_full_name() == "John"


async def test_user_all_has_perm_exact_wildcard_and_missing():
    user = _make_user_all([
        Permission(codename="widgets.view"),
        Permission(codename="workspace.*"),
    ])

    assert user.has_perm("widgets.view") is True
    assert user.has_perm("workspace.edit") is True
    assert user.has_perm("unknown.permission") is False
