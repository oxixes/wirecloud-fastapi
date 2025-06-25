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

# TODO Add translations in pydantic error on version 1.0

from pydantic import BaseModel, Field, StringConstraints, model_validator, field_serializer
from typing import Any, Optional, Union, Annotated
from enum import Enum

from src.wirecloud.platform.wiring import docs

IntegerStr = Annotated[str, StringConstraints(pattern=r'^\d+$')]
ResourceName = Annotated[str, StringConstraints(
    pattern=r'^[^\/]+\/[^\/]+\/((?:[1-9]\d*\.|0\.)*(?:[1-9]\d*|0))((a|b|rc)([1-9]\d*))?(-dev(.+)?)?$')]


class WiringType(Enum):
    operator = 'operator'
    widget = 'widget'


class WiringConnectionEndpoint(BaseModel):
    type: WiringType = Field(description=docs.wiring_connection_endpoint_type_description)
    id: IntegerStr = Field(description=docs.wiring_connection_endpoint_id_description)
    endpoint: str = Field(description=docs.wiring_connection_endpoint_endpoint_description)

    # Serialize WiringType as a string
    @field_serializer("type")
    def serialize_wiring_type(self, v):
        return v.value


class WiringConnection(BaseModel):
    readonly: bool = Field(description=docs.wiring_connection_readonly_description, default=False)
    source: WiringConnectionEndpoint = Field(description=docs.wiring_connection_source_description)
    target: WiringConnectionEndpoint = Field(description=docs.wiring_connection_target_description)


class WiringOperatorPreferenceValue(BaseModel):
    users: dict[str, Any] = {}


class WiringOperatorPreference(BaseModel):
    readonly: bool = Field(description=docs.wiring_operator_preference_readonly_description)
    hidden: bool = Field(description=docs.wiring_operator_preference_hidden_description)
    value: Any = Field(description=docs.wiring_operator_preference_value_description)


class WiringOperator(BaseModel):
    id: Optional[IntegerStr] = Field(description=docs.wiring_operator_id_description),
    name: ResourceName = Field(description=docs.wiring_operator_name_description)
    preferences: dict[str, WiringOperatorPreference] = Field(description=docs.wiring_operator_preference_description)


class WiringComponentEndpoints(BaseModel):
    source: list[str] = Field(description=docs.wiring_component_endpoints_source_description, default=[])
    target: list[str] = Field(description=docs.wiring_component_endpoints_target_description, default=[])


class WiringPosition(BaseModel):
    x: int = Field(description=docs.wiring_position_x_description)
    y: int = Field(description=docs.wiring_position_y_description)


class WiringComponent(BaseModel):
    collapsed: bool = Field(description=docs.wiring_component_collapsed_description,
                            default=False)
    endpoints: Optional[WiringComponentEndpoints] = Field(description=docs.wiring_component_endpoints_description,
                                                          default=None)
    position: Optional[WiringPosition] = Field(description=docs.wiring_component_position_description,
                                               default=None)


class WiringComponents(BaseModel):
    widget: dict[IntegerStr, WiringComponent] = Field(description=docs.wiring_components_widget_description,
                                                      default={})
    operator: dict[IntegerStr, WiringComponent] = Field(description=docs.wiring_components_operator_description,
                                                        default={})


class WiringConnectionHandlePositionType(Enum):
    auto = 'auto'


class WiringVisualDescriptionConnection(BaseModel):
    sourcename: str = Field(description=docs.wiring_visual_description_connection_sourcename_description)
    targetname: str = Field(description=docs.wiring_visual_description_connection_targetname_description)
    sourcehandle: Union[WiringConnectionHandlePositionType, WiringPosition] = (
        Field(description=docs.wiring_visual_description_connection_sourcehandle_description,
              default=WiringConnectionHandlePositionType.auto))
    targethandle: Union[WiringConnectionHandlePositionType, WiringPosition] = (
        Field(description=docs.wiring_visual_description_connection_targethandle_description,
              default=WiringConnectionHandlePositionType.auto))

    # Serialize WiringConnectionHandlePositionType as a string
    @field_serializer("sourcehandle", "targethandle")
    def serialize_handle_position_type(self, v):
        if isinstance(v, WiringConnectionHandlePositionType):
            return v.value
        return v


class WiringBehaviour(BaseModel):
    title: str = Field(description=docs.wiring_behaviour_title_description)
    description: str = Field(description=docs.wiring_behaviour_description_description)
    components: WiringComponents = Field(description=docs.wiring_behaviour_components_description)
    connections: list[WiringVisualDescriptionConnection] = Field(
        description=docs.wiring_behaviour_connections_description)


class WiringVisualDescription(BaseModel):
    behaviours: list[WiringBehaviour] = Field(description=docs.wiring_visual_description_behaviours_description,
                                              default=[])
    components: WiringComponents = Field(description=docs.wiring_visual_description_components_description,
                                         default=WiringComponents())
    connections: list[WiringVisualDescriptionConnection] = Field(
        description=docs.wiring_visual_description_connections_description,
        default=[])


class Wiring(BaseModel):
    version: str = Field(pattern=r'^\d+\.\d+$', description=docs.wiring_version_description, default='2.0')
    connections: list[WiringConnection] = Field(description=docs.wiring_connections_description, default=[])
    operators: dict[IntegerStr, WiringOperator] = Field(description=docs.wiring_operators_description, default={})
    visualdescription: WiringVisualDescription = Field(description=docs.wiring_visual_description_description,
                                                       default=WiringVisualDescription())

    @model_validator(mode='before')
    @classmethod
    def check_version(cls, data: Any):
        if isinstance(data, dict) and 'version' in data:
            assert data['version'] == '2.0', 'Only wiring version 2.0 is supported. The old 1.0 version is no longer supported.'

        return data

    # The key id of the operators must match the id attribute of the operator
    @model_validator(mode='after')
    def check_operator_id(self):
        for operator_id, operator in self.operators.items():
            if operator_id != operator.id:
                raise ValueError(f"Operator id {operator.id} does not match the key id {operator_id}")

        return self


class WiringInout(BaseModel):
    name: str = Field(description=docs.wiring_inout_name_description)
    type: str = Field(description=docs.wiring_inout_type_description)  # TODO: Add enum
    label: str = Field(description=docs.wiring_inout_label_description, default='')
    description: str = Field(description=docs.wiring_inout_description_description, default='')
    friendcode: str = Field(description=docs.wiring_inout_friendcode_description, default='')


class WiringInput(WiringInout):
    actionlabel: str = Field(description=docs.wiring_input_actionlabel_description, default='')


class WiringOutput(WiringInout):
    pass


class WiringEndpoints(BaseModel):
    inputs: list[WiringInput] = Field(description=docs.wiring_endpoints_inputs_description, default=[])
    outputs: list[WiringOutput] = Field(description=docs.wiring_endpoints_outputs_description, default=[])


class WiringEntryPatch(BaseModel):
    op: str
    path: str
    value: Optional[Any] = None


class WiringOperatorVariablesValues(BaseModel):
    name: str
    secure: bool
    readonly: bool
    hidden: bool
    value: Any


class WiringOperatorVariables(BaseModel):
    preferences: WiringOperatorVariablesValues = {}
    properties: WiringOperatorVariablesValues = {}
