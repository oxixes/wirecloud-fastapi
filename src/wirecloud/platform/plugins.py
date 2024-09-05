# -*- coding: utf-8 -*-

# Copyright (c) 2011-2016 CoNWeT Lab., Universidad Politécnica de Madrid

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

# TODO Define types for the following methods

from importlib import import_module
from typing import Optional, Any
from pydantic import BaseModel
from fastapi import FastAPI
import inspect
import logging
import json

from src.wirecloud.commons.utils.encoding import LazyEncoderXHTML
from src.wirecloud.platform.context.schemas import BaseContextKey, WorkspaceContextKey
from src.wirecloud.platform.preferences.schemas import PreferenceKey, TabPreferenceKey
from src.wirecloud.commons.auth.schemas import UserAll, Session

# Get an instance of a logger
logger = logging.getLogger(__name__)

_wirecloud_plugins = None
_wirecloud_features = None
_wirecloud_features_info = None
_wirecloud_proxy_processors = None
_wirecloud_request_proxy_processors = []
_wirecloud_response_proxy_processors = []
_wirecloud_constants = None
_wirecloud_api_auth_backends = None
_wirecloud_tab_preferences = None
_wirecloud_workspace_preferences = None


class URLTemplate(BaseModel):
    urlpattern: str
    defaults: dict[str, str]


class AjaxEndpoint(BaseModel):
    id: str
    url: str


class ImproperlyConfigured(Exception):
    pass


def find_wirecloud_plugins():
    from src import settings

    modules = []

    for app in getattr(settings, 'INSTALLED_APPS', []):
        if app == 'wirecloud.platform':
            continue

        plugins_module = 'src.%s.plugins' % app
        try:
            mod = import_module(plugins_module)
        except (NameError, ImportError, SyntaxError) as exc:
            error_message = str(exc)
            if error_message not in (
                    "No module named plugins", "No module named " + plugins_module,
                    "No module named '" + plugins_module + "'"):
                logger.error(
                    "Error importing %(module)s (%(error_message)s). Any WireCloud plugin available through the %(app)s app will be ignored" % {
                        "module": plugins_module, "error_message": error_message, "app": app})
            continue

        mod_plugins = [cls for name, cls in mod.__dict__.items() if
                       inspect.isclass(cls) and cls != WirecloudPlugin and issubclass(cls, WirecloudPlugin)]
        modules += mod_plugins

    return modules


def get_plugins(app: Optional[FastAPI] = None):
    from src import settings
    global _wirecloud_plugins
    global _wirecloud_features

    if _wirecloud_plugins is None:
        modules = getattr(settings, 'WIRECLOUD_PLUGINS', None)
        if modules is None:
            modules = find_wirecloud_plugins()

        plugins = []
        features = {}

        def add_plugin(module, plugin):
            plugin_features = plugin.get_features()
            for feature_name in plugin_features:
                if feature_name in features:
                    raise ImproperlyConfigured(
                        'Feature already declared by wirecloud plugin %s' % features[feature_name]['module'])

                features[feature_name] = {
                    'module': module,
                    'version': plugin_features[feature_name],
                }

            plugins.append(plugin)

        if 'wirecloud.platform' in getattr(settings, 'INSTALLED_APPS', []):
            from src.wirecloud.platform.core.plugins import WirecloudCorePlugin
            add_plugin('src.wirecloud.platform.WirecloudCorePlugin', WirecloudCorePlugin(app))

        for entry in modules:
            if isinstance(entry, str):
                i = entry.rfind('.')
                module, attr = entry[:i], entry[i + 1:]
                try:
                    mod = import_module(module)
                except ImportError as e:
                    raise ImproperlyConfigured('Error importing wirecloud plugin module %s: "%s"' % (module, e))

                try:
                    plugin = getattr(mod, attr)(app)
                except AttributeError:
                    raise ImproperlyConfigured(
                        'Module "%s" does not define a "%s" instanciable Wirecloud plugin' % (module, attr))
            elif inspect.isclass(entry):
                plugin = entry(app)
            else:
                raise ImproperlyConfigured('Error importing wirecloud plugin. Invalid plugin entry: "%s"' % entry)

            add_plugin(plugin.__module__, plugin)

        _wirecloud_plugins = tuple(plugins)
        _wirecloud_features = features

    return _wirecloud_plugins


