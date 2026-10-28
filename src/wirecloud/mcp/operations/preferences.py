"""Read and update user-editable preferences at explicitly supported targets."""

from fastapi import HTTPException

from wirecloud.database import Id
from wirecloud.mcp.utils import safe_preferences
from wirecloud.platform.preferences import routes

READ_OPERATIONS = {
    "platform": routes.get_platform_preferences,
    "workspace": routes.get_workspace_preferences,
    "tab": routes.get_tab_preferences,
}
WRITE_OPERATIONS = {
    "platform": routes.create_platform_preferences,
    "workspace": routes.create_workspace_preferences,
    "tab": routes.create_tab_preferences,
}


def target_arguments(args):
    if (args.target != "platform" and not args.workspace_id) or (args.target == "tab" and not args.tab_id):
        raise HTTPException(422, "Workspace and tab IDs are required for this preference target")

    identifiers = {}
    if args.target != "platform":
        identifiers["workspace_id"] = Id(args.workspace_id)
    if args.target == "tab":
        identifiers["tab_id"] = args.tab_id
    return identifiers


async def get_preferences(adapter, args):
    return await adapter.call(READ_OPERATIONS[args.target], **target_arguments(args))


async def update_preferences(adapter, args):
    identifiers = target_arguments(args)
    safe_preferences(args.values)
    return await adapter.call(WRITE_OPERATIONS[args.target], preferences=args.values, **identifiers)
