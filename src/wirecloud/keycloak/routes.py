# -*- coding: utf-8 -*-
# Copyright (c) 2026 Future Internet Consulting and Development Solutions S.L.

# This file is part of Wirecloud.

# Wirecloud is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# Wirecloud is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with Wirecloud.  If not, see <http://www.gnu.org/licenses/>.

from fastapi import APIRouter, Request, Response, Form
from typing import Annotated
import jwt

from src.wirecloud.commons.auth.crud import invalidate_tokens_by_idm_session, update_user, invalidate_all_user_tokens
from src.wirecloud.commons.utils.http import build_error_response, consumes
from src.wirecloud.database import DBDep
from src.wirecloud.keycloak.crud import get_user_by_idm_user_id
from src.wirecloud.keycloak import docs
from src.wirecloud import docs as root_docs
from src import settings

keycloak_router = APIRouter()

@keycloak_router.post(
    "/oidc/k_logout",
    summary=docs.keycloak_backchannel_logout_summary,
    description=docs.keycloak_backchannel_logout_description,
    response_class=Response,
    status_code=204,
    responses={
        204: {"description": docs.keycloak_backchannel_logout_no_content_response_description},
        400: root_docs.generate_error_response_openapi_description(
            docs.keycloak_backchannel_logout_bad_request_response_description,
            "Invalid token"
        ),
        415: root_docs.generate_unsupported_media_type_response_openapi_description(
            docs.keycloak_backchannel_logout_unsupported_media_type_response_description),
        422: root_docs.generate_validation_error_response_openapi_description(
            docs.keycloak_backchannel_logout_validation_error_response_description)
    }
)
@consumes(["application/x-www-form-urlencoded"])
async def keycloak_backchannel_logout(db: DBDep, request: Request, logout_token: Annotated[str, Form(
    ..., description=docs.keycloak_backchannel_logout_logout_token_description)]):
    # Parse body as form data

    header = jwt.get_unverified_header(logout_token)
    if 'kid' not in header:
        return build_error_response(request, 400, "Invalid token: missing 'kid' in header.")

    if header['kid'] not in getattr(settings, "OID_CONNECT_DATA")["keys"]:
        return build_error_response(request, 400, "Invalid token: unknown 'kid'.")

    key = getattr(settings, "OID_CONNECT_DATA")["keys"][header['kid']]
    alg = header.get('alg', 'RS256')

    try:
        decoded_token = jwt.decode(logout_token,
                                   key=key,
                                   algorithms=[alg],
                                   audience=getattr(settings, "OID_CONNECT_CLIENT_ID"),
                                   issuer=getattr(settings, "OID_CONNECT_DATA")["issuer"],
                                   require=["exp", "sub", "iat", "iss"],
                                   options={"verify_exp": True, "verify_aud": True, "verify_iss": True})
    except Exception:
        return build_error_response(request, 400, "Invalid token: could not be decoded or verified.")

    if 'typ' not in decoded_token or decoded_token['typ'] != 'Logout':
        return build_error_response(request, 400, "Invalid token: incorrect 'typ' claim.")

    user = await get_user_by_idm_user_id(db, decoded_token['sub'])
    if user is None:
        return build_error_response(request, 400, "Invalid token: user not found.")

    if 'sid' in decoded_token:
        await invalidate_tokens_by_idm_session(db, decoded_token['sid'])
        if ('keycloak' not in user.idm_data or 'idm_session' not in user.idm_data['keycloak']) or \
              user.idm_data['keycloak']['idm_session'] != decoded_token['sid']:
            return Response(status_code=204)
        else:
            # Remove idm_data.keycloak
            del user.idm_data['keycloak']
            await update_user(db, user)
    else:
        await invalidate_all_user_tokens(db, user.id)
        del user.idm_data['keycloak']
        await update_user(db, user)

    return Response(status_code=204)