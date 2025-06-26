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

# TODO Update descriptions (David JSON Schema PR)

# WiringConnectionEndpoint
wiring_connection_endpoint_type_description = "The type of the endpoint (widget or operator)"
wiring_connection_endpoint_id_description = "The identifier of component of the endpoint"
wiring_connection_endpoint_endpoint_description = "The endpoint name of the connection"

# WiringConnection
wiring_connection_readonly_description = "Whether the connection is read-only"
wiring_connection_source_description = "The source endpoint of the connection"
wiring_connection_target_description = "The target endpoint of the connection"

# WiringOperatorPreference
wiring_operator_preference_readonly_description = "Whether the operator preference is read-only"
wiring_operator_preference_hidden_description = "Whether the operator preference is hidden"
wiring_operator_preference_value_description = "The value of the operator preference"

# WiringOperator
wiring_operator_id_description = "The operator's identifier"
wiring_operator_name_description = "The operator's name"
wiring_operator_preference_description = "The operator's preferences"

# WiringComponentEndpoints
wiring_component_endpoints_source_description = "The source endpoints of the component"
wiring_component_endpoints_target_description = "The target endpoints of the component"

# WiringPosition
wiring_position_x_description = "The x coordinate of the position"
wiring_position_y_description = "The y coordinate of the position"

# WiringComponent
wiring_component_collapsed_description = "Whether the component is collapsed"
wiring_component_endpoints_description = "The endpoints of the component"
wiring_component_position_description = "The position of the component"

# WiringComponents
wiring_components_widget_description = "The widget components"
wiring_components_operator_description = "The operator components"

# WiringVisualDescriptionConnection
wiring_visual_description_connection_sourcename_description = "The source endpoint of the connection"
wiring_visual_description_connection_targetname_description = "The target endpoint of the connection"
wiring_visual_description_connection_sourcehandle_description = "The source handle position of the connection"
wiring_visual_description_connection_targethandle_description = "The target handle position of the connection"

# WiringBehaviour
wiring_behaviour_title_description = "The behaviour's title"
wiring_behaviour_description_description = "The behaviour's description"
wiring_behaviour_components_description = "The components of the behaviour"
wiring_behaviour_connections_description = "The connections of the behaviour"

# WiringVisualDescription
wiring_visual_description_behaviours_description = "The behaviours of the visual description"
wiring_visual_description_components_description = "The components of the visual description"
wiring_visual_description_connections_description = "The connections of the visual description"

# Wiring
wiring_version_description = "Wiring version"
wiring_connections_description = "The connections of the wiring"
wiring_operators_description = "The operators of the wiring"
wiring_visual_description_description = "The visual description of the wiring"

# WiringInout
wiring_inout_name_description = "The name of the input/output"
wiring_inout_type_description = "The type of the input/output (text, number, boolean, etc.)"
wiring_inout_label_description = "The label of the input/output"
wiring_inout_description_description = "The description of the input/output"
wiring_inout_friendcode_description = "The friendcode of the input/output (allows for the wiring editor to signal \
                                       which connections are compatible)"

# WiringInput
wiring_input_actionlabel_description = "The action label of the input"

# WiringEndpoints
wiring_endpoints_inputs_description = "The input descriptions of the input of a component in the wiring"
wiring_endpoints_outputs_description = "The output descriptions of the output of a component in the wiring"

