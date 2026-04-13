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

from bson import ObjectId

from wirecloud.commons.auth.models import Group
from wirecloud.database import Id


def test_group_parent_property_returns_none_without_parent():
    group_id = Id(str(ObjectId()))
    group = Group(_id=group_id, name="Root", codename="root", path=[group_id])

    assert group.parent is None


def test_group_parent_property_returns_previous_id_in_path():
    parent_id = Id(str(ObjectId()))
    child_id = Id(str(ObjectId()))
    group = Group(_id=child_id, name="Child", codename="child", path=[parent_id, child_id])

    assert str(group.parent) == str(parent_id)
