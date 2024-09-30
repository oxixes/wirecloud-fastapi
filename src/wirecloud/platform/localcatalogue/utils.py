# -*- coding: utf-8 -*-

# Copyright (c) 2012-2015 CoNWeT Lab., Universidad Politécnica de Madrid
# Copyright (c) 2019 Future Internet Consulting and Development Solutions S.L.

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

import re
from typing import Optional

from src.wirecloud.database import DBSession
from src.wirecloud.commons.utils.wgt import WgtFile
from src.wirecloud.catalogue.utils import add_packaged_resource, check_vendor_permissions
from src.wirecloud.catalogue.crud import (get_catalogue_resource, delete_catalogue_resources, install_resource_to_user,
                                          install_resource_to_group, change_resource_publicity)
from src.wirecloud.commons.auth.schemas import UserAll, User, Group
from src.wirecloud.catalogue.schemas import CatalogueResource
from src.wirecloud.commons.utils.template import TemplateParser
from src.wirecloud.commons.utils.http import PermissionDenied
from src.wirecloud.commons.utils.template.writers.json import write_json_description


async def install_resource(db: DBSession, wgt_file: WgtFile, executor_user: Optional[UserAll], restricted: bool = False) -> CatalogueResource:
    if not isinstance(wgt_file, WgtFile):
        raise TypeError('wgt_file must be a WgtFile')

    file_contents = wgt_file.get_underlying_file()
    template_contents = wgt_file.get_template()

    template = TemplateParser(template_contents)
    resource_version = template.get_resource_version()
    if restricted:
        if '-dev' in resource_version:
            raise PermissionDenied("dev versions cannot be published")
        vendor = template.get_resource_vendor()
        if await check_vendor_permissions(db, executor_user, vendor) is False:
            raise PermissionDenied("You don't have persmissions to publish in name of {}".format(vendor))

    resource = await get_catalogue_resource(db, template.get_resource_vendor(), template.get_resource_name(), template.get_resource_version())

    # Create/recreate/recover catalogue resource
    if resource is None:
        resource = await add_packaged_resource(db, file_contents, executor_user, wgt_file=wgt_file)
    elif '-dev' in resource_version:
        # dev version are automatically overwritten
        await delete_catalogue_resources(db, [resource.id])
        await db.commit_transaction()
        resource = await add_packaged_resource(db, file_contents, executor_user, wgt_file=wgt_file)

    return resource


async def install_component(db: DBSession, file_contents: WgtFile, executor_user: Optional[UserAll] = None,
                            public: bool = False, users: list[User] = [], groups: list[Group] = [],
                            restricted: bool = False) -> tuple[bool, CatalogueResource]:
    resource = await install_resource(db, file_contents, executor_user, restricted=restricted)
    initially_available = False
    if executor_user is not None:
        initially_available = await resource.is_available_for(db, executor_user)
    installed_to_someone = False

    # TODO Send signals or whatever system we will implement to notify the installation of the resource
    change = public is True and resource.public is False
    if change:
        await change_resource_publicity(db, resource, True)
        # resource_installed.send(sender=resource)
        installed_to_someone = True

    for user in users:
        change = await install_resource_to_user(db, resource, user)
        installed_to_someone |= change
        if change and not public:
            # resource_installed.send(sender=resource, user=user)
            pass

    for group in groups:
        change = await install_resource_to_group(db, resource, group)
        installed_to_someone |= change
        if change and not public:
            # resource_installed.send(sender=resource, group=group)
            pass

    if executor_user is not None:
        finally_available = await resource.is_available_for(db, executor_user)
        return initially_available is False and finally_available is True, resource
    else:
        return installed_to_someone, resource


def fix_dev_version(wgt_file: WgtFile, user: User) -> None:
    template_contents = wgt_file.get_template()
    template = TemplateParser(template_contents)

    resource_info = template.get_resource_info()

    # Add user name to the version if the component is in development
    if '-dev' in resource_info.version:
        # User name added this way to prevent users to upload a version
        # *.*-devAnotherUser that would be accepted but might collide with
        # AnotherUser's development version
        resource_info.version = re.sub('-dev.*$', '-dev' + user.username, resource_info.version)
        template_string = write_json_description(resource_info)
        wgt_file.update_config(template_string)
