"""Configuration loading and validation for the Obsidian Integration."""

from __future__ import annotations

import os
import re
import stat
import tempfile
import tomllib
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from .errors import IntegrationError


DEFAULT_CONFIG_PATH = Path("~/.config/personal-ai-os/integrations.toml").expanduser()
ALIAS_PATTERN = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")
_DRIVE_PATTERN = re.compile(r"^[A-Za-z]:")
_WINDOWS_RESERVED = {
    "con",
    "prn",
    "aux",
    "nul",
    *(f"com{number}" for number in range(1, 10)),
    *(f"lpt{number}" for number in range(1, 10)),
}
_PROTECTED_COMPONENTS = {".obsidian", ".trash", ".git"}

_ALLOWED_KEYS = {
    "vault_alias",
    "vault_path",
    "read_roots",
    "write_enabled",
    "allowed_write_roots",
    "cli_enabled",
    "cli_command",
    "cli_vault_selector",
    "cli_timeout_seconds",
    "max_page_size",
    "max_note_bytes",
    "max_read_chars",
    "max_search_files",
    "max_search_bytes",
    "max_link_results",
    "max_cli_response_bytes",
}


@dataclass(frozen=True)
class ObsidianConfig:
    """Validated non-secret settings for one Obsidian Vault."""

    vault_alias: str = "knowledge"
    vault_path: str = "/path/to/Obsidian/Vault"
    read_roots: tuple[str, ...] = (".",)
    write_enabled: bool = False
    allowed_write_roots: tuple[str, ...] = ()
    cli_enabled: bool = False
    cli_command: str = ""
    cli_vault_selector: str = ""
    cli_timeout_seconds: float = 30.0
    max_page_size: int = 50
    max_note_bytes: int = 2_000_000
    max_read_chars: int = 50_000
    max_search_files: int = 10_000
    max_search_bytes: int = 64_000_000
    max_link_results: int = 200
    max_cli_response_bytes: int = 8_000_000
    source_path: str = ""

    @property
    def vault_root(self) -> Path:
        return Path(self.vault_path)

    def public_summary(self) -> dict[str, object]:
        """Return configuration state without machine paths or native selectors."""

        return {
            "vault_alias": self.vault_alias,
            "vault_path_configured": bool(self.vault_path),
            "read_root_count": len(self.read_roots),
            "write_enabled": self.write_enabled,
            "allowed_write_root_count": len(self.allowed_write_roots),
            "cli_enabled": self.cli_enabled,
            "cli_command_configured": bool(self.cli_command),
            "cli_vault_selector_configured": bool(self.cli_vault_selector),
            "cli_timeout_seconds": self.cli_timeout_seconds,
            "max_page_size": self.max_page_size,
            "max_note_bytes": self.max_note_bytes,
            "max_read_chars": self.max_read_chars,
            "max_search_files": self.max_search_files,
            "max_search_bytes": self.max_search_bytes,
            "max_link_results": self.max_link_results,
        }

    def validate(self) -> None:
        if not ALIAS_PATTERN.fullmatch(self.vault_alias):
            _invalid("vault_alias must be a lowercase slug")
        if not self.vault_path or not Path(self.vault_path).is_absolute():
            _invalid("vault_path must be an absolute path visible to the MCP process")
        if Path(self.vault_path) == Path("/"):
            _invalid("vault_path must not be the filesystem root")

        if not self.read_roots:
            _invalid("read_roots must contain at least one Vault-relative root")
        normalized_reads = tuple(_validate_root(root, allow_vault_root=True) for root in self.read_roots)
        normalized_writes = tuple(
            _validate_root(root, allow_vault_root=False) for root in self.allowed_write_roots
        )
        _reject_casefold_duplicates(normalized_reads, "read_roots")
        _reject_casefold_duplicates(normalized_writes, "allowed_write_roots")
        for write_root in normalized_writes:
            if not any(_root_contains(read_root, write_root) for read_root in normalized_reads):
                _invalid("every allowed_write_root must be contained by a read_root")
        if self.write_enabled and not normalized_writes:
            _invalid("write_enabled requires at least one non-root allowed_write_root")

        if self.cli_enabled:
            if not self.cli_command or not Path(self.cli_command).is_absolute():
                _invalid("cli_enabled requires an absolute cli_command")
            basename = Path(self.cli_command).name.casefold()
            if basename not in {"obsidian", "obsidian.com", "obsidian.exe"}:
                _invalid("cli_command must name an official Obsidian executable")
            if not self.cli_vault_selector.strip():
                _invalid("cli_enabled requires cli_vault_selector")
            if any(character in self.cli_vault_selector for character in "\r\n\0"):
                _invalid("cli_vault_selector contains a forbidden control character")
        elif self.cli_command or self.cli_vault_selector:
            _invalid("cli_command and cli_vault_selector must be empty when cli_enabled is false")

        _bounded_number(self.cli_timeout_seconds, 1, 60, "cli_timeout_seconds")
        _bounded_integer(self.max_page_size, 1, 100, "max_page_size")
        _bounded_integer(self.max_note_bytes, 1_000, 10_000_000, "max_note_bytes")
        _bounded_integer(self.max_read_chars, 1_000, 200_000, "max_read_chars")
        _bounded_integer(self.max_search_files, 1, 50_000, "max_search_files")
        _bounded_integer(self.max_search_bytes, 1_000_000, 256_000_000, "max_search_bytes")
        _bounded_integer(self.max_link_results, 1, 1_000, "max_link_results")
        _bounded_integer(
            self.max_cli_response_bytes,
            1_000,
            16_000_000,
            "max_cli_response_bytes",
        )

    def validate_write_ready(self) -> None:
        self.validate()
        if not self.write_enabled:
            raise IntegrationError(
                "WRITE_DISABLED",
                "Obsidian writes are disabled in local configuration",
            )