def get_active_features():
    global _wirecloud_plugins
    global _wirecloud_features

    if _wirecloud_plugins is None:
        get_plugins()

    return _wirecloud_features


def get_active_features_info():
    global _wirecloud_features_info

    if _wirecloud_features_info is None:
        info = get_active_features()
        features_info = {}
        for feature_name in info:
            features_info[feature_name] = info[feature_name]['version']

        _wirecloud_features_info = features_info

    return _wirecloud_features_info


def clear_cache():
    global _wirecloud_plugins
    global _wirecloud_features
    global _wirecloud_features_info
    global _wirecloud_proxy_processors
    global _wirecloud_request_proxy_processors
    global _wirecloud_response_proxy_processors
    global _wirecloud_constants
    global _wirecloud_api_auth_backends
    global _wirecloud_tab_preferences
    global _wirecloud_workspace_preferences

    _wirecloud_plugins = None
    _wirecloud_features = None
    _wirecloud_features_info = None
    _wirecloud_proxy_processors = None
    _wirecloud_request_proxy_processors = []
    _wirecloud_response_proxy_processors = []
    _wirecloud_constants = None
    _wirecloud_api_auth_backends = None
    _wirecloud_tab_preferences = None
    _wirecloud_workspace_preferences = None


def get_plugin_urls() -> dict[str, URLTemplate]:
    plugins = get_plugins()

    urls = {}

    for plugin in plugins:
        urls.update(plugin.get_urls())

    return urls


def get_wirecloud_ajax_endpoints(view: str, prefix: str) -> list[AjaxEndpoint]:
    plugins = get_plugins()
    endpoints = []

    for plugin in plugins:
        endpoints += plugin.get_ajax_endpoints(view, prefix)

    return endpoints


def get_extra_javascripts(view: str) -> list[str]:
    plugins = get_plugins()
    files = []

    for plugin in plugins:
        files += plugin.get_scripts(view)

    return files


def get_tab_preferences() -> list[TabPreferenceKey]:
    global _wirecloud_tab_preferences

    if _wirecloud_tab_preferences is None:
        plugins = get_plugins()
        preferences = []

        for plugin in plugins:
            preferences += plugin.get_tab_preferences()

        _wirecloud_tab_preferences = preferences

    return _wirecloud_tab_preferences


def get_workspace_preferences() -> list[PreferenceKey]:
    global _wirecloud_workspace_preferences

    if _wirecloud_workspace_preferences is None:
        plugins = get_plugins()
        preferences = []

        for plugin in plugins:
            preferences += plugin.get_workspace_preferences()

        _wirecloud_workspace_preferences = preferences

    return _wirecloud_workspace_preferences


def get_constants() -> list[dict[str, str]]:
    global _wirecloud_constants

    if _wirecloud_constants is None:
        plugins = get_plugins()
        constants_dict = {}
        for plugin in plugins:
            constants_dict.update(plugin.get_constants())

        constants_dict['WORKSPACE_PREFERENCES'] = get_workspace_preferences()
        constants_dict['TAB_PREFERENCES'] = get_tab_preferences()

        constants = []
        for constant_key in constants_dict:
            constants.append(
                {'key': constant_key, 'value': json.dumps(constants_dict[constant_key], cls=LazyEncoderXHTML)})

        _wirecloud_constants = constants

    return _wirecloud_constants


def get_widget_api_extensions(view: str, features: list[str]) -> list[str]:
    plugins = get_plugins()
    files = []

    for plugin in plugins:
        files += plugin.get_widget_api_extensions(view, features)

    return files


def get_operator_api_extensions(view: str, features: list[str]) -> list[str]:
    plugins = get_plugins()
    files = []

    for plugin in plugins:
        files += plugin.get_operator_api_extensions(view, features)

    return files


def get_platform_css(view: str) -> tuple[str, ...]:
    plugins = get_plugins()
    files = []

    for plugin in plugins:
        files += plugin.get_platform_css(view)

    return tuple(files)


def get_api_auth_backends():
    global _wirecloud_api_auth_backends

    if _wirecloud_api_auth_backends is None:
        plugins = get_plugins()

        _wirecloud_api_auth_backends = {}
        for plugin in plugins:
            _wirecloud_api_auth_backends.update(plugin.get_api_auth_backends())

    return _wirecloud_api_auth_backends


