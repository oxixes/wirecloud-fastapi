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

from pydantic import BaseModel, Field, field_validator
from enum import Enum
from datetime import datetime
from urllib.parse import urlparse
from fastapi import Request
from typing import Optional
import random

from wirecloud.settings import cache
from wirecloud.catalogue.models import XHTML
from wirecloud.commons.utils.template.schemas.macdschemas import MACD, MACType, Vendor, Name, Version
from wirecloud.commons.utils.template.base import Contact
from wirecloud.commons.auth.schemas import User, UserAll
from wirecloud.commons.utils.http import get_absolute_reverse_url
from wirecloud.commons.utils.template import TemplateParser
from wirecloud.database import DBSession, Id

from wirecloud.catalogue import docs

RESOURCE_MIMETYPES = ('application/x-widget+mashable-application-component',
                      'application/x-mashup+mashable-application-component',
                      'application/x-operator+mashable-application-component')


class CatalogueResourceType(Enum):
    widget = 0
    mashup = 1
    operator = 2


class CatalogueResourceBase(BaseModel):
    vendor: str
    short_name: str
    version: str
    type: CatalogueResourceType
    public: bool
    creation_date: datetime
    template_uri: str
    popularity: float
    description: MACD

    @property
    def local_uri_part(self) -> str:
        return self.vendor + '/' + self.short_name + '/' + self.version

    async def is_removable_by(self, db: DBSession, user: UserAll, vendor: bool = False) -> bool:
        from wirecloud.catalogue.utils import check_vendor_permissions

        if user.is_superuser:
            return True
        elif not user.has_perm("COMPONENT.UNINSTALL"):
            return False
        else:
            return vendor is False or await check_vendor_permissions(db, user, self.vendor)

    def get_template_url(self, request: Optional[Request] = None, for_base: bool = False,
                         url_pattern_name: str = 'wirecloud_catalogue.media') -> str:
        return get_template_url(self.vendor, self.short_name, self.version, '' if for_base else self.template_uri,
                                request=request, url_pattern_name=url_pattern_name)

    def get_template(self, request: Optional[Request] = None,
                     url_pattern_name: str = 'wirecloud_catalogue.media') -> TemplateParser:
        template_uri = self.get_template_url(request=request, url_pattern_name=url_pattern_name)
        parser = TemplateParser(self.description.model_dump_json(), base=template_uri)
        return parser

    def get_processed_info(self, request: Optional[Request] = None, lang: Optional[str] = None,
                           process_urls: bool = True, translate: bool = True, process_variables: bool = False,
                           url_pattern_name: str = 'wirecloud_catalogue.media') -> MACD:
        # TODO Handle translations
        lang = None

        parser = self.get_template(request, url_pattern_name=url_pattern_name)
        processed_info = parser.get_resource_processed_info(lang=lang, process_urls=process_urls, translate=True,
                                                            process_variables=process_variables)

        return processed_info

    def resource_type(self) -> str:
        return self.type.name

    @property
    def mimetype(self) -> str:
        return RESOURCE_MIMETYPES[self.type.value]

    def __str__(self) -> str:
        return self.local_uri_part


class CatalogueResourceCreate(CatalogueResourceBase):
    creator: Optional[User]


class CatalogueResource(CatalogueResourceBase, populate_by_name=True):
    id: Id = Field(alias="_id")
    users: list[str]
    groups: list[str]

    def is_available_for(self, user: Optional[UserAll]) -> bool:
        has_global_view = user and user.has_perm("COMPONENT.VIEW")
        if not has_global_view:
            allowed = False
            if self.public:
                allowed = True
            elif user is not None:
                if str(user.id) in self.users:
                    allowed = True
                elif any(str(group_id) in self.groups for group_id in user.groups):
                    allowed = True
            return allowed
        return True

    def is_installed_for(self, user: Optional[UserAll]) -> bool:
        if user is None:
            return False
        if self.public or str(user.id) in self.users:
            return True
        return any(str(group_id) in self.groups for group_id in user.groups)

    @property
    def cache_version_key(self) -> str:
        return f"_catalogue_resource_version/{self.id}"

    @property
    async def cache_version(self):
        version = await cache.get(self.cache_version_key)
        if version is None:
            version = random.randrange(1, 100000)
            await cache.set(self.cache_version_key, version)

        return version

    @field_validator("users", "groups", mode="before")
    @classmethod
    def convert_objectid_to_str(cls, v):
        if not v:
            return []
        return [str(item) for item in v]


