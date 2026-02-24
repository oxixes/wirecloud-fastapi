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

# CatalogueResourceDataSummaryPermissions
catalogue_resource_data_summary_permissions_delete_description = "Whether the user can delete the catalogue resource"
catalogue_resource_data_summary_permissions_uninstall_description = "Whether the user can uninstall the catalogue resource"

# CatalogueResourceDataSummaryBase
catalogue_resource_data_summary_version_description = "The version of the catalogue resource"
catalogue_resource_data_summary_date_description = "When the catalogue resource was added to the catalogue (timestamp)"
catalogue_resource_data_summary_permissions_description = "Permissions for the catalogue resource"
catalogue_resource_data_summary_authors_description = "Authors of the catalogue resource"
catalogue_resource_data_summary_contributors_description = "Contributors of the catalogue resource"
catalogue_resource_data_summary_title_description = "The title of the catalogue resource"
catalogue_resource_data_summary_description_description = "The description of the catalogue resource"
catalogue_resource_data_summary_longdescription_description = "A HTML description of the catalogue resource"
catalogue_resource_data_summary_email_description = "The contact email of the catalogue resource author or vendor"
catalogue_resource_data_summary_image_description = "The image URI of the catalogue resource"
catalogue_resource_data_summary_homepage_description = "The homepage URL of the catalogue resource"
catalogue_resource_data_summary_doc_description = "The documentation URI of the catalogue resource"
catalogue_resource_data_summary_changelog_description = "The changelog URI of the catalogue resource"
catalogue_resource_data_summary_size_description = "The size of the catalogue resource in bytes"
catalogue_resource_data_summary_uri_template_description = "The URI template of the catalogue resource"
catalogue_resource_data_summary_license_description = "The license of the catalogue resource (name)"
catalogue_resource_data_summary_licenseurl_description = "The license URL of the catalogue resource"
catalogue_resource_data_summary_issuetracker_description = "The issue tracker URL of the catalogue resource"

# CatalogueResourceDataSummaryIdentifier
catalogue_resource_data_summary_vendor_description = "The vendor of the catalogue resource"
catalogue_resource_data_summary_name_description = "The name of the catalogue resource"
catalogue_resource_data_summary_type_description = "The type of the catalogue resource (widget, mashup, operator)"

# CatalogueResourceDataSummaryGroup
catalogue_resource_data_summary_group_versions_description = "List of version descriptions of the catalogue resource"

# CatalogueResourceDeleteResults
catalogue_resource_delete_results_affected_versions_description = "The list of affected versions of the catalogue resource"

# POST /resources
create_resource_entry_request_schema_form = {
    "type": "object",
    "properties": {
        "file": {
            "type": "string",
            "format": "binary",
            "description": "The file to create the catalogue resource from"
        },
        "public": {
            "type": "boolean",
            "description": "Whether the catalogue resource should be public or not"
        }
    },
    "required": ["file"]
}
create_resource_entry_request_schema_binary = {
    "type": "string",
    "format": "binary",
    "description": "The file to create the catalogue resource from"
}
create_resource_entry_summary = "Create a catalogue resource"
create_resource_entry_description = "Creates a catalogue resource from the provided file."
create_resource_entry_response_description = "The catalogue resource was created"
create_resource_entry_bad_request_response_description = "Missing or invalid data was provided"
create_resource_entry_auth_required_response_description = "Authentication is required to create the catalogue resource"
create_resource_entry_permission_denied_response_description = "The user does not have permission to create the catalogue resource"
create_resource_entry_conflict_response_description = "The catalogue resource already exists"

