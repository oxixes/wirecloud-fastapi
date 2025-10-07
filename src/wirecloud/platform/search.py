#  -*- coding: utf-8 -*-

#  -*- coding: utf-8 -*-
#
#  Copyright (c) 2024 Future Internet Consulting and Development Solutions S.L.
#
#  This file is part of Wirecloud.
#
#  Wirecloud is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Affero General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  Wirecloud is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Affero General Public License for more details.
#
#  You should have received a copy of the GNU Affero General Public License
#  along with Wirecloud.  If not, see <http://www.gnu.org/licenses/>.

#
#  Copyright (c) 2024 Future Internet Consulting and Development Solutions S.L.
#
#  This file is part of Wirecloud.
#
#  Wirecloud is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Affero General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  Wirecloud is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Affero General Public License for more details.
#
#  You should have received a copy of the GNU Affero General Public License
#  along with Wirecloud.  If not, see <http://www.gnu.org/licenses/>.
from typing import Optional
from datetime import datetime

from elasticsearch._async.helpers import async_bulk
from pydantic import BaseModel

from src.wirecloud.commons.auth.crud import get_username_by_id
from src.wirecloud.commons.auth.schemas import UserAll, User
from src.wirecloud.database import DBSession
from src.wirecloud.platform.workspace.models import Workspace

WORKSPACES_INDEX = 'workspaces'
# TODO check this
WORKSPACE_CONTENT_FIELDS = ["owner", "name^1.3"]  # "title^1.3"
WORKSPACE_MAPPINGS = {
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
            },
            "title": {
                "type": "text",
                "analyzer": "ngram_analyzer",
                "search_analyzer": "standard",
                "fields": {
                    "keyword": {"type": "keyword"}
                }
            },
            "description": {"type": "text"},
            "longdescription": {"type": "text"},
            "public": {"type": "boolean"},
            "requireauth": {"type": "boolean"},
            "searchable": {"type": "boolean"},
            "last_modified": {"type": "date", "format": "strict_date_optional_time||epoch_millis"},
            "owner": {"type": "keyword"},
            "users": {"type": "keyword"},
            "groups": {"type": "keyword"},
            "shared": {"type": "boolean"}
        }
    }
}


class WorkspaceOutResponse(BaseModel):
    name: str
    title: str
    description: str
    longdescription: str
    public: bool
    requireauth: bool
    last_modified: datetime
    owner: str
    shared: bool


class WorkspaceOut(WorkspaceOutResponse):
    searchable: Optional[bool]
    users: list[str]
    groups: list[str]


def clean_workspace_out(hit: dict) -> WorkspaceOutResponse:
    source = hit["_source"]
    return WorkspaceOutResponse(
        name=source["name"],
        title=source["title"],
        description=source["description"],
        longdescription=source["longdescription"],
        public=source["public"],
        requireauth=source["requireauth"],
        last_modified=source["last_modified"],
        owner=source["owner"],
        shared=source["shared"]
    )


async def search_workspaces(user: UserAll, querytext: str, pagenum: int, max_results: int, order_by: Optional[tuple[str]] = None):
    must_clauses = []
    filter_clauses = [{"term": {"searchable": True}}]

    if querytext:
        must_clauses.append({"multi_match": {"query": querytext, "fields": WORKSPACE_CONTENT_FIELDS}})

    should_clauses = [{"term": {"public": True}}]

    if user:
        should_clauses.append({"term": {"users": str(user.id)}})
        if user.groups:
            for group in user.groups:
                should_clauses.append({"term": {"groups": str(group)}})

    body = {
        "query": {
            "bool": {
                "must": must_clauses,
                "filter": filter_clauses,
                "should": should_clauses,
                "minimum_should_match": 1
            }
        }
    }

    if order_by:
        body["sort"] = [{f.lstrip("-") + ".keyword": {"order": "desc" if f.startswith("-") else "asc"} for f in order_by}]

    from src.wirecloud.commons.search import build_search_response
    return await build_search_response(index=WORKSPACES_INDEX, body=body, pagenum=pagenum, max_results=max_results, clean=clean_workspace_out)


def prepare_workspace_for_indexing(workspace: Workspace, owner_username: str) -> WorkspaceOut:
    return WorkspaceOut(
        name=workspace.name,
        title=workspace.title,
        description=workspace.description,
        longdescription=workspace.longdescription,
        public=workspace.public,
        requireauth=workspace.requireauth,
        searchable=workspace.searchable,
        last_modified=workspace.last_modified if workspace.last_modified else workspace.creation_date,
        owner=owner_username,
        users=[str(user.id) for user in workspace.users],
        groups=[str(group.id) for group in workspace.groups],
        shared=workspace.is_shared()
    )


async def rebuild_workspace_index(db: DBSession):
    from src.wirecloud.commons.search import es_client

    if await es_client.indices.exists(index=WORKSPACES_INDEX):
        await es_client.indices.delete(index=WORKSPACES_INDEX)

    await es_client.indices.create(index=WORKSPACES_INDEX, body={
        "settings": {"index": {"max_ngram_diff": 18}, "analysis": WORKSPACE_MAPPINGS["settings"]["analysis"]},
        "mappings": WORKSPACE_MAPPINGS["mappings"]})

    from src.wirecloud.platform.workspace.crud import get_all_workspaces
    data = await get_all_workspaces(db)
    actions = [{'_index': WORKSPACES_INDEX, '_id': str(workspace.id),
                '_source': prepare_workspace_for_indexing(workspace, await get_username_by_id(db, workspace.creator)).model_dump()} for workspace in data]
    await async_bulk(es_client, actions)


async def add_workspace_to_index(user: User, workspace: Workspace):
    from src.wirecloud.commons.search import es_client

    await es_client.index(index=WORKSPACES_INDEX, id=str(workspace.id),
                          document=prepare_workspace_for_indexing(workspace, user.username).model_dump())


async def delete_workspace_from_index(workspace: Workspace):
    from src.wirecloud.commons.search import es_client

    await es_client.delete(index=WORKSPACES_INDEX, id=str(workspace.id))


async def update_workspace_in_index(db: DBSession, workspace: Workspace):
    from src.wirecloud.commons.search import es_client

    if await es_client.exists(index=WORKSPACES_INDEX, id=str(workspace.id)):
        username = await get_username_by_id(db, workspace.creator)
        await es_client.update(index=WORKSPACES_INDEX, id=str(workspace.id),
                               doc=prepare_workspace_for_indexing(workspace, username).model_dump())