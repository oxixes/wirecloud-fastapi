# -*- coding: utf-8 -*-

from bson import ObjectId

from wirecloud.platform.widget import crud, docs
from wirecloud.platform.widget.models import Widget


def test_widget_model_and_docs():
    widget = Widget(resource=ObjectId(), xhtml="/vendor/name/1.0/xhtml")
    assert widget.xhtml.endswith("/xhtml")
    assert isinstance(docs.get_widget_html_summary, str)
    assert isinstance(docs.get_widget_file_summary, str)
    assert isinstance(docs.get_missing_widget_html_summary, str)


async def test_get_widget_from_resource(db_session):
    resource_id = ObjectId()
    await db_session.client.widgets.insert_one({"resource": resource_id, "xhtml": "/x.xhtml"})

    found = await crud.get_widget_from_resource(db_session, resource_id)
    assert found is not None
    assert found.resource == resource_id

    missing = await crud.get_widget_from_resource(db_session, ObjectId())
    assert missing is None
