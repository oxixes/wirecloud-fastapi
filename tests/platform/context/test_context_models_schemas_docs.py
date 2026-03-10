# -*- coding: utf-8 -*-

from bson import ObjectId

from wirecloud.platform.context import docs, models, schemas


def test_docs_constants_are_strings():
    assert isinstance(docs.context_key_description_description, str)
    assert isinstance(docs.context_key_label_description, str)
    assert isinstance(docs.platform_context_key_value_description, str)
    assert isinstance(docs.context_platform_description, str)
    assert isinstance(docs.context_workspace_description, str)


def test_dbconstant_alias_and_schema_models():
    raw_id = ObjectId()
    constant = models.DBConstant.model_validate({"_id": raw_id, "concept": "A", "value": "1"})
    assert str(constant.id) == str(raw_id)
    assert constant.concept == "A"
    assert constant.value == "1"

    assert schemas.Constant is models.DBConstant

    base = schemas.BaseContextKey(label="Label", description="Description")
    platform = schemas.PlatformContextKey(label="Label", description="Description", value="v")
    workspace = schemas.WorkspaceContextKey(label="WL", description="WD")
    context = schemas.Context(platform={"k": platform}, workspace={"w": workspace})

    assert base.label == "Label"
    assert platform.value == "v"
    assert context.platform["k"].description == "Description"
    assert context.workspace["w"].label == "WL"