class CatalogueResourceXHTML(CatalogueResource):
    xhtml: Optional[XHTML]


class CatalogueResourceDataSummaryPermissions(BaseModel):
    delete: bool = Field(description=docs.catalogue_resource_data_summary_permissions_delete_description)
    uninstall: bool = Field(description=docs.catalogue_resource_data_summary_permissions_uninstall_description)


class CatalogueResourceDataSummaryBase(BaseModel):
    version: Version = Field(description=docs.catalogue_resource_data_summary_version_description)
    date: float = Field(description=docs.catalogue_resource_data_summary_date_description)
    permissions: CatalogueResourceDataSummaryPermissions = Field(
        description=docs.catalogue_resource_data_summary_permissions_description)
    authors: list[Contact] = Field(description=docs.catalogue_resource_data_summary_authors_description)
    contributors: list[Contact] = Field(description=docs.catalogue_resource_data_summary_contributors_description)
    title: str = Field(description=docs.catalogue_resource_data_summary_title_description)
    description: str = Field(description=docs.catalogue_resource_data_summary_description_description)
    longdescription: str = Field(description=docs.catalogue_resource_data_summary_longdescription_description)
    email: str = Field(description=docs.catalogue_resource_data_summary_email_description)
    image: str = Field(description=docs.catalogue_resource_data_summary_image_description)
    homepage: str = Field(description=docs.catalogue_resource_data_summary_homepage_description)
    doc: str = Field(description=docs.catalogue_resource_data_summary_doc_description)
    changelog: str = Field(description=docs.catalogue_resource_data_summary_changelog_description)
    size: int = Field(description=docs.catalogue_resource_data_summary_size_description)
    uriTemplate: str = Field(description=docs.catalogue_resource_data_summary_uri_template_description)
    license: str = Field(description=docs.catalogue_resource_data_summary_license_description)
    licenseurl: str = Field(description=docs.catalogue_resource_data_summary_licenseurl_description)
    issuetracker: str = Field(description=docs.catalogue_resource_data_summary_issuetracker_description)


class CatalogueResourceDataSummaryIdentifier(BaseModel, use_enum_values=True):
    vendor: Vendor = Field(description=docs.catalogue_resource_data_summary_vendor_description)
    name: Name = Field(description=docs.catalogue_resource_data_summary_name_description)
    type: MACType = Field(description=docs.catalogue_resource_data_summary_type_description)


class CatalogueResourceDataSummary(CatalogueResourceDataSummaryBase, CatalogueResourceDataSummaryIdentifier):
    pass


class CatalogueResourceDataSummaryGroup(CatalogueResourceDataSummaryIdentifier):
    versions: list[CatalogueResourceDataSummaryBase] = Field(
        description=docs.catalogue_resource_data_summary_group_versions_description)


class CatalogueResourceDeleteResults(BaseModel):
    affectedVersions: list[Version] = Field(
        description=docs.catalogue_resource_delete_results_affected_versions_description)


def get_template_url(vendor: Vendor, name: Name, version: Version, url: str, request: Optional[Request] = None,
                     url_pattern_name: str = 'wirecloud_catalogue.media') -> str:
    if urlparse(url).scheme == '':
        template_url = get_absolute_reverse_url(url_pattern_name, request=request, vendor=vendor, name=name,
                                                version=version, file_path=url)
    else:
        template_url = url

    return template_url
