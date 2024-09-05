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

from typing import Optional
from sqlalchemy import insert, select, update, delete, union
from sqlalchemy.exc import IntegrityError

from src.wirecloud.catalogue.schemas import (CatalogueResourceCreate, CatalogueResource, CatalogueResourceType,
                                             CatalogueResourceBase)
from src.wirecloud.catalogue.models import (CatalogueResource as CatalogueResourceModel,
                                            CatalogueResourceUsers as CatalogueResourceUsersModel,
                                            CatalogueResourceGroups as CatalogueResourceGroupsModel)
from src.wirecloud.commons.auth.schemas import UserAll, User, Group
from src.wirecloud.commons.utils.template.schemas.macdschemas import (MACD, MACDWidget, MACDOperator, MACDMashup,
                                                                      Vendor, Name, Version)
from src.wirecloud.database import DBSession


def build_schema_from_resource(resource: CatalogueResourceModel) -> CatalogueResource:
    desc = None
    mac_type = CatalogueResourceType(resource.type)
    if mac_type == CatalogueResourceType.widget:
        desc = MACDWidget.model_validate_json(resource.json_description)
    elif mac_type == CatalogueResourceType.operator:
        desc = MACDOperator.model_validate_json(resource.json_description)
    elif mac_type == CatalogueResourceType.mashup:
        desc = MACDMashup.model_validate_json(resource.json_description)

    assert desc is not None

    return CatalogueResource(
        id=resource.id,
        vendor=resource.vendor,
        short_name=resource.short_name,
        version=resource.version,
        type=mac_type,
        public=resource.public,
        creation_date=resource.creation_date,
        template_uri=resource.template_uri,
        popularity=resource.popularity,
        description=desc
    )


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
    query = select(CatalogueResourceModel.id).where(
        CatalogueResourceModel.vendor == resource.vendor,
        CatalogueResourceModel.short_name == resource.short_name,
        CatalogueResourceModel.version == resource.version
    )

    result = await db.execute(query)
    resource_id = result.scalar()

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


async def get_catalogue_resource(db: DBSession, vendor: Vendor, short_name: Name, version: Version) -> Optional[CatalogueResource]:
    query = select(CatalogueResourceModel).where(
        CatalogueResourceModel.vendor == vendor,
        CatalogueResourceModel.short_name == short_name,
        CatalogueResourceModel.version == version
    )

    result = await db.execute(query)
    resource = result.scalar()

    if resource is None:
        return None

    return build_schema_from_resource(resource)


async def has_resource_user(db: DBSession, resource_id: int, user_id: int) -> bool:
    # Checks if the resource is owned by the user (present in CatalogueResource.users)
    query = select(CatalogueResourceUsersModel.id).where(
        CatalogueResourceUsersModel.catalogueresource_id == resource_id,
        CatalogueResourceUsersModel.user_id == user_id
    )

    result = await db.execute(query)
    return result.scalar() is not None


async def is_resource_available_for_user(db: DBSession, resource: CatalogueResourceBase, user: UserAll) -> bool:
    # Checks if the resource is public or owned by the user
    if resource.public:
        return True

    # Check if the resource is available for the user or any of the groups the user belongs to
    user_query = select(CatalogueResourceUsersModel.id).where(
        CatalogueResourceUsersModel.catalogueresource_id == resource.id,
        CatalogueResourceUsersModel.user_id == user.id
    )

    group_query = select(CatalogueResourceGroupsModel.id).where(
        CatalogueResourceGroupsModel.catalogueresource_id == resource.id,
        CatalogueResourceGroupsModel.group_id.in_([group.id for group in user.groups])
    )

    # Union of the two queries
    query = user_query.union(group_query)

    result = await db.execute(query)

    return result.scalar() is not None


async def get_all_catalogue_resource_versions(db: DBSession, vendor: Vendor, short_name: Name) -> list[CatalogueResource]:
    query = select(CatalogueResourceModel).where(
        CatalogueResourceModel.vendor == vendor,
        CatalogueResourceModel.short_name == short_name
    )

    result = await db.execute(query)
    resources = result.scalars().all()

    return [build_schema_from_resource(resource) for resource in resources]


async def get_catalogue_resource_versions_for_user(db: DBSession, vendor: Optional[Vendor] = None,
                                                   short_name: Optional[Name] = None,
                                                   user: Optional[UserAll] = None) -> list[CatalogueResource]:
    # Gets all public resources and the resources owned by the user or the groups the user belongs to
    public_resources_query = select(CatalogueResourceModel).where(
        CatalogueResourceModel.vendor == vendor if vendor is not None else True,
        CatalogueResourceModel.short_name == short_name if short_name is not None else True,
        CatalogueResourceModel.public.is_(True)
    )

    if user is None:
        query = public_resources_query
    else:
        user_resources_query = select(CatalogueResourceModel) \
            .join(CatalogueResourceUsersModel,
                  CatalogueResourceModel.id == CatalogueResourceUsersModel.catalogueresource_id) \
            .where(
                CatalogueResourceModel.vendor == vendor if vendor is not None else True,
                CatalogueResourceModel.short_name == short_name if short_name is not None else True,
                CatalogueResourceUsersModel.user_id == user.id
            )

        group_resources_query = select(CatalogueResourceModel) \
            .join(CatalogueResourceGroupsModel,
                  CatalogueResourceModel.id == CatalogueResourceGroupsModel.catalogueresource_id) \
            .where(
                CatalogueResourceModel.vendor == vendor if vendor is not None else True,
                CatalogueResourceModel.short_name == short_name if short_name is not None else True,
                CatalogueResourceGroupsModel.group_id.in_([group.id for group in user.groups])
            )

        combined_query = union(public_resources_query, user_resources_query, group_resources_query).alias()
        query = select(CatalogueResourceModel).select_from(combined_query).where(
            CatalogueResourceModel.id == combined_query.c.id
        )

    result = await db.execute(query)
    resources = result.scalars().all()

    return [build_schema_from_resource(resource) for resource in resources]


async def get_all_catalogue_resources(db: DBSession) -> list[CatalogueResource]:
    query = select(CatalogueResourceModel)

    result = await db.execute(query)
    resources = result.scalars().all()

    return [build_schema_from_resource(resource) for resource in resources]


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


async def mark_resources_as_not_available(db: DBSession, resources: list[CatalogueResource]) -> None:
    await db.execute(
        update(CatalogueResourceModel).where(CatalogueResourceModel.id.in_([resource.id for resource in resources])).values(
            template_uri=""
        )
    )


async def change_resource_publicity(db: DBSession, resource: CatalogueResource, public: bool) -> None:
    await db.execute(
        update(CatalogueResourceModel).where(CatalogueResourceModel.id == resource.id).values(
            public=public
        )
    )


async def install_resource_to_user(db: DBSession, resource: CatalogueResource, user: User) -> bool:
    # Check integrity
    try:
        await db.execute(
            insert(CatalogueResourceUsersModel).values(
                catalogueresource_id=resource.id,
                user_id=user.id
            )
        )
        await db.commit()
    except IntegrityError:
        await db.rollback()
        return False

    return True


async def install_resource_to_group(db: DBSession, resource: CatalogueResource, group: Group) -> bool:
    # Check integrity
    try:
        await db.execute(
            insert(CatalogueResourceGroupsModel).values(
                catalogueresource_id=resource.id,
                group_id=group.id
            )
        )
        await db.commit()
    except IntegrityError:
        await db.rollback()
        return False

    return True
