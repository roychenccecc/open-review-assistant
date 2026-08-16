"""Deterministic scheduling rules for review items."""

from __future__ import annotations

from dataclasses import dataclass


MIN_EASE = 1.3
MAX_EASE = 3.0


@dataclass(frozen=True)
class Schedule:
    interval_days: int
    ease: float


def schedule_review(previous_interval: int, ease: float, score: int) -> Schedule:
    """Return the next interval and ease for a score from zero to five."""
    if score < 0 or score > 5:
        raise ValueError("score must be between 0 and 5")
    if previous_interval < 0:
        raise ValueError("previous_interval must not be negative")

    ease = min(MAX_EASE, max(MIN_EASE, ease))
    if score <= 1:
        interval = 1
        ease -= 0.20
    elif score == 2:
        interval = max(1, round(previous_interval * 0.60))
        ease -= 0.10
    elif score == 3:
        interval = 1 if previous_interval == 0 else max(1, round(previous_interval * 1.50))
    elif score == 4:
        interval = 3 if previous_interval == 0 else max(2, round(previous_interval * ease))
        ease += 0.05
    else:
        interval = 5 if previous_interval == 0 else max(3, round(previous_interval * (ease + 0.15)))
        ease += 0.10

    return Schedule(interval_days=interval, ease=round(min(MAX_EASE, max(MIN_EASE, ease)), 2))
