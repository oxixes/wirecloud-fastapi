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

from types import SimpleNamespace

from wirecloud.keycloak import proxy


async def test_keycloak_token_processor_delegates_to_idm_processor(monkeypatch, db_session):
    called = {}

    class _FakeIDMTokenProcessor:
        async def process_request(self, db, request, use_real_user):
            called["db"] = db
            called["request"] = request
            called["use_real_user"] = use_real_user

    monkeypatch.setattr(proxy, "IDMTokenProcessor", _FakeIDMTokenProcessor)

    processor = proxy.KeycloakTokenProcessor()
    req = SimpleNamespace()
    await processor.process_request(db_session, req)

    assert called["db"] == db_session
    assert called["request"] == req
    assert called["use_real_user"] is False
