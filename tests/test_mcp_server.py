from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from open_review_assistant.mcp_server import McpServer
from open_review_assistant.store import ReviewStore


class McpServerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.server = McpServer(ReviewStore(Path(self.tempdir.name) / "review.sqlite3"))

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_initialize_and_list_tools(self) -> None:
        initialized = self.server.handle({"jsonrpc": "2.0", "id": 1, "method": "initialize"})
        self.assertEqual(initialized["result"]["serverInfo"]["name"], "open-review-assistant")
        listed = self.server.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        self.assertEqual(len(listed["result"]["tools"]), 4)

    def test_tool_call_returns_structured_content_without_answer(self) -> None:
        added = self.server.handle(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "review_add_item",
                    "arguments": {
                        "title": "Demo",
                        "prompt": "Prompt",
                        "answer": "Secret answer",
                    },
                },
            }
        )
        self.assertFalse(added["result"]["isError"])
        result = self.server.handle(
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {"name": "review_next", "arguments": {}},
            }
        )
        self.assertNotIn("answer", result["result"]["structuredContent"])


if __name__ == "__main__":
    unittest.main()
