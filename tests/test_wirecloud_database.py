# -*- coding: utf-8 -*-

from types import SimpleNamespace

import pytest
from bson import ObjectId
from pymongo.errors import OperationFailure

from wirecloud import database


def test_collection_and_database_wrappers():
    called = {"kwargs": None}

    class _Collection:
        constant = 7

        def op(self, **kwargs):
            called["kwargs"] = kwargs
            return "ok"

    wrapped = database.CollectionWrapper(_Collection(), session="session")
    assert wrapped.op() == "ok"
    assert called["kwargs"]["session"] == "session"
    assert wrapped.op(session="other") == "ok"
    assert wrapped.constant == 7
    assert wrapped._collection is not None

    class _DB:
        col = _Collection()

        def __getitem__(self, _name):
            return _Collection()

    db = database.DatabaseWrapper(_DB(), "session")
    col_attr = db.col
    assert isinstance(col_attr, database.CollectionWrapper)
    col_item = db["x"]
    assert isinstance(col_item, database.CollectionWrapper)


def test_pymongo_session_and_pyobjectid(monkeypatch):
    fake_session = SimpleNamespace(
        client={database.DATABASE["NAME"]: SimpleNamespace()},
        in_transaction=False,
    )
    pym = database.PyMongoSession(fake_session, use_transactions=True)
    assert isinstance(pym.client, database.DatabaseWrapper)
    assert pym.in_transaction is False

    no_tx = database.PyMongoSession(fake_session, use_transactions=False)
    assert no_tx.in_transaction is False
    assert no_tx.client is fake_session.client[database.DATABASE["NAME"]]
    assert no_tx.in_transaction is False
    assert no_tx.__getattr__("in_transaction") is False

    assert database.PyObjectId.validate(str(ObjectId()))
    with pytest.raises(ValueError, match="Invalid ObjectId"):
        database.PyObjectId.validate("invalid")
    assert database.Id is database.PyObjectId

    schema = database.PyObjectId.__get_pydantic_core_schema__(None, None)
    assert schema["type"] == "json-or-python"


def test_get_db_url_branches(monkeypatch):
    monkeypatch.setitem(database.DATABASE, "USER", "u")
    monkeypatch.setitem(database.DATABASE, "PASSWORD", "p")
    monkeypatch.setitem(database.DATABASE, "HOST", "localhost")
    monkeypatch.setitem(database.DATABASE, "PORT", "27017")
    assert database.get_db_url().startswith("mongodb://u:p@localhost:27017")

    monkeypatch.setitem(database.DATABASE, "PASSWORD", "")
    assert database.get_db_url().startswith("mongodb://u@localhost:27017")

    monkeypatch.setitem(database.DATABASE, "USER", "")
    assert database.get_db_url().startswith("mongodb://localhost:27017")

    monkeypatch.setitem(database.DATABASE, "PORT", "")
    assert database.get_db_url() == "mongodb://localhost"


