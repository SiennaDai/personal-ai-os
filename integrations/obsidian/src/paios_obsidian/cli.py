"""Narrow adapter for the official Obsidian command-line interface."""

from __future__ import annotations

import json
import os
import re
import stat
import subprocess
from pathlib import Path
from typing import Callable, Sequence

from .config import ObsidianConfig
from .errors import IntegrationError


_VERSION_PATTERN = re.compile(
    r"^(?P<app>\d+\.\d+\.\d+)(?:\s+\(installer\s+(?P<installer>\d+\.\d+\.\d+)\))?$"
)
_SUPPORTED_VERSION_PATTERN = re.compile(r"^1\.13\.\d+$")
_WINDOWS_PATH_PATTERN = re.compile(r"^(?P<drive>[A-Za-z]):[\\/](?P<rest>.*)$")
_ALLOWED_COMMANDS = {
    "version",
    "vault",
    "files",
    "search",
    "links",
    "backlinks",
    "properties",
    "unresolved",
}


Executor = Callable[[Sequence[str], float], subprocess.CompletedProcess[bytes]]


class ObsidianCli:
    """Invoke only contract-allowlisted official CLI read commands."""

    def __init__(self, config: ObsidianConfig, executor: Executor | None = None) -> None:
        self.config = config
        self._executor = executor or _execute
        self._ready_checked = False

    def status(self) -> dict[str, object]:
        if not self.config.cli_enabled:
            return {
                "enabled": False,
                "ready": False,
                "error_code": None,
                "version": None,
                "installer_version": None,
                "supported": False,
                "same_vault": False,
                "capabilities": [],
            }
        try:
            version = self.version()
            same_vault = self.same_vault()
            if not version["supported"]:
                error_code = "CLI_INCOMPATIBLE"
                ready = False
            elif not same_vault:
                error_code = "CONFIG_INVALID"
                ready = False
            else:
                error_code = None
                ready = True
                self._ready_checked = True
            return {
                "enabled": True,
                "ready": ready,
                "error_code": error_code,
                "version": version["version"],
                "installer_version": version["installer_version"],
                "supported": version["supported"],
                "same_vault": same_vault,
                "capabilities": ["obsidian_search", "properties", "links", "backlinks"]
                if ready
                else [],
            }
        except IntegrationError as exc:
            return {
                "enabled": True,
                "ready": False,
                "error_code": exc.code,
                "version": None,
                "installer_version": None,
                "supported": False,
                "same_vault": False,
                "capabilities": [],
            }

    def require_ready(self) -> None:
        if not self.config.cli_enabled:
            raise IntegrationError(
                "OPTIONAL_CAPABILITY_UNAVAILABLE",
                "The official Obsidian CLI semantic capability is disabled",
            )
        if self._ready_checked:
            return
        status = self.status()
        if not status["ready"]:
            code = str(status["error_code"] or "CLI_UNAVAILABLE")
            raise IntegrationError(
                code,
                "The official Obsidian CLI semantic capability is unavailable",
                retryable=code == "CLI_UNAVAILABLE",
            )

    def version(self) -> dict[str, object]:
        output = self._run("version")
        match = _VERSION_PATTERN.fullmatch(output.strip())
        if not match:
            raise IntegrationError(
                "BACKEND_PROTOCOL_ERROR",
                "The official Obsidian CLI returned an unrecognized version",
            )
        version = match.group("app")
        return {
            "version": version,
            "installer_version": match.group("installer"),
            "supported": bool(_SUPPORTED_VERSION_PATTERN.fullmatch(version)),
        }

    def same_vault(self) -> bool:
        output = self._run("vault", "info=path")
        try:
            configured = self.config.vault_root.resolve(strict=True)
            reported = _cli_path_to_local(output.strip()).resolve(strict=True)
        except OSError as exc:
            raise IntegrationError(
                "CONFIG_INVALID",
                "The configured CLI Vault cannot be matched to the filesystem Vault",
            ) from exc
        try:
            return os.path.samefile(configured, reported)
        except OSError:
            return str(configured).casefold() == str(reported).casefold()

    def search(
        self,
        query: str,
        *,
        folder: str,
        case_sensitive: bool,
        limit: int,
    ) -> list[str]:
        self.require_ready()
        if any(character in query for character in "\r\n\0"):
            raise IntegrationError("INVALID_ARGUMENT", "Obsidian CLI queries must be one line")
        arguments = [f"query={query}", f"limit={limit}", "format=json"]
        if folder != ".":
            arguments.append(f"path={folder}")
        if case_sensitive:
            arguments.append("case")
        output = self._run("search", *arguments)
        if output == "No matches found.":
            return []
        document = self._json(output)
        return _extract_paths(document)

    def properties(self, path: str) -> dict[str, object]:
        self.require_ready()
        output = self._run("properties", f"path={path}", "format=json")
        if output == "No frontmatter found.":
            return {}
        document = self._json(output)
        if isinstance(document, dict):
            values = document.get("properties", document)
            if isinstance(values, dict):
                return _validate_properties(values)
        if isinstance(document, list):
            result: dict[str, object] = {}
            for entry in document:
                if not isinstance(entry, dict) or not isinstance(entry.get("name"), str):
                    raise _protocol("property")
                result[entry["name"]] = _json_value(entry.get("value"))
            return result
        raise _protocol("property")

    def links(self, path: str) -> list[str]:
        self.require_ready()
        output = self._run("links", f"path={path}")
        if output == "No links found.":
            return []
        values: list[str] = []
        for line in output.splitlines():
            value = line.strip()
            if value.endswith(" (unresolved)"):
                value = value[: -len(" (unresolved)")]
            if value:
                values.append(value)
        return values

    def backlinks(self, path: str) -> list[dict[str, object]]:
        self.require_ready()
        output = self._run("backlinks", f"path={path}", "counts", "format=json")
        if output == "No backlinks found.":
            return []
        document = self._json(output)
        return _extract_records(document)

    def unresolved(self, path: str) -> list[dict[str, object]]:
        self.require_ready()
        output = self._run("unresolved", "counts", "verbose", "format=json")
        if output == "No unresolved links found.":
            return []
        document = self._json(output)
        return _unresolved_for_source(document, path)

    def _run(self, command: str, *arguments: str) -> str:
        if not self.config.cli_enabled:
            raise IntegrationError(
                "OPTIONAL_CAPABILITY_UNAVAILABLE",
                "The official Obsidian CLI semantic capability is disabled",
            )
        if command not in _ALLOWED_COMMANDS:
            raise IntegrationError(
                "UNSUPPORTED_CAPABILITY",
                "The requested native Obsidian CLI command is not allowlisted",
            )
        executable = Path(self.config.cli_command)
        try:
            metadata = executable.lstat()
        except OSError as exc:
            raise IntegrationError(
                "CLI_UNAVAILABLE",
                "The configured official Obsidian CLI is unavailable",
                retryable=True,
            ) from exc
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
            raise IntegrationError(
                "CLI_UNAVAILABLE",
                "The configured official Obsidian CLI must be a regular non-symlink file",
            )
        vector = [
            str(executable),
            f"vault={self.config.cli_vault_selector}",
            command,
            *arguments,
        ]
        try:
            completed = self._executor(vector, self.config.cli_timeout_seconds)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise IntegrationError(
                "CLI_UNAVAILABLE",
                "The official Obsidian CLI did not complete",
                retryable=True,
            ) from exc
        if len(completed.stdout) > self.config.max_cli_response_bytes or len(completed.stderr) > self.config.max_cli_response_bytes:
            raise IntegrationError(
                "LIMIT_EXCEEDED",
                "The official Obsidian CLI response exceeded the configured byte limit",
            )
        if completed.returncode != 0:
            raise IntegrationError(
                "CLI_UNAVAILABLE",
                "The official Obsidian CLI command failed",
                retryable=True,
            )
        try:
            return completed.stdout.decode("utf-8", errors="strict").strip()
        except UnicodeDecodeError as exc:
            raise IntegrationError(
                "BACKEND_PROTOCOL_ERROR",
                "The official Obsidian CLI response is not UTF-8",
            ) from exc

    @staticmethod
    def _json(output: str) -> object:
        try:
            return json.loads(output)
        except json.JSONDecodeError as exc:
            raise IntegrationError(
                "BACKEND_PROTOCOL_ERROR",
                "The official Obsidian CLI returned invalid JSON",
            ) from exc


