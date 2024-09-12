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

# MarketOptions
market_options_name_description = "Name of the market"
market_options_type_description = "Type of the market"
market_options_title_description = "Title of the market"
market_options_url_description = "URL of the market"
market_options_public_description = "Whether the market is public (available to all users) or not"
market_options_user_description = "User who owns the market"

# MarketPermissions
market_permissions_delete_description = "Whether the user can delete the market"

# MarketData
market_permissions_description = "Permissions of the user over the market"

# MarketEndpoint
market_endpoint_market_description = "Market identifier"
market_endpoint_store_description = "Store identifier"

# PublishData
publish_data_marketplaces_description = "Marketplaces where the resource will be published"
publish_data_resource_description = "Resource to publish"

# GET /markets/
get_market_collection_summary = "Get the list of available markets"
get_market_collection_description = "Get the list of available markets for the current user."
get_market_collection_response_description = "List of available markets"
get_market_collection_auth_required_response_description = "Authentication required"
get_market_collection_not_acceptable_response_description = "Invalid request content type"
get_market_collection_response_example = [
    {
        "name": "market1",
        "type": "wirecloud",
        "title": "Market 1",
        "url": "https://macs1.example.com",
        "public": True,
        "user": "user1",
        "permissions": {
            "delete": True
        }
    },
    {
        "name": "market2",
        "type": "wirecloud",
        "title": "Market 2",
        "url": "https://macs2.example.com",
        "public": False,
        "user": "user2",
        "permissions": {
            "delete": False
        }
    }
]

# POST /markets/
create_market_collection_summary = "Create a new market"
create_market_collection_description = "Creates a new market."
create_market_collection_market_description = "Market creation data"
create_market_collection_response_description = "Market created"
create_market_collection_auth_required_response_description = "Authentication required"
create_market_collection_permission_denied_response_description = "Permission denied"
create_market_collection_not_acceptable_response_description = "Invalid request content type"
create_market_collection_conflict_response_description = "Market already exists"
create_market_collection_unsupported_media_type_response_description = "Unsupported media type provided"
create_market_collection_validation_error_response_description = "Validation error"
create_market_collection_market_example = {
    "name": "market1",
    "type": "wirecloud",
    "title": "Market 1",
    "url": "https://macs1.example.com",
    "public": True,
    "user": "user1"
}

# DELETE /market/{user}/{market}
delete_market_entry_summary = "Delete a market"
delete_market_entry_description = "Deletes a market for a given user."
delete_market_entry_response_description = "Market deleted"
delete_market_entry_auth_required_response_description = "Authentication required"
delete_market_entry_permission_denied_response_description = "Permission denied"
delete_market_entry_not_found_response_description = "Market not found"
delete_market_entry_user_description = "User who owns the market"
delete_market_entry_market_description = "Name of the market to delete"
delete_market_entry_validation_error_response_description = "Validation error"

# POST /markets/publish
publish_service_process_summary = "Publish on a market"
publish_service_process_description = "Publish a resource on a market."
publish_service_process_response_description = "Resource published"
publish_service_process_auth_required_response_description = "Authentication required"
publish_service_process_permission_denied_response_description = "Permission denied"
publish_service_process_not_found_response_description = "Resource not found"
publish_service_process_not_acceptable_response_description = "Invalid request content type"
publish_service_process_validation_error_response_description = "Invalid request data"
publish_service_process_error_response_description = "Error publishing the resource"
publish_service_process_data_description = "Resource and marketplaces to publish"
publish_service_process_data_example = {
    "resource": "wirecloud/example/1.0.0",
    "marketplaces": [
        {
            "market": "user/market1",
            "store": "store1"
        },
        {
            "market": "user/market2"
        }
    ]
}