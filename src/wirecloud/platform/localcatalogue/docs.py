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

# MultipleResourcesInstalledResponse
multiple_resources_installed_response_resource_details_description = "The details of the main resource"
multiple_resources_installed_response_extra_resources_description = "A list of extra resources that were installed along with the main resource"

# ResourceCreateData
resource_create_data_install_embedded_resources_description = "If true, the embedded resources will be installed along with the main resource"
resource_create_data_force_create_description = "If true, an error will be thrown if the resource already exists in the local catalogue"
resource_create_data_url_description = "The URL of the resource template to be installed"
resource_create_data_headers_description = "Additional headers to be sent in the request to obtain the resource"

# ResourceCreateFormData
resource_create_form_data_force_create_description = "If true, an error will be thrown if the resource already exists in the local catalogue"
resource_create_form_data_public_description = "If true, the resource will be created as public, otherwise it will be private to the users or groups specified in the request"
resource_create_form_data_users_description = "Comma-separated list of user IDs that will have access to the resource. If not specified, the resource will be private to the user creating it."
resource_create_form_data_groups_description = "Comma-separated list of group IDs that will have access to the resource. If not specified, the resource will be private to the user creating it."
resource_create_form_data_install_embedded_resources_description = "If true, the embedded resources will be installed along with the main resource. If false, only the main resource will be installed."
resource_create_form_data_file_description = "The WGT file to be installed."

# GET /api/resources
get_resource_collection_summary = "Get all available resources"
get_resource_collection_description = "Get all available resources in the local catalogue. If the user is not authenticated, only public resources will be returned."
get_resource_collection_process_urls_description = "Process URLs in the response"
get_resource_collection_response_description = "A dictionary containing the available resources. The keys are the local URI part of the resources and the values are the processed information of the resources"
get_resource_collection_not_acceptable_response_description = "Invalid request content type"
get_resource_entry_group_validation_error_response_description = "The request data (the query) was invalid"
get_resource_collection_response_example = {
    "example/widget/1.0.0": {
        "type": "widget",
        "macversion": 1,
        "name": "widget",
        "vendor": "example",
        "version": "1.0.0",
        "title": "Example",
        "description": "Example Widget",
        "longdescription": "",
        "email": "example@example.com",
        "homepage": "",
        "doc": "http://example.com/docs/display/wirecloud/Widgets",
        "changelog": "",
        "image": "http://wc.example/api/widget/example/widget/1.0.0/images/catalogue.png",
        "smartphoneimage": "http://wc.example/api/widget/example/widget/1.0.0/images/catalogue.png",
        "license": "",
        "licenseurl": "",
        "issuetracker": "",
        "authors": [
          {
            "name": "example",
            "email": None,
            "url": None
          }
        ],
        "contributors": [],
        "requirements": [],
        "default_lang": "en",
        "translations": {},
        "translation_index_usage": {},
        "wgt_files": None,
        "preferences": [
          {
            "name": "Example",
            "type": "text",
            "label": "Example label",
            "description": "Example description.",
            "default": "Example",
            "readonly": False,
            "required": False,
            "secure": False,
            "multiuser": False,
            "value": None,
            "options": None,
            "language": None
          }
        ],
        "properties": [],
        "entrypoint": None,
        "js_files": [],
        "wiring": {
          "inputs": [],
          "outputs": []
        },
        "variables": {
          "all": {},
          "preferences": {},
          "properties": {}
        },
        "contents": {
          "src": "http://wc.example/api/widget/example/widget/1.0.0/index.html",
          "contenttype": "text/html",
          "charset": "utf-8",
          "cacheable": False,
          "useplatformstyle": True
        },
        "altcontents": [],
        "widget_width": "5",
        "widget_height": "8"
    }
}

# POST /api/resources
create_resource_summary = "Create a new resource"
create_resource_description = ("Create a new resource in the local catalogue. The resource will be created from a template located "
                               "at the specified URL, or from the provided WGT file. The query parameters are used only if content type "
                               "application/octet-stream is used, otherwise the form or json data will be used.")
create_resource_force_create_parameter_description = "If true, an error will be thrown if the resource already exists in the local catalogue"
create_resource_install_embedded_resources_parameter_description = ("If true, the embedded resources will be installed along with the main resource. "
                                                                    "If false, only the main resource will be installed.")
create_resource_public_parameter_description = "If true, the resource will be created as public, otherwise it will be private to the users or groups specified in the request"
create_resource_users_parameter_description = ("Comma-separated list of user IDs that will have access to the resource. "
                                               "If not specified, the resource will be private to the user creating it.")
create_resource_groups_parameter_description = ("Comma-separated list of group IDs that will have access to the resource. "
                                                "If not specified, the resource will be private to the user creating it.")