def _execute(arguments: Sequence[str], timeout: float) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        list(arguments),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=timeout,
    )


def _extract_paths(document: object) -> list[str]:
    records = _extract_records(document)
    result: list[str] = []
    for record in records:
        value = record.get("path")
        if not isinstance(value, str):
            raise _protocol("search path")
        result.append(value)
    return result


def _extract_records(document: object) -> list[dict[str, object]]:
    if isinstance(document, dict):
        for key in ("results", "files", "matches", "backlinks"):
            if key in document:
                return _extract_records(document[key])
        records: list[dict[str, object]] = []
        for key, value in document.items():
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                records.append({"path": key, "count": int(value)})
            elif isinstance(value, dict):
                record = dict(value)
                record.setdefault("path", key)
                records.append(_normalize_record(record))
            else:
                raise _protocol("record")
        return records
    if not isinstance(document, list):
        raise _protocol("record list")
    records = []
    for entry in document:
        if isinstance(entry, str):
            records.append({"path": entry})
        elif isinstance(entry, dict):
            records.append(_normalize_record(entry))
        else:
            raise _protocol("record")
    return records


def _normalize_record(entry: dict[str, object]) -> dict[str, object]:
    path = next(
        (entry.get(key) for key in ("path", "file", "name", "target") if isinstance(entry.get(key), str)),
        None,
    )
    if not isinstance(path, str):
        raise _protocol("record path")
    record: dict[str, object] = {"path": path}
    count = entry.get("count", entry.get("mentions"))
    if isinstance(count, (int, float)) and not isinstance(count, bool):
        record["count"] = int(count)
    source = entry.get("source")
    if isinstance(source, str):
        record["source"] = source
    return record


