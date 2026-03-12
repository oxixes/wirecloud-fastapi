# -*- coding: utf-8 -*-

from wirecloud.platform.iwidget import docs, schemas
from wirecloud.platform.iwidget.models import WidgetPermissions


def test_iwidget_docs_constants():
    assert isinstance(docs.get_widget_instance_collection_summary, str)
    assert isinstance(docs.create_widget_instance_collection_summary, str)
    assert isinstance(docs.update_widget_instance_collection_summary, str)
    assert isinstance(docs.get_widget_instance_entry_summary, str)
    assert isinstance(docs.update_widget_instance_properties_summary, str)
    assert isinstance(docs.widget_instance_data, list)


def test_iwidget_schemas_roundtrip():
    create = schemas.WidgetInstanceDataCreate(
        title="Widget",
        layout=0,
        widget="acme/widget/1.0.0",
        layoutConfig=[],
        permissions=WidgetPermissions(),
    )
    data = schemas.WidgetInstanceData(
        **create.model_dump(),
        id="ws-0-0",
        preferences={},
        properties={},
    )
    update = schemas.WidgetInstanceDataUpdate(
        id="ws-0-0",
        layout=1,
        move=True,
    )
    assert create.widget == "acme/widget/1.0.0"
    assert data.id == "ws-0-0"
    assert update.move is True
