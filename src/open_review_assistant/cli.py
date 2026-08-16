"""Command-line interface for Open Review Assistant."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .demo import DEMO_ITEMS
from .store import ReviewStore


def _emit(payload: object, as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    elif payload is None:
        print("No due review items.")
    elif isinstance(payload, dict):
        for key, value in payload.items():
            print(f"{key}: {value}")
    else:
        print(payload)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=Path("review.sqlite3"))
    parser.add_argument("--json", action="store_true", dest="as_json")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("init", help="Initialize the SQLite database")

    add = subparsers.add_parser("add", help="Add a review item")
    add.add_argument("--title", required=True)
    add.add_argument("--prompt", required=True)
    add.add_argument("--answer", required=True)
    add.add_argument("--tags", nargs="*", default=[])
    add.add_argument("--due-date")

    next_parser = subparsers.add_parser("next", help="Return the next due item")
    next_parser.add_argument("--on-date")
    next_parser.add_argument("--tag")
    next_parser.add_argument("--show-answer", action="store_true")

    grade = subparsers.add_parser("grade", help="Grade a review item")
    grade.add_argument("item_id")
    grade.add_argument("score", type=int, choices=range(0, 6))
    grade.add_argument("--reviewed-on")

    stats = subparsers.add_parser("stats", help="Show review statistics")
    stats.add_argument("--on-date")

    subparsers.add_parser("seed-demo", help="Load synthetic demo items")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    store = ReviewStore(args.database)
    try:
        if args.command == "init":
            result = store.initialize()
        else:
            store.initialize()
            if args.command == "add":
                result = store.add_item(
                    title=args.title,
                    prompt=args.prompt,
                    answer=args.answer,
                    tags=args.tags,
                    due_date=args.due_date,
                )
            elif args.command == "next":
                result = store.next_item(
                    on_date=args.on_date, tag=args.tag, show_answer=args.show_answer
                )
            elif args.command == "grade":
                result = store.grade_item(
                    args.item_id, args.score, reviewed_on=args.reviewed_on
                )
            elif args.command == "stats":
                result = store.stats(on_date=args.on_date)
            elif args.command == "seed-demo":
                result = [store.add_item(**item) for item in DEMO_ITEMS]
            else:
                raise AssertionError("unreachable command")
        _emit(result, args.as_json)
        return 0
    except (ValueError, KeyError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
