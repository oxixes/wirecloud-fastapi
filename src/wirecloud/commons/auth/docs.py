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

# Permission
permission_codename_description = "The permission's codename"

# Group
group_id_description = "The group's id"
group_name_description = "The group's name"

# User
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

# UserLogin
user_login_password_description = "The user's password"

# UserToken
user_token_token_description = "The user's token"
user_token_token_type_description = "The type of token"

# GET /oidc/callback/
oidc_login_summary = "OIDC login callback"
oidc_login_description = "Handles the OIDC login callback, validates the authorization code, and sets the session cookie."
oidc_login_response_description = "Response to the OIDC login request, which sets the session cookie and redirects to the home page or the specified redirect URL in the `state` parameter."
oidc_login_code_description = "The OIDC authorization code received from the OIDC provider"
oidc_login_validation_error_response_description = "Validation error in the OIDC login request, such as missing or invalid parameters"

# POST /api/auth/login/
api_login_summary = "API Login"
api_login_description = "Logs in a user via the API using their username and password. Returns a JWT token for authenticated requests."
api_login_response_model_description = "The user's JWT"
api_login_response_model_example = {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOjEsImlzcyI6IldpcmVjbG91ZCIsImV4cCI6MTcyMTYzMTk1NywiaWF0IjoxNzIwNDIyMzU3fQ.SIGNATURE",
    "token_type": "bearer"
}
api_login_unauthorized_response_description = "Invalid username or password"
api_login_not_acceptable_response_description = "Invalid request content type"
api_login_unsupported_media_type_response_description = "Unsupported request media type"
api_login_validation_error_response_descrition = "Validation error"

# GET /login
login_page_summary = "Login Page"
login_page_description = "Renders the login page for the user to enter their credentials."
login_page_response_description = "HTML content of the login page, which includes a form for the user to enter their username and password."

# POST /login
login_summary = "Login"
login_description = "Logs in a user by validating their credentials and setting the session cookie. If the user is authenticated, they are redirected to the home page or a specified URL in the `state` or `next` parameter."
login_response_description = "Response to the login request, which sets the session cookie and redirects to the home page or the specified URL in the `state` or `next` parameter."
login_unauthorized_response_description = "HTML content of the login page with an error message if the provided credentials are invalid."
login_not_acceptable_response_description = "Invalid request content type."
login_unsupported_media_type_response_description = "Unsupported request media type."
login_validation_error_response_description = "Validation error in the login request, such as missing or invalid parameters."

# GET /logout
logout_summary = "Logout"
logout_description = "Logs out the user by clearing the session and redirecting to the home page or a specified URL in the `state` or `next` parameter. Performs a back channel logout in the OIDC provider if configured."
logout_response_description = "Response to the logout request, which clears the session and redirects to the home page or the specified URL in the `state` or `next` parameter."

# GET /api/auth/refresh/
token_refresh_summary = "API Token Refresh"
token_refresh_description = "Refreshes the user's API token. This endpoint is used to obtain a new JWT token when the current one is about to expire. It also updates the session cookie with the new token."
token_refresh_response_model_description = "The user's new JWT"
token_refresh_response_model_example = {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOjEsImlzcyI6IldpcmVjbG91ZCIsImV4cCI6MTcyMTYzMTk1NywiaWF0IjoxNzIwNDIyMzU3fQ.SIGNATURE",
    "token_type": "bearer"
}
token_refresh_unauthorized_response_description = "Invalid or expired token"