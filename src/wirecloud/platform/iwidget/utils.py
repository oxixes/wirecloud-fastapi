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

from typing import Union, Any, Optional
from fastapi import Request, Response

from wirecloud.catalogue.crud import get_catalogue_resource, get_catalogue_resource_by_id
from wirecloud.catalogue.schemas import CatalogueResource
from wirecloud.commons.auth.schemas import User, UserAll
from wirecloud.commons.utils.http import NotFound, build_error_response
from wirecloud.commons.utils.template.schemas.macdschemas import MACDWidget, MACDProperty, MACDPreference
from wirecloud.database import DBSession
from wirecloud.platform.iwidget.models import WidgetVariables, WidgetInstance, WidgetPositionsConfig, WidgetConfig, \
    WidgetPermissionsConfig, WidgetPositions
from wirecloud.platform.iwidget.schemas import WidgetInstanceDataUpdate, WidgetInstanceDataCreate, LayoutConfig
from wirecloud.platform.workspace.models import Workspace, Tab
from wirecloud.translation import gettext as _

def parse_value_from_text(info: dict, value) -> Any:
    if info['type'] == 'boolean':
        return value.strip().lower() in ('true', '1', 'on')
    elif info['type'] == 'number':
        try:
            return float(value)
        except ValueError:
            try:
                return float(info['default'])
            except (KeyError, ValueError):
                return 0
    else:
        return str(value)


def process_initial_value(vardef: Union[MACDProperty, MACDPreference],
                          initial_value: Union[str, WidgetVariables, None] = None) -> Any:
    if (isinstance(vardef, MACDProperty) or not vardef.readonly) and initial_value is not None:
        value = initial_value
    elif vardef.value is not None:
        value = vardef.value
    elif vardef.default:
        value = parse_value_from_text(vardef.model_dump(), vardef.default)
    else:
        value = ''

    return value


async def update_widget_value(db: DBSession, iwidget: WidgetInstance, data: Union[WidgetInstanceDataCreate, WidgetInstanceDataUpdate], user: UserAll,
                              required: bool = False) -> Optional[CatalogueResource]:
    if data.widget != '' and data.widget is not None:
        (widget_vendor, widget_name, widget_version) = data.widget.split('/')
        resource = await get_catalogue_resource(db, widget_vendor, widget_name, widget_version)
        if resource is None:
            raise ValueError(_('Widget not found'))

        if not resource.is_available_for(user):
            raise NotFound(_('Widget not available'))

        if resource.resource_type() != 'widget':
            raise ValueError(_('%(uri)s is not a widget') % {"uri": data.widget})

        iwidget.resource = resource.id
        return resource

    elif required:
        raise ValueError('Missing widget info')

    return None


async def update_title_value(db: DBSession, iwidget: WidgetInstance, data: Union[WidgetInstanceDataCreate, WidgetInstanceDataUpdate]) -> None:
    if data.title is not None:
        if data.title.strip() == '':
            resource = await get_catalogue_resource_by_id(db, iwidget.resource)
            iwidget_info = resource.get_processed_info()
            iwidget.title = iwidget_info.title
        else:
            iwidget.title = data.title


def update_screen_size_value(model: WidgetPositionsConfig, data: LayoutConfig, field: str) -> None:
    value = getattr(data, field)

    if value is None:
        return

    if type(value) is not int:
        raise TypeError(_('Field %(field)s must contain a number value') % {"field": field})

    if value < -1:
        raise ValueError(_('Invalid value for %(field)s field') % {"field": field})

    setattr(model, field, value)


def update_position_value(model: WidgetConfig, data: LayoutConfig, field: str, data_field=None) -> None:
    data_field = data_field if data_field is not None else field

    if getattr(data, data_field) is None:
        return

    size = getattr(data, data_field)

    if type(size) not in (int, float):
        raise TypeError(_('Field %(data_field)s must contain a number value') % {"data_field": data_field})

    if size < 0:
        raise ValueError(_('Invalid value for %(data_field)s field') % {"data_field": data_field})

    setattr(model, field, size)


def update_size_value(model: WidgetConfig, data: LayoutConfig, field: str) -> None:
    size = getattr(data, field)

    if size is None:
        return

    if type(size) not in (int, float):
        raise TypeError(_('Field %(field)s must contain a number value') % {"field": field})

    if size <= 0:
        raise ValueError(_('Invalid value for %(field)s field') % {"field": field})

    setattr(model, field, size)


