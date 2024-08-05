# -*- coding: utf-8 -*-
import json
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

# TODO Move into separate files

from typing import Optional
from src.wirecloud.commons.utils.http import get_xml_error_response, get_json_error_response, HTTPError

title = "WireCloud"
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
                                                details: Optional[dict] = None) -> dict:
    return {"description": model_desc,
            "model": HTTPError,
            "content": {
                "application/json": {
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
                }
            }}


# AUTH
permission_codename_description = "The permission's codename"

group_id_description = "The group's id"
group_name_description = "The group's name"

user_username_description = "The user's username"
user_id_description = "The user's id"
user_email_description = "The user's email"
user_first_name_description = "The user's first name"
user_last_name_description = "The user's last name"
user_is_superuser_description = "Whether the user is a superuser"
user_is_staff_description = "Whether the user is staff"
user_is_active_description = "Whether the user is active"
user_date_joined_description = "The date the user joined"
user_last_login_description = "The user's last login"

user_login_password_description = "The user's password"

user_token_token_description = "The user's token"
user_token_token_type_description = "The type of token"

login_response_model_description = "The user's JWT"
login_response_model_example = {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOjEsImlzcyI6IldpcmVjbG91ZCIsImV4cCI6MTcyMTYzMTk1NywiaWF0IjoxNzIwNDIyMzU3fQ.SIGNATURE",
    "token_type": "bearer"
}
login_error_invalid_user_pass_response_model_description = "Invalid username or password"
login_error_invalid_payload_response_model_descrition = "Validation error"

# CONTEXT
context_key_description_description = "The context key's description"
context_key_label_description = "The context key's label"
platform_context_key_value_description = "The context key's value"
context_platform_description = "The platform context"
context_workspace_description = "The workspace context description"