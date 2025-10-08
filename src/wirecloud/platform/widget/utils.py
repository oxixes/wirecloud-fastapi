#  -*- coding: utf-8 -*-
#
#  Copyright (c) 2024 Future Internet Consulting and Development Solutions S.L.
#
#  This file is part of Wirecloud.
#
#  Wirecloud is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Affero General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  Wirecloud is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Affero General Public License for more details.
#
#  You should have received a copy of the GNU Affero General Public License
#  along with Wirecloud.  If not, see <http://www.gnu.org/licenses/>.


from typing import Optional, Union, Any
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from urllib.request import url2pathname
import errno
import time
from html import escape

from lxml import etree
from io import BytesIO

from fastapi import Request, Response
from fastapi.responses import HTMLResponse
import os

from lxml.etree import _ElementTree, _Element

from src import settings
from src.settings import cache
from src.wirecloud.catalogue.crud import get_catalogue_resources_with_regex, get_catalogue_resource_with_xhtml, \
    save_catalogue_resource_xhtml
from src.wirecloud.catalogue.models import XHTML
from src.wirecloud.catalogue.schemas import CatalogueResource, CatalogueResourceXHTML
from src.wirecloud.commons.auth.schemas import UserAll
from src.wirecloud.commons.templates.tags import get_static_path
from src.wirecloud.commons.utils.cache import patch_cache_headers
from src.wirecloud.commons.utils.downloader import download_local_file
from src.wirecloud.commons.utils.http import get_current_domain, build_response, ERROR_FORMATTERS, \
    get_absolute_static_url
from src.wirecloud.commons.utils.template import UnsupportedFeature
from src.wirecloud.commons.utils.template.schemas.macdschemas import Vendor, Name, Version, MACDRequirement, MACDWidget, \
    MACType
from src.wirecloud.commons.utils.theme import get_jinja2_templates
from src.wirecloud.commons.utils.wgt import WgtDeployer, WgtFile
from src.wirecloud.database import DBSession
from src.wirecloud.platform.plugins import get_widget_api_extensions, get_active_features
from src.wirecloud.platform.routes import get_current_theme
from src.wirecloud.platform.widget.crud import get_widget_from_resource
from src.wirecloud.platform.widget.models import Widget
from src.wirecloud.translation import gettext as _

wgt_deployer = WgtDeployer(settings.WIDGET_DEPLOYMENT_DIR)
WIDGET_ERROR_FORMATTERS = ERROR_FORMATTERS.copy()


def get_html_error_response(request: Request, mimetype: str, status_code: int, context: dict) -> Response:
    templates = get_jinja2_templates(get_current_theme(request))
    return templates.TemplateResponse(request=request, name="wirecloud/widget_error.html", context=context,
                                      status_code=status_code, media_type=mimetype)


WIDGET_ERROR_FORMATTERS.update({
    'text/html; charset=utf-8': get_html_error_response,
    'application/xhtml+xml; charset=utf-8': get_html_error_response,
})


def process_requirements(requirements: list[MACDRequirement]) -> dict[str, dict[str, str]]:
    return dict((requirement.name, {}) for requirement in requirements)


async def get_or_add_widget_from_catalogue(db: DBSession, vendor: Vendor, name: Name, version: Version,
                                           user: UserAll) -> Optional[tuple[Widget, CatalogueResource]]:
    resource_list = await get_catalogue_resources_with_regex(db, vendor, name, version)
    for resource in resource_list:
        if await resource.is_available_for(db, user):
            return await get_widget_from_resource(db, resource.id), resource

    return None


def xpath(tree: _ElementTree, query: str, xmlns: Any) -> Union[
    list[_Element], list[str], str, float, bool, _Element, None]:
    if xmlns is None:
        query = query.replace('xhtml:', '')
        return tree.xpath(query)
    else:
        return tree.xpath(query, namespaces={'xhtml': xmlns})


_widget_platform_style: dict[str, tuple[str]] = {}

def add_query_param(url: str, key: str, value: str) -> str:
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)
    query_params[key] = [value]
    new_query = urlencode(query_params, doseq=True)
    new_url = urlunparse(parsed_url._replace(query=new_query))
    return new_url

