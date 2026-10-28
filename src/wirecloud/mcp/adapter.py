"""Authorize MCP operations and coordinate concurrency, transactions, and audit logs."""

from datetime import datetime, timezone
import logging

from bson.errors import InvalidId
from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder

from wirecloud.catalogue.crud import get_catalogue_resource
from wirecloud.commons.utils.operations import invoke_operation
from wirecloud.database import Id, commit, rollback
from wirecloud.mcp.tools import TOOL_MAP
from wirecloud.mcp.utils import operation_request, redact
from wirecloud.platform.workspace.concurrency import write_preconditions
from wirecloud.platform.workspace.crud import get_workspace_by_id

logger = logging.getLogger(__name__)
CREATES_WORKSPACE = {"create_workspace", "clone_workspace", "import_mashup"}


class WireCloudAdapter:
    def __init__(self, db, principal, request):
        self.db = db
        self.principal = principal
        self.request = request
        self.user = principal.user

    async def execute(self, name, arguments):
        tool = TOOL_MAP.get(name)
        if tool is None:
            raise HTTPException(404, "Unknown tool")

        self.principal.require(*tool.scopes)
        args = tool.model.model_validate(arguments)
        conditions = await self.write_conditions(args)
        context = write_preconditions.set(conditions)
        try:
            result = await tool.operation(self, args)
            result = await self.include_timestamp(name, args, conditions, result)
            result = redact(jsonable_encoder(result))
            await commit(self.db)
            self.audit(name, args, "success")
            return result
        except Exception:
            await rollback(self.db)
            self.audit(name, args, "failure")
            raise
        finally:
            write_preconditions.reset(context)

    async def workspace(self, workspace_id, edit=False):
        try:
            workspace = await get_workspace_by_id(self.db, Id(workspace_id))
        except (InvalidId, ValueError, TypeError) as exc:
            raise HTTPException(422, "Invalid workspace ID") from exc
        if workspace is None:
            raise HTTPException(404, "Workspace not found")

        allowed = (
            await workspace.is_editable_by(self.db, self.user)
            if edit
            else await workspace.is_accessible_by(self.db, self.user)
        )
        if not allowed:
            raise HTTPException(403, "Insufficient workspace permissions")
        return workspace

    async def resource(self, identifier):
        resource = await get_catalogue_resource(self.db, *identifier.split("/"))
        if resource is None or not resource.is_available_for(self.user):
            raise HTTPException(404, "Resource not available")
        return resource

    async def call(self, operation, body=None, content_type="application/json", **kwargs):
        request = operation_request(self.request, body, content_type)
        return await invoke_operation(operation, self.db, self.user, request, **kwargs)

    async def write_conditions(self, args):
        workspace_id = getattr(args, "workspace_id", None)
        if not workspace_id:
            return {}

        workspace = await self.workspace(workspace_id)
        if not hasattr(args, "expected_last_modified"):
            return {}

        expected = args.expected_last_modified
        if expected:
            try:
                timestamp = datetime.fromisoformat(expected.replace("Z", "+00:00"))
            except ValueError as exc:
                raise HTTPException(422, "Invalid modification timestamp") from exc
            if timestamp != workspace.last_modified.replace(tzinfo=timezone.utc):
                raise HTTPException(409, "Workspace changed; read it again before editing")
        return {str(workspace.id): workspace.last_modified}

    async def include_timestamp(self, name, args, conditions, result):
        if name in CREATES_WORKSPACE and result.get("id"):
            workspace = await self.workspace(result["id"])
            result["modification_timestamp"] = self.timestamp(workspace)
        if conditions and name != "delete_workspace":
            workspace = await self.workspace(args.workspace_id)
            return {"result": result, "modification_timestamp": self.timestamp(workspace)}
        return result

    @staticmethod
    def timestamp(workspace) -> str:
        return workspace.last_modified.replace(tzinfo=timezone.utc).isoformat()

    def audit(self, name, args, outcome):
        logger.info(
            "MCP operation",
            extra={
                "wirecloud_user": str(self.user.id),
                "oauth_client": self.principal.client_id,
                "oauth_grant": self.principal.grant_id,
                "operation": name,
                "target": getattr(args, "workspace_id", getattr(args, "resource", None)),
                "outcome": outcome,
            },
        )