# GET /resources
get_resources_entries_summary = "Get catalogue resources"
get_resources_entries_description = "Get a list of catalogue resources from the provided query (leave empty to get all)."
get_resources_entries_response_description = "The list of catalogue resources"
get_resources_entries_bad_request_response_description = "Missing or invalid data was provided"
get_resources_entries_validation_error_response_description = "The request data was invalid"
get_resources_entries_q_description = "The search query to filter the catalogue resources"
get_resources_entries_pagenum_description = "The page number to retrieve (starting from 1)"
get_resources_entries_maxresults_description = "The maximum number of results to return per page"
get_resources_entries_orderby_description = "Comma-separated list of fields to order the results by. Prefix with '-' for descending order."
get_resources_entries_scope_description = "The scope of the search: mashup, widget and operator"
get_resources_entries_response_example = {
    "offset": 0,
    "pagecount": 1,
    "pagelen": 1,
    "pagenum": 1,
    "results": [
        {
            "id": "6889005fa185ce37a5faaa5a",
            "vendor_name": "api/workspace-1",
            "vendor": "api",
            "name": "workspace-1",
            "version": "1.0",
            "description_url": "api_workspace-1_1.0.wgt",
            "type": "mashup",
            "creation_date": "2025-07-29T17:09:51.480000",
            "public": False,
            "title": "prueba",
            "description": "Temporal mashup for the workspace copy operation",
            "image": "http://localhost:8000/catalogue/media/api/workspace-1/1.0/images/catalogue.png",
            "smartphoneimage": "http://localhost:8000/catalogue/media/api/workspace-1/1.0/images/smartphone.jpeg",
            "input_friendcodes": [],
            "output_friendcodes": [],
            "others": [],
            "uri": "api/workspace-1/1.0"
        }
    ],
    "total": 1
}


# GET /resource/{vendor}/{name}
get_resource_entry_group_summary = "Get catalogue resource version descriptions"
get_resource_entry_group_description = "Get the version descriptions of a catalogue resource."
get_resource_entry_group_response_description = "The version descriptions of a catalogue resource"
get_resource_entry_group_vendor_description = "The vendor of the catalogue resource"
get_resource_entry_group_name_description = "The name of the catalogue resource"
get_resource_entry_group_not_found_response_description = "The catalogue resource was not found"
get_resource_entry_group_not_acceptable_response_description = "Invalid request content type"
get_resource_entry_group_validation_error_response_description = "The request data was invalid"
get_resource_entry_group_response_example = {
  "vendor": "Wirecloud",
  "name": "awesome-widget",
  "type": "widget",
  "versions": [
    {
      "version": "1.0.0.",
      "date": 1722902021135,
      "permissions": {
        "delete": False,
        "uninstall": False
      },
      "authors": [
        {
          "name": "Wirecloud",
          "email": "wirecloud@example.com",
          "url": "https://wirecloud.example.com"
        }
      ],
      "contributors": [
          {
            "name": "John Doe",
            "email": "john.doe@wirecloud.example.com",
            "url": "https://wirecloud.example.com/johndoe"
          }
      ],
      "title": "Awesome Widget",
      "description": "This is an awesome widget",
      "longdescription": "<p>Using this widget makes you</p>\n<h2>awesome</h2>",
      "email": "wirecloud@example.com",
      "image": "https://wirecloud.example.com/catalogue/media/Wirecloud/awesome-widget/1.0.0/images/catalogue.png",
      "homepage": "https://wirecloud.example.com",
      "doc": "https://wirecloud.example.com/catalogue/media/Wirecloud/awesome-widget/1.0.0/doc/userguide.md",
      "changelog": "doc/changelog.md",
      "size": 5208,
      "uriTemplate": "https://wirecloud.example.com/catalogue/media/Wirecloud/awesome-widget/1.0.0/Wirecloud_awesome-widget_1.0.0.wgt",
      "license": "MIT",
      "licenseurl": "https://opensource.org/licenses/MIT",
      "issuetracker": "https://wirecloud.example.com/awesome-widget/issues"
    }
  ]
}

