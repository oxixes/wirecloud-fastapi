"""Closed tool inputs: administrative and sharing fields cannot pass through."""
from __future__ import annotations

from typing import Any, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator
from wirecloud.platform.iwidget.models import WidgetLayout
from wirecloud.platform.iwidget.schemas import WidgetLayoutUpdate
from wirecloud.platform.wiring.schemas import WiringConnectionEndpoint


class Arguments(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Empty(Arguments):
    pass


class Page(Arguments):
    query: str = Field(default="", max_length=200)
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=20, ge=1, le=100)


class Workspace(Arguments):
    workspace_id: str


class Edit(Workspace):
    expected_last_modified: Optional[str] = Field(default=None, description="Modification timestamp returned by get_workspace; stale edits return a conflict")


class CreateWorkspace(Arguments):
    name: str = ""
    title: str = ""
    preferences: dict[str, str] = Field(default_factory=dict)
    allow_renaming: bool = False


class CloneWorkspace(CreateWorkspace):
    source_workspace_id: str


class UpdateWorkspace(Edit):
    name: str = ""
    title: str = ""
    description: str = ""
    longdescription: str = ""


class CreateTab(Edit):
    name: str = ""
    title: str = ""


class Tab(Edit):
    tab_id: str


class UpdateTab(Tab):
    name: str = ""
    title: str = ""
    visible: Optional[bool] = None


class ReorderTabs(Edit):
    tab_ids: list[str]


class AddWidget(Tab):
    resource: str = Field(pattern=r"^[^/]+/[^/]+/[^/]+$")
    title: str
    layouts: dict[str, WidgetLayout] = Field(default_factory=dict)


class Widget(Tab):
    widget_id: str


class UpdateWidget(Widget):
    title: Optional[str] = None
    resource: Optional[str] = Field(default=None, pattern=r"^[^/]+/[^/]+/[^/]+$")
    destination_tab_id: Optional[str] = None
    layouts: Optional[dict[str, WidgetLayoutUpdate]] = None


class WidgetVariables(Widget):
    values: dict[str, Any]
    kind: Literal["preferences", "properties"] = "preferences"


class Preferences(Arguments):
    target: Literal["platform", "workspace", "tab"]
    workspace_id: Optional[str] = None
    tab_id: Optional[str] = None


class UpdatePreferences(Preferences):
    values: dict[str, str]
    expected_last_modified: Optional[str] = None


class Resource(Arguments):
    resource: str = Field(pattern=r"^[^/]+/[^/]+/[^/]+$")


class Install(Arguments):
    url: Optional[str] = None
    package_base64: Optional[str] = None
    upload_id: Optional[str] = None
    install_embedded_resources: bool = False

    @model_validator(mode="after")
    def single_source(self):
        if sum(value is not None for value in (self.url, self.package_base64, self.upload_id)) != 1:
            raise ValueError("Supply exactly one of url, package_base64, or upload_id")
        return self


class ValidatePackage(Arguments):
    package_base64: str


class AddOperator(Edit):
    resource: str = Field(pattern=r"^[^/]+/[^/]+/[^/]+$")
    preferences: dict[str, Any] = Field(default_factory=dict)


class Operator(Edit):
    operator_id: str = Field(pattern=r"^\d+$")


class UpdateOperator(Operator):
    preferences: dict[str, Any] = Field(default_factory=dict)


class Connect(Edit):
    source: WiringConnectionEndpoint
    target: WiringConnectionEndpoint


class Disconnect(Edit):
    connection_index: int = Field(ge=0)


class WiringPlacement(Arguments):
    type: Literal["widget", "operator"]
    id: str = Field(min_length=1)
    x: int = Field(ge=20, strict=True, description="Wiring editor horizontal position in pixels")
    y: int = Field(ge=10, strict=True, description="Wiring editor vertical position in pixels")


class LayoutWiring(Edit):
    preserve_existing: bool = Field(default=True, description="Keep existing positions; set false to automatically rearrange the whole wiring graph")
    positions: list[WiringPlacement] = Field(default_factory=list, max_length=500,
        description="Optional explicit moves, applied together; omit for automatic placement")


class ImportMashup(CreateWorkspace):
    mashup: str = Field(pattern=r"^[^/]+/[^/]+/[^/]+$")


class MergeMashup(Edit):
    mashup: str = Field(pattern=r"^[^/]+/[^/]+/[^/]+$")


class ExportWorkspace(Workspace):
    vendor: str = "export"
    name: str = "workspace"
    version: str = "1.0.0"
