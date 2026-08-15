from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from paios_obsidian.mcp import (
    READ_TOOLS,
    SERVER_INSTRUCTIONS,
    WRITE_TOOLS,
    ObsidianMcpServer,
)


OBSIDIAN_ROOT = Path(__file__).parents[1]
EXAMPLE_CONFIG = OBSIDIAN_ROOT.parent / "config.example.toml"
SERVER = OBSIDIAN_ROOT / "src" / "obsidian_mcp_server.py"


class McpTests(unittest.TestCase):
    def _config(self, directory: str, *, writes: bool = False) -> Path:
        vault = Path(directory) / "vault"
        (vault / "Published").mkdir(parents=True)
        config = Path(directory) / "integrations.toml"
        config.write_text(
            f"""
[obsidian]
vault_path = {json.dumps(str(vault))}
write_enabled = {str(writes).lower()}
allowed_write_roots = {json.dumps(["Published"] if writes else [])}
""".strip()
            + "\n",
            encoding="utf-8",
        )
        return config

    def test_default_inventory_contains_only_five_read_tools(self) -> None:
        tools = ObsidianMcpServer(EXAMPLE_CONFIG).available_tools()
        self.assertEqual(len(tools), 5)
        self.assertTrue(all(tool.annotations["readOnlyHint"] for tool in tools))
        self.assertFalse(any(word in tool.name for tool in tools for word in ("delete", "move", "bulk")))
        self.assertLessEqual(len(SERVER_INSTRUCTIONS), 512)

    def test_write_tools_appear_only_when_explicitly_enabled(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config = self._config(directory, writes=True)
            tools = ObsidianMcpServer(config).available_tools()
        self.assertEqual(len(tools), len(READ_TOOLS) + len(WRITE_TOOLS))
        self.assertEqual({tool.name for tool in tools if tool.write}, {tool.name for tool in WRITE_TOOLS})

    def test_write_annotations_distinguish_create_and_replace(self) -> None:
        tools = {tool.name: tool for tool in WRITE_TOOLS}
        self.assertFalse(tools["obsidian_publish_note"].annotations["destructiveHint"])
        self.assertTrue(tools["obsidian_update_note"].annotations["destructiveHint"])
        self.assertTrue(all(tool.annotations["idempotentHint"] for tool in WRITE_TOOLS))

    def test_every_tool_has_specific_output_schema(self) -> None:
        for tool in READ_TOOLS + WRITE_TOOLS:
            data = tool.as_mcp()["outputSchema"]["properties"]["data"]
            self.assertEqual(data["type"], "object", tool.name)
            self.assertTrue(data.get("properties"), tool.name)
            self.assertTrue(data.get("required"), tool.name)

    def test_initialize_and_tools_list_follow_json_rpc(self) -> None:
        server = ObsidianMcpServer(EXAMPLE_CONFIG)
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
        self.assertEqual(len(listed["result"]["tools"]), 5)

    def test_identity_and_closed_arguments_return_structured_errors(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config = self._config(directory)
            server = ObsidianMcpServer(config)
            missing_identity = server.handle(
                {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "tools/call",
                    "params": {"name": "obsidian_get_note", "arguments": {}},
                }
            )
            extra = server.handle(
                {
                    "jsonrpc": "2.0",
                    "id": 4,
                    "method": "tools/call",
                    "params": {"name": "obsidian_status", "arguments": {"command": "delete"}},
                }
            )
        self.assertEqual(missing_identity["result"]["structuredContent"]["error"]["code"], "INVALID_ARGUMENT")
        self.assertEqual(extra["result"]["structuredContent"]["error"]["code"], "INVALID_ARGUMENT")

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
        self.assertEqual(len(responses[1]["result"]["tools"]), 5)


if __name__ == "__main__":
    unittest.main()
