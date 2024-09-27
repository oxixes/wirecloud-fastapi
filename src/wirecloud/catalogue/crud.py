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

from bson import ObjectId

from src.wirecloud.catalogue.schemas import (CatalogueResourceCreate, CatalogueResource, CatalogueResourceBase)
from src.wirecloud.catalogue.models import DBCatalogueResource as CatalogueResourceModel
from src.wirecloud.commons.auth.schemas import UserAll, User, Group
from src.wirecloud.commons.utils.template.schemas.macdschemas import (MACD, Vendor, Name, Version)
from src.wirecloud.database import DBSession, Id


def build_schema_from_resource(resource: CatalogueResourceModel) -> CatalogueResource:
    return CatalogueResource(
        id=resource.id,
        vendor=resource.vendor,
        short_name=resource.short_name,
        version=resource.version,
        type=resource.type,
        public=resource.public,
        creation_date=resource.creation_date,
        template_uri=resource.template_uri,
        popularity=resource.popularity,
        description=resource.description
    )


async def create_catalogue_resource(db: DBSession, resource: CatalogueResourceCreate) -> CatalogueResource:
    if not db.in_transaction:
        db.start_transaction()

    catalogue = CatalogueResourceModel(
        vendor=resource.vendor,
        short_name=resource.short_name,
        version=resource.version,
        type=resource.type.value,
        public=resource.public,
        creation_date=resource.creation_date,
        template=resource.template,
        popularity=resource.popularity,
        json_description=resource.description.model_dump_json()
    )
    result = await db.client.catalogue_resources.insert_one(catalogue)
    await db.commit_transaction()

    if result.inserted_id is None:
        raise ValueError('Resource not created')

    return CatalogueResource(
        id=result.inserted_id,
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
    query = {"vendor": vendor, "short_name": short_name, "version": version}
    result = await db.client.catalogue_resources.find_one(query)

    if result is None:
        return None

    return build_schema_from_resource(CatalogueResourceModel.model_validate(result))


async def has_resource_user(db: DBSession, resource_id: Id, user_id: Id) -> bool:
    # Checks if the resource is owned by the user (present in CatalogueResource.users)
    query = {"_id": ObjectId(resource_id), "creator_id": ObjectId(user_id)}
    result = await db.client.catalogue_resources.find_one(query)

    return result is not None


async def is_resource_available_for_user(db: DBSession, resource: CatalogueResourceBase, user: UserAll) -> bool:
    # Checks if the resource is public or owned by the user
    if resource.public:
        return True

    # Check if the resource is available for the user or any of the groups the user belongs to
    user_query = {"_id": ObjectId(resource.id), "users": ObjectId(user.id)}
    creator_query = {"_id": ObjectId(resource.id), "creator_id": ObjectId(user.id)}
    group_query = {"_id": ObjectId(resource.id), "groups": {"$in": [ObjectId(group.id) for group in user.groups]}}

    result = await db.client.catalogue_resources.find_one({"$or": [user_query, creator_query, group_query]})

    return result is not None


async def get_all_catalogue_resource_versions(db: DBSession, vendor: Vendor, short_name: Name) -> list[CatalogueResource]:
    query = {"vendor": vendor, "short_name": short_name}

    resources = [CatalogueResourceModel.model_validate(resource) for resource in
                 await db.client.catalogue_resources.find(query)]

    return [build_schema_from_resource(resource) for resource in resources]


async def get_catalogue_resource_versions_for_user(db: DBSession, vendor: Optional[Vendor] = None,
                                                   short_name: Optional[Name] = None,
                                                   user: Optional[UserAll] = None) -> list[CatalogueResource]:
    # Gets all public resources and the resources owned by the user or the groups the user belongs to
    public_resources_query = {"vendor": vendor if vendor is not None else True,
                              "short_name": short_name if short_name is not None else True, "public": True}

    if user is None:
        query = public_resources_query
    else:
        user_resources_query = {"vendor": vendor if vendor is not None else True,
                                "short_name": short_name if short_name is not None else True,
                                "creator_id": ObjectId(user.id)}
        creator_resources_query = {"vendor": vendor if vendor is not None else True,
                                   "short_name": short_name if short_name is not None else True,
                                   "users": ObjectId(user.id)}
        group_resources_query = {"vendor": vendor if vendor is not None else True,
                                 "short_name": short_name if short_name is not None else True,
                                 "groups": {"$in": [ObjectId(group.id) for group in user.groups]}}

        query = {"$or": [public_resources_query, user_resources_query, creator_resources_query, group_resources_query]}

    result = await db.client.catalogue_resources.find(query).to_list()
    resources = [CatalogueResourceModel.model_validate(resource) for resource in result]

    return [build_schema_from_resource(resource) for resource in resources]


async def get_all_catalogue_resources(db: DBSession) -> list[CatalogueResource]:
    result = await db.client.catalogue_resources.find()
    resources = [CatalogueResourceModel.model_validate(resource) for resource in result]

    return [build_schema_from_resource(resource) for resource in resources]


async def update_catalogue_resource_description(db: DBSession, resource_id: Id, description: MACD) -> None:
    if not db.in_transaction:
        db.start_transaction()
    query = {"_id": ObjectId(resource_id)}
    update = {"$set": {"description": description.model_dump_json()}}
    await db.client.catalogue_resources.update_one(query, update)


async def delete_catalogue_resources(db: DBSession, resource_ids: list[Id]) -> None:
    if not db.in_transaction:
        db.start_transaction()
    query = {"_id": {"$in": ObjectId(resource_ids)}}
    await db.client.catalogue_resources.delete_many(query)


async def mark_resources_as_not_available(db: DBSession, resources: list[CatalogueResource]) -> None:
    if not db.in_transaction:
        db.start_transaction()
    for resource in resources:
        await db.client.catalogue_resources.update_one({"_id": ObjectId(resource.id)}, {"$set": {"template_uri": ""}})


async def change_resource_publicity(db: DBSession, resource: CatalogueResource, public: bool) -> None:
    if not db.in_transaction:
        db.start_transaction()
    await db.client.catalogue_resources.update_one({"_id": ObjectId(resource.id)}, {"$set": {"public": public}})


async def install_resource_to_user(db: DBSession, resource: CatalogueResource, user: User) -> bool:
    if not db.in_transaction:
        db.start_transaction()
    # Check integrity
    query = {"_id": ObjectId(resource.id), "user_id": ObjectId(user.id)}
    result = await db.client.catalogue_resource_users.find_one(query)
    if result is not None:
        return False
    else:
        await db.client.catalogue_resource_users.insert_one(
            {"_id": ObjectId(resource.id), "user_id": ObjectId(user.id)})
        await db.commit_transaction()
        return True


async def install_resource_to_group(db: DBSession, resource: CatalogueResource, group: Group) -> bool:
    # Check integrity
    if not db.in_transaction:
        db.start_transaction()
    query = {"_id": ObjectId(resource.id), "groups": ObjectId(group.id)}
    result = await db.client.catalogue_resources.find_one(query)
    if result is not None:
        return False
    else:
        await db.client.catalogue_resources.update_one({"_id": ObjectId(resource.id)},
                                                       {"$push": {"groups": ObjectId(group.id)}})
        await db.commit_transaction()
        return True