async def test_transactions_support_and_session_management(monkeypatch):
    called = {"start": 0, "abort": 0, "commit": 0}
    monkeypatch.setattr(database, "USE_TRANSACTIONS", True)

    class _Session:
        def __init__(self, fail_code=None):
            self.in_transaction = False
            self.client = {database.DATABASE["NAME"]: SimpleNamespace(command=self._command)}
            self.fail_code = fail_code

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def start_transaction(self):
            called["start"] += 1
            if self.fail_code is not None:
                raise OperationFailure("failed", code=self.fail_code)
            self.in_transaction = True

        async def abort_transaction(self):
            called["abort"] += 1
            self.in_transaction = False

        async def commit_transaction(self):
            called["commit"] += 1
            self.in_transaction = False

        async def _command(self, *_args, **_kwargs):
            return None

    class _Client:
        def __init__(self, session):
            self._session = session

        def start_session(self):
            return self._session

        async def close(self):
            called["closed"] = True

    database._transactions_supported = None
    ok_session = _Session()
    monkeypatch.setattr(database, "client", _Client(ok_session))
    assert await database.check_transactions_supported() is True
    assert called["abort"] == 1
    assert await database.check_transactions_supported() is True

    database._transactions_supported = None
    fail_session = _Session(fail_code=20)
    monkeypatch.setattr(database, "client", _Client(fail_session))
    assert await database.check_transactions_supported() is False

    database._transactions_supported = None
    other_fail = _Session(fail_code=99)
    monkeypatch.setattr(database, "client", _Client(other_fail))
    with pytest.raises(OperationFailure):
        await database.check_transactions_supported()

    committed = {"start_tx": 0, "commit": 0, "abort": 0}

    class _PySession(database.PyMongoSession):
        async def start_transaction(self):
            committed["start_tx"] += 1
            self._session.in_transaction = True

    class _Session2(_Session):
        async def commit_transaction(self):
            committed["commit"] += 1
            self.in_transaction = False

        async def abort_transaction(self):
            committed["abort"] += 1
            self.in_transaction = False

    session2 = _Session2()

    class _Client2(_Client):
        pass

    monkeypatch.setattr(database, "client", _Client2(session2))
    monkeypatch.setattr(database, "check_transactions_supported", lambda: _true())
    monkeypatch.setattr(database, "PyMongoSession", _PySession)

    async def _true():
        return True

    gen = database.get_session()
    sess = await gen.__anext__()
    with pytest.raises(StopAsyncIteration):
        await gen.__anext__()
    assert committed["start_tx"] >= 1
    assert committed["commit"] == 1

    async def _false():
        return False

    monkeypatch.setattr(database, "check_transactions_supported", _false)
    gen2 = database.get_session()
    sess2 = await gen2.__anext__()
    with pytest.raises(StopAsyncIteration):
        await gen2.__anext__()
    assert sess2 is not None

    gen2_err = database.get_session()
    _ = await gen2_err.__anext__()
    with pytest.raises(RuntimeError, match="forced"):
        await gen2_err.athrow(RuntimeError("forced"))

    class _ErrorPySession(database.PyMongoSession):
        async def start_transaction(self):
            self._session.in_transaction = True

    class _SessionErr(_Session):
        async def commit_transaction(self):
            raise RuntimeError("boom")

    err_session = _SessionErr()
    monkeypatch.setattr(database, "client", _Client2(err_session))
    monkeypatch.setattr(database, "check_transactions_supported", _true)
    monkeypatch.setattr(database, "PyMongoSession", _ErrorPySession)
    aborts_before = called["abort"]
    gen3 = database.get_session()
    _ = await gen3.__anext__()
    with pytest.raises(RuntimeError):
        await gen3.__anext__()
    assert called["abort"] > aborts_before

    await database.close()


async def test_commit_and_start_transaction_error_paths(monkeypatch):
    called = {"start": 0}
    fake_session = SimpleNamespace(
        in_transaction=True,
        start_transaction=lambda: _start(),
        commit_transaction=lambda: _commit(),
    )

    async def _start():
        called["start"] += 1

    async def _commit():
        called["commit"] = called.get("commit", 0) + 1

    wrapper = database.PyMongoSession(fake_session, use_transactions=True)
    await database.commit(wrapper)
    assert called["commit"] == 1
    assert called["start"] == 0

    wrapper_no_tx = database.PyMongoSession(SimpleNamespace(in_transaction=False), use_transactions=False)
    await wrapper_no_tx.start_transaction()
    await database.commit(wrapper_no_tx)

    failing = database.PyMongoSession(
        SimpleNamespace(
            in_transaction=False,
            start_transaction=lambda: _raise20(),
        ),
        use_transactions=True,
    )

    async def _raise20():
        raise OperationFailure("no tx", code=20)

    await failing.start_transaction()
    assert failing._transactions_supported is False

    failing_other = database.PyMongoSession(
        SimpleNamespace(
            in_transaction=False,
            start_transaction=lambda: _raise_other(),
        ),
        use_transactions=True,
    )

    async def _raise_other():
        raise OperationFailure("boom", code=99)

    with pytest.raises(OperationFailure):
        await failing_other.start_transaction()


