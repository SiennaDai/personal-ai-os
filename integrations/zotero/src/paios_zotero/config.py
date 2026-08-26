"""Configuration loading and validation for the Zotero Integration."""

from __future__ import annotations

import os
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping
from urllib.parse import urlsplit

from .errors import IntegrationError


DEFAULT_CONFIG_PATH = Path("~/.config/personal-ai-os/integrations.toml").expanduser()
ZOTERO_KEY_PATTERN = re.compile(r"^[23456789ABCDEFGHIJKLMNPQRSTUVWXYZ]{8}$")
ENV_NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
ALIAS_PATTERN = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")

_ALLOWED_KEYS = {
    "read_backend",
    "local_transport",
    "library_alias",
    "library_type",
    "local_library_id",
    "web_library_id",
    "local_api_url",
    "web_api_url",
    "api_key_env",
    "better_bibtex_enabled",
    "better_bibtex_url",
    "better_bibtex_library_id",
    "write_enabled",
    "write_scope",
    "allowed_write_collection_keys",
    "allowed_write_collection_names",
    "request_timeout_seconds",
    "local_authorization_timeout_seconds",
    "max_page_size",
    "max_fulltext_chars",
    "max_note_chars",
    "max_backend_response_bytes",
}


@dataclass(frozen=True)
class ZoteroConfig:
    """Validated, non-secret settings for one configured Zotero library."""

    read_backend: str = "local"
    local_transport: str = "auto"
    library_alias: str = "personal"
    library_type: str = "user"
    local_library_id: str = "0"
    web_library_id: str = ""
    local_api_url: str = "http://127.0.0.1:23119/api"
    web_api_url: str = "https://api.zotero.org"
    api_key_env: str = "ZOTERO_API_KEY"
    better_bibtex_enabled: bool = True
    better_bibtex_url: str = "http://127.0.0.1:23119/better-bibtex/json-rpc"
    better_bibtex_library_id: str = ""
    write_enabled: bool = False
    write_scope: str = "disabled"
    allowed_write_collection_keys: tuple[str, ...] = ()
    allowed_write_collection_names: tuple[str, ...] = ()
    request_timeout_seconds: float = 10.0
    local_authorization_timeout_seconds: float = 120.0
    max_page_size: int = 50
    max_fulltext_chars: int = 20_000
    max_note_chars: int = 50_000
    max_backend_response_bytes: int = 25_000_000
    source_path: str = ""

    @property
    def read_library_id(self) -> str:
        if self.read_backend == "local":
            return self.local_library_id
        return self.web_library_id

    @property
    def canonical_library_id(self) -> str:
        return self.web_library_id or self.local_library_id

    def api_key(self, environ: Mapping[str, str] | None = None) -> str:
        source = os.environ if environ is None else environ
        return source.get(self.api_key_env, "")

    def public_summary(self, environ: Mapping[str, str] | None = None) -> dict[str, object]:
        return {
            "source_path": self.source_path,
            "read_backend": self.read_backend,
            "local_transport": self.local_transport,
            "library_alias": self.library_alias,
            "library_type": self.library_type,
            "local_library_id": self.local_library_id,
            "web_library_id_configured": bool(self.web_library_id),
            "local_api_url": self.local_api_url,
            "web_api_url": self.web_api_url,
            "api_key_env": self.api_key_env,
            "api_key_available": bool(self.api_key(environ)),
            "better_bibtex_enabled": self.better_bibtex_enabled,
            "better_bibtex_url": self.better_bibtex_url,
            "write_enabled": self.write_enabled,
            "write_scope": self.write_scope,
            "allowed_write_collection_count": len(self.allowed_write_collection_keys),
            "allowed_write_collection_name_count": len(self.allowed_write_collection_names),
            "request_timeout_seconds": self.request_timeout_seconds,
            "local_authorization_timeout_seconds": self.local_authorization_timeout_seconds,
            "max_page_size": self.max_page_size,
            "max_fulltext_chars": self.max_fulltext_chars,
        }

    def validate(self) -> None:
        if self.read_backend not in {"local", "web"}:
            _invalid("read_backend must be 'local' or 'web'")
        if self.local_transport not in {"auto", "direct", "windows"}:
            _invalid("local_transport must be 'auto', 'direct', or 'windows'")
        if not ALIAS_PATTERN.fullmatch(self.library_alias):
            _invalid("library_alias must be a lowercase slug")
        if self.library_type not in {"user", "group"}:
            _invalid("library_type must be 'user' or 'group'")
        _validate_numeric_id(self.local_library_id, "local_library_id", allow_zero=True)
        if self.web_library_id:
            _validate_numeric_id(self.web_library_id, "web_library_id", allow_zero=False)
        if self.read_backend == "web" and not self.web_library_id:
            _invalid("web_library_id is required when read_backend is 'web'")

        _validate_loopback_url(self.local_api_url, "/api", "local_api_url")
        _validate_official_web_url(self.web_api_url)
        if not ENV_NAME_PATTERN.fullmatch(self.api_key_env):
            _invalid("api_key_env is not a valid environment variable name")

        if self.better_bibtex_enabled:
            _validate_loopback_url(
                self.better_bibtex_url,
                "/better-bibtex/json-rpc",
                "better_bibtex_url",
            )
        if self.better_bibtex_library_id and not self.better_bibtex_library_id.isdigit():
            _invalid("better_bibtex_library_id must contain digits only")

        if self.write_scope not in {"disabled", "collections", "library"}:
            _invalid("write_scope must be 'disabled', 'collections', or 'library'")
        for key in self.allowed_write_collection_keys:
            if not ZOTERO_KEY_PATTERN.fullmatch(key):
                _invalid(f"invalid allowed write collection key: {key}")
        for name in self.allowed_write_collection_names:
            if not name.strip() or len(name) > 255:
                _invalid("allowed write collection names must contain 1 to 255 characters")
        if (
            self.write_scope == "collections"
            and not self.allowed_write_collection_keys
            and not self.allowed_write_collection_names
        ):
            _invalid(
                "write_scope 'collections' requires an allowed collection key or exact name"
            )
        if self.write_enabled and self.write_scope == "disabled":
            _invalid("write_enabled requires an explicit non-disabled write_scope")
        if self.write_enabled and self.read_backend != "local":
            _invalid("Zotero 10 local writes require read_backend = 'local'")

        if not 1 <= self.request_timeout_seconds <= 60:
            _invalid("request_timeout_seconds must be between 1 and 60")
        if not 10 <= self.local_authorization_timeout_seconds <= 300:
            _invalid("local_authorization_timeout_seconds must be between 10 and 300")
        if not 1 <= self.max_page_size <= 100:
            _invalid("max_page_size must be between 1 and 100")
        if not 1_000 <= self.max_fulltext_chars <= 100_000:
            _invalid("max_fulltext_chars must be between 1000 and 100000")
        if not 1_000 <= self.max_note_chars <= 200_000:
            _invalid("max_note_chars must be between 1000 and 200000")
        if not 1_000_000 <= self.max_backend_response_bytes <= 100_000_000:
            _invalid("max_backend_response_bytes must be between 1000000 and 100000000")

    def validate_write_ready(self, environ: Mapping[str, str] | None = None) -> None:
        self.validate()
        if not self.write_enabled:
            raise IntegrationError("WRITE_DISABLED", "Zotero writes are disabled in local configuration")
        if self.write_scope == "disabled":
            raise IntegrationError("WRITE_SCOPE_DENIED", "No Zotero write scope is configured")
        # Zotero 10 grants an unscoped local key interactively on first write.
        # The service enforces this narrower configured scope before requesting it.


