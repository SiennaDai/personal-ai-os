"""Stable Obsidian Integration service composed from filesystem and CLI adapters."""

from __future__ import annotations

from datetime import datetime, timezone

from .cli import ObsidianCli
from .config import ObsidianConfig
from .errors import IntegrationError
from .filesystem import VaultFilesystem, normalize_note_path


class ObsidianService:
    def __init__(
        self,
        config: ObsidianConfig,
        *,
        filesystem: VaultFilesystem | None = None,
        cli: ObsidianCli | None = None,
    ) -> None:
        self.config = config
        self.filesystem = filesystem or VaultFilesystem(config)
        self.cli = cli or ObsidianCli(config)

    def status(self) -> dict[str, object]:
        filesystem = self.filesystem.status()
        cli = self.cli.status()
        if not filesystem["ready"]:
            state = "unavailable"
        elif self.config.cli_enabled and not cli["ready"]:
            state = "degraded"
        elif self.config.write_enabled and not filesystem["write_ready"]:
            state = "degraded"
        else:
            state = "healthy"
        return {
            "state": state,
            "overall_ok": state == "healthy",
            "vault_alias": self.config.vault_alias,
            "configuration": self.config.public_summary(),
            "filesystem": filesystem,
            "cli": cli,
            "writes": {
                "enabled": self.config.write_enabled,
                "ready": filesystem["write_ready"],
                "root_count": len(self.config.allowed_write_roots),
            },
            "counts": {
                "markdown_notes": filesystem["note_count"],
                "truncated": filesystem["count_truncated"],
            },
        }

    def list_notes(
        self,
        *,
        folder: str | None = None,
        start: int = 0,
        limit: int | None = None,
    ) -> dict[str, object]:
        return self.filesystem.list_notes(folder=folder, start=start, limit=limit)

    def search_notes(
        self,
        query: str,
        mode: str,
        *,
        folder: str | None = None,
        case_sensitive: bool = False,
        include_excerpt: bool = False,
        start: int = 0,
        limit: int | None = None,
    ) -> dict[str, object]:
        if mode == "literal":
            return self.filesystem.search_literal(
                query,
                folder=folder,
                case_sensitive=case_sensitive,
                include_excerpt=include_excerpt,
                start=start,
                limit=limit,
            )
        if mode != "obsidian":
            raise IntegrationError("INVALID_ARGUMENT", "mode must be literal or obsidian")
        if case_sensitive or include_excerpt:
            raise IntegrationError(
                "INVALID_ARGUMENT",
                "case_sensitive and include_excerpt are available only in literal mode",
            )
        if not query or len(query) > 1_000:
            raise IntegrationError(
                "INVALID_ARGUMENT",
                "query must contain between 1 and 1000 characters",
            )
        normalized_folder = self.filesystem.validate_folder(folder)
        effective_limit = min(limit or self.config.max_page_size, self.config.max_page_size)
        native_limit = min(start + effective_limit + 1, self.config.max_search_files)
        paths = self.cli.search(
            query,
            folder=normalized_folder,
            case_sensitive=False,
            limit=native_limit,
        )
        normalized: list[str] = []
        seen: set[str] = set()
        for native_path in paths:
            try:
                path = normalize_note_path(native_path)
            except IntegrationError as exc:
                raise IntegrationError(
                    "BACKEND_PROTOCOL_ERROR",
                    "The official Obsidian CLI returned an invalid note path",
                ) from exc
            if not self.filesystem.is_read_path(path):
                raise IntegrationError(
                    "BACKEND_PROTOCOL_ERROR",
                    "The official Obsidian CLI returned a path outside the read scope",
                )
            folded = path.casefold()
            if folded in seen:
                continue
            seen.add(folded)
            normalized.append(path)
        selected_paths = normalized[start : start + effective_limit]
        matches = [{"note": self.filesystem.note_summary(path)} for path in selected_paths]
        truncated = len(normalized) > start + len(matches) or len(paths) >= native_limit
        return {
            "mode": "obsidian",
            "query": query,
            "matches": matches,
            "page": {
                "start": start,
                "limit": effective_limit,
                "returned": len(matches),
                "has_more": truncated,
                "next_start": start + len(matches) if truncated and matches else None,
            },
            "truncated": truncated,
            "retrieved_at": _now(),
        }

    def get_note(
        self,
        *,
        ref: str | None = None,
        path: str | None = None,
        offset: int = 0,
        max_chars: int | None = None,
        include_properties: bool = False,
    ) -> dict[str, object]:
        result = self.filesystem.get_note(
            ref=ref,
            path=path,
            offset=offset,
            max_chars=max_chars,
        )
        if include_properties:
            note_path = str(result["note"]["path"])
            result["properties"] = self.cli.properties(note_path)
            result["provenance"]["properties_backend"] = "official_cli"
        return result

    def get_links(
        self,
        *,
        ref: str | None = None,
        path: str | None = None,
        direction: str = "both",
        limit: int | None = None,
    ) -> dict[str, object]:
        if direction not in {"outgoing", "backlinks", "both"}:
            raise IntegrationError(
                "INVALID_ARGUMENT",
                "direction must be outgoing, backlinks, or both",
            )
        note_path = self.filesystem.resolve_identity(ref=ref, path=path)
        note = self.filesystem.note_summary(note_path)
        effective_limit = min(limit or self.config.max_link_results, self.config.max_link_results)
        outgoing: list[dict[str, object]] = []
        backlinks: list[dict[str, object]] = []
        truncated = False

        if direction in {"outgoing", "both"}:
            native_links = self.cli.links(note_path)
            unresolved = self.cli.unresolved(note_path)
            unresolved_counts = {
                str(record["path"]): record.get("count")
                for record in unresolved
                if isinstance(record.get("path"), str)
            }
            seen_targets: set[str] = set()
            for target in native_links:
                entry = self._outgoing_entry(target, unresolved_counts.get(target))
                key = str(entry["target"]).casefold()
                if key not in seen_targets:
                    outgoing.append(entry)
                    seen_targets.add(key)
            for target, count in unresolved_counts.items():
                if target.casefold() not in seen_targets:
                    entry = {"target": target, "resolved": False}
                    if isinstance(count, int):
                        entry["count"] = count
                    outgoing.append(entry)
            outgoing.sort(key=lambda item: str(item["target"]).casefold())
            if len(outgoing) > effective_limit:
                outgoing = outgoing[:effective_limit]
                truncated = True

        if direction in {"backlinks", "both"}:
            native_backlinks = self.cli.backlinks(note_path)
            for record in native_backlinks:
                native_path = record.get("path")
                if not isinstance(native_path, str):
                    raise IntegrationError(
                        "BACKEND_PROTOCOL_ERROR",
                        "The official Obsidian CLI returned an invalid backlink",
                    )
                try:
                    normalized = normalize_note_path(native_path)
                    summary = self.filesystem.note_summary(normalized)
                except IntegrationError as exc:
                    if exc.code in {"PATH_OUTSIDE_SCOPE", "NOT_FOUND", "INVALID_PATH"}:
                        continue
                    raise
                entry: dict[str, object] = {
                    "target": summary["id"],
                    "resolved": True,
                    "note": summary,
                }
                if isinstance(record.get("count"), int):
                    entry["count"] = record["count"]
                backlinks.append(entry)
            backlinks.sort(key=lambda item: str(item["target"]).casefold())
            if len(backlinks) > effective_limit:
                backlinks = backlinks[:effective_limit]
                truncated = True

        result: dict[str, object] = {
            "note": note,
            "truncated": truncated,
            "provenance": {"links_backend": "official_cli"},
            "retrieved_at": _now(),
        }
        if direction in {"outgoing", "both"}:
            result["outgoing"] = outgoing
        if direction in {"backlinks", "both"}:
            result["backlinks"] = backlinks
        return result

    def publish_note(self, path: str, content: str) -> dict[str, object]:
        return self.filesystem.publish_note(path, content)

    def update_note(
        self,
        content: str,
        expected_revision: str,
        *,
        ref: str | None = None,
        path: str | None = None,
    ) -> dict[str, object]:
        return self.filesystem.update_note(
            content,
            expected_revision,
            ref=ref,
            path=path,
        )

    def _outgoing_entry(self, target: str, count: object) -> dict[str, object]:
        candidate = _link_target_to_path(target)
        if candidate and self.filesystem.is_read_path(candidate):
            try:
                summary = self.filesystem.note_summary(candidate)
            except IntegrationError:
                summary = None
            if summary is not None:
                entry: dict[str, object] = {
                    "target": summary["id"],
                    "resolved": True,
                    "note": summary,
                }
                if isinstance(count, int):
                    entry["count"] = count
                return entry
        entry = {"target": target[:1_000], "resolved": False}
        if isinstance(count, int):
            entry["count"] = count
        return entry


def _link_target_to_path(value: str) -> str | None:
    target = value.strip()
    if target.startswith("[[") and target.endswith("]]"):
        target = target[2:-2]
    target = target.split("|", 1)[0].split("#", 1)[0]
    if not target:
        return None
    if not target.casefold().endswith(".md"):
        target += ".md"
    try:
        return normalize_note_path(target)
    except IntegrationError:
        return None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
