# -*- coding: utf-8 -*-

import sys
from types import SimpleNamespace

import pytest

from wirecloud.platform import plugins
from src import settings as project_settings


@pytest.fixture(autouse=True)
def _clear_platform_plugin_cache():
    plugins.clear_cache()
    plugins._wirecloud_config_validators = None
    plugins._wirecloud_idm_get_authorization_url_functions = None
    plugins._wirecloud_idm_get_token_functions = None
    plugins._wirecloud_idm_get_user_functions = None
    plugins._wirecloud_idm_backchannel_logout_functions = None
    plugins._wirecloud_templates = {}
    yield
    plugins.clear_cache()
    plugins._wirecloud_config_validators = None
    plugins._wirecloud_idm_get_authorization_url_functions = None
    plugins._wirecloud_idm_get_token_functions = None
    plugins._wirecloud_idm_get_user_functions = None
    plugins._wirecloud_idm_backchannel_logout_functions = None
    plugins._wirecloud_templates = {}


class _PluginA(plugins.WirecloudPlugin):
    features = {"a": "1.0.0"}

    def get_urls(self):
        return {"a": plugins.URLTemplate(urlpattern="/a", defaults={})}

    def get_ajax_endpoints(self, _view, _request):
        return (plugins.AjaxEndpoint(id="A", url="/a"),)

    def get_platform_preferences(self):
        return [SimpleNamespace(model_dump=lambda: {"name": "p"})]

    def get_workspace_preferences(self):
        return [SimpleNamespace(model_dump=lambda: {"name": "wp"})]

    def get_tab_preferences(self):
        return [SimpleNamespace(model_dump=lambda: {"name": "tp"})]

    def get_constants(self):
        return {"X": 1}

    def get_widget_api_extensions(self, _view, _features):
        return ["w.js"]

    def get_operator_api_extensions(self, _view, _features):
        return ["o.js"]

    def get_api_auth_backends(self):
        return {"token": lambda: "ok"}

    def get_template_context_processors(self, _request):
        return {"a": 1}

    def get_proxy_processors(self):
        return ("wirecloud.platform.test_processors.RequestResponseProcessor",)

    def get_config_validators(self):
        return (lambda *_args, **_kwargs: None,)

    def get_idm_get_authorization_url_functions(self):
        return {"idm_auth": lambda: "auth"}

    def get_idm_get_token_functions(self):
        return {"idm_token": lambda: "token"}

    def get_idm_get_user_functions(self):
        return {"idm_user": lambda: "user"}

    def get_idm_backchannel_logout_functions(self):
        return {"idm_logout": lambda: "logout"}

    def get_management_commands(self, _subparsers):
        return {"cmd-a": lambda: "a"}

    def get_openapi_extra_schemas(self):
        return {"SchemaA": {"type": "object"}}

    def get_templates(self, view):
        return [f"{view}-a.html"]


class _PluginB(plugins.WirecloudPlugin):
    features = {"b": "2.0.0"}

    def get_urls(self):
        return {"b": plugins.URLTemplate(urlpattern="/b", defaults={"x": "1"})}

    def get_ajax_endpoints(self, _view, _request):
        return (plugins.AjaxEndpoint(id="B", url="/b"),)

    def get_template_context_processors(self, _request):
        return {"b": 2}

    def get_api_auth_backends(self):
        return {}

    def get_management_commands(self, _subparsers):
        return {"cmd-b": lambda: "b"}

    def get_openapi_extra_schemas(self):
        return {"SchemaB": {"type": "string"}}

    def get_templates(self, view):
        return [f"{view}-b.html"]


class _PluginFeatureCollisionA(plugins.WirecloudPlugin):
    features = {"dup": "1.0"}


class _PluginFeatureCollisionB(plugins.WirecloudPlugin):
    features = {"dup": "2.0"}


class _RequestOnlyProcessor:
    def process_request(self, _request_data):
        return _request_data


class _RequestResponseProcessor:
    def process_request(self, _request_data):
        return _request_data

    def process_response(self, _response_data):
        return _response_data


