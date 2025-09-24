# -*- coding: utf-8 -*-
# Copyright (c) 2024 Future Internet Consulting and Development Solutions S.L.
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

import aiohttp
import asyncio
from typing import Optional

from src import settings
from src.wirecloud.commons.auth.crud import update_user
from src.wirecloud.commons.auth.schemas import UserAll
from src.wirecloud.database import DBSession
from src.wirecloud.platform.plugins import get_idm_get_token_functions


async def first_step_openstack(url: str, idm_token: str) -> str:
    payload = {
        "auth": {
            "identity": {
                "methods": ["oauth2"],
                "oauth2": {
                    "access_token_id": idm_token
                }
            }
        }
    }

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload, headers=headers, ssl=getattr(settings, "WIRECLOUD_HTTPS_VERIFY", True)) as response:
            if response.status != 200 and response.status != 201:
                raise Exception(f"Error in OpenStack authentication: {response.status} {await response.text()}")
            token = response.headers.get("X-Subject-Token")
            if not token:
                raise Exception("No token received from OpenStack")
            return token


async def get_projects(url: str, general_token: str, username: str) -> dict:
    headers = {
        "X-Auth-Token": general_token,
        "Accept": "application/json"
    }

    payload = {"user.id": username}

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, params=payload, ssl=getattr(settings, "WIRECLOUD_HTTPS_VERIFY", True)) as response:
            if response.status != 200:
                raise Exception(f"Error retrieving projects: {response.status} {await response.text()}")
            projects = await response.json()
            return projects


async def get_project_permissions(url: str, token: str) -> dict:
    headers = {
        "X-Auth-Token": token,
        "Accept": "application/json"
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, ssl=getattr(settings, "WIRECLOUD_HTTPS_VERIFY", True)) as response:
            if response.status != 200:
                raise Exception(f"Error retrieving project permissions: {response.status} {await response.text()}")
            permissions = await response.json()
            return permissions


async def get_openstack_project_token(url: str, project_id: str, idm_token: str) -> str:
    payload = {
        "auth": {
            "identity": {
                "methods": ["oauth2"],
                "oauth2": {
                    "access_token_id": idm_token
                }
            },
            "scope": {
                "project": {
                    "id": project_id
                }
            }
        }
    }

    headers = {
        "Content-Type": "application/json"
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload, headers=headers, ssl=getattr(settings, "WIRECLOUD_HTTPS_VERIFY", True)) as response:
            if response.status != 200 and response.status != 201:
                raise Exception(f"Error in OpenStack project authentication: {response.status} {await response.text()}")
            token = response.headers.get("X-Subject-Token")
            if not token:
                raise Exception("No project token received from OpenStack")
            return token


class OpenStackTokenManager:
    def __init__(self, url: str):
        self.url = url

    async def get_token(self, db: DBSession, user: UserAll, tenant_id: Optional[str]) -> str:
        tenant_id = "__default__" if tenant_id is None else tenant_id
        if "openstack_token" in user.idm_data and tenant_id in user.idm_data["openstack_token"]:
            return user.idm_data["openstack_token"][tenant_id]

        if not getattr(settings, "OID_CONNECT_ENABLED", False):
            raise Exception("OIDC is not enabled")

        if not getattr(settings, "OID_CONNECT_PLUGIN", "") in get_idm_get_token_functions():
            raise Exception("OIDC provider is not configured correctly! Contact your administrator.")

        token_data_get_func = get_idm_get_token_functions()[getattr(settings, "OID_CONNECT_PLUGIN")]

        try:
            if asyncio.iscoroutinefunction(token_data_get_func):
                token_data = await token_data_get_func(refresh_token=user.idm_data[getattr(settings, "OID_CONNECT_PLUGIN")]["idm_token"], code=None, redirect_uri=None)
            else:
                token_data = token_data_get_func(refresh_token=user.idm_data[getattr(settings, "OID_CONNECT_PLUGIN")]["idm_token"], code=None, redirect_uri=None)
        except ValueError as e:
            raise Exception(f"Error retrieving token from IDM: {str(e)}")

        os_token = await self.get_openstack_token(user.username, token_data["access_token"], tenant_id)

        user.idm_data[getattr(settings, "OID_CONNECT_PLUGIN")]["openstack_token"] = os_token
        user.idm_data[getattr(settings, "OID_CONNECT_PLUGIN")]["idm_token"] = token_data["refresh_token"]

        await update_user(db, user)

        return os_token

    async def get_openstack_token(self, username: str, idm_token: str, tenant_id: Optional[str]) -> str:
        # We love FIWARE process to get the token <3

        # Fist we get an initial token
        general_token = await first_step_openstack(f"{self.url}/keystone/v3/auth/tokens", idm_token)

        # Then we ask for all the projects the user have
        projects = await get_projects(f"{self.url}/keystone/v3/role_assignments", general_token, username)

        for role in projects["role_assignments"]:
            if role.get("scope", None) is not None and role["scope"].get("project", None) is not None:
                project_id = role["scope"]["project"]["id"]

                # Ask for permissions for every project
                permissions = await get_project_permissions(f"{self.url}/keystone/v3/projects/{project_id}", general_token)
                if permissions.get("project").get("is_cloud_project") and (
                        tenant_id == "__default__" or permissions.get("project").get("id") == tenant_id):
                    # And if the project was cloud, we finally ask for the token
                    return await get_openstack_project_token(f"{self.url}/keystone/v3/auth/tokens", project_id, idm_token)

        # if we are here, we didn't detected any openstack token
        raise Exception("No OpenStack cloud project found for the user")