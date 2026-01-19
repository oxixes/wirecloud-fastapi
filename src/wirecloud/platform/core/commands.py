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

import argparse
import os
from pathlib import Path
from typing import Callable

from src.wirecloud.platform.plugins import get_plugins


async def runserver_cmd(args: argparse.Namespace) -> None:
    import uvicorn

    # Import the FastAPI application
    try:
        from src.main import app as application
    except Exception as exc:
        print("Failed to import the FastAPI application from 'src.main'.")
        print(f"Error: {exc}")
        raise

    # Use uvicorn.Server to leverage the existing event loop
    config = uvicorn.Config(
        app=application,
        host=args.host,
        port=args.port,
        reload=args.reload,
        workers=args.workers,
        log_level="debug" if args.debug else "info"
    )
    server = uvicorn.Server(config)
    try:
        await server.serve()
    except KeyboardInterrupt:
        pass


def _get_modules_to_process(wirecloud_path: Path, settings) -> list:
    modules_to_process = []

    # Add installed apps
    for app_name in settings.INSTALLED_APPS:
        module_path = wirecloud_path / app_name.replace("wirecloud.", "")
        if module_path.exists():
            modules_to_process.append({
                'name': app_name,
                'path': module_path,
                'domain': app_name
            })

    # Add themes
    themes_path = wirecloud_path / "themes"
    if themes_path.exists():
        for theme_dir in themes_path.iterdir():
            if theme_dir.is_dir() and not theme_dir.name.startswith('_') and not theme_dir.name == '__pycache__':
                modules_to_process.append({
                    'name': f'wirecloud.themes.{theme_dir.name}',
                    'path': theme_dir,
                    'domain': theme_dir.name
                })

    return modules_to_process


def _extract_messages(module_path: Path, extraction_methods: list, keywords: dict, file_type: str) -> dict:
    from babel.messages.extract import extract_from_dir

    extracted_messages = {}

    try:
        for extracted in extract_from_dir(
            dirname=str(module_path),
            method_map=extraction_methods,
            keywords=keywords,
            comment_tags=['TRANSLATORS:']
        ):
            filename, lineno, message, comments, context = extracted

            # Skip empty messages
            if not message or (isinstance(message, tuple) and not message[0]):
                continue

            # Create a key for the message
            msg_key = message if isinstance(message, str) else message[0]

            if msg_key not in extracted_messages:
                extracted_messages[msg_key] = []

            # Store location info
            rel_path = os.path.relpath(filename, str(module_path))
            extracted_messages[msg_key].append((rel_path, lineno))
    except Exception as e:
        print(f"  Warning: Error extracting messages from {file_type} files: {e}")

    return extracted_messages


def _process_po_file(po_file_path: Path, extracted_messages: dict, lang_code: str, domain: str) -> None:
    from babel.messages.catalog import Catalog
    from babel.messages.pofile import read_po, write_po

    # Load existing catalog or create new one
    if po_file_path.exists():
        print(f"    Updating existing file: {po_file_path.name}")
        try:
            with open(po_file_path, 'rb') as f:
                existing_catalog = read_po(f, locale=lang_code, domain=domain)

            # Create new catalog with updated messages
            catalog = Catalog(
                locale=lang_code,
                domain=domain,
                project='WireCloud',
                copyright_holder='Future Internet Consulting and Development Solutions S.L.',
                charset='utf-8'
            )

            # Copy existing translations
            for message in existing_catalog:
                if message.id:  # Skip header
                    catalog[message.id] = message

            # Add new messages from extracted
            for msg_id, locations in extracted_messages.items():
                if msg_id not in catalog:
                    catalog.add(msg_id, locations=locations)
                else:
                    # Update locations for existing messages
                    catalog[msg_id].locations = locations

        except Exception as e:
            print(f"    Warning: Could not read existing file, creating new one. Error: {e}")
            catalog = Catalog(
                locale=lang_code,
                domain=domain,
                project='WireCloud',
                copyright_holder='Future Internet Consulting and Development Solutions S.L.',
                charset='utf-8'
            )
            for msg_id, locations in extracted_messages.items():
                catalog.add(msg_id, locations=locations)
    else:
        print(f"    Creating new file: {po_file_path.name}")
        catalog = Catalog(
            locale=lang_code,
            domain=domain,
            project='WireCloud',
            copyright_holder='Future Internet Consulting and Development Solutions S.L.',
            charset='utf-8'
        )
        for msg_id, locations in extracted_messages.items():
            catalog.add(msg_id, locations=locations)

    # Write the catalog to file
    try:
        with open(po_file_path, 'wb') as f:
            write_po(f, catalog, width=80, sort_output=True, ignore_obsolete=True)
        print(f"    ✓ Successfully written to {po_file_path}")
    except Exception as e:
        print(f"    ✗ Error writing file: {e}")


