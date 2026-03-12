# -*- coding: utf-8 -*-

import pytest
from pydantic import ValidationError

from wirecloud.platform.wiring import docs, schemas


def test_wiring_docs_constants():
    assert isinstance(docs.update_wiring_entry_summary, str)
    assert isinstance(docs.patch_wiring_entry_wiring_example, list)
    assert isinstance(docs.get_operator_response_example, str)


def test_wiring_schemas_serializers_and_validators():
    endpoint = schemas.WiringConnectionEndpoint(type=schemas.WiringType.widget, id="w1", endpoint="out")
    assert endpoint.model_dump()["type"] == "widget"
    assert endpoint.serialize_wiring_type(schemas.WiringType.operator) == "operator"

    conn_default = schemas.WiringVisualDescriptionConnection(sourcename="widget/w1/out", targetname="operator/1/in")
    dumped_default = conn_default.model_dump()
    assert dumped_default["sourcehandle"] == "auto"
    assert dumped_default["targethandle"] == "auto"

    conn_pos = schemas.WiringVisualDescriptionConnection(
        sourcename="widget/w1/out",
        targetname="operator/1/in",
        sourcehandle=schemas.WiringPosition(x=1, y=2),
        targethandle=schemas.WiringPosition(x=3, y=4),
    )
    dumped_pos = conn_pos.model_dump()
    assert dumped_pos["sourcehandle"] == {"x": 1, "y": 2}
    assert dumped_pos["targethandle"] == {"x": 3, "y": 4}

    wiring = schemas.Wiring(
        version="2.0",
        operators={
            "1": schemas.WiringOperator(id="1", name="acme/op/1.0.0", preferences={}),
        },
    )
    assert wiring.version == "2.0"

    with pytest.raises(ValidationError):
        schemas.Wiring(version="1.0")

    with pytest.raises(ValidationError, match="does not match the key id"):
        schemas.Wiring(
            version="2.0",
            operators={
                "1": schemas.WiringOperator(id="2", name="acme/op/1.0.0", preferences={}),
            },
        )

    vars_data = schemas.WiringOperatorVariables()
    assert vars_data.preferences == {}
    assert vars_data.properties == {}
