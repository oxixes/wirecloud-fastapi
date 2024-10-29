# -*- coding: utf-8 -*-

# Copyright (c) 2013-2017 CoNWeT Lab., Universidad Politécnica de Madrid
# Copyright (c) 2019-2020 Future Internet Consulting and Development Solutions S.L.

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

import orjson as json

from src.wirecloud.commons.utils.template.schemas.macdschemas import MACD, MACType
from src.wirecloud.translation import gettext as _


def remove_empty_string_fields(fields: tuple[str, ...], data: dict) -> None:
    for field in fields:
        value = data.get(field)

        if value is not None and not isinstance(value, str):
            raise Exception(_("Invalid value for field %s") % field)

        if field in data and (value is None or value == ''):
            del data[field]


def remove_empty_array_fields(fields: tuple[str, ...], data: dict) -> None:
    for field in fields:
        value = data.get(field)

        if value is not None and not isinstance(value, (list, tuple)):
            raise Exception(_("Invalid value for field %s") % field)

        if field in data and (value is None or len(value) == 0):
            del data[field]


def write_json_description(template_info: MACD) -> str:
    template_info_json = template_info.model_dump()

    remove_empty_string_fields(('title', 'description', 'longdescription', 'homepage', 'doc', 'image', 'smartphoneimage', 'license', 'licenseurl', 'issuetracker'), template_info_json)
    remove_empty_array_fields(('authors', 'contributors', 'altcontents', 'embedded'), template_info_json)

    if template_info.type == MACType.mashup:
        for tab in template_info_json['tabs']:
            remove_empty_string_fields(('title',), tab)

    del template_info_json['translation_index_usage']
    return json.dumps(template_info_json).decode('utf-8')
