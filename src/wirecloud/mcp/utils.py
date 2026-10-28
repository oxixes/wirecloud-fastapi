"""Output redaction and safe input shared by MCP operations."""

import json

from fastapi import HTTPException, Request

BLOCKED_PREFERENCES = {"public", "sharelist", "requireauth", "searchable", "permissions", "owner", "creator"}
PRIVATE_FIELDS = {"password", "idm_data", "token_data", "csrf_token", "variable_values", "forced_values"}


def redact(value):
    if isinstance(value, dict):
        secret = value.get("secure") is True or value.get("hidden") is True
        blocked = PRIVATE_FIELDS
        if secret:
            blocked = blocked | {"value", "default", "users", "defaultValue"}

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


def operation_request(original: Request, body=None, content_type="application/json") -> Request:
    """Call core operations without forwarding the client's cookies or bearer token."""
    scope = dict(original.scope)
    scope["headers"] = [
        (b"accept", b"application/json"),
        (b"content-type", content_type.encode()),
        (b"user-agent", b"WireCloud-MCP/1.0"),
    ]
    scope["query_string"] = b""
    scope["state"] = {"lang": getattr(original.state, "lang", "en")}
    request = Request(scope)
    request._body = json.dumps(body or {}).encode()
    return request


def paginate(items, args):
    filtered = [item for item in items if args.query.casefold() in json.dumps(item).casefold()]
    end = args.offset + args.limit
    return {
        "items": filtered[args.offset : end],
        "total": len(filtered),
        "next_offset": end if end < len(filtered) else None,
    }
