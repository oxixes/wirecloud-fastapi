# -*- coding: utf-8 -*-

from datetime import datetime, timezone

import pytest
from bson import ObjectId

from wirecloud.platform.markets import docs, models, schemas


def test_docs_constants_are_present():
    assert isinstance(docs.market_options_name_description, str)
    assert isinstance(docs.publish_service_process_summary, str)
    assert isinstance(docs.create_market_collection_market_example, dict)


def test_market_models_and_schema_aliases():
    user_id = ObjectId()
    market_id = ObjectId()
    market = models.DBMarket.model_validate(
        {
            "_id": market_id,
            "name": "local",
            "public": True,
            "user_id": user_id,
            "options": {
                "name": "local",
                "type": "wirecloud",
                "title": "Local",
                "url": "https://example.org",
                "public": True,
                "user": "alice",
            },
        }
    )
    assert str(market.id) == str(market_id)
    assert str(market.user_id) == str(user_id)
    assert market.options.type == "wirecloud"
    assert schemas.Market is models.DBMarket


def test_market_create_validators(monkeypatch):
    monkeypatch.setattr("wirecloud.platform.markets.utils.get_market_classes", lambda: {"wirecloud": object})
    valid = schemas.MarketCreate(
        name="local",
        type="wirecloud",
        title="Local",
        url="https://example.org",
        public=True,
        user="alice",
    )
    assert valid.name == "local"
    assert valid.type == "wirecloud"

    with pytest.raises(ValueError, match="Invalid market type"):
        schemas.MarketCreate(
            name="local",
            type="missing",
            title="Local",
            url="https://example.org",
            public=True,
            user="alice",
        )

    with pytest.raises(ValueError):
        schemas.MarketCreate(
            name="local",
            type="wirecloud",
            title="Local",
            url="not-a-url",
            public=True,
            user="alice",
        )

    endpoint = schemas.MarketEndpoint(market="alice/local", store="s1")
    publish = schemas.PublishData(marketplaces=[endpoint], resource="wirecloud/example/1.0.0")
    permissions = schemas.MarketPermissions(delete=True)
    data = schemas.MarketData(
        name="local",
        type="wirecloud",
        title="Local",
        url="https://example.org",
        public=True,
        user="alice",
        permissions=permissions,
    )
    assert publish.marketplaces[0].market == "alice/local"
    assert data.permissions.delete is True