create_resource_ok_response_description = "The resource already existed in the local catalogue"
create_resource_created_response_description = "The resource was created successfully"
create_resource_bad_request_response_description = "The request data (the body or uploaded file) was invalid"
create_resource_auth_required_response_description = "Authentication is required to create a resource"
create_resource_permission_denied_response_description = "The user does not have permission to create the resource"
create_resource_permission_denied_response_example_msg = "You do not have permission to create this resource for the given users or groups"
create_resource_entry_not_found_response_description = "The specified users or groups do not exist"
create_resource_entry_not_acceptable_response_description = "Invalid request content type"
create_resource_conflict_response_description = "The resource already exists in the local catalogue and the force_create parameter was set to true"
create_resource_response_example = {
    "type": "widget",
    "macversion": 1,
    "name": "widget",
    "vendor": "example",
    "version": "1.0.0",
    "title": "Example",
    "description": "Example Widget",
    "longdescription": "",
    "email": "example@example.com",
    "homepage": "",
    "doc": "http://example.com/docs/display/wirecloud/Widgets",
    "changelog": "",
    "image": "http://wc.example/api/widget/example/widget/1.0.0/images/catalogue.png",
    "smartphoneimage": "http://wc.example/api/widget/example/widget/1.0.0/images/catalogue.png",
    "license": "",
    "licenseurl": "",
    "issuetracker": "",
    "authors": [
      {
        "name": "example",
        "email": None,
        "url": None
      }
    ],
    "contributors": [],
    "requirements": [],
    "default_lang": "en",
    "translations": {},
    "translation_index_usage": {},
    "wgt_files": None,
    "preferences": [
      {
        "name": "Example",
        "type": "text",
        "label": "Example label",
        "description": "Example description.",
        "default": "Example",
        "readonly": False,
        "required": False,
        "secure": False,
        "multiuser": False,
        "value": None,
        "options": None,
        "language": None
      }
    ],
    "properties": [],
    "entrypoint": None,
    "js_files": [],
    "wiring": {
      "inputs": [],
      "outputs": []
    },
    "variables": {
      "all": {},
      "preferences": {},
      "properties": {}
    },
    "contents": {
      "src": "http://wc.example/api/widget/example/widget/1.0.0/index.html",
      "contenttype": "text/html",
      "charset": "utf-8",
      "cacheable": False,
      "useplatformstyle": True
    },
    "altcontents": [],
    "widget_width": "5",
    "widget_height": "8"
}

# GET /api/resource/{vendor}/{name}/{version}
get_resource_entry_summary = "Get a specific resource WGT file"
get_resource_entry_description = "Get a specific resource WGT file from the local catalogue."
get_resource_entry_parameter_vendor_description = "The vendor of the resource"
get_resource_entry_parameter_name_description = "The name of the resource"
get_resource_entry_parameter_version_description = "The version of the resource"
get_resource_entry_response_description = "The WGT file of the resource"
get_resource_entry_auth_required_response_description = "Authentication is required to access the resource"
get_resource_entry_permission_denied_response_description = "The user does not have permission to access the resource"
get_resource_entry_not_found_response_description = "The resource does not exist in the local catalogue"

# DELETE /api/resource/{vendor}/{name}/{version}
delete_resource_entry_version_summary = "Delete a specific resource version"
delete_resource_entry_version_description = "Delete a specific resource version from the local catalogue."
delete_resource_entry_version_parameter_vendor_description = "The vendor of the resource"
delete_resource_entry_version_parameter_name_description = "The name of the resource"
delete_resource_entry_version_parameter_version_description = "The version of the resource"
delete_resource_entry_version_allusers_parameter_description = "If true, the resource will be deleted for all users, otherwise it will be deleted only for the user making the request"
delete_resource_entry_version_affected_parameter_description = "If true, the response will include the affected versions of the resource that were deleted"
delete_resource_entry_version_auth_required_response_description = "Authentication is required to delete the resource"
delete_resource_entry_version_permission_denied_response_description = "The user does not have permission to delete the resource"
delete_resource_entry_version_not_found_response_description = "The resource does not exist in the local catalogue"
delete_resource_entry_version_ok_response_description = "The affected versions of the resource that were deleted successfully"
delete_resource_entry_version_no_content_response_description = "The resource was deleted successfully"
delete_resource_entry_version_response_example = {
    "affectedVersions": ["1.0.0"]
}

