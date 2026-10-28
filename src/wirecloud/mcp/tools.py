"""Explicit capability inventory: each tool names its schema and authorized operation."""

from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from wirecloud.mcp import schemas
from wirecloud.mcp.operations import preferences, resources, widgets, wiring, workspaces

READ = "wirecloud:read"
WRITE = "wirecloud:workspace:write"
DELETE = "wirecloud:workspace:delete"
INSTALL = "wirecloud:component:install"
UNINSTALL = "wirecloud:component:uninstall"

SCOPES = {
    READ: "Read accessible workspaces, components, and documentation; export workspaces",
    WRITE: "Create and edit workspaces, tabs, components, layouts, preferences, and wiring",
    DELETE: "Delete owned workspaces and remove permitted workspace contents",
    INSTALL: "Install finished component packages for your account",
    UNINSTALL: "Uninstall components from your personal collection",
}


@dataclass(frozen=True)
class Tool:
    operation: Callable[..., Awaitable[Any]]
    model: type[schemas.Arguments]
    scopes: tuple[str, ...]
    description: str
    destructive: bool = False

    @property
    def name(self) -> str:
        return self.operation.__name__


TOOLS = [
    Tool(
        workspaces.get_session_info,
        schemas.Empty,
        (READ,),
        "Get the current user, grant scopes, and WireCloud capabilities.",
    ),
    Tool(
        workspaces.list_workspaces,
        schemas.Page,
        (READ,),
        "List accessible workspaces with optional text filtering and pagination.",
    ),
    Tool(
        workspaces.get_workspace,
        schemas.Workspace,
        (READ,),
        "Inspect workspace tabs, widgets, wiring, and the modification timestamp. Secure values are " "redacted.",
    ),
    Tool(
        workspaces.create_workspace,
        schemas.CreateWorkspace,
        (WRITE,),
        "Create a private workspace.",
    ),
    Tool(
        workspaces.clone_workspace,
        schemas.CloneWorkspace,
        (WRITE,),
        "Clone an accessible workspace into a new private workspace.",
    ),
    Tool(
        workspaces.update_workspace,
        schemas.UpdateWorkspace,
        (WRITE,),
        "Rename a workspace or edit its descriptions.",
    ),
    Tool(
        workspaces.delete_workspace,
        schemas.Edit,
        (WRITE, DELETE),
        "Delete a workspace owned by the current user.",
        destructive=True,
    ),
    Tool(
        workspaces.create_tab,
        schemas.CreateTab,
        (WRITE,),
        "Create a tab in an editable workspace.",
    ),
    Tool(
        workspaces.update_tab,
        schemas.UpdateTab,
        (WRITE,),
        "Rename a tab or change its visibility.",
    ),
    Tool(
        workspaces.reorder_tabs,
        schemas.ReorderTabs,
        (WRITE,),
        "Reorder all tabs using their existing IDs.",
    ),
    Tool(
        workspaces.delete_tab,
        schemas.Tab,
        (WRITE, DELETE),
        "Delete a tab and its removable widget instances.",
        destructive=True,
    ),
    Tool(
        widgets.add_widget,
        schemas.AddWidget,
        (WRITE,),
        "Add an installed widget to a tab with responsive layouts.",
    ),
    Tool(
        widgets.update_widget,
        schemas.UpdateWidget,
        (WRITE,),
        "Change a widget's title, resource version, responsive layouts, or tab.",
    ),
    Tool(
        widgets.remove_widget,
        schemas.Widget,
        (WRITE, DELETE),
        "Remove a widget instance from a workspace.",
        destructive=True,
    ),
    Tool(
        widgets.set_widget_variables,
        schemas.WidgetVariables,
        (WRITE,),
        "Update permitted widget preferences or properties, preserving omitted values.",
    ),
    Tool(
        preferences.get_preferences,
        schemas.Preferences,
        (READ,),
        "Read platform, workspace, or tab preferences.",
    ),
    Tool(
        preferences.update_preferences,
        schemas.UpdatePreferences,
        (WRITE,),
        "Update user-editable preferences. Sharing and publishing settings are excluded.",
    ),
    Tool(
        wiring.get_wiring,
        schemas.Workspace,
        (READ,),
        "Inspect operators, connections, and endpoint definitions with secure values redacted.",
    ),
    Tool(
        wiring.add_operator,
        schemas.AddOperator,
        (WRITE,),
        "Add an installed operator to workspace wiring with automatic editor placement.",
    ),
    Tool(
        wiring.update_operator,
        schemas.UpdateOperator,
        (WRITE,),
        "Update named operator preferences, preserving all omitted values.",
    ),
    Tool(
        wiring.remove_operator,
        schemas.Operator,
        (WRITE, DELETE),
        "Remove an operator and its removable connections.",
        destructive=True,
    ),
    Tool(
        wiring.connect_components,
        schemas.Connect,
        (WRITE,),
        "Connect a widget or operator output to a compatible input endpoint; automatically place components "
        "missing editor positions.",
    ),
    Tool(
        wiring.disconnect_components,
        schemas.Disconnect,
        (WRITE, DELETE),
        "Remove a connection by its current index.",
        destructive=True,
    ),
    Tool(
        wiring.layout_wiring,
        schemas.LayoutWiring,
        (WRITE,),
        "Arrange the wiring editor without supplying coordinates. By default fill missing positions; set "
        "preserve_existing=false to rearrange the whole graph after wiring. Optionally supply multiple "
        "explicit positions in one call. Dashboard layouts and behaviour layouts are unchanged.",
    ),
    Tool(
        resources.list_resources,
        schemas.Page,
        (READ,),
        "Search accessible component packages, descriptors, and versions.",
    ),
    Tool(
        resources.get_resource,
        schemas.Resource,
        (READ,),
        "Read a component descriptor, including preference and wiring endpoint definitions.",
    ),
    Tool(
        resources.get_resource_documentation,
        schemas.Resource,
        (READ,),
        "Read the accessible component's description, usage documentation reference, and changelog.",
    ),
    Tool(
        resources.validate_resource_package,
        schemas.ValidatePackage,
        (INSTALL,),
        "Validate a finished base64 WGT package without installing or building it.",
    ),
    Tool(
        resources.install_resource,
        schemas.Install,
        (INSTALL,),
        "Install an externally built WGT from URL, base64 bytes, or an upload handle, privately for the "
        "current user.",
    ),
    Tool(
        resources.uninstall_resource,
        schemas.Resource,
        (UNINSTALL,),
        "Uninstall a component version from the current user's collection.",
        destructive=True,
    ),
    Tool(
        workspaces.import_mashup,
        schemas.ImportMashup,
        (WRITE,),
        "Create a private workspace from an accessible installed mashup package.",
    ),
    Tool(
        workspaces.merge_mashup,
        schemas.MergeMashup,
        (WRITE,),
        "Merge an accessible installed mashup into an editable workspace.",
    ),
    Tool(
        workspaces.export_workspace,
        schemas.ExportWorkspace,
        (READ,),
        "Export a workspace as a mashup descriptor without publishing or including stored secrets.",
    ),
]

TOOL_MAP = {tool.name: tool for tool in TOOLS}