def get_proxy_processors():
    global _wirecloud_proxy_processors
    global _wirecloud_request_proxy_processors
    global _wirecloud_response_proxy_processors

    if _wirecloud_proxy_processors is None:
        plugins = get_plugins()
        modules = []

        for plugin in plugins:
            modules += plugin.get_proxy_processors()

        processors = []
        for path in modules:
            i = path.rfind('.')
            module, attr = path[:i], path[i + 1:]
            try:
                mod = import_module(module)
            except ImportError as e:
                raise ImproperlyConfigured('Error importing proxy processor module %s: "%s"' % (module, e))

            try:
                processor = getattr(mod, attr)()
            except AttributeError:
                raise ImproperlyConfigured(
                    'Module "%s" does not define a "%s" instanciable processor processor' % (module, attr))

            if hasattr(processor, 'process_request'):
                _wirecloud_request_proxy_processors.append(processor)
            if hasattr(processor, 'process_response'):
                _wirecloud_response_proxy_processors.insert(0, processor)

            processors.append(processor)

        _wirecloud_proxy_processors = tuple(processors)
        _wirecloud_request_proxy_processors = tuple(_wirecloud_request_proxy_processors)
        _wirecloud_response_proxy_processors = tuple(_wirecloud_response_proxy_processors)

    return _wirecloud_proxy_processors


def get_request_proxy_processors():
    if _wirecloud_proxy_processors is None:
        get_proxy_processors()

    return _wirecloud_request_proxy_processors


def get_response_proxy_processors():
    if _wirecloud_proxy_processors is None:
        get_proxy_processors()

    return _wirecloud_response_proxy_processors


def build_url_template(urltemplate: URLTemplate, kwargs: Optional[list[str]] = None, prefix: Optional[str] = None) -> str:
    if kwargs is None:
        kwargs = []

    if prefix is not None and prefix[-1] == '/':
        prefix = prefix[:-1]
    else:
        prefix = ''

    template = prefix + urltemplate.urlpattern

    # Replace defaults of the non-karg arguments
    for arg in urltemplate.defaults:
        if arg not in kwargs:
            template = template.replace('{' + arg + '}', str(urltemplate.defaults[arg]))

    template.replace('{', '%(').replace('}', ')s')

    return template


def get_extra_openapi_schemas() -> dict[str, dict[str, Any]]:
    plugins = get_plugins()
    schemas = {}

    for plugin in plugins:
        schemas.update(plugin.get_openapi_extra_schemas())

    return schemas


class WirecloudPlugin:
    features: dict[str, str] = {}
    urls: dict[str, URLTemplate] = ()

    def __init__(self, app: FastAPI):
        self.app = app

    def get_market_classes(self):
        return {}

    def get_features(self) -> dict[str, str]:
        return self.features

    def get_platform_context_definitions(self) -> dict[str, BaseContextKey]:
        return {}

    def get_platform_context_current_values(self, user: Optional[UserAll], session: Optional[Session]):
        return {}

    def get_tab_preferences(self) -> list[TabPreferenceKey]:
        return []

    def get_workspace_context_definitions(self) -> dict[str, WorkspaceContextKey]:
        return {}

    def get_workspace_context_current_values(self, workspace, user):
        return {}

    def get_workspace_preferences(self) -> list[PreferenceKey]:
        return []

    def get_scripts(self, view: str) -> tuple[str, ...]:
        return ()

    def get_templates(self, view: str) -> list[str]:
        return []

    def get_urls(self) -> dict[str, URLTemplate]:
        return self.urls

    def get_constants(self) -> dict[str, Any]:
        return {}

    def get_ajax_endpoints(self, view: str, prefix: str) -> tuple[AjaxEndpoint, ...]:
        return ()

    def get_widget_api_extensions(self, view: str, features: list[str]) -> list[str]:
        return []

    def get_operator_api_extensions(self, view: str, features: list[str]) -> list[str]:
        return []

    def get_platform_css(self, view: str) -> tuple[str, ...]:
        return ()

    def get_proxy_processors(self) -> tuple[str, ...]:
        return ()

    def get_django_template_context_processors(self):
        return {}

    def get_api_auth_backends(self):
        return {}

    def get_openapi_extra_schemas(self) -> dict[str, dict[str, Any]]:
        return {}

    def populate(self, wirecloud_user, log):
        return False