def get_widget_platform_style(request: Request, theme: str) -> tuple[str]:
    global _widget_platform_style

    if theme not in _widget_platform_style or settings.DEBUG:
        base_href = get_static_path(theme, 'widget', request, 'cache.css')
        href = add_query_param(base_href, 'context', 'widget')
        safe_href = escape(href, quote=True)

        files = [safe_href]
        files.reverse()

        _widget_platform_style[theme] = tuple(files)

    return _widget_platform_style[theme]


async def get_widget_api_files(request: Request, theme: str) -> list[str]:
    from src.wirecloud.platform.core.plugins import get_version_hash
    key = f"widget_api_files/{get_current_domain(request)}?v={get_version_hash()}"
    widget_api_files = await cache.get(key)

    if widget_api_files is None or settings.DEBUG:

        files = [get_absolute_static_url(f"static/js/main-{theme}-widget.js", request=request)]
        files.reverse()
        widget_api_files = tuple([get_absolute_static_url(file, request=request, versioned=True) for file in files])
        await cache.set(key, widget_api_files)

    return list(widget_api_files)


async def fix_widget_code(widget_code: Union[str, bytes], content_type: str, request: Request, encoding: str,
                          use_platform_style: bool, requirements, mode: str, theme: str, macversion: int) -> Optional[bytes]:
    # This line is here for raising UnicodeDecodeError in case the widget_code is not encoded using the specified encoding
    widget_code.decode(encoding)

    if content_type in ('text/html', 'application/xhtml+xml') and widget_code.strip() == b'':
        widget_code = b'<html></html>'

    if content_type == 'text/html':
        parser = etree.HTMLParser(encoding=encoding)
        serialization_options = {'method': 'html'}

    elif content_type == 'application/xhtml+xml':
        parser = etree.XMLParser(encoding=encoding)
        serialization_options = {'method': 'xml', 'xml_declaration': False}

    else:
        return widget_code

    xmltree = etree.parse(BytesIO(widget_code), parser)

    prefix = xmltree.getroot().prefix
    xmlns = None
    if prefix in xmltree.getroot().nsmap:
        xmlns = xmltree.getroot().nsmap[prefix]

    # Fix head element
    head_elements = xpath(xmltree, '/xhtml:html/xhtml:head', xmlns)
    if len(head_elements) == 0:
        head_element = etree.Element('head')
        xmltree.getroot().insert(0, head_element)
    else:
        head_element = head_elements[0]

    if macversion == 1:
        # Fix base element
        base_elements = xpath(xmltree, '/xhtml:html/xhtml:head/xhtml:base', xmlns)
        for base_element in base_elements[1:]:
            base_element.getparent().remove(base_element)

        # Fix scripts
        scripts = xpath(xmltree, '/xhtml:html//xhtml:script', xmlns)
        for script in scripts:
            if 'src' in script.attrib:
                script.text = ''

        head_element.insert(0, etree.Element('script', type="text/javascript", src=get_absolute_static_url('static/js/WirecloudAPI/WirecloudAPIClosure.js', request=request, versioned=True)))
        files = get_widget_api_extensions(mode, requirements)
        files.reverse()
        for file in files:
            head_element.insert(0, etree.Element('script', type="text/javascript",
                                                 src=get_absolute_static_url("/static/" + file, request=request, versioned=True)))

        for file in await get_widget_api_files(request, theme):
            head_element.insert(0, etree.Element('script', type="text/javascript", src=file))

    if use_platform_style:
        for file in get_widget_platform_style(request, theme):
            head_element.insert(0, etree.Element('link', rel='stylesheet', type='text/css', href=file))

    # Return modified code
    return etree.tostring(xmltree, pretty_print=False, encoding=encoding, **serialization_options)


