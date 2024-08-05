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
import json
from hashlib import sha1, md5
from typing import Any, Optional
import src.wirecloud.platform as platform
from src import settings
from src.wirecloud.platform.plugins import (get_active_features_info, get_plugin_urls, AjaxEndpoint, build_url_template,
                                            WirecloudPlugin)
from src.wirecloud.platform.context.routes import router as context_router
from src.wirecloud.platform.context.schemas import BaseContextKey, WorkspaceContextKey
from src.wirecloud.platform.preferences.schemas import PreferenceKey, SelectEntry, TabPreferenceKey
from src.wirecloud.platform.urls import patterns
from src.wirecloud.commons.auth.schemas import UserAll, Session

WIRING_EDITOR_FILES = (
    'js/wirecloud/ui/WiringEditor.js',
    'js/wirecloud/ui/WiringEditor/Behaviour.js',
    'js/wirecloud/ui/WiringEditor/BehaviourPrefs.js',
    'js/wirecloud/ui/WiringEditor/BehaviourEngine.js',
    'js/wirecloud/ui/WiringEditor/Endpoint.js',
    'js/wirecloud/ui/WiringEditor/EndpointGroup.js',
    'js/wirecloud/ui/WiringEditor/Component.js',
    'js/wirecloud/ui/WiringEditor/ComponentPrefs.js',
    'js/wirecloud/ui/WiringEditor/ComponentGroup.js',
    'js/wirecloud/ui/WiringEditor/ComponentShowcase.js',
    'js/wirecloud/ui/WiringEditor/ComponentDraggable.js',
    'js/wirecloud/ui/WiringEditor/ComponentDraggablePrefs.js',
    'js/wirecloud/ui/WiringEditor/Connection.js',
    'js/wirecloud/ui/WiringEditor/ConnectionPrefs.js',
    'js/wirecloud/ui/WiringEditor/ConnectionHandle.js',
    'js/wirecloud/ui/WiringEditor/ConnectionEngine.js',
    'js/wirecloud/ui/WiringEditor/KeywordSuggestion.js',
)

WIRECLOUD_API_FILES = (
    'js/WirecloudAPI/WirecloudAPIBootstrap.js',
    'js/WirecloudAPI/WirecloudWidgetAPI.js',
    'js/WirecloudAPI/WirecloudOperatorAPI.js',
    'js/WirecloudAPI/WirecloudAPICommon.js',
    'js/WirecloudAPI/StyledElements.js',
    'js/WirecloudAPI/ComponentManagementAPI.js',
    'js/WirecloudAPI/DashboardManagementAPI.js',
    'js/WirecloudAPI/WirecloudAPIClosure.js',
    'js/WirecloudAPI/WirecloudAPIV2Bootstrap.js'
)

TUTORIAL_FILES = (
    'js/wirecloud/ui/Tutorial.js',
    'js/wirecloud/ui/Tutorial/Utils.js',
    'js/wirecloud/ui/TutorialCatalogue.js',
    'js/wirecloud/ui/TutorialSubMenu.js',
    'js/wirecloud/ui/Tutorial/PopUp.js',
    'js/wirecloud/ui/Tutorial/SimpleDescription.js',
    'js/wirecloud/ui/Tutorial/UserAction.js',
    'js/wirecloud/ui/Tutorial/FormAction.js',
    'js/wirecloud/ui/Tutorial/AutoAction.js',
    'js/wirecloud/Tutorials/BasicConcepts.js',
    'js/wirecloud/Tutorials/BehaviourOrientedWiring.js',
)

SHIM_FILES = (
    'js/wirecloud/shims/classList.js',
)

