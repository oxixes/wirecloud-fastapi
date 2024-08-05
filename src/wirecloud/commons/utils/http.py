# -*- coding: utf-8 -*-

# Copyright (c) 2012-2016 CoNWeT Lab., Universidad Politécnica de Madrid

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

# TODO Add HTML response

import socket
import json
from lxml import etree
from fastapi import Request, Response
from pydantic import BaseModel
from typing import Optional, Any
from urllib.parse import urljoin

from src.wirecloud.commons.utils import mimeparser


class HTTPError(BaseModel):
    error_msg: str
    details: Optional[dict[str, Any]] = None


def get_xml_error_response(request: Optional[Request], mimetype: str, status_code: int, context: dict) -> str:
    doc = etree.Element('error')

    description = etree.Element('description')
    description.text = str(context['error_msg'])

    doc.append(description)

    if context.get('details') is not None:
        details_element = etree.Element('details')
        for key in context['details']:
            element = etree.Element(key)

            if isinstance(context['details'][key], str):
                element.text = context['details'][key]
            elif hasattr(context['details'][key], '__iter__'):
                for value in context['details'][key]:
                    list_element = etree.Element('element')
                    list_element.text = value
                    element.append(list_element)
            else:
                for key2 in context['details'][key]:
                    list_element = etree.Element(key2)
                    list_element.text = context['details'][key][key2]
                    element.append(list_element)

            details_element.append(element)

        doc.append(details_element)

    return etree.tostring(doc, pretty_print=False, method='xml')


def get_json_error_response(request: Optional[Request], mimetype: str, status_code: int, context: dict) -> str:
    body = {
        'description': str(context['error_msg'])
    }
    if context.get('details') is not None:
        body['details'] = context['details']

    return json.dumps(body, ensure_ascii=False, sort_keys=True)


def get_plain_text_error_response(request: Optional[Request], mimetype: str, status_code: int, context: dict) -> str:
    return "%s" % context['error_msg']


ERROR_FORMATTERS = {
    'application/json; charset=utf-8': get_json_error_response,
    'application/xml; charset=utf-8': get_xml_error_response,
    # 'text/html; charset=utf-8': get_html_basic_error_response,
    # 'application/xhtml+xml; charset=utf-8': get_html_basic_error_response,
    'text/plain; charset=utf-8': get_plain_text_error_response,
    '': get_plain_text_error_response,  # Fallback
}


def build_response(request: Request, status_code: int, context: dict, formatters: dict,
                   headers: dict[str, str] = None) -> Response:
    if request.headers.get('X-Requested-With', '') == 'XMLHttpRequest':
        content_type = 'application/json; charset=utf-8'
    else:
        formatter_keys = list(formatters.keys())
        formatter_keys.remove('')
        content_type = mimeparser.best_match(formatter_keys, request.headers.get('Accept', '*/*'))

    if content_type in formatters:
        formatter = formatters[content_type]
    else:
        raise Exception('No suitable formatter found')

    body = formatter(request, content_type, status_code, context)
    response = Response(content=body, status_code=status_code, media_type=content_type)
    if headers is None:
        headers = {}

    for header_name in headers:
        response.headers[header_name] = headers[header_name]

    return response


def build_error_response(request: Request, status_code: int, error_msg: str, extra_formats: dict = None,
                         headers: dict[str, str] = None, details: dict = None, context: dict = None) -> Response:
    if extra_formats is not None:
        formatters = extra_formats.copy()
        formatters.update(ERROR_FORMATTERS)
    else:
        formatters = ERROR_FORMATTERS

    if context is None:
        context = {}

    context.update({'error_msg': error_msg, 'details': details})

    return build_response(request, status_code, context, formatters, headers)


_servername = None


def get_current_scheme(request: Optional[Request] = None) -> str:
    from src import settings

    if getattr(settings, 'FORCE_PROTO', None) is not None:
        return settings.FORCE_PROTO
    elif request is not None and request.url.is_secure:
        return 'https'
    else:
        return 'http'


def force_trailing_slash(url):
    return url if url[-1] == '/' else url + '/'


def get_current_domain(request: Optional[Request] = None) -> str:
    from src import settings

    # Server name
    if getattr(settings, 'FORCE_DOMAIN', None) is not None:
        servername = settings.FORCE_DOMAIN
    else:
        try:
            servername = request.url.hostname
        except Exception:
            global _servername
            if _servername is None:
                _servername = socket.getfqdn()
            servername = _servername

    # Port
    scheme = get_current_scheme(request)

    if getattr(settings, 'FORCE_PORT', None) is not None:
        port = int(settings.FORCE_PORT)
    else:
        try:
            port = request.url.port
        except Exception:
            port = 80 if scheme == 'http' else 443

    if (scheme == 'http' and port != 80) or (scheme == 'https' and port != 443):
        return servername + (':%s' % port)
    else:
        return servername


def get_absolute_reverse_url(viewname: str, request: Optional[Request] = None, **kwargs) -> str:
    from src.wirecloud.platform.plugins import get_plugin_urls

    patterns = get_plugin_urls()
    if viewname not in patterns:
        raise ValueError('No URL pattern found for view "%s"' % viewname)

    url = patterns[viewname].urlpattern
    for key in kwargs:
        url = url.replace('{' + key + '}', str(kwargs[key]))

    return urljoin(get_current_scheme(request) + '://' + get_current_domain(request), url)