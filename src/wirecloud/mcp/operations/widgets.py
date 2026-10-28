"""Widget authoring without bypassing core permissions or forced values."""

from fastapi import HTTPException

from wirecloud.database import Id
from wirecloud.platform.iwidget import routes
from wirecloud.platform.iwidget.schemas import WidgetInstanceDataCreate, WidgetInstanceDataUpdate


async def add_widget(adapter, args):
    await adapter.resource(args.resource)
    return await adapter.call(
        routes.create_widget_instance_collection,
        workspace_id=Id(args.workspace_id),
        tab_id=args.tab_id,
        iwidget=WidgetInstanceDataCreate(title=args.title, widget=args.resource, layouts=args.layouts),
    )


async def update_widget(adapter, args):
    if args.resource:
        await adapter.resource(args.resource)
    return await adapter.call(
        routes.update_widget_instance_entry,
        workspace_id=Id(args.workspace_id),
        tab_id=args.tab_id,
        iwidget_id=args.widget_id,
        iwidget_data=WidgetInstanceDataUpdate(
            title=args.title,
            widget=args.resource,
            tab=args.destination_tab_id,
            layouts=args.layouts,
        ),
    )


async def remove_widget(adapter, args):
    return await adapter.call(
        routes.delete_widget_instance_entry,
        workspace_id=Id(args.workspace_id),
        tab_id=args.tab_id,
        iwidget_id=args.widget_id,
    )


async def set_widget_variables(adapter, args):
    workspace = await adapter.workspace(args.workspace_id)
    forced = workspace.forced_values.widget.get(args.widget_id, {})
    if any(key in forced for key in args.values):
        raise HTTPException(403, "Forced widget values cannot be changed")

    operation = (
        routes.update_widget_instance_preferences
        if args.kind == "preferences"
        else routes.update_widget_instance_properties
    )
    return await adapter.call(
        operation,
        workspace_id=Id(args.workspace_id),
        tab_id=args.tab_id,
        iwidget_id=args.widget_id,
        new_values=args.values,
    )
