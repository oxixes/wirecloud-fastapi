# -*- coding: utf-8 -*-

# Copyright (c) 2012-2017 CoNWeT Lab., Universidad Politécnica de Madrid

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

from typing import Optional, Callable, Union
from fastapi import Request

from elasticsearch import AsyncElasticsearch
from elasticsearch.helpers import async_bulk
from pydantic import BaseModel

from src import settings
from src.wirecloud.catalogue.search import ResourceOutResponse, ResourceOut, RESOURCES_INDEX
from src.wirecloud.commons.auth.crud import get_all_users, get_all_groups
from src.wirecloud.commons.auth.models import Group
from src.wirecloud.commons.auth.schemas import User
from src.wirecloud.database import DBSession
from src.wirecloud.platform.search import SearchWorkspaceOutputResponse, SearchWorkspaceOutput

es_client = AsyncElasticsearch(hosts=f"{'https' if settings.ELASTICSEARCH['SECURE'] else 'http'}://{settings.ELASTICSEARCH['HOST']}:{settings.ELASTICSEARCH['PORT']}",
                               http_auth=(settings.ELASTICSEARCH['USER'], settings.ELASTICSEARCH['PASSWORD']))

# TODO: organizations

USERS_INDEX = 'users'
GROUPS_INDEX = 'groups'

USER_CONTENT_FIELDS = ['fullname', 'username']
GROUP_CONTENT_FIELDS = ['name']

USER_MAPPINGS = {
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
        "properties": {
            "fullname": {
                "type": "text",
                "analyzer": "ngram_analyzer",
                "search_analyzer": "standard",
                "fields": {
                    "keyword": {"type": "keyword"}
                }
            },
            "username": {
                "type": "text",
                "analyzer": "ngram_analyzer",
                "search_analyzer": "standard",
                "fields": {
                    "keyword": {"type": "keyword"}
                }
            }
        }
    }
}
GROUP_MAPPINGS = {
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
        "properties": {
            "name": {
                "type": "text",
                "analyzer": "ngram_analyzer",
                "search_analyzer": "standard",
                "fields": {
                    "keyword": {"type": "keyword"}
                }
            }
        }
    }
}

_available_search_engines = None
_available_rebuild_engines = None


class SearchUserOutput(BaseModel):
    fullname: str
    username: str
    # TODO: Organizations


class SearchGroupOutput(BaseModel):
    name: str
    # TODO: Organizations


class SearchResponse(BaseModel):
    offset: int
    pagecount: int
    pagelen: int
    pagenum: int
    results: list[Union[SearchUserOutput, SearchGroupOutput, SearchWorkspaceOutputResponse, ResourceOutResponse]]
    total: int


def get_available_search_engines() -> dict[str, Callable[[str, int, int, Optional[str]], SearchResponse]]:
    global _available_search_engines

    if _available_search_engines is None:
        from src.wirecloud.platform.search import search_workspaces
        from src.wirecloud.catalogue.search import search_resources
        _available_search_engines = {"group": search_groups,
                                     "user": search_users,
                                     "workspace": search_workspaces,
                                     "usergroup": search_user_groups,
                                     "resource": search_resources}

    return _available_search_engines


def get_available_rebuild_engines() -> dict[str, Callable[[DBSession], None]]:
    global _available_rebuild_engines

    if _available_rebuild_engines is None:
        from src.wirecloud.platform.search import rebuild_workspace_index
        from src.wirecloud.catalogue.search import rebuild_resource_index
        _available_rebuild_engines = {"group": rebuild_group_index,
                                      "user": rebuild_user_index,
                                      "workspace": rebuild_workspace_index,
                                      "resource": rebuild_resource_index,
                                      "all": rebuild_all_indexes}

    return _available_rebuild_engines


def is_available_search_engine(indexname: str) -> bool:
    return indexname in get_available_search_engines()


def is_available_rebuild_engine(indexname: str) -> bool:
    return indexname in get_available_rebuild_engines()


def get_search_engine(indexname: str) -> Optional[Callable[[str, int, int, Optional[str]], SearchResponse]]:
    return get_available_search_engines().get(indexname)


def get_rebuild_engine(indexname: str) -> Optional[Callable[[DBSession], None]]:
    return get_available_rebuild_engines().get(indexname)


async def calculate_pagination(index: str, body: dict, pagenum: int, max_results: int) -> tuple[int, int, int, int]:
    resp = await es_client.count(index=index, body={"query": body.get("query", {"match_all": {}})})
    total = resp['count']

    pagecount = total // max_results
    if total % max_results != 0:
        pagecount += 1

    if pagenum > pagecount:
        pagenum = max(1, pagecount)
    else:
        pagenum = pagenum

    offset = (pagenum - 1) * max_results
    return offset, pagecount, pagenum, total


async def build_search_response(index: Union[str, list[str]], body: dict, pagenum: int,
                                max_results: int,
                                clean: Union[Callable[[dict], Union[SearchUserOutput, SearchGroupOutput, SearchWorkspaceOutputResponse, ResourceOutResponse]], Callable[[dict, Request], Union[SearchUserOutput, SearchGroupOutput, SearchWorkspaceOutputResponse, ResourceOutResponse]]],
                                request: Optional[Request] = None) -> SearchResponse:
    offset, pagecount, pagenum, total = await calculate_pagination(index=index, body=body, pagenum=pagenum, max_results=max_results)

    resp = await es_client.search(index=index, body=body, from_=offset, size=max_results)
    hits = resp.get("hits", {}).get("hits", [])
    if index == RESOURCES_INDEX:
        results = [clean(hit, request) for hit in hits]
    else:
        results = [clean(hit) for hit in hits]

    total = resp.get("hits", {}).get("total", {}).get("value", len(results))

    return SearchResponse(
        offset=offset,
        pagecount=pagecount,
        pagelen=len(results),
        pagenum=pagenum,
        results=results,
        total=total
    )


