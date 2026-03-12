# -*- coding: utf-8 -*-

import pytest

from wirecloud import settings_validator


def _valid_settings_dict(tmp_path):
    base = tmp_path / "wirecloud-base"
    base.mkdir()
    return {
        "DEBUG": False,
        "BASEDIR": str(base),
        "ALLOW_ANONYMOUS_ACCESS": False,
        "INSTALLED_APPS": ["wirecloud.commons", "wirecloud.catalogue", "wirecloud.platform"],
        "DATABASE": {
            "DRIVER": "mongodb",
            "NAME": "wirecloud",
            "HOST": "localhost",
            "PORT": "",
            "USER": "",
            "PASSWORD": "",
            "USE_TRANSACTIONS": True,
        },
        "ELASTICSEARCH": {"HOST": "localhost", "PORT": 9200, "SECURE": False, "USER": "", "PASSWORD": ""},
        "LANGUAGES": [("en", "English"), ("es", "Spanish")],
        "DEFAULT_LANGUAGE": "en",
        "JWT_KEY": "x" * 32,
        "SESSION_AGE": 100,
        "SECRET_KEY": "y" * 32,
        "OID_CONNECT_ENABLED": False,
        "WIRECLOUD_HTTPS_VERIFY": True,
    }


def _apply_settings(monkeypatch, values):
    for key, value in values.items():
        monkeypatch.setattr(settings_validator.settings, key, value, raising=False)


def test_set_default_if_missing(monkeypatch):
    if hasattr(settings_validator.settings, "TMP_ATTR"):
        delattr(settings_validator.settings, "TMP_ATTR")
    settings_validator._set_default_if_missing("TMP_ATTR", 1)
    assert settings_validator.settings.TMP_ATTR == 1
    settings_validator._set_default_if_missing("TMP_ATTR", 2)
    assert settings_validator.settings.TMP_ATTR == 1


def test_validate_and_set_defaults_happy_path_and_warnings(monkeypatch, tmp_path):
    values = _valid_settings_dict(tmp_path)
    values["JWT_KEY"] = "short"
    values["SECRET_KEY"] = "short"
    _apply_settings(monkeypatch, values)
    monkeypatch.setattr(settings_validator.logger, "warning", lambda *_args, **_kwargs: None)

    settings_validator._validate_and_set_defaults()
    assert settings_validator.settings.CACHE_DIR.endswith("cache")
    assert settings_validator.settings.DATABASE["USE_TRANSACTIONS"] is True


def test_validate_and_set_defaults_optional_defaults_and_valid_oidc(monkeypatch, tmp_path):
    values = _valid_settings_dict(tmp_path)
    values["DATABASE"].pop("PORT")
    values["DATABASE"].pop("USER")
    values["DATABASE"].pop("PASSWORD")
    values["DATABASE"].pop("USE_TRANSACTIONS")
    values["ELASTICSEARCH"].pop("USER")
    values["ELASTICSEARCH"].pop("PASSWORD")
    values["ELASTICSEARCH"].pop("SECURE")
    values["OID_CONNECT_ENABLED"] = True
    values["OID_CONNECT_CLIENT_ID"] = "cid"
    values["OID_CONNECT_CLIENT_SECRET"] = "secret"
    values["OID_CONNECT_PLUGIN"] = "platform"
    values["OID_CONNECT_FULLY_SYNC_GROUPS"] = False
    values["OID_CONNECT_BACKCHANNEL_LOGOUT"] = False
    values["cache"] = object()
    _apply_settings(monkeypatch, values)
    settings_validator._validate_and_set_defaults()
    assert settings_validator.settings.DATABASE["PORT"] == ""
    assert settings_validator.settings.ELASTICSEARCH["SECURE"] is False