# DELETE /resource/{vendor}/{name}
delete_resource_entry_group_summary = "Delete all versions of a catalogue resource"
delete_resource_entry_group_description = "Delete all versions of a catalogue resource. This action is irreversible."
delete_resource_entry_group_response_description = "The affected versions of the catalogue resource"
delete_resource_entry_group_vendor_description = "The vendor of the catalogue resource"
delete_resource_entry_group_name_description = "The name of the catalogue resource"
delete_resource_entry_group_auth_required_response_description = "Authentication is required to delete the catalogue resource"
delete_resource_entry_group_permission_denied_response_description = "The user does not have permission to delete the catalogue resource"
delete_resource_entry_group_permission_denied_response_example_msg = "User example is not the owner of the resource wirecloud/example"
delete_resource_entry_group_not_found_response_description = "The catalogue resource was not found"
delete_resource_entry_group_not_acceptable_response_description = "Invalid request content type"
delete_resource_entry_group_validation_error_response_description = "The request data was invalid"
delete_resource_entry_group_response_example = {
    "affectedVersions": ["1.0.0", "1.0.1-rc1"]
}

# GET /resource/{vendor}/{name}/{version}
get_resource_entry_summary = "Get catalogue resource description"
get_resource_entry_description = "Get the description of a catalogue resource version."
get_resource_entry_response_description = "The description of a catalogue resource version"
get_resource_entry_vendor_description = "The vendor of the catalogue resource"
get_resource_entry_name_description = "The name of the catalogue resource"
get_resource_entry_version_description = "The version of the catalogue resource"
get_resource_entry_not_found_response_description = "The catalogue resource was not found"
get_resource_entry_not_acceptable_response_description = "Invalid request content type"
get_resource_entry_permission_denied_response_description = "The user does not have permission to access the resource"
get_resource_entry_permission_denied_response_example_msg = "User example does not have permission to access the resource wirecloud/example/1.0.0"
get_resource_entry_validation_error_response_description = "The request data was invalid"
get_resource_entry_response_example = {
  "vendor": "Wirecloud",
  "name": "awesome-widget",
  "type": "widget",
  "version": "1.0.0",
  "date": 1722902021135,
  "permissions": {
    "delete": False,
    "uninstall": False
  },
  "authors": [
      {
        "name": "Wirecloud",
        "email": "wirecloud@example.com",
        "url": "https://wirecloud.example.com"
      }
  ],
  "contributors": [
      {
        "name": "John Doe",
        "email": "john.doe@wirecloud.example.com",
        "url": "https://wirecloud.example.com/johndoe"
      }
  ],
  "title": "Awesome Widget",
  "description": "This is an awesome widget",
  "longdescription": "<p>Using this widget makes you</p>\n<h2>awesome</h2>>",
  "email": "wirecloud@example.com",
  "image": "https://wirecloud.example.com/catalogue/media/Wirecloud/awesome-widget/1.0.0/images/catalogue.png",
  "homepage": "https://wirecloud.example.com",
  "doc": "https://wirecloud.example.com/catalogue/media/Wirecloud/awesome-widget/1.0.0/doc/userguide.md",
  "changelog": "doc/changelog.md",
  "size": 5208,
  "uriTemplate": "https://wirecloud.example.com/catalogue/media/Wirecloud/awesome-widget/1.0.0/Wirecloud_awesome-widget_1.0.0.wgt",
  "license": "MIT",
  "licenseurl": "https://opensource.org/licenses/MIT",
  "issuetracker": "https://wirecloud.example.com/awesome-widget/issues"
}

# DELETE /resource/{vendor}/{name}/{version}
delete_resource_entry_summary = "Delete a catalogue resource version"
delete_resource_entry_description = "Delete a catalogue resource version. This action is irreversible."
delete_resource_entry_response_description = "The affected version of the catalogue resource"
delete_resource_entry_vendor_description = "The vendor of the catalogue resource"
delete_resource_entry_name_description = "The name of the catalogue resource"
delete_resource_entry_version_description = "The version of the catalogue resource"
delete_resource_entry_auth_required_response_description = "The user must be authenticated to delete the catalogue resource"
delete_resource_entry_permission_denied_response_description = "The user does not have permission to delete the catalogue resource"
delete_resource_entry_permission_denied_response_example_msg = "User example is not the owner of the resource wirecloud/example"
delete_resource_entry_not_found_response_description = "The catalogue resource was not found"
delete_resource_entry_not_acceptable_response_description = "Invalid request content type"
delete_resource_entry_validation_error_response_description = "The request data was invalid"
delete_resource_entry_response_example = {
    "affectedVersions": ["1.0.0"]
}

