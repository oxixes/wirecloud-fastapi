# -*- coding: utf-8 -*-
# Copyright (c) 2024 Future Internet Consulting and Development Solutions S.L.
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

import aiohttp
from fastapi import FastAPI, Request
from typing import Callable, Optional, Union
from urllib.parse import urlparse, quote

from src import settings
from src.wirecloud.commons.auth.utils import make_oidc_provider_request
from src.wirecloud.commons.utils.http import get_absolute_reverse_url
from src.wirecloud.platform.plugins import WirecloudPlugin, URLTemplate
from src.wirecloud.translation import gettext as _

# TODO Implement proxy processors
class WirecloudKeycloakPlugin(WirecloudPlugin):
    def __init__(self, app: FastAPI):
        super().__init__(app)


    def get_idm_get_authorization_url_functions(self) -> dict[str, Callable]:
        def get_oidc_authorization_url() -> URLTemplate:
            base_url = getattr(settings, 'OID_CONNECT_DATA')["authorization_endpoint"]
            query_params = {
                'client_id': getattr(settings, 'OID_CONNECT_CLIENT_ID'),
                'response_type': 'code',
                'scope': quote(' '.join(getattr(settings, 'OID_CONNECT_DATA')["scopes"]))
            }

            # Add the query parameters to the URL
            parsed_url = urlparse(base_url)
            query = parsed_url.query
            if query:
                query += '&'

            query += '&'.join(f"{key}={value}" for key, value in query_params.items())

            # Rebuild the URL with the new query parameters
            base_url = parsed_url._replace(query=query).geturl()

            return URLTemplate(urlpattern=base_url, defaults={})

        return {"keycloak": get_oidc_authorization_url}


    def get_idm_get_token_functions(self) -> dict[str, Callable]:
        async def get_oidc_token(code: Optional[str], refresh_token: Optional[str], request: Request) -> dict[str, Union[str, int]]:
            if not code and not refresh_token:
                raise ValueError("Either code or refresh_token must be provided")

            if code:
                redirect_uri = get_absolute_reverse_url('oidc_login_callback', request)

                token_data_to_send = {
                    "code": code,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                    "client_id": getattr(settings, "OID_CONNECT_CLIENT_ID"),
                }

                if getattr(settings, "OID_CONNECT_CLIENT_SECRET", None) is not None:
                    token_data_to_send["client_secret"] = getattr(settings, "OID_CONNECT_CLIENT_SECRET")

                try:
                    token_data = await make_oidc_provider_request(getattr(settings, "OID_CONNECT_DATA")["token_endpoint"],
                                                                  token_data_to_send)
                except Exception as e:
                    raise ValueError(f"Exception while requesting OIDC access token: {str(e)}")

                # Check that the given scope is valid
                given_scopes = token_data["scope"].split(" ")
                for scope in getattr(settings, "OID_CONNECT_DATA")["scopes"]:
                    if scope not in given_scopes:
                        raise ValueError(_("OIDC provider has not returned a valid response: invalid scope"))

                if "access_token" not in token_data or "refresh_token" not in token_data or "refresh_expires_in" not in token_data:
                    raise ValueError(_("OIDC provider has not returned a valid response: missing access_token, refresh_token or refresh_expires_in"))

                return token_data
            else:
                token_data_to_send = {
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token",
                    "client_id": getattr(settings, "OID_CONNECT_CLIENT_ID"),
                }

                if getattr(settings, "OID_CONNECT_CLIENT_SECRET", None) is not None:
                    token_data_to_send["client_secret"] = getattr(settings, "OID_CONNECT_CLIENT_SECRET")

                try:
                    token_data = await make_oidc_provider_request(getattr(settings, "OID_CONNECT_DATA")["token_endpoint"],
                                                                  token_data_to_send)
                except Exception as e:
                    raise ValueError(f"Exception while requesting OIDC access token: {str(e)}")

                if "access_token" not in token_data or "refresh_token" not in token_data or "refresh_expires_in" not in token_data:
                    raise ValueError(_("OIDC provider has not returned a valid response: missing access_token, refresh_token or refresh_expires_in"))

                return token_data

        return {"keycloak": get_oidc_token}


    def get_idm_get_user_functions(self) -> dict[str, Callable]:
        async def get_oidc_user_info(token_data: dict[str, Union[str, int]]) -> dict[str, Union[str, dict]]:
            if not token_data:
                raise ValueError("Access token must be provided")

            try:
                user_data = await make_oidc_provider_request(getattr(settings, "OID_CONNECT_DATA")["userinfo_endpoint"],
                                                             data=None,
                                                             auth=token_data['access_token'])
            except Exception as e:
                raise ValueError(f"Exception while requesting OIDC access token: {str(e)}")

            if "preferred_username" not in user_data:
                raise ValueError(_("OIDC provider has not returned a valid response: missing preferred_username"))

            return user_data

        return {"keycloak": get_oidc_user_info}


    def get_idm_backchannel_logout_functions(self) -> dict[str, Callable]:
        async def backchannel_logout(refresh_token: str) -> None:
            if not refresh_token:
                raise ValueError("Access token must be provided")

            if getattr(settings, "OID_CONNECT_BACKCHANNEL_LOGOUT", False):
                # If the user has an OIDC token, we will try to perform a backchannel logout
                try:
                    data = {
                        "client_id": getattr(settings, "OID_CONNECT_CLIENT_ID"),
                        "refresh_token": refresh_token
                    }

                    if getattr(settings, "OID_CONNECT_CLIENT_SECRET", None) is not None:
                        data["client_secret"] = getattr(settings, "OID_CONNECT_CLIENT_SECRET")

                    await make_oidc_provider_request(
                        getattr(settings, "OID_CONNECT_DATA")["end_session_endpoint"],
                        data=data
                    )
                except Exception as e:
                    # TODO Better logging
                    # Log the error but do not fail the logout process
                    print(f"OIDC backchannel logout failed: {e}")

        return {"keycloak": backchannel_logout}


    def get_config_validators(self) -> tuple[Callable, ...]:
        async def validate_oidc_settings(settings) -> None:
            if getattr(settings, "OID_CONNECT_PLUGIN", "") != "keycloak":
                return

            if getattr(settings, "OID_CONNECT_ENABLED", False):
                if getattr(settings, "OID_CONNECT_DISCOVERY_URL", None):
                    session = aiohttp.ClientSession()
                    try:
                        res = await session.get(
                            getattr(settings, "OID_CONNECT_DISCOVERY_URL"),
                            timeout=5,
                            headers={"Accept": "application/json"},
                            allow_redirects=True,
                            ssl=getattr(settings, "WIRECLOUD_HTTPS_VERIFY", True),
                        )
                    except:
                        await session.close()
                        raise ValueError("OID_CONNECT_DISCOVERY_URL is not valid or reachable")

                    if res.status != 200:
                        await session.close()
                        raise ValueError("OID_CONNECT_DISCOVERY_URL is not valid or reachable")

                    try:
                        data = await res.json()
                    except:
                        await session.close()
                        raise ValueError("OID_CONNECT_DISCOVERY_URL is not valid or reachable")

                    await session.close()

                    if "issuer" not in data:
                        raise ValueError("OID_CONNECT_DISCOVERY_URL does not contain issuer")

                    if "authorization_endpoint" not in data:
                        raise ValueError("OID_CONNECT_DISCOVERY_URL does not contain authorization_endpoint")

                    if "token_endpoint" not in data:
                        raise ValueError("OID_CONNECT_DISCOVERY_URL does not contain token_endpoint")

                    if "userinfo_endpoint" not in data:
                        raise ValueError("OID_CONNECT_DISCOVERY_URL does not contain userinfo_endpoint")

                    if "end_session_endpoint" not in data:
                        raise ValueError("OID_CONNECT_DISCOVERY_URL does not contain end_session_endpoint")

                    if "scopes_supported" not in data:
                        raise ValueError("OID_CONNECT_DISCOVERY_URL does not contain scopes_supported")

                    if "response_types_supported" not in data:
                        raise ValueError("OID_CONNECT_DISCOVERY_URL does not contain response_types_supported")

                    if "grant_types_supported" not in data:
                        raise ValueError("OID_CONNECT_DISCOVERY_URL does not contain grant_types_supported")

                    if type(data["scopes_supported"]) != list:
                        raise ValueError("OID_CONNECT_DISCOVERY_URL scopes_supported is not a list")

                    if type(data["response_types_supported"]) != list:
                        raise ValueError("OID_CONNECT_DISCOVERY_URL response_types_supported is not a list")

                    if type(data["grant_types_supported"]) != list:
                        raise ValueError("OID_CONNECT_DISCOVERY_URL grant_types_supported is not a list")

                    if "openid" not in data["scopes_supported"]:
                        raise ValueError("OID_CONNECT_DISCOVERY_URL scopes_supported does not contain openid")

                    if "profile" not in data["scopes_supported"]:
                        raise ValueError("OID_CONNECT_DISCOVERY_URL scopes_supported does not contain profile")

                    if "code" not in data["response_types_supported"]:
                        raise ValueError("OID_CONNECT_DISCOVERY_URL response_types_supported does not contain code")

                    if "authorization_code" not in data["grant_types_supported"]:
                        raise ValueError(
                            "OID_CONNECT_DISCOVERY_URL grant_types_supported does not contain authorization_code")

                    OID_DATA = {
                        "issuer": data["issuer"],
                        "authorization_endpoint": data["authorization_endpoint"],
                        "token_endpoint": data["token_endpoint"],
                        "end_session_endpoint": data["end_session_endpoint"],
                        "userinfo_endpoint": data["userinfo_endpoint"],
                        "scopes": ["openid", "profile"]
                    }

                    if "email" in data["scopes_supported"]:
                        OID_DATA["scopes"].append("email")

                    if "wirecloud" in data["scopes_supported"]:
                        OID_DATA["scopes"].append("wirecloud")
                    else:
                        print(
                            "WARNING: wirecloud scope not supported by OIDC provider. Users will be created with default permissions.")

                    setattr(settings, "OID_CONNECT_DATA", OID_DATA)
                else:
                    data = getattr(settings, "OID_CONNECT_DATA", None)
                    if not data:
                        raise ValueError("OID_CONNECT_DATA must be set if OID_CONNECT_DISCOVERY_URL is not set")

                    if "issuer" not in data or not isinstance(data["issuer"], str):
                        raise ValueError("OID_CONNECT_DATA must contain issuer as a string")

                    if "authorization_endpoint" not in data or not isinstance(data["authorization_endpoint"], str):
                        raise ValueError("OID_CONNECT_DATA must contain authorization_endpoint as a string")

                    if "token_endpoint" not in data or not isinstance(data["token_endpoint"], str):
                        raise ValueError("OID_CONNECT_DATA must contain token_endpoint as a string")

                    if "userinfo_endpoint" not in data or not isinstance(data["userinfo_endpoint"], str):
                        raise ValueError("OID_CONNECT_DATA must contain userinfo_endpoint as a string")

                    if getattr(settings, "OID_CONNECT_BACKCHANNEL_LOGOUT", False) and (
                            "end_session_endpoint" not in data or not isinstance(data["end_session_endpoint"], str)):
                        raise ValueError("OID_CONNECT_DATA must contain end_session_endpoint as a string if OID_CONNECT_BACKCHANNEL_LOGOUT is enabled")

                    if "scopes" not in data or not isinstance(data["scopes"], list):
                        raise ValueError("OID_CONNECT_DATA must contain scopes as a list")

                    if "openid" not in data["scopes"]:
                        raise ValueError("OID_CONNECT_DATA scopes must contain openid")

        return (validate_oidc_settings,)