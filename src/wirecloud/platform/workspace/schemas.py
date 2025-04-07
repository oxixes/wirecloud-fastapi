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


from datetime import datetime
from typing import Optional, Any, Union

from pydantic import BaseModel, model_validator, Field, field_serializer

from src.wirecloud.commons.auth.crud import get_user_by_id, get_user_groups
from src.wirecloud.commons.auth.schemas import User
from src.wirecloud.database import DBSession
from src.wirecloud.platform.iwidget.schemas import IWidgetData
from src.wirecloud.platform.preferences.schemas import TabPreference, WorkspacePreference
from src.wirecloud.platform.workspace.models import DBWorkspace, DBWorkspaceAccessPermissions, \
    DBWorkspaceExtraPreference, DBWorkspaceForcedValue, DBWiringOperator, IntegerStr, DBWiring, DBTab

WorkspaceForcedValue = DBWorkspaceForcedValue
WorkspaceExtraPreference = DBWorkspaceExtraPreference
Wiring = DBWiring
Tab = DBTab


class TabData(BaseModel):
    id: str
    name: str
    title: str
    visible: bool = False
    widgets: list[IWidgetData] = []
    preferences: dict[str, TabPreference] = {}
    last_modified: Optional[datetime] = datetime.now()

    @field_serializer("last_modified")
    def serialize_last_modified(self, dt: datetime, _info) -> int:
        return int(datetime.timestamp(dt) * 1000)


class Workspace(DBWorkspace):
    def is_editable_by(self, user: User) -> bool:
        return user.is_superuser or self.creator == user.id
        # TODO check more permissions

    def is_shared(self) -> bool:
        return self.public or len(self.users) > 1 or len(self.groups) > 1

    async def is_accsessible_by(self, db: DBSession, user: Optional[User]) -> bool:
        from src.wirecloud.platform.workspace.crud import get_workspace_groups
        if user is None:
            return self.public and not self.requireauth
        return (user.is_superuser
                or self.public and not self.requireauth
                or self.public and user is None
                or not user is None and (
                        self.creator == user.id
                        or get_user_by_id(db, user.id) is not None
                        or len(set(await get_workspace_groups(db, self)) & set(await get_user_groups(db, user.id))) > 0
                )
                )  # TODO check more permissions


class UserWorkspaceData(BaseModel):
    fullname: str
    username: str
    organization: bool
    accesslevel: str


class GroupWorkspaceData(BaseModel):
    name: str
    accesslevel: str


class WorkspaceData(BaseModel):
    id: str
    name: str
    title: str
    public: bool
    shared: bool
    requireauth: bool
    owner: str
    removable: bool
    lastmodified: datetime
    description: str
    longdescription: str

    @field_serializer("lastmodified")
    def serialize_lastmodified(self, dt: datetime, _info) -> int:
        return int(datetime.timestamp(dt) * 1000)


class WorkspaceGlobalData(WorkspaceData):
    preferences: dict[str, WorkspacePreference] = {}
    users: list[UserWorkspaceData] = []
    groups: list[GroupWorkspaceData] = []
    empty_params: list[str] = []
    extra_prefs: list[WorkspaceExtraPreference] = []
    wiring: Wiring = Wiring()
    tabs: list[TabData] = []


class WorkspaceCreate(BaseModel):
    name: Optional[str] = Field(pattern=r'^[^/]+$')
    title: Optional[str]
    workspace: Optional[str]
    mashup: Optional[str]
    preferences: dict[str, Union[str, WorkspacePreference]]
    allow_renaming: bool = False
    dry_run: bool = False

    @model_validator(mode="after")
    def check_missing_parameters(self):
        if self.mashup == '' and self.workspace == '' and (self.name == '' and self.title == ''):
            raise ValueError("Missing name or title parameter")
        elif self.mashup != '' and self.workspace != '':
            raise ValueError("Workspace and mashup parameters cannot be used at the same time")

        return self


class WorkspaceForcedValues(BaseModel):
    extra_prefs: list[WorkspaceExtraPreference] = []
    ioperator: dict[IntegerStr, dict[str, WorkspaceForcedValue]] = {}
    iwidget: dict[IntegerStr, dict[str, WorkspaceForcedValue]] = {}
    empty_params: Any = []  # TODO: create a schema for this


WorkspaceAccessPermissions = DBWorkspaceAccessPermissions
WiringOperator = DBWiringOperator


class IdMappingOperator(BaseModel):
    id: str


class IdMappingWidget(BaseModel):
    id: str
    name: str


class IdMapping(BaseModel):
    operator: dict[str, IdMappingOperator] = {}
    widget: dict[str, IdMappingWidget] = {}


class CacheEntry(BaseModel):
    type: str
    secure: bool
    value: Optional[str] = None
    default: Optional[str] = None
    readonly: Optional[bool] = None
    hidden: bool = False


class CacheVariableData(BaseModel):
    name: str
    secure: bool
    readonly: bool
    hidden: bool
    value: Any


class WorkspaceEntry(BaseModel):
    name: str = ''
    title: str = ''
    description: str = ''
    longdescription: str = ''


class TabCreate(BaseModel):
    name: str
    title: str


class TabCreateEntry(TabCreate):
    visible: Optional[bool] = None


class MashupMergeService(BaseModel):
    workspace: str
    mashup: str


class TabOrderService(BaseModel):
    tabs: list[int]
