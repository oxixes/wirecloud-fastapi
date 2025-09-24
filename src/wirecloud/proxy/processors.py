# -*- coding: utf-8 -*-

# Copyright (c) 2011-2017 CoNWeT Lab., Universidad Politécnica de Madrid

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

import re
import base64
from typing import Optional
from urllib.parse import unquote, quote as urlquote, urlparse

from fastapi import Request

from src.wirecloud.database import DBSession
from src.wirecloud.platform.workspace.utils import VariableValueCacheManager
from src.wirecloud.proxy.schemas import ProxyRequestData
from src.wirecloud.proxy.utils import ValidationError
from src.wirecloud.translation import gettext as _

WIRECLOUD_SECURE_DATA_HEADER = 'x-wirecloud-secure-data'
WIRECLOUD_SECURE_DATA_QUERY_PARAM = '__wirecloud_secure_data'

VAR_REF_RE = re.compile(r'^((?P<constant>c)/)?(?P<var_name>.+)$', re.S)


async def get_variable_value_by_ref(db: DBSession, request: Optional[Request], ref: str,
                              cache_manager: VariableValueCacheManager, component_type: str, component_id: str) -> Optional[str]:
    result = VAR_REF_RE.match(ref)
    if result.group('constant') == 'c':
        return result.group('var_name')

    try:
        return await cache_manager.get_variable_value_from_varname(db, request, "i" + component_type,
                                                             component_id, result.group('var_name'))
    except Exception:
        return None


def check_empty_params(**kargs):
    missing_params = []

    for param_name in kargs:
        if kargs[param_name] == '':
            missing_params.append(param_name)

    if len(missing_params) > 0:
        msg = _('X-WireCloud-Secure-Data: The following required parameters are missing: %(params)s')
        raise ValidationError(msg % {'params': ', '.join(missing_params)})


def check_invalid_refs(**kargs):
    invalid_params = []

    for param_name in kargs:
        if kargs[param_name] is None:
            invalid_params.append(param_name)

    if len(invalid_params) > 0:
        msg = _('X-WireCloud-Secure-Data: The following required parameters are invalid: %(params)s')
        raise ValidationError(msg % {'params': ', '.join(invalid_params)})


async def process_secure_data(db: DBSession, text: str, request: ProxyRequestData, component_id: str, component_type: str):
    definitions = text.split('&')
    cache_manager = VariableValueCacheManager(request.workspace, request.user)
    for definition in definitions:
        params = definition.split(',')
        if len(params) == 1 and params[0].strip() == '':
            continue

        options = {}
        for pair in params:
            tokens = pair.split('=')
            option_name = unquote(tokens[0].strip())
            options[option_name] = unquote(tokens[1].strip())

        action = options.get('action', 'data')
        if action == 'data' and not request.is_ws:
            var_ref = options.get('var_ref', '')
            substr = options.get('substr', '{' + var_ref + '}')
            check_empty_params(substr=substr, var_ref=var_ref)

            value = await get_variable_value_by_ref(db, request.original_request, var_ref, cache_manager,
                                                    component_type, component_id)
            check_invalid_refs(var_ref=value)

            encoding = options.get('encoding', 'none')
            substr = substr.encode('utf8')
            if encoding == 'url':
                value = urlquote(value).encode('utf8')
            elif encoding == 'base64':
                value = base64.b64encode(value.encode('utf8'))
            else:
                value = value.encode('utf8')

            if request.data is None:
                raise ValidationError(_('X-WireCloud-Secure-Data: The request does not contain any data to process.'))

            new_body_array = bytearray()
            if isinstance(request.data, bytes):
                new_body_array.extend(request.data)
            else:
                async for chunk in request.data:
                    new_body_array.extend(chunk)

            new_body = new_body_array.replace(substr, value)
            request.headers['content-length'] = str(len(new_body))
            request.data = new_body
        elif action == "header":
            var_ref = options.get('var_ref', '')
            substr = options.get('substr', '{' + var_ref + '}')
            header = options.get('header', '').lower()
            check_empty_params(substr=substr, var_ref=var_ref, header=header)

            value = await get_variable_value_by_ref(db, request.original_request, var_ref, cache_manager,
                                                    component_type, component_id)
            check_invalid_refs(var_ref=value)

            encoding = options.get('encoding', 'none')
            if encoding == 'url':
                value = urlquote(value)
            elif encoding == 'base64':
                value = base64.b64encode(value.encode('utf8')).decode('utf8')

            request.headers[header] = request.headers[header].replace(substr, value)
        elif action == "basic_auth":
            user_ref = options.get('user_ref', '')
            password_ref = options.get('pass_ref', '')
            check_empty_params(user_ref=user_ref, password_ref=password_ref)

            user_value = await get_variable_value_by_ref(db, request.original_request, user_ref, cache_manager,
                                                         component_type, component_id)
            password_value = await get_variable_value_by_ref(db, request.original_request, password_ref, cache_manager,
                                                             component_type, component_id)
            check_invalid_refs(user_ref=user_value, password_ref=password_value)
            token = base64.b64encode((user_value + ':' + password_value).encode('utf8'))

            request.headers['authorization'] = 'Basic ' + token.decode('utf8')
        elif action == "data" and request.is_ws:
            raise ValidationError(_('X-WireCloud-Secure-Data: The "data" action is not supported for WebSocket requests.'))
        else:
            raise ValidationError(_('X-WireCloud-Secure-Data: Unknown action "%(action)s".') % {'action': action})


class SecureDataProcessor:
    async def process_request(self, db: DBSession, request: ProxyRequestData) -> None:
        if request.workspace is None or request.component_id is None or request.component_type is None:
            return

        url_query_params = urlparse(request.url).query
        url_query_dict = dict(param.split('=') for param in url_query_params.split('&') if '=' in param)

        if WIRECLOUD_SECURE_DATA_HEADER in request.headers:
            secure_data_value = request.headers[WIRECLOUD_SECURE_DATA_HEADER]
            await process_secure_data(db, secure_data_value, request, request.component_id, request.component_type)
            del request.headers[WIRECLOUD_SECURE_DATA_HEADER]
        elif WIRECLOUD_SECURE_DATA_QUERY_PARAM in url_query_dict:
            secure_data_value = url_query_dict[WIRECLOUD_SECURE_DATA_QUERY_PARAM]
            await process_secure_data(db, secure_data_value, request, request.component_id, request.component_type)

            # Remove the parameter from the query
            url_parts = list(request.url)
            query = url_parts[4]
            query_items = query.split('&')
            filtered_query_items = [item for item in query_items if not item.startswith(WIRECLOUD_SECURE_DATA_QUERY_PARAM)]
            url_parts[4] = '&'.join(filtered_query_items)
            new_url = urlparse(request.url)._replace(query=url_parts[4]).geturl()
            request.url = new_url
