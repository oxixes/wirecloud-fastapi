# -*- coding: utf-8 -*-

from wirecloud.platform.theme import docs, schemas


def test_theme_docs_constants():
    assert isinstance(docs.get_theme_info_summary, str)
    assert isinstance(docs.get_theme_info_description, str)
    assert isinstance(docs.get_theme_info_response_description, str)
    assert isinstance(docs.get_theme_info_not_found_response_description, str)
    assert isinstance(docs.get_theme_info_validation_error_response_description, str)
    assert isinstance(docs.get_theme_info_theme_param_description, str)
    assert isinstance(docs.get_theme_info_view_param_description, str)
    assert isinstance(docs.theme_info_name_description, str)
    assert isinstance(docs.theme_info_label_description, str)
    assert isinstance(docs.theme_info_templates_description, str)


def test_theme_info_schema_roundtrip():
    info = schemas.ThemeInfo(
        name="defaulttheme",
        label="Default",
        templates={"wirecloud/head": "<wirecloud/head.html>"},
    )
    assert info.name == "defaulttheme"
    assert info.label == "Default"
    assert info.templates["wirecloud/head"] == "<wirecloud/head.html>"