STYLED_ELEMENTS_FILES = (
    # 'js/StyledElements/Utils.js', Added on bootstrap.html
    # 'js/StyledElements/ObjectWithEvents.js', Added as common file
    'js/StyledElements/StyledElements.js',
    'js/StyledElements/InputElement.js',
    'js/StyledElements/CommandQueue.js',
    'js/StyledElements/Container.js',
    'js/StyledElements/Accordion.js',
    'js/StyledElements/Expander.js',
    'js/StyledElements/Fragment.js',
    'js/StyledElements/PaginatedSource.js',
    'js/StyledElements/GUIBuilder.js',
    'js/StyledElements/Tooltip.js',
    'js/StyledElements/Addon.js',
    'js/StyledElements/Button.js',
    'js/StyledElements/FileButton.js',
    'js/StyledElements/PopupMenuBase.js',
    'js/StyledElements/PopupMenu.js',
    'js/StyledElements/DynamicMenuItems.js',
    'js/StyledElements/MenuItem.js',
    'js/StyledElements/Separator.js',
    'js/StyledElements/SubMenuItem.js',
    'js/StyledElements/PopupButton.js',
    'js/StyledElements/StaticPaginatedSource.js',
    'js/StyledElements/FileField.js',
    'js/StyledElements/NumericField.js',
    'js/StyledElements/TextField.js',
    'js/StyledElements/TextArea.js',
    'js/StyledElements/CodeArea.js',
    'js/StyledElements/List.js',
    'js/StyledElements/PasswordField.js',
    'js/StyledElements/Select.js',
    'js/StyledElements/ToggleButton.js',
    'js/StyledElements/Pills.js',
    'js/StyledElements/Tab.js',
    'js/StyledElements/Notebook.js',
    'js/StyledElements/Alternative.js',
    'js/StyledElements/Alternatives.js',
    'js/StyledElements/HorizontalLayout.js',
    'js/StyledElements/VerticalLayout.js',
    'js/StyledElements/BorderLayout.js',
    'js/StyledElements/ModelTable.js',
    'js/StyledElements/EditableElement.js',
    'js/StyledElements/HiddenField.js',
    'js/StyledElements/ButtonsGroup.js',
    'js/StyledElements/CheckBox.js',
    'js/StyledElements/RadioButton.js',
    'js/StyledElements/InputInterface.js',
    'js/StyledElements/TextInputInterface.js',
    'js/StyledElements/InputInterfaces.js',
    'js/StyledElements/MultivaluedInputInterface.js',
    'js/wirecloud/ui/ParametrizableValueInputInterface.js',
    'js/wirecloud/ui/ParametrizedTextInputInterface.js',
    'js/wirecloud/ui/LayoutInputInterface.js',
    'js/wirecloud/ui/ScreenSizesInputInterface.js',
    'js/StyledElements/VersionInputInterface.js',
    'js/StyledElements/InputInterfaceFactory.js',
    'js/StyledElements/DefaultInputInterfaceFactory.js',
    'js/StyledElements/Form.js',
    'js/StyledElements/PaginationInterface.js',
    'js/StyledElements/Popover.js',
    'js/StyledElements/Panel.js',
    'js/StyledElements/OffCanvasLayout.js',
    'js/StyledElements/Alert.js',
    'js/StyledElements/Typeahead.js',
)

BASE_CSS = (
    'css/fontawesome.min.css',
    'css/fontawesome-v4-shims.min.css',
    'css/base/utils.scss',
    'css/base/body.scss',
    'css/base/fade.css',
    'css/base/slide.scss',
    'css/base/code.scss',
    'css/base/z-depth.scss',
    'css/base/navigation.scss',
)

CLASSIC_CORE_CSS = (
    'css/mac_search.scss',
    'css/layout_field.css',
    'css/screen_size_field.css',
    'css/mac_field.scss',
    'css/mac_selection_dialog.css',
)

WORKSPACE_CSS = (
    'css/workspace/dragboard.scss',
    'css/workspace/dragboard_cursor.scss',
    'css/workspace/operator.scss',
    'css/workspace/widget.scss',
    'css/workspace/modals/share.scss',
    'css/workspace/modals/upload.scss',
    'css/modals/upgrade_downgrade_component.scss',
    'css/modals/embed_code.scss',
)

CATALOGUE_CSS = (
    'css/catalogue/emptyCatalogueBox.css',
    'css/catalogue/resource.scss',
    'css/catalogue/resource_details.scss',
    'css/catalogue/search_interface.scss',
    'css/catalogue/modals/upload.scss',
)

PLATFORM_CORE_CSS = (
    'css/wirecloud_core.scss',
    'css/header.scss',
    'css/icons.css',
    'css/modals/base.scss',
    'css/modals/logs.scss',
)

WIRING_EDITOR_CSS = (
    'css/wiring/layout.scss',
    'css/wiring/components.scss',
    'css/wiring/connection.scss',
    'css/wiring/behaviours.scss',
)

TUTORIAL_CSS = (
    'css/tutorial.scss',
)

