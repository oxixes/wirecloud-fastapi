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

import orjson as json
from typing import Optional
from wirecloud.commons.utils.http import get_xml_error_response, get_json_error_response, HTTPError

title = "WireCloud"
logo_url = "https://raw.githubusercontent.com/Wirecloud/wirecloud/develop/src/wirecloud/defaulttheme/static/images/logos/wc1.png"
version = "2.0.0"
summary = "Widgets Container and Mashup edition tools. Reference implementation of the FIWARE Application Mashup GE."
license_info = {"name": "AGPL-3.0 with classpath-like exception",
                "url": "https://github.com/Wirecloud/wirecloud/blob/develop/LICENSE"}
contact = {"name": "WireCloud",
           "url": "https://github.com/Wirecloud/wirecloud"}

description = """\
WireCloud builds on cutting-edge end-user development, RIA and semantic
technologies to offer a next-generation end-user centred web application mashup
platform aimed at leveraging the long tail of the Internet of Services.

WireCloud builds on cutting-edge end-user (software) development, RIA and
semantic technologies to offer a next-generation end-user centred web
application mashup platform aimed at allowing end users without programming
skills to easily create web applications and dashboards/cockpits (e.g. to
visualize their data of interest or to control their domotized home or
environment). Web application mashups integrate heterogeneous data, application
logic, and UI components (widgets) sourced from the Web to create new coherent
and value-adding composite applications. They are targeted at leveraging the
"long tail" of the Web of Services (a.k.a. the Programmable Web) by exploiting
rapid development, DIY, and shareability. They typically serve a specific
situational (i.e. immediate, short-lived, customized) need, frequently with high
potential for reuse. Is this "situational" character which precludes them to be
offered as 'off-the-shelf' functionality by solution providers, and therefore
creates the need for a tool like WireCloud.

This project is part of [FIWARE](https://www.fiware.org/). For more information
check the FIWARE Catalogue entry for
[Context Processing, Analysis and Visualization](https://github.com/Fiware/catalogue/tree/master/processing).\
"""

error_response_xml_schema = {
    "type": "object",
    "format": "xml",
    "xml": {
        "name": "error",
    },
    "properties": {
        "description": {
            "type": "string",
            "xml": {
                "name": "description"
            }
        },
        "details": {
            "type": "object",
            "additionalProperties": True,
            "xml": {
                "name": "details"
            }
        }
    }
}


def generate_error_response_xml_example(description: str, details: Optional[dict] = None) -> str:
    return get_xml_error_response(None, "", 0, context={"error_msg": description, "details": details})


def generate_error_response_json_example(description: str, details: Optional[dict] = None) -> str:
    return get_json_error_response(None, "", 0, context={"error_msg": description, "details": details})


def generate_error_response_openapi_description(model_desc: str, description: str,
                                                details: Optional[dict] = None, include_schema: bool = True) -> dict:
    result = {"description": model_desc,
              "content": {
                  "application/json": {
                      "schema": {
                          "$ref": "#/components/schemas/HTTPError"
                      },
                      "example": json.loads(generate_error_response_json_example(description, details)),
                  },
                  "application/xml": {
                      "schema": error_response_xml_schema,
                      "example": generate_error_response_xml_example(description, details)
                  },
                  "text/plain": {
                      "example": description
                  },
                  "text/html": {
                      "example": "<h1>{}</h1>".format(description)
                  },
                  "application/xhtml+xml": {
                      "example": "<h1>{}</h1>".format(description)
                  }
              }}

    if include_schema:
        result["model"] = HTTPError

    return result


def generate_not_found_response_openapi_description(model_desc: str, include_schema: bool = True) -> dict:
    return generate_error_response_openapi_description(model_desc, 'Page Not Found',
                                                       include_schema=include_schema)


def generate_validation_error_response_openapi_description(model_desc: str, include_schema: bool = True) -> dict:
    return generate_error_response_openapi_description(model_desc, 'Invalid payload',
                                                       include_schema=include_schema)


def generate_not_acceptable_response_openapi_description(model_desc: str, mime_types: list[str], include_schema: bool = True) -> dict:
    msg = "The requested resource is only capable of generating content not acceptable according to the Accept headers sent in the request"
    details = {"mime_types": mime_types}
    return generate_error_response_openapi_description(model_desc, msg, details, include_schema=include_schema)


def generate_unsupported_media_type_response_openapi_description(model_desc: str, include_schema: bool = True) -> dict:
    msg = "Unsupported request media type"
    return generate_error_response_openapi_description(model_desc, msg, include_schema=include_schema)


def generate_auth_required_response_openapi_description(model_desc: str, include_schema: bool = True) -> dict:
    return generate_error_response_openapi_description(model_desc, "Authentication required",
                                                       include_schema=include_schema)


def generate_permission_denied_response_openapi_description(model_desc: str, msg: Optional[str], include_schema: bool = True) -> dict:
    if msg is None:
        msg = "Permission denied"
    return generate_error_response_openapi_description(model_desc, msg, include_schema=include_schema)
