# -*- coding: utf-8 -*-
# Copyright (c) 2008-2017 CoNWeT Lab., Universidad Politécnica de Madrid

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

from urllib.parse import urlparse
from http.cookies import SimpleCookie
from fastapi import APIRouter, Path, Response, Request
from fastapi.responses import StreamingResponse
from typing import Optional
import re
import aiohttp

from src.wirecloud.proxy import docs
from src.wirecloud.proxy.schemas import ProxyRequestData
from src.wirecloud.proxy.utils import is_valid_response_header
from src.wirecloud.commons.utils.http import (build_error_response, resolve_url_name, iri_to_uri, get_current_domain,
                                              get_relative_reverse_url)
from src.wirecloud.commons.auth.schemas import User
from src.wirecloud.platform.plugins import get_request_proxy_processors, get_response_proxy_processors
from src import settings
from src.wirecloud import docs as root_docs
from src.wirecloud.translation import gettext as _

router = APIRouter()

HTTP_HEADER_RE = re.compile('^http_')
BLACKLISTED_HTTP_HEADERS = [
    'http_host', 'http_forwarded', 'http_x_forwarded_by',
    'http_x_forwarded_host', 'http_x_forwarded_port',
    'http_x_forwarded_proto', 'http_x_forwarded_server'
]


async def parse_request_headers(request: Request, request_data: ProxyRequestData) -> None:
    if 'Transfer-Encoding' in request.headers:
        raise ValueError("WireCloud doesn't support requests using the Transfer-Encoding header")

    for header in request.headers.items():
        header_name = header[0].lower()

        if header_name == 'content_type' and header[1]:
            request_data.headers['Content-Type'] = header[1]
        elif header_name == 'content_length' and header[1]:
            # Only take into account request body if the request has a
            # Content-Length header (we don't support chunked requests)
            request_data.data = request.stream()
            request_data.headers["Content-Length"] = "%s" % header[1]
        elif header_name == 'cookie' or header_name == 'http_cookie':
            cookie_parser = SimpleCookie(str(header[1]))
            request_data.cookies.update(cookie_parser)
        elif HTTP_HEADER_RE.match(header_name) and header_name not in BLACKLISTED_HTTP_HEADERS:
            fixed_name = header_name.replace("http_", "", 1).replace('_', '-')
            request_data.headers[fixed_name] = header[1]

    if request_data.data is None and 'Content-Type' in request_data.headers:
        del request_data.headers['Content-Type']


def parse_context_from_referer(request: Request, request_method: str = "GET") -> ProxyRequestData:
    referrer = request.headers.get('Referer')
    if referrer is None:
        raise Exception()

    parsed_referrer = urlparse(referrer)
    if request.url.netloc != parsed_referrer[1]:
        raise Exception()

    referer_view_name = resolve_url_name(parsed_referrer.path)
    if referer_view_name is not None and referer_view_name == 'wirecloud.workspace_view':
        # TODO Check if workspace is accessible by the user
        print("TODO: Check if workspace is accessible by the user")
        raise Exception()
    elif referer_view_name is not None and referer_view_name == 'wirecloud.showcase_media' or referer_view_name == 'wirecloud|proxy':
        if request_method not in ('GET', 'POST'):
            raise Exception()

        workspace = None
    else:
        raise Exception()

    component_type = request.headers.get("Wirecloud-Component-Type")
    component_id = request.headers.get("Wirecloud-Component-Id")

    return ProxyRequestData(
        workspace=workspace,
        component_type=component_type,
        component_id=component_id
    )


