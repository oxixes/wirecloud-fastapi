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

# POST /api/admin/switchuser
switch_user_summary = "Switch User"
switch_user_description = "Switches the currently logged in user to another user. Sends a new token in the form of a cookie to the client."
switch_user_no_content_response_description = "The user was successfully switched"
switch_user_unauthorized_response_description = "You are not logged in"
switch_user_forbidden_response_description = "You do not have permission to switch users"
switch_user_not_found_response_description = "Target user not found"

# POST /api/admin/users
create_user_collection_summary = "Create a new user"
create_user_collection_description = "Create a new user with the provided information."
create_user_collection_response_description = "User created"
create_user_collection_auth_required_response_description = "Authentication required"
create_user_collection_permission_denied_response_description = "Permission denied"
create_user_collection_not_acceptable_response_description = "Invalid request content type"
create_user_collection_conflict_response_description = "A user with the given username already exists"
create_user_collection_bad_request_response_description = "Missing or invalid data was provided"
create_user_collection_user_data_description = "User creation data"
create_user_collection_user_data_example = {
    "username": "john_doe",
    "email": "john@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "is_staff": False,
    "is_active": True,
    "is_superuser": False,
    "password": "strong_password_123"
}

# GET /api/admin/users/{user_username}
get_user_entry_summary = "Get user details"
get_user_entry_description = "Retrieve the details of a user by their username."
get_user_entry_response_description = "User details retrieved"
get_user_entry_auth_required_response_description = "Authentication required"
get_user_entry_permission_denied_response_description = "Permission denied"
get_user_entry_not_found_response_description = "User not found"
get_user_entry_user_username_description = "The username of the user to retrieve"
get_user_entry_response_example = {
    "username": "john_doe",
    "email": "john@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "is_staff": False,
    "is_active": True,
    "is_superuser": False,
    "permissions": ["WORKSPACE.CREATE", "COMPONENT.INSTALL"]
}

# PUT /api/admin/users/{user_username}
update_user_entry_summary = "Update user details"
update_user_entry_description = "Update the details of a user by their username."
update_user_entry_response_description = "User details updated"
update_user_entry_auth_required_response_description = "Authentication required"
update_user_entry_permission_denied_response_description = "Permission denied"
update_user_entry_not_found_response_description = "User not found"
update_user_entry_not_acceptable_response_description = "Invalid request content type"
update_user_entry_conflict_response_description = "A user with the given username already exists"
update_user_entry_bad_request_response_description = "Missing or invalid data was provided"
update_user_entry_user_username_description = "The username of the user to update"
update_user_entry_user_data_description = "User update data"
update_user_entry_user_data_example = {
    "username": "john_doe",
    "email": "john@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "is_staff": False,
    "is_active": True,
    "is_superuser": False,
    "permissions": ["WORKSPACE.CREATE", "COMPONENT.INSTALL"]
}

# DELETE /api/admin/users/{user_username}
delete_user_entry_summary = "Delete a user"
delete_user_entry_description = "Delete a user by their username."
delete_user_entry_response_description = "User deleted"
delete_user_entry_auth_required_response_description = "Authentication required"
delete_user_entry_permission_denied_response_description = "Permission denied"
delete_user_entry_not_found_response_description = "User not found"
delete_user_entry_user_username_description = "The username of the user to delete"

# POST /api/admin/groups
create_group_collection_summary = "Create a new group"
create_group_collection_description = "Create a new group with the provided information."
create_group_collection_response_description = "Group created"
create_group_collection_auth_required_response_description = "Authentication required"
create_group_collection_permission_denied_response_description = "Permission denied"
create_group_collection_not_acceptable_response_description = "Invalid request content type"
create_group_collection_conflict_response_description = "A group with the given name already exists"
create_group_collection_bad_request_response_description = "Missing or invalid data was provided"
create_group_collection_group_data_description = "Group creation data"
create_group_collection_group_data_example = {
    "name": "Editors",
    "codename": "editors",
    "users": ["507f1f77bcf86cd799439012", "507f1f77bcf86cd799439013"]
}

# GET /api/admin/groups/{group_name}
get_group_entry_summary = "Get group details"
get_group_entry_description = "Retrieve the details of a group by its name."
get_group_entry_response_description = "Group details retrieved"
get_group_entry_auth_required_response_description = "Authentication required"
get_group_entry_permission_denied_response_description = "Permission denied"
get_group_entry_not_found_response_description = "Group not found"
get_group_entry_group_name_description = "The name of the group to retrieve"
get_group_entry_response_example = {
    "name": "Editors",
    "codename": "editors",
    "permissions": ["WORKSPACE.CREATE", "COMPONENT.INSTALL"],
    "users": ["507f1f77bcf86cd799439012", "507f1f77bcf86cd799439013"]
}

