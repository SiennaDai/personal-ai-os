from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from paios_obsidian.config import ObsidianConfig
from paios_obsidian.service import ObsidianService
from paios_obsidian.smoke import run_read_smoke


class SmokeTests(unittest.TestCase):
    def test_read_smoke_returns_only_capability_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            vault = Path(directory) / "vault"
            vault.mkdir()
            (vault / "Private-name.md").write_text("private body", encoding="utf-8")
            service = ObsidianService(ObsidianConfig(vault_path=str(vault)))
            result = run_read_smoke(service)
        self.assertTrue(result["overall_ok"])
        self.assertTrue(result["exercised"]["exact_read"])
        rendered = str(result)
        self.assertNotIn("Private-name", rendered)
        self.assertNotIn("private body", rendered)

    def test_empty_vault_is_valid_but_exact_read_is_not_exercised(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            vault = Path(directory) / "vault"
            vault.mkdir()
            result = run_read_smoke(
                ObsidianService(ObsidianConfig(vault_path=str(vault)))
            )
        self.assertTrue(result["overall_ok"])
        self.assertFalse(result["note_available"])
        self.assertFalse(result["exercised"]["exact_read"])


if __name__ == "__main__":
    unittest.main()
