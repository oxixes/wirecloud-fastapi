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

from typing import Optional
from pydantic import BaseModel, Field

from wirecloud.commons.utils.template.schemas.macdschemas import MACD
from wirecloud.platform.localcatalogue import docs


class MultipleResourcesInstalledResponse(BaseModel):
    resource_details: MACD = Field(..., description=docs.multiple_resources_installed_response_resource_details_description)
    extra_resources: list[MACD] = Field([], description=docs.multiple_resources_installed_response_extra_resources_description)


class ResourceCreateData(BaseModel):
    install_embedded_resources: bool = Field(False, description=docs.resource_create_data_install_embedded_resources_description)
    force_create: bool = Field(False, description=docs.resource_create_data_force_create_description),
    url: str = Field(..., description=docs.resource_create_data_url_description)
    headers: dict[str, str] = Field(default_factory=dict, description=docs.resource_create_data_headers_description)

class ResourceCreateFormData(BaseModel):
    force_create: bool = Field(False, description=docs.resource_create_form_data_force_create_description)
    public: bool = Field(False, description=docs.resource_create_form_data_public_description)
    users: Optional[list[str]] = Field(None, description=docs.resource_create_form_data_users_description)
    groups: Optional[list[str]] = Field(None, description=docs.resource_create_form_data_groups_description)
    install_embedded_resources: bool = Field(False, description=docs.resource_create_form_data_install_embedded_resources_description)
    file: bytes = Field(None, description=docs.resource_create_form_data_file_description)