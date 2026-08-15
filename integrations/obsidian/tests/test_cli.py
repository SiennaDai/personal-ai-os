from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from typing import Sequence

from paios_obsidian.cli import ObsidianCli
from paios_obsidian.config import ObsidianConfig
from paios_obsidian.errors import IntegrationError


class FakeExecutor:
    def __init__(self, vault: Path) -> None:
        self.vault = vault
        self.calls: list[list[str]] = []
        self.responses: dict[str, tuple[int, bytes, bytes]] = {
            "version": (0, b"1.13.7 (installer 1.13.7)\n", b""),
            "vault": (0, str(vault).encode("utf-8") + b"\n", b""),
            "search": (0, b"[]\n", b""),
            "properties": (0, b"{}\n", b""),
            "links": (0, b"", b""),
            "backlinks": (0, b"[]\n", b""),
            "unresolved": (0, b"[]\n", b""),
        }

    def __call__(
        self,
        arguments: Sequence[str],
        timeout: float,
    ) -> subprocess.CompletedProcess[bytes]:
        vector = list(arguments)
        self.calls.append(vector)
        command = vector[2]
        returncode, stdout, stderr = self.responses[command]
        return subprocess.CompletedProcess(vector, returncode, stdout, stderr)


class CliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.vault = Path(self.temporary.name) / "vault"
        self.vault.mkdir()
        self.executable = Path(self.temporary.name) / "Obsidian.com"
        self.executable.write_bytes(b"placeholder")
        self.config = ObsidianConfig(
            vault_path=str(self.vault),
            cli_enabled=True,
            cli_command=str(self.executable),
            cli_vault_selector="vault-id",
        )
        self.config.validate()
        self.executor = FakeExecutor(self.vault)
        self.cli = ObsidianCli(self.config, self.executor)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_status_verifies_supported_version_and_same_vault(self) -> None:
        status = self.cli.status()
        self.assertTrue(status["ready"])
        self.assertEqual(status["version"], "1.13.7")
        self.assertTrue(status["same_vault"])

    def test_vault_selector_is_first_and_query_is_one_argument(self) -> None:
        self.executor.responses["search"] = (
            0,
            json.dumps([{"path": "Knowledge/Alpha.md"}]).encode("utf-8"),
            b"",
        )
        paths = self.cli.search("attention query", folder="Knowledge", case_sensitive=False, limit=5)
        call = self.executor.calls[-1]
        self.assertEqual(call[1], "vault=vault-id")
        self.assertIn("query=attention query", call)
        self.assertEqual(paths, ["Knowledge/Alpha.md"])

    def test_ready_check_is_cached_for_followup_semantic_calls(self) -> None:
        self.cli.status()
        initial = len(self.executor.calls)
        self.cli.search("none", folder=".", case_sensitive=False, limit=1)
        self.assertEqual(len(self.executor.calls), initial + 1)

    def test_properties_accept_json_object_and_reject_nested_values(self) -> None:
        self.cli.status()
        self.executor.responses["properties"] = (
            0,
            b'{"type":"concept","tags":["ai"]}',
            b"",
        )
        self.assertEqual(self.cli.properties("Note.md")["type"], "concept")
        self.executor.responses["properties"] = (0, b'{"nested":{"x":1}}', b"")
        with self.assertRaisesRegex(IntegrationError, "property value"):
            self.cli.properties("Note.md")

    def test_backlinks_and_unresolved_are_normalized(self) -> None:
        self.cli.status()
        self.executor.responses["backlinks"] = (
            0,
            b'{"Knowledge/Source.md":2}',
            b"",
        )
        self.executor.responses["unresolved"] = (
            0,
            b'{"Missing":{"count":1,"sources":["Knowledge/Alpha.md"]}}',
            b"",
        )
        self.assertEqual(self.cli.backlinks("Knowledge/Alpha.md")[0]["count"], 2)
        self.assertEqual(self.cli.unresolved("Knowledge/Alpha.md")[0]["path"], "Missing")

    def test_live_cli_empty_notices_and_unresolved_suffix_are_supported(self) -> None:
        self.cli.status()
        self.executor.responses.update(
            {
                "search": (0, b"No matches found.\n", b""),
                "properties": (0, b"No frontmatter found.\n", b""),
                "links": (0, "Missing (unresolved)\n".encode(), b""),
                "backlinks": (0, b"No backlinks found.\n", b""),
                "unresolved": (
                    0,
                    b'[{"link":"Missing","count":1,"sources":["Knowledge/Alpha.md"]}]',
                    b"",
                ),
            }
        )
        self.assertEqual(self.cli.search("none", folder=".", case_sensitive=False, limit=1), [])
        self.assertEqual(self.cli.properties("Knowledge/Alpha.md"), {})
        self.assertEqual(self.cli.links("Knowledge/Alpha.md"), ["Missing"])
        self.assertEqual(self.cli.backlinks("Knowledge/Alpha.md"), [])
        self.assertEqual(self.cli.unresolved("Knowledge/Alpha.md")[0]["path"], "Missing")

    def test_non_allowlisted_native_command_is_rejected(self) -> None:
        with self.assertRaisesRegex(IntegrationError, "not allowlisted"):
            self.cli._run("delete", "path=Note.md")

    def test_timeout_exit_failure_and_output_bound_are_safe(self) -> None:
        self.executor.responses["version"] = (1, b"", b"private failure")
        status = self.cli.status()
        self.assertFalse(status["ready"])
        self.assertNotIn("private failure", str(status))

        small = ObsidianConfig(
            vault_path=str(self.vault),
            cli_enabled=True,
            cli_command=str(self.executable),
            cli_vault_selector="vault-id",
            max_cli_response_bytes=1_000,
        )
        executor = FakeExecutor(self.vault)
        executor.responses["version"] = (0, b"x" * 1_001, b"")
        with self.assertRaisesRegex(IntegrationError, "byte limit"):
            ObsidianCli(small, executor).version()

    def test_symlink_executable_is_rejected(self) -> None:
        link = Path(self.temporary.name) / "obsidian"
        link.symlink_to(self.executable)
        config = ObsidianConfig(
            vault_path=str(self.vault),
            cli_enabled=True,
            cli_command=str(link),
            cli_vault_selector="vault-id",
        )
        with self.assertRaisesRegex(IntegrationError, "non-symlink"):
            ObsidianCli(config, self.executor).version()


if __name__ == "__main__":
    unittest.main()
