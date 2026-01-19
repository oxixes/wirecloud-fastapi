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

import inspect
import gettext as gt
import os
from gettext import NullTranslations
from typing import Optional, Callable
from fastapi import Request, WebSocket

from src import settings


translations = {}

def generate_translations() -> None:
    for plugin_name in settings.INSTALLED_APPS:
        src_path = os.path.dirname(os.path.dirname(__file__))
        locale_path = os.path.join(src_path, plugin_name.replace(".", "/"), "locale")

        if not os.path.exists(locale_path) or not os.path.isdir(locale_path):
            continue

        for lang in settings.LANGUAGES:
            try:
                translations[(plugin_name, lang[0])] = gt.translation(plugin_name, locale_path, languages=[lang[0]])
            except FileNotFoundError:
                pass


def find_request_language() -> Optional[str]:
    # We find a call in the stack that has a Request object in its arguments, and return the language from it
    stack = inspect.stack()
    for frame_info in stack:
        frame = frame_info.frame

        for value in frame.f_locals.values():
            if isinstance(value, Request) or isinstance(value, WebSocket):
                return value.state.lang

    return None


def gettext(text: str, lang: Optional[str] = None, translation: Optional[NullTranslations] = None) -> str:
    lang = lang or find_request_language()
    if lang is None and translation is None:
        raise ValueError("Was not able to find the request language for gettext. Was this function called from a request context?")

    # WireCloud is written in English, so we return the text as is if the language is English
    if lang == "en" or lang == "en-GB":
        return text

    if translation is None:
        # Find the plugin that requested the translation
        plugin: Optional[str] = None
        module_name = inspect.stack()[1].frame.f_globals.get('__name__')
        for plugin_name in settings.INSTALLED_APPS:
            if module_name.startswith(f"src.{plugin_name}"):
                plugin = plugin_name
                break

        if plugin is None:
            raise ValueError("Was not able to find the plugin name for gettext. Was this function called from a plugin?")

        # Get the locale directory for the plugin
        src_path = os.path.dirname(os.path.dirname(__file__))
        locale_path = os.path.join(src_path, plugin.replace(".", "/"), "locale")

        if not os.path.exists(locale_path) or not os.path.isdir(locale_path):
            raise ValueError(f"Could not find the locale directory for plugin {plugin}, but a translation was requested")

        # Load the translation
        if translation is None:
            translation = translations.get((plugin, lang)) if translations else None

        if translation is None:
            print(f"WARNING: Translation for language {lang} in module {plugin} not found, but was requested")
            return text

    return translation.gettext(text)


def gettext_lazy(text: str) -> Callable[[], str]:
    def _gettext(lang: Optional[str] = None, translation: Optional[NullTranslations] = None):
        return gettext(text, lang, translation)

    return _gettext

generate_translations()