STYLED_ELEMENTS_CSS = (
    'css/styled_elements_core.css',
    'css/styledelements/styled_addon.scss',
    'css/styledelements/styled_alternatives.scss',
    'css/styledelements/styled_container.css',
    'css/styledelements/styled_button.scss',
    'css/styledelements/styled_code_area.scss',
    'css/styledelements/styled_checkbox.css',
    'css/styledelements/styled_pills.scss',
    'css/styledelements/styled_notebook.scss',
    'css/styledelements/styled_form.css',
    'css/styledelements/styled_panel.scss',
    'css/styledelements/styled_numeric_field.scss',
    'css/styledelements/styled_text_field.scss',
    'css/styledelements/styled_text_area.scss',
    'css/styledelements/styled_password_field.scss',
    'css/styledelements/styled_select.scss',
    'css/styledelements/styled_border_layout.css',
    'css/styledelements/styled_horizontal_and_vertical_layout.scss',
    'css/styledelements/styled_file_field.scss',
    'css/styledelements/styled_table.scss',
    'css/styledelements/styled_label_badge.scss',
    'css/styledelements/styled_alert.scss',
    'css/styledelements/styled_rating.scss',
    'css/styledelements/styled_popup_menu.scss',
    'css/styledelements/styled_popover.scss',
    'css/styledelements/styled_tooltip.scss',
    'css/styledelements/styled_expander.scss',
    'css/styledelements/styled_offcanvas_layout.scss',
    'css/styledelements/styled_pagination.scss',
    'css/styledelements/styled_thumbnail.scss',
)

BASE_PATH = os.path.dirname(__file__)
WORKSPACE_BROWSER_FILE = os.path.join(BASE_PATH, 'initial', 'WireCloud_workspace-browser_0.1.4a1.wgt')
INITIAL_HOME_DASHBOARD_FILE = os.path.join(BASE_PATH, 'initial', 'initial_home_dashboard.wgt')
MARKDOWN_VIEWER_FILE = os.path.join(BASE_PATH, 'initial', 'CoNWeT_markdown-viewer_0.1.1.wgt')
MARKDOWN_EDITOR_FILE = os.path.join(BASE_PATH, 'initial', 'CoNWeT_markdown-editor_0.1.0.wgt')
LANDING_DASHBOARD_FILE = os.path.join(BASE_PATH, 'initial', 'WireCloud_landing-dashboard_1.0.wgt')