def update_boolean_value(model: Union[WidgetConfig, WidgetPermissionsConfig], data: Union[WidgetConfig, WidgetInstanceDataUpdate], field: str) -> None:
    value = getattr(data, field)

    if value is None:
        return

    if not isinstance(value, bool):
        raise TypeError(_(f'Field %(field)s must contain a boolean value') % {"field": field})

    setattr(model, field, value)


def update_anchor_value(model: WidgetConfig, data: LayoutConfig) -> None:
    if data.anchor is None:
        return

    model.anchor = data.anchor

def update_permissions(iwidget: WidgetInstance, data: WidgetInstanceDataUpdate) -> None:
    permissions = iwidget.permissions.viewer
    if data.move is not None:
        update_boolean_value(permissions, data, 'move')

async def set_initial_values(db: DBSession, iwidget: WidgetInstance,
                             initial_values: dict[str, Union[str, WidgetVariables]], iwidget_info: MACDWidget,
                             user: User) -> None:
    for vardef in (iwidget_info.preferences + iwidget_info.properties):
        if vardef.name in initial_values:
            initial_value = initial_values[vardef.name]
        else:
            initial_value = None
        await iwidget.set_variable_value(db, vardef.name, process_initial_value(vardef, initial_value), user)


def check_intervals(data: list[WidgetPositionsConfig]) -> None:
    # The screen size intervals should cover the interval [0, +inf) and should not overlap nor have gaps,
    # each interval is defined by the properties 'moreOrEqual' and 'lessOrEqual'

    data.sort(key=lambda x: x.moreOrEqual)

    if data[0].moreOrEqual != 0:
        raise ValueError('The first interval must start from 0')

    for i in range(len(data) - 1):
        if data[i].lessOrEqual + 1 != data[i + 1].moreOrEqual:
            raise ValueError('Intervals should not overlap nor have gaps')

    if data[-1].lessOrEqual != -1:
        raise ValueError('The last interval must extend to infinity')



def update_position(iwidget: WidgetInstance, key: str, data: Union[WidgetInstanceDataCreate, WidgetInstanceDataUpdate]) -> None:
    ids = set()
    for layoutConfig in data.layoutConfig:
        if layoutConfig.id in ids:
            raise ValueError('Duplicated id field')
        ids.add(layoutConfig.id)

    intervals = {}
    for conf in iwidget.positions.configurations:
        intervals[conf.id] = conf

    for layoutConfig in data.layoutConfig:
        if layoutConfig.action not in ('update', 'delete'):
            raise ValueError(f'Invalid value for action field: {layoutConfig.action}')
        if layoutConfig.action == 'delete':
            del intervals[layoutConfig.id]
        else:
            if not layoutConfig.id in intervals:
                intervals[layoutConfig.id] = WidgetPositionsConfig(
                    id=layoutConfig.id,
                    moreOrEqual=0,
                    lessOrEqual=-1,
                )
                wgt_config = WidgetConfig(
                    top=0,
                    left=0,
                    zIndex=0,
                    height=0,
                    width=0,
                    minimized=False,
                    titlevisible=True,
                    fulldragboard=False
                )
                setattr(intervals[layoutConfig.id], key, wgt_config)

            update_screen_size_value(intervals[layoutConfig.id], layoutConfig, 'moreOrEqual')
            update_screen_size_value(intervals[layoutConfig.id], layoutConfig, 'lessOrEqual')
            update_position_value(getattr(intervals[layoutConfig.id], key), layoutConfig, 'top')
            update_position_value(getattr(intervals[layoutConfig.id], key), layoutConfig, 'left')
            update_position_value(getattr(intervals[layoutConfig.id], key), layoutConfig, 'zIndex')
            update_size_value(getattr(intervals[layoutConfig.id], key), layoutConfig, 'height')
            update_size_value(getattr(intervals[layoutConfig.id], key), layoutConfig, 'width')
            update_boolean_value(getattr(intervals[layoutConfig.id], key), layoutConfig, 'minimized')
            update_boolean_value(getattr(intervals[layoutConfig.id], key), layoutConfig, 'titlevisible')
            update_boolean_value(getattr(intervals[layoutConfig.id], key), layoutConfig, 'fulldragboard')
            update_boolean_value(getattr(intervals[layoutConfig.id], key), layoutConfig, 'relwidth')
            update_boolean_value(getattr(intervals[layoutConfig.id], key), layoutConfig, 'relheight')
            update_boolean_value(getattr(intervals[layoutConfig.id], key), layoutConfig, 'relx')
            update_boolean_value(getattr(intervals[layoutConfig.id], key), layoutConfig, 'rely')
            update_anchor_value(getattr(intervals[layoutConfig.id], key), layoutConfig)

    new_positions = list(intervals.values())
    check_intervals(new_positions)
    iwidget.positions.configurations = new_positions

