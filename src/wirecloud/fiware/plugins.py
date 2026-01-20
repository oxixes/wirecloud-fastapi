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

import os
import base64
import logging
from typing import Optional, Callable, Union, Any
from urllib.parse import quote, urlparse, urljoin

from fastapi import FastAPI, Request

from src import settings
from wirecloud import fiware
from wirecloud.commons.auth.schemas import UserAll, Session
from wirecloud.commons.auth.utils import make_oidc_provider_request
from wirecloud.database import DBSession
from wirecloud.platform.context.schemas import BaseContextKey
from wirecloud.platform.core.plugins import populate_component
from wirecloud.platform.markets.models import MarketOptions
from wirecloud.platform.markets.utils import MarketManager
from wirecloud.platform.plugins import WirecloudPlugin, URLTemplate
from wirecloud.platform.workspace.crud import create_workspace, get_workspace_by_username_and_name
from wirecloud.translation import gettext as _

BASE_PATH = os.path.dirname(__file__)
BAE_BROWSER_WIDGET = os.path.join(BASE_PATH, 'initial', 'CoNWeT_bae-browser_0.1.1.wgt')
BAE_DETAILS_WIDGET = os.path.join(BASE_PATH, 'initial', 'CoNWeT_bae-details_0.1.1.wgt')
BAE_SEARCH_FILTERS_WIDGET = os.path.join(BASE_PATH, 'initial', 'CoNWeT_bae-search-filters_0.1.1.wgt')
BAE_MASHUP = os.path.join(BASE_PATH, 'initial', 'CoNWeT_bae-marketplace_0.1.1.wgt')

FIWARE_AUTHORIZATION_ENDPOINT = 'oauth2/authorize'
FIWARE_ACCESS_TOKEN_ENDPOINT = 'oauth2/token'
FIWARE_REVOKE_TOKEN_ENDPOINT = 'oauth2/revoke'
FIWARE_USER_DATA_ENDPOINT = 'user'

logger = logging.getLogger(__name__)

class FIWAREBAEManager(MarketManager):
    _user: str = None
    _name: str = None
    _options: MarketOptions = None

    def __init__(self, user: Optional[str], name: str, options: MarketOptions):
        super().__init__(user, name, options)

        if user is None:
            raise ValueError("User must be specified for FIWARE BAE Manager")

        self._user = user
        self._name = name
        self._options = options

    async def create(self, db: DBSession, request: Request, user: UserAll):
        await create_workspace(
            db,
            request,
            user,
            mashup="CoNWeT/bae-marketplace/0.1.1",
            new_name=self._options.name,
            preferences={'server_url': self._options.url},
            searchable=False,
            public=self._options.public
        )

    async def delete(self, db: DBSession, request: Request):
        await get_workspace_by_username_and_name(db, creator_username=self._user, name=self._name)


IDM_SUPPORT_ENABLED = False

