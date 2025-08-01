import atexit
import time
import sqlite3
from typing import Optional

DEFAULT_DB = "/tmp/spantom.db"


class SpantomSession:
    def __init__(self, path: str):
        self.tags = {}
        self.path = path

        self.conn = sqlite3.connect(self.path)
        self.curs = self.conn.cursor()
        self.curs.execute("PRAGMA foreign_keys = ON")
        self.curs.execute(
            """CREATE TABLE IF NOT EXISTS spans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            start TIMESTAMP NOT NULL,
            duration FLOAT NOT NULL
        )"""
        )
        self.curs.execute(
            """CREATE TABLE IF NOT EXISTS span_tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            span_id INTEGER NOT NULL,
            key TEXT NOT NULL,
            value TEXT NOT NULL,
            FOREIGN KEY (span_id) REFERENCES spans (id)
        )"""
        )

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.conn.commit()
        self.conn.close()

    def tag(self, new_tags: dict):
        self.tags.update(new_tags)

    def write(self, name: str, start_time: float, duration: float):
        self.curs.execute(
            "INSERT INTO spans (name, start, duration) VALUES (?, ?, ?)",
            (name, start_time, duration),
        )

        span_id = self.curs.lastrowid
        if self.tags:
            self.curs.executemany(
                "INSERT INTO span_tags (span_id, key, value) VALUES (?, ?, ?)",
                [(span_id, str(key), str(value)) for key, value in self.tags.items()],
            )
        self.tags.clear()

    def span(self, name: Optional[str] = None):
        def wrapper(func):
            def inner(*args, **kwargs):
                parent_tags, self.tags = self.tags, dict()

                start_time = time.time()

                try:
                    result = func(*args, **kwargs)
                finally:
                    end_time = time.time()
                    duration = end_time - start_time
                    self.write(name or func.__name__, start_time, duration)
                    self.tags = parent_tags

                return result

            return inner

        return wrapper

    def clear(self):
        self.tags.clear()
        self.curs.execute("DELETE FROM span_tags")
        self.curs.execute("DELETE FROM spans")

    def summary(self):
        return {
            "db_path": self.path,
            "span_count": self.curs.execute("SELECT COUNT(*) FROM spans").fetchone()[0],
            "tag_count": self.curs.execute("SELECT COUNT(*) FROM span_tags").fetchone()[
                0
            ],
            "min_start": self.curs.execute("SELECT MIN(start) FROM spans").fetchone()[
                0
            ],
            "max_start": self.curs.execute("SELECT MAX(start) FROM spans").fetchone()[
                0
            ],
            "total_duration": self.curs.execute(
                "SELECT SUM(duration) FROM spans"
            ).fetchone()[0],
            "span_names": self.curs.execute(
                "SELECT DISTINCT name FROM spans"
            ).fetchall(),
            "tag_keys": self.curs.execute(
                "SELECT DISTINCT key FROM span_tags"
            ).fetchall(),
        }


class SP:
    @classmethod
    def tag(cls, new_tags: dict):
        cls._tls.tag(new_tags)

    @classmethod
    def span(cls, name: Optional[str] = None):
        return cls._tls.span(name)

    @classmethod
    def init(cls, path: str = DEFAULT_DB):
        cls._tls = SpantomSession(path)
        atexit.register(cls._tls.__exit__, None, None, None)

    @classmethod
    def clear(cls):
        cls._tls.clear()

    @classmethod
    def summary(cls):
        return cls._tls.summary()