class _NoSuchEntry:
    pass


class _FakeCorePlugin(plugins.WirecloudPlugin):
    features = {"core": "0.0.1"}


def test_wirecloud_plugin_default_behaviour():
    plugin = plugins.WirecloudPlugin(None)
    assert plugin.get_market_classes() == {}
    assert plugin.get_features() == {}
    assert plugin.get_platform_context_definitions() == {}
    assert plugin.get_workspace_context_definitions() == {}
    assert plugin.get_workspace_context_current_values(None, None) == {}
    assert plugin.get_platform_preferences() == []
    assert plugin.get_tab_preferences() == []
    assert plugin.get_workspace_preferences() == []
    assert plugin.get_templates("classic") == []
    assert plugin.get_urls() == ()
    assert plugin.get_constants() == {}
    assert plugin.get_ajax_endpoints("classic", None) == ()
    assert plugin.get_widget_api_extensions("classic", []) == []
    assert plugin.get_operator_api_extensions("classic", []) == []
    assert plugin.get_proxy_processors() == ()
    assert plugin.get_template_context_processors(None) == {}
    assert plugin.get_openapi_extra_schemas() == {}
    assert plugin.get_config_validators() == ()
    assert plugin.get_idm_get_authorization_url_functions() == {}
    assert plugin.get_idm_get_token_functions() == {}
    assert plugin.get_idm_get_user_functions() == {}
    assert plugin.get_idm_backchannel_logout_functions() == {}
    assert plugin.get_management_commands(None) == {}


async def test_wirecloud_plugin_default_async_behaviour():
    plugin = plugins.WirecloudPlugin(None)
    assert await plugin.get_platform_context_current_values(None, None, None, None) == {}
    assert await plugin.populate(None, None) is False


async def test_get_plugins_and_feature_caching(monkeypatch):
    monkeypatch.setattr(plugins, "find_wirecloud_plugins", lambda: [_PluginA, _PluginB])
    monkeypatch.setattr(project_settings, "WIRECLOUD_PLUGINS", None, raising=False)
    monkeypatch.setattr(project_settings, "INSTALLED_APPS", [], raising=False)

    loaded = plugins.get_plugins()
    assert len(loaded) == 2
    assert plugins.get_active_features()["a"]["version"] == "1.0.0"
    assert plugins.get_active_features_info() == {"a": "1.0.0", "b": "2.0.0"}
    assert plugins.get_plugins() is loaded

    plugins.clear_cache()
    monkeypatch.setattr(project_settings, "WIRECLOUD_PLUGINS", [_PluginFeatureCollisionA, _PluginFeatureCollisionB], raising=False)
    with pytest.raises(plugins.ImproperlyConfigured, match="Feature already declared"):
        plugins.get_plugins()

    plugins.clear_cache()
    monkeypatch.setattr(project_settings, "WIRECLOUD_PLUGINS", [_NoSuchEntry()], raising=False)
    with pytest.raises(plugins.ImproperlyConfigured, match="Invalid plugin entry"):
        plugins.get_plugins()


def test_find_wirecloud_plugins_ignores_missing_modules(monkeypatch):
    monkeypatch.setattr(project_settings, "INSTALLED_APPS", ["wirecloud.platform", "app_without_plugins"], raising=False)
    found = plugins.find_wirecloud_plugins()
    assert found == []


def test_find_wirecloud_plugins_with_import_error_and_discovery(monkeypatch):
    monkeypatch.setattr(project_settings, "INSTALLED_APPS", ["app_error", "app_ok"], raising=False)

    fake_mod = SimpleNamespace(
        NotAPlugin=object,
        PluginA=type("PluginA", (plugins.WirecloudPlugin,), {}),
        PluginB=type("PluginB", (plugins.WirecloudPlugin,), {}),
    )

    errors = []

    def _import(module_name):
        if module_name == "app_error.plugins":
            raise ImportError("boom-error")
        return fake_mod

    monkeypatch.setattr(plugins, "import_module", _import)
    monkeypatch.setattr(plugins.logger, "error", lambda msg, **kwargs: errors.append(msg))
    found = plugins.find_wirecloud_plugins()
    assert len(found) == 2
    assert any("Error importing app_error.plugins" in msg for msg in errors)


