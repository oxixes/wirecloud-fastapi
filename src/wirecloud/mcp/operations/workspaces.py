"""Workspace and tab authoring through existing WireCloud operations."""

from fastapi import HTTPException

from wirecloud.catalogue.crud import get_catalogue_resource_by_id
from wirecloud.commons.utils.template.schemas.macdschemas import (
    MACDMashupWithParametrization,
    MACDParametrizationOptions,
)
from wirecloud.database import Id
from wirecloud.mcp.utils import operation_request, paginate, safe_preferences
from wirecloud.platform.workspace import routes
from wirecloud.platform.workspace.crud import change_workspace
from wirecloud.platform.workspace.mashupTemplateGenerator import build_json_template_from_workspace
from wirecloud.platform.workspace.schemas import (
    WorkspaceCreate,
    WorkspaceEntry,
    TabCreate,
    TabCreateEntry,
    MashupMergeService,
)
from wirecloud.platform.workspace.utils import is_owner_or_has_permission


async def get_session_info(adapter, args):
    from wirecloud.mcp.tools import TOOLS

    principal = adapter.principal
    return {
        "user": {"id": str(adapter.user.id), "username": adapter.user.username},
        "scopes": sorted(principal.scopes),
        "tools": [tool.name for tool in TOOLS if set(tool.scopes) <= principal.scopes],
        "connections_url": principal.audience.rsplit("/", 1)[0] + "/oauth2/connections",
        "package_building": "external",
    }


async def list_workspaces(adapter, args):
    items = await adapter.call(routes.get_workspace_list_route)
    return paginate(items, args)


async def get_workspace(adapter, args):
    data = await adapter.call(routes.get_workspace_entry_with_id, workspace_id=Id(args.workspace_id))
    workspace = await adapter.workspace(args.workspace_id)
    return {"workspace": data, "modification_timestamp": adapter.timestamp(workspace)}


def workspace_input(args):
    safe_preferences(args.preferences)
    data = {key: getattr(args, key) for key in ("name", "title", "preferences", "allow_renaming")}
    if not data["name"]:
        del data["name"]
    return data


async def create_workspace(adapter, args):
    return await adapter.call(routes.create_workspace_collection, workspace=WorkspaceCreate(**workspace_input(args)))


async def clone_workspace(adapter, args):
    data = workspace_input(args)
    data["workspace"] = args.source_workspace_id
    return await adapter.call(routes.create_workspace_collection, workspace=WorkspaceCreate(**data))


async def import_mashup(adapter, args):
    data = workspace_input(args)
    await adapter.resource(args.mashup)
    data["mashup"] = args.mashup
    return await adapter.call(routes.create_workspace_collection, workspace=WorkspaceCreate(**data))


async def update_workspace(adapter, args):
    data = args.model_dump(include={"name", "title", "description", "longdescription"})
    return await adapter.call(
        routes.create_workspace_entry,
        workspace_id=Id(args.workspace_id),
        workspace_entry=WorkspaceEntry(**data),
    )


async def delete_workspace(adapter, args):
    workspace = await adapter.workspace(args.workspace_id, edit=True)
    if workspace.creator != adapter.user.id:
        raise HTTPException(403, "Only owned workspaces can be deleted through MCP")
    return await adapter.call(routes.delete_workspace_entry, workspace_id=workspace.id)


async def create_tab(adapter, args):
    return await adapter.call(
        routes.create_tab_collection,
        workspace_id=Id(args.workspace_id),
        tab_create=TabCreate(name=args.name, title=args.title),
    )


async def update_tab(adapter, args):
    return await adapter.call(
        routes.create_tab_entry,
        workspace_id=Id(args.workspace_id),
        tab_id=args.tab_id,
        tab_entry=TabCreateEntry(name=args.name, title=args.title, visible=args.visible),
    )


async def delete_tab(adapter, args):
    return await adapter.call(routes.delete_tab_entry, workspace_id=Id(args.workspace_id), tab_id=args.tab_id)


async def reorder_tabs(adapter, args):
    workspace = await adapter.workspace(args.workspace_id, edit=True)
    if not is_owner_or_has_permission(adapter.user, workspace, "WORKSPACE.TAB.EDIT"):
        raise HTTPException(403, "Insufficient tab permissions")
    if len(args.tab_ids) != len(workspace.tabs) or set(args.tab_ids) != set(workspace.tabs):
        raise HTTPException(422, "Supply every tab ID exactly once")

    workspace.tabs = {key: workspace.tabs[key] for key in args.tab_ids}
    await change_workspace(adapter.db, workspace, adapter.user)
    return {"tab_ids": args.tab_ids}


async def merge_mashup(adapter, args):
    await adapter.resource(args.mashup)
    return await adapter.call(
        routes.process_mashup,
        to_ws_id=Id(args.workspace_id),
        mashup_data=MashupMergeService(workspace="", mashup=args.mashup),
    )


async def export_workspace(adapter, args):
    workspace = await adapter.workspace(args.workspace_id)
    options = MACDMashupWithParametrization(
        type="mashup",
        vendor=args.vendor,
        name=args.name,
        version=args.version,
        title=workspace.title,
        description=workspace.description or "Exported workspace",
        email="",
    )
    # Replace secure/hidden variables before the core serializer can read them.
    for tab in workspace.tabs.values():
        for widget in tab.widgets.values():
            resource = await get_catalogue_resource_by_id(adapter.db, widget.resource)
            if resource is None:
                raise HTTPException(422, "Cannot export a workspace with missing components")
            definitions = list(resource.description.preferences) + list(resource.description.properties)
            hidden = {key for key, value in workspace.forced_values.widget.get(widget.id, {}).items() if value.hidden}
            options.parametrization.iwidgets[widget.id] = {
                variable.name: MACDParametrizationOptions(source="default", value="")
                for variable in definitions
                if variable.secure or getattr(variable, "hidden", False) or variable.name in hidden
            }

    for operator_id, operator in workspace.wiring_status.operators.items():
        resource = await adapter.resource(operator.name)
        hidden = {key for key, value in operator.preferences.items() if value.hidden}
        hidden |= {key for key, value in workspace.forced_values.operator.get(operator_id, {}).items() if value.hidden}
        options.parametrization.ioperators[operator_id] = {
            variable.name: MACDParametrizationOptions(source="default", value="")
            for variable in resource.description.preferences
            if variable.secure or variable.name in hidden
        }

    descriptor = await build_json_template_from_workspace(
        adapter.db,
        operation_request(adapter.request),
        options,
        workspace,
    )
    return {
        "format": "application/json",
        "descriptor": descriptor.model_dump(mode="json", exclude={"parametrization"}),
    }
