"""SQLite persistence for Open Review Assistant."""

from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Iterator

from .scheduler import schedule_review


SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS review_items (
    item_id TEXT PRIMARY KEY,
    title TEXT NOT NULL CHECK (length(trim(title)) > 0),
    prompt TEXT NOT NULL CHECK (length(trim(prompt)) > 0),
    answer TEXT NOT NULL CHECK (length(trim(answer)) > 0),
    tags_json TEXT NOT NULL DEFAULT '[]',
    due_date TEXT NOT NULL,
    interval_days INTEGER NOT NULL DEFAULT 0 CHECK (interval_days >= 0),
    ease REAL NOT NULL DEFAULT 2.50 CHECK (ease >= 1.30 AND ease <= 3.00),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS review_items_due_idx
ON review_items(due_date, created_at, item_id);

CREATE TABLE IF NOT EXISTS review_events (
    event_id TEXT PRIMARY KEY,
    item_id TEXT NOT NULL REFERENCES review_items(item_id) ON DELETE CASCADE,
    reviewed_at TEXT NOT NULL,
    score INTEGER NOT NULL CHECK (score BETWEEN 0 AND 5),
    previous_interval INTEGER NOT NULL CHECK (previous_interval >= 0),
    next_interval INTEGER NOT NULL CHECK (next_interval >= 1),
    previous_ease REAL NOT NULL,
    next_ease REAL NOT NULL,
    next_due_date TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS review_events_item_idx
ON review_events(item_id, reviewed_at);
"""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _normalize_tags(tags: list[str] | None) -> list[str]:
    normalized = {tag.strip().lower() for tag in (tags or []) if tag.strip()}
    return sorted(normalized)


class ReviewStore:
    def __init__(self, database: str | Path):
        self.database = Path(database).expanduser().resolve()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.database)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 5000")
        try:
            yield connection
        finally:
            connection.close()

    def initialize(self) -> dict[str, object]:
        self.database.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            connection.executescript(SCHEMA)
            integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
            connection.commit()
        try:
            self.database.chmod(0o600)
        except OSError:
            pass
        return {"status": "ready", "database": str(self.database), "integrity_check": integrity}

    def add_item(
        self,
        *,
        title: str,
        prompt: str,
        answer: str,
        tags: list[str] | None = None,
        item_id: str | None = None,
        due_date: str | None = None,
    ) -> dict[str, object]:
        title, prompt, answer = title.strip(), prompt.strip(), answer.strip()
        if not title or not prompt or not answer:
            raise ValueError("title, prompt, and answer must not be empty")
        item_id = item_id or f"item_{uuid.uuid4().hex}"
        due_date = due_date or date.today().isoformat()
        date.fromisoformat(due_date)
        now = _utc_now()
        normalized_tags = _normalize_tags(tags)
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO review_items(
                    item_id, title, prompt, answer, tags_json, due_date,
                    interval_days, ease, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, 0, 2.50, ?, ?)
                """,
                (item_id, title, prompt, answer, json.dumps(normalized_tags), due_date, now, now),
            )
            connection.commit()
        return {
            "item_id": item_id,
            "title": title,
            "prompt": prompt,
            "tags": normalized_tags,
            "due_date": due_date,
        }

    def next_item(
        self,
        *,
        on_date: str | None = None,
        tag: str | None = None,
        show_answer: bool = False,
    ) -> dict[str, object] | None:
        on_date = on_date or date.today().isoformat()
        date.fromisoformat(on_date)
        query = "SELECT * FROM review_items WHERE due_date <= ?"
        parameters: list[object] = [on_date]
        if tag:
            query += " AND EXISTS (SELECT 1 FROM json_each(tags_json) WHERE value = ?)"
            parameters.append(tag.strip().lower())
        query += " ORDER BY due_date, created_at, item_id LIMIT 1"
        with self.connect() as connection:
            row = connection.execute(query, parameters).fetchone()
        if row is None:
            return None
        result: dict[str, object] = {
            "item_id": row["item_id"],
            "title": row["title"],
            "prompt": row["prompt"],
            "tags": json.loads(row["tags_json"]),
            "due_date": row["due_date"],
            "interval_days": row["interval_days"],
        }
        if show_answer:
            result["answer"] = row["answer"]
        return result

    def grade_item(
        self, item_id: str, score: int, *, reviewed_on: str | None = None
    ) -> dict[str, object]:
        reviewed_on = reviewed_on or date.today().isoformat()
        reviewed_date = date.fromisoformat(reviewed_on)
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT interval_days, ease FROM review_items WHERE item_id = ?", (item_id,)
            ).fetchone()
            if row is None:
                raise KeyError(f"unknown item_id: {item_id}")
            next_schedule = schedule_review(row["interval_days"], row["ease"], score)
            next_due = (reviewed_date + timedelta(days=next_schedule.interval_days)).isoformat()
            event_id = f"event_{uuid.uuid4().hex}"
            now = _utc_now()
            connection.execute(
                """
                INSERT INTO review_events(
                    event_id, item_id, reviewed_at, score, previous_interval,
                    next_interval, previous_ease, next_ease, next_due_date
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_id,
                    item_id,
                    now,
                    score,
                    row["interval_days"],
                    next_schedule.interval_days,
                    row["ease"],
                    next_schedule.ease,
                    next_due,
                ),
            )
            connection.execute(
                """
                UPDATE review_items
                SET due_date = ?, interval_days = ?, ease = ?, updated_at = ?
                WHERE item_id = ?
                """,
                (next_due, next_schedule.interval_days, next_schedule.ease, now, item_id),
            )
            connection.commit()
        return {
            "event_id": event_id,
            "item_id": item_id,
            "score": score,
            "previous_interval": row["interval_days"],
            "next_interval": next_schedule.interval_days,
            "next_ease": next_schedule.ease,
            "next_due_date": next_due,
        }

    def stats(self, *, on_date: str | None = None) -> dict[str, object]:
        on_date = on_date or date.today().isoformat()
        date.fromisoformat(on_date)
        with self.connect() as connection:
            item_stats = connection.execute(
                """
                SELECT COUNT(*) AS total,
                       SUM(CASE WHEN due_date <= ? THEN 1 ELSE 0 END) AS due
                FROM review_items
                """,
                (on_date,),
            ).fetchone()
            event_stats = connection.execute(
                "SELECT COUNT(*) AS total, AVG(score) AS average_score FROM review_events"
            ).fetchone()
        return {
            "as_of": on_date,
            "items": int(item_stats["total"]),
            "due": int(item_stats["due"] or 0),
            "reviews": int(event_stats["total"]),
            "average_score": (
                round(float(event_stats["average_score"]), 2)
                if event_stats["average_score"] is not None
                else None
            ),
        }
