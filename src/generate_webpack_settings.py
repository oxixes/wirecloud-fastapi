#!/usr/bin/env python3
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

"""
Generates a small settings JSON for webpack in the system temporary directory.
The output path is taken from the WEBPACK_SETTINGS_JSON environment variable if set,
otherwise the script writes to: <tempdir>/wirecloud_settings_js.json.

The produced JSON contains only one key for now: `installedApps`, which is a list
of objects: { "name": "catalogue", "module": "wirecloud.catalogue", "path": "/abs/path/to/module" }
"""
import json
import os
import sys
import tempfile
import asyncio
from os import path

# Project root is assumed to be the parent of the scripts/ directory
ROOT = path.abspath(path.join(path.dirname(path.abspath(__file__)), '..'))

# Make sure we can import src.settings
# Use slice assignment to avoid potential type warnings from some linters
sys.path[0:0] = [ROOT]

from src.settings_validator import validate_settings

# Run settings validation to ensure settings are correct as async
asyncio.run(validate_settings(True))

out_path = os.environ.get('WEBPACK_SETTINGS_JSON') or path.join(tempfile.gettempdir(), 'wirecloud_settings_js.json')

try:
    from src import settings as srv_settings
except Exception:
    try:
        import settings as srv_settings
    except Exception:
        srv_settings = None

installed_apps_raw = []
if srv_settings is not None:
    installed_apps_raw = getattr(srv_settings, 'INSTALLED_APPS', None) or getattr(srv_settings, 'installed_apps', None) or []

# Resolve Python modules to filesystem paths
import importlib

installed_apps = []
seen = set()
for app in installed_apps_raw:
    if not isinstance(app, str):
        continue
    dotted = app
    # use rsplit to avoid negative-index warnings
    parts = dotted.rsplit('.', 1)
    short = parts[-1] if parts else dotted

    # Avoid duplicates
    if short in seen:
        continue
    seen.add(short)

    module_path = None
    try:
        mod = importlib.import_module(dotted)
        # Prefer package __path__ (first entry) or module __file__ parent
        if hasattr(mod, '__path__'):
            # __path__ can be an iterable; pick first entry if present
            module_path = next(iter(getattr(mod, '__path__', [])), None)
        elif hasattr(mod, '__file__'):
            module_path = path.dirname(getattr(mod, '__file__'))
    except Exception:
        module_path = None

    # Normalize module_path to absolute path if possible
    if module_path:
        try:
            module_path = path.abspath(str(module_path))
        except Exception:
            pass

    installed_apps.append({
        'name': short,
        'module': dotted,
        'path': module_path
    })

payload = {
    'installedApps': installed_apps
}

# Ensure destination dir exists
try:
    os.makedirs(path.dirname(out_path), exist_ok=True)
except Exception:
    pass

with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(payload, f, indent=2, ensure_ascii=False)

print(f'Generated webpack settings at: {out_path}')
