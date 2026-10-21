"""Explicit capability inventory. No caller-controlled operation dispatch."""
from dataclasses import dataclass
from wirecloud.mcp import schemas as s

READ = "wirecloud:read"
WRITE = "wirecloud:workspace:write"
DELETE = "wirecloud:workspace:delete"
INSTALL = "wirecloud:component:install"
UNINSTALL = "wirecloud:component:uninstall"
SCOPES = {READ: "Read accessible workspaces, components, and documentation; export workspaces",
          WRITE: "Create and edit workspaces, tabs, components, layouts, preferences, and wiring",
          DELETE: "Delete owned workspaces and remove permitted workspace contents",
          INSTALL: "Install finished component packages for your account",
          UNINSTALL: "Uninstall components from your personal collection"}


@dataclass(frozen=True)
class Tool:
    name: str
    model: type
    scopes: tuple
    description: str
    destructive: bool = False


TOOLS = [
    Tool("get_session_info", s.Empty, (READ,), "Get the current user, grant scopes, and WireCloud capabilities."),
    Tool("list_workspaces", s.Page, (READ,), "List accessible workspaces with optional text filtering and pagination."),
    Tool("get_workspace", s.Workspace, (READ,), "Inspect workspace tabs, widgets, wiring, and the modification timestamp. Secure values are redacted."),
    Tool("create_workspace", s.CreateWorkspace, (WRITE,), "Create a private workspace."),
    Tool("clone_workspace", s.CloneWorkspace, (WRITE,), "Clone an accessible workspace into a new private workspace."),
    Tool("update_workspace", s.UpdateWorkspace, (WRITE,), "Rename a workspace or edit its descriptions."),
    Tool("delete_workspace", s.Edit, (WRITE, DELETE), "Delete a workspace owned by the current user.", True),
    Tool("create_tab", s.CreateTab, (WRITE,), "Create a tab in an editable workspace."),
    Tool("update_tab", s.UpdateTab, (WRITE,), "Rename a tab or change its visibility."),
    Tool("reorder_tabs", s.ReorderTabs, (WRITE,), "Reorder all tabs using their existing IDs."),
    Tool("delete_tab", s.Tab, (WRITE, DELETE), "Delete a tab and its removable widget instances.", True),
    Tool("add_widget", s.AddWidget, (WRITE,), "Add an installed widget to a tab with responsive layouts."),
    Tool("update_widget", s.UpdateWidget, (WRITE,), "Change a widget's title, resource version, responsive layouts, or tab."),
    Tool("remove_widget", s.Widget, (WRITE, DELETE), "Remove a widget instance from a workspace.", True),
    Tool("set_widget_variables", s.WidgetVariables, (WRITE,), "Update permitted widget preferences or properties, preserving omitted values."),
    Tool("get_preferences", s.Preferences, (READ,), "Read platform, workspace, or tab preferences."),
    Tool("update_preferences", s.UpdatePreferences, (WRITE,), "Update user-editable preferences. Sharing and publishing settings are excluded."),
    Tool("get_wiring", s.Workspace, (READ,), "Inspect operators, connections, and endpoint definitions with secure values redacted."),
    Tool("add_operator", s.AddOperator, (WRITE,), "Add an installed operator to workspace wiring with automatic editor placement."),
    Tool("update_operator", s.UpdateOperator, (WRITE,), "Update named operator preferences, preserving all omitted values."),
    Tool("remove_operator", s.Operator, (WRITE, DELETE), "Remove an operator and its removable connections.", True),
    Tool("connect_components", s.Connect, (WRITE,), "Connect a widget or operator output to a compatible input endpoint; automatically place components missing editor positions."),
    Tool("disconnect_components", s.Disconnect, (WRITE, DELETE), "Remove a connection by its current index.", True),
    Tool("layout_wiring", s.LayoutWiring, (WRITE,), "Arrange the wiring editor without supplying coordinates. By default fill missing positions; set preserve_existing=false to rearrange the whole graph after wiring. Optionally supply multiple explicit positions in one call. Dashboard layouts and behaviour layouts are unchanged."),
    Tool("list_resources", s.Page, (READ,), "Search accessible component packages, descriptors, and versions."),
    Tool("get_resource", s.Resource, (READ,), "Read a component descriptor, including preference and wiring endpoint definitions."),
    Tool("get_resource_documentation", s.Resource, (READ,), "Read the accessible component's description, usage documentation reference, and changelog."),
    Tool("validate_resource_package", s.ValidatePackage, (INSTALL,), "Validate a finished base64 WGT package without installing or building it."),
    Tool("install_resource", s.Install, (INSTALL,), "Install an externally built WGT from URL, base64 bytes, or an upload handle, privately for the current user."),
    Tool("uninstall_resource", s.Resource, (UNINSTALL,), "Uninstall a component version from the current user's collection.", True),
    Tool("import_mashup", s.ImportMashup, (WRITE,), "Create a private workspace from an accessible installed mashup package."),
    Tool("merge_mashup", s.MergeMashup, (WRITE,), "Merge an accessible installed mashup into an editable workspace."),
    Tool("export_workspace", s.ExportWorkspace, (READ,), "Export a workspace as a mashup descriptor without publishing or including stored secrets."),
]
TOOL_MAP = {tool.name: tool for tool in TOOLS}
