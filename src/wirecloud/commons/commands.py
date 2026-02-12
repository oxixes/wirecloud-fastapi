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
# TODO Migrate maybe teams
import argparse
import sys
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Callable, Any
import json
from bson import ObjectId
import traceback

from wirecloud.catalogue.utils import add_packaged_resource, create_widget_on_resource_creation, \
    deploy_operators_on_resource_creation
from wirecloud.commons.auth.crud import get_user_by_username
from wirecloud.commons.utils.template.schemas.macdschemas import MACDWidget, MACDOperator, MACDMashup
from wirecloud.platform.markets.schemas import MarketCreate

try:
    import aiohttp
except ImportError:
    aiohttp = None

try:
    import pymysql
    from pymysql.cursors import DictCursor as MySQLDictCursor
except ImportError:
    pymysql = None
    MySQLDictCursor = None

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    psycopg2 = None
    RealDictCursor = None

try:
    import sqlite3
except ImportError:
    sqlite3 = None

from wirecloud.database import get_session, commit, Id


async def migrate_cmd(args: argparse.Namespace) -> None:
    """
    Migrate data from an old Django-based Wirecloud instance to the new FastAPI/MongoDB version.

    This command will:
    1. Migrate users and groups from the old SQL database
    2. Migrate catalogue resources using the API and file system
    3. Migrate workspaces using the API
    4. Copy catalogue and deployment media files
    """

    # Check dependencies
    if args.db_type == 'mysql' and pymysql is None:
        print("Error: pymysql is required for MySQL. Install it with: pip install pymysql")
        sys.exit(1)
    elif args.db_type == 'postgresql' and psycopg2 is None:
        print("Error: psycopg2 is required for PostgreSQL. Install it with: pip install psycopg2-binary")
        sys.exit(1)
    elif args.db_type == 'sqlite' and sqlite3 is None:
        print("Error: sqlite3 is required for SQLite")
        sys.exit(1)

    if aiohttp is None:
        print("Error: aiohttp is required for migration. Install it with: pip install aiohttp")
        sys.exit(1)

    # Validate database credentials for non-SQLite databases
    if args.db_type != 'sqlite':
        if not args.db_user:
            print(f"Error: --db-user is required for {args.db_type}")
            sys.exit(1)
        if not args.db_password:
            print(f"Error: --db-password is required for {args.db_type}")
            sys.exit(1)

    # Set default port if not specified
    if args.db_port is None:
        if args.db_type == 'mysql':
            args.db_port = 3306
        elif args.db_type == 'postgresql':
            args.db_port = 5432

    print("=" * 80)
    print("Wirecloud Migration Tool")
    print("=" * 80)
    print()
    print("This tool will migrate data from an old Wirecloud instance to this new version.")
    print(f"Source URL: {args.url}")
    if args.db_type == 'sqlite':
        print(f"Database: SQLite {args.db_name}")
    else:
        print(f"Database: {args.db_type.upper()} - {args.db_name} at {args.db_host}:{args.db_port}")
    print()

    if not args.yes:
        confirm = input("Do you want to continue? (yes/no): ")
        if confirm.lower() not in ['yes', 'y']:
            print("Migration cancelled.")
            return

    try:
        # Connect to old database
        print("\n[1/7] Connecting to old database...")

        db_connection = None
        if args.db_type == 'mysql':
            db_connection = pymysql.connect(
                host=args.db_host,
                port=args.db_port,
                user=args.db_user,
                password=args.db_password,
                database=args.db_name,
                charset='utf8mb4',
                cursorclass=MySQLDictCursor
            )
            print(f"✓ Connected to MySQL database: {args.db_name}")
        elif args.db_type == 'postgresql':
            db_connection = psycopg2.connect(
                host=args.db_host,
                port=args.db_port,
                user=args.db_user,
                password=args.db_password,
                dbname=args.db_name,
                cursor_factory=RealDictCursor
            )
            print(f"✓ Connected to PostgreSQL database: {args.db_name}")
        elif args.db_type == 'sqlite':
            db_connection = sqlite3.connect(args.db_name)
            db_connection.row_factory = sqlite3.Row
            print(f"✓ Connected to SQLite database: {args.db_name}")

        if db_connection is None:
            print("Error: Failed to establish database connection")
            sys.exit(1)

        # Setup HTTP client for API calls
        connector = aiohttp.TCPConnector(ssl=not args.no_verify_ssl)
        async with aiohttp.ClientSession(connector=connector) as http_session:

            # Login to old instance
            print("\n[2/7] Authenticating with old Wirecloud instance...")
            token = await _login_old_wirecloud(http_session, args.url, args.admin_user, args.admin_password)
            print(f"✓ Authenticated as {args.admin_user}")

            # Check if user is an administrator
            with db_connection.cursor() as cursor:
                cursor.execute(_adapt_sql_query("""SELECT is_superuser FROM auth_user WHERE username = %s""", args.db_type), (args.admin_user,))
                is_superuser = cursor.fetchone()['is_superuser']
                if not is_superuser:
                    print("Error: User is not an administrator")
                    sys.exit(1)

            # Get database session
            async for session in get_session():
                # Migrate constants
                print("\n[3/7] Migrating constants...")
                count = await _migrate_constants(db_connection, session, args.db_type)
                print(f"✓ Migrated {count} constants")

                # Migrate users and groups
                print("\n[4/7] Migrating users and groups...")
                user_id_mapping, group_id_mapping = await _migrate_users_and_groups(db_connection, session, args.db_type)
                print(f"✓ Migrated {len(user_id_mapping)} users and {len(group_id_mapping)} groups")

                # Migrate markets
                print("\n[5/7] Migrating markets...")
                market_count = await _migrate_markets(db_connection, session, user_id_mapping, args.db_type)
                print(f"✓ Migrated {market_count} markets")

                # Migrate catalogue resources
                print("\n[6/7] Migrating catalogue resources...")
                resource_mapping = await _migrate_catalogue_resources(
                    db_connection, session, http_session, args.url, token,
                    user_id_mapping, group_id_mapping, args.db_type
                )
                print(f"✓ Migrated {len(resource_mapping)} catalogue resources")

                # Migrate workspaces
                print("\n[7/7] Migrating workspaces...")
                workspace_count = await _migrate_workspaces(
                    db_connection, session, http_session, args.url, token,
                    user_id_mapping, group_id_mapping, resource_mapping, args.db_type
                )
                print(f"✓ Migrated {workspace_count} workspaces")
                break

        db_connection.close()

        print("\n" + "=" * 80)
        print("Migration completed successfully!")
        print("=" * 80)

    except Exception as e:
        print(f"\n✗ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        print("Migration cancelled.")


def _adapt_sql_query(query: str, db_type: str) -> str:
    """Adapt SQL query for different database types."""
    if db_type == 'sqlite':
        # SQLite uses ? as placeholder instead of %s
        return query.replace('%s', '?')
    return query


def _dict_from_row(row, db_type: str):
    """Convert database row to dictionary based on database type."""
    if db_type == 'sqlite':
        return dict(row)
    # For MySQL and PostgreSQL with DictCursor, rows are already dicts
    return row


def _table_exists(cursor, table_name: str, db_type: str) -> bool:
    """Check if a table exists in the database."""
    if db_type == 'mysql':
        cursor.execute("SHOW TABLES LIKE %s", (table_name,))
        return cursor.fetchone() is not None
    elif db_type == 'postgresql':
        cursor.execute("SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = %s)", (table_name,))
        return cursor.fetchone()["exists"]
    elif db_type == 'sqlite':
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
        return cursor.fetchone() is not None
    return False


async def _login_old_wirecloud(session: aiohttp.ClientSession, url: str, username: str, password: str) -> str:
    """Login to old Wirecloud instance and return authentication token."""
    login_url = f"{url.rstrip('/')}/login"

    try:
        # First, do a GET request to obtain the CSRF token
        async with session.get(login_url) as resp:
            if resp.status != 200:
                raise Exception(f"Could not access login page: {resp.status}")

            html_content = await resp.text()

            # Extract CSRF token from the HTML
            # Look for: <input type="hidden" name="csrfmiddlewaretoken" value="...">
            import re
            csrf_match = re.search(r'name=["\']csrfmiddlewaretoken["\'][^>]+value=["\']([^"\']+)["\']', html_content)
            if not csrf_match:
                csrf_match = re.search(r'value=["\']([^"\']+)["\'][^>]+name=["\']csrfmiddlewaretoken["\']', html_content)

            if not csrf_match:
                raise Exception("Could not find CSRF token in login page")

            csrf_token = csrf_match.group(1)

        # Now POST with the CSRF token and credentials
        async with session.post(login_url, data={
            "username": username,
            "password": password,
            "csrfmiddlewaretoken": csrf_token
        }, headers={
            "Referer": login_url
        }) as resp:
            if resp.status in [200, 302]:
                # Check if login was successful by looking for redirect or checking cookies
                return "session"  # Use session cookies
            else:
                raise Exception(f"Authentication failed with status: {resp.status}")

    except Exception as e:
        raise Exception(f"Could not authenticate with old Wirecloud instance: {e}")


async def _migrate_constants(db_connection, new_db_session, db_type: str) -> int:
    with db_connection.cursor() as cursor:
        cursor.execute(_adapt_sql_query("""
                                        SELECT concept, value
                                        FROM wirecloud_constant
                                        ORDER BY id
                                        """, db_type))
        constants = cursor.fetchall()

        for constant in constants:
            await new_db_session.client.constants.update_one({"_id": Id()},
                                                             {"$set": {"concept": constant['concept'],
                                                                       "value": constant['value']}}, upsert=True)

    await commit(new_db_session)

    return len(constants)


# TODO Migrate permissions
# TODO Migrate organizations
async def _migrate_users_and_groups(db_connection, new_db_session, db_type: str) -> tuple[dict[int, str], dict[int, str]]:
    from wirecloud.commons.auth.crud import create_user, create_group_if_not_exists
    from wirecloud.commons.auth.schemas import UserCreate
    from wirecloud.commons.auth.models import Group

    user_id_mapping = {}  # old_id -> new_id
    group_id_mapping = {}  # old_id -> new_id

    with db_connection.cursor() as cursor:
        # Migrate groups first
        cursor.execute(_adapt_sql_query("""
            SELECT id, name
            FROM auth_group
            ORDER BY id
        """, db_type))
        groups = cursor.fetchall()

        for group in groups:
            group_obj = Group(
                _id=Id(str(ObjectId())),
                name=group['name'],
                codename=group['name'].lower().replace(' ', '_')
            )
            await create_group_if_not_exists(new_db_session, group_obj)

            # Retrieve the created/existing group to get its ID
            from wirecloud.commons.auth.crud import get_group_by_name
            new_group = await get_group_by_name(new_db_session, group['name'])
            if new_group:
                group_id_mapping[group['id']] = str(new_group.id)
            await commit(new_db_session)

        # Migrate users
        cursor.execute(_adapt_sql_query("""
            SELECT id, password, last_login, is_superuser, username, first_name, last_name,
                   email, is_staff, is_active, date_joined
            FROM auth_user
            ORDER BY id
        """, db_type))
        users = cursor.fetchall()

        for user in users:
            user_data = UserCreate(
                username=user['username'],
                email=user['email'] or '',
                first_name=user['first_name'] or '',
                last_name=user['last_name'] or '',
                is_superuser=bool(user['is_superuser']),
                is_staff=bool(user['is_staff']),
                is_active=bool(user['is_active']),
                idm_data={},
                password=user['password'] or '!'
            )

            await create_user(new_db_session, user_data)
            new_user = await get_user_by_username(new_db_session, user['username'])
            if new_user is None:
                print(f"  ✗ Failed to migrate user {user['username']}")
                continue

            user_id_mapping[user['id']] = str(new_user.id)

            # Update last_login and date_joined
            if user['last_login']:
                await new_db_session.client.users.update_one(
                    {"_id": ObjectId(new_user.id)},
                    {"$set": {"last_login": user['last_login']}}
                )

            if user['date_joined']:
                await new_db_session.client.users.update_one(
                    {"_id": ObjectId(new_user.id)},
                    {"$set": {"date_joined": user['date_joined']}}
                )

            # Migrate user preferences
            cursor.execute(_adapt_sql_query("""
                SELECT name, value
                FROM wirecloud_platformpreference
                WHERE user_id = %s
            """, db_type), (user['id'],))
            preferences = cursor.fetchall()

            if preferences:
                pref_list = [{"name": p['name'], "value": p['value'] or ""} for p in preferences]
                await new_db_session.client.users.update_one(
                    {"_id": ObjectId(new_user.id)},
                    {"$set": {"preferences": pref_list}}
                )

            await commit(new_db_session)

        # Migrate user-group relationships
        cursor.execute("""
            SELECT user_id, group_id
            FROM auth_user_groups
        """)
        user_groups = cursor.fetchall()

        for ug in user_groups:
            old_user_id = ug['user_id']
            old_group_id = ug['group_id']

            if old_user_id in user_id_mapping and old_group_id in group_id_mapping:
                new_user_id = ObjectId(user_id_mapping[old_user_id])
                new_group_id = ObjectId(group_id_mapping[old_group_id])

                # Add user to group
                await new_db_session.client.groups.update_one(
                    {"_id": new_group_id},
                    {"$addToSet": {"users": new_user_id}}
                )

                await new_db_session.client.users.update_one(
                    {"_id": new_user_id},
                    {"$addToSet": {"groups": new_group_id}}
                )

        await commit(new_db_session)

    return user_id_mapping, group_id_mapping


async def _migrate_markets(db_connection, new_db_session, user_id_mapping: dict[int, str], db_type: str) -> int:
    with db_connection.cursor() as cursor:
        cursor.execute(_adapt_sql_query("""
            SELECT name, public, options, user_id
            FROM wirecloud_market
            ORDER BY id
        """, db_type))
        markets = cursor.fetchall()

        for market in markets:
            market_data = {
                "_id": Id(),
                "name": market['name'],
                "public": market['public'] if type(market['public']) == bool else (str(market['public']).lower() == "true" or str(market['public']).lower() == "1"),
                "options": json.loads(market['options']) if market['options'] else {},
                "user_id": Id(user_id_mapping[market['user_id']]) if market['user_id'] in user_id_mapping else None
            }

            await new_db_session.client.markets.insert_one(market_data)

    await commit(new_db_session)
    return len(markets)


async def _migrate_catalogue_resources(
    db_connection, new_db_session, http_session: aiohttp.ClientSession,
    old_url: str, token: str, user_id_mapping: dict[int, str],
    group_id_mapping: dict[int, str], db_type: str
) -> dict[int, str]:
    from wirecloud.catalogue.crud import create_catalogue_resource
    from wirecloud.catalogue.schemas import CatalogueResourceCreate, CatalogueResourceType
    from wirecloud.commons.auth.crud import get_user_by_id
    from src import settings

    resource_id_mapping = {}  # old_id -> new_id

    # Get catalogue media path from settings
    catalogue_media_path = Path(settings.CATALOGUE_MEDIA_ROOT) if hasattr(settings, 'CATALOGUE_MEDIA_ROOT') else Path('./catalogue/media')

    # Create catalogue media directory if it doesn't exist
    catalogue_media_path.mkdir(parents=True, exist_ok=True)

    with db_connection.cursor() as cursor:
        # Get all catalogue resources
        cursor.execute(_adapt_sql_query("""
            SELECT cr.id, cr.vendor, cr.short_name, cr.version, cr.type,
                   cr.creation_date, cr.template_uri, cr.popularity,
                   cr.public, cr.creator_id, cr.json_description
            FROM catalogue_catalogueresource cr
            ORDER BY cr.creation_date
        """, db_type))
        resources = cursor.fetchall()

        for resource in resources:
            try:
                # Parse template description
                description_data = json.loads(resource['json_description']) if resource['json_description'] else {}
                resource_type = description_data.get('type', '')

                if resource_type == 'widget':
                    description = MACDWidget.model_validate(description_data)
                elif resource_type == 'operator':
                    description = MACDOperator.model_validate(description_data)
                elif resource_type == 'mashup':
                    description = MACDMashup.model_validate(description_data)
                else:
                    print(f"  ⚠ Unknown resource type for {resource['vendor']}/{resource['short_name']}/{resource['version']}, skipping.")
                    continue

                # Map creator
                creator = None
                if resource['creator_id'] and resource['creator_id'] in user_id_mapping:
                    creator_id = Id(user_id_mapping[resource['creator_id']])
                    creator = await get_user_by_id(new_db_session, creator_id)

                # Create resource
                resource_data = CatalogueResourceCreate(
                    vendor=resource['vendor'],
                    short_name=resource['short_name'],
                    version=resource['version'],
                    type=CatalogueResourceType(resource['type']),
                    public=bool(resource['public']),
                    creation_date=resource['creation_date'] or datetime.now(timezone.utc),
                    template_uri=resource['template_uri'],
                    popularity=float(resource['popularity'] or 0.0),
                    description=description,
                    creator=creator
                )

                new_resource = await create_catalogue_resource(new_db_session, resource_data)
                resource_id_mapping[resource['id']] = str(new_resource.id)

                # Migrate resource-user relationships
                cursor.execute(_adapt_sql_query("""
                    SELECT user_id FROM catalogue_catalogueresource_users
                    WHERE catalogueresource_id = %s
                """, db_type), (resource['id'],))
                resource_users = cursor.fetchall()

                for ru in resource_users:
                    if ru['user_id'] in user_id_mapping:
                        await new_db_session.client.catalogue_resources.update_one(
                            {"_id": ObjectId(new_resource.id)},
                            {"$addToSet": {"users": ObjectId(user_id_mapping[ru['user_id']])}}
                        )

                # Migrate resource-group relationships
                cursor.execute(_adapt_sql_query("""
                    SELECT group_id FROM catalogue_catalogueresource_groups
                    WHERE catalogueresource_id = %s
                """, db_type), (resource['id'],))
                resource_groups = cursor.fetchall()

                for rg in resource_groups:
                    if rg['group_id'] in group_id_mapping:
                        await new_db_session.client.catalogue_resources.update_one(
                            {"_id": ObjectId(new_resource.id)},
                            {"$addToSet": {"groups": ObjectId(group_id_mapping[rg['group_id']])}}
                        )

                await commit(new_db_session)

                # Download and save widget/operator files via API, then deploy them
                try:
                    wgt_url = None
                    wgt_type = None
                    resource_info_url = f"{old_url.rstrip('/')}/catalogue/resource/{resource['vendor']}/{resource['short_name']}/{resource['version']}"
                    async with http_session.get(resource_info_url) as resp:
                        if resp.status != 200:
                            print(f"  ✓ {resource['vendor']}/{resource['short_name']}/{resource['version']} (metadata only)")
                            continue

                        info = json.loads(await resp.text())
                        wgt_url = info['uriTemplate']
                        wgt_type = info['type']

                    # Download the WGT file from old instance
                    async with http_session.get(wgt_url) as resp:
                        if resp.status == 200:
                            wgt_bytes = await resp.read()

                            await add_packaged_resource(new_db_session, BytesIO(wgt_bytes), user=None, deploy_only=True)

                            # Deploy the widget/operator for use
                            try:
                                if wgt_type == "widget":
                                    await create_widget_on_resource_creation(new_db_session, new_resource)
                                elif wgt_type == "operator":
                                    deploy_operators_on_resource_creation(new_resource)

                                print(f"  ✓ {resource['vendor']}/{resource['short_name']}/{resource['version']} (downloaded & deployed)")
                            except Exception as deploy_error:
                                print(f"  ✓ {resource['vendor']}/{resource['short_name']}/{resource['version']} (downloaded, deployment failed: {deploy_error})")
                        else:
                            print(f"  ✓ {resource['vendor']}/{resource['short_name']}/{resource['version']} (metadata only)")
                except Exception as e:
                    print(f"  ✓ {resource['vendor']}/{resource['short_name']}/{resource['version']} (metadata only, download failed: {e})")

            except Exception as e:
                print(f"  ✗ Failed to migrate {resource['vendor']}/{resource['short_name']}/{resource['version']}: {e}")

    await commit(new_db_session)

    return resource_id_mapping


def _migrate_prop_users(field: dict[str, Any], user_id_mapping: dict[int, str]) -> None:
    for prop_name, prop_value in field.items():
        if not 'users' in prop_value:
            prop_value['users'] = {}

        new_users = {}
        for user_id, value in prop_value['users'].items():
            if user_id in user_id_mapping:
                new_users[user_id_mapping[user_id]] = value

        prop_value['users'] = new_users


def _migrate_prop_value_users(field: dict[str, Any], user_id_mapping: dict[int, str]) -> None:
    for prop_name, prop_value in field.items():
        if not 'value' in prop_value:
            prop_value['value'] = {}
        if not 'users' in prop_value['value']:
            prop_value['value']['users'] = {}

        new_users = {}
        for user_id, value in prop_value['value']['users'].items():
            if user_id in user_id_mapping:
                new_users[user_id_mapping[user_id]] = value

        prop_value['value']['users'] = new_users


async def _migrate_workspaces(
    db_connection, new_db_session, http_session: aiohttp.ClientSession,
    old_url: str, token: str, user_id_mapping: dict[int, str],
    group_id_mapping: dict[int, str], resource_mapping: dict[int, str], db_type: str
) -> int:
    from wirecloud.platform.workspace.crud import create_empty_workspace
    from wirecloud.platform.workspace.utils import create_tab
    from wirecloud.commons.auth.crud import get_user_by_id

    workspace_count = 0

    with db_connection.cursor() as cursor:
        # Get all workspaces
        cursor.execute(_adapt_sql_query("""
            SELECT w.id, w.name, w.title, w.creation_date, w.creator_id, w.last_modified,
                   w.description, w.longdescription, w.public, w.searchable,
                   w.requireauth, w."wiringStatus"
            FROM wirecloud_workspace w
            ORDER BY w.creation_date
        """, db_type))
        workspaces = cursor.fetchall()

        for workspace in workspaces:
            try:
                iwidget_mapping = {}  # old_iwidget_id -> new_iwidget_id (for wiring migration)

                # Map creator
                if workspace['creator_id'] not in user_id_mapping:
                    print(f"  ⚠ Skipping workspace '{workspace['name']}' - creator not found")
                    continue

                creator_id = Id(user_id_mapping[workspace['creator_id']])
                creator = await get_user_by_id(new_db_session, creator_id)
                if not creator:
                    continue

                # Create workspace
                new_workspace = await create_empty_workspace(
                    new_db_session,
                    title=workspace['title'],
                    user=creator,
                    name=workspace['name'],
                    translate=False
                )

                if new_workspace is None:
                    print(f"  ⚠ Could not create workspace '{workspace['name']}' - name conflict")
                    continue

                # Parse creation_date if it is not already a datetime object
                workspace['creation_date'] = datetime.strptime(workspace['creation_date'], '%Y-%m-%d %H:%M:%S.%f') if type(workspace['creation_date']) == str else workspace['creation_date']
                if workspace['creation_date'] is None:
                    workspace['creation_date'] = datetime.now(timezone.utc)

                # Parse last_modified if it is not already a datetime object
                workspace['last_modified'] = datetime.strptime(workspace['last_modified'], '%Y-%m-%d %H:%M:%S.%f') if type(workspace['last_modified']) == str else workspace['last_modified']
                if workspace['last_modified'] is None:
                    workspace['last_modified'] = workspace['creation_date']

                # Update workspace metadata
                await new_db_session.client.workspaces.update_one(
                    {"_id": ObjectId(new_workspace.id)},
                    {"$set": {
                        "description": workspace['description'] or '',
                        "longdescription": workspace['longdescription'] or '',
                        "public": bool(workspace['public']),
                        "searchable": bool(workspace['searchable']),
                        "requireauth": bool(workspace['requireauth']),
                        "creation_date": workspace['creation_date'],
                        "last_modified": workspace['last_modified']
                    }}
                )

                # Migrate workspace user permissions
                cursor.execute(_adapt_sql_query("""
                    SELECT user_id, accesslevel
                    FROM wirecloud_userworkspace
                    WHERE workspace_id = %s
                """, db_type), (workspace['id'],))
                workspace_users = cursor.fetchall()

                for wu in workspace_users:
                    if wu['user_id'] in user_id_mapping:
                        user_perm = {
                            "id": ObjectId(user_id_mapping[wu['user_id']]),
                            "accesslevel": wu['accesslevel'] or 1
                        }
                        await new_db_session.client.workspaces.update_one(
                            {"_id": ObjectId(new_workspace.id)},
                            {"$addToSet": {"users": user_perm}}
                        )

                # Migrate workspace group permissions (if groups exist in old system)
                table_name = 'wirecloud_groupworkspace' if _table_exists(cursor, 'wirecloud_groupworkspace', db_type) else 'wirecloud_workspace_groups'
                column_name = None if table_name == 'wirecloud_workspace_groups' else 'accesslevel'

                cursor.execute(_adapt_sql_query(f"""
                    SELECT group_id{', ' + column_name if column_name else ''}
                    FROM {table_name}
                    WHERE workspace_id = %s
                """, db_type), (workspace['id'],))
                workspace_groups = cursor.fetchall()

                for wg in workspace_groups:
                    if wg['group_id'] in group_id_mapping:
                        group_perm = {
                            "id": ObjectId(group_id_mapping[wg['group_id']]),
                            "accesslevel": wg[column_name] or 1
                        }
                        await new_db_session.client.workspaces.update_one(
                            {"_id": ObjectId(new_workspace.id)},
                            {"$addToSet": {"groups": group_perm}}
                        )

                # Migrate workspace preferences
                cursor.execute(_adapt_sql_query("""
                    SELECT name, value, inherit
                    FROM wirecloud_workspacepreference
                    WHERE workspace_id = %s
                """, db_type), (workspace['id'],))
                workspace_prefs = cursor.fetchall()

                if workspace_prefs:
                    pref_list = [{"name": p['name'], "value": p['value'] or "",
                                  "inherit": p['inherit'] if type(p['inherit']) == bool else (str(p['inherit']).lower() == "true" or str(p['inherit']).lower() == "1")} for p in workspace_prefs]
                    await new_db_session.client.workspaces.update_one(
                        {"_id": ObjectId(new_workspace.id)},
                        {"$set": {"preferences": pref_list}}
                    )

                # Migrate tabs
                cursor.execute(_adapt_sql_query("""
                    SELECT id, name, title, visible, position
                    FROM wirecloud_tab
                    WHERE workspace_id = %s
                    ORDER BY position
                """, db_type), (workspace['id'],))
                tabs = cursor.fetchall()

                # Remove default tab if we have tabs to migrate
                if tabs:
                    new_workspace.tabs.clear()

                old_tab_id_to_new = {}  # Mapping for widget migration

                for tab_data in tabs:
                    tab = await create_tab(
                        new_db_session,
                        creator,
                        tab_data['title'],
                        new_workspace,
                        name=tab_data['name']
                    )

                    old_tab_id_to_new[tab_data['id']] = tab.id

                    tab.visible = tab_data['visible'] if type(tab_data['visible']) == bool else (str(tab_data['visible']).lower() == "true" or str(tab_data['visible']).lower() == "1")
                    await new_db_session.client.workspaces.update_one(
                        {"_id": ObjectId(new_workspace.id)},
                        {"$set": {f"tabs.{tab.id}.visible": tab.visible}}
                    )

                    # Migrate tab preferences
                    cursor.execute(_adapt_sql_query("""
                        SELECT name, value, inherit
                        FROM wirecloud_tabpreference
                        WHERE tab_id = %s
                    """, db_type), (tab_data['id'],))
                    tab_prefs = cursor.fetchall()

                    if tab_prefs:
                        pref_list = [{"name": p['name'], "value": p['value'] or "",
                                      "inherit": p['inherit'] if type(p['inherit']) == bool else (str(p['inherit']).lower() == "true" or str(p['inherit']).lower() == "1")} for p in tab_prefs]
                        await new_db_session.client.workspaces.update_one(
                            {"_id": ObjectId(new_workspace.id)},
                            {"$set": {f"tabs.{tab.id}.preferences": pref_list}}
                        )

                    # Migrate widget instances (IWidgets)
                    cursor.execute(_adapt_sql_query("""
                        SELECT iw.id, iw.name, iw.widget_uri, iw.layout,
                            iw.positions, iw."readOnly", iw.variables, iw.permissions,
                            w.resource_id
                        FROM wirecloud_iwidget iw JOIN wirecloud_widget w ON iw.widget_id = w.id
                        WHERE iw.tab_id = %s
                    """, db_type), (tab_data['id'],))
                    iwidgets = cursor.fetchall()

                    iwidget_id = 0

                    for iwidget in iwidgets:
                        new_resource_id = resource_mapping.get(iwidget['resource_id'])
                        if not new_resource_id:
                            print(f"    ⚠ Skipping widget instance '{iwidget['name']}' - resource not found")
                            continue

                        # Fix variables ids
                        variables = json.loads(iwidget['variables']) if iwidget['variables'] else {}
                        _migrate_prop_users(variables, user_id_mapping)

                        # Fix old positions
                        positions = json.loads(iwidget['positions']) if iwidget['positions'] else {}
                        if not 'configurations' in positions:
                            new_positions = {}

                            if not 'widget' in positions:
                                print(f"    ⚠ Widget instance '{iwidget['name']}' has no position information, skipping")
                                continue

                            new_positions["configurations"] = []
                            new_positions["configurations"].append({
                                "id": 0,
                                "moreOrEqual": 0,
                                "lessOrEqual": -1,
                                "widget": {
                                    "id": 0,
                                    "top": int(positions['widget']['top']) if 'top' in positions['widget'] else 0,
                                    "left": int(positions['widget']['left']) if 'left' in positions['widget'] else 0,
                                    "zIndex": int(positions['widget']['zIndex']) if 'zIndex' in positions['widget'] else 0,
                                    "height": int(positions['widget']['height']) if 'height' in positions['widget'] else 10,
                                    "width": int(positions['widget']['width']) if 'width' in positions['widget'] else 10,
                                    "minimized": positions['widget']['minimized'] if 'minimized' in positions['widget'] else False,
                                    "titlevisible": positions['widget']['titlevisible'] if 'titlevisible' in positions['widget'] else True,
                                    "fulldragboard": positions['widget']['fulldragboard'] if 'fulldragboard' in positions['widget'] else False,
                                    "relx": positions['widget']['relx'] if 'relx' in positions['widget'] else True,
                                    "rely": positions['widget']['rely'] if 'rely' in positions['widget'] else False,
                                    "relwidth": positions['widget']['relwidth'] if 'relwidth' in positions['widget'] else True,
                                    "relheight": positions['widget']['relheight'] if 'relheight' in positions['widget'] else False,
                                    "anchor": positions['widget']['anchor'] if 'anchor' in positions['widget'] else "top-left",
                                }
                            })

                            positions = new_positions

                        # Fix permissions
                        permissions = json.loads(iwidget['permissions']) if iwidget['permissions'] else {}
                        if not 'viewer' in permissions:
                            permissions['viewer'] = {}

                        if not 'editor' in permissions:
                            permissions['editor'] = {}

                        # Create widget instance structure
                        widget_instance = {
                            "id": f"{tab.id}-{str(iwidget_id)}",
                            "resource": ObjectId(new_resource_id),
                            "widget_uri": iwidget['widget_uri'],
                            "title": iwidget['name'],
                            "layout": iwidget['layout'],
                            "read_only": iwidget['readOnly'] if type(iwidget['readOnly']) == bool else (str(iwidget['readOnly']).lower() == "true" or str(iwidget['readOnly']).lower() == "1"),
                            "variables": variables,
                            "positions": positions,
                            "permissions": permissions
                        }

                        iwidget_mapping[iwidget['id']] = widget_instance['id']

                        iwidget_id += 1

                        # Add widget to tab
                        await new_db_session.client.workspaces.update_one(
                            {"_id": ObjectId(new_workspace.id)},
                            {"$set": {f"tabs.{tab.id}.widgets.{widget_instance['id']}": widget_instance}}
                        )

                # Migrate wiring configuration
                try:
                    wiring_status = json.loads(workspace['wiringStatus']) if workspace['wiringStatus'] else {}

                    if not 'version' in wiring_status or wiring_status['version'] != '2.0':
                        print(f"    ⚠ Unsupported wiring configuration version for workspace '{workspace['name']}', skipping wiring migration")
                    else:
                        if not 'connections' in wiring_status:
                            wiring_status['connections'] = []

                        for connection in wiring_status['connections']:
                            if connection['source']['type'] == 'widget':
                                connection['source']['id'] = iwidget_mapping.get(int(connection['source']['id'])) or connection['source']['id']
                            if connection['target']['type'] == 'widget':
                                connection['target']['id'] = iwidget_mapping.get(int(connection['target']['id'])) or connection['target']['id']

                        if not 'operators' in wiring_status:
                            wiring_status['operators'] = {}

                        for operator_id, operator in wiring_status['operators'].items():
                            _migrate_prop_value_users(operator['preferences'], user_id_mapping)
                            _migrate_prop_value_users(operator['properties'], user_id_mapping)

                        if not 'visualdescription' in wiring_status:
                            wiring_status['visualdescription'] = {}

                        if not 'behaviours' in wiring_status['visualdescription']:
                            wiring_status['visualdescription']['behaviours'] = []

                        if not 'components' in wiring_status['visualdescription']:
                            wiring_status['visualdescription']['components'] = {}

                        if not 'connections' in wiring_status['visualdescription']:
                            wiring_status['visualdescription']['connections'] = []

                        for behaviour in wiring_status['visualdescription']['behaviours']:
                            if 'widgets' not in behaviour['components']:
                                behaviour['components']['widget'] = {}

                            if 'operators' not in behaviour['components']:
                                behaviour['components']['operator'] = {}

                            new_behaviour_widgets = {}

                            for widget_id, widget_data in behaviour['components']['widget'].items():
                                new_behaviour_widgets[iwidget_mapping.get(int(widget_id)) or widget_id] = widget_data

                            behaviour['components']['widget'] = new_behaviour_widgets

                        if not 'operators' in wiring_status['visualdescription']['components']:
                            wiring_status['visualdescription']['components']['operator'] = {}

                        if not 'widgets' in wiring_status['visualdescription']['components']:
                            wiring_status['visualdescription']['components']['widget'] = {}

                        new_components_widgets = {}
                        for widget_id, widget_data in wiring_status['visualdescription']['components']['widget'].items():
                            new_components_widgets[iwidget_mapping.get(int(widget_id)) or widget_id] = widget_data

                        wiring_status['visualdescription']['components']['widget'] = new_components_widgets

                        for connection in wiring_status['visualdescription']['connections']:
                            sourcename_parts = connection['sourcename'].split('/')
                            if len(sourcename_parts) == 3 and sourcename_parts[0] == 'widget':
                                connection['sourcename'] = f"widget/{iwidget_mapping.get(int(sourcename_parts[1])) or sourcename_parts[1]}/{sourcename_parts[2]}"

                            targetname_parts = connection['targetname'].split('/')
                            if len(targetname_parts) == 3 and targetname_parts[0] == 'widget':
                                connection['targetname'] = f"widget/{iwidget_mapping.get(int(targetname_parts[1])) or targetname_parts[1]}/{targetname_parts[2]}"

                        await new_db_session.client.workspaces.update_one(
                            {"_id": ObjectId(new_workspace.id)},
                            {"$set": {"wiring_status": wiring_status}}
                        )
                except Exception as e:
                    print(f"    ⚠ Could not migrate wiring configuration: {e}")


                await commit(new_db_session)
                workspace_count += 1
                print(f"  ✓ {workspace['name']}")

            except Exception as e:
                print(f"  ✗ Failed to migrate workspace '{workspace.get('name', '?')}': {e}")
                traceback.print_exc()

    return workspace_count


def setup_commands(subparsers: argparse._SubParsersAction) -> dict[str, Callable]:
    migrate = subparsers.add_parser(
        "migrate",
        help="Migrate data from old Wirecloud instance (Django/SQL) to new version (FastAPI/MongoDB)"
    )

    # Connection parameters
    migrate.add_argument(
        "-u", "--url",
        required=True,
        help="URL of the old Wirecloud instance (e.g., http://localhost:8000)"
    )
    migrate.add_argument(
        "--admin-user",
        required=True,
        help="Admin username for the old Wirecloud instance"
    )
    migrate.add_argument(
        "--admin-password",
        required=True,
        help="Admin password for the old Wirecloud instance"
    )

    # Database parameters
    migrate.add_argument(
        "--db-type",
        choices=['mysql', 'postgresql', 'sqlite'],
        default='mysql',
        help="Database type: mysql, postgresql, or sqlite (default: mysql)"
    )
    migrate.add_argument(
        "--db-host",
        default="localhost",
        help="Database host (default: localhost). Not used for SQLite."
    )
    migrate.add_argument(
        "--db-port",
        type=int,
        default=None,
        help="Database port (default: 3306 for MySQL, 5432 for PostgreSQL). Not used for SQLite."
    )
    migrate.add_argument(
        "--db-name",
        required=True,
        help="Database name (for SQLite, this is the path to the .db file)"
    )
    migrate.add_argument(
        "--db-user",
        default=None,
        help="Database username. Not used for SQLite."
    )
    migrate.add_argument(
        "--db-password",
        default=None,
        help="Database password. Not used for SQLite."
    )


    # Options
    migrate.add_argument(
        "--no-verify-ssl",
        action="store_true",
        help="Disable SSL certificate verification"
    )
    migrate.add_argument(
        "-y", "--yes",
        action="store_true",
        help="Skip confirmation prompt"
    )

    return {
        "migrate": migrate_cmd
    }
