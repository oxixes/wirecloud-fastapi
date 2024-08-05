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

from sqlalchemy import insert, select, update, delete

from src.wirecloud.catalogue.schemas import CatalogueResourceCreate, CatalogueResource, CatalogueResourceType
from src.wirecloud.catalogue.models import (CatalogueResource as CatalogueResourceModel,
                                            CatalogueResourceUsers as CatalogueResourceUsersModel)
from src.wirecloud.commons.utils.template.schemas.macdschemas import MACD
from src.wirecloud.database import DBSession


async def create_catalogue_resource(db: DBSession, resource: CatalogueResourceCreate) -> CatalogueResource:
    await db.execute(
        insert(CatalogueResourceModel).values(
            vendor=resource.vendor,
            short_name=resource.short_name,
            version=resource.version,
            type=resource.type.value,
            public=resource.public,
            creation_date=resource.creation_date,
            template_uri=resource.template_uri,
            popularity=resource.popularity,
            json_description=resource.description.model_dump_json(),
            creator_id=resource.creator.id
        )
    )

    await db.commit()

    # Obtain the id of the created resource
    query = select([CatalogueResourceModel.id]).where(
        CatalogueResourceModel.vendor == resource.vendor,
        CatalogueResourceModel.short_name == resource.short_name,
        CatalogueResourceModel.version == resource.version
    )

    result = await db.execute(query)
    resource_id = await result.scalar()

    if resource_id is None:
        raise ValueError('Resource not created')

    return CatalogueResource(
        id=resource_id,
        vendor=resource.vendor,
        short_name=resource.short_name,
        version=resource.version,
        type=resource.type,
        public=resource.public,
        creation_date=resource.creation_date,
        template_uri=resource.template_uri,
        popularity=resource.popularity,
        description=resource.description,
    )


async def has_resource_user(db: DBSession, resource_id: int, user_id: int) -> bool:
    # Checks if the resource is owned by the user (present in CatalogueResource.users)
    query = select([CatalogueResourceUsersModel.id]).where(
        CatalogueResourceUsersModel.catalogueresource_id == resource_id,
        CatalogueResourceUsersModel.user_id == user_id
    )

    result = await db.execute(query)
    return await result.scalar() is not None


async def get_all_catalogue_resource_versions(db: DBSession, vendor: str, short_name: str) -> list[CatalogueResource]:
    query = select([CatalogueResourceModel]).where(
        CatalogueResourceModel.vendor == vendor,
        CatalogueResourceModel.short_name == short_name
    )

    result = await db.execute(query)
    resources = result.scalars().all()

    return [CatalogueResource(
        id=resource.id,
        vendor=resource.vendor,
        short_name=resource.short_name,
        version=resource.version,
        type=CatalogueResourceType(resource.type),
        public=resource.public,
        creation_date=resource.creation_date,
        template_uri=resource.template_uri,
        popularity=resource.popularity,
        description=MACD.model_validate_json(resource.json_description)
    ) for resource in resources]


async def get_all_catalogue_resources(db: DBSession) -> list[CatalogueResource]:
    query = select([CatalogueResourceModel])

    result = await db.execute(query)
    resources = result.scalars().all()

    return [CatalogueResource(
        id=resource.id,
        vendor=resource.vendor,
        short_name=resource.short_name,
        version=resource.version,
        type=CatalogueResourceType(resource.type),
        public=resource.public,
        creation_date=resource.creation_date,
        template_uri=resource.template_uri,
        popularity=resource.popularity,
        description=MACD.model_validate_json(resource.json_description)
    ) for resource in resources]


async def update_catalogue_resource_description(db: DBSession, resource_id: int, description: MACD) -> None:
    await db.execute(
        update(CatalogueResourceModel).where(CatalogueResourceModel.id == resource_id).values(
            json_description=description.model_dump_json()
        )
    )


async def delete_catalogue_resources(db: DBSession, resource_ids: list[int]) -> None:
    await db.execute(
        delete(CatalogueResourceModel).where(CatalogueResourceModel.id.in_(resource_ids))
    )