def gentranslations_cmd(args: argparse.Namespace) -> None:
    from src import settings

    # Get the base source directory
    src_path = Path(__file__).parent.parent.parent.parent
    wirecloud_path = src_path / "wirecloud"

    # Determine which languages to process
    if args.language:
        # Check if the language code is valid (basic format check)
        lang_code = args.language
        # Try to find the language name in settings.LANGUAGES
        lang_name = None
        for code, name in settings.LANGUAGES:
            if code == lang_code:
                lang_name = name
                break

        # If not found, use the code as the name (for new languages)
        if lang_name is None:
            lang_name = lang_code
            print(f"Note: '{lang_code}' is not in LANGUAGES setting. Creating new language files.")

        languages_to_process = [(lang_code, lang_name)]
    else:
        # Process all languages from settings
        languages_to_process = list(settings.LANGUAGES)

    print("=" * 70)
    print("Generating translation files for Wirecloud modules and themes")
    if args.language:
        print(f"Language: {languages_to_process[0][1]} ({languages_to_process[0][0]})")
    else:
        print(f"Languages: {', '.join([f'{name} ({code})' for code, name in languages_to_process])}")
    print("=" * 70)

    # Define extraction methods for different file types
    # We'll process Python and JS/TS separately to create different .po files
    extraction_methods_python = [
        ('**.py', 'python'),
        ('**/templates/**.html', 'jinja2'),  # Add Jinja2 templates
    ]

    extraction_methods_js = [
        ('**.js', 'javascript'),
        ('**.ts', 'javascript'),
    ]

    # Custom keywords for extraction
    keywords = {
        '_': None,
        'gettext': None,
        'ngettext': (1, 2),
        'ugettext': None,
        'ungettext': (1, 2),
        'gettext_lazy': None,
        'ugettext_lazy': None,
        'ngettext_lazy': (1, 2),
        'ungettext_lazy': (1, 2),
        'trans': None,  # Jinja2 trans function
        'trans_text': None,  # Alternative Jinja2 function
    }

    # Get all modules to process
    modules_to_process = _get_modules_to_process(wirecloud_path, settings)

    # Process each module
    for module_info in modules_to_process:
        module_name = module_info['name']
        module_path = module_info['path']
        domain = module_info['domain']

        print(f"\nProcessing module: {module_name}")
        print(f"  Path: {module_path}")

        # Create locale directory if it doesn't exist
        locale_path = module_path / "locale"
        locale_path.mkdir(exist_ok=True)

        # Extract messages from Python files
        print(f"  Extracting messages from Python files...")
        extracted_messages_python = _extract_messages(
            module_path,
            extraction_methods_python,
            keywords,
            "Python"
        )

        if extracted_messages_python:
            print(f"    Found {len(extracted_messages_python)} unique messages in Python files")

        # Extract messages from JavaScript/TypeScript files
        print(f"  Extracting messages from JavaScript/TypeScript files...")
        extracted_messages_js = _extract_messages(
            module_path,
            extraction_methods_js,
            keywords,
            "JS/TS"
        )

        if extracted_messages_js:
            print(f"    Found {len(extracted_messages_js)} unique messages in JS/TS files")

        # Skip if no messages found at all
        if not extracted_messages_python and not extracted_messages_js:
            print(f"  No translatable messages found, skipping...")
            continue

        # Process each language
        for lang_code, lang_name in languages_to_process:
            # Skip English as it's the source language (unless explicitly requested)
            if lang_code in ['en', 'en-US', 'en-GB'] and not args.language:
                print(f"  Skipping {lang_name} (source language)")
                continue

            print(f"  Processing language: {lang_name} ({lang_code})")

            # Create language directory structure
            lang_dir = locale_path / lang_code / "LC_MESSAGES"
            lang_dir.mkdir(parents=True, exist_ok=True)

            # Process Python messages (domain.po)
            if extracted_messages_python:
                po_file_path = lang_dir / f"{domain}.po"
                _process_po_file(
                    po_file_path,
                    extracted_messages_python,
                    lang_code,
                    domain
                )

            # Process JavaScript/TypeScript messages (domain.js.po)
            if extracted_messages_js:
                po_file_path_js = lang_dir / f"{domain}.js.po"
                _process_po_file(
                    po_file_path_js,
                    extracted_messages_js,
                    lang_code,
                    domain
                )

    print("\n" + "=" * 70)
    print("Translation file generation completed!")
    print("=" * 70)