def load_config(path: str | os.PathLike[str] | None = None) -> ObsidianConfig:
    """Load the Obsidian table from the unified Integration configuration."""

    resolved = Path(
        path or os.environ.get("PAIOS_INTEGRATIONS_CONFIG", DEFAULT_CONFIG_PATH)
    ).expanduser()
    if not resolved.is_file():
        raise IntegrationError(
            "CONFIG_NOT_FOUND",
            "The unified Integration configuration is unavailable",
        )
    try:
        with resolved.open("rb") as handle:
            document = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise IntegrationError(
            "CONFIG_INVALID",
            "The unified Integration configuration cannot be parsed",
        ) from exc

    section = document.get("obsidian")
    if not isinstance(section, dict):
        raise IntegrationError("CONFIG_INVALID", "Missing [obsidian] configuration table")
    unknown = sorted(set(section) - _ALLOWED_KEYS)
    if unknown:
        raise IntegrationError(
            "CONFIG_INVALID",
            "Unknown Obsidian configuration fields",
            details={"fields": unknown},
        )

    try:
        config = ObsidianConfig(
            vault_alias=_string(section, "vault_alias", "knowledge"),
            vault_path=_string(section, "vault_path", "/path/to/Obsidian/Vault"),
            read_roots=tuple(_string_list(section, "read_roots", ["."])),
            write_enabled=_boolean(section, "write_enabled", False),
            allowed_write_roots=tuple(
                _string_list(section, "allowed_write_roots", [])
            ),
            cli_enabled=_boolean(section, "cli_enabled", False),
            cli_command=_string(section, "cli_command", ""),
            cli_vault_selector=_string(section, "cli_vault_selector", ""),
            cli_timeout_seconds=_number(section, "cli_timeout_seconds", 30.0),
            max_page_size=_integer(section, "max_page_size", 50),
            max_note_bytes=_integer(section, "max_note_bytes", 2_000_000),
            max_read_chars=_integer(section, "max_read_chars", 50_000),
            max_search_files=_integer(section, "max_search_files", 10_000),
            max_search_bytes=_integer(section, "max_search_bytes", 64_000_000),
            max_link_results=_integer(section, "max_link_results", 200),
            max_cli_response_bytes=_integer(
                section,
                "max_cli_response_bytes",
                8_000_000,
            ),
            source_path=str(resolved),
        )
    except (TypeError, ValueError) as exc:
        raise IntegrationError("CONFIG_INVALID", str(exc)) from exc
    config.validate()
    return config