def first_id_widget_instance(widgets: dict[str, WidgetInstance]) -> int:
    used = {int(widget.id.split("-")[2]) for widget in widgets.values()}
    i = 0
    while i in used:
        i += 1
    return i

async def save_widget_instance(db: DBSession, workspace: Workspace, iwidget: WidgetInstanceDataCreate, user: UserAll, tab: Tab,
                       initial_variable_values: dict[str, WidgetVariables] = None,
                       commit: bool = True, resource_owner: Optional[UserAll] = None) -> WidgetInstance:

    new_iwidget = WidgetInstance(
        id=tab.id + '-' + str(first_id_widget_instance(tab.widgets)),
        permissions=iwidget.permissions,
        widget_uri=iwidget.widget
    )
    resource = await update_widget_value(db, new_iwidget, iwidget, resource_owner if resource_owner is not None else user, required=True)
    iwidget_info = resource.get_processed_info()
    new_iwidget.title = iwidget_info.title
    new_iwidget.layout = iwidget.layout

    new_iwidget.positions = WidgetPositions(
        configurations=[]
    )

    if initial_variable_values is not None:
        await set_initial_values(db, new_iwidget, initial_variable_values, iwidget_info, user)

    await update_title_value(db, new_iwidget, iwidget)
    if len(iwidget.layoutConfig) > 0:
        update_position(new_iwidget, 'widget', iwidget)
    else:
        # Set default positions
        new_iwidget.positions.configurations = [WidgetPositionsConfig(
            moreOrEqual=0,
            lessOrEqual=-1,
            id=0,
            widget=WidgetConfig(
                top=0,
                left=0,
                zIndex=0,
                height=1,
                width=1,
                minimized=False,
                titlevisible=True,
                fulldragboard=False
            )
        )]

    if commit:
        tab.widgets[new_iwidget.id] = new_iwidget
        from wirecloud.platform.workspace.crud import change_tab
        await change_tab(db, user, workspace, tab)

    return new_iwidget


def get_widget_instances_from_workspace(workspace: Workspace) -> list[WidgetInstance]:
    return [widget for tab in workspace.tabs.values() for widget in tab.widgets.values()]


async def update_widget_instance(db: DBSession, request: Request,  data: WidgetInstanceDataUpdate, user: UserAll, workspace: Workspace, tab: Tab, update_cache: bool = True) -> Optional[Response]:
    if data.id is None:
        raise ValueError('Missing id field')

    try:
        iwidget = tab.widgets[data.id]
    except KeyError:
        return build_error_response(request, 404, _("Widget Instance not found"))

    await update_widget_value(db, iwidget, data, user)
    await update_title_value(db, iwidget, data)

    if data.layout is not None:
        if data.layout < 0:
            raise ValueError('Invalid value for layout field') # TODO remove this
        layout = data.layout
        iwidget.layout = layout

    update_permissions(iwidget, data)

    if data.layoutConfig is not None:
        update_position(iwidget, 'widget', data)

    if data.tab is not None:
        if data.tab not in workspace.tabs:
            return build_error_response(request, 404, _("Tab not found"))
        if data.tab != tab.id:
            del workspace.tabs[tab.id].widgets[iwidget.id]
            iwidget.id = str(data.tab) + '-' + str(first_id_widget_instance(workspace.tabs[data.tab].widgets))
            workspace.tabs[data.tab].widgets[iwidget.id] = iwidget

        else:
            workspace.tabs[tab.id].widgets[iwidget.id] = iwidget
    else:
        workspace.tabs[tab.id].widgets[iwidget.id] = iwidget

    if update_cache:
        from wirecloud.platform.workspace.crud import change_workspace
        await change_workspace(db, workspace, user)


