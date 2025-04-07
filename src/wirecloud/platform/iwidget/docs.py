#  -*- coding: utf-8 -*-
#
#  Copyright (c) 2024 Future Internet Consulting and Development Solutions S.L.
#
#  This file is part of Wirecloud.
#
#  Wirecloud is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Affero General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  Wirecloud is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Affero General Public License for more details.
#
#  You should have received a copy of the GNU Affero General Public License
#  along with Wirecloud.  If not, see <http://www.gnu.org/licenses/>.

iwidget_data = [
    {
        "id": "67af66aa3ac952bc88cc1a63-0-0",
        "title": "string",
        "layout": 0,
        "widget": "vendor/name/version",
        "layout_config": [
            {
                "id": 0,
                "top": 0,
                "left": 0,
                "zIndex": 0,
                "height": 1,
                "width": 1,
                "minimized": False,
                "titlevisible": True,
                "fulldragboard": False,
                "relx": True,
                "rely": True,
                "relwidth": True,
                "relheight": True,
                "anchor": "top-left",
                "moreOrEqual": 0,
                "lessOrEqual": -1
            }
        ],
        "icon_left": 0,
        "icon_top": 0,
        "read_only": False,
        "permissions": {
            "editor": {
                "close": None,
                "configure": None,
                "move": None,
                "rename": None,
                "resize": None,
                "minimize": None,
                "upgrade": None
            },
            "viewer": {
                "close": None,
                "configure": None,
                "move": None,
                "rename": None,
                "resize": None,
                "minimize": None,
                "upgrade": None
            }
        },
        "variable_values": None,
        "preferences": {
            "input_label_pref": {
                "name": "input_label_pref",
                "secure": False,
                "readonly": False,
                "hidden": False,
                "value": "Keywords"
            },
            "input_placeholder_pref": {
                "name": "input_placeholder_pref",
                "secure": False,
                "readonly": False,
                "hidden": False,
                "value": "Text to send..."
            },
            "button_label_pref": {
                "name": "button_label_pref",
                "secure": False,
                "readonly": False,
                "hidden": False,
                "value": "Send"
            }
        },
        "properties": {}
    },
    {
        "id": "67af66aa3ac952bc88cc1a63-0-1",
        "title": "string",
        "layout": 0,
        "widget": "vendor/name/version",
        "layout_config": [
            {
                "id": 0,
                "top": 0,
                "left": 0,
                "zIndex": 0,
                "height": 1,
                "width": 1,
                "minimized": False,
                "titlevisible": True,
                "fulldragboard": False,
                "relx": True,
                "rely": True,
                "relwidth": True,
                "relheight": True,
                "anchor": "top-left",
                "moreOrEqual": 0,
                "lessOrEqual": -1
            }
        ],
        "icon_left": 0,
        "icon_top": 0,
        "read_only": False,
        "permissions": {
            "editor": {
                "close": None,
                "configure": None,
                "move": None,
                "rename": None,
                "resize": None,
                "minimize": None,
                "upgrade": None
            },
            "viewer": {
                "close": None,
                "configure": None,
                "move": None,
                "rename": None,
                "resize": None,
                "minimize": None,
                "upgrade": None
            }
        },
        "variable_values": None,
        "preferences": {
            "input_label_pref": {
                "name": "input_label_pref",
                "secure": False,
                "readonly": False,
                "hidden": False,
                "value": "Keywords"
            },
            "input_placeholder_pref": {
                "name": "input_placeholder_pref",
                "secure": False,
                "readonly": False,
                "hidden": False,
                "value": "Text to send..."
            },
            "button_label_pref": {
                "name": "button_label_pref",
                "secure": False,
                "readonly": False,
                "hidden": False,
                "value": "Send"
            }
        },
        "properties": {}
    }
]
# GET /workspace/{workspace_id}/tab/{tab_position}/iwidgets/
get_iwidget_collection_summary = "Get all iwidgets in a tab"
get_iwidget_collection_description = "Gets all iwidgets in a tab"
get_iwidget_collection_response_description = "List of iwidgets"
get_iwidget_collection_auth_required_response_description = "Authentication required"
get_iwidget_collection_permission_denied_response_description = "Permission denied"
get_iwidget_collection_not_found_response_description = "Workspace or Tab not found"
get_iwidget_collection_workspace_id_description = "Workspace identifier"
get_iwidget_collection_tab_position_description = "Tab position"
get_iwidget_collection_response_example = iwidget_data

