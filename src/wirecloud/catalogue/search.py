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

from typing import Optional, Any
from urllib.parse import urljoin

from elasticsearch._async.helpers import async_bulk
from pydantic import BaseModel
from datetime import datetime
from fastapi import Request

from wirecloud.catalogue.crud import get_all_catalogue_resources_with_usersgroups, \
    get_catalogue_resource_with_usersgroups_by_id
from wirecloud.catalogue.schemas import CatalogueResource, get_template_url, CatalogueResourceWithUsersGroups
from wirecloud.commons.auth.schemas import UserAll
from wirecloud.commons.utils.version import Version
from wirecloud.database import DBSession

RESOURCES_INDEX = 'resources'
RESOURCE_CONTENT_FIELDS = ["name^1.5", "vendor", "version", "type", "title^1.5", "description", "endpoint_descriptions"]
RESOURCE_MAPPINGS = {
    "settings": {
        "analysis": {
            "analyzer": {
                "ngram_analyzer": {
                    "tokenizer": "ngram_tokenizer",
                    "filter": ["lowercase"]
                },
                "keyword_lowercase": {
                    "tokenizer": "keyword",
                    "filter": ["lowercase"]
                }
            },
            "tokenizer": {
                "ngram_tokenizer": {
                    "type": "ngram",
                    "min_gram": 2,
                    "max_gram": 20,
                    "token_chars": ["letter", "digit"]
                }
            }
        }
    },
    "mappings": {
        "properties":{
            "id": {"type": "keyword"},
            "vendor_name": {"type": "keyword"},
            "vendor": {
                "type": "text",
                "analyzer": "ngram_analyzer",
                "search_analyzer": "standard",
                "fields": {
                    "keyword": {"type": "keyword"}
                }
            },
            "name": {
                "type": "text",
                "analyzer": "ngram_analyzer",
                "search_analyzer": "standard",
                "fields": {
                    "keyword": {"type": "keyword"}
                }
            },
            "version": {"type": "keyword"},
            "version_sortable": {"type": "float"},
            "description_url": {"type": "keyword"},
            "type": {"type": "keyword"},
            "creation_date": {"type": "date", "format": "strict_date_optional_time||epoch_millis"},
            "public": {"type": "boolean"},
            "title": {
                "type": "text",
                "analyzer": "ngram_analyzer",
                "search_analyzer": "standard"
            },
            "endpoint_descriptions": {
                "type": "text",
                "analyzer": "ngram_analyzer",
                "search_analyzer": "standard"
            },
            "description": {
                "type": "text",
                "analyzer": "ngram_analyzer",
                "search_analyzer": "standard"
            },
            "image": {"type": "keyword"},
            "smartphoneimage": {"type": "keyword"},
            "users": {"type": "keyword"},
            "groups": {"type": "keyword"},
            "input_friendcodes": {"type": "keyword"},
            "output_friendcodes": {"type": "keyword"}
        }
    }
}


class ResourceBase(BaseModel):
    id: str
    vendor_name: str
    vendor: str
    name: str
    version: str
    description_url: str
    type: str
    creation_date: datetime
    public: bool
    title: str
    description: str
    image: str
    smartphoneimage: str
    input_friendcodes: Any
    output_friendcodes: Any


class ResourceOut(ResourceBase):
    version_sortable: float
    endpoint_descriptions: str
    users: list[str]
    groups: list[str]


class ResourceOutResponse(ResourceBase):
    others: list[str]
    uri: str


def build_version_sortable(version: str):
    code = 0
    ver = Version(version)

    code += ver.version[0] * 1000 * 1000
    code += ver.version[1] * 1000 if len(ver.version) > 1 else 0
    code += ver.version[2] if len(ver.version) > 2 else 0

    prerelease = ver.prerelease
    if prerelease is None:
        code += .999
    elif prerelease[0] == "a":
        code += prerelease[1] / 1000
    elif prerelease[0] == "b":
        code += (100 + prerelease[1]) / 1000
    else:
        code += (200 + prerelease[1]) / 1000

    return code


def clean_resource_out(hit: dict, request: Request) -> ResourceOutResponse:
    source = hit["_source"]

    others = []
    if "inner_hits" in hit:
        inner_hits = hit["inner_hits"]["others"]["hits"]["hits"]
        others = [h["_source"]["version"] for h in inner_hits if h["_source"]["version"] != source["version"]]

    base_url = get_template_url(source['vendor'], source['name'], source['version'], source['description_url'], request=request)

    return ResourceOutResponse(
        id=hit["_id"],
        vendor_name=source["vendor_name"],
        vendor=source["vendor"],
        name=source["name"],
        version=source["version"],
        description_url=urljoin(base_url, source["description_url"]),
        type=source["type"],
        creation_date=source["creation_date"],
        public=source["public"],
        title=source["title"],
        description=source["description"],
        image=urljoin(base_url, source["image"]) if source.get("image") else "",
        smartphoneimage=urljoin(base_url, source["smartphoneimage"]) if source.get("smartphoneimage") else "",
        input_friendcodes=list(source.get("input_friendcodes", [])),
        output_friendcodes=list(source.get("output_friendcodes", [])),
        others=others,
        uri="/".join((source["vendor"], source["name"], source["version"]))
    )


