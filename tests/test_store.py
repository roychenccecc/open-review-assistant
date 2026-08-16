from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from open_review_assistant.store import ReviewStore


class ReviewStoreTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.database = Path(self.tempdir.name) / "review.sqlite3"
        self.store = ReviewStore(self.database)
        self.store.initialize()

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_next_does_not_leak_answer(self) -> None:
        created = self.store.add_item(
            title="Synthetic item",
            prompt="A freely written prompt",
            answer="A freely written answer",
            tags=["Demo", "demo"],
            due_date="2026-01-01",
        )
        item = self.store.next_item(on_date="2026-01-01")
        self.assertEqual(item["item_id"], created["item_id"])
        self.assertEqual(item["tags"], ["demo"])
        self.assertNotIn("answer", item)

    def test_filter_and_grade(self) -> None:
        first = self.store.add_item(
            title="First", prompt="First prompt", answer="First answer",
            tags=["one"], due_date="2026-01-01"
        )
        self.store.add_item(
            title="Second", prompt="Second prompt", answer="Second answer",
            tags=["two"], due_date="2026-01-01"
        )
        item = self.store.next_item(on_date="2026-01-01", tag="one")
        self.assertEqual(item["item_id"], first["item_id"])

        event = self.store.grade_item(first["item_id"], 4, reviewed_on="2026-01-01")
        self.assertEqual(event["next_due_date"], "2026-01-04")
        self.assertEqual(self.store.stats(on_date="2026-01-01")["reviews"], 1)

    def test_unknown_item_is_rejected(self) -> None:
        with self.assertRaises(KeyError):
            self.store.grade_item("missing", 3, reviewed_on="2026-01-01")


if __name__ == "__main__":
    unittest.main()