# GET /api/resource/{vendor}/{name}/{version}/description
get_resource_description_summary = "Get a specific resource description"
get_resource_description_description = "Get a specific resource description from the local catalogue."
get_resource_description_parameter_vendor_description = "The vendor of the resource"
get_resource_description_parameter_name_description = "The name of the resource"
get_resource_description_parameter_version_description = "The version of the resource"
get_resource_description_parameter_process_urls_description = "If true, the URLs in the response will be processed to include the full URL"
get_resource_description_parameter_include_wgt_files_description = "If true, the list of files in the WGT will be included in the response"
get_resource_description_response_description = "The description of the resource"
get_resource_description_not_found_response_description = "The resource does not exist in the local catalogue"
get_resource_description_response_example = {
    "type": "widget",
    "macversion": 1,
    "name": "widget",
    "vendor": "example",
    "version": "1.0.0",
    "title": "Example",
    "description": "Example Widget",
    "longdescription": "",
    "email": "example@example.com",
    "homepage": "",
    "doc": "http://example.com/docs/display/wirecloud/Widgets",
    "changelog": "",
    "image": "http://wc.example/api/widget/example/widget/1.0.0/images/catalogue.png",
    "smartphoneimage": "http://wc.example/api/widget/example/widget/1.0.0/images/catalogue.png",
    "license": "",
    "licenseurl": "",
    "issuetracker": "",
    "authors": [
      {
        "name": "example",
        "email": None,
        "url": None
      }
    ],
    "contributors": [],
    "requirements": [],
    "default_lang": "en",
    "translations": {},
    "translation_index_usage": {},
    "wgt_files": None,
    "preferences": [
      {
        "name": "Example",
        "type": "text",
        "label": "Example label",
        "description": "Example description.",
        "default": "Example",
        "readonly": False,
        "required": False,
        "secure": False,
        "multiuser": False,
        "value": None,
        "options": None,
        "language": None
      }
    ],
    "properties": [],
    "entrypoint": None,
    "js_files": [],
    "wiring": {
      "inputs": [],
      "outputs": []
    },
    "variables": {
      "all": {},
      "preferences": {},
      "properties": {}
    },
    "contents": {
      "src": "http://wc.example/api/widget/example/widget/1.0.0/index.html",
      "contenttype": "text/html",
      "charset": "utf-8",
      "cacheable": False,
      "useplatformstyle": True
    },
    "altcontents": [],
    "widget_width": "5",
    "widget_height": "8"
}

# DELETE /api/resource/{vendor}/{name}
delete_resource_entry_summary = "Delete a specific resource"
delete_resource_entry_description = "Delete a specific resource from the local catalogue."

# GET /api/workspace/{workspace_id}/resources
get_workspace_resource_collection_summary = "Get all available resources for a workspace"
get_workspace_resource_collection_description = "Get all available resources for a specific workspace identified by its ID."
get_workspace_resource_collection_response_description = "A dictionary containing the available resources for the workspace. The keys are the local URI part of the resources and the values are the processed information of the resources"
get_workspace_resource_collection_not_found_response_description = "The workspace does not exist"
get_workspace_resource_collection_not_acceptable_response_description = "Invalid request content type"
get_workspace_resource_collection_response_example = {
    "example/widget/1.0.0": {
        "type": "widget",
        "macversion": 1,
        "name": "widget",
        "vendor": "example",
        "version": "1.0.0",
        "title": "Example",
        "description": "Example Widget",
        "longdescription": "",
        "email": "example@example.com",
        "homepage": "",
        "doc": "http://example.com/docs/display/wirecloud/Widgets",
        "changelog": "",
        "image": "http://wc.example/api/widget/example/widget/1.0.0/images/catalogue.png",
        "smartphoneimage": "http://wc.example/api/widget/example/widget/1.0.0/images/catalogue.png",
        "license": "",
        "licenseurl": "",
        "issuetracker": "",
        "authors": [
          {
            "name": "example",
            "email": None,
            "url": None
          }
        ],
        "contributors": [],
        "requirements": [],
        "default_lang": "en",
        "translations": {},
        "translation_index_usage": {},
        "wgt_files": None,
        "preferences": [
          {
            "name": "Example",
            "type": "text",
            "label": "Example label",
            "description": "Example description.",
            "default": "Example",
            "readonly": False,
            "required": False,
            "secure": False,
            "multiuser": False,
            "value": None,
            "options": None,
            "language": None
          }
        ],
        "properties": [],
        "entrypoint": None,
        "js_files": [],
        "wiring": {
          "inputs": [],
          "outputs": []
        },
        "variables": {
          "all": {},
          "preferences": {},
          "properties": {}
        },
        "contents": {
          "src": "http://wc.example/api/widget/example/widget/1.0.0/index.html",
          "contenttype": "text/html",
          "charset": "utf-8",
          "cacheable": False,
          "useplatformstyle": True
        },
        "altcontents": [],
        "widget_width": "5",
        "widget_height": "8"
    }
}
get_workspace_resource_collection_parameter_workspace_id_description = "The ID of the workspace for which to retrieve the resources"
get_workspace_resource_collection_parameter_process_urls_description = "Process URLs in the response"