def load_config(
    path: str | os.PathLike[str] | None = None,
) -> ZoteroConfig:
    """Load the unified integrations TOML and return its Zotero section."""

    resolved = Path(path or os.environ.get("PAIOS_INTEGRATIONS_CONFIG", DEFAULT_CONFIG_PATH)).expanduser()
    if not resolved.is_file():
        raise IntegrationError(
            "CONFIG_NOT_FOUND",
            f"Integration configuration was not found at {resolved}",
        )
    try:
        with resolved.open("rb") as handle:
            document = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise IntegrationError("CONFIG_INVALID", f"Cannot read Integration configuration: {exc}") from exc

    section = document.get("zotero")
    if not isinstance(section, dict):
        raise IntegrationError("CONFIG_INVALID", "Missing [zotero] configuration table")
    unknown = sorted(set(section) - _ALLOWED_KEYS)
    if unknown:
        raise IntegrationError(
            "CONFIG_INVALID",
            "Unknown Zotero configuration fields",
            details={"fields": unknown},
        )

    try:
        config = ZoteroConfig(
            read_backend=_string(section, "read_backend", "local"),
            local_transport=_string(section, "local_transport", "auto"),
            library_alias=_string(section, "library_alias", "personal"),
            library_type=_string(section, "library_type", "user"),
            local_library_id=_string(section, "local_library_id", "0"),
            web_library_id=_string(section, "web_library_id", ""),
            local_api_url=_string(section, "local_api_url", "http://127.0.0.1:23119/api").rstrip("/"),
            web_api_url=_string(section, "web_api_url", "https://api.zotero.org").rstrip("/"),
            api_key_env=_string(section, "api_key_env", "ZOTERO_API_KEY"),
            better_bibtex_enabled=_boolean(section, "better_bibtex_enabled", True),
            better_bibtex_url=_string(
                section,
                "better_bibtex_url",
                "http://127.0.0.1:23119/better-bibtex/json-rpc",
            ).rstrip("/"),
            better_bibtex_library_id=_string(section, "better_bibtex_library_id", ""),
            write_enabled=_boolean(section, "write_enabled", False),
            write_scope=_string(section, "write_scope", "disabled"),
            allowed_write_collection_keys=tuple(
                _string_list(section, "allowed_write_collection_keys", [])
            ),
            allowed_write_collection_names=tuple(
                _string_list(section, "allowed_write_collection_names", [])
            ),
            request_timeout_seconds=_number(section, "request_timeout_seconds", 10.0),
            local_authorization_timeout_seconds=_number(
                section,
                "local_authorization_timeout_seconds",
                120.0,
            ),
            max_page_size=_integer(section, "max_page_size", 50),
            max_fulltext_chars=_integer(section, "max_fulltext_chars", 20_000),
            max_note_chars=_integer(section, "max_note_chars", 50_000),
            max_backend_response_bytes=_integer(
                section,
                "max_backend_response_bytes",
                25_000_000,
            ),
            source_path=str(resolved),
        )
    except (TypeError, ValueError) as exc:
        raise IntegrationError("CONFIG_INVALID", str(exc)) from exc
    config.validate()
    return config


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
    if not isinstance(value, list) or any(not isinstance(entry, str) for entry in value):
        raise TypeError(f"{key} must be an array of strings")
    return value


def _validate_numeric_id(value: str, field: str, *, allow_zero: bool) -> None:
    if not value.isdigit() or (not allow_zero and int(value) == 0):
        _invalid(f"{field} must be a {'non-zero ' if not allow_zero else ''}numeric Zotero library ID")


def _validate_loopback_url(value: str, expected_path: str, field: str) -> None:
    parsed = urlsplit(value)
    if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        _invalid(f"{field} must use HTTP on a loopback host")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        _invalid(f"{field} must not contain credentials, a query, or a fragment")
    if parsed.path.rstrip("/") != expected_path:
        _invalid(f"{field} must use the {expected_path} path")


def _validate_official_web_url(value: str) -> None:
    parsed = urlsplit(value)
    if (
        parsed.scheme != "https"
        or parsed.hostname != "api.zotero.org"
        or parsed.path.rstrip("/")
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        _invalid("web_api_url must be exactly https://api.zotero.org")


def _invalid(message: str) -> None:
    raise IntegrationError("CONFIG_INVALID", message)
