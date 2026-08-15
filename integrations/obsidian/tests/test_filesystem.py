from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from paios_obsidian.config import ObsidianConfig
from paios_obsidian.errors import IntegrationError
from paios_obsidian.filesystem import VaultFilesystem, normalize_note_path


class FilesystemTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.vault = Path(self.temporary.name) / "vault"
        (self.vault / "Knowledge" / "Sub").mkdir(parents=True)
        (self.vault / "Knowledge" / "Published").mkdir()
        (self.vault / ".obsidian").mkdir()
        (self.vault / ".hidden").mkdir()
        (self.vault / "Knowledge" / "Alpha.md").write_text(
            "# Alpha\n\nAttention is useful.\n",
            encoding="utf-8",
        )
        (self.vault / "Knowledge" / "Sub" / "Beta.md").write_text(
            "# Beta\n\nSecond note.\n",
            encoding="utf-8",
        )
        (self.vault / ".hidden" / "Secret.md").write_text("secret", encoding="utf-8")
        (self.vault / "Outside.md").write_text("outside", encoding="utf-8")
        self.config = ObsidianConfig(
            vault_path=str(self.vault),
            read_roots=("Knowledge",),
            write_enabled=True,
            allowed_write_roots=("Knowledge/Published",),
            max_read_chars=1_000,
        )
        self.config.validate()
        self.filesystem = VaultFilesystem(self.config)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_list_is_scoped_sorted_and_returns_revisions(self) -> None:
        result = self.filesystem.list_notes()
        paths = [note["path"] for note in result["notes"]]
        self.assertEqual(paths, ["Knowledge/Alpha.md", "Knowledge/Sub/Beta.md"])
        self.assertTrue(all(note["revision"].startswith("sha256:") for note in result["notes"]))
        self.assertNotIn("Secret", str(result))
        self.assertNotIn(str(self.vault), str(result))

    def test_get_note_returns_exact_slice_and_canonical_ref(self) -> None:
        result = self.filesystem.get_note(path="Knowledge/Alpha.md", offset=2, max_chars=5)
        self.assertEqual(result["content"], "Alpha")
        ref = result["note"]["id"]
        by_ref = self.filesystem.get_note(ref=ref, max_chars=1)
        self.assertEqual(by_ref["note"]["revision"], result["note"]["revision"])

    def test_identity_requires_exactly_one_ref_or_path(self) -> None:
        for kwargs in ({}, {"ref": "x", "path": "Knowledge/Alpha.md"}):
            with self.subTest(kwargs=kwargs):
                with self.assertRaisesRegex(IntegrationError, "exactly one"):
                    self.filesystem.get_note(**kwargs)

    def test_literal_search_is_bounded_and_can_return_excerpt(self) -> None:
        result = self.filesystem.search_literal("attention", include_excerpt=True)
        self.assertEqual(len(result["matches"]), 1)
        self.assertEqual(result["matches"][0]["note"]["path"], "Knowledge/Alpha.md")
        self.assertIn("Attention", result["matches"][0]["excerpt"])

    def test_read_scope_blocks_outside_note(self) -> None:
        with self.assertRaisesRegex(IntegrationError, "outside"):
            self.filesystem.get_note(path="Outside.md")

    def test_traversal_absolute_windows_and_protected_paths_are_rejected(self) -> None:
        paths = (
            "../Outside.md",
            "/tmp/note.md",
            "C:/note.md",
            "Knowledge\\Alpha.md",
            ".obsidian/app.md",
            "Knowledge/CON.md",
        )
        for path in paths:
            with self.subTest(path=path):
                with self.assertRaises(IntegrationError):
                    normalize_note_path(path)

    def test_case_mismatch_is_rejected(self) -> None:
        with self.assertRaisesRegex(IntegrationError, "spelling"):
            self.filesystem.get_note(path="Knowledge/alpha.md")

    def test_symlink_read_and_write_escape_are_denied(self) -> None:
        outside = Path(self.temporary.name) / "outside"
        outside.mkdir()
        (outside / "Leak.md").write_text("leak", encoding="utf-8")
        (self.vault / "Knowledge" / "Linked").symlink_to(outside, target_is_directory=True)
        with self.assertRaises(IntegrationError):
            self.filesystem.get_note(path="Knowledge/Linked/Leak.md")

        (self.vault / "Knowledge" / "Published" / "Escape").symlink_to(
            outside,
            target_is_directory=True,
        )
        with self.assertRaisesRegex(IntegrationError, "Symlink"):
            self.filesystem.publish_note("Knowledge/Published/Escape/New.md", "no")

    def test_invalid_utf8_and_nul_are_rejected(self) -> None:
        (self.vault / "Knowledge" / "Bad.md").write_bytes(b"\xff")
        with self.assertRaisesRegex(IntegrationError, "UTF-8"):
            self.filesystem.get_note(path="Knowledge/Bad.md")
        with self.assertRaisesRegex(IntegrationError, "NUL"):
            self.filesystem.publish_note("Knowledge/Published/Zero.md", "bad\0value")

    def test_publish_is_idempotent_and_never_overwrites(self) -> None:
        path = "Knowledge/Published/New.md"
        first = self.filesystem.publish_note(path, "# New\n")
        second = self.filesystem.publish_note(path, "# New\n")
        self.assertEqual(first["state"], "created")
        self.assertEqual(second["state"], "already_present")
        with self.assertRaisesRegex(IntegrationError, "different content"):
            self.filesystem.publish_note(path, "# Different\n")
        self.assertEqual((self.vault / path).read_text(encoding="utf-8"), "# New\n")

    def test_publish_creates_only_children_below_existing_write_root(self) -> None:
        path = "Knowledge/Published/Nested/Note.md"
        result = self.filesystem.publish_note(path, "body")
        self.assertEqual(result["state"], "created")
        self.assertTrue((self.vault / path).is_file())
        with self.assertRaisesRegex(IntegrationError, "write roots"):
            self.filesystem.publish_note("Knowledge/Unsafe.md", "body")

    def test_update_requires_current_revision_and_is_idempotent(self) -> None:
        path = "Knowledge/Published/Update.md"
        created = self.filesystem.publish_note(path, "one")
        old_revision = created["note"]["revision"]
        updated = self.filesystem.update_note("two", old_revision, path=path)
        self.assertEqual(updated["state"], "updated")
        retried = self.filesystem.update_note("two", old_revision, path=path)
        self.assertEqual(retried["state"], "already_current")
        with self.assertRaisesRegex(IntegrationError, "changed"):
            self.filesystem.update_note("three", old_revision, path=path)
        self.assertEqual((self.vault / path).read_text(encoding="utf-8"), "two")

    def test_write_disabled_fails_before_mutation(self) -> None:
        disabled = VaultFilesystem(
            ObsidianConfig(vault_path=str(self.vault), read_roots=("Knowledge",))
        )
        with self.assertRaisesRegex(IntegrationError, "disabled"):
            disabled.publish_note("Knowledge/Published/No.md", "no")
        self.assertFalse((self.vault / "Knowledge" / "Published" / "No.md").exists())


if __name__ == "__main__":
    unittest.main()
