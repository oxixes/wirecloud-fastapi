# -*- coding: utf-8 -*-

# Copyright (c) 2025 Future Internet Consulting and Development Solutions S.L.

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
import asyncio
import argparse
import sys
from pathlib import Path
from typing import Optional, Callable

from src.settings_validator import validate_settings

# Add the parent directory to the path to allow importing src module
# This allows the script to work when run as "python manage.py" or "python -m src.manage"
current_file = Path(__file__).resolve()
project_root = current_file.parent.parent  # Go up from src/ to project root
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.wirecloud.platform.plugins import get_management_commands

_commands: dict[str, Callable[[argparse.Namespace], None]] = {}

def _parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    global _commands

    parser = argparse.ArgumentParser(prog="manage.py",
                                     description="Management script for Wirecloud")
    subparsers = parser.add_subparsers(dest="command", required=True)

    _commands = get_management_commands(subparsers)

    return parser.parse_args(argv)


async def main(argv: Optional[list[str]] = None) -> int:
    await validate_settings()
    args = _parse_args(argv)

    command_func = _commands.get(args.command)
    if command_func is not None:
        if inspect.iscoroutinefunction(command_func):
            await command_func(args)
        else:
            command_func(args)
        return 0

    return 2


if __name__ == "__main__":
    exit(asyncio.run(main()))