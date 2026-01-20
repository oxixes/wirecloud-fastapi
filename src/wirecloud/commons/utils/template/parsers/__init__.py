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

# TODO Add translations

import re
from typing import Any
from copy import deepcopy
from urllib.parse import urljoin
from lxml import etree
import rdflib

from wirecloud.commons.utils.template.base import ObsoleteFormatError, TemplateFormatError, TemplateParseException
from wirecloud.commons.utils.template.schemas.macdschemas import *
from wirecloud.database import Id
from wirecloud.platform.wiring.schemas import WiringInput, WiringOutput
from wirecloud.commons.utils.template.parsers.json import JSONTemplateParser
from wirecloud.commons.utils.template.parsers.xml import ApplicationMashupTemplateParser
from wirecloud.commons.utils.template.parsers.rdf import RDFTemplateParser

__all__ = ('ObsoleteFormatError', 'TemplateFormatError', 'TemplateParseException', 'TemplateParser')

BASIC_URL_FIELDS = ['doc', 'image', 'smartphoneimage']


def absolutize_url_field(value: str, base_url: str) -> str:
    value = value.strip()
    if value != '':
        value = urljoin(base_url, value)

    return value


class TemplateParser(object):
    _doc = None
    _parser = None
    parsers = (ApplicationMashupTemplateParser, JSONTemplateParser, RDFTemplateParser)

    def __init__(self, template: Union[str, bytes, dict, etree.Element, rdflib.Graph], base: str = None):
        self.base = base

        for parser in self.parsers:
            try:
                self._parser = parser(template)
                # We have found a valid parser for this document, stop
                # searching
                break
            except TemplateParseException:
                # A TemplateParseException means that the document uses the
                # format associated with the parser (except when the
                # ObsoleteFormatError is raised), but that something is not
                # correct
                raise
            except Exception:
                # Any other exception means that the document cannot be read
                # by the current parser, try the next one
                pass

        if self._parser is None:
            raise TemplateFormatError('No valid parser found')

        self._parser._init()

    def set_base(self, base: str) -> None:
        self.base = base

    def get_resource_type(self) -> MACType:
        return self._parser.get_resource_type()

    def get_resource_name(self) -> Name:
        return self._parser.get_resource_name()

    def get_resource_vendor(self) -> Vendor:
        return self._parser.get_resource_vendor()

    def get_resource_version(self) -> Version:
        return self._parser.get_resource_version()

    def get_resource_info(self) -> MACD:
        return self._parser.get_resource_info()

    def get_absolute_url(self, url: str, base: Optional[str] = None) -> str:
        if base is None:
            base = self.base

        return urljoin(base, url)

    def get_resource_processed_info(self, base: Optional[str] = None, lang: Optional[str] = None,
                                    process_urls: bool = True, translate: bool = True,
                                    process_variables: bool = False) -> MACD:
        info = deepcopy(self.get_resource_info())

        if translate and lang is None:
            # TODO Obtain lang from the request
            # lang = translation.get_language()
            lang = "en"

        variables: dict[str, Union[MACDPreference, MACDProperty, WiringInput, WiringOutput]] = {}
        if info.type == MACType.widget or info.type == MACType.operator:
            for pref in info.preferences:
                variables[pref.name] = pref
            for prop in info.properties:
                variables[prop.name] = prop
            for inputendpoint in info.wiring.inputs:
                variables[inputendpoint.name] = inputendpoint
            for outputendpoint in info.wiring.outputs:
                variables[outputendpoint.name] = outputendpoint

        # process translations
        if translate and len(info.translations) > 0:
            translation = info.translations[info.default_lang]
            if lang in info.translations:
                translation.update(info.translations[lang])

            for index in translation:
                value = translation[index]
                usages = info.translation_index_usage[index]
                for use in usages:
                    if use.type == 'resource':
                        setattr(info, use.field, getattr(info, use.field).replace('__MSG_' + index + '__', value))
                    elif use.type in ('vdef', 'inputendpoint', 'outputendpoint'):
                        variable = variables[use.variable]
                        for field in vars(variable):
                            if isinstance(getattr(variable, field), str):
                                setattr(variable, field, getattr(variable, field).replace('__MSG_' + index + '__', value))
                    elif use.type == 'upo':
                        variable = variables[use.variable]
                        for option in variable.options:
                            for field in vars(option):
                                if isinstance(getattr(option, field), str):
                                    setattr(option, field, getattr(option, field).replace('__MSG_' + index + '__', value))

        info.translations = {}
        info.translation_index_usage = {}

        # Provide a fallback for the title
        if info.title == '':
            info.title = info.name

        # Process resource variables
        if process_variables and (info.type == MACType.widget or info.type == MACType.operator):
            for vardef in info.preferences:
                info.variables.all[vardef.name] = vardef
                info.variables.preferences[vardef.name] = vardef

            for vardef in info.properties:
                info.variables.all[vardef.name] = vardef
                info.variables.properties[vardef.name] = vardef

        if process_urls is False:
            return info

        if base is None:
            base = self.base

        # process url fields
        for field in BASIC_URL_FIELDS:
            setattr(info, field, absolutize_url_field(getattr(info, field), base))

        if info.type == MACType.widget:
            info.contents.src = absolutize_url_field(info.contents.src, base)
            for altcontent in info.altcontents:
                altcontent.src = absolutize_url_field(altcontent.src, base)

        if info.type == MACType.widget or info.type == MACType.operator:
            info.js_files = [absolutize_url_field(js_file, base) for js_file in info.js_files]

        return info

    def get_resource_dependencies(self) -> set[str]:
        dependencies = set()

        info = self.get_resource_info()
        if info.type != MACType.mashup:
            return dependencies

        for tab_entry in info.tabs:
            for resource in tab_entry.resources:
                dependencies.add('/'.join([resource.vendor, resource.name, resource.version]))

        for id_, op in info.wiring.operators.items():
            dependencies.add(op.name)

        return dependencies


class TemplateValueProcessor(BaseModel):
    context: dict[str, Union[str, dict[str, Any]]]

    _RE = re.compile(r'(%+)\(([a-zA-Z][\w-]*(?:\.[a-zA-Z][\w-]*)*)\)')

    def __repl(self, matching):
        plen = len(matching.group(1))
        if (plen % 2) == 0:
            return '%' * (plen // 2) + '(' + matching.group(2) + ')'

        var_path = matching.group(2).split('.')
        current_context = self.context

        while len(var_path) > 0:
            current_path = var_path.pop(0)

            if hasattr(current_context, current_path):
                current_context = getattr(current_context, current_path)
            elif current_path in current_context:
                current_context = current_context[current_path]
            else:
                current_context = self._context
                break

        if current_context != self._context:
            return current_context
        else:
            return matching.group(0)

    def process(self, value: str) -> str:
        return self._RE.sub(self.__repl, value)