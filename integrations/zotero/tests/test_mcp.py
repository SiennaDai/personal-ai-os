from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from paios_zotero.mcp import READ_TOOLS, SERVER_INSTRUCTIONS, WRITE_TOOLS, ZoteroMcpServer


ZOTERO_ROOT = Path(__file__).parents[1]
EXAMPLE_CONFIG = ZOTERO_ROOT.parent / "config.example.toml"
SERVER = ZOTERO_ROOT / "src" / "zotero_mcp_server.py"


class McpTests(unittest.TestCase):
    def test_default_inventory_contains_only_nine_read_tools(self) -> None:
        tools = ZoteroMcpServer(EXAMPLE_CONFIG).available_tools()
        self.assertEqual(len(tools), 9)
        self.assertTrue(all(tool.annotations["readOnlyHint"] for tool in tools))
        self.assertFalse(any("delete" in tool.name or "bulk" in tool.name for tool in tools))
        self.assertLessEqual(len(SERVER_INSTRUCTIONS), 512)

    def test_write_tools_appear_only_when_explicitly_enabled(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / "integrations.toml"
            config.write_text(
                """
[zotero]
web_library_id = "123456"
write_enabled = true
write_scope = "library"
better_bibtex_enabled = false
""".strip()
                + "\n",
                encoding="utf-8",
            )
            tools = ZoteroMcpServer(config).available_tools()
        self.assertEqual(len(tools), len(READ_TOOLS) + len(WRITE_TOOLS))
        self.assertEqual({tool.name for tool in tools if tool.write}, {tool.name for tool in WRITE_TOOLS})
        self.assertEqual(len(WRITE_TOOLS), 5)
        self.assertIn("zotero_create_bibliographic_item", {tool.name for tool in WRITE_TOOLS})
        self.assertIn("zotero_add_item_to_collection", {tool.name for tool in WRITE_TOOLS})
        self.assertFalse(any("delete" in tool.name or "bulk" in tool.name for tool in WRITE_TOOLS))

    def test_every_tool_declares_a_tool_specific_output_data_schema(self) -> None:
        for tool in READ_TOOLS + WRITE_TOOLS:
            output = tool.as_mcp()["outputSchema"]
            data_schema = output["properties"]["data"]
            self.assertEqual(data_schema["type"], "object", tool.name)
            self.assertTrue(data_schema.get("properties"), tool.name)
            self.assertTrue(data_schema.get("required"), tool.name)

    def test_tools_list_keeps_protocol_maximum_and_caps_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / "integrations.toml"
            config.write_text(
                "[zotero]\nmax_page_size = 7\nbetter_bibtex_enabled = false\n",
                encoding="utf-8",
            )
            listed = ZoteroMcpServer(config).handle(
                {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
            )
        schemas = {
            tool["name"]: tool["inputSchema"]
            for tool in listed["result"]["tools"]
        }
        for name in (
            "zotero_search_items",
            "zotero_list_collections",
            "zotero_get_collection_items",
            "zotero_get_item_children",
            "zotero_get_annotations",
        ):
            limit = schemas[name]["properties"]["limit"]
            self.assertEqual(limit["maximum"], 100, name)
            self.assertLessEqual(limit["default"], 7, name)

    def test_tool_validation_enforces_protocol_page_maximum(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / "integrations.toml"
            config.write_text(
                "[zotero]\nmax_page_size = 7\nbetter_bibtex_enabled = false\n",
                encoding="utf-8",
            )
            response = ZoteroMcpServer(config).handle(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/call",
                    "params": {
                        "name": "zotero_search_items",
                        "arguments": {"query": "test", "limit": 101},
                    },
                }
            )
        result = response["result"]
        self.assertTrue(result["isError"])
        self.assertEqual(result["structuredContent"]["error"]["code"], "INVALID_ARGUMENT")
        self.assertEqual(
            result["structuredContent"]["error"]["message"],
            "arguments.limit is above the maximum",
        )

    def test_dispatch_clamps_default_and_explicit_limits_to_configured_cap(self) -> None:
        class FakeService:
            config = SimpleNamespace(max_page_size=7)

            def search_items(self, query: str, **kwargs: object) -> dict[str, object]:
                return {"query": query, "limit": kwargs["limit"]}

        default_result = ZoteroMcpServer._dispatch(
            FakeService(),
            "zotero_search_items",
            {"query": "test"},
        )
        explicit_result = ZoteroMcpServer._dispatch(
            FakeService(),
            "zotero_search_items",
            {"query": "test", "limit": 100},
        )
        self.assertEqual(default_result["limit"], 7)
        self.assertEqual(explicit_result["limit"], 7)

    def test_initialize_and_tools_list_follow_json_rpc(self) -> None:
        server = ZoteroMcpServer(EXAMPLE_CONFIG)
        initialized = server.handle(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {},
                    "clientInfo": {"name": "test", "version": "1"},
                },
            }
        )
        self.assertEqual(initialized["result"]["protocolVersion"], "2025-06-18")
        listed = server.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
        self.assertEqual(len(listed["result"]["tools"]), 9)

    def test_invalid_tool_arguments_return_structured_tool_error(self) -> None:
        server = ZoteroMcpServer(EXAMPLE_CONFIG)
        response = server.handle(
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": "zotero_get_item", "arguments": {"item_key": "bad"}},
            }
        )
        result = response["result"]
        self.assertTrue(result["isError"])
        self.assertEqual(result["structuredContent"]["error"]["code"], "INVALID_ARGUMENT")
        self.assertEqual(
            json.loads(result["content"][0]["text"]),
            result["structuredContent"],
        )

    def test_stdio_transport_delimits_messages_with_newlines(self) -> None:
        messages = [
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {},
                    "clientInfo": {"name": "test", "version": "1"},
                },
            },
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        ]
        payload = "".join(json.dumps(message) + "\n" for message in messages)
        process = subprocess.run(
            [sys.executable, str(SERVER), "--config", str(EXAMPLE_CONFIG), "serve"],
            input=payload,
            text=True,
            capture_output=True,
            check=False,
            timeout=5,
        )
        self.assertEqual(process.returncode, 0, process.stderr)
        responses = [json.loads(line) for line in process.stdout.splitlines()]
        self.assertEqual([response["id"] for response in responses], [1, 2])
        self.assertEqual(len(responses[1]["result"]["tools"]), 9)


if __name__ == "__main__":
    unittest.main()
