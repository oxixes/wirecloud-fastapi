"""Invoke an existing authorized WireCloud operation from another transport.

FastAPI handlers retain their decorators and permission checks. The caller must
supply a server-verified principal and validated typed arguments; this helper
does not accept operation names or URLs from external input.
"""
import inspect
import json

from fastapi import HTTPException, Request, Response
from fastapi.encoders import jsonable_encoder
from fastapi.params import Param, Body


async def invoke_operation(operation, db, user, request, **arguments):
    parameters = inspect.signature(operation).parameters
    values = {"db": db, "user": user, "request": request, **arguments}
    for name, parameter in parameters.items():
        if name not in values and isinstance(parameter.default, (Param, Body)):
            values[name] = parameter.default.default
    result = await operation(**{name: value for name, value in values.items() if name in parameters})
    if isinstance(result, Response):
        body = getattr(result, "body", b"")
        if result.status_code >= 400:
            try:
                details = json.loads(body)
            except (ValueError, TypeError):
                details = {"description": "WireCloud operation failed"}
            raise HTTPException(result.status_code, details)
        if not body:
            return {"ok": True}
        try:
            return json.loads(body)
        except (ValueError, TypeError) as exc:
            raise HTTPException(500, "Unexpected operation response") from exc
    return jsonable_encoder(result) if result is not None else {"ok": True}