# POST /workspace/{workspace_id}/tab/{tab_position}/iwidgets/
create_iwidget_collection_summary = "Create a new iwidget"
create_iwidget_collection_description = "Creates a new iwidget"
create_iwidget_collection_response_description = "IWidget created"
create_iwidget_collection_auth_required_response_description = "Authentication required"
create_iwidget_collection_permission_denied_response_description = "Permission denied"
create_iwidget_collection_not_found_response_description = "Workspace or Tab not found"
create_iwidget_collection_validation_error_response_description = "Validation error"
create_iwidget_collection_not_acceptable_response_description = "Invalid request content type"
create_iwidget_collection_workspace_id_description = "Workspace identifier"
create_iwidget_collection_tab_position_description = "Tab position"
create_iwidget_collection_iwidget_description = "IWidget data"
create_iwidget_collection_iwidget_example = {
    "title": "IWidget",
    "layout": 0,
    "widget": "vendor/name/version",
    "layout_config": [
        {
            "action": "update",
            "id": 0,
            "top": 0,
            "left": 0,
            "zIndex": 0,
            "height": 1,
            "width": 1,
            "minimized": False,
            "titlevisible": True,
            "fulldragboard": False,
            "relx": True,
            "rely": False,
            "relwidth": True,
            "relheight": False,
            "anchor": "top-left",
            "moreOrEqual": 0,
            "lessOrEqual": -1
        }
    ],
    "icon_left": 0,
    "icon_top": 0,
    "read_only": False,
    "permissions": {},
    "variable_values": {}
}
create_iwidget_collection_response_example = iwidget_data

# POST /workspace/{workspace_id}/tab/{tab_position}/iwidgets/
update_iwidget_collection_summary = "Update a iwidget or iwidgets"
update_iwidget_collection_description = "Updates a iwidget or iwidgets"
update_iwidget_collection_response_description = "IWidget(s) updated"
update_iwidget_collection_auth_required_response_description = "Authentication required"
update_iwidget_collection_permission_denied_response_description = "Permission denied"
update_iwidget_collection_not_found_response_description = "Workspace or Tab not found"
update_iwidget_collection_validation_error_response_description = "Validation error"
update_iwidget_collection_bad_request_response_description = "Missing or invalid data was provided"
update_iwidget_collection_workspace_id_description = "Workspace identifier"
update_iwidget_collection_tab_position_description = "Tab position"
update_iwidget_collection_iwidget_description = "IWidget data"
update_iwidget_collection_iwidget_example = [{
    "id": 0,
    "tab": 0,
    "layout": 0,
    "layout_config": [
        {
            "action": "update",
            "id": 0,
            "top": 0,
            "left": 0,
            "zIndex": 0,
            "height": 1,
            "width": 1,
            "minimized": False,
            "titlevisible": True,
            "fulldragboard": False,
            "relx": True,
            "rely": False,
            "relwidth": True,
            "relheight": False,
            "anchor": "top-left",
            "moreOrEqual": 0,
            "lessOrEqual": -1
        }
    ],
    "title": "new-name-for-iwidget",
    "widget": "vendor/name/version",
    "move": False
}]

# GET /workspace/{workspace_id}/tab/{tab_position}/iwidgets/{iwidget_position}
get_iwidget_entry_summary = "Get a iwidget"
get_iwidget_entry_description = "Gets a iwidget"
get_iwidget_entry_response_description = "IWidget information"
get_iwidget_entry_auth_required_response_description = "Authentication required"
get_iwidget_entry_not_found_response_description = "Workspace, Tab or IWidget not found"
get_iwidget_entry_workspace_id_description = "Workspace identifier"
get_iwidget_entry_tab_position_description = "Tab position"
get_iwidget_entry_iwidget_position_description = "IWidget position"
get_iwidget_entry_response_example = iwidget_data

# POST /workspace/{workspace_id}/tab/{tab_position}/iwidgets/{iwidget_position}
update_iwidget_entry_summary = "Update a iwidget"
update_iwidget_entry_description = "Updates a iwidget"
update_iwidget_entry_response_description = "IWidget updated"
update_iwidget_entry_auth_required_response_description = "Authentication required"
update_iwidget_entry_permission_denied_response_description = "Permission denied"
update_iwidget_entry_not_found_response_description = "Workspace, Tab or IWidget not found"
update_iwidget_entry_validation_error_response_description = "Validation error"
update_iwidget_entry_bad_request_response_description = "Missing or invalid data was provided"
update_iwidget_entry_workspace_id_description = "Workspace identifier"
update_iwidget_entry_tab_position_description = "Tab position"
update_iwidget_entry_iwidget_position_description = "IWidget position"
update_iwidget_entry_iwidget_description = "IWidget data"
update_iwidget_entry_iwidget_example = {
    "tab": 0,
    "layout": 0,
    "layout_config": [
        {
            "action": "update",
            "id": 0,
            "top": 0,
            "left": 0,
            "zIndex": 0,
            "height": 1,
            "width": 1,
            "minimized": False,
            "titlevisible": True,
            "fulldragboard": False,
            "relx": True,
            "rely": False,
            "relwidth": True,
            "relheight": False,
            "anchor": "top-left",
            "moreOrEqual": 0,
            "lessOrEqual": -1
        }
    ],
    "title": "new-name-for-iwidget",
    "widget": "vendor/name/version",
    "move": False
}