def clean_user_out(hit: dict) -> SearchUserOutput:
    source = hit["_source"]
    return SearchUserOutput(
        fullname=source["fullname"],
        username=source["username"]
    )


async def search_users(querytext: str, pagenum: int, max_results: int, order_by: Optional[tuple[str]] = None) -> Optional[SearchResponse]:
    body = {}
    if querytext:
        body = {"query": {"multi_match": {"query": querytext, "fields": USER_CONTENT_FIELDS}}}

    if order_by:
        sort_list = []
        for f in order_by:
            field_name = f.lstrip("-")
            if field_name not in SearchUserOutput.model_fields:
                return None

            order = "desc" if f.startswith("-") else "asc"
            sort_list.append({field_name + ".keyword": {"order": order}})

        body["sort"] = sort_list

    return await build_search_response(index=USERS_INDEX, body=body, pagenum=pagenum, max_results=max_results, clean=clean_user_out)


async def add_user_to_index(user: User):
    await es_client.index(index=USERS_INDEX, id=str(user.id), document=SearchUserOutput(
        fullname=f"{user.first_name} {user.last_name}".strip(),
        username=user.username
    ).model_dump())


async def add_group_to_index(group: Group):
    await es_client.index(index=GROUPS_INDEX, id=str(group.id), document=SearchGroupOutput(
        name=group.name
    ).model_dump())


def clean_group_out(hit: dict) -> SearchGroupOutput:
    source = hit["_source"]
    return SearchGroupOutput(
        name=source["name"]
    )


async def search_groups(querytext: str, pagenum: int, max_results: int, order_by: Optional[str] = None) -> Optional[SearchResponse]:
    body = {}
    if querytext:
        body = {"query": {"multi_match": {"query": querytext, "fields": GROUP_CONTENT_FIELDS}}}

    if order_by:
        sort_list = []
        for f in order_by:
            field_name = f.lstrip("-")
            if field_name not in SearchGroupOutput.model_fields:
                return None

            order = "desc" if f.startswith("-") else "asc"
            sort_list.append({field_name + ".keyword": {"order": order}})

        body["sort"] = sort_list

    return await build_search_response(index=GROUPS_INDEX, body=body, pagenum=pagenum, max_results=max_results, clean=clean_group_out)


async def search_user_groups(querytext: str, pagenum: int, max_results: int, order_by: Optional[str] = None) -> Optional[SearchResponse]:
    body = {}
    if querytext:
        body = {"query": {"multi_match": {"query": querytext, "fields": USER_CONTENT_FIELDS}}}

    if order_by:
        sort_list = []
        for f in order_by:
            field_name = f.lstrip("-")
            if field_name not in SearchUserOutput.model_fields and field_name not in SearchGroupOutput.model_fields:
                return None

            order = "desc" if f.startswith("-") else "asc"
            sort_list.append({field_name + ".keyword": {"order": order}})

        body["sort"] = sort_list

    return await build_search_response(index=[USERS_INDEX, GROUPS_INDEX], body=body,
                                       pagenum=pagenum, max_results=max_results,
                                       clean=lambda hit: clean_group_out(hit) if hit["_index"] == GROUPS_INDEX else clean_user_out(hit))


async def rebuild_user_index(db: DBSession) -> None:
    if await es_client.indices.exists(index=USERS_INDEX):
        await es_client.indices.delete(index=USERS_INDEX)

    await es_client.indices.create(index=USERS_INDEX, body={
        "settings": {"index": {"max_ngram_diff": 18}, "analysis": USER_MAPPINGS["settings"]["analysis"]},
        "mappings": USER_MAPPINGS["mappings"]})
    data = await get_all_users(db)
    actions = [{'_index': USERS_INDEX, '_id': str(user.id), '_source': SearchUserOutput(
        fullname=f"{user.first_name} {user.last_name}".strip(),
        username=user.username
    ).model_dump()} for user in data]
    await async_bulk(es_client, actions)


async def rebuild_group_index(db: DBSession):
    if await es_client.indices.exists(index=GROUPS_INDEX):
        await es_client.indices.delete(index=GROUPS_INDEX)

    await es_client.indices.create(index=GROUPS_INDEX, body={
        "settings": {"index": {"max_ngram_diff": 18}, "analysis": GROUP_MAPPINGS["settings"]["analysis"]},
        "mappings": GROUP_MAPPINGS["mappings"]})
    data = await get_all_groups(db)
    actions = [{'_index': GROUPS_INDEX, '_id': str(group.id), '_source': SearchGroupOutput(
        name=group.name
    ).model_dump()} for group in data]
    await async_bulk(es_client, actions)


async def rebuild_all_indexes(db: DBSession):
    from src.wirecloud.platform.search import rebuild_workspace_index
    from src.wirecloud.catalogue.search import rebuild_resource_index

    await rebuild_user_index(db)
    await rebuild_group_index(db)
    await rebuild_workspace_index(db)
    await rebuild_resource_index(db)