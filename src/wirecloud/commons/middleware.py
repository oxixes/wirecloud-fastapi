# -*- coding: utf-8 -*-

# Copyright (c) 2008-2016 CoNWeT Lab., Universidad Politécnica de Madrid
# Copyright (c) 2019-2020 Future Internet Consulting and Development Solutions S.L.

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

from fastapi import Request, FastAPI
from fastapi.middleware.gzip import GZipMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from src import settings

DEFAULT_LANGUAGE = getattr(settings, "DEFAULT_LANGUAGE", "en")
AVAILABLE_LANGUAGES = [lang[0] for lang in settings.LANGUAGES]


class LocaleMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: FastAPI):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        # Get the language from the request
        accept_lang_header = request.headers.get("Accept-Language")
        if accept_lang_header is None:
            browser_language = DEFAULT_LANGUAGE
        else:
            # Parse the header and get a list of languages sorted by priority
            languages = []
            for lang in accept_lang_header.split(","):
                parts = lang.strip().split(";")
                lang = parts[0].strip()
                quality = 1.0
                if len(parts) == 2:
                    if parts[1].strip().startswith("q="):
                        try:
                            quality = float(parts[1].strip()[2:])
                        except ValueError:
                            pass
                if lang in AVAILABLE_LANGUAGES:
                    languages.append((lang, quality))

            # Sort the languages by quality
            languages.sort(key=lambda x: x[1], reverse=True)

            language = None
            for lang, _ in languages:
                if lang in AVAILABLE_LANGUAGES:
                    language = lang
                    break

            browser_language = language if language is not None else DEFAULT_LANGUAGE

        if request.query_params.get("lang") in AVAILABLE_LANGUAGES:
            language = request.query_params["lang"]
            request.state.lang_prefs = True
        elif request.cookies.get("lang") in AVAILABLE_LANGUAGES:
            language = request.cookies["lang"]
            request.state.lang_prefs = True
        else:
            language = browser_language
            request.state.lang_prefs = False

        request.state.lang = language

        # Call the next middleware
        response = await call_next(request)

        # Add a Content-Language header to the response
        response.headers["Content-Language"] = language

        return response


def install_all_middlewares(app: FastAPI) -> None:
    app.add_middleware(LocaleMiddleware)
    app.add_middleware(GZipMiddleware)