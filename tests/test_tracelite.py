import os
import time
import tempfile

import pytest


class SpantomTestException(Exception):
    pass


@pytest.fixture()
def SP():
    with tempfile.NamedTemporaryFile(mode="w+b", delete=False, suffix=".db") as temp_db:
        os.environ["SPANTOM_DB"] = temp_db.name

        # path is set at import time
        from spantom import SP

        return SP


def test_SP(SP):
    nsamples = 1000

    # check columns are correct
    assert SP.curs.execute("PRAGMA table_info(spans)").fetchall() == [
        (0, "id", "INTEGER", 0, None, 1),
        (1, "name", "TEXT", 1, None, 0),
        (2, "start", "TIMESTAMP", 1, None, 0),
        (3, "duration", "FLOAT", 1, None, 0),
    ]
    assert SP.curs.execute("PRAGMA table_info(span_tags)").fetchall() == [
        (0, "id", "INTEGER", 0, None, 1),
        (1, "span_id", "INTEGER", 1, None, 0),
        (2, "key", "TEXT", 1, None, 0),
        (3, "value", "TEXT", 1, None, 0),
    ]

    # check tables are initially empty
    assert SP.curs.execute("SELECT count(*) FROM spans").fetchone() == (0,)
    assert SP.curs.execute("SELECT count(*) FROM span_tags").fetchone() == (0,)

    # insert spans and tags
    @SP.span("bar-test-name")
    def bar(x):
        SP.tag({"bar_input": x + "-bar"})
        raise SpantomTestException()

    @SP.span()
    def foo(x):
        SP.tag({"foo_input": x + "-foo"})
        bar(x)
        return x

    start = time.time()
    for _ in range(nsamples):
        with pytest.raises(SpantomTestException):
            foo("test")
    end = time.time()
    total_runtime = end - start

    # check data was inserted as expected
    assert SP.curs.execute("SELECT COUNT(*) FROM spans").fetchall() == [(2000,)]
    assert SP.curs.execute("SELECT COUNT(*) FROM span_tags").fetchall() == [(2000,)]
    assert SP.curs.execute(
        "SELECT id, name FROM spans ORDER BY id LIMIT 2"
    ).fetchall() == [(1, "bar-test-name"), (2, "foo")]
    assert SP.curs.execute(
        "SELECT span_id, key, value FROM span_tags ORDER BY span_id LIMIT 2"
    ).fetchall() == [(1, "bar_input", "test-bar"), (2, "foo_input", "test-foo")]

    # check runtime less than 10 microseconds per call
    # when the test was written it was less than 1 microsecond per call
    assert total_runtime / nsamples / 4 < 1e-5

    # check summary
    summary = SP.summary()
    assert summary["db_path"] == SP.path
    assert summary["span_count"] == 2000
    assert summary["tag_count"] == 2000
    assert summary["min_start"] is not None
    assert summary["max_start"] is not None
    assert summary["total_duration"] is not None
    assert summary["span_names"] == [("bar-test-name",), ("foo",)]
    assert summary["tag_keys"] == [("bar_input",), ("foo_input",)]

    # check clear operation works
    SP.clear()
    assert SP.curs.execute("SELECT COUNT(*) FROM spans").fetchall() == [(0,)]
    assert SP.curs.execute("SELECT COUNT(*) FROM span_tags").fetchall() == [(0,)]

    # check that context manager works
    with SP.span("context-test"):
        SP.tag({"context_key": "context_value"})

    assert SP.curs.execute("SELECT COUNT(*) FROM spans").fetchall() == [(1,)]
    assert SP.curs.execute("SELECT COUNT(*) FROM span_tags").fetchall() == [(1,)]
    assert SP.curs.execute("SELECT name FROM spans").fetchall() == [("context-test",)]
    assert SP.curs.execute("SELECT key, value FROM span_tags").fetchall() == [
        ("context_key", "context_value"),
    ]