# PUT /api/admin/groups/{group_name}
update_group_entry_summary = "Update group details"
update_group_entry_description = "Update the details of a group by its name."
update_group_entry_response_description = "Group details updated"
update_group_entry_auth_required_response_description = "Authentication required"
update_group_entry_permission_denied_response_description = "Permission denied"
update_group_entry_not_found_response_description = "Group not found"
update_group_entry_not_acceptable_response_description = "Invalid request content type"
update_group_entry_conflict_response_description = "A group with the given name already exists"
update_group_entry_bad_request_response_description = "Missing or invalid data was provided"
update_group_entry_group_name_description = "The name of the group to update"
update_group_entry_group_data_description = "Group update data"
update_group_entry_group_data_example = {
    "name": "Editors",
    "codename": "editors",
    "permissions": ["WORKSPACE.CREATE", "COMPONENT.INSTALL"],
    "users": ["507f1f77bcf86cd799439012", "507f1f77bcf86cd799439013"]
}

# DELETE /api/admin/groups/{group_name}
delete_group_entry_summary = "Delete a group"
delete_group_entry_description = "Delete a group by its name."
delete_group_entry_response_description = "Group deleted"
delete_group_entry_auth_required_response_description = "Authentication required"
delete_group_entry_permission_denied_response_description = "Permission denied"
delete_group_entry_not_found_response_description = "Group not found"
delete_group_entry_group_name_description = "The name of the group to delete"

# POST /api/admin/organizations
create_organization_collection_summary = "Create a new organization"
create_organization_collection_description = "Create a new organization with the provided information."
create_organization_collection_response_description = "Organization created"
create_organization_collection_auth_required_response_description = "Authentication required"
create_organization_collection_permission_denied_response_description = "Permission denied"
create_organization_collection_not_acceptable_response_description = "Invalid request content type"
create_organization_collection_conflict_response_description = "A group with the given name already exists"
create_organization_collection_bad_request_response_description = "Missing or invalid data was provided"
create_organization_collection_organization_data_description = "Organization creation data"
create_organization_collection_organization_data_example = {
    "name": "Best Company",
    "codename": "best_company",
    "users": ["507f1f77bcf86cd799439012", "507f1f77bcf86cd799439013"]
}

# GET /api/admin/organizations/{organization_name}
get_organization_entry_summary = "Get organization details"
get_organization_entry_description = "Retrieve the details of an organization by its name."
get_organization_entry_response_description = "Organization details retrieved"
get_organization_entry_auth_required_response_description = "Authentication required"
get_organization_entry_permission_denied_response_description = "Permission denied"
get_organization_entry_not_found_response_description = "Organization not found"
get_organization_entry_organization_name_description = "The name of the organization to retrieve"
get_organization_entry_response_example = [
    {
         "name": "Best Company",
         "codename": "best_company",
         "users": ["507f1f77bcf86cd799439012", "507f1f77bcf86cd799439013"],
         "path": ["507f1f77bcf86cd799439014"]
    },
    {
        "name": "Best Company",
        "codename": "best_company",
        "users": ["507f1f77bcf86cd799439012", "507f1f77bcf86cd799439013"],
        "path": ["507f1f77bcf86cd799439014", "507f1f77bcf86cd799439015"]
    }
]

# DELETE /api/admin/organizations/{organization_name}
delete_organization_entry_summary = "Delete an organization"
delete_organization_entry_description = "Delete an organization by its name."
delete_organization_entry_response_description = "Organization deleted"
delete_organization_entry_auth_required_response_description = "Authentication required"
delete_organization_entry_permission_denied_response_description = "Permission denied"
delete_organization_entry_not_found_response_description = "Organization not found"
delete_organization_entry_organization_name_description = "The name of the organization to delete"

# PUT /api/admin/organizations/groups/{group_name}
update_organization_group_entry_summary = "Update organization group details"
update_organization_group_entry_description = "Update the parent of a group by its name."
update_organization_group_entry_response_description = "Organization group parent updated"
update_organization_group_entry_auth_required_response_description = "Authentication required"
update_organization_group_entry_permission_denied_response_description = "Permission denied"
update_organization_group_entry_not_found_response_description = "Group not found"
update_organization_group_entry_not_acceptable_response_description = "Invalid request content type"
update_organization_group_entry_bad_request_response_description = "Missing or invalid data was provided"
update_organization_group_entry_group_name_description = "The name of the group to update"
update_organization_group_entry_new_parent_description = "Organization group update data"
update_organization_group_entry_new_parent_example = {
    "parent_name": "Editors"
}