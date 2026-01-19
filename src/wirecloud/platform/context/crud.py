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

from src.wirecloud.platform.context.schemas import Constant
from src.wirecloud.platform.context.models import DBConstant as ConstantModel
from src.wirecloud.database import DBSession


async def get_all_constants(db: DBSession) -> list[Constant]:
    results = [ConstantModel.model_validate(result) for result in await db.client.constants.find().to_list()]
    return results
