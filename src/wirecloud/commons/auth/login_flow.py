"""Browser login continuation shared by all WireCloud authentication providers."""
from __future__ import annotations

import hmac
import inspect
from typing import Optional, Literal
from datetime import timedelta
from urllib.parse import urlencode, urlsplit, parse_qsl, urlunsplit

from fastapi import APIRouter, HTTPException, Request, Query
from fastapi.responses import RedirectResponse

from wirecloud import settings
from wirecloud.database import DBDep, commit
from wirecloud.commons.auth import tokens
from wirecloud.platform.plugins import get_idm_get_authorization_url_functions

router = APIRouter()


def accepts_context(function):
    parameters = inspect.signature(function).parameters
    return "login_context" in parameters or any(p.kind == p.VAR_KEYWORD for p in parameters.values())


def local_target(target):
    if not target.startswith("/") or target.startswith("//") or "\\" in target or any(ord(c) < 32 for c in target):
        raise HTTPException(400, "Invalid login return destination")
    return target


@router.get("/auth/login")
async def begin_login(request: Request, db: DBDep, return_to: str = "/",
                      next_url: Optional[str] = Query(None, alias="next"),
                      prompt: Optional[Literal["login", "select_account", "consent", "none"]] = None):
    return_to = local_target(next_url or return_to)
    state, browser, verifier = tokens.random_token(), tokens.random_token(), tokens.random_token()
    context = {"state": "wc." + state, "nonce": tokens.random_token(), "code_verifier": verifier,
               "return_to": return_to, "browser": tokens.digest(browser),
               "expires_at": tokens.now() + timedelta(minutes=10)}
    await db.client.oauth_logins.insert_one(dict(context, _id=tokens.digest(context["state"])))
    await commit(db)
    base = tokens.public_base(request)
    if getattr(settings, "OID_CONNECT_ENABLED", False):
        provider = getattr(settings, "OID_CONNECT_PLUGIN", "")
        functions = get_idm_get_authorization_url_functions()
        if provider not in functions:
            raise HTTPException(503, "Authentication provider is unavailable")
        from wirecloud.platform.plugins import get_idm_get_token_functions
        exchange = get_idm_get_token_functions().get(provider)
        context["pkce"] = exchange is not None and accepts_context(exchange)
        context["redirect_uri"] = base + "/oidc/callback"
        function = functions[provider]
        result = function(login_context=context) if accepts_context(function) else function()
        if inspect.isawaitable(result):
            result = await result
        parts = urlsplit(result.urlpattern)
        query = dict(parse_qsl(parts.query))
        query.update(state=context["state"], nonce=context["nonce"], redirect_uri=context["redirect_uri"])
        if prompt:
            query["prompt"] = prompt
        if context["pkce"]:
            query.update(code_challenge=tokens.pkce(verifier), code_challenge_method="S256")
        destination = urlunsplit(parts._replace(query=urlencode(query)))
    else:
        destination = base + "/login?" + urlencode({"continue": context["state"]})
    response = RedirectResponse(destination, 302, headers={"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"})
    response.set_cookie("wc_login_browser", browser, httponly=True, secure=base.startswith("https:"), samesite="lax", max_age=600)
    return response


async def consume_login_attempt(request, db, state=None):
    state = state or request.query_params.get("state", "")
    attempt = await db.client.oauth_logins.find_one_and_delete({"_id": tokens.digest(state),
        "browser": tokens.digest(request.cookies.get("wc_login_browser", "")), "expires_at": {"$gt": tokens.now()}})
    if attempt is None:
        raise HTTPException(400, "Invalid or expired login state")
    await commit(db)
    request.state.login_return_to = local_target(attempt["return_to"])
    return attempt


async def prepare_local_login(request, db):
    state = request.query_params.get("continue")
    if state:
        attempt = await db.client.oauth_logins.find_one({"_id": tokens.digest(state), "expires_at": {"$gt": tokens.now()}})
        if attempt is None or not hmac.compare_digest(attempt["browser"], tokens.digest(request.cookies.get("wc_login_browser", ""))):
            raise HTTPException(400, "Invalid login continuation")
        request.state.login_return_to = local_target(attempt["return_to"])