def append_runtime_config(path: str | os.PathLike[str], config: ObsidianConfig) -> None:
    """Append one default-off Obsidian section without rewriting existing tables."""

    config.validate()
    if config.write_enabled:
        raise IntegrationError(
            "CONFIG_INVALID",
            "Runtime bootstrap never enables Obsidian writes",
        )
    target = Path(path).expanduser()
    if not target.is_file() or target.is_symlink():
        raise IntegrationError(
            "CONFIG_INVALID",
            "Runtime configuration must be an existing regular file",
        )
    try:
        original = target.read_bytes()
        document = tomllib.loads(original.decode("utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        raise IntegrationError("CONFIG_INVALID", "Runtime configuration cannot be parsed") from exc
    if "obsidian" in document:
        raise IntegrationError(
            "RUNTIME_CONFIG_CONFLICT",
            "Runtime configuration already contains an Obsidian table",
        )

    rendered = _render_section(config).encode("utf-8")
    separator = (
        b""
        if not original or original.endswith(b"\n\n")
        else (b"\n" if original.endswith(b"\n") else b"\n\n")
    )
    mode = stat.S_IMODE(target.stat().st_mode)
    temporary_name = ""
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=target.parent,
            prefix=f".{target.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary_name = handle.name
            handle.write(original)
            handle.write(separator)
            handle.write(rendered)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary_name, mode)
        os.replace(temporary_name, target)
        temporary_name = ""
    except OSError as exc:
        raise IntegrationError(
            "WRITE_FAILED",
            "Runtime configuration migration failed",
        ) from exc
    finally:
        if temporary_name:
            try:
                os.unlink(temporary_name)
            except OSError:
                pass


def _render_section(config: ObsidianConfig) -> str:
    lines = [
        "[obsidian]",
        f'vault_alias = {_toml_string(config.vault_alias)}',
        f'vault_path = {_toml_string(config.vault_path)}',
        f"read_roots = {_toml_strings(config.read_roots)}",
        "write_enabled = false",
        "allowed_write_roots = []",
        f"cli_enabled = {'true' if config.cli_enabled else 'false'}",
        f'cli_command = {_toml_string(config.cli_command)}',
        f'cli_vault_selector = {_toml_string(config.cli_vault_selector)}',
        f"cli_timeout_seconds = {_toml_number(config.cli_timeout_seconds)}",
        f"max_page_size = {config.max_page_size}",
        f"max_note_bytes = {config.max_note_bytes}",
        f"max_read_chars = {config.max_read_chars}",
        f"max_search_files = {config.max_search_files}",
        f"max_search_bytes = {config.max_search_bytes}",
        f"max_link_results = {config.max_link_results}",
        f"max_cli_response_bytes = {config.max_cli_response_bytes}",
        "",
    ]
    return "\n".join(lines)


def _toml_string(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _toml_strings(values: tuple[str, ...]) -> str:
    return "[" + ", ".join(_toml_string(value) for value in values) + "]"


def _toml_number(value: float) -> str:
    return str(int(value)) if value.is_integer() else str(value)


def _validate_root(value: str, *, allow_vault_root: bool) -> str:
    if not isinstance(value, str) or not value:
        _invalid("Vault-relative roots must be non-empty strings")
    if value == ".":
        if allow_vault_root:
            return value
        _invalid("the Vault root cannot be an allowed_write_root")
    if "\\" in value or value.startswith("/") or value.startswith("//") or _DRIVE_PATTERN.match(value):
        _invalid("Vault-relative roots must use relative '/' paths")
    path = PurePosixPath(value)
    if str(path) != value or any(part in {"", ".", ".."} for part in path.parts):
        _invalid("Vault-relative roots must be normalized and cannot traverse")
    for component in path.parts:
        _validate_component(component)
    return value


def _validate_component(component: str) -> None:
    folded = component.casefold()
    stem = component.split(".", 1)[0].casefold()
    if component.startswith(".") or folded in _PROTECTED_COMPONENTS:
        _invalid("hidden and protected Vault paths are not configurable")
    if component[-1:] in {".", " "}:
        _invalid("Vault path components cannot end in a dot or space")
    if any(ord(character) < 32 or character in '<>:"|?*' for character in component):
        _invalid("Vault path components contain Windows-forbidden characters")
    if stem in _WINDOWS_RESERVED:
        _invalid("Vault path components cannot use Windows-reserved names")


def _root_contains(root: str, candidate: str) -> bool:
    return root == "." or candidate == root or candidate.startswith(root + "/")


def _reject_casefold_duplicates(values: tuple[str, ...], field: str) -> None:
    folded = [value.casefold() for value in values]
    if len(folded) != len(set(folded)):
        _invalid(f"{field} contains case-fold duplicate roots")


def _string(section: dict[str, object], key: str, default: str) -> str:
    value = section.get(key, default)
    if not isinstance(value, str):
        raise TypeError(f"{key} must be a string")
    return value


def _boolean(section: dict[str, object], key: str, default: bool) -> bool:
    value = section.get(key, default)
    if not isinstance(value, bool):
        raise TypeError(f"{key} must be a boolean")
    return value


def _integer(section: dict[str, object], key: str, default: int) -> int:
    value = section.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{key} must be an integer")
    return value


def _number(section: dict[str, object], key: str, default: float) -> float:
    value = section.get(key, default)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{key} must be a number")
    return float(value)


def _string_list(section: dict[str, object], key: str, default: list[str]) -> list[str]:
    value = section.get(key, default)
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise TypeError(f"{key} must be an array of strings")
    return value


def _bounded_integer(value: int, minimum: int, maximum: int, field: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        _invalid(f"{field} must be between {minimum} and {maximum}")


def _bounded_number(value: float, minimum: float, maximum: float, field: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not minimum <= value <= maximum:
        _invalid(f"{field} must be between {minimum} and {maximum}")


def _invalid(message: str) -> None:
    raise IntegrationError("CONFIG_INVALID", message)