def test_find_wirecloud_plugins_ignored_import_error_message(monkeypatch):
    monkeypatch.setattr(project_settings, "INSTALLED_APPS", ["app_ignored"], raising=False)

    def _import(_module_name):
        raise ImportError("No module named app_ignored.plugins")

    errors = []
    monkeypatch.setattr(plugins, "import_module", _import)
    monkeypatch.setattr(plugins.logger, "error", lambda msg, **kwargs: errors.append(msg))
    assert plugins.find_wirecloud_plugins() == []
    assert errors == []


def test_get_plugins_string_entries_and_platform_core(monkeypatch):
    plugins.clear_cache()
    fake_core_mod = SimpleNamespace(WirecloudCorePlugin=_FakeCorePlugin)
    monkeypatch.setitem(sys.modules, "wirecloud.platform.core.plugins", fake_core_mod)
    monkeypatch.setattr(project_settings, "INSTALLED_APPS", ["wirecloud.platform"], raising=False)
    monkeypatch.setattr(project_settings, "WIRECLOUD_PLUGINS", ["wirecloud.platform.plugins.WirecloudPlugin"], raising=False)

    loaded = plugins.get_plugins(app=SimpleNamespace())
    assert len(loaded) == 2
    assert "core" in plugins.get_active_features()

    plugins.clear_cache()
    monkeypatch.setattr(project_settings, "WIRECLOUD_PLUGINS", ["missing.module.Plugin"], raising=False)
    with pytest.raises(plugins.ImproperlyConfigured, match="Error importing wirecloud plugin module"):
        plugins.get_plugins()

    plugins.clear_cache()
    monkeypatch.setattr(project_settings, "WIRECLOUD_PLUGINS", ["wirecloud.platform.plugins.MissingClass"], raising=False)
    with pytest.raises(plugins.ImproperlyConfigured, match='does not define'):
        plugins.get_plugins()


def test_get_active_features_calls_get_plugins_when_cache_is_empty(monkeypatch):
    plugins.clear_cache()
    monkeypatch.setattr(plugins, "get_plugins", lambda _app=None: tuple())
    monkeypatch.setattr(plugins, "_wirecloud_features", {"x": {"module": "m", "version": "1"}})
    assert plugins.get_active_features() == {"x": {"module": "m", "version": "1"}}

    monkeypatch.setattr(plugins, "_wirecloud_features_info", {"cached": "1"})
    assert plugins.get_active_features_info() == {"cached": "1"}


async def test_aggregators_and_cached_helpers(monkeypatch):
    monkeypatch.setattr(plugins, "get_plugins", lambda _app=None: (_PluginA(None), _PluginB(None)))

    urls = plugins.get_plugin_urls()
    assert "a" in urls and "b" in urls

    endpoints = plugins.get_wirecloud_ajax_endpoints("classic", None)
    assert [e.id for e in endpoints] == ["A", "B"]

    constants = plugins.get_constants()
    values = {item["key"]: item["value"] for item in constants}
    assert "X" in values
    assert "PLATFORM_PREFERENCES" in values
    assert "WORKSPACE_PREFERENCES" in values
    assert "TAB_PREFERENCES" in values

    assert plugins.get_widget_api_extensions("classic", []) == ["w.js"]
    assert plugins.get_operator_api_extensions("classic", []) == ["o.js"]

    assert "token" in plugins.get_api_auth_backends()
    assert plugins.get_api_auth_backends()["token"]() == "ok"
    assert plugins.get_template_context(SimpleNamespace()) == {"a": 1, "b": 2}

    assert plugins.get_config_validators() != ()
    assert plugins.get_config_validators() is plugins.get_config_validators()
    assert plugins.get_idm_get_authorization_url_functions()["idm_auth"]() == "auth"
    assert plugins.get_idm_get_authorization_url_functions() is plugins.get_idm_get_authorization_url_functions()
    assert plugins.get_idm_get_token_functions()["idm_token"]() == "token"
    assert plugins.get_idm_get_token_functions() is plugins.get_idm_get_token_functions()
    assert plugins.get_idm_get_user_functions()["idm_user"]() == "user"
    assert plugins.get_idm_get_user_functions() is plugins.get_idm_get_user_functions()
    assert plugins.get_idm_backchannel_logout_functions()["idm_logout"]() == "logout"
    assert plugins.get_idm_backchannel_logout_functions() is plugins.get_idm_backchannel_logout_functions()

    commands = plugins.get_management_commands("subparsers")
    assert "cmd-a" in commands and "cmd-b" in commands

    schemas = plugins.get_extra_openapi_schemas()
    assert "SchemaA" in schemas and "SchemaB" in schemas

    first = plugins.get_templates("classic")
    second = plugins.get_templates("classic")
    assert first == ["classic-a.html", "classic-b.html"]
    assert second is first


