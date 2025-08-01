import time
import tempfile

import pytest


from spantom import SP


class TraceliteTestException(Exception):
    pass


def test_SP():
    nsamples = 1000
    with tempfile.NamedTemporaryFile(mode="w+b", delete=False, suffix=".db") as temp_db:
        SP.init(temp_db.name)

        # check columns are correct
        assert SP._tls.curs.execute("PRAGMA table_info(spans)").fetchall() == [
            (0, "id", "INTEGER", 0, None, 1),
            (1, "name", "TEXT", 1, None, 0),
            (2, "start", "TIMESTAMP", 1, None, 0),
            (3, "duration", "FLOAT", 1, None, 0),
        ]
        assert SP._tls.curs.execute("PRAGMA table_info(span_tags)").fetchall() == [
            (0, "id", "INTEGER", 0, None, 1),
            (1, "span_id", "INTEGER", 1, None, 0),
            (2, "key", "TEXT", 1, None, 0),
            (3, "value", "TEXT", 1, None, 0),
        ]

        # check tables are initially empty
        assert SP._tls.curs.execute("SELECT count(*) FROM spans").fetchone() == (0,)
        assert SP._tls.curs.execute("SELECT count(*) FROM span_tags").fetchone() == (0,)

        # insert spans and tags
        @SP.span("bar-test-name")
        def bar(x):
            SP.tag({"bar_input": x + "-bar"})
            raise TraceliteTestException()

        @SP.span()
        def foo(x):
            SP.tag({"foo_input": x + "-foo"})
            bar(x)
            return x

        start = time.time()
        for _ in range(nsamples):
            with pytest.raises(TraceliteTestException):
                foo("test")
        end = time.time()
        total_runtime = end - start

        # check data was inserted as expected
        assert SP._tls.curs.execute("SELECT COUNT(*) FROM spans").fetchall() == [
            (2000,)
        ]
        assert SP._tls.curs.execute("SELECT COUNT(*) FROM span_tags").fetchall() == [
            (2000,)
        ]
        assert SP._tls.curs.execute(
            "SELECT id, name FROM spans ORDER BY id LIMIT 2"
        ).fetchall() == [(1, "bar-test-name"), (2, "foo")]
        assert SP._tls.curs.execute(
            "SELECT span_id, key, value FROM span_tags ORDER BY span_id LIMIT 2"
        ).fetchall() == [(1, "bar_input", "test-bar"), (2, "foo_input", "test-foo")]

        # check runtime less than 10 microseconds per call
        # when the test was written it was less than 1 microsecond per call
        assert total_runtime / nsamples / 4 < 1e-5

        # check summary
        summary = SP.summary()
        assert summary["db_path"] == temp_db.name
        assert summary["span_count"] == 2000
        assert summary["tag_count"] == 2000
        assert summary["min_start"] is not None
        assert summary["max_start"] is not None
        assert summary["total_duration"] is not None
        assert summary["span_names"] == [("bar-test-name",), ("foo",)]
        assert summary["tag_keys"] == [("bar_input",), ("foo_input",)]

        # check clear operation works
        SP.clear()
        assert SP._tls.curs.execute("SELECT COUNT(*) FROM spans").fetchall() == [(0,)]
        assert SP._tls.curs.execute("SELECT COUNT(*) FROM span_tags").fetchall() == [
            (0,)
        ]
