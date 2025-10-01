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

# POST /oidc/k_logout
keycloak_backchannel_logout_summary = "Keycloak Backchannel Logout"
keycloak_backchannel_logout_description = "Handles Keycloak backchannel logout requests by validating the logout token and invalidating the user's session and tokens."
keycloak_backchannel_logout_logout_token_description = "The logout token received from Keycloak."
keycloak_backchannel_logout_no_content_response_description = "Logout successful."
keycloak_backchannel_logout_bad_request_response_description = "Bad request due to invalid token or missing parameters."
keycloak_backchannel_logout_unsupported_media_type_response_description = "Unsupported Media Type. The request must have a Content-Type of application/x-www-form-urlencoded."
keycloak_backchannel_logout_validation_error_response_description = "Validation error due to invalid input."