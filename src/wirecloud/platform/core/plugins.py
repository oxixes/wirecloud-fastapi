# -*- coding: utf-8 -*-

# Copyright (c) 2012-2017 CoNWeT Lab., Universidad Politécnica de Madrid
# Copyright (c) 2018-2021 Future Internet Consulting and Development Solutions S.L.

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

# TODO Add translations, finish the class implementation

import os

import orjson as json
from hashlib import sha1, md5
from typing import Any, Optional

from fastapi import FastAPI, Request

import src.wirecloud.platform as platform
from src import settings
from src.wirecloud.platform.iwidget.routes import iwidget_router
from src.wirecloud.platform.workspace.routes import workspace_router
from src.wirecloud.platform.plugins import (get_active_features_info, get_plugin_urls, AjaxEndpoint, build_url_template,
                                            WirecloudPlugin)
from src.wirecloud.platform.context.schemas import BaseContextKey, WorkspaceContextKey
from src.wirecloud.platform.preferences.routes import preferences_router
from src.wirecloud.platform.preferences.schemas import PreferenceKey, SelectEntry, TabPreferenceKey
from src.wirecloud.platform.urls import patterns
from src.wirecloud.platform.routes import get_current_theme
from src.wirecloud.commons.auth.schemas import UserAll, Session

from src.wirecloud.platform.context.routes import router as context_router
from src.wirecloud.platform.localcatalogue.routes import (router as localcatalogue_router,
                                                          resources_router as localcatalogue_resources_router)
from src.wirecloud.platform.markets.routes import router as market_router, markets_router
from src.wirecloud.platform.routes import router as platform_router
from src.wirecloud.platform.theme.routes import router as theme_router
from src.wirecloud.platform.core.catalogue_manager import WirecloudCatalogueManager

BASE_PATH = os.path.dirname(__file__)
WORKSPACE_BROWSER_FILE = os.path.join(BASE_PATH, 'initial', 'WireCloud_workspace-browser_0.1.4a1.wgt')
INITIAL_HOME_DASHBOARD_FILE = os.path.join(BASE_PATH, 'initial', 'initial_home_dashboard.wgt')
MARKDOWN_VIEWER_FILE = os.path.join(BASE_PATH, 'initial', 'CoNWeT_markdown-viewer_0.1.1.wgt')
MARKDOWN_EDITOR_FILE = os.path.join(BASE_PATH, 'initial', 'CoNWeT_markdown-editor_0.1.0.wgt')
LANDING_DASHBOARD_FILE = os.path.join(BASE_PATH, 'initial', 'WireCloud_landing-dashboard_1.0.wgt')


def get_version_hash():
    return sha1(json.dumps(get_active_features_info())).hexdigest()