@pytest.mark.parametrize(
    "mutator, message",
    [
        (lambda v: v.update({"DEBUG": "x"}), "DEBUG must be a boolean"),
        (lambda v: v.update({"BASEDIR": ""}), "BASEDIR is required"),
        (lambda v: v.update({"BASEDIR": 1}), "BASEDIR must be a string"),
        (lambda v: v.update({"BASEDIR": "/path/does/not/exist"}), "BASEDIR directory does not exist"),
        (lambda v: v.update({"ALLOW_ANONYMOUS_ACCESS": "x"}), "ALLOW_ANONYMOUS_ACCESS must be a boolean"),
        (lambda v: v.update({"INSTALLED_APPS": []}), "INSTALLED_APPS is required"),
        (lambda v: v.update({"INSTALLED_APPS": "x"}), "INSTALLED_APPS must be a list or tuple"),
        (lambda v: v.update({"DATABASE": None}), "DATABASE configuration is required"),
        (lambda v: v.update({"DATABASE": "x"}), "DATABASE must be a dictionary"),
        (lambda v: v["DATABASE"].pop("DRIVER"), "DATABASE.DRIVER is required"),
        (lambda v: v["DATABASE"].update({"DRIVER": ""}), "DATABASE.DRIVER must not be empty"),
        (lambda v: v["DATABASE"].update({"USE_TRANSACTIONS": "x"}), "DATABASE.USE_TRANSACTIONS must be a boolean"),
        (lambda v: v["DATABASE"].update({"DRIVER": "invalid"}), "DATABASE.DRIVER must be one of"),
        (lambda v: v.update({"ELASTICSEARCH": None}), "ELASTICSEARCH configuration is required"),
        (lambda v: v.update({"ELASTICSEARCH": "x"}), "ELASTICSEARCH must be a dictionary"),
        (lambda v: v["ELASTICSEARCH"].pop("HOST"), "ELASTICSEARCH.HOST is required"),
        (lambda v: v["ELASTICSEARCH"].update({"PORT": "x"}), "ELASTICSEARCH.PORT must be an integer"),
        (lambda v: v["ELASTICSEARCH"].update({"PORT": 70000}), "ELASTICSEARCH.PORT must be between 1 and 65535"),
        (lambda v: v["ELASTICSEARCH"].update({"SECURE": "x"}), "ELASTICSEARCH.SECURE must be a boolean"),
        (lambda v: v.update({"LANGUAGES": []}), "LANGUAGES is required"),
        (lambda v: v.update({"LANGUAGES": "x"}), "LANGUAGES must be a list or tuple"),
        (lambda v: v.update({"LANGUAGES": [("en",)]}), "Each language in LANGUAGES must be a tuple"),
        (lambda v: v.update({"LANGUAGES": [(1, "English")]}), "Language code and name must be strings"),
        (lambda v: v.update({"DEFAULT_LANGUAGE": ""}), "DEFAULT_LANGUAGE is required"),
        (lambda v: v.update({"DEFAULT_LANGUAGE": "fr"}), "DEFAULT_LANGUAGE 'fr' is not in LANGUAGES"),
        (lambda v: v.update({"JWT_KEY": ""}), "JWT_KEY is required"),
        (lambda v: v.update({"SESSION_AGE": 0}), "SESSION_AGE must be a positive integer"),
        (lambda v: v.update({"SECRET_KEY": ""}), "SECRET_KEY is required"),
        (lambda v: v.update({"OID_CONNECT_ENABLED": "x"}), "OID_CONNECT_ENABLED must be a boolean"),
        (lambda v: v.update({"WIRECLOUD_HTTPS_VERIFY": "x"}), "WIRECLOUD_HTTPS_VERIFY must be a boolean"),
        (lambda v: v.update({"CACHE_DIR": 1}), "CACHE_DIR must be a string"),
    ],
)
def test_validate_and_set_defaults_error_paths(monkeypatch, tmp_path, mutator, message):
    values = _valid_settings_dict(tmp_path)
    mutator(values)
    _apply_settings(monkeypatch, values)
    with pytest.raises(ValueError, match=message):
        settings_validator._validate_and_set_defaults()


def test_validate_and_set_defaults_languages_zero_len_branch(monkeypatch, tmp_path):
    class _WeirdLanguages(list):
        def __bool__(self):
            return True

    values = _valid_settings_dict(tmp_path)
    values["LANGUAGES"] = _WeirdLanguages()
    _apply_settings(monkeypatch, values)
    with pytest.raises(ValueError, match="at least one language"):
        settings_validator._validate_and_set_defaults()