def _unresolved_for_source(document: object, source_path: str) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    if isinstance(document, list):
        for entry in document:
            if not isinstance(entry, dict):
                raise _protocol("unresolved link")
            source = entry.get("source", entry.get("file"))
            sources = entry.get("sources", [])
            target = entry.get("target", entry.get("link", entry.get("name")))
            source_names = [
                item if isinstance(item, str) else item.get("path", item.get("file"))
                for item in sources
                if isinstance(item, (str, dict))
            ]
            if (source == source_path or source_path in source_names) and isinstance(target, str):
                result: dict[str, object] = {"path": target, "source": source_path}
                if isinstance(entry.get("count"), int):
                    result["count"] = entry["count"]
                results.append(result)
        return results
    if isinstance(document, dict):
        for target, value in document.items():
            if isinstance(value, dict):
                sources = value.get("sources", value.get("files", []))
                count = value.get("count")
            elif isinstance(value, list):
                sources = value
                count = None
            else:
                continue
            source_names = [
                entry if isinstance(entry, str) else entry.get("path", entry.get("file"))
                for entry in sources
                if isinstance(entry, (str, dict))
            ]
            if source_path in source_names:
                result = {"path": target, "source": source_path}
                if isinstance(count, int):
                    result["count"] = count
                results.append(result)
        return results
    raise _protocol("unresolved link list")


def _validate_properties(values: dict[object, object]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in values.items():
        if not isinstance(key, str):
            raise _protocol("property name")
        result[key] = _json_value(value)
    return result


def _json_value(value: object) -> object:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    raise _protocol("property value")


def _cli_path_to_local(value: str) -> Path:
    match = _WINDOWS_PATH_PATTERN.match(value)
    if match:
        rest = match.group("rest").replace("\\", "/")
        return Path(f"/mnt/{match.group('drive').lower()}/{rest}")
    return Path(value)


def _protocol(kind: str) -> IntegrationError:
    return IntegrationError(
        "BACKEND_PROTOCOL_ERROR",
        f"The official Obsidian CLI returned an invalid {kind} structure",
    )