# GET /{workspace_id}/wiring
update_wiring_entry_summary = "Update the wiring of a workspace"
update_wiring_entry_description = "Updates the wiring of a workspace."
update_wiring_entry_response_description = "Wiring updated successfully"
update_wiring_entry_auth_required_response_description = "Authentication required"
update_wiring_entry_not_found_response_description = "Workspace not found"
update_wiring_entry_permission_denied_response_description = "Permission denied"
update_wiring_entry_validation_error_response_description = "Validation error"
update_wiring_entry_workspace_id_description = "Workspace identifier"
update_wiring_entry_wiring_description = "Wiring entry data"
update_wiring_entry_wiring_example = {
    "version": "2.0",
    "connections": [
        {
            "readonly": False,
            "source": {
                "type": "operator",
                "id": "1",
                "endpoint": "out1"
            },
            "target": {
                "type": "operator",
                "id": "2",
                "endpoint": "in1"
            }
        }
    ],
    "operators": {
        "1": {
            "id": "1",
            "name": "admin/demo_operator/0.1.5",
            "preferences": {
                "color": {
                    "readonly": False,
                    "hidden": False,
                    "value": "blue"
                }
            },
            "properties": {
                "size": {
                    "readonly": False,
                    "hidden": False,
                    "value": "big"
                }
            }
        }
    },
    "visualdescription": {
        "behaviours": [],
        "components": {
            "widget": {},
            "operator": {}
        },
        "connections": []
    }
}

# PATCH /{workspace_id}/wiring
patch_wiring_entry_summary = "Patch the wiring of a workspace"
patch_wiring_entry_description = "Patches the wiring of a workspace."
patch_wiring_entry_response_description = "Wiring patched successfully"
patch_wiring_entry_auth_required_response_description = "Authentication required"
patch_wiring_entry_not_found_response_description = "Workspace or Operator not found"
patch_wiring_entry_permission_denied_response_description = "Permission denied"
patch_wiring_entry_validation_error_response_description = "Validation error"
patch_wiring_entry_workspace_id_description = "Workspace identifier"
patch_wiring_entry_wiring_description = "Wiring entry data"
patch_wiring_entry_wiring_example = [{
    "op": "replace",
    "path": "/operators/1/preferences/pref1/value",
    "value": "helloWorld"
}]

# GET /{vendor}/{name}/{version}/html
get_operator_summary = "Get the HTML of an operator"
get_operator_description = "Returns the HTML of an operator."
get_operator_response_description = "Operator HTML returned successfully"
get_operator_response_example = """<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
    <head>
        <base href="http://127.0.0.1:8000/showcase/media/admin/demo_operator/0.1.5/admin_demo_operator_0.1.5.wgt"/>
        <script type="text/javascript" src="http://127.0.0.1:8000/static/js/main-defaulttheme-operator.js?v=41a8ec3a29bcdc18198d0f126a7d4d8006a90126"></script>
        <script type="text/javascript" src="http://127.0.0.1:8000/static/js/WirecloudAPI/WirecloudAPIClosure.js?v=41a8ec3a29bcdc18198d0f126a7d4d8006a90126"></script>
        <script type="text/javascript" src="js/main.js"></script>
    </head>
    <body>
    </body>
</html>"""
get_operator_not_found_response_description = "Operator not found"
get_operator_vendor_description = "Vendor of the operator"
get_operator_name_description = "Name of the operator"
get_operator_version_description = "Version of the operator"
get_operator_mode_description = "Mode of the operator"

# GET /{workspace_id}/operators/{operator_id}/variables
get_operator_variables_entry_summary = "Get the variables of an operator"
get_operator_variables_entry_description = "Returns the variables of an operator."
get_operator_variables_entry_response_description = "Operator variables returned successfully"
get_operator_variables_entry_response_example = {
    "preferences": {
        "input": {
            "name": "input",
            "secure": False,
            "readonly": False,
            "hidden": False,
            "value": "blue"
        }
    },
    "properties": {
        "input": {
            "name": "input",
            "secure": False,
            "readonly": False,
            "hidden": False,
            "value": "blue"
        }
    }
}
get_operator_variables_entry_auth_required_response_description = "Authentication required"
get_operator_variables_entry_not_found_response_description = "Workspace or Operator not found"
get_operator_variables_entry_permission_denied_response_description = "Permission denied"
get_operator_variables_entry_workspace_id_description = "Workspace identifier"
get_operator_variables_entry_operator_id_description = "Operator identifier"
