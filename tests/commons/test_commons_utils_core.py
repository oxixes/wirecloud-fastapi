# -*- coding: utf-8 -*-

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi import Response
from fastapi.responses import StreamingResponse
from starlette.requests import Request

from wirecloud.commons.utils import cache, db, downloader, encoding, git, structures, translation, urlify, version
from wirecloud.platform.workspace.models import Tab
from wirecloud.platform.workspace.schemas import WorkspaceGlobalData


def _request_with_headers(headers=None):
    raw_headers = []
    for key, value in (headers or {}).items():
        raw_headers.append((key.lower().encode("latin-1"), value.encode("latin-1")))
    return Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": "GET",
            "path": "/",
            "query_string": b"",
            "headers": raw_headers,
        }
    )


def _workspace_global_data():
    return WorkspaceGlobalData(
        id="507f1f77bcf86cd799439011",
        name="main",
        title="Main",
        public=False,
        shared=False,
        requireauth=False,
        owner="alice",
        removable=True,
        lastmodified=datetime.now(timezone.utc),
        description="",
        longdescription="",
    )


def test_patch_cache_headers_and_modified_since(monkeypatch):
    monkeypatch.setattr(cache.time, "time", lambda: 1000)
    response = Response(content="ok", media_type="text/plain")
    patched = cache.patch_cache_headers(response, timestamp=900000, cache_timeout=200, etag=None)
    assert "Last-Modified" in patched.headers
    assert "ETag" in patched.headers
    assert patched.headers["Cache-Control"] == "private, max-age=100"
    assert "Expires" in patched.headers

    custom_etag = cache.patch_cache_headers(Response(content="x"), timestamp=None, cache_timeout=0, etag='"abc"')
    assert custom_etag.headers["ETag"] == '"abc"'
    assert custom_etag.headers["Cache-Control"] == "private, max-age=0"
    response_with_lm = Response(content="ok")
    response_with_lm.headers["Last-Modified"] = "keep"
    kept = cache.patch_cache_headers(response_with_lm, timestamp=None, cache_timeout=None)
    assert kept.headers["Last-Modified"] == "keep"

    stream = StreamingResponse(iter([b"x"]))
    patched_stream = cache.patch_cache_headers(stream, timestamp=None, cache_timeout=None)
    assert "ETag" not in patched_stream.headers

    now = datetime.now(timezone.utc)
    req = _request_with_headers({"if-modified-since": cache.http_date(int((now - timedelta(seconds=10)).timestamp()))})
    assert cache.check_if_modified_since(req, now) is True

    req_newer = _request_with_headers({"if-modified-since": cache.http_date(int((now + timedelta(seconds=10)).timestamp()))})
    assert cache.check_if_modified_since(req_newer, now) is False

    bad_date = _request_with_headers({"if-modified-since": "not-a-date"})
    assert cache.check_if_modified_since(bad_date, now) is True
    assert cache.check_if_modified_since(_request_with_headers(), now) is True
    assert cache.check_if_modified_since(_request_with_headers(), None) is True


def test_cacheable_data_get_response(monkeypatch):
    monkeypatch.setattr(cache.time, "time", lambda: 1234.0)
    html_data = cache.CacheableData(data="<h1>Hello</h1>", timeout=60)
    response_html = html_data.get_response(status_code=201, cacheable=True)
    assert response_html.status_code == 201
    assert response_html.headers["Content-Type"].startswith("text/html")
    assert "ETag" in response_html.headers

    json_data = cache.CacheableData(data=_workspace_global_data(), timeout=0, timestamp=datetime.now(timezone.utc))
    response_json = json_data.get_response(cacheable=True)
    assert response_json.headers["Content-Type"].startswith("application/json")
    assert response_json.headers["Cache-Control"].startswith("private, max-age=")

    no_cache = cache.CacheableData(data="<p>x</p>")
    response_no_cache = no_cache.get_response(cacheable=False)
    assert "ETag" not in response_no_cache.headers


class _DBItem:
    def __init__(self, name):
        self.name = name

    def model_dump(self, **_kwargs):
        return {"name": self.name}


async def test_db_save_alternative_and_tab(db_session, monkeypatch):
    await db_session.client["items"].insert_one({"name": "tab"})
    await db_session.client["items"].insert_one({"name": "tab-2"})

    instance = _DBItem(name="tab")
    await db.save_alternative(db_session, "items", "name", instance)
    assert instance.name == "tab-3"
    inserted = await db_session.client["items"].find_one({"name": "tab-3"})
    assert inserted is not None

    tab = Tab(id="507f1f77bcf86cd799439011-1", name="Main", title="Main")
    workspace = SimpleNamespace(tabs={"1": Tab(id="1", name="Main", title="Main")})

    async def _workspace_by_id(_db, _id):
        return workspace

    monkeypatch.setattr("wirecloud.platform.workspace.crud.get_workspace_by_id", _workspace_by_id)
    monkeypatch.setattr(db, "is_there_a_tab_with_that_name", lambda name, tabs: any(t.name == name for t in tabs.values()))
    updated = await db.save_alternative_tab(db_session, tab)
    assert updated.name == "Main-2"

    async def _none_workspace(_db, _id):
        return None

    monkeypatch.setattr("wirecloud.platform.workspace.crud.get_workspace_by_id", _none_workspace)
    with pytest.raises(ValueError, match="Workspace not found"):
        await db.save_alternative_tab(db_session, tab)


