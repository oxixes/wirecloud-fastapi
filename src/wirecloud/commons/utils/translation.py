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

import re
from pathlib import Path
from typing import Optional


def compile_catalog(po_file: Path, mo_file: Path) -> None:
    """Validate and compile a catalog for management commands and package builds."""
    from babel.messages.mofile import write_mo
    from babel.messages.pofile import read_po

    with po_file.open("rb") as stream:
        catalog = read_po(stream, locale=po_file.parent.parent.name, abort_invalid=True)
    errors = [
        f"{message.id!r}: {error}"
        for message, problems in catalog.check()
        for error in problems
    ]
    if errors:
        raise ValueError(f"Invalid catalog {po_file}:\n" + "\n".join(errors))

    mo_file.parent.mkdir(parents=True, exist_ok=True)
    with mo_file.open("wb") as stream:
        write_mo(stream, catalog)


def get_trans_index(value: Optional[str]) -> Optional[str]:
    """Checks if the string received as argument is a translation index"""
    if isinstance(value, str):
        index = re.match("__MSG_(?P<value>.+)__", value, re.I)
        if index:
            return index.group("value")
    return None


def replace_trans_index(index: str, text: str, value: str) -> str:

    return text.replace('__MSG_' + index + '__', value)