def get_version_hash():
    return sha1(json.dumps(get_active_features_info(), ensure_ascii=False, sort_keys=True).encode('utf8')).hexdigest()


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

    def __init__(self, app):
        super().__init__(app)

        app.include_router(context_router, prefix="/api/context", tags=["Context"])

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

    def get_platform_context_current_values(self, user: Optional[UserAll], session: Optional[Session]):
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
            # 'language': get_language(),
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
            # 'theme': get_active_theme_name(),
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

    def get_scripts(self, view: str) -> tuple[str, ...]:
        common = SHIM_FILES + (
            'js/wirecloud/BaseRequirements.js',
            'js/common/ComputedStyle.js',
            'js/wirecloud/constants.js',
            'js/StyledElements/Event.js',
            'js/StyledElements/ObjectWithEvents.js',
            'js/wirecloud/core.js',
            'js/wirecloud/UserInterfaceManager.js',
            'js/wirecloud/Task.js',
            'js/wirecloud/io.js',
            'js/wirecloud/ContextManager.js',
            'js/wirecloud/PreferenceDoesNotExistError.js',
            'js/wirecloud/UserPrefDef.js',
            'js/wirecloud/UserPref.js',
            'js/wirecloud/PersistentVariable.js',
            'js/wirecloud/PersistentVariableDef.js',
            'js/wirecloud/PolicyManager.js',
            'js/wirecloud/HistoryManager.js',
            'js/wirecloud/Version.js',
            'js/wirecloud/MashableApplicationComponent.js',
            'js/wirecloud/WidgetMeta.js',
            'js/wirecloud/PreferenceDef.js',
            'js/wirecloud/PlatformPref.js',
            'js/wirecloud/PreferencesDef.js',
            'js/wirecloud/PlatformPreferencesDef.js',
            'js/wirecloud/WorkspacePreferencesDef.js',
            'js/wirecloud/TabPreferencesDef.js',
        ) + STYLED_ELEMENTS_FILES + (
                     'js/wirecloud/WorkspaceTab.js',
                     'js/wirecloud/Workspace.js',
                     'js/wirecloud/Preferences.js',
                     'js/wirecloud/PlatformPreferences.js',
                     'js/wirecloud/PreferenceManager.js',
                     'js/wirecloud/WorkspacePreferences.js',
                     'js/wirecloud/TabPreferences.js',
                     'js/wirecloud/PropertyCommiter.js',
                     'js/wirecloud/LogManager.js',
                     'js/wirecloud/Widget.js',
                     'js/wirecloud/Wiring.js',
                     'js/wirecloud/ui/MACField.js',
                     'js/wirecloud/ui/InputInterfaceFactory.js',
                     'js/wirecloud/ui/ResizeHandle.js',
                     'js/wirecloud/ui/WidgetView.js',
                     'js/wirecloud/ui/WidgetElement.js',
                     'js/wirecloud/ui/WidgetViewMenuItems.js',
                     'js/wirecloud/ui/WidgetViewResizeHandle.js',
                     'js/wirecloud/ui/Draggable.js',
                     'js/wirecloud/ui/Theme.js',
                     'js/wirecloud/WirecloudCatalogue.js',
                     'js/wirecloud/WirecloudCatalogue/ResourceDetails.js',
                     'js/wirecloud/LocalCatalogue.js',
                     'js/wirecloud/WorkspaceCatalogue.js',
                     'js/wirecloud/wiring/Connection.js',
                     'js/wirecloud/wiring/Endpoint.js',
                     'js/wirecloud/wiring/EndpointDoesNotExistError.js',
                     'js/wirecloud/wiring/EndpointTypeError.js',
                     'js/wirecloud/wiring/EndpointValueError.js',
                     'js/wirecloud/wiring/SourceEndpoint.js',
                     'js/wirecloud/wiring/TargetEndpoint.js',
                     'js/wirecloud/wiring/MissingEndpoint.js',
                     'js/wirecloud/wiring/Operator.js',
                     'js/wirecloud/wiring/OperatorMeta.js',
                     'js/wirecloud/wiring/OperatorSourceEndpoint.js',
                     'js/wirecloud/wiring/OperatorTargetEndpoint.js',
                     'js/wirecloud/wiring/WidgetSourceEndpoint.js',
                     'js/wirecloud/wiring/WidgetTargetEndpoint.js',
                     'js/wirecloud/wiring/KeywordSuggestion.js',
                 ) + WIRECLOUD_API_FILES

        if view in ('classic', 'embedded', 'smartphone'):
            scripts = common + (
                'js/wirecloud/ui/WorkspaceListItems.js',
                'js/wirecloud/ui/WorkspaceViewMenuItems.js',
                'js/wirecloud/ui/MACSearch.js',
                'js/wirecloud/ui/ComponentSidebar.js',
                'js/wirecloud/ui/WorkspaceView.js',
                'js/wirecloud/ui/WorkspaceTabView.js',
                'js/wirecloud/ui/WorkspaceTabViewMenuItems.js',
                'js/wirecloud/ui/WorkspaceTabViewDragboard.js',
                'js/wirecloud/ui/MyResourcesView.js',
                'js/wirecloud/ui/MarketplaceView.js',
                'js/wirecloud/ui/CatalogueSearchView.js',
                'js/wirecloud/ui/CatalogueView.js',
                'js/wirecloud/ui/WidgetViewDraggable.js',
                'js/wirecloud/DragboardPosition.js',
                'js/wirecloud/ui/DragboardCursor.js',
                'js/wirecloud/ui/MultiValuedSize.js',
                'js/wirecloud/ui/DragboardLayout.js',
                'js/wirecloud/ui/FreeLayout.js',
                'js/wirecloud/ui/FullDragboardLayout.js',
                'js/wirecloud/ui/ColumnLayout.js',
                'js/wirecloud/ui/SmartColumnLayout.js',
                'js/wirecloud/ui/SidebarLayout.js',
                'js/wirecloud/ui/GridLayout.js',
                'js/wirecloud/MarketManager.js',
                'js/wirecloud/ui/MarketplaceViewMenuItems.js',
                'js/wirecloud/ui/ResourcePainter.js',
                'js/wirecloud/ui/WindowMenu.js',
                'js/wirecloud/ui/WirecloudCatalogue/UploadWindowMenu.js',
                'js/wirecloud/ui/WirecloudCatalogue/ResourceDetailsView.js',
                'js/wirecloud/ui/AlertWindowMenu.js',
                'js/wirecloud/ui/HTMLWindowMenu.js',
                'js/wirecloud/Widget/PreferencesWindowMenu.js',
                'js/wirecloud/ui/MissingDependenciesWindowMenu.js',
                'js/wirecloud/ui/FormWindowMenu.js',
                'js/wirecloud/ui/LogWindowMenu.js',
                'js/wirecloud/ui/EmbedCodeWindowMenu.js',
                'js/wirecloud/ui/SharingWindowMenu.js',
                'js/wirecloud/ui/MACSelectionWindowMenu.js',
                'js/wirecloud/ui/MessageWindowMenu.js',
                'js/wirecloud/ui/NewWorkspaceWindowMenu.js',
                'js/wirecloud/ui/ParametrizeWindowMenu.js',
                'js/wirecloud/ui/PreferencesWindowMenu.js',
                'js/wirecloud/ui/OperatorPreferencesWindowMenu.js',
                'js/wirecloud/ui/PublishWorkspaceWindowMenu.js',
                'js/wirecloud/ui/PublishResourceWindowMenu.js',
                'js/wirecloud/ui/RenameWindowMenu.js',
                'js/wirecloud/ui/UpgradeWindowMenu.js',
                'js/wirecloud/ui/UserTypeahead.js',
                'js/wirecloud/ui/UserGroupTypeahead.js',
            ) + WIRING_EDITOR_FILES + TUTORIAL_FILES

            if view != 'embedded':
                scripts += ('js/wirecloud/ui/WirecloudHeader.js',)

            return scripts

        else:
            return common

    def get_constants(self) -> dict[str, Any]:
        languages = [{'value': lang[0], 'label': lang[1]} for lang in settings.LANGUAGES]
        return {
            'AVAILABLE_LANGUAGES': languages,
        }

    def get_templates(self, view: str) -> list[str]:
        if view == 'classic':
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

        endpoints = (
            AjaxEndpoint(id='IWIDGET_COLLECTION', url=build_url_template(url_patterns['wirecloud.iwidget_collection'], ['workspace_id', 'tab_id'], prefix)),
            AjaxEndpoint(id='IWIDGET_ENTRY', url=build_url_template(url_patterns['wirecloud.iwidget_entry'], ['workspace_id', 'tab_id', 'iwidget_id'], prefix)),
            AjaxEndpoint(id='IWIDGET_PREFERENCES', url=build_url_template(url_patterns['wirecloud.iwidget_preferences'], ['workspace_id', 'tab_id', 'iwidget_id'], prefix)),
            AjaxEndpoint(id='IWIDGET_PROPERTIES', url=build_url_template(url_patterns['wirecloud.iwidget_properties'], ['workspace_id', 'tab_id', 'iwidget_id'], prefix)),
            AjaxEndpoint(id='LOCAL_REPOSITORY', url=build_url_template(url_patterns['wirecloud.root'], [], prefix)),
            AjaxEndpoint(id='LOCAL_RESOURCE_COLLECTION', url=build_url_template(url_patterns['wirecloud.resource_collection'], ['vendor', 'name', 'version'], prefix)),
            AjaxEndpoint(id='LOCAL_UNVERSIONED_RESOURCE_ENTRY', url=build_url_template(url_patterns['wirecloud.unversioned_resource_entry'], ['vendor', 'name'], prefix)),
            AjaxEndpoint(id='LOGIN_API', url=build_url_template(url_patterns['wirecloud.login'], [], prefix)),
            AjaxEndpoint(id='LOGIN_VIEW', url=build_url_template(url_patterns['login'], [], prefix)),
            AjaxEndpoint(id='LOGOUT_VIEW', url=build_url_template(url_patterns['logout'], [], prefix)),
            AjaxEndpoint(id='MAC_BASE_URL', url=build_url_template(url_patterns['wirecloud.showcase_media'], ['vendor', 'name', 'version', 'file_path'], prefix)),
            AjaxEndpoint(id='MARKET_COLLECTION', url=build_url_template(url_patterns['wirecloud.market_collection'], [], prefix)),
            AjaxEndpoint(id='MARKET_ENTRY', url=build_url_template(url_patterns['wirecloud.market_entry'], ['user', 'market'], prefix)),
            AjaxEndpoint(id='MISSING_WIDGET_CODE_ENTRY', url=build_url_template(url_patterns['wirecloud.missing_widget_code_entry'], [], prefix)),
            AjaxEndpoint(id='OPERATOR_ENTRY', url=build_url_template(url_patterns['wirecloud.operator_entry'], ['vendor', 'name', 'version'], prefix)),
            # AjaxEndpoint(id='PROXY', url=build_url_template(url_patterns['wirecloud|proxy'], ['protocol', 'domain', 'path'], prefix)),
            AjaxEndpoint(id='PUBLISH_ON_OTHER_MARKETPLACE', url=build_url_template(url_patterns['wirecloud.publish_on_other_marketplace'], [], prefix)),
            AjaxEndpoint(id='ROOT_URL', url=build_url_template(url_patterns['wirecloud.root'], [], prefix)),
            AjaxEndpoint(id='SEARCH_SERVICE', url=build_url_template(url_patterns['wirecloud.search_service'], [], prefix)),
            AjaxEndpoint(id='SWITCH_USER_SERVICE', url=build_url_template(url_patterns['wirecloud.switch_user_service'], [], prefix)),
            AjaxEndpoint(id='TAB_COLLECTION', url=build_url_template(url_patterns['wirecloud.tab_collection'], ['workspace_id'], prefix)),
            AjaxEndpoint(id='TAB_ENTRY', url=build_url_template(url_patterns['wirecloud.tab_entry'], ['workspace_id', 'tab_id'], prefix)),
            AjaxEndpoint(id='TAB_PREFERENCES', url=build_url_template(url_patterns['wirecloud.tab_preferences'], ['workspace_id', 'tab_id'], prefix)),
            AjaxEndpoint(id='THEME_ENTRY', url=build_url_template(url_patterns['wirecloud.theme_entry'], ['name'], prefix)),
            AjaxEndpoint(id='WIRING_ENTRY', url=build_url_template(url_patterns['wirecloud.wiring_entry'], ['workspace_id'], prefix)),
            AjaxEndpoint(id='OPERATOR_VARIABLES_ENTRY', url=build_url_template(url_patterns['wirecloud.operator_variables'], ['workspace_id', 'operator_id'], prefix)),
            AjaxEndpoint(id='WORKSPACE_COLLECTION', url=build_url_template(url_patterns['wirecloud.workspace_collection'], [], prefix)),
            AjaxEndpoint(id='WORKSPACE_ENTRY_OWNER_NAME', url=build_url_template(url_patterns['wirecloud.workspace_entry_owner_name'], ['owner', 'name'], prefix)),
            AjaxEndpoint(id='WORKSPACE_ENTRY', url=build_url_template(url_patterns['wirecloud.workspace_entry'], ['workspace_id'], prefix)),
            AjaxEndpoint(id='WORKSPACE_MERGE', url=build_url_template(url_patterns['wirecloud.workspace_merge'], ['to_ws_id'], prefix)),
            AjaxEndpoint(id='WORKSPACE_PREFERENCES', url=build_url_template(url_patterns['wirecloud.workspace_preferences'], ['workspace_id'], prefix)),
            AjaxEndpoint(id='WORKSPACE_PUBLISH', url=build_url_template(url_patterns['wirecloud.workspace_publish'], ['workspace_id'], prefix)),
            AjaxEndpoint(id='WORKSPACE_RESOURCE_COLLECTION', url=build_url_template(url_patterns['wirecloud.workspace_resource_collection'], ['workspace_id'], prefix)),
            AjaxEndpoint(id='WORKSPACE_VIEW', url=build_url_template(url_patterns['wirecloud.workspace_view'], ['owner', 'name'], prefix)),
        )

        return endpoints

    def get_platform_css(self, view: str) -> tuple[str, ...]:
        common = BASE_CSS + STYLED_ELEMENTS_CSS

        if view in ('classic', 'smartphone'):
            return common + PLATFORM_CORE_CSS + WORKSPACE_CSS + CLASSIC_CORE_CSS + WIRING_EDITOR_CSS + CATALOGUE_CSS + TUTORIAL_CSS
        elif view == 'embedded':
            return common + PLATFORM_CORE_CSS + WORKSPACE_CSS
        else:
            return common

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
        return ('wirecloud.proxy.processors.SecureDataProcessor',)