class WirecloudCorePlugin(WirecloudPlugin):
    features = {
        'Wirecloud': platform.__version__,
        'ApplicationMashup': platform.__application_mashup_version__,
        'StyledElements': '0.11.0',
        'FullscreenWidget': '0.5',
        'DashboardManagement': '1.0',
        'ComponentManagement': '1.0',
    }

    urls = patterns

    def __init__(self, app: FastAPI):
        super().__init__(app)

        app.include_router(context_router, prefix="/api/context", tags=["Context"])
        app.include_router(localcatalogue_resources_router, prefix="/api/resources", tags=["Local Catalogue"])
        app.include_router(localcatalogue_router, prefix="/api/resource", tags=["Local Catalogue"])
        app.include_router(market_router, prefix="/api/market", tags=["Market"])
        app.include_router(markets_router, prefix="/api/markets", tags=["Market"])
        app.include_router(preferences_router, prefix="/api/preferences", tags=["Preferences"])
        app.include_router(workspace_router, prefix="/api/workspace", tags=["Workspace"])
        app.include_router(iwidget_router, prefix="/api/workspace", tags=["Iwidget"])
        app.include_router(theme_router, prefix="/api/theme", tags=["Theme"])
        app.include_router(platform_router, prefix="", tags=["Platform"])

    def get_platform_context_definitions(self) -> dict[str, BaseContextKey]:
        return {
            'language': BaseContextKey(
                label='Language',
                description='Current language used in the platform',
            ),
            'username': BaseContextKey(
                label='Username',
                description='User name of the current logged user',
            ),
            'fullname': BaseContextKey(
                label='Full name',
                description='Full name of the logged user',
            ),
            'avatar': BaseContextKey(
                label='Avatar',
                description='URL of the avatar',
            ),
            'isanonymous': BaseContextKey(
                label='Is Anonymous',
                description='Boolean. Designates whether current user is logged in the system.',
            ),
            'isstaff': BaseContextKey(
                label='Is Staff',
                description='Boolean. Designates whether current user can access the admin site.',
            ),
            'issuperuser': BaseContextKey(
                label='Is Superuser',
                description='Boolean. Designates whether current user is a super user.',
            ),
            'groups': BaseContextKey(
                label='Groups',
                description='List of groups the user belongs to',
            ),
            'mode': BaseContextKey(
                label='Mode',
                description='Rendering mode used by the platform (available modes: classic, smartphone and embedded)',
            ),
            'organizations': BaseContextKey(
                label='User Organizations',
                description='List of the organizations the user belongs to.',
            ),
            'orientation': BaseContextKey(
                label='Orientation',
                description='Current screen orientation',
            ),
            'realuser': BaseContextKey(
                label='Real User Username',
                description='User name of the real logged user',
            ),
            'theme': BaseContextKey(
                label='Theme',
                description='Name of the theme used by the platform',
            ),
            'version': BaseContextKey(
                label='Version',
                description='Version of the platform',
            ),
            'version_hash': BaseContextKey(
                label='Version Hash',
                description='Hash for the current version of the platform. This hash changes when the platform is updated or when an addon is added or removed',
            ),
        }

    def get_platform_context_current_values(self, request: Request, user: Optional[UserAll],
                                            session: Optional[Session]):
        if user:
            username = user.username
            fullname = user.get_full_name()
            avatar = 'https://www.gravatar.com/avatar/' + md5(
                user.email.strip().lower().encode('utf8')).hexdigest() + '?s=25'
            groups = tuple([group.name for group in user.groups])
        else:
            username = 'anonymous'
            fullname = 'Anonymous'
            avatar = 'https://www.gravatar.com/avatar/00000000000000000000000000000000?s=25'
            groups = ()

        return {
            'language': request.state.lang,
            'orientation': 'landscape',
            'username': username,
            'fullname': fullname,
            'avatar': avatar,
            'isanonymous': user is None,
            'isstaff': user.is_staff if user else False,
            'issuperuser': user.is_superuser if user else False,
            'groups': groups,
            # 'organizations': tuple(user.groups.filter(organization__isnull=False).values_list('name', flat=True)),
            'mode': 'unknown',
            'realuser': session.real_user if session else None,
            'theme': get_current_theme(request),
            'version': platform.__version__,
            'version_hash': get_version_hash(),
        }

    def get_workspace_context_definitions(self) -> dict[str, WorkspaceContextKey]:
        return {
            'description': WorkspaceContextKey(
                label='Description',
                description='Short description of the workspace without formating',
            ),
            'editing': WorkspaceContextKey(
                label='Editing mode',
                description='Boolean. Designates whether the workspace is in editing mode.',
            ),
            'title': WorkspaceContextKey(
                label='Title',
                description='Current title of the workspace',
            ),
            'name': WorkspaceContextKey(
                label='Name',
                description='Current name of the workspace',
            ),
            'owner': WorkspaceContextKey(
                label='Owner',
                description='Workspace\'s owner username',
            ),
            'longdescription': WorkspaceContextKey(
                label='Long description',
                description='Detailed workspace\'s description. This description can contain formatting.',
            ),
            'params': WorkspaceContextKey(
                label='Params',
                description='Dictionary with the parameters of the workspace',
            ),
        }

    def get_workspace_preferences(self) -> list[PreferenceKey]:
        return [
            PreferenceKey(
                name='public',
                label='Public',
                type='boolean',
                hidden=True,
                description='Allow any user to open this workspace (in read-only mode). (default: disabled)',
                defaultValue=False
            ),
            PreferenceKey(
                name='requireauth',
                label='Required registered user',
                type='boolean',
                hidden=True,
                description='Require users to be logged in to access the workspace (This option has only effect if the workspace is public). (default: disabled)',
                defaultValue=False
            ),
            PreferenceKey(
                name='sharelist',
                label='Share list',
                type='layout',  # TODO This is layout type in the original code, but that does not make sense
                hidden=True,
                description='List of users with access to this workspace. (default: [])',
                defaultValue=[]
            ),
            PreferenceKey(
                name='initiallayout',
                label='Initial layout',
                type='select',
                initialEntries=[
                    SelectEntry(value='Fixed', label='Base'),
                    SelectEntry(value='Free', label='Free')
                ],
                description='Default layout for the new widgets.'
            ),
            PreferenceKey(
                name='screenSizes',
                label='Screen sizes',
                type='screenSizes',
                description='List of screen sizes supported by the workspace. Each screen size is defined by a range of screen widths and different widget configurations are associated with it.',
                defaultValue=[
                    {
                        "moreOrEqual": 0,
                        "lessOrEqual": -1,
                        "name": "Default",
                        "id": 0
                    }
                ]
            ),
            PreferenceKey(
                name='baselayout',
                label='Base layout',
                type='layout',
                defaultValue={
                    "type": "columnlayout",
                    "smart": "false",
                    "columns": 20,
                    "cellheight": 12,
                    "horizontalmargin": 4,
                    "verticalmargin": 3
                }
            )
        ]

    def get_tab_preferences(self) -> list[TabPreferenceKey]:
        workspace_preferences = self.get_workspace_preferences()
        tab_preferences = []
        for preference in workspace_preferences:
            if preference.name != 'public':
                tab_preferences.append(TabPreferenceKey(
                    name=preference.name,
                    label=preference.label,
                    type=preference.type,
                    hidden=preference.hidden,
                    description=preference.description,
                    initialEntries=preference.initialEntries,
                    defaultValue=preference.defaultValue,
                    inheritable=True,
                    inheritByDefault=True
                ))

        return tab_preferences

    def get_market_classes(self) -> dict[str, type]:
        return {
            'wirecloud': WirecloudCatalogueManager,
        }

    def get_constants(self) -> dict[str, Any]:
        languages = [{'value': lang[0], 'label': lang[1]} for lang in settings.LANGUAGES]
        return {
            'AVAILABLE_LANGUAGES': languages,
        }

    def get_templates(self, view: str) -> list[str]:
        if view == 'classic' or view == 'smartphone':
            return [
                "wirecloud/component_sidebar",
                "wirecloud/catalogue/main_resource_details",
                "wirecloud/catalogue/modals/upload",
                "wirecloud/catalogue/resource",
                "wirecloud/catalogue/resource_details",
                "wirecloud/catalogue/search_interface",
                "wirecloud/logs/details",
                "wirecloud/modals/base",
                "wirecloud/modals/embed_code",
                "wirecloud/macsearch/base",
                "wirecloud/macsearch/component",
                "wirecloud/wiring/behaviour_sidebar",
                "wirecloud/wiring/component_group",
                "wirecloud/wiring/footer",
                "wirecloud/workspace/empty_tab_message",
                "wirecloud/workspace/sharing_user",
                "wirecloud/workspace/visibility_option",
                "wirecloud/workspace/widget",
                "wirecloud/modals/upgrade_downgrade_component",
                "wirecloud/signin",
                "wirecloud/user_menu",
            ]
        else:
            return []

    def get_ajax_endpoints(self, view: str, prefix: str) -> tuple[AjaxEndpoint, ...]:
        url_patterns = get_plugin_urls()

        if not 'wirecloud|proxy' in url_patterns:
            raise ValueError('Missing proxy url pattern. Is the proxy plugin enabled?')

        endpoints = (
            AjaxEndpoint(id='IWIDGET_COLLECTION', url=build_url_template(url_patterns['wirecloud.iwidget_collection'],
                                                                         ['workspace_id', 'tab_id'], prefix)),
            AjaxEndpoint(id='IWIDGET_ENTRY', url=build_url_template(url_patterns['wirecloud.iwidget_entry'],
                                                                    ['workspace_id', 'tab_id', 'iwidget_id'], prefix)),
            AjaxEndpoint(id='IWIDGET_PREFERENCES', url=build_url_template(url_patterns['wirecloud.iwidget_preferences'],
                                                                          ['workspace_id', 'tab_id', 'iwidget_id'],
                                                                          prefix)),
            AjaxEndpoint(id='IWIDGET_PROPERTIES', url=build_url_template(url_patterns['wirecloud.iwidget_properties'],
                                                                         ['workspace_id', 'tab_id', 'iwidget_id'],
                                                                         prefix)),
            AjaxEndpoint(id='LOCAL_REPOSITORY', url=build_url_template(url_patterns['wirecloud.root'], [], prefix)),
            AjaxEndpoint(id='LOCAL_RESOURCE_COLLECTION',
                         url=build_url_template(url_patterns['wirecloud.resource_collection'],
                                                ['vendor', 'name', 'version'], prefix)),
            AjaxEndpoint(id='LOCAL_RESOURCE_ENTRY',
                         url=build_url_template(url_patterns['wirecloud.resource_entry'], ['vendor', 'name', 'version'],
                                                prefix)),
            AjaxEndpoint(id='LOCAL_UNVERSIONED_RESOURCE_ENTRY',
                         url=build_url_template(url_patterns['wirecloud.unversioned_resource_entry'],
                                                ['vendor', 'name'], prefix)),
            AjaxEndpoint(id='LOGIN_API', url=build_url_template(url_patterns['wirecloud.login'], [], prefix)),
            AjaxEndpoint(id='LOGIN_VIEW', url=build_url_template(url_patterns['login'], [], prefix)),
            AjaxEndpoint(id='LOGOUT_VIEW', url=build_url_template(url_patterns['logout'], [], prefix)),
            AjaxEndpoint(id='MAC_BASE_URL', url=build_url_template(url_patterns['wirecloud.showcase_media'],
                                                                   ['vendor', 'name', 'version', 'file_path'], prefix)),
            AjaxEndpoint(id='MARKET_COLLECTION',
                         url=build_url_template(url_patterns['wirecloud.market_collection'], [], prefix)),
            AjaxEndpoint(id='MARKET_ENTRY',
                         url=build_url_template(url_patterns['wirecloud.market_entry'], ['user', 'market'], prefix)),
            AjaxEndpoint(id='MISSING_WIDGET_CODE_ENTRY',
                         url=build_url_template(url_patterns['wirecloud.missing_widget_code_entry'], [], prefix)),
            AjaxEndpoint(id='OPERATOR_ENTRY', url=build_url_template(url_patterns['wirecloud.operator_code_entry'],
                                                                     ['vendor', 'name', 'version'], prefix)),
            AjaxEndpoint(id='PLATFORM_CONTEXT_COLLECTION',
                         url=build_url_template(url_patterns['wirecloud.platform_context_collection'], [], prefix)),
            AjaxEndpoint(id='PLATFORM_PREFERENCES',
                         url=build_url_template(url_patterns['wirecloud.platform_preferences'], [], prefix)),
            AjaxEndpoint(id='PROXY',
                         url=build_url_template(url_patterns['wirecloud|proxy'], ['protocol', 'domain', 'path'],
                                                prefix)),
            AjaxEndpoint(id='PUBLISH_ON_OTHER_MARKETPLACE',
                         url=build_url_template(url_patterns['wirecloud.publish_on_other_marketplace'], [], prefix)),
            AjaxEndpoint(id='ROOT_URL', url=build_url_template(url_patterns['wirecloud.root'], [], prefix)),
            AjaxEndpoint(id='SEARCH_SERVICE',
                         url=build_url_template(url_patterns['wirecloud.search_service'], [], prefix)),
            AjaxEndpoint(id='SWITCH_USER_SERVICE',
                         url=build_url_template(url_patterns['wirecloud.switch_user_service'], [], prefix)),
            AjaxEndpoint(id='TAB_COLLECTION',
                         url=build_url_template(url_patterns['wirecloud.tab_collection'], ['workspace_id'], prefix)),
            AjaxEndpoint(id='TAB_ENTRY',
                         url=build_url_template(url_patterns['wirecloud.tab_entry'], ['workspace_id', 'tab_id'],
                                                prefix)),
            AjaxEndpoint(id='TAB_PREFERENCES',
                         url=build_url_template(url_patterns['wirecloud.tab_preferences'], ['workspace_id', 'tab_id'],
                                                prefix)),
            AjaxEndpoint(id='THEME_ENTRY',
                         url=build_url_template(url_patterns['wirecloud.theme_entry'], ['name'], prefix)),
            AjaxEndpoint(id='WIRING_ENTRY',
                         url=build_url_template(url_patterns['wirecloud.workspace_wiring'], ['workspace_id'], prefix)),
            AjaxEndpoint(id='OPERATOR_VARIABLES_ENTRY',
                         url=build_url_template(url_patterns['wirecloud.operator_variables'],
                                                ['workspace_id', 'operator_id'], prefix)),
            AjaxEndpoint(id='WORKSPACE_COLLECTION',
                         url=build_url_template(url_patterns['wirecloud.workspace_collection'], [], prefix)),
            AjaxEndpoint(id='WORKSPACE_ENTRY_OWNER_NAME',
                         url=build_url_template(url_patterns['wirecloud.workspace_entry_owner_name'], ['owner', 'name'],
                                                prefix)),
            AjaxEndpoint(id='WORKSPACE_ENTRY',
                         url=build_url_template(url_patterns['wirecloud.workspace_entry'], ['workspace_id'], prefix)),
            AjaxEndpoint(id='WORKSPACE_MERGE',
                         url=build_url_template(url_patterns['wirecloud.workspace_merge'], ['to_ws_id'], prefix)),
            AjaxEndpoint(id='WORKSPACE_PREFERENCES',
                         url=build_url_template(url_patterns['wirecloud.workspace_preferences'], ['workspace_id'],
                                                prefix)),
            AjaxEndpoint(id='WORKSPACE_PUBLISH',
                         url=build_url_template(url_patterns['wirecloud.workspace_publish'], ['workspace_id'], prefix)),
            AjaxEndpoint(id='WORKSPACE_RESOURCE_COLLECTION',
                         url=build_url_template(url_patterns['wirecloud.workspace_resource_collection'],
                                                ['workspace_id'], prefix)),
            AjaxEndpoint(id='WORKSPACE_VIEW',
                         url=build_url_template(url_patterns['wirecloud.workspace_view'], ['owner', 'name'], prefix)),
        )

        return endpoints

    def get_widget_api_extensions(self, view: str, features: list[str]) -> list[str]:
        extensions = ['js/WirecloudAPI/StyledElements.js']

        if 'DashboardManagement' in features:
            extensions.append('js/WirecloudAPI/DashboardManagementAPI.js')

        if 'ComponentManagement' in features:
            extensions.append('js/WirecloudAPI/ComponentManagementAPI.js')

        return extensions

    def get_operator_api_extensions(self, view: str, features: list[str]) -> list[str]:
        extensions = []

        if 'DashboardManagement' in features:
            extensions.append('js/WirecloudAPI/DashboardManagementAPI.js')

        if 'ComponentManagement' in features:
            extensions.append('js/WirecloudAPI/ComponentManagementAPI.js')

        return extensions

    def get_proxy_processors(self) -> tuple[str, ...]:
        return ('src.wirecloud.proxy.processors.SecureDataProcessor',)