def compiletranslations_cmd(args: argparse.Namespace) -> None:
    from babel.messages.mofile import write_mo
    from babel.messages.pofile import read_po
    from src import settings

    # Get the base source directory
    src_path = Path(__file__).parent.parent.parent.parent
    wirecloud_path = src_path / "wirecloud"

    # Determine which languages to compile
    if args.language:
        lang_code = args.language
        lang_name = None
        for code, name in settings.LANGUAGES:
            if code == lang_code:
                lang_name = name
                break

        if lang_name is None:
            lang_name = lang_code

        languages_to_compile = [(lang_code, lang_name)]
    else:
        languages_to_compile = list(settings.LANGUAGES)

    print("=" * 70)
    print("Compiling translation files for Wirecloud modules and themes")
    if args.language:
        print(f"Language: {languages_to_compile[0][1]} ({languages_to_compile[0][0]})")
    else:
        print(f"Languages: {', '.join([f'{name} ({code})' for code, name in languages_to_compile])}")
    print("=" * 70)

    # Get all modules to process
    modules_to_process = _get_modules_to_process(wirecloud_path, settings)

    total_compiled = 0
    total_errors = 0

    # Process each module
    for module_info in modules_to_process:
        module_name = module_info['name']
        module_path = module_info['path']

        locale_path = module_path / "locale"

        # Skip if locale directory doesn't exist
        if not locale_path.exists():
            continue

        module_compiled = 0

        # Process each language
        for lang_code, lang_name in languages_to_compile:
            lang_dir = locale_path / lang_code / "LC_MESSAGES"

            # Skip if language directory doesn't exist
            if not lang_dir.exists():
                continue

            # Find all .po files in the directory
            po_files = list(lang_dir.glob("*.po"))

            for po_file in po_files:
                # Generate .mo filename
                mo_file = po_file.with_suffix('.mo')

                try:
                    # Read the .po file
                    with open(po_file, 'rb') as f:
                        catalog = read_po(f, locale=lang_code)

                    # Write the .mo file
                    with open(mo_file, 'wb') as f:
                        write_mo(f, catalog)

                    module_compiled += 1
                    total_compiled += 1

                    if args.verbose:
                        print(f"  ✓ Compiled: {po_file.name} → {mo_file.name}")

                except Exception as e:
                    total_errors += 1
                    print(f"  ✗ Error compiling {po_file}: {e}")

        if module_compiled > 0 and not args.verbose:
            print(f"✓ {module_name}: {module_compiled} file(s) compiled")

    print("\n" + "=" * 70)
    print(f"Compilation completed!")
    print(f"  Total compiled: {total_compiled}")
    if total_errors > 0:
        print(f"  Total errors: {total_errors}")
    print("=" * 70)


async def rebuildsearchindexes_cmd(_args: argparse.Namespace) -> None:
    from src.wirecloud.commons.search import rebuild_all_indexes
    from src.wirecloud.database import get_session

    # get_session provides an async iterator
    async for session in get_session():
        await rebuild_all_indexes(session)

    print("Search indexes rebuilt successfully.")


async def populate_cmd(_args: argparse.Namespace) -> None:
    from src.wirecloud.database import get_session

    async for session in get_session():
        # Get the wirecloud user
        from src.wirecloud.commons.auth.crud import get_user_with_all_info_by_username

        wirecloud_user = await get_user_with_all_info_by_username(session, "wirecloud")
        if not wirecloud_user:
            # Create the wirecloud user if it doesn't exist
            from src.wirecloud.commons.auth.crud import create_user
            from src.wirecloud.commons.auth.schemas import UserCreate
            from src.wirecloud.database import commit

            wirecloud_user_data = UserCreate(
                username="wirecloud",
                email="",
                first_name="",
                last_name="",
                is_superuser=False,
                is_staff=False,
                is_active=True,
                idm_data={},
                password="!"
            )

            await create_user(session, wirecloud_user_data)
            await commit(session)

            wirecloud_user = await get_user_with_all_info_by_username(session, "wirecloud")

            print("Created 'wirecloud' user.")

        plugins = get_plugins()
        for plugin in plugins:
            if hasattr(plugin, "populate"):
                await plugin.populate(session, wirecloud_user)


def setup_commands(subparsers: argparse._SubParsersAction) -> dict[str, Callable]:
    runserver = subparsers.add_parser("runserver", help="Start the development server (uvicorn)")
    runserver.add_argument("-H", "--host", default="localhost", help="Host to bind to (default: localhost)")
    runserver.add_argument("-p", "--port", type=int, default=8000, help="Port to listen on (default: 8000)")
    runserver.add_argument("-r", "--reload", action="store_true", help="Enable autoreload (useful in development)")
    runserver.add_argument("-w", "--workers", type=int, default=1, help="Number of uvicorn workers (default: 1)")
    runserver.add_argument("--debug", action="store_true", help="Enable debug mode")

    gentranslations = subparsers.add_parser("gentranslations", help="Generate or update translation files (.po) for all modules")
    gentranslations.add_argument("-l", "--language", help="Generate translations for a specific language (e.g., 'es', 'fr', 'de'). If not specified, all languages from settings.LANGUAGES will be processed.")

    compiletranslations = subparsers.add_parser("compiletranslations", help="Compile translation files (.po) to binary format (.mo)")
    compiletranslations.add_argument("-l", "--language", help="Compile translations for a specific language. If not specified, all languages from settings.LANGUAGES will be compiled.")
    compiletranslations.add_argument("-v", "--verbose", action="store_true", help="Show detailed output for each file compiled")

    _rebuildsearchindexes = subparsers.add_parser("rebuildsearchindexes", help="Rebuild all search indexes")
    _populate = subparsers.add_parser("populate", help="Populate the database with initial data")

    return {
        "runserver": runserver_cmd,
        "gentranslations": gentranslations_cmd,
        "compiletranslations": compiletranslations_cmd,
        "rebuildsearchindexes": rebuildsearchindexes_cmd,
        "populate": populate_cmd
    }