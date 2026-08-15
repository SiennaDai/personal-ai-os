from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from paios_obsidian.config import ObsidianConfig
from paios_obsidian.errors import IntegrationError
from paios_obsidian.filesystem import VaultFilesystem
from paios_obsidian.service import ObsidianService


class FakeCli:
    def __init__(self, *, ready: bool = True) -> None:
        self.ready = ready

    def status(self) -> dict[str, object]:
        return {
            "enabled": True,
            "ready": self.ready,
            "error_code": None if self.ready else "CLI_UNAVAILABLE",
            "version": "1.13.7" if self.ready else None,
            "installer_version": "1.13.7" if self.ready else None,
            "supported": self.ready,
            "same_vault": self.ready,
            "capabilities": ["obsidian_search", "properties", "links", "backlinks"]
            if self.ready
            else [],
        }

    def search(self, query: str, **kwargs: object) -> list[str]:
        if not self.ready:
            raise IntegrationError("CLI_UNAVAILABLE", "not ready")
        return ["Knowledge/Alpha.md"] if query == "alpha" else []

    def properties(self, path: str) -> dict[str, object]:
        return {"type": "concept", "tags": ["ai"]}

    def links(self, path: str) -> list[str]:
        return ["Knowledge/Beta.md", "Missing"]

    def backlinks(self, path: str) -> list[dict[str, object]]:
        return [{"path": "Knowledge/Beta.md", "count": 2}]

    def unresolved(self, path: str) -> list[dict[str, object]]:
        return [{"path": "Missing", "count": 1}]


class ServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.vault = Path(self.temporary.name) / "vault"
        (self.vault / "Knowledge").mkdir(parents=True)
        (self.vault / "Knowledge" / "Alpha.md").write_text("# Alpha\n", encoding="utf-8")
        (self.vault / "Knowledge" / "Beta.md").write_text("# Beta\n", encoding="utf-8")
        self.config = ObsidianConfig(
            vault_path=str(self.vault),
            read_roots=("Knowledge",),
            cli_enabled=True,
            cli_command="/tmp/Obsidian.com",
            cli_vault_selector="vault",
        )
        self.config.validate()
        self.filesystem = VaultFilesystem(self.config)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def service(self, *, ready: bool = True) -> ObsidianService:
        return ObsidianService(
            self.config,
            filesystem=self.filesystem,
            cli=FakeCli(ready=ready),
        )

    def test_status_is_healthy_or_degraded_without_note_identity(self) -> None:
        healthy = self.service().status()
        degraded = self.service(ready=False).status()
        self.assertEqual(healthy["state"], "healthy")
        self.assertEqual(degraded["state"], "degraded")
        self.assertNotIn("Alpha", str(healthy))
        self.assertNotIn(str(self.vault), str(healthy))

    def test_obsidian_search_returns_hashed_in_scope_notes(self) -> None:
        result = self.service().search_notes("alpha", "obsidian")
        self.assertEqual(result["matches"][0]["note"]["path"], "Knowledge/Alpha.md")
        self.assertTrue(result["matches"][0]["note"]["revision"].startswith("sha256:"))

    def test_search_modes_do_not_silently_change_semantics(self) -> None:
        with self.assertRaisesRegex(IntegrationError, "literal mode"):
            self.service().search_notes(
                "alpha",
                "obsidian",
                include_excerpt=True,
            )
        with self.assertRaisesRegex(IntegrationError, "mode"):
            self.service().search_notes("alpha", "semantic")

    def test_get_note_can_add_cli_properties_with_separate_provenance(self) -> None:
        result = self.service().get_note(
            path="Knowledge/Alpha.md",
            include_properties=True,
        )
        self.assertEqual(result["properties"]["type"], "concept")
        self.assertEqual(result["provenance"]["content_backend"], "vault_filesystem")
        self.assertEqual(result["provenance"]["properties_backend"], "official_cli")

    def test_get_links_preserves_resolved_unresolved_and_backlinks(self) -> None:
        result = self.service().get_links(path="Knowledge/Alpha.md")
        resolved = [entry for entry in result["outgoing"] if entry["resolved"]]
        unresolved = [entry for entry in result["outgoing"] if not entry["resolved"]]
        self.assertEqual(resolved[0]["note"]["path"], "Knowledge/Beta.md")
        self.assertEqual(unresolved[0]["target"], "Missing")
        self.assertEqual(result["backlinks"][0]["count"], 2)

    def test_cli_returned_out_of_scope_search_path_fails_closed(self) -> None:
        class BadCli(FakeCli):
            def search(self, query: str, **kwargs: object) -> list[str]:
                return ["Outside.md"]

        service = ObsidianService(self.config, filesystem=self.filesystem, cli=BadCli())
        with self.assertRaisesRegex(IntegrationError, "outside"):
            service.search_notes("alpha", "obsidian")


if __name__ == "__main__":
    unittest.main()
