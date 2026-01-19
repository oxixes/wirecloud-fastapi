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

import asyncio
from typing import Union
from urllib.parse import quote_plus, urlparse

from src import settings
from src.wirecloud.commons.auth.crud import get_user_with_all_info, update_user
from src.wirecloud.database import DBSession
from src.wirecloud.fiware import FIWARE_LAB_CLOUD_SERVER
from src.wirecloud.fiware.openstack_token_manager import OpenStackTokenManager
from src.wirecloud.platform.plugins import get_idm_get_token_functions
from src.wirecloud.proxy.schemas import ProxyRequestData
from src.wirecloud.proxy.utils import ValidationError
from src.wirecloud.translation import gettext as _


def get_header_or_query(request: ProxyRequestData, header: str, delete: bool = False) -> Union[str, None]:
    query_param = '__' + header.replace('-', '_').lower()
    url_query_params = urlparse(request.url).query
    url_query_dict = dict(param.split('=') for param in url_query_params.split('&') if '=' in param)

    if header in request.headers:
        value = request.headers[header]
        if delete:
            del request.headers[header]
        return value
    elif query_param in url_query_dict:
        value = url_query_dict[query_param]
        if delete:
            url_parts = list(request.url)
            query = url_parts[4]
            query_items = query.split('&')
            filtered_query_items = [item for item in query_items if not item.startswith(query_param)]
            url_parts[4] = '&'.join(filtered_query_items)
            new_url = urlparse(request.url)._replace(query=url_parts[4]).geturl()
            request.url = new_url
        return value

    return None


def replace_get_parameter(request: ProxyRequestData, gets: list[str], token: str) -> None:
    for get in gets:
        parameter_name = get_header_or_query(request, get, delete=True)
        if parameter_name is None:
            continue

        url = request.url
        if '?' in url:
            url += '&'
        else:
            url += '?'

        url += "{}={}".format(quote_plus(parameter_name), quote_plus(token))
        request.url = url

        return


def replace_header_name(request: ProxyRequestData, headers: list[str], token: str) -> None:
    for header in headers:
        header_name = get_header_or_query(request, header, delete=True)
        if header_name is None:
            continue

        if header_name == "Authorization":
            header_value = f"Bearer {token}"
        else:
            header_value = token

        request.headers[header_name] = header_value
        return


async def replace_body_pattern(request: ProxyRequestData, bodies: list[str], token: str) -> None:
    for body in bodies:
        pattern = get_header_or_query(request, body, delete=True)
        if pattern is None:
            continue

        if request.data is None:
            raise ValidationError(_('No body data to replace pattern'))

        new_body_array = bytearray()
        if isinstance(request.data, bytes):
            new_body_array.extend(request.data)
        else:
            async for chunk in request.data:
                new_body_array.extend(chunk)

        new_body = new_body_array.replace(pattern.encode('utf8'), token.encode('utf8'))
        request.headers['content-length'] = str(len(new_body))
        request.data = new_body


class IDMTokenProcessor:
    def __init__(self):
        if getattr(settings, "OID_CONNECT_ENABLED", False):
            self.openstack_manager = OpenStackTokenManager(getattr(settings, 'FIWARE_CLOUD_SERVER', FIWARE_LAB_CLOUD_SERVER))

    async def process_request(self, db: DBSession, request: ProxyRequestData, enable_openstack: bool = True) -> None:
        if request.workspace is None or request.component_id is None or request.component_type is None:
            return

        headers = ['fiware-oauth-token']
        if enable_openstack:
            headers.append('fiware-openstack-token')

        filtered = []

        for header in headers:
            if get_header_or_query(request, header, delete=True) is not None:
                filtered.append(header)

        if len(filtered) == 0:
            return

        if not getattr(settings, "OID_CONNECT_ENABLED", False):
            raise ValidationError(_('IdM support not enabled'))

        source = get_header_or_query(request, 'fiware-oauth-source', delete=True)
        if source is None:
            source = 'user'

        user = None
        if source == 'user':
            user = request.user
        elif source == 'workspace':
            user = await get_user_with_all_info(db, request.workspace.creator)
        else:
            raise ValidationError(_('Invalid FIWARE OAuth token source'))

        if user is None or 'idm_token' not in user.idm_data[getattr(settings, "OID_CONNECT_PLUGIN")] \
                or not user.idm_data[getattr(settings, "OID_CONNECT_PLUGIN")]['idm_token']:
            raise ValidationError(_('User has not an active FIWARE profile'))

        if user is not None and source == 'workspace' and not user.has_perm("ALLOW_TOKEN_TO_OTHER_USERS"):
            raise ValidationError(_('Workspace owner does not have permission to give their token to other users'))

        token_data_get_func = get_idm_get_token_functions()[getattr(settings, "OID_CONNECT_PLUGIN")]

        try:
            if asyncio.iscoroutinefunction(token_data_get_func):
                token_data = await token_data_get_func(
                    refresh_token=user.idm_data[getattr(settings, "OID_CONNECT_PLUGIN")]["idm_token"], code=None,
                    redirect_uri=None)
            else:
                token_data = token_data_get_func(
                    refresh_token=user.idm_data[getattr(settings, "OID_CONNECT_PLUGIN")]["idm_token"], code=None,
                    redirect_uri=None)
        except ValueError:
            raise Exception(_("Failed to get token from IdM"))

        user.idm_data[getattr(settings, "OID_CONNECT_PLUGIN")]["idm_token"] = token_data["refresh_token"]

        if 'fiware-openstack-token' in filtered:
            tenant_id = request.headers.get('fiware-openstack-tenant-id', None)

            openstack_token = await self.openstack_manager.get_token(db, user, tenant_id)

        await update_user(db, user)
        await db.commit()

        if 'fiware-oauth-token' in filtered:
            replace_get_parameter(request, ["fiware-oauth-get-parameter"], token_data["access_token"])
            replace_header_name(request, ["fiware-oauth-header-name"], token_data["access_token"])
            await replace_body_pattern(request, ["fiware-oauth-body-pattern"], token_data["access_token"])

        if 'fiware-openstack-token' in filtered:
            replace_get_parameter(request, ["fiware-openstack-get-parameter"], openstack_token)
            replace_header_name(request, ["fiware-openstack-header-name"], openstack_token)
            await replace_body_pattern(request, ["fiware-openstack-body-pattern"], openstack_token)