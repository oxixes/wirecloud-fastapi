# -*- coding: utf-8 -*-

import pytest

from wirecloud.commons.utils import mimeparser


def test_parse_mime_type_and_media_range():
    full, params = mimeparser.parse_mime_type("application/json; charset=utf-8")
    assert full == "application/json"
    assert params["charset"] == "utf-8"

    typ, subtyp, params2 = mimeparser.parse_mime_type("text/plain; q=0.5", split_type=True)
    assert (typ, subtyp) == ("text", "plain")
    assert params2["q"] == "0.5"

    any_full, _ = mimeparser.parse_mime_type("*")
    assert any_full == "*/*"

    with pytest.raises(mimeparser.InvalidMimeType):
        mimeparser.parse_mime_type("invalid")

    t, s, p = mimeparser.parse_media_range("text/plain")
    assert (t, s, p["q"]) == ("text", "plain", "1")
    assert mimeparser.parse_media_range("text/plain;q=2")[2]["q"] == "1"
    assert mimeparser.parse_media_range("text/plain;q=0")[2]["q"] == "1"
    assert mimeparser.parse_media_range("text/plain;q=-1")[2]["q"] == "1"


def test_fitness_and_best_match():
    parsed = [mimeparser.parse_media_range("text/*;q=0.5"), mimeparser.parse_media_range("application/json;q=1")]
    fitness, quality = mimeparser.fitness_and_quality_parsed("application/json", parsed)
    assert fitness > 0
    assert quality == 1.0

    no_match = mimeparser.fitness_and_quality_parsed("image/png", parsed)
    assert no_match == (-1, 0.0)

    match = mimeparser.best_match(
        ["application/xbel+xml", "text/xml"],
        "text/*;q=0.5,*/*;q=0.1",
    )
    assert match == "text/xml"

    tie = mimeparser.best_match(["text/xml", "application/json"], "text/xml;q=0.8,application/json;q=0.8")
    assert tie == "text/xml" or tie == "application/json"

    invalid_header = mimeparser.best_match(["text/plain"], "bad-range,text/plain;q=0.9")
    assert invalid_header == "text/plain"

    none_match = mimeparser.best_match(["application/json"], "image/*;q=1")
    assert none_match == ""

