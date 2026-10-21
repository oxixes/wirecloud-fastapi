"""The sole boundary between MCP and WireCloud's authorized operations."""
from __future__ import annotations

import json
import logging
import hashlib
import jsonpatch
from datetime import datetime, timezone
from urllib.parse import urlsplit

from bson.errors import InvalidId
from fastapi import HTTPException, Request
from fastapi.encoders import jsonable_encoder

from wirecloud.database import Id, commit, rollback
from wirecloud.commons.utils.operations import invoke_operation
from wirecloud.platform.workspace.concurrency import write_preconditions
from wirecloud.platform.workspace import routes as workspaces
from wirecloud.platform.workspace.crud import get_workspace_by_id, change_workspace
from wirecloud.platform.workspace.utils import is_owner_or_has_permission
from wirecloud.platform.iwidget import routes as widgets
from wirecloud.platform.preferences import routes as preferences
from wirecloud.platform.wiring import routes as wiring
from wirecloud.platform.localcatalogue import routes as resources
from wirecloud.platform.workspace.schemas import WorkspaceCreate, WorkspaceEntry, TabCreate, TabCreateEntry, MashupMergeService
from wirecloud.platform.iwidget.schemas import WidgetInstanceDataCreate, WidgetInstanceDataUpdate
from wirecloud.platform.wiring.schemas import WiringEntryPatch
from wirecloud.mcp import packages
from wirecloud.mcp.layout import component_nodes, placement_patches
from wirecloud.mcp.tools import TOOLS, TOOL_MAP

logger = logging.getLogger(__name__)
BLOCKED_PREFERENCES = {"public", "sharelist", "requireauth", "searchable", "permissions", "owner", "creator"}


def redact(value):
    if isinstance(value, dict):
        secret = value.get("secure") is True or value.get("hidden") is True
        blocked = {"password", "idm_data", "token_data", "csrf_token", "variable_values", "forced_values"}
        if secret:
            blocked |= {"value", "default", "users", "defaultValue"}
        result = {key: redact(item) for key, item in value.items() if key not in blocked}
        if secret:
            result["has_value"] = bool(value.get("value"))
        if result.get("value") == "********":
            result.pop("value")
            result["has_value"] = True
        return result
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value


def safe_preferences(values):
    if set(values) & BLOCKED_PREFERENCES:
        raise HTTPException(403, "Sharing, authentication, and publishing settings are unavailable through MCP")
    return values


def operation_request(original, body=None, content_type="application/json"):
    scope = dict(original.scope)
    scope["headers"] = [(b"accept", b"application/json"), (b"content-type", content_type.encode()), (b"user-agent", b"WireCloud-MCP/1.0")]
    scope["query_string"] = b""
    scope["state"] = {"lang": getattr(original.state, "lang", "en")}
    request = Request(scope)
    request._body = json.dumps(body or {}).encode()
    return request