async def test_proxy_processors_and_url_template_builder(monkeypatch):
    monkeypatch.setattr(plugins, "get_plugins", lambda _app=None: (_PluginA(None),))

    processor_module = SimpleNamespace(
        RequestOnlyProcessor=_RequestOnlyProcessor,
        RequestResponseProcessor=_RequestResponseProcessor,
    )
    monkeypatch.setattr(plugins, "import_module", lambda _name: processor_module)

    processors = plugins.get_proxy_processors()
    assert len(processors) == 1
    assert len(plugins.get_request_proxy_processors()) == 1
    assert len(plugins.get_response_proxy_processors()) == 1
    assert plugins.get_proxy_processors() is processors

    template = plugins.build_url_template(
        plugins.URLTemplate(urlpattern="/x/{id}/{slug:path}", defaults={"id": "1"}),
        kwargs=["slug"],
        prefix="/api/",
    )
    assert template == "/api/x/1/%(slug)s"
    assert (
        plugins.build_url_template(
            plugins.URLTemplate(urlpattern="/x/{id}", defaults={"id": "1"}),
            kwargs=None,
            prefix=None,
        )
        == "/x/1"
    )
    assert (
        plugins.build_url_template(
            plugins.URLTemplate(urlpattern="/x/{id}", defaults={"id": "1"}),
            kwargs=["id"],
            prefix="api",
        )
        == "/x/%(id)s"
    )

    plugins.clear_cache()
    monkeypatch.setattr(plugins, "get_plugins", lambda _app=None: (SimpleNamespace(get_proxy_processors=lambda: ("pkg.Missing",)),))
    monkeypatch.setattr(plugins, "import_module", lambda _name: SimpleNamespace())
    with pytest.raises(plugins.ImproperlyConfigured, match="does not define"):
        plugins.get_proxy_processors()

    plugins.clear_cache()
    monkeypatch.setattr(plugins, "get_plugins", lambda _app=None: (SimpleNamespace(get_proxy_processors=lambda: ("pkg.Cls",)),))

    def _raise_import_error(_name):
        raise ImportError("boom")

    monkeypatch.setattr(plugins, "import_module", _raise_import_error)
    with pytest.raises(plugins.ImproperlyConfigured, match="Error importing proxy processor module"):
        plugins.get_proxy_processors()

    plugins.clear_cache()
    monkeypatch.setattr(plugins, "_wirecloud_proxy_processors", tuple())
    monkeypatch.setattr(plugins, "get_proxy_processors", lambda: (_ for _ in ()).throw(RuntimeError("should not happen")))
    assert plugins.get_request_proxy_processors() == ()
    assert plugins.get_response_proxy_processors() == ()

    plugins.clear_cache()
    monkeypatch.setattr(plugins, "get_proxy_processors", lambda: tuple())
    assert plugins.get_request_proxy_processors() == ()
    plugins.clear_cache()
    monkeypatch.setattr(plugins, "get_proxy_processors", lambda: tuple())
    assert plugins.get_response_proxy_processors() == ()