# GET /resource/{vendor}/{name}/{version}/changelog
get_resource_changelog_summary = "Get the catalogue resource changelog"
get_resource_changelog_description = "Get the changelog of a catalogue resource version."
get_resource_changelog_response_description = "The changelog of a catalogue resource version"
get_resource_changelog_vendor_description = "The vendor of the catalogue resource"
get_resource_changelog_name_description = "The name of the catalogue resource"
get_resource_changelog_version_description = "The version of the catalogue resource"
get_resource_changelog_from_version_description = "The version of the catalogue resource to start the changelog from (until the requested version). If not provided, the changelog will start from the first version. It is non-inclusive"
get_resource_changelog_permission_denied_response_description = "The user does not have permission to access the resource"
get_resource_changelog_permission_denied_response_example_msg = "User example does not have permission to access the resource wirecloud/example/1.0.0"
get_resource_changelog_not_found_response_description = "The catalogue resource was not found"
get_resource_changelog_not_acceptable_response_description = "Invalid request content type"
get_resource_changelog_validation_error_response_description = "The request data was invalid"
get_resource_changelog_response_example = """<h2>1.0.1</h2>
<ul>
<li>Added some fantastic features</li>
</ul>
<h2>1.0.0</h2>
<p>Initial version</p>"""

# GET /resource/{vendor}/{name}/{version}/userguide
get_resource_userguide_summary = "Get the catalogue resource user guide"
get_resource_userguide_description = "Get the user guide of a catalogue resource version."
get_resource_userguide_response_description = "The user guide of a catalogue resource version"
get_resource_userguide_vendor_description = "The vendor of the catalogue resource"
get_resource_userguide_name_description = "The name of the catalogue resource"
get_resource_userguide_version_description = "The version of the catalogue resource"
get_resource_userguide_permission_denied_response_description = "The user does not have permission to access the resource"
get_resource_userguide_permission_denied_response_example_msg = "User example does not have permission to access the resource wirecloud/example/1.0.0"
get_resource_userguide_not_found_response_description = "The catalogue resource was not found"
get_resource_userguide_not_acceptable_response_description = "Invalid request content type"
get_resource_userguide_validation_error_response_description = "The request data was invalid"
get_resource_userguide_response_example = """<h2>Introduction</h2>
<p>Awesome Widget is a widget that makes you awesome.</p>
<h2>Settings</h2>
<p><em><strong>Setting 1</strong></em>: This setting makes you awesome.</p>
<h2>Wiring</h2>
<p><em>No wiring is used</em></p>
<h2>Usage</h2>
<ol>
  <li>Drag the widget to the workspace</li>
  <li>Configure the widget</li>
  <li>Enjoy being awesome</li>
</ol>
<h2>Reference</h2>
<ul>
  <li><a href="https://mashup.lab.fiware.org/">FIWARE Mashup</a></li>
</ul>"""

# GET /resource/{vendor}/{name}/{version}/{file_path}
get_resource_file_summary = "Get a catalogue resource file"
get_resource_file_description = "Get a file of a catalogue resource version."
get_resource_file_response_description = "The file of a catalogue resource version"
get_resource_file_vendor_description = "The vendor of the catalogue resource"
get_resource_file_name_description = "The name of the catalogue resource"
get_resource_file_version_description = "The version of the catalogue resource"
get_resource_file_file_path_description = "The path of the file to retrieve within the catalogue resource"
get_resource_file_permission_denied_response_description = "The user does not have permission to access the resource"
get_resource_file_permission_denied_response_example_msg = "User example does not have permission to access the resource wirecloud/example/1.0.0"
get_resource_file_not_found_response_description = "The catalogue resource file was not found"
get_resource_file_not_acceptable_response_description = "Invalid request content type"
get_resource_file_validation_error_response_description = "The request data was invalid"
get_resource_file_response_example = "The contents of the file"
