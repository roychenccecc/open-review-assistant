"""Minimal MCP stdio server for the review workflow."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .store import ReviewStore


TOOLS = [
    {
        "name": "review_add_item",
        "description": "Add a new local review item.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "prompt": {"type": "string"},
                "answer": {"type": "string"},
                "tags": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["title", "prompt", "answer"],
            "additionalProperties": False,
        },
    },
    {
        "name": "review_next",
        "description": "Return the next due item without its answer.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "on_date": {"type": "string"},
                "tag": {"type": "string"},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "review_grade",
        "description": "Record a score from 0 to 5 and schedule the next review.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "item_id": {"type": "string"},
                "score": {"type": "integer", "minimum": 0, "maximum": 5},
                "reviewed_on": {"type": "string"},
            },
            "required": ["item_id", "score"],
            "additionalProperties": False,
        },
    },
    {
        "name": "review_stats",
        "description": "Return local item and review statistics.",
        "inputSchema": {
            "type": "object",
            "properties": {"on_date": {"type": "string"}},
            "additionalProperties": False,
        },
    },
]


class McpServer:
    def __init__(self, store: ReviewStore):
        self.store = store
        self.store.initialize()

    def call_tool(self, name: str, arguments: dict[str, Any]) -> object:
        if name == "review_add_item":
            return self.store.add_item(**arguments)
        if name == "review_next":
            return self.store.next_item(**arguments)
        if name == "review_grade":
            return self.store.grade_item(
                arguments["item_id"],
                arguments["score"],
                reviewed_on=arguments.get("reviewed_on"),
            )
        if name == "review_stats":
            return self.store.stats(on_date=arguments.get("on_date"))
        raise ValueError(f"unknown tool: {name}")

    def handle(self, request: dict[str, Any]) -> dict[str, Any] | None:
        request_id = request.get("id")
        method = request.get("method")
        if method == "notifications/initialized":
            return None
        if method == "initialize":
            params = request.get("params") or {}
            result = {
                "protocolVersion": params.get("protocolVersion", "2025-03-26"),
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "open-review-assistant", "version": "0.1.0"},
            }
        elif method == "tools/list":
            result = {"tools": TOOLS}
        elif method == "tools/call":
            params = request.get("params") or {}
            payload = self.call_tool(params.get("name", ""), params.get("arguments") or {})
            result = {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
                    }
                ],
                "structuredContent": payload,
                "isError": False,
            }
        else:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32601, "message": f"Method not found: {method}"},
            }
        return {"jsonrpc": "2.0", "id": request_id, "result": result}


def serve(database: Path) -> None:
    server = McpServer(ReviewStore(database))
    for line in sys.stdin:
        try:
            request = json.loads(line)
            response = server.handle(request)
            if response is not None:
                print(json.dumps(response, ensure_ascii=False, separators=(",", ":")), flush=True)
        except Exception as exc:
            request_id = request.get("id") if isinstance(locals().get("request"), dict) else None
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32603, "message": str(exc)},
            }
            print(json.dumps(response, ensure_ascii=False, separators=(",", ":")), flush=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    args = parser.parse_args(argv)
    serve(args.database)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
