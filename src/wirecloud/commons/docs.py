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

# GET /api/i18n/js_catalogue
get_js_catalogue_summary = "Get the javascript translation catalogue"
get_js_catalogue_description = "Get the javascript translation catalogue script, which contains the translations for "\
                               "the specified language as well as translation utilities."
get_js_catalogue_response_description = "Javascript translation catalogue"
get_js_catalogue_validation_error_response_description = "Invalid parameters"

# GET /api/search
get_search_resources_summary = "Search resources"
get_search_resources_description = "Search resources in a given namespace."
get_search_resources_response_description = "Search results"
get_search_resources_validation_error_response_description = "The request data was invalid"
get_search_resources_auth_required_response_description = "Authentication required"
get_search_resources_namespace_description = "The namespace to search into."
get_search_resources_q_description = "The search query string."
get_search_resources_pagenum_description = "The page number to retrieve."
get_search_resources_maxresults_description = "The maximum number of results per page."
get_search_resources_orderby_description = "Comma-separated list of fields to order the results by. Prefix a field with '-' to order in descending order."
get_search_resources_response_example = {
    "offset": 0,
    "pagecount": 1,
    "pagelen": 1,
    "pagenum": 1,
    "results": [
        {
            "name": "landing",
            "title": "Workspace 1",
            "description": "",
            "longdescription": "",
            "public": True,
            "requireauth": False,
            "last_modified": "2025-07-30T10:45:08.845000",
            "owner": "wirecloud",
            "shared": True
        }
    ],
    "total": 1
}

# POST /api/search/rebuild/{namespace}
rebuild_index_resources_summary = "Rebuild search index"
rebuild_index_resources_description = "Rebuild the search index for a given namespace."
rebuild_index_resources_response_description = "Rebuild started"
rebuild_index_resources_validation_error_response_description = "The request data was invalid"
rebuild_index_resources_auth_required_response_description = "Authentication required"
rebuild_index_resources_permission_denied_response_description = "Permission denied"
rebuild_index_resources_namespace_description = "The namespace to rebuild the index for."