# DELETE /workspace/{workspace_id}/tab/{tab_position}/iwidgets/{iwidget_position}
delete_iwidget_entry_summary = "Delete a iwidget"
delete_iwidget_entry_description = "Deletes a iwidget"
delete_iwidget_entry_response_description = "IWidget deleted"
delete_iwidget_entry_auth_required_response_description = "Authentication required"
delete_iwidget_entry_permission_denied_response_description = "Permission denied"
delete_iwidget_entry_not_found_response_description = "Workspace, Tab or IWidget not found"
delete_iwidget_entry_workspace_id_description = "Workspace identifier"
delete_iwidget_entry_tab_position_description = "Tab position"
delete_iwidget_entry_iwidget_position_description = "IWidget position"

# POST /workspace/{workspace_id}/tab/{tab_position}/iwidgets/{iwidget_position}/preferences
update_iwidget_preferences_summary = "Update a iwidget preference"
update_iwidget_preferences_description = "Updates iwidget preferences"
update_iwidget_preferences_response_description = "IWidget preferences updated"
update_iwidget_preferences_auth_required_response_description = "Authentication required"
update_iwidget_preferences_permission_denied_response_description = "Permission denied"
update_iwidget_preferences_not_found_response_description = "Workspace, Tab, IWidget or Resource not found"
update_iwidget_preferences_validation_error_response_description = "Validation error"
update_iwidget_preferences_bad_request_response_description = "Missing or invalid data was provided"
update_iwidget_preferences_workspace_id_description = "Workspace identifier"
update_iwidget_preferences_tab_position_description = "Tab position"
update_iwidget_preferences_iwidget_position_description = "IWidget position"
update_iwidget_preferences_new_values_description = "New values for iwidget preferences"
update_iwidget_preferences_new_values_example = {
    "pref1": 2,
    "pref2": "string",
}

# GET /workspace/{workspace_id}/tab/{tab_position}/iwidgets/{iwidget_position}/preferences
get_iwidget_preferences_summary = "Get iwidget preferences"
get_iwidget_preferences_description = "Gets iwidget preferences"
get_iwidget_preferences_response_description = "IWidget preferences"
get_iwidget_preferences_auth_required_response_description = "Authentication required"
get_iwidget_preferences_permission_denied_response_description = "Permission denied"
get_iwidget_preferences_not_found_response_description = "Workspace, Tab, IWidget or Resource not found"
get_iwidget_preferences_workspace_id_description = "Workspace identifier"
get_iwidget_preferences_tab_position_description = "Tab position"
get_iwidget_preferences_iwidget_position_description = "IWidget position"
get_iwidget_preferences_response_example = {
    "pref1": 2,
    "pref2": "string",
}

# POST /workspace/{workspace_id}/tab/{tab_position}/iwidgets/{iwidget_position}/properties
update_iwidget_properties_summary = "Get iwidget properties"
update_iwidget_properties_description = "Gets iwidget properties"
update_iwidget_properties_response_description = "IWidget properties"
update_iwidget_properties_auth_required_response_description = "Authentication required"
update_iwidget_properties_permission_denied_response_description = "Permission denied"
update_iwidget_properties_not_found_response_description = "Workspace, Tab, IWidget or Resource not found"
update_iwidget_properties_validation_error_response_description = "Validation error"
update_iwidget_properties_bad_request_response_description = "Missing or invalid data was provided"
update_iwidget_properties_workspace_id_description = "Workspace identifier"
update_iwidget_properties_tab_position_description = "Tab position"
update_iwidget_properties_iwidget_position_description = "IWidget position"
update_iwidget_properties_new_values_description = "New values for iwidget properties"
update_iwidget_properties_new_values_example = {
    "name-pref": "new-value-for-pref"
}

# GET /workspace/{workspace_id}/tab/{tab_position}/iwidgets/{iwidget_position}/properties
get_iwidget_properties_summary = "Get iwidget properties"
get_iwidget_properties_description = "Gets iwidget properties"
get_iwidget_properties_response_description = "IWidget properties"
get_iwidget_properties_auth_required_response_description = "Authentication required"
get_iwidget_properties_permission_denied_response_description = "Permission denied"
get_iwidget_properties_not_found_response_description = "Workspace, Tab, IWidget or Resource not found"
get_iwidget_properties_workspace_id_description = "Workspace identifier"
get_iwidget_properties_tab_position_description = "Tab position"
get_iwidget_properties_iwidget_position_description = "IWidget position"
get_iwidget_properties_response_example = {
    "name-prop": "new-value-for-prop"
}