@pytest.mark.parametrize(
    "mutator, message",
    [
        (lambda v: v.update({"OID_CONNECT_CLIENT_ID": ""}), "OID_CONNECT_CLIENT_ID is required"),
        (lambda v: v.update({"OID_CONNECT_CLIENT_SECRET": ""}), "OID_CONNECT_CLIENT_SECRET is required"),
        (lambda v: v.update({"OID_CONNECT_PLUGIN": ""}), "OID_CONNECT_PLUGIN is required"),
        (lambda v: v.update({"OID_CONNECT_PLUGIN": "missing.plugin"}), "OID_CONNECT_PLUGIN"),
        (lambda v: v.update({"OID_CONNECT_FULLY_SYNC_GROUPS": "x"}), "OID_CONNECT_FULLY_SYNC_GROUPS must be a boolean"),
        (lambda v: v.update({"OID_CONNECT_BACKCHANNEL_LOGOUT": "x"}), "OID_CONNECT_BACKCHANNEL_LOGOUT must be a boolean"),
    ],
)
def test_validate_and_set_defaults_oidc_paths(monkeypatch, tmp_path, mutator, message):
    values = _valid_settings_dict(tmp_path)
    values["OID_CONNECT_ENABLED"] = True
    values["OID_CONNECT_CLIENT_ID"] = "cid"
    values["OID_CONNECT_CLIENT_SECRET"] = "secret"
    values["OID_CONNECT_PLUGIN"] = "platform"
    mutator(values)
    _apply_settings(monkeypatch, values)
    with pytest.raises(ValueError, match=message):
        settings_validator._validate_and_set_defaults()


async def test_validate_settings_and_validate_plugins(monkeypatch, tmp_path):
    values = _valid_settings_dict(tmp_path)
    _apply_settings(monkeypatch, values)

    called = {"sync": 0, "async": 0}

    def _sync_validator(_settings, _offline):
        called["sync"] += 1

    async def _async_validator(_settings, _offline):
        called["async"] += 1

    monkeypatch.setattr(settings_validator, "get_config_validators", lambda: [_sync_validator, _async_validator])
    await settings_validator.validate_settings(offline=True)
    assert called == {"sync": 1, "async": 1}

    called["async"] = 0
    monkeypatch.setattr(settings_validator, "get_config_validators", lambda: [_async_validator, _async_validator])
    await settings_validator.validate_settings(offline=False)
    assert called["async"] == 2

    called["async"] = 0
    monkeypatch.setattr(settings_validator, "get_config_validators", lambda: [object(), _async_validator])
    await settings_validator.validate_settings(offline=False)
    assert called["async"] == 1

    monkeypatch.setattr(settings_validator.settings, "INSTALLED_APPS", ["wirecloud.catalogue"], raising=False)
    with pytest.raises(ValueError, match="wirecloud.commons"):
        settings_validator.validate_plugins()

    monkeypatch.setattr(
        settings_validator.settings,
        "INSTALLED_APPS",
        ["wirecloud.commons", "wirecloud.catalogue", "wirecloud.platform"],
        raising=False,
    )
    settings_validator.validate_plugins()
    assert "wirecloud.proxy" in settings_validator.settings.INSTALLED_APPS

    monkeypatch.setattr(
        settings_validator.settings,
        "INSTALLED_APPS",
        ["wirecloud.commons", "wirecloud.catalogue"],
        raising=False,
    )
    settings_validator.validate_plugins()
    assert settings_validator.settings.INSTALLED_APPS == ["wirecloud.commons", "wirecloud.catalogue"]


def test_validate_and_set_defaults_without_cache_attr(monkeypatch, tmp_path):
    values = _valid_settings_dict(tmp_path)
    _apply_settings(monkeypatch, values)
    if hasattr(settings_validator.settings, "cache"):
        delattr(settings_validator.settings, "cache")
    settings_validator._validate_and_set_defaults()
