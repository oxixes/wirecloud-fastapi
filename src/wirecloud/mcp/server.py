"""Validate original tool arguments before the SDK normalizes function inputs."""
import json

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import ValidationError

from wirecloud.mcp.tools import TOOL_MAP


class WireCloudMCPServer(MCPServer):
    async def list_tools(self):
        tools = await super().list_tools()
        return [tool.model_copy(update={"input_schema": TOOL_MAP[tool.name].model.model_json_schema()})
                if tool.name in TOOL_MAP else tool for tool in tools]

    async def call_tool(self, name, arguments, context):
        spec = TOOL_MAP.get(name)
        if spec is not None:
            try:
                spec.model.model_validate(arguments)
            except ValidationError as exc:
                raise ToolError(json.dumps({"status": 422,
                    "error": exc.errors(include_input=False, include_context=False)})) from exc
        return await super().call_tool(name, arguments, context)