async def test_collection_wrapper_retry_awaitable_and_helpers(monkeypatch):
    def _opfail(msg, code, labels=None):
        return OperationFailure(msg, code=code, details={"errorLabels": labels or []})

    class _Session:
        def __init__(self):
            self.in_transaction = True
            self.aborts = 0
            self.starts = 0

        async def abort_transaction(self):
            self.aborts += 1
            self.in_transaction = False

        async def start_transaction(self):
            self.starts += 1
            self.in_transaction = True

    class _Collection:
        def __init__(self):
            self.calls = 0
            self.mode = "ok"

        async def op(self, **_kwargs):
            self.calls += 1
            if self.mode == "ok":
                return "ok"
            if self.mode == "transient-once" and self.calls == 1:
                raise _opfail("retry", 112, ["TransientTransactionError"])
            if self.mode == "transient-always":
                raise _opfail("retry", 112, ["TransientTransactionError"])
            if self.mode == "non-transient":
                raise _opfail("no-retry", 99, [])
            return "ok"

    async def _no_sleep(_seconds):
        return None

    monkeypatch.setattr(database.asyncio, "sleep", _no_sleep)

    # Retry succeeds on second attempt
    session = _Session()
    collection = _Collection()
    collection.mode = "transient-once"
    wrapped = database.CollectionWrapper(collection, session)
    assert await wrapped.op() == "ok"
    assert collection.calls == 2
    assert session.aborts == 1
    assert session.starts == 1

    # Retry exhausts max attempts
    session2 = _Session()
    collection2 = _Collection()
    collection2.mode = "transient-always"
    wrapped2 = database.CollectionWrapper(collection2, session2)
    with pytest.raises(OperationFailure):
        await wrapped2.op()
    assert collection2.calls == 5

    # Non-transient error does not retry
    session3 = _Session()
    collection3 = _Collection()
    collection3.mode = "non-transient"
    wrapped3 = database.CollectionWrapper(collection3, session3)
    with pytest.raises(OperationFailure):
        await wrapped3.op()
    assert collection3.calls == 1

    # Helper branches
    assert database._is_transient_transaction_error(_opfail("x", 251, [])) is True
    assert database._is_transient_transaction_error(_opfail("x", 99, ["TransientTransactionError"])) is True
    assert database._is_transient_transaction_error(_opfail("x", 99, [])) is False


async def test_restart_transaction_branches():
    class _Session:
        def __init__(self, in_tx=True, abort_error=None):
            self.in_transaction = in_tx
            self.abort_error = abort_error
            self.aborted = 0
            self.started = 0

        async def abort_transaction(self):
            self.aborted += 1
            if self.abort_error is not None:
                raise self.abort_error
            self.in_transaction = False

        async def start_transaction(self):
            self.started += 1
            self.in_transaction = True

    # in_transaction=False: only start_transaction
    s1 = _Session(in_tx=False)
    await database._restart_transaction(s1)
    assert s1.aborted == 0
    assert s1.started == 1

    # in_transaction=True with transient abort error: swallowed
    transient = OperationFailure("x", code=112, details={"errorLabels": ["TransientTransactionError"]})
    s2 = _Session(in_tx=True, abort_error=transient)
    await database._restart_transaction(s2)
    assert s2.aborted == 1
    assert s2.started == 1

    # in_transaction=True with non-transient abort error: raised
    non_transient = OperationFailure("x", code=99, details={"errorLabels": []})
    s3 = _Session(in_tx=True, abort_error=non_transient)
    with pytest.raises(OperationFailure):
        await database._restart_transaction(s3)


async def test_get_session_abort_non_transient_error(monkeypatch):
    async def _true():
        return True

    class _Session:
        def __init__(self):
            self.in_transaction = False

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def commit_transaction(self):
            raise RuntimeError("commit-failed")

        async def abort_transaction(self):
            raise OperationFailure("abort-failed", code=99, details={"errorLabels": []})

    class _Client:
        def __init__(self, session):
            self._session = session

        def start_session(self):
            return self._session

    class _PySession(database.PyMongoSession):
        async def start_transaction(self):
            self._session.in_transaction = True

    monkeypatch.setattr(database, "USE_TRANSACTIONS", True)
    database._transactions_supported = True
    monkeypatch.setattr(database, "check_transactions_supported", _true)
    monkeypatch.setattr(database, "client", _Client(_Session()))
    monkeypatch.setattr(database, "PyMongoSession", _PySession)

    gen = database.get_session()
    _ = await gen.__anext__()
    with pytest.raises(OperationFailure):
        await gen.__anext__()


async def test_get_session_abort_transient_error_is_swallowed(monkeypatch):
    async def _true():
        return True

    class _Session:
        def __init__(self):
            self.in_transaction = False

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def commit_transaction(self):
            raise RuntimeError("commit-failed")

        async def abort_transaction(self):
            raise OperationFailure("abort-failed", code=112, details={"errorLabels": ["TransientTransactionError"]})

    class _Client:
        def __init__(self, session):
            self._session = session

        def start_session(self):
            return self._session

    class _PySession(database.PyMongoSession):
        async def start_transaction(self):
            self._session.in_transaction = True

    monkeypatch.setattr(database, "USE_TRANSACTIONS", True)
    database._transactions_supported = True
    monkeypatch.setattr(database, "check_transactions_supported", _true)
    monkeypatch.setattr(database, "client", _Client(_Session()))
    monkeypatch.setattr(database, "PyMongoSession", _PySession)

    gen = database.get_session()
    _ = await gen.__anext__()
    with pytest.raises(RuntimeError, match="commit-failed"):
        await gen.__anext__()
