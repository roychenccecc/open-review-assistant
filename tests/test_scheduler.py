from __future__ import annotations

import unittest

from open_review_assistant.scheduler import schedule_review


class SchedulerTest(unittest.TestCase):
    def test_first_success_uses_seed_interval(self) -> None:
        self.assertEqual(schedule_review(0, 2.5, 4).interval_days, 3)
        self.assertEqual(schedule_review(0, 2.5, 5).interval_days, 5)

    def test_failure_restarts_and_lowers_ease(self) -> None:
        result = schedule_review(20, 2.5, 1)
        self.assertEqual(result.interval_days, 1)
        self.assertEqual(result.ease, 2.3)

    def test_ease_stays_bounded(self) -> None:
        self.assertEqual(schedule_review(1, 1.3, 0).ease, 1.3)
        self.assertEqual(schedule_review(10, 3.0, 5).ease, 3.0)

    def test_invalid_values_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            schedule_review(1, 2.5, 6)
        with self.assertRaises(ValueError):
            schedule_review(-1, 2.5, 3)


if __name__ == "__main__":
    unittest.main()