def test_downloader_and_encoding(monkeypatch, tmp_path):
    path = tmp_path / "a.txt"
    path.write_bytes(b"hello")
    assert downloader.download_local_file(str(path)) == b"hello"

    with pytest.raises(Exception):
        downloader.download_http_content("ftp://example.com/file")

    captured = {}

    class _Resp:
        content = b"payload"

        def raise_for_status(self):
            return None

    def _get(url, headers):
        captured["url"] = url
        captured["headers"] = headers
        return _Resp()

    monkeypatch.setattr(downloader.requests, "get", _get)
    assert downloader.download_http_content("https://example.com") == b"payload"
    assert "Wirecloud/" in captured["headers"]["User-Agent"]

    encoder = encoding.LazyEncoderXHTML()
    encoded = encoder.encode({"x": "&<>"})
    assert "\\u0026" in encoded
    assert "\\u003c" in encoded
    assert "\\u003e" in encoded


def test_git_info(monkeypatch):
    commands = []

    class _Proc:
        def __init__(self, cmd, **_kwargs):
            self.cmd = cmd

        def communicate(self):
            commands.append(self.cmd)
            if self.cmd[:3] == ["git", "status", "--porcelain"]:
                return [b""]
            if self.cmd[:3] == ["git", "rev-parse", "HEAD"]:
                return [b"abcdef\n"]
            if self.cmd[:4] == ["git", "tag", "-l", "--points-at"]:
                return [f"{git.wirecloud.__version__}\n".encode("ascii")]
            if self.cmd[:4] == ["git", "log", "-1", "--date=short"]:
                return [b"2026-03-09"]
            return [b""]

    monkeypatch.setattr(git.subprocess, "Popen", _Proc)
    rev, date, dirty = git.get_git_info()
    assert rev == "abcdef"
    assert date == "2026-03-09"
    assert dirty is False
    assert commands

    class _RaiseProc:
        def __init__(self, *_args, **_kwargs):
            raise OSError("no git")

    monkeypatch.setattr(git.subprocess, "Popen", _RaiseProc)
    rev2, date2, dirty2 = git.get_git_info()
    assert rev2 == "Unknown"
    assert date2 == "Unknown"
    assert dirty2 is True

    class _LogErrorProc:
        def __init__(self, cmd, **_kwargs):
            self.cmd = cmd

        def communicate(self):
            if self.cmd[:3] == ["git", "status", "--porcelain"]:
                return [b""]
            if self.cmd[:3] == ["git", "rev-parse", "HEAD"]:
                return [b"abcdef\n"]
            if self.cmd[:4] == ["git", "tag", "-l", "--points-at"]:
                return [f"{git.wirecloud.__version__}\n".encode("ascii")]
            if self.cmd[:4] == ["git", "log", "-1", "--date=short"]:
                raise OSError("log unavailable")
            return [b""]

    monkeypatch.setattr(git.subprocess, "Popen", _LogErrorProc)
    rev3, date3, dirty3 = git.get_git_info()
    assert rev3 == "abcdef"
    assert date3 == "Unknown"
    assert dirty3 is False


def test_structures_translation_urlify_and_version():
    empty = structures.CaseInsensitiveDict()
    assert len(empty) == 0

    cid = structures.CaseInsensitiveDict({"Accept": "json"})
    cid["X-Test"] = "1"
    assert cid["accept"] == "json"
    assert list(cid) == ["Accept", "X-Test"]
    assert len(cid) == 2
    assert dict(cid.lower_items())["accept"] == "json"
    assert cid == {"accept": "json", "x-test": "1"}
    assert structures.CaseInsensitiveDict.__eq__(cid, 123) is NotImplemented
    copied = cid.copy()
    assert copied == cid
    assert "Accept" in repr(cid)
    del cid["x-test"]
    assert len(cid) == 1

    assert translation.get_trans_index("__MSG_HELLO__") == "HELLO"
    assert translation.get_trans_index("nope") is None
    assert translation.get_trans_index(None) is None
    assert translation.replace_trans_index("HELLO", "Say __MSG_HELLO__", "hi") == "Say hi"

    assert urlify.downcode("áÇβ") == "aCb"
    assert urlify.URLify("This is a test!!!") == "test"
    assert urlify.URLify("Hello world - ", num_chars=8) == "hello-wo"

    assert version.cmp(1, 2) == -1
    assert version.Version("1.0.0") > version.Version("1.0.0rc1")
    assert version.Version("1") == version.Version("1.0.0")
    assert version.Version("1.0.0rc1") < version.Version("1.0.0")
    assert version.Version("1.0.0a1") < version.Version("1.0.0b1")
    assert version.Version("1.0.0-dev1") < version.Version("1.0.0")
    assert version.Version("1.0.0", reverse=True) < version.Version("0.9.9", reverse=True)
    assert version.Version("1.0") == "1.0.0"
    assert version.Version("1.0") != version.Version("1.1")
    assert version.Version("1.0") <= version.Version("1.0")
    assert version.Version("1.0") >= version.Version("1.0")
    assert version.Version("1.0").__cmp__("1.0.1") < 0
    with pytest.raises(ValueError, match="invalid version number"):
        version.Version("01.0")
    with pytest.raises(ValueError, match="invalid version number"):
        version.Version("1.0").__cmp__(object())