async def search_resources(request: Request, user: Optional[UserAll], querytext: str, pagenum: int = 1, maxresults: int = 30, scope: Optional[str] = None, order_by: Optional[tuple[str]] = None) -> Optional['SearchResponse']:
    must_clauses = []
    filter_clauses = []
    if querytext:
        must_clauses.append({"multi_match": {"query": querytext, "fields": RESOURCE_CONTENT_FIELDS}})

    if scope is not None:
        filter_clauses.append({"term": {"type": scope}})

    should_clauses = []
    if user is None or not user.is_staff:
        should_clauses.append({"term": {"public": True}})
        if user is not None:
            should_clauses.append({"term": {"users": str(user.id)}})
            for group in user.groups:
                should_clauses.append({"term": {"groups": str(group)}})

    body = {
        "query": {
            "bool": {
                "must": must_clauses,
                "filter": filter_clauses,
                "should": should_clauses
            }
        },
        "collapse": {
            "field": "vendor_name",
            "inner_hits": {
                "name": "others",
                "size": 10,
                "sort": [{"version_sortable": {"order": "desc"}}],
            }
        }
    }

    body["query"]["bool"]["minimum_should_match"] = 1 if should_clauses else 0

    # if order_by and order_by no

    if not order_by:
        order_by = ("-creation_date", )

    sort_list = []
    for field in order_by:
        if field.lstrip("-") not in ResourceOutResponse.model_fields:
            return None

        order = "desc" if field.startswith("-") else "asc"

        name = field.lstrip("-")
        if name in ["vendor", "name"]:
            name += ".keyword"

        sort_list.append({name: {"order": order}})

    from wirecloud.commons.search import build_search_response
    return await build_search_response(index=RESOURCES_INDEX, body=body, pagenum=pagenum, max_results=maxresults, clean=clean_resource_out, request=request)


def prepare_resource_for_indexing(resource: CatalogueResourceWithUsersGroups) -> ResourceOut:
    resource_info = resource.get_processed_info(process_urls=False)

    endpoint_descriptions = ''
    input_friendcodes = set()
    output_friendcodes = set()

    for endpoint in resource_info.wiring.inputs:
        endpoint_descriptions += endpoint.description + ' '
        input_friendcodes.update(endpoint.friendcode.split(' '))

    for endpoint in resource_info.wiring.outputs:
        endpoint_descriptions += endpoint.description + ' '
        output_friendcodes.update(endpoint.friendcode.split(' '))

    return ResourceOut(
        id=str(resource.id),
        endpoint_descriptions=endpoint_descriptions,
        input_friendcodes=tuple(input_friendcodes),
        output_friendcodes=tuple(output_friendcodes),
        type=resource.type.name,
        users=resource.users,
        groups=resource.groups,
        version_sortable=build_version_sortable(resource.version),
        vendor_name=f'{resource.vendor}/{resource.short_name}',
        title=resource_info.title,
        description=resource_info.description,
        image=resource_info.image,
        smartphoneimage=resource_info.smartphoneimage,
        vendor=resource.vendor,
        name=resource.short_name,
        version=resource.version,
        description_url=resource.template_uri,
        creation_date=resource.creation_date,
        public=resource.public
    )


async def rebuild_resource_index(db: DBSession):
    from wirecloud.commons.search import es_client

    if await es_client.indices.exists(index=RESOURCES_INDEX):
        await es_client.indices.delete(index=RESOURCES_INDEX)

    await es_client.indices.create(index=RESOURCES_INDEX, body={
        "settings": {"index": {"max_ngram_diff": 18}, "analysis": RESOURCE_MAPPINGS["settings"]["analysis"]},
        "mappings": RESOURCE_MAPPINGS["mappings"]})

    data = await get_all_catalogue_resources_with_usersgroups(db)
    actions = [{'_index': RESOURCES_INDEX, '_id': str(resource.id),
                '_source': prepare_resource_for_indexing(resource).model_dump()} for resource in data]

    await async_bulk(es_client, actions)


async def add_resource_to_index(db: DBSession, resource: CatalogueResource):
    from wirecloud.commons.search import es_client
    res = await get_catalogue_resource_with_usersgroups_by_id(db, resource.id)

    await es_client.index(index=RESOURCES_INDEX, id=str(res.id), document=prepare_resource_for_indexing(res).model_dump())


async def delete_resource_from_index(resource: CatalogueResource):
    from wirecloud.commons.search import es_client

    await es_client.delete(index=RESOURCES_INDEX, id=str(resource.id))