class FiWareWirecloudPlugin(WirecloudPlugin):
    features = {
        'FIWARE': fiware.__version__,
        'NGSI': '1.4.1',
        'ObjectStorage': '0.5',
    }

    AUTH_TOKEN = None

    def __init__(self, app: Optional[FastAPI]):
        super().__init__(app)

    def get_market_classes(self):
        return {
            'fiware-bae': FIWAREBAEManager
        }

    def get_platform_context_definitions(self):
        if getattr(settings, "OID_CONNECT_PLUGIN", "") != "fiware" or not IDM_SUPPORT_ENABLED:
            return {'fiware_version': BaseContextKey(
                label=_('FIWARE version'),
                description=_('FIWARE version of the platform')
            )}

        return {
            'fiware_version': BaseContextKey(
                label=_('FIWARE version'),
                description=_('FIWARE version of the platform')
            ),
            'fiware_token_available': BaseContextKey(
                label=_('FIWARE token available'),
                description=_(
                    'Indicates if the current user has associated a FIWARE auth token that can be used for accessing other FIWARE resources')
            )
        }

    async def get_platform_context_current_values(self, db: DBSession, request: Optional[Request], user: Optional[UserAll],
                                                  session: Optional[Session]):
        if getattr(settings, "OID_CONNECT_PLUGIN", "") != "fiware" or not IDM_SUPPORT_ENABLED:
            return {
                'fiware_version': fiware.__version__
            }

        fiware_token_available = IDM_SUPPORT_ENABLED and user is not None and getattr(settings, "OID_CONNECT_PLUGIN", "") in user.idm_data
        return {
            'fiware_version': fiware.__version__,
            'fiware_token_available': fiware_token_available
        }

    def get_constants(self):
        constants = {
            "FIWARE_HOME": getattr(settings, "FIWARE_HOME", fiware.DEFAULT_FIWARE_HOME),
            'FIWARE_PORTALS': getattr(settings, "FIWARE_PORTALS", ())
        }

        if IDM_SUPPORT_ENABLED:
            constants["FIWARE_OFFICIAL_PORTAL"] = getattr(settings, "FIWARE_OFFICIAL_PORTAL", False)
            constants["FIWARE_IDM_SERVER"] = getattr(settings, "FIWARE_IDM_SERVER", False)

        return constants

    def get_widget_api_extensions(self, view, features):
        files = []

        if 'NGSI' in features:
            files.append('js/WirecloudAPI/NGSIAPI.js')

        if 'ObjectStorage' in features:
            files.append('js/ObjectStorage/ObjectStorageAPI.js')

        return files

    def get_operator_api_extensions(self, view, features):
        files = []

        if 'NGSI' in features:
            files.append('js/WirecloudAPI/NGSIAPI.js')

        if 'ObjectStorage' in features:
            files.append('js/ObjectStorage/ObjectStorageAPI.js')

        return files

    def get_proxy_processors(self) -> tuple[str, ...]:
        if not IDM_SUPPORT_ENABLED:
            return ()

        return ('src.wirecloud.fiware.proxy.IDMTokenProcessor',)

    def get_template_context_processors(self, request: Request) -> dict[str, Any]:
        context = {
            "FIWARE_HOME": getattr(settings, "FIWARE_HOME", fiware.DEFAULT_FIWARE_HOME),
            "FIWARE_OFFICIAL_PORTAL": getattr(settings, "FIWARE_OFFICIAL_PORTAL", False),
            "FIWARE_PORTALS": getattr(settings, "FIWARE_PORTALS", ()),
        }

        if IDM_SUPPORT_ENABLED:
            context["FIWARE_IDM_SERVER"] = getattr(settings, "FIWARE_IDM_SERVER", None)
            context["FIWARE_IDM_PUBLIC_URL"] = getattr(settings, "FIWARE_IDM_PUBLIC_URL", None)
        else:
            context["FIWARE_IDM_SERVER"] = None
            context["FIWARE_IDM_PUBLIC_URL"] = None

        return context

    def get_idm_get_authorization_url_functions(self) -> dict[str, Callable]:
        def get_keyrock_authorization_url() -> URLTemplate:
            base_url = urljoin(getattr(settings, 'FIWARE_IDM_SERVER', ''), FIWARE_AUTHORIZATION_ENDPOINT)
            query_params = {
                'client_id': getattr(settings, 'OID_CONNECT_CLIENT_ID'),
                'response_type': 'code',
                'scope': quote(' '.join(getattr(settings, 'FIWARE_EXTENDED_PERMISSIONS', []))),
            }

            if len(query_params['scope']) == 0:
                del query_params['scope']

            # Add the query parameters to the URL
            parsed_url = urlparse(base_url)
            query = parsed_url.query
            if query:
                query += '&'

            query += '&'.join(f"{key}={value}" for key, value in query_params.items())

            # Rebuild the URL with the new query parameters
            base_url = parsed_url._replace(query=query).geturl()

            return URLTemplate(urlpattern=base_url, defaults={})

        return {"fiware": get_keyrock_authorization_url}

    def get_idm_get_token_functions(self) -> dict[str, Callable]:
        async def get_keyrock_token(code: Optional[str], refresh_token: Optional[str],
                                    redirect_uri: Optional[str]) -> dict[str, Union[str, int]]:
            if not code and not refresh_token:
                raise ValueError("Either code or refresh_token must be provided")

            if code:
                token_data_to_send = {
                    "code": code,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                }

                token_url = urljoin(getattr(settings, 'FIWARE_IDM_SERVER', ''), FIWARE_ACCESS_TOKEN_ENDPOINT)

                try:
                    token_data = await make_oidc_provider_request(token_url, token_data_to_send, auth=self.AUTH_TOKEN,
                                                                  auth_type="Basic")
                except Exception as e:
                    raise ValueError(f"Exception while requesting OIDC access token: {str(e)}")
            else:
                token_data_to_send = {
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token",
                }

                token_url = urljoin(getattr(settings, 'FIWARE_IDM_SERVER', ''), FIWARE_ACCESS_TOKEN_ENDPOINT)

                try:
                    token_data = await make_oidc_provider_request(token_url, token_data_to_send, auth=self.AUTH_TOKEN,
                                                                  auth_type="Basic")
                except Exception as e:
                    raise ValueError(f"Exception while requesting OIDC access token: {str(e)}")

            if "access_token" not in token_data or "refresh_token" not in token_data:
                raise ValueError(_("OIDC provider has not returned a valid response: missing access_token or refresh_token"))

            return token_data

        return {"fiware": get_keyrock_token}

    def get_idm_get_user_functions(self) -> dict[str, Callable]:
        async def get_keyrock_user_info(token_data: dict[str, Union[str, int]]) -> dict[str, Union[str, dict]]:
            if not token_data:
                raise ValueError("Access token must be provided")

            try:
                user_data = await make_oidc_provider_request(getattr(settings, "OID_CONNECT_DATA")["userinfo_endpoint"],
                                                             data=None,
                                                             auth=token_data['access_token'])
            except Exception as e:
                raise ValueError(f"Exception while requesting OIDC access token: {str(e)}")

            if "username" not in user_data:
                raise ValueError(_("OIDC provider has not returned a valid response: missing username"))

            first_name = user_data.get("displayName", "").split(" ")[0] if "displayName" in user_data else ""
            last_name = " ".join(user_data.get("displayName", "").split(" ")[1:]) if "displayName" in user_data else ""

            data = {
                "sub": user_data["id"],
                "preferred_username": user_data["username"],
                "email": user_data.get("email", ""),
                "given_name": first_name,
                "family_name": last_name,
                "wirecloud": {
                    "groups": [role["name"] for role in user_data.get("roles", [])],
                }
            }

            return data

        return {"fiware": get_keyrock_user_info}

    def get_idm_backchannel_logout_functions(self) -> dict[str, Callable]:
        async def backchannel_logout(refresh_token: str) -> None:
            if not refresh_token:
                raise ValueError("Access token must be provided")

            if getattr(settings, "OID_CONNECT_BACKCHANNEL_LOGOUT", False):
                try:
                    data = {
                        "token": refresh_token,
                        "token_type_hint": "refresh_token"
                    }

                    logout_url = urljoin(getattr(settings, 'FIWARE_IDM_SERVER', ''), FIWARE_REVOKE_TOKEN_ENDPOINT)
                    await make_oidc_provider_request(logout_url, data, auth=self.AUTH_TOKEN, auth_type="Basic")
                except Exception as e:
                    # Log the error but do not fail the logout process
                    logger.error(f"Keyrock token revocation failed: {e}")

        return {"fiware": backchannel_logout}

    def get_config_validators(self) -> tuple[Callable, ...]:
        async def validate_fiware_settings(settings, _offline: bool) -> None:
            global IDM_SUPPORT_ENABLED

            if getattr(settings, "OID_CONNECT_PLUGIN", "") != "fiware":
                return

            if getattr(settings, "OID_CONNECT_ENABLED", False):
                IDM_SUPPORT_ENABLED = True

                if not getattr(settings, "FIWARE_IDM_SERVER", None):
                    raise ValueError(_("The FIWARE IDM server must be configured when using the OIDC plugin with FIWARE."))

                if not getattr(settings, "FIWARE_APP_ID", None):
                    raise ValueError(_("The FIWARE App ID must be configured when using the OIDC plugin with FIWARE."))

                if not getattr(settings, "FIWARE_APP_SECRET", None):
                    raise ValueError(_("The FIWARE App Secret must be configured when using the OIDC plugin with FIWARE."))

                app_id = settings.FIWARE_APP_ID
                app_secret = settings.FIWARE_APP_SECRET

                self.AUTH_TOKEN = base64.urlsafe_b64encode(f"{app_id}:{app_secret}".encode()).decode()

        return (validate_fiware_settings,)

    async def populate(self, db: DBSession, wirecloud_user: UserAll) -> bool:
        updated = False

        updated |= await populate_component(db, wirecloud_user, "CoNWeT", "bae-browser", "0.1.1",
                                            BAE_BROWSER_WIDGET)
        updated |= await populate_component(db, wirecloud_user, "CoNWeT", "bae-details", "0.1.1",
                                            BAE_DETAILS_WIDGET)
        updated |= await populate_component(db, wirecloud_user, "CoNWeT", "bae-search-filters", "0.1.1",
                                            BAE_SEARCH_FILTERS_WIDGET)
        updated |= await populate_component(db, wirecloud_user, "CoNWeT", "bae-marketplace", "0.1.1",
                                            BAE_MASHUP)

        return updated