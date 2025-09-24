# -*- coding: utf-8 -*-

# Copyright (c) 2012-2017 CoNWeT Lab., Universidad Politécnica de Madrid
# Copyright (c) 2021 Future Internet Consulting and Development Solutions S.L.

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

from src.wirecloud.platform.plugins import URLTemplate

patterns = {
    'wirecloud.root': URLTemplate(urlpattern='/', defaults={}),
    'wirecloud.features': URLTemplate(urlpattern='/api/features', defaults={}),
    'wirecloud.version': URLTemplate(urlpattern='/api/version', defaults={}),

    # Context
    'wirecloud.platform_context_collection': URLTemplate(urlpattern='/api/context', defaults={}),

    'wirecloud.showcase_media': URLTemplate(urlpattern='/showcase/media/{vendor}/{name}/{version}/{path}', defaults={}),

    # Search service
    'wirecloud.search_service': URLTemplate(urlpattern='/api/search', defaults={}),

    # Widgets
    'wirecloud.resource_collection': URLTemplate(urlpattern='/api/resources', defaults={}),
    'wirecloud.resource_entry': URLTemplate(urlpattern='/api/resource/{vendor}/{name}/{version}', defaults={}),
    'wirecloud.unversioned_resource_entry': URLTemplate(urlpattern='/api/resource/{vendor}/{name}', defaults={}),
    'wirecloud.resource_description_entry': URLTemplate(
        urlpattern='/api/resource/{vendor}/{name}/{version}/description', defaults={}),
    'wirecloud.missing_widget_code_entry': URLTemplate(urlpattern='/api/widget/missing_widget', defaults={}),

    # IWidgets
    'wirecloud.iwidget_collection': URLTemplate(
        urlpattern='/api/workspace/{workspace_id}/tab/{tab_id}/widget_instances', defaults={}),
    'wirecloud.iwidget_entry': URLTemplate(
        urlpattern='/api/workspace/{workspace_id}/tab/{tab_id}/widget_instances/{iwidget_id}', defaults={}),
    'wirecloud.iwidget_preferences': URLTemplate(
        urlpattern='/api/workspace/{workspace_id}/tab/{tab_id}/widget_instances/{iwidget_id}/preferences', defaults={}),
    'wirecloud.iwidget_properties': URLTemplate(
        urlpattern='/api/workspace/{workspace_id}/tab/{tab_id}/widget_instances/{iwidget_id}/properties', defaults={}),

    # Preferences
    'wirecloud.platform_preferences': URLTemplate(urlpattern='/api/preferences/platform', defaults={}),
    'wirecloud.workspace_preferences': URLTemplate(urlpattern='/api/workspace/{workspace_id}/preferences', defaults={}),
    'wirecloud.tab_preferences': URLTemplate(
        urlpattern='/api/workspace/{workspace_id}/tab/{tab_id}/preferences', defaults={}),

    'wirecloud.operator_code_entry': URLTemplate(
        urlpattern='/api/operator/{vendor}/{name}/{version}/html', defaults={}),

    'wirecloud.market_collection': URLTemplate(urlpattern='/api/markets', defaults={}),
    'wirecloud.market_entry': URLTemplate(urlpattern='/api/market/{user}/{market}', defaults={}),
    'wirecloud.publish_on_other_marketplace': URLTemplate(urlpattern='/api/markets/publish', defaults={}),

    # Themes
    'wirecloud.theme_entry': URLTemplate(urlpattern='/api/theme/{name}', defaults={}),

    # Workspace
    'wirecloud.workspace_collection': URLTemplate(urlpattern='/api/workspaces', defaults={}),
    'wirecloud.workspace_entry': URLTemplate(urlpattern='/api/workspace/{workspace_id}', defaults={}),
    'wirecloud.tab_collection': URLTemplate(urlpattern='/api/workspace/{workspace_id}/tabs', defaults={}),
    'wirecloud.tab_order': URLTemplate(urlpattern='/api/workspace/{workspace_id}/tabs/order', defaults={}),
    'wirecloud.tab_entry': URLTemplate(urlpattern='/api/workspace/{workspace_id}/tab/{tab_id}', defaults={}),

    'wirecloud.workspace_resource_collection': URLTemplate(
        urlpattern='/api/workspace/{workspace_id}/resources', defaults={}),
    'wirecloud.workspace_wiring': URLTemplate(urlpattern='/api/workspace/{workspace_id}/wiring', defaults={}),
    'wirecloud.operator_variables': URLTemplate(
        urlpattern='/api/workspace/{workspace_id}/operators/{operator_id}/variables', defaults={}),
    'wirecloud.workspace_merge': URLTemplate(urlpattern='/api/workspace/{to_ws_id}/merge', defaults={}),
    'wirecloud.workspace_publish': URLTemplate(urlpattern='/api/workspace/{workspace_id}/publish', defaults={}),
    'wirecloud.workspace_entry_owner_name': URLTemplate(urlpattern='/api/workspace/{owner}/{name}', defaults={}),
    'wirecloud.switch_user_service': URLTemplate(urlpattern='/api/admin/switchuser', defaults={}),

    'wirecloud.workspace_view': URLTemplate(urlpattern='/{owner}/{name}', defaults={}),
}
