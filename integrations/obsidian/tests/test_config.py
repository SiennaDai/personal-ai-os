from __future__ import annotations

import tempfile
import tomllib
import unittest
from pathlib import Path

from paios_obsidian.config import ObsidianConfig, append_runtime_config, load_config
from paios_obsidian.errors import IntegrationError


class ConfigTests(unittest.TestCase):
    def test_example_config_is_valid_and_default_off(self) -> None:
        config = load_config(Path(__file__).parents[2] / "config.example.toml")
        self.assertEqual(config.vault_alias, "knowledge")
        self.assertEqual(config.read_roots, (".",))
        self.assertFalse(config.cli_enabled)
        self.assertFalse(config.write_enabled)

    def test_unknown_field_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "integrations.toml"
            path.write_text("[obsidian]\nunknown = true\n", encoding="utf-8")
            with self.assertRaisesRegex(IntegrationError, "Unknown Obsidian"):
                load_config(path)

    def test_write_root_cannot_be_vault_root(self) -> None:
        config = ObsidianConfig(write_enabled=True, allowed_write_roots=(".",))
        with self.assertRaisesRegex(IntegrationError, "Vault root"):
            config.validate()

    def test_write_root_must_be_inside_read_scope(self) -> None:
        config = ObsidianConfig(
            read_roots=("Readable",),
            write_enabled=True,
            allowed_write_roots=("Elsewhere",),
        )
        with self.assertRaisesRegex(IntegrationError, "contained"):
            config.validate()

    def test_protected_and_windows_reserved_roots_are_rejected(self) -> None:
        for root in (".obsidian", "Knowledge/.hidden", "CON", "Folder/NUL.md"):
            with self.subTest(root=root):
                with self.assertRaises(IntegrationError):
                    ObsidianConfig(read_roots=(root,)).validate()

    def test_cli_requires_both_official_command_and_selector(self) -> None:
        with self.assertRaisesRegex(IntegrationError, "absolute cli_command"):
            ObsidianConfig(cli_enabled=True, cli_vault_selector="vault").validate()
        with self.assertRaisesRegex(IntegrationError, "official Obsidian"):
            ObsidianConfig(
                cli_enabled=True,
                cli_command="/usr/bin/bash",
                cli_vault_selector="vault",
            ).validate()
        with self.assertRaisesRegex(IntegrationError, "must be empty"):
            ObsidianConfig(cli_command="/usr/bin/obsidian").validate()

    def test_public_summary_never_returns_paths_or_selector(self) -> None:
        config = ObsidianConfig(
            vault_path="/private/vault",
            cli_enabled=True,
            cli_command="/private/Obsidian.com",
            cli_vault_selector="private-id",
        )
        config.validate()
        rendered = str(config.public_summary())
        self.assertNotIn("/private", rendered)
        self.assertNotIn("private-id", rendered)

    def test_append_runtime_config_preserves_existing_table_and_disables_writes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "integrations.toml"
            path.write_text('[zotero]\nlibrary_alias = "personal"\n', encoding="utf-8")
            append_runtime_config(path, ObsidianConfig(vault_path="/tmp/vault"))
            with path.open("rb") as handle:
                document = tomllib.load(handle)
        self.assertEqual(document["zotero"]["library_alias"], "personal")
        self.assertFalse(document["obsidian"]["write_enabled"])
        self.assertEqual(document["obsidian"]["allowed_write_roots"], [])

    def test_append_runtime_config_refuses_existing_obsidian_table(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "integrations.toml"
            path.write_text('[obsidian]\nvault_path = "/tmp/vault"\n', encoding="utf-8")
            with self.assertRaisesRegex(IntegrationError, "already contains"):
                append_runtime_config(path, ObsidianConfig(vault_path="/tmp/vault"))


if __name__ == "__main__":
    unittest.main()
