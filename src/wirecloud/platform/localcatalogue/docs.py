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

# GET /
get_resource_collection_summary = "Get all available resources"
get_resource_collection_description = "Get all available resources in the local catalogue. If the user is not authenticated, only public resources will be returned."
get_resource_collection_process_urls_description = "Process URLs in the response"
get_resource_collection_response_description = "A dictionary containing the available resources. The keys are the local URI part of the resources and the values are the processed information of the resources"
get_resource_collection_not_acceptable_response_description = "Invalid request content type"
get_resource_entry_group_validation_error_response_description = "The request data (the query) was invalid"
get_resource_collection_response_example = {}
