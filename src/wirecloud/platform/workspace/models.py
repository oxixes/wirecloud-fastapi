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

from pydantic import BaseModel, Field, StringConstraints
from typing import Optional, Annotated, Any
from datetime import datetime, timezone

from wirecloud.commons.auth.crud import get_user_by_id, get_all_user_groups
from wirecloud.commons.auth.schemas import User, UserAll
from wirecloud.database import Id, DBSession
from wirecloud.platform.iwidget.models import WidgetInstance
from wirecloud.platform.preferences.schemas import WorkspacePreference
from wirecloud.platform.wiring.schemas import Wiring, WiringOperatorPreference, WiringOperator
from wirecloud.platform.wiring.utils import get_wiring_skeleton

IntegerStr = Annotated[str, StringConstraints(pattern=r'^\d+$')]


class WiringOperatorPreferenceValue(BaseModel):
    users: dict[str, Any] = {}


class DBWiringOperatorPreference(WiringOperatorPreference):
    value: Any


class WorkspaceWiringOperator(WiringOperator):
    properties: dict[str, DBWiringOperatorPreference]


class WorkspaceWiring(Wiring):
    operators: dict[str, WorkspaceWiringOperator] = {}


class WorkspaceAccessPermissions(BaseModel):
    id: Id
    accesslevel: int = 1


class DBWorkspacePreference(WorkspacePreference):
    name: str


DBTabPreference = DBWorkspacePreference


class Tab(BaseModel, populate_by_name=True):
    id: str
    name: str
    title: str
    visible: bool = False
    last_modified: Optional[datetime] = datetime.now(timezone.utc)
    widgets: dict[str, WidgetInstance] = {}
    preferences: list[DBTabPreference] = []


class WorkspaceExtraPreference(BaseModel):
    name: str
    inheritable: bool
    label: str
    type: str
    description: str
    required: bool


class WorkspaceForcedValue(BaseModel):
    value: Any
    hidden: bool = False


class DBWorkspaceForcedValues(BaseModel):
    extra_prefs: list[WorkspaceExtraPreference] = []
    operator: dict[IntegerStr, dict[str, WorkspaceForcedValue]] = {}
    widget: dict[str, dict[str, WorkspaceForcedValue]] = {}
    empty_params: list[str] = []


class Workspace(BaseModel, populate_by_name=True):
    id: Id = Field(alias="_id")
    name: str
    title: str
    creation_date: datetime = datetime.now(timezone.utc)
    last_modified: Optional[datetime] = datetime.now(timezone.utc)
    searchable: bool = True
    public: bool = False
    creator: Id
    description: str = ''
    longdescription: str = ''
    forced_values: DBWorkspaceForcedValues = DBWorkspaceForcedValues()
    wiring_status: WorkspaceWiring = get_wiring_skeleton()
    requireauth: bool = False

    # Relationships
    users: list[WorkspaceAccessPermissions] = []
    groups: list[WorkspaceAccessPermissions] = []
    tabs: dict[str, Tab] = {}
    preferences: list[DBWorkspacePreference] = []

    def is_editable_by(self, user: User) -> bool:
        return (
            user.is_superuser
            or self.creator == user.id
            or any(ws_user.id == user.id for ws_user in self.users)
        )
        # TODO check more permissions

    def is_shared(self) -> bool:
        return self.public or len(self.users) > 1 or len(self.groups) > 1

    async def is_accessible_by(self, db: DBSession, user: Optional[UserAll]) -> bool:
        if user is None:
            return self.public and not self.requireauth
        user_groups = await get_all_user_groups(db, user)
        return (user.is_superuser
                or self.public and not self.requireauth
                or user is not None and (
                        self.creator == user.id
                        or await get_user_by_id(db, user.id) is not None
                        or len(set(g.id for g in self.groups) & set(g.id for g in user_groups)) > 0)
                )  # TODO check more permissions
