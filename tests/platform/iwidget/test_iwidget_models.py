# -*- coding: utf-8 -*-

from types import SimpleNamespace

from bson import ObjectId

from wirecloud.platform.iwidget import models


def test_widget_models_serialization():
    cfg = models.WidgetConfig(anchor=models.WidgetConfigAnchor.top_left)
    assert cfg.model_dump()["anchor"] == "top-left"
    assert cfg.serialize_enum(models.WidgetConfigAnchor.top_left, None) == "top-left"
    assert cfg.serialize_enum("top-left", None) == "top-left"

    pos = models.WidgetPositionsConfig(id=0, moreOrEqual=0, lessOrEqual=-1)
    assert pos.widget.moreOrEqual == 0
    assert pos.widget.lessOrEqual == -1

    perms = models.WidgetPermissions(
        editor=models.WidgetPermissionsConfig(move=True, close=None),
        viewer=models.WidgetPermissionsConfig(move=False, rename=None),
    )
    serialized = perms.model_dump()
    assert serialized["editor"] == {"move": True}
    assert serialized["viewer"] == {"move": False}


async def test_widget_instance_set_variable_value(monkeypatch, db_session):
    instance = models.WidgetInstance(id="ws-0-0", resource=ObjectId())
    user = SimpleNamespace(id="u1")

    class _VarDef:
        def __init__(self, secure=False, var_type="text"):
            self.secure = secure
            self.type = var_type

    class _ResourceInfo:
        variables = SimpleNamespace(
            all={
                "secure_var": _VarDef(secure=True, var_type="text"),
                "bool_var": _VarDef(secure=False, var_type="boolean"),
                "num_var": _VarDef(secure=False, var_type="number"),
                "text_var": _VarDef(secure=False, var_type="text"),
            }
        )

    monkeypatch.setattr(models, "get_catalogue_resource_by_id", lambda *_args, **_kwargs: _resource())
    monkeypatch.setattr("wirecloud.platform.workspace.utils.encrypt_value", lambda value: f"enc:{value}")

    async def _resource():
        return SimpleNamespace(get_processed_info=lambda **_kwargs: _ResourceInfo())

    await instance.set_variable_value(db_session, "secure_var", "secret", user)
    assert instance.variables["secure_var"].users["u1"] == "enc:secret"

    await instance.set_variable_value(db_session, "bool_var", "true", user)
    assert instance.variables["bool_var"].users["u1"] is True
    await instance.set_variable_value(db_session, "bool_var", 0, user)
    assert instance.variables["bool_var"].users["u1"] is False

    await instance.set_variable_value(db_session, "num_var", "3.5", user)
    assert instance.variables["num_var"].users["u1"] == 3.5

    await instance.set_variable_value(db_session, "text_var", "abc", user)
    assert instance.variables["text_var"].users["u1"] == "abc"

    instance.variables["text_var"] = {"users": {"u1": "x"}}
    await instance.set_variable_value(db_session, "text_var", "def", user)
    assert instance.variables["text_var"]["users"]["u1"] == "def"

    monkeypatch.setattr(models, "get_catalogue_resource_by_id", lambda *_args, **_kwargs: _none())

    async def _none():
        return None

    try:
        await instance.set_variable_value(db_session, "text_var", "x", user)
    except ValueError as exc:
        assert "Widget not found" in str(exc)