class Proxy:
    async def do_request(self, request: Request, url: str, method: str, request_data: ProxyRequestData,
                         protocol: str, domain: str, path: str, user: Optional[User] = None) -> Response:
        url = iri_to_uri(url)

        request_data.method = method
        request_data.url = url
        request_data.original_request = request
        request_data.user = user

        # Build the Via header
        protocol_version = request.scope.get('http_version', '1.1')
        via_header = "%s %s (Wirecloud-python-Proxy/2.0)" % (protocol_version, get_current_domain(request))
        if 'via' in request_data.headers:
            request_data.headers['via'] += ', ' + via_header
        else:
            request_data.headers['via'] = via_header

        # XFF headers
        if 'x-forwarded-for' in request.headers:
            request_data.headers['x-forwarded-for'] += ', ' + request.client.host
        else:
            request_data.headers['x-forwarded-for'] = request.client.host

        # Pass proxy processors to the new request
        try:
            for processor in get_request_proxy_processors():
                processor.process_request(request_data)
        except ValueError as e:
            return build_error_response(request, 422, str(e))

        # Cookies
        cookie_header_content = ', '.join([request_data.cookies[key].OutputString() for key in request_data.cookies])
        if cookie_header_content != '':
            request_data.headers['Cookie'] = cookie_header_content

        try:
            session = aiohttp.ClientSession(cookie_jar=aiohttp.CookieJar(unsafe=True))
            res = await session.request(
                method=request_data.method,
                url=request_data.url,
                headers=request_data.headers,
                data=request_data.data,
                timeout=60,
                auto_decompress=False,
                ssl=getattr(settings, 'WIRECLOUD_HTTPS_VERIFY', True)
            )
        except aiohttp.ServerTimeoutError as e:
            return build_error_response(request, 504, _('Gateway Timeout'), details=str(e))
        except aiohttp.ClientSSLError as e:
            return build_error_response(request, 502, _('Bad Gateway'), details=str(e))
        except aiohttp.ClientError as e:
            return build_error_response(request, 502, _('Connection Error'), details=str(e))

        async def stream_response(s: aiohttp.ClientSession, r: aiohttp.ClientResponse):
            async for chunk in r.content.iter_any():
                yield chunk

            await s.close()

        response = StreamingResponse(stream_response(session, res), status_code=res.status)
        for header in res.headers:
            header_lower = header.lower()
            if header_lower == 'set-cookie':
                for cookie in session.cookie_jar:
                    response.set_cookie(
                        key=cookie.key,
                        value=cookie.value,
                        path=cookie['path'] if cookie['path'] != '' else
                            get_relative_reverse_url('wirecloud|proxy', request=request, protocol=protocol,
                                                     domain=domain, path=path),
                        expires=cookie['expires']
                    )
            elif header_lower == 'via':
                via_header = via_header + ', ' + res.headers[header]
            elif is_valid_response_header(header_lower):
                response.headers[header] = res.headers[header]

        # Pass proxy processors to the response
        for processor in get_response_proxy_processors():
            response = processor.process_response(request_data, response)

        response.headers['Via'] = via_header

        return response


WIRECLOUD_PROXY = Proxy()


async def proxy_request(request: Request,
                        protocol: str = Path(description=docs.proxy_request_protocol_description, regex='http|https'),
                        domain: str = Path(description=docs.proxy_request_domain_description, regex='[A-Za-z0-9-.]+'),
                        path: str = Path(description=docs.proxy_request_path_description)) -> Response:
    # TODO improve proxy security
    request_method = request.method.upper()
    if protocol not in ('http', 'https'):
        return build_error_response(request, 422, _("Invalid protocol: %s") % protocol)

    try:
        context = parse_context_from_referer(request, request_method)
    except Exception:
        return build_error_response(request, 403, _("Invalid request"))

    url = protocol + '://' + domain + "/" + (path[1:] if path.startswith('/') else path)
    # Add query and fragment to the url
    for query_param in request.query_params.items():
        url += ('&' if '?' in url else '?') + query_param[0] + '=' + query_param[1]

    if request.url.fragment:
        url += '#' + request.url.fragment

    try:
        # Extract headers from META
        await parse_request_headers(request, context)

        response = await WIRECLOUD_PROXY.do_request(request, url, request_method, context, protocol, domain, path)
    except ValueError as e:
        return build_error_response(request, 422, str(e))
    except Exception as e:
        # TODO Log
        msg = _("Error processing proxy request: %s") % e
        return build_error_response(request, 500, msg)

    return response


for method in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS', 'HEAD']:
    router.add_api_route('/{protocol}/{domain}/{path:path}', proxy_request,
                     response_class=Response,
                     summary=docs.proxy_request_summary,
                     description=docs.proxy_request_description,
                     response_description=docs.proxy_request_response_description,
                     methods=[method],
                     responses={
                        403: root_docs.generate_permission_denied_response_openapi_description(
                             docs.proxy_request_permission_denied_description,
                            "Invalid request"),
                        422: root_docs.generate_validation_error_response_openapi_description(
                             docs.proxy_request_validation_error_description),
                        502: root_docs.generate_error_response_openapi_description(
                             docs.proxy_request_bad_gateway_description,
                             "Bad Gateway"),
                        504: root_docs.generate_error_response_openapi_description(
                             docs.proxy_request_gateway_timeout_description,
                             "Gateway Timeout")
                     })