class WireCloudAdapter:
    def __init__(self, db, principal, request):
        self.db, self.principal, self.request = db, principal, request
        self.user = principal.user

    async def workspace(self, workspace_id, edit=False):
        try:
            workspace = await get_workspace_by_id(self.db, Id(workspace_id))
        except (InvalidId, ValueError, TypeError) as exc:
            raise HTTPException(422, "Invalid workspace ID") from exc
        if workspace is None:
            raise HTTPException(404, "Workspace not found")
        allowed = await workspace.is_editable_by(self.db, self.user) if edit else await workspace.is_accessible_by(self.db, self.user)
        if not allowed:
            raise HTTPException(403, "Insufficient workspace permissions")
        return workspace

    async def call(self, operation, body=None, content_type="application/json", **kwargs):
        return await invoke_operation(operation, self.db, self.user, operation_request(self.request, body, content_type), **kwargs)

    async def execute(self, name, arguments):
        spec = TOOL_MAP.get(name)
        if spec is None:
            raise HTTPException(404, "Unknown tool")
        self.principal.require(*spec.scopes)
        args = spec.model.model_validate(arguments)
        conditions = {}
        if hasattr(args, "workspace_id") and args.workspace_id:
            workspace = await self.workspace(args.workspace_id)
            if hasattr(args, "expected_last_modified"):
                expected = args.expected_last_modified
                if expected:
                    try:
                        timestamp = datetime.fromisoformat(expected.replace("Z", "+00:00"))
                    except ValueError as exc:
                        raise HTTPException(422, "Invalid modification timestamp") from exc
                    actual = workspace.last_modified.replace(tzinfo=timezone.utc)
                    if timestamp != actual:
                        raise HTTPException(409, "Workspace changed; read it again before editing")
                conditions[str(workspace.id)] = workspace.last_modified
        context = write_preconditions.set(conditions)
        try:
            result = await self.run(name, args)
            if name in ("create_workspace", "clone_workspace", "import_mashup") and result.get("id"):
                current = await self.workspace(result["id"])
                result["modification_timestamp"] = current.last_modified.replace(tzinfo=timezone.utc).isoformat()
            if conditions and getattr(args, "workspace_id", None) and name != "delete_workspace":
                current = await self.workspace(args.workspace_id)
                result = {"result": result, "modification_timestamp": current.last_modified.replace(tzinfo=timezone.utc).isoformat()}
            result = redact(jsonable_encoder(result))
            await commit(self.db)
            logger.info("MCP operation", extra={"wirecloud_user": str(self.user.id), "oauth_client": self.principal.client_id,
                "oauth_grant": self.principal.grant_id, "operation": name,
                "target": getattr(args, "workspace_id", getattr(args, "resource", None)), "outcome": "success"})
            return result
        except Exception:
            await rollback(self.db)
            logger.info("MCP operation", extra={"wirecloud_user": str(self.user.id), "oauth_client": self.principal.client_id,
                "oauth_grant": self.principal.grant_id, "operation": name, "outcome": "failure"})
            raise
        finally:
            write_preconditions.reset(context)

    async def run(self, name, args):
        if name == "get_session_info":
            return {"user": {"id": str(self.user.id), "username": self.user.username},
                    "scopes": sorted(self.principal.scopes), "tools": [t.name for t in TOOLS if set(t.scopes) <= self.principal.scopes],
                    "connections_url": self.principal.audience.rsplit("/", 1)[0] + "/oauth2/connections", "package_building": "external"}
        if name == "list_workspaces":
            items = await self.call(workspaces.get_workspace_list_route)
            return self.paginate(items, args)
        if name in ("get_workspace", "get_wiring"):
            data = await self.call(workspaces.get_workspace_entry_with_id, workspace_id=Id(args.workspace_id))
            workspace = await self.workspace(args.workspace_id)
            return {"workspace" if name == "get_workspace" else "wiring": data if name == "get_workspace" else data.get("wiring", {}),
                    "modification_timestamp": workspace.last_modified.replace(tzinfo=timezone.utc).isoformat()}
        if name in ("create_workspace", "clone_workspace", "import_mashup"):
            safe_preferences(args.preferences)
            data = {key: getattr(args, key) for key in ("name", "title", "preferences", "allow_renaming")}
            if not data["name"]:
                del data["name"]
            if name == "clone_workspace":
                data["workspace"] = args.source_workspace_id
            elif name == "import_mashup":
                await self.resource(args.mashup)
                data["mashup"] = args.mashup
            return await self.call(workspaces.create_workspace_collection, workspace=WorkspaceCreate(**data))
        if name == "update_workspace":
            return await self.call(workspaces.create_workspace_entry, workspace_id=Id(args.workspace_id),
                workspace_entry=WorkspaceEntry(**args.model_dump(include={"name", "title", "description", "longdescription"})))
        if name == "delete_workspace":
            workspace = await self.workspace(args.workspace_id, edit=True)
            if workspace.creator != self.user.id:
                raise HTTPException(403, "Only owned workspaces can be deleted through MCP")
            return await self.call(workspaces.delete_workspace_entry, workspace_id=workspace.id)
        if name == "create_tab":
            return await self.call(workspaces.create_tab_collection, workspace_id=Id(args.workspace_id),
                tab_create=TabCreate(name=args.name, title=args.title))
        if name == "update_tab":
            return await self.call(workspaces.create_tab_entry, workspace_id=Id(args.workspace_id), tab_id=args.tab_id,
                tab_entry=TabCreateEntry(name=args.name, title=args.title, visible=args.visible))
        if name == "delete_tab":
            return await self.call(workspaces.delete_tab_entry, workspace_id=Id(args.workspace_id), tab_id=args.tab_id)
        if name == "reorder_tabs":
            workspace = await self.workspace(args.workspace_id, edit=True)
            if not is_owner_or_has_permission(self.user, workspace, "WORKSPACE.TAB.EDIT"):
                raise HTTPException(403, "Insufficient tab permissions")
            if len(args.tab_ids) != len(workspace.tabs) or set(args.tab_ids) != set(workspace.tabs):
                raise HTTPException(422, "Supply every tab ID exactly once")
            workspace.tabs = {key: workspace.tabs[key] for key in args.tab_ids}
            await change_workspace(self.db, workspace, self.user)
            return {"tab_ids": args.tab_ids}
        if name == "add_widget":
            await self.resource(args.resource)
            return await self.call(widgets.create_widget_instance_collection, workspace_id=Id(args.workspace_id), tab_id=args.tab_id,
                iwidget=WidgetInstanceDataCreate(title=args.title, widget=args.resource, layouts=args.layouts))
        if name == "update_widget":
            if args.resource:
                await self.resource(args.resource)
            return await self.call(widgets.update_widget_instance_entry, workspace_id=Id(args.workspace_id), tab_id=args.tab_id,
                iwidget_id=args.widget_id, iwidget_data=WidgetInstanceDataUpdate(title=args.title, widget=args.resource,
                    tab=args.destination_tab_id, layouts=args.layouts))
        if name == "remove_widget":
            return await self.call(widgets.delete_widget_instance_entry, workspace_id=Id(args.workspace_id),
                tab_id=args.tab_id, iwidget_id=args.widget_id)
        if name == "set_widget_variables":
            workspace = await self.workspace(args.workspace_id)
            hidden = workspace.forced_values.widget.get(args.widget_id, {})
            if any(key in hidden for key in args.values):
                raise HTTPException(403, "Forced widget values cannot be changed")
            operation = widgets.update_widget_instance_preferences if args.kind == "preferences" else widgets.update_widget_instance_properties
            return await self.call(operation, workspace_id=Id(args.workspace_id), tab_id=args.tab_id,
                iwidget_id=args.widget_id, new_values=args.values)
        if name in ("get_preferences", "update_preferences"):
            return await self.preference_operation(name, args)
        if name in ("add_operator", "update_operator", "remove_operator", "connect_components", "disconnect_components", "layout_wiring"):
            return await self.wiring_operation(name, args)
        if name == "list_resources":
            data = await self.call(resources.get_resource_collection, process_urls=True)
            return self.paginate([dict(value, resource=key) for key, value in data.items()], args)
        if name in ("get_resource", "get_resource_documentation"):
            resource = await self.resource(args.resource)
            info = jsonable_encoder(resource.get_processed_info(self.request, process_variables=True))
            if name == "get_resource_documentation":
                result = {key: info.get(key) for key in ("title", "description", "longdescription", "doc", "changelog", "homepage")}
                from wirecloud.catalogue.utils import wgt_deployer
                from wirecloud.commons.utils.wgt import WgtFile
                from wirecloud.commons.utils.template import TemplateParser
                import os
                package = WgtFile(os.path.join(wgt_deployer.get_base_dir(resource.vendor, resource.short_name, resource.version), resource.template_uri))
                try:
                    descriptor = TemplateParser(package.get_template()).get_resource_info()
                    raw_doc = descriptor.doc
                    if raw_doc and not urlsplit(raw_doc).scheme and not raw_doc.startswith("/"):
                        candidates = [raw_doc, raw_doc.rstrip("/") + "/index.md", raw_doc.rstrip("/") + "/index.html"]
                        for path in candidates:
                            if path in package.namelist():
                                content = package.read(path)
                                result["documentation"] = content[:65536].decode("utf-8", errors="replace")
                                result["truncated"] = len(content) > 65536
                                break
                finally:
                    package.close()
                return result
            return info
        if name == "validate_resource_package":
            _, info = packages.validate_package(packages.decode_package(args.package_base64))
            return {"valid": True, "descriptor": jsonable_encoder(info)}
        if name == "install_resource":
            return await self.install(args)
        if name == "uninstall_resource":
            vendor, short_name, version = args.resource.split("/")
            if not (self.user.has_perm("COMPONENT.UNINSTALL") or self.user.is_superuser):
                raise HTTPException(403, "Component uninstall permission is required")
            return await self.call(resources.delete_resource_entry_version, vendor=vendor, name=short_name,
                version=version, allusers=False, affected=True)
        if name == "merge_mashup":
            await self.resource(args.mashup)
            return await self.call(workspaces.process_mashup, to_ws_id=Id(args.workspace_id),
                mashup_data=MashupMergeService(workspace="", mashup=args.mashup))
        if name == "export_workspace":
            return await self.export(args)
        raise HTTPException(404, "Unknown operation")

    @staticmethod
    def paginate(items, args):
        filtered = [item for item in items if args.query.casefold() in json.dumps(item).casefold()]
        return {"items": filtered[args.offset:args.offset + args.limit], "total": len(filtered),
                "next_offset": args.offset + args.limit if args.offset + args.limit < len(filtered) else None}

    async def resource(self, identifier):
        from wirecloud.catalogue.crud import get_catalogue_resource
        resource = await get_catalogue_resource(self.db, *identifier.split("/"))
        if resource is None or not resource.is_available_for(self.user):
            raise HTTPException(404, "Resource not available")
        return resource

    async def preference_operation(self, name, args):
        write = name == "update_preferences"
        target = args.target
        if target != "platform" and not args.workspace_id or target == "tab" and not args.tab_id:
            raise HTTPException(422, "Workspace and tab IDs are required for this preference target")
        kwargs = {}
        if target != "platform":
            kwargs["workspace_id"] = Id(args.workspace_id)
        if target == "tab":
            kwargs["tab_id"] = args.tab_id
        if write:
            safe_preferences(args.values)
            kwargs["preferences"] = args.values
        operation = getattr(preferences, ("create_" if write else "get_") + target + "_preferences")
        return await self.call(operation, **kwargs)

    async def wiring_operation(self, name, args):
        workspace = await self.workspace(args.workspace_id, edit=name == "layout_wiring")
        if name == "layout_wiring" and not is_owner_or_has_permission(self.user, workspace, "WORKSPACE.WIRING.EDIT"):
            raise HTTPException(403, "Insufficient wiring permissions")
        old = workspace.wiring_status
        patches = []
        if name == "add_operator":
            resource = await self.resource(args.resource)
            if resource.resource_type() != "operator":
                raise HTTPException(422, "An operator resource is required")
            self.validate_operator_preferences(resource, args.preferences)
            operator_id = str(max((int(key) for key in old.operators), default=-1) + 1)
            patches.append({"op": "add", "path": "/operators/" + operator_id,
                "value": {"id": operator_id, "name": args.resource,
                          "preferences": {key: {"value": value} for key, value in args.preferences.items()}, "properties": {}}})
        elif name in ("update_operator", "remove_operator"):
            if args.operator_id not in old.operators:
                raise HTTPException(404, "Operator not found")
            operator_id = args.operator_id
            if name == "remove_operator":
                if not is_owner_or_has_permission(self.user, workspace, "WORKSPACE.OPERATOR.DELETE"):
                    raise HTTPException(403, "Operator deletion permission is required")
                patches.append({"op": "remove", "path": "/operators/" + operator_id})
                descriptions = [("/visualdescription", old.visualdescription)] + [
                    (f"/visualdescription/behaviours/{index}", behaviour)
                    for index, behaviour in enumerate(old.visualdescription.behaviours)]
                for path, description in descriptions:
                    if operator_id in description.components.operator:
                        patches.append({"op": "remove", "path": path + "/components/operator/" + operator_id})
                    prefix = f"operator/{operator_id}/"
                    for index in range(len(description.connections) - 1, -1, -1):
                        connection = description.connections[index]
                        if connection.sourcename.startswith(prefix) or connection.targetname.startswith(prefix):
                            patches.append({"op": "remove", "path": path + "/connections/" + str(index)})
                for index in range(len(old.connections) - 1, -1, -1):
                    connection = old.connections[index]
                    if any(endpoint.type.value == "operator" and endpoint.id == operator_id for endpoint in (connection.source, connection.target)):
                        patches.append({"op": "remove", "path": "/connections/" + str(index)})
            else:
                resource = await self.resource(old.operators[operator_id].name)
                self.validate_operator_preferences(resource, args.preferences)
                # Patch only supplied preferences: never round-trip masked secrets.
                for key, value in args.preferences.items():
                    escaped = key.replace("~", "~0").replace("/", "~1")
                    patches.append({"op": "add", "path": f"/operators/{operator_id}/preferences/{escaped}", "value": {"value": value}})
        elif name == "connect_components":
            await self.validate_connection(workspace, args.source, args.target)
            patches.append({"op": "add", "path": "/connections/-", "value": {"source": args.source.model_dump(mode="json"),
                "target": args.target.model_dump(mode="json"), "readonly": False}})
        elif name == "disconnect_components":
            if not is_owner_or_has_permission(self.user, workspace, "WORKSPACE.WIRING.DELETE"):
                raise HTTPException(403, "Connection deletion permission is required")
            if args.connection_index >= len(old.connections):
                raise HTTPException(404, "Connection not found")
            patches.append({"op": "remove", "path": "/connections/" + str(args.connection_index)})
        if name == "remove_operator" and any(patch["path"].startswith("/connections/") for patch in patches) and not is_owner_or_has_permission(self.user, workspace, "WORKSPACE.WIRING.DELETE"):
            raise HTTPException(403, "Connection deletion permission is required")
        positioned = 0
        if name in ("add_operator", "connect_components", "layout_wiring"):
            proposed = type(old).model_validate(jsonpatch.apply_patch(old.model_dump(), patches))
            layout = await self.wiring_layout_patches(workspace, proposed,
                moves=args.positions if name == "layout_wiring" else (),
                preserve_existing=args.preserve_existing if name == "layout_wiring" else True)
            positioned = len(layout)
            patches.extend(layout)
        if name == "layout_wiring" and not patches:
            return {"positioned": 0}
        result = await self.call(wiring.patch_wiring_entry, workspace_id=workspace.id,
            req=[WiringEntryPatch(**patch) for patch in patches], content_type="application/json-patch+json")
        if name == "add_operator":
            return {"operator_id": operator_id, "result": result}
        if name == "layout_wiring":
            return {"positioned": positioned}
        return result

    async def wiring_layout_patches(self, workspace, status, moves=(), preserve_existing=True):
        from wirecloud.catalogue.crud import get_catalogue_resource, get_catalogue_resource_by_id
        widgets = {widget.id: widget for tab in workspace.tabs.values() for widget in tab.widgets.values()}
        valid_nodes = {("widget", key) for key in widgets} | {("operator", key) for key in status.operators}
        nodes = component_nodes(status, valid_nodes, moves)
        heights, resources_by_id = {}, {}
        for kind, key in sorted(nodes):
            identifier = widgets[key].resource if kind == "widget" else status.operators[key].name
            cache_key = (kind, str(identifier))
            if cache_key not in resources_by_id:
                resources_by_id[cache_key] = (await get_catalogue_resource_by_id(self.db, identifier) if kind == "widget"
                    else await get_catalogue_resource(self.db, *identifier.split("/")))
            resource = resources_by_id[cache_key]
            if resource is not None:
                endpoints = resource.description.wiring
                heights[(kind, key)] = max(240, 110 + 35 * max(len(endpoints.inputs), len(endpoints.outputs)))
        return placement_patches(status, nodes, heights, moves, preserve_existing)

    async def validate_connection(self, workspace, source, target):
        from wirecloud.catalogue.crud import get_catalogue_resource_by_id
        definitions = []
        for endpoint, direction in ((source, "outputs"), (target, "inputs")):
            if endpoint.type.value == "operator":
                operator = workspace.wiring_status.operators.get(endpoint.id)
                if operator is None:
                    raise HTTPException(404, "Operator endpoint not found")
                resource = await self.resource(operator.name)
            else:
                widget = next((widget for tab in workspace.tabs.values() for widget in tab.widgets.values() if widget.id == endpoint.id), None)
                if widget is None:
                    raise HTTPException(404, "Widget endpoint not found")
                resource = await get_catalogue_resource_by_id(self.db, widget.resource)
                if resource is None or not resource.is_available_for(self.user):
                    raise HTTPException(404, "Endpoint resource not available")
            definition = next((value for value in getattr(resource.description.wiring, direction) if value.name == endpoint.endpoint), None)
            if definition is None:
                raise HTTPException(422, "Unknown component endpoint: " + endpoint.endpoint)
            definitions.append(definition)
        if definitions[0].type != definitions[1].type:
            raise HTTPException(422, "Wiring endpoint types are incompatible")

    @staticmethod
    def validate_operator_preferences(resource, values):
        definitions = {preference.name: preference for preference in resource.description.preferences}
        for name in values:
            if name not in definitions:
                raise HTTPException(422, "Unknown operator preference: " + name)
            if definitions[name].readonly or getattr(definitions[name], "hidden", False):
                raise HTTPException(403, "Read-only and hidden preferences cannot be changed")

    async def install(self, args):
        if not (self.user.has_perm("COMPONENT.INSTALL") or self.user.is_superuser):
            raise HTTPException(403, "Component install permission is required")
        if args.url:
            parsed = urlsplit(args.url)
            if parsed.scheme not in ("https", "http") or not parsed.hostname or parsed.username or parsed.password:
                raise HTTPException(422, "An HTTP(S) package URL without embedded credentials is required")
            from wirecloud.proxy.routes import WIRECLOUD_PROXY
            from wirecloud.proxy.schemas import ProxyRequestData
            response = await WIRECLOUD_PROXY.do_request(operation_request(self.request), args.url, "GET",
                ProxyRequestData(headers={"Accept-Encoding": "identity"}), self.db, user=self.user)
            if response is None or not 200 <= response.status_code < 300:
                raise HTTPException(409, "Package cannot be downloaded through the configured proxy")
            content = bytearray()
            try:
                if hasattr(response, "body_iterator"):
                    async for chunk in response.body_iterator:
                        content.extend(chunk)
                        if len(content) > packages.PACKAGE_LIMIT:
                            raise HTTPException(413, "Downloaded package exceeds 100 MiB")
                else:
                    content.extend(response.body)
            finally:
                if response.background:
                    await response.background()
            content = bytes(content)
        elif args.package_base64 is not None:
            content = packages.decode_package(args.package_base64)
        else:
            content = await packages.consume_upload(self.db, self.principal, args.upload_id)
        package, info = packages.validate_package(content)
        from wirecloud.platform.localcatalogue.utils import fix_dev_version, install_component
        from wirecloud.catalogue.search import add_resource_to_index
        from wirecloud.catalogue.crud import get_catalogue_resource
        from wirecloud.catalogue.utils import wgt_deployer
        import os
        # Embedded resources must go through the same bounded validator and installer.
        embedded = list(getattr(info, "embedded", [])) if args.install_embedded_resources else []
        for item in embedded:
            if item.src.startswith(("http:", "https:")):
                raise HTTPException(422, "Install remote embedded dependencies explicitly before installing this mashup")
            child = package.read(item.src)
            packages.validate_package(child)
        for child_content in [package.read(item.src) for item in embedded] + [content]:
            child, _ = packages.validate_package(child_content)
            fix_dev_version(child, self.user)
            effective = packages.TemplateParser(child.get_template()).get_resource_info()
            existing = await get_catalogue_resource(self.db, effective.vendor, effective.name, effective.version)
            reused = existing is not None and "-dev" not in effective.version
            if reused:
                stored_hash = hashlib.sha256()
                with open(os.path.join(wgt_deployer.get_base_dir(existing.vendor, existing.short_name, existing.version), existing.template_uri), "rb") as stored:
                    for chunk in iter(lambda: stored.read(1024 * 1024), b""):
                        stored_hash.update(chunk)
                if stored_hash.digest() != hashlib.sha256(child_content).digest():
                    raise HTTPException(409, "An immutable resource version already exists with different contents; use a new version")
            added, resource = await install_component(self.db, child, executor_user=self.user, public=False, users=[self.user], groups=[])
            await add_resource_to_index(self.db, resource)
        return {"installed": added, "reused_existing": reused, "resource": resource.local_uri_part,
                "descriptor": jsonable_encoder(resource.get_processed_info(self.request))}

    async def export(self, args):
        from wirecloud.commons.utils.template.schemas.macdschemas import MACDMashupWithParametrization, MACDParametrizationOptions
        from wirecloud.platform.workspace.mashupTemplateGenerator import build_json_template_from_workspace
        from wirecloud.catalogue.crud import get_catalogue_resource_by_id
        workspace = await self.workspace(args.workspace_id)
        options = MACDMashupWithParametrization(type="mashup", vendor=args.vendor, name=args.name,
            version=args.version, title=workspace.title, description=workspace.description or "Exported workspace", email="")
        # Use defaults for secure/hidden variables before serialization can read their stored values.
        for tab in workspace.tabs.values():
            for widget in tab.widgets.values():
                resource = await get_catalogue_resource_by_id(self.db, widget.resource)
                if resource is None:
                    raise HTTPException(422, "Cannot export a workspace with missing components")
                definitions = list(resource.description.preferences) + list(resource.description.properties)
                hidden = {key for key, value in workspace.forced_values.widget.get(widget.id, {}).items() if value.hidden}
                options.parametrization.iwidgets[widget.id] = {v.name: MACDParametrizationOptions(source="default", value="")
                    for v in definitions if v.secure or getattr(v, "hidden", False) or v.name in hidden}
        for operator_id, operator in workspace.wiring_status.operators.items():
            resource = await self.resource(operator.name)
            hidden = {key for key, value in operator.preferences.items() if value.hidden}
            hidden |= {key for key, value in workspace.forced_values.operator.get(operator_id, {}).items() if value.hidden}
            options.parametrization.ioperators[operator_id] = {v.name: MACDParametrizationOptions(source="default", value="")
                for v in resource.description.preferences if v.secure or v.name in hidden}
        result = await build_json_template_from_workspace(self.db, operation_request(self.request), options, workspace)
        return {"format": "application/json", "descriptor": result.model_dump(mode="json", exclude={"parametrization"})}