async def process_widget_code(db: DBSession, request: Request, resource: CatalogueResourceXHTML, mode: str,
                              theme: Optional[str]) -> Union[HTMLResponse, Response]:
    if theme is None:
        theme = get_current_theme(request)

    widget_info = resource.description
    xhtml = resource.xhtml

    # Check if the xhtml code has been cached
    if widget_info.contents.cacheable:
        cache_key = xhtml.get_cache_key(str(resource.id), get_current_domain(request), mode, theme)
        cache_entry = await cache.get(cache_key)
        if cache_entry is not None:
            response = Response(content=cache_entry['code'], media_type=cache_entry['content_type'])
            patch_cache_headers(response, cache_entry['timestamp'], cache_entry['timeout'])
            return response

    # Process xhtml
    content_type = widget_info.contents.contenttype
    charset = widget_info.contents.charset

    code = xhtml.code
    if not xhtml.cacheable or code == '':
        try:
            code = download_local_file(os.path.join(wgt_deployer.root_dir, url2pathname(xhtml.url)))
        except Exception as e:
            if isinstance(e, IOError) and e.errno == errno.ENOENT:
                return build_response(request, 404, {'error_msg': _("Widget code not found"), 'details': str(e)},
                                      WIDGET_ERROR_FORMATTERS)
    else:
        code = code.encode(charset)

    if xhtml.cacheable and (xhtml.code == '' or xhtml.code_timestamp is None):
        try:
            xhtml.code = code.decode(charset)
        except UnicodeDecodeError:
            msg = _(
                f"Widget code was not encoded using the specified charset ({charset} as stated in the widget description file).")
            return build_response(request, 502, {'error_msg': msg}, WIDGET_ERROR_FORMATTERS)

        xhtml.code_timestamp = time.time() * 1000
        await save_catalogue_resource_xhtml(db, resource.id, xhtml)

    try:
        code = await fix_widget_code(code, content_type, request, charset, xhtml.use_platform_style,
                                     process_requirements(widget_info.requirements), mode, theme,
                                     resource.get_processed_info().macversion)
    except UnicodeDecodeError:
        msg = _(
            f"Widget code was not encoded using the specified charset ({charset} as stated in the widget description file).")
        return build_response(request, 502, {'error_msg': msg}, WIDGET_ERROR_FORMATTERS)
    except Exception as e:
        msg = _('Error processing widget code')
        return build_response(request, 502, {'error_msg': msg, 'details': str(e)}, WIDGET_ERROR_FORMATTERS)

    if xhtml.cacheable:
        cache_timeout = 31536000  # 1 year
        cache_entry = {
            'code': code,
            'content_type': f"{content_type}; charset={charset}",
            'timestamp': xhtml.code_timestamp,
            'timeout': cache_timeout
        }
        await cache.set(cache_key, cache_entry, cache_timeout)
    else:
        cache_timeout = 0

    response = HTMLResponse(content=code, media_type=f"{content_type}; charset={charset}")
    patch_cache_headers(response, xhtml.code_timestamp, cache_timeout)
    return response


def check_requirements(resource: MACDWidget) -> None:
    active_features = get_active_features()

    for requirement in resource.requirements:
        if requirement.type == 'feature':
            if requirement.name not in active_features:
                raise UnsupportedFeature(
                    f"Required feature ({requirement.name}) is not enabled for this WireCloud installation.")
        else:
            raise UnsupportedFeature(f"Unsupported requirement type ({requirement.type}).")


async def create_widget_from_wgt(db: DBSession, wgt_file: WgtFile, deploy_only: bool = False) -> None:
    template = wgt_deployer.deploy(wgt_file)
    if template.get_resource_type() != MACType.widget:
        raise Exception()

    if not deploy_only:
        widget_info = template.get_resource_info()
        check_requirements(widget_info)

        widget = await get_catalogue_resource_with_xhtml(db, template.get_resource_vendor(),
                                                         template.get_resource_name(), template.get_resource_version())
        widget_code = template.get_absolute_url(widget_info.contents.src)
        widget.xhtml = XHTML(
            uri='/'.join((template.get_resource_vendor(), template.get_resource_name(),
                          template.get_resource_version())) + "/xhtml",
            url=widget_code,
            content_type=widget_info.contents.contenttype,
            use_platform_style=widget_info.contents.useplatformstyle,
            cacheable=widget_info.contents.cacheable
        )
        await save_catalogue_resource_xhtml(db, widget.id, widget.xhtml)

        return widget

    return None
