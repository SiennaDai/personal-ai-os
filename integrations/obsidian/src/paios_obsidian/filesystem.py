"""Confined filesystem data plane for one Obsidian Vault."""

from __future__ import annotations

import errno
import hashlib
import os
import re
import secrets
import stat
import unicodedata
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from urllib.parse import quote, unquote_to_bytes

from .config import ObsidianConfig
from .errors import IntegrationError


_DRIVE_PATTERN = re.compile(r"^[A-Za-z]:")
_REVISION_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
_WINDOWS_RESERVED = {
    "con",
    "prn",
    "aux",
    "nul",
    *(f"com{number}" for number in range(1, 10)),
    *(f"lpt{number}" for number in range(1, 10)),
}
_PROTECTED_COMPONENTS = {".obsidian", ".trash", ".git"}
_REF_PREFIX = "obsidian:{alias}:note:"
_EXCERPT_CHARS = 500


class VaultFilesystem:
    """Exact note I/O with path confinement and optimistic revisions."""

    def __init__(self, config: ObsidianConfig) -> None:
        self.config = config

    def status(self) -> dict[str, object]:
        try:
            self._vault_root()
            count, truncated = self.count_notes()
            read_ready = True
            error_code = None
        except IntegrationError as exc:
            count = 0
            truncated = False
            read_ready = False
            error_code = exc.code
        write_ready = False
        if read_ready and self.config.write_enabled:
            try:
                for root in self.config.allowed_write_roots:
                    path = self._resolve_existing(root, require_directory=True)
                    if not os.access(path, os.W_OK):
                        raise IntegrationError(
                            "WRITE_SCOPE_DENIED",
                            "A configured Obsidian write root is not writable",
                        )
                write_ready = True
            except IntegrationError:
                write_ready = False
        return {
            "ready": read_ready,
            "error_code": error_code,
            "note_count": count,
            "count_truncated": truncated,
            "write_enabled": self.config.write_enabled,
            "write_ready": write_ready,
            "read_root_count": len(self.config.read_roots),
            "write_root_count": len(self.config.allowed_write_roots),
        }

    def count_notes(self) -> tuple[int, bool]:
        seen: set[str] = set()
        truncated = False
        for root in self.config.read_roots:
            remaining = self.config.max_search_files - len(seen)
            if remaining <= 0:
                return len(seen), True
            paths, root_truncated = self._enumerate_notes(root, remaining)
            seen.update(path.casefold() for path in paths)
            truncated = truncated or root_truncated
            if truncated:
                break
        return len(seen), truncated

    def list_notes(
        self,
        *,
        folder: str | None = None,
        start: int = 0,
        limit: int | None = None,
    ) -> dict[str, object]:
        selected_folder = folder or self.config.read_roots[0]
        effective_limit = min(limit or self.config.max_page_size, self.config.max_page_size)
        paths, truncated_scan = self._enumerate_notes(
            selected_folder,
            self.config.max_search_files,
        )
        if truncated_scan and start >= len(paths):
            raise IntegrationError(
                "LIMIT_EXCEEDED",
                "The requested page is beyond the bounded note enumeration",
            )
        selected = paths[start : start + effective_limit]
        notes = [self.note_summary(path) for path in selected]
        has_more = start + len(selected) < len(paths) or truncated_scan
        return {
            "notes": notes,
            "page": {
                "start": start,
                "limit": effective_limit,
                "returned": len(notes),
                "has_more": has_more,
                "next_start": start + len(notes) if has_more and notes else None,
            },
            "truncated": truncated_scan,
            "retrieved_at": _now(),
        }

    def search_literal(
        self,
        query: str,
        *,
        folder: str | None = None,
        case_sensitive: bool = False,
        include_excerpt: bool = False,
        start: int = 0,
        limit: int | None = None,
    ) -> dict[str, object]:
        if not query or len(query) > 1_000 or "\0" in query:
            raise IntegrationError(
                "INVALID_ARGUMENT",
                "query must contain between 1 and 1000 non-NUL characters",
            )
        selected_folder = folder or self.config.read_roots[0]
        effective_limit = min(limit or self.config.max_page_size, self.config.max_page_size)
        paths, enumeration_truncated = self._enumerate_notes(
            selected_folder,
            self.config.max_search_files,
        )
        scanned_bytes = 0
        scanned_files = 0
        skipped_files = 0
        budget_truncated = False
        matches: list[dict[str, object]] = []
        needle = query if case_sensitive else query.lower()
        for path in paths:
            try:
                data, snapshot = self._read_snapshot(path)
            except IntegrationError as exc:
                if exc.code in {"LIMIT_EXCEEDED", "BACKEND_UNAVAILABLE"}:
                    skipped_files += 1
                    continue
                raise
            if scanned_bytes + len(data) > self.config.max_search_bytes:
                budget_truncated = True
                break
            scanned_bytes += len(data)
            scanned_files += 1
            try:
                text = self._decode_note(data)
            except IntegrationError as exc:
                if exc.code == "ENCODING_ERROR":
                    skipped_files += 1
                    continue
                raise
            haystack = text if case_sensitive else text.lower()
            index = haystack.find(needle)
            if index < 0:
                continue
            match: dict[str, object] = {"note": self._summary(path, data, snapshot)}
            if include_excerpt:
                excerpt_start = max(0, index - _EXCERPT_CHARS // 2)
                excerpt_end = min(len(text), excerpt_start + _EXCERPT_CHARS)
                match.update(
                    {
                        "excerpt": text[excerpt_start:excerpt_end],
                        "excerpt_start": excerpt_start,
                        "excerpt_truncated": excerpt_start > 0 or excerpt_end < len(text),
                    }
                )
            matches.append(match)
        selected = matches[start : start + effective_limit]
        truncated = enumeration_truncated or budget_truncated
        has_more = start + len(selected) < len(matches) or truncated
        return {
            "mode": "literal",
            "query": query,
            "matches": selected,
            "page": {
                "start": start,
                "limit": effective_limit,
                "returned": len(selected),
                "has_more": has_more,
                "next_start": start + len(selected) if has_more and selected else None,
            },
            "truncated": truncated,
            "scanned_files": scanned_files,
            "scanned_bytes": scanned_bytes,
            "skipped_files": skipped_files,
            "retrieved_at": _now(),
        }

    def get_note(
        self,
        *,
        ref: str | None = None,
        path: str | None = None,
        offset: int = 0,
        max_chars: int | None = None,
    ) -> dict[str, object]:
        relative = self.resolve_identity(ref=ref, path=path)
        data, snapshot = self._read_snapshot(relative)
        text = self._decode_note(data)
        effective_max = min(max_chars or self.config.max_read_chars, self.config.max_read_chars)
        content = text[offset : offset + effective_max]
        next_offset = offset + len(content) if offset + len(content) < len(text) else None
        return {
            "note": self._summary(relative, data, snapshot),
            "content": content,
            "content_page": {
                "offset": offset,
                "returned_chars": len(content),
                "total_chars": len(text),
                "truncated": next_offset is not None,
                "next_offset": next_offset,
            },
            "provenance": {"content_backend": "vault_filesystem"},
            "retrieved_at": _now(),
        }

    def note_summary(self, path: str) -> dict[str, object]:
        relative = normalize_note_path(path)
        self._assert_read_scope(relative)
        data, snapshot = self._read_snapshot(relative)
        self._decode_note(data)
        return self._summary(relative, data, snapshot)

    def publish_note(self, path: str, content: str) -> dict[str, object]:
        self.config.validate_write_ready()
        relative = normalize_note_path(path)
        write_root = self._assert_write_scope(relative)
        self._resolve_existing(write_root, require_directory=True)
        data = self._encode_note(content)
        target = self._prepare_write_target(relative)
        if target.exists():
            existing, snapshot = self._read_snapshot(relative)
            if existing == data:
                return {
                    "state": "already_present",
                    "note": self._summary(relative, existing, snapshot),
                    "semantic_index": "pending_or_unknown",
                }
            raise IntegrationError(
                "ALREADY_EXISTS",
                "The Obsidian note already exists with different content",
            )

        created = self._atomic_create(target, data)
        if not created:
            existing, snapshot = self._read_snapshot(relative)
            if existing == data:
                state = "already_present"
            else:
                raise IntegrationError(
                    "ALREADY_EXISTS",
                    "The Obsidian note was created concurrently with different content",
                )
        else:
            state = "created"
        final_data, final_snapshot = self._read_snapshot(relative)
        if final_data != data:
            raise IntegrationError(
                "WRITE_FAILED",
                "The created Obsidian note does not match the requested content",
            )
        return {
            "state": state,
            "note": self._summary(relative, final_data, final_snapshot),
            "semantic_index": "pending_or_unknown",
        }

    def update_note(
        self,
        content: str,
        expected_revision: str,
        *,
        ref: str | None = None,
        path: str | None = None,
    ) -> dict[str, object]:
        self.config.validate_write_ready()
        if not _REVISION_PATTERN.fullmatch(expected_revision):
            raise IntegrationError(
                "INVALID_ARGUMENT",
                "expected_revision must be a complete lowercase sha256 revision",
            )
        relative = self.resolve_identity(ref=ref, path=path)
        self._assert_write_scope(relative)
        requested = self._encode_note(content)
        current, snapshot = self._read_snapshot(relative)
        current_revision = _revision(current)
        if current == requested:
            return {
                "state": "already_current",
                "note": self._summary(relative, current, snapshot),
                "previous_revision": current_revision,
                "semantic_index": "pending_or_unknown",
            }
        if current_revision != expected_revision:
            raise IntegrationError(
                "REVISION_CONFLICT",
                "The Obsidian note changed after it was read",
            )

        target = self._resolve_existing(relative, require_directory=False)
        replacement = self._write_temporary(target.parent, requested, target.stat().st_mode)
        try:
            latest, _ = self._read_snapshot(relative)
            if _revision(latest) != expected_revision:
                raise IntegrationError(
                    "REVISION_CONFLICT",
                    "The Obsidian note changed while the update was prepared",
                )
            try:
                os.replace(replacement, target)
                replacement = None
                _fsync_directory(target.parent)
            except OSError as exc:
                raise IntegrationError(
                    "WRITE_FAILED",
                    "The Obsidian note could not be replaced atomically",
                ) from exc
        finally:
            if replacement is not None:
                try:
                    replacement.unlink()
                except OSError:
                    pass
        final_data, final_snapshot = self._read_snapshot(relative)
        if final_data != requested:
            raise IntegrationError(
                "WRITE_FAILED",
                "The updated Obsidian note does not match the requested content",
            )
        return {
            "state": "updated",
            "note": self._summary(relative, final_data, final_snapshot),
            "previous_revision": current_revision,
            "semantic_index": "pending_or_unknown",
        }

    def resolve_identity(self, *, ref: str | None, path: str | None) -> str:
        if bool(ref) == bool(path):
            raise IntegrationError(
                "INVALID_ARGUMENT",
                "Provide exactly one of ref or path",
            )
        if path is not None:
            relative = normalize_note_path(path)
        else:
            assert ref is not None
            prefix = _REF_PREFIX.format(alias=self.config.vault_alias)
            if not ref.startswith(prefix):
                raise IntegrationError(
                    "INVALID_ARGUMENT",
                    "The Obsidian ref does not belong to the configured Vault alias",
                )
            encoded = ref[len(prefix) :]
            try:
                decoded = unquote_to_bytes(encoded).decode("utf-8")
            except UnicodeDecodeError as exc:
                raise IntegrationError("INVALID_ARGUMENT", "The Obsidian ref is invalid") from exc
            if quote(decoded, safe="/-._~") != encoded:
                raise IntegrationError("INVALID_ARGUMENT", "The Obsidian ref is not canonical")
            relative = normalize_note_path(decoded)
        self._assert_read_scope(relative)
        return relative

    def is_read_path(self, path: str) -> bool:
        try:
            relative = normalize_note_path(path)
            self._assert_read_scope(relative)
            return True
        except IntegrationError:
            return False

    def validate_folder(self, folder: str | None) -> str:
        normalized = normalize_folder_path(folder or self.config.read_roots[0])
        if not any(_scope_contains(root, normalized) for root in self.config.read_roots):
            raise IntegrationError(
                "PATH_OUTSIDE_SCOPE",
                "The requested folder is outside the configured read roots",
            )
        self._resolve_existing(normalized, require_directory=True)
        return normalized

    def _summary(self, relative: str, data: bytes, snapshot: os.stat_result) -> dict[str, object]:
        encoded = quote(relative, safe="/-._~")
        return {
            "id": f"obsidian:{self.config.vault_alias}:note:{encoded}",
            "system": "obsidian",
            "kind": "note",
            "vault": {"alias": self.config.vault_alias},
            "path": relative,
            "revision": _revision(data),
            "size_bytes": len(data),
            "modified_ns": snapshot.st_mtime_ns,
        }

    def _vault_root(self) -> Path:
        root = self.config.vault_root
        try:
            metadata = root.lstat()
        except OSError as exc:
            raise IntegrationError(
                "VAULT_UNAVAILABLE",
                "The configured Obsidian Vault is unavailable",
                retryable=True,
            ) from exc
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
            raise IntegrationError(
                "VAULT_UNAVAILABLE",
                "The configured Obsidian Vault must be a non-symlink directory",
            )
        try:
            return root.resolve(strict=True)
        except OSError as exc:
            raise IntegrationError(
                "VAULT_UNAVAILABLE",
                "The configured Obsidian Vault cannot be resolved",
                retryable=True,
            ) from exc

    def _assert_read_scope(self, relative: str) -> None:
        if not any(_scope_contains(root, relative) for root in self.config.read_roots):
            raise IntegrationError(
                "PATH_OUTSIDE_SCOPE",
                "The Obsidian note is outside the configured read roots",
            )

    def _assert_write_scope(self, relative: str) -> str:
        matches = [
            root
            for root in self.config.allowed_write_roots
            if _scope_contains(root, relative)
        ]
        if not matches:
            raise IntegrationError(
                "WRITE_SCOPE_DENIED",
                "The Obsidian note is outside the configured write roots",
            )
        return max(matches, key=len)

    def _resolve_existing(self, relative: str, *, require_directory: bool) -> Path:
        normalized = normalize_folder_path(relative) if require_directory else normalize_note_path(relative)
        root = self._vault_root()
        if normalized == ".":
            return root
        current = root
        for component in PurePosixPath(normalized).parts:
            match = self._exact_child(current, component, allow_missing=False)
            assert match is not None
            current = match
            metadata = current.lstat()
            if stat.S_ISLNK(metadata.st_mode):
                raise IntegrationError("SYMLINK_DENIED", "Symlinked Vault paths are denied")
            self._assert_contained(current)
        metadata = current.lstat()
        if require_directory and not stat.S_ISDIR(metadata.st_mode):
            raise IntegrationError("NOT_FOUND", "The requested Obsidian folder was not found")
        if not require_directory and not stat.S_ISREG(metadata.st_mode):
            raise IntegrationError("NOT_FOUND", "The requested Obsidian note was not found")
        return current

    def _prepare_write_target(self, relative: str) -> Path:
        root = self._vault_root()
        parts = PurePosixPath(relative).parts
        current = root
        for component in parts[:-1]:
            match = self._exact_child(current, component, allow_missing=True)
            if match is None:
                candidate = current / component
                try:
                    candidate.mkdir(mode=0o700)
                except FileExistsError:
                    match = self._exact_child(current, component, allow_missing=False)
                except OSError as exc:
                    raise IntegrationError(
                        "WRITE_FAILED",
                        "An Obsidian note parent directory could not be created",
                    ) from exc
                else:
                    match = candidate
            metadata = match.lstat()
            if stat.S_ISLNK(metadata.st_mode):
                raise IntegrationError("SYMLINK_DENIED", "Symlinked Vault paths are denied")
            if not stat.S_ISDIR(metadata.st_mode):
                raise IntegrationError("INVALID_PATH", "A note parent path is not a directory")
            self._assert_contained(match)
            current = match
        existing = self._exact_child(current, parts[-1], allow_missing=True)
        if existing is not None:
            metadata = existing.lstat()
            if stat.S_ISLNK(metadata.st_mode):
                raise IntegrationError("SYMLINK_DENIED", "Symlinked Vault paths are denied")
            if not stat.S_ISREG(metadata.st_mode):
                raise IntegrationError("INVALID_PATH", "The note target is not a regular file")
            return existing
        target = current / parts[-1]
        self._assert_contained(target, strict=False)
        return target

    def _exact_child(self, parent: Path, name: str, *, allow_missing: bool) -> Path | None:
        try:
            matches = [entry for entry in parent.iterdir() if entry.name.casefold() == name.casefold()]
        except OSError as exc:
            raise IntegrationError(
                "BACKEND_UNAVAILABLE",
                "A Vault directory could not be inspected",
                retryable=True,
            ) from exc
        if len(matches) > 1:
            raise IntegrationError("CASE_COLLISION", "A Vault path has a case-fold collision")
        if not matches:
            if allow_missing:
                return None
            raise IntegrationError("NOT_FOUND", "The requested Obsidian path was not found")
        match = matches[0]
        if match.name != name:
            raise IntegrationError(
                "CASE_COLLISION",
                "The requested path spelling does not exactly match the Vault path",
            )
        return match

    def _read_snapshot(self, relative: str) -> tuple[bytes, os.stat_result]:
        self._assert_read_scope(relative)
        target = self._resolve_existing(relative, require_directory=False)
        flags = os.O_RDONLY
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            descriptor = os.open(target, flags)
        except OSError as exc:
            code = "SYMLINK_DENIED" if exc.errno == errno.ELOOP else "BACKEND_UNAVAILABLE"
            raise IntegrationError(code, "The Obsidian note could not be opened", retryable=code == "BACKEND_UNAVAILABLE") from exc
        try:
            before = os.fstat(descriptor)
            if not stat.S_ISREG(before.st_mode):
                raise IntegrationError("INVALID_PATH", "The requested note is not a regular file")
            if before.st_size > self.config.max_note_bytes:
                raise IntegrationError("LIMIT_EXCEEDED", "The Obsidian note exceeds max_note_bytes")
            chunks: list[bytes] = []
            total = 0
            while True:
                chunk = os.read(descriptor, min(65_536, self.config.max_note_bytes + 1 - total))
                if not chunk:
                    break
                chunks.append(chunk)
                total += len(chunk)
                if total > self.config.max_note_bytes:
                    raise IntegrationError("LIMIT_EXCEEDED", "The Obsidian note exceeds max_note_bytes")
            after = os.fstat(descriptor)
        finally:
            os.close(descriptor)
        data = b"".join(chunks)
        try:
            current = target.lstat()
        except OSError as exc:
            raise IntegrationError(
                "BACKEND_UNAVAILABLE",
                "The Obsidian note changed while it was read",
                retryable=True,
            ) from exc
        if _fingerprint(before) != _fingerprint(after) or _fingerprint(after) != _fingerprint(current):
            raise IntegrationError(
                "BACKEND_UNAVAILABLE",
                "The Obsidian note changed while it was read",
                retryable=True,
            )
        if len(data) != after.st_size:
            raise IntegrationError(
                "BACKEND_UNAVAILABLE",
                "The Obsidian note changed while it was read",
                retryable=True,
            )
        self._assert_contained(target)
        return data, after

    def _enumerate_notes(self, folder: str, cap: int) -> tuple[list[str], bool]:
        normalized = normalize_folder_path(folder)
        if not any(_scope_contains(root, normalized) for root in self.config.read_roots):
            raise IntegrationError(
                "PATH_OUTSIDE_SCOPE",
                "The requested folder is outside the configured read roots",
            )
        base = self._resolve_existing(normalized, require_directory=True)
        root = self._vault_root()
        results: list[str] = []
        truncated = False
        for current_text, directories, files in os.walk(base, topdown=True, followlinks=False):
            current = Path(current_text)
            self._assert_contained(current)
            names = directories + files
            folded: dict[str, int] = {}
            for name in names:
                key = name.casefold()
                folded[key] = folded.get(key, 0) + 1
            if any(count > 1 for count in folded.values()):
                raise IntegrationError("CASE_COLLISION", "A Vault directory has a case-fold collision")
            kept_directories: list[str] = []
            for name in sorted(directories, key=lambda item: (item.casefold(), item)):
                if _protected_name(name):
                    continue
                candidate = current / name
                try:
                    metadata = candidate.lstat()
                except OSError:
                    continue
                if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
                    continue
                kept_directories.append(name)
            directories[:] = kept_directories
            for name in sorted(files, key=lambda item: (item.casefold(), item)):
                if _protected_name(name) or not name.casefold().endswith(".md"):
                    continue
                candidate = current / name
                try:
                    metadata = candidate.lstat()
                except OSError:
                    continue
                if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
                    continue
                relative = candidate.relative_to(root).as_posix()
                normalize_note_path(relative)
                results.append(relative)
                if len(results) > cap:
                    truncated = True
                    break
            if truncated:
                break
        results.sort(key=lambda item: (item.casefold(), item))
        return results[:cap], truncated

    def _encode_note(self, content: str) -> bytes:
        if not isinstance(content, str) or "\0" in content:
            raise IntegrationError("ENCODING_ERROR", "Obsidian note content must be NUL-free text")
        try:
            data = content.encode("utf-8", errors="strict")
        except UnicodeEncodeError as exc:
            raise IntegrationError("ENCODING_ERROR", "Obsidian note content is not valid UTF-8 text") from exc
        if len(data) > self.config.max_note_bytes:
            raise IntegrationError("LIMIT_EXCEEDED", "Obsidian note content exceeds max_note_bytes")
        return data

    @staticmethod
    def _decode_note(data: bytes) -> str:
        try:
            text = data.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise IntegrationError("ENCODING_ERROR", "The Obsidian note is not valid UTF-8") from exc
        if "\0" in text:
            raise IntegrationError("ENCODING_ERROR", "The Obsidian note contains a NUL byte")
        return text

    def _atomic_create(self, target: Path, data: bytes) -> bool:
        temporary = self._write_temporary(target.parent, data, 0o600)
        try:
            try:
                os.link(temporary, target)
            except FileExistsError:
                return False
            except OSError as exc:
                raise IntegrationError(
                    "WRITE_FAILED",
                    "The platform could not install the Obsidian note without overwrite",
                ) from exc
            _fsync_directory(target.parent)
            return True
        finally:
            try:
                temporary.unlink()
            except OSError:
                pass

    @staticmethod
    def _write_temporary(parent: Path, data: bytes, mode: int) -> Path:
        target = parent / f".paios-{secrets.token_hex(16)}.tmp"
        descriptor = -1
        try:
            descriptor = os.open(
                target,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                stat.S_IMODE(mode),
            )
            view = memoryview(data)
            while view:
                written = os.write(descriptor, view)
                if written <= 0:
                    raise OSError("The temporary note write made no progress")
                view = view[written:]
            os.fsync(descriptor)
            return target
        except OSError as exc:
            try:
                target.unlink()
            except OSError:
                pass
            raise IntegrationError("WRITE_FAILED", "A temporary Obsidian note could not be written") from exc
        finally:
            if descriptor >= 0:
                os.close(descriptor)

    def _assert_contained(self, path: Path, *, strict: bool = True) -> None:
        root = self._vault_root()
        try:
            resolved = path.resolve(strict=strict)
            if os.path.commonpath((str(root), str(resolved))) != str(root):
                raise ValueError
        except (OSError, ValueError) as exc:
            raise IntegrationError("SYMLINK_DENIED", "A Vault path escapes the configured root") from exc


def normalize_note_path(value: str) -> str:
    normalized = _normalize_relative(value, allow_root=False)
    if not normalized.casefold().endswith(".md"):
        raise IntegrationError("INVALID_PATH", "Obsidian note paths must end in .md")
    return normalized


def normalize_folder_path(value: str) -> str:
    return _normalize_relative(value, allow_root=True)


def _normalize_relative(value: str, *, allow_root: bool) -> str:
    if not isinstance(value, str) or not value:
        raise IntegrationError("INVALID_PATH", "Vault-relative paths must be non-empty strings")
    if value == "." and allow_root:
        return value
    if value == "." or "\\" in value or value.startswith("/") or value.startswith("//") or _DRIVE_PATTERN.match(value):
        raise IntegrationError("INVALID_PATH", "Vault-relative paths must use normalized '/' separators")
    path = PurePosixPath(value)
    if str(path) != value or any(part in {"", ".", ".."} for part in path.parts):
        raise IntegrationError("INVALID_PATH", "Vault-relative paths cannot traverse or contain empty components")
    for component in path.parts:
        if unicodedata.normalize("NFC", component) != component:
            raise IntegrationError("INVALID_PATH", "Vault path components must use NFC Unicode")
        if _protected_name(component):
            raise IntegrationError("PROTECTED_PATH", "Hidden and protected Vault paths are denied")
        if component[-1:] in {".", " "}:
            raise IntegrationError("INVALID_PATH", "Vault path components cannot end in a dot or space")
        if any(ord(character) < 32 or character in '<>:"|?*' for character in component):
            raise IntegrationError("INVALID_PATH", "A Vault path contains forbidden characters")
        if component.split(".", 1)[0].casefold() in _WINDOWS_RESERVED:
            raise IntegrationError("INVALID_PATH", "A Vault path uses a Windows-reserved name")
    return value


def _protected_name(name: str) -> bool:
    return name.startswith(".") or name.casefold() in _PROTECTED_COMPONENTS


def _scope_contains(root: str, candidate: str) -> bool:
    return root == "." or candidate == root or candidate.startswith(root + "/")


def _revision(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _fingerprint(metadata: os.stat_result) -> tuple[int, int, int, int]:
    return metadata.st_dev, metadata.st_ino, metadata.st_size, metadata.st_mtime_ns


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _fsync_directory(directory: Path) -> None:
    descriptor = -1
    try:
        descriptor = os.open(directory, os.O_RDONLY)
        os.fsync(descriptor)
    except OSError as exc:
        if exc.errno not in {errno.EINVAL, errno.ENOTSUP, errno.EBADF, errno.EACCES}:
            raise IntegrationError("WRITE_FAILED", "The Vault directory could not be flushed") from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)
