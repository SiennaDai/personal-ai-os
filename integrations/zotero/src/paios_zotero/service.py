"""Stable Zotero Integration operations over official Zotero APIs."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Mapping

from .adapter import (
    Clock,
    collection_ref,
    item_ref,
    normalize_collection,
    normalize_item,
    utc_now,
)
from .config import ZOTERO_KEY_PATTERN, ZoteroConfig
from .errors import IntegrationError
from .http_client import BetterBibtexClient, JsonResponse, ZoteroApiClient


_SORT_FIELDS = {
    "dateModified",
    "dateAdded",
    "title",
    "creator",
    "date",
    "publicationTitle",
    "itemType",
}
_SCALAR_FIELD_MAP = {
    "title": "title",
    "abstract": "abstractNote",
    "date": "date",
    "short_title": "shortTitle",
    "url": "url",
    "doi": "DOI",
    "isbn": "ISBN",
    "issn": "ISSN",
    "language": "language",
    "rights": "rights",
    "extra": "extra",
}
_ACTIVE_HTML = re.compile(
    r"<(?:script|iframe|object|embed)\b|javascript\s*:|\bon[a-z]+\s*=",
    re.IGNORECASE,
)


class ZoteroService:
    """Contract-level operations for one configured Zotero library."""

    def __init__(
        self,
        config: ZoteroConfig,
        *,
        environ: Mapping[str, str] | None = None,
        read_client: ZoteroApiClient | None = None,
        write_client: ZoteroApiClient | None = None,
        bbt_client: BetterBibtexClient | None = None,
        clock: Clock = utc_now,
    ) -> None:
        config.validate()
        self.config = config
        self.environ = environ
        self.read_client = read_client or ZoteroApiClient(
            config,
            config.read_backend,
            environ=environ,
        )
        self._write_client = write_client
        self._bbt_client = bbt_client
        self.clock = clock

    def status(self) -> dict[str, object]:
        """Perform a representative read and optional BBT readiness check."""

        read_status: dict[str, object]
        try:
            response = self.read_client.get(
                "/items",
                query={"format": "versions", "limit": 1},
            )
            if not isinstance(response.data, dict):
                raise IntegrationError(
                    "BACKEND_PROTOCOL_ERROR",
                    "Zotero status read returned an unexpected response",
                )
            read_status = {
                "available": True,
                "backend": self.config.read_backend,
                "transport": getattr(self.read_client, "transport_name", "injected"),
                "library_version": _header_int(response, "last-modified-version"),
            }
        except IntegrationError as exc:
            read_status = {
                "available": False,
                "backend": self.config.read_backend,
                "transport": getattr(self.read_client, "transport_name", "injected"),
                "error": exc.as_dict(),
            }

        bbt_status: dict[str, object]
        if not self.config.better_bibtex_enabled:
            bbt_status = {"enabled": False, "available": False, "required": False}
        else:
            try:
                ready = self.bbt_client.ready()
                bbt_status = {
                    "enabled": True,
                    "available": True,
                    "required": False,
                    "transport": getattr(self.bbt_client, "transport_name", "injected"),
                    "versions": ready,
                }
            except IntegrationError as exc:
                bbt_status = {
                    "enabled": True,
                    "available": False,
                    "required": False,
                    "transport": getattr(self.bbt_client, "transport_name", "injected"),
                    "error": exc.as_dict(),
                }

        write_status: dict[str, object] = {
            "enabled": self.config.write_enabled,
            "backend": "web",
            "scope": self.config.write_scope,
            "ready": False,
        }
        if self.config.write_enabled:
            try:
                self.config.validate_write_ready(self.environ)
                write_status["ready"] = True
            except IntegrationError as exc:
                write_status["error"] = exc.as_dict()

        overall_ok = bool(read_status["available"]) and (
            not self.config.write_enabled or bool(write_status["ready"])
        )
        return {
            "overall_ok": overall_ok,
            "checked_at": self.clock().isoformat(),
            "contract_version": "1.0",
            "configuration": self.config.public_summary(self.environ),
            "read": read_status,
            "better_bibtex": bbt_status,
            "write": write_status,
        }

    def search_items(
        self,
        query: str,
        *,
        qmode: str = "titleCreatorYear",
        item_type: str | None = None,
        collection_key: str | None = None,
        tag: str | None = None,
        top_level_only: bool = True,
        sort: str = "dateModified",
        direction: str = "desc",
        limit: int = 20,
        start: int = 0,
    ) -> dict[str, object]:
        query = _bounded_string(query, "query", 1, 500)
        if qmode not in {"titleCreatorYear", "everything"}:
            raise IntegrationError("INVALID_ARGUMENT", "qmode is not supported")
        if item_type is not None:
            item_type = _bounded_string(item_type, "item_type", 1, 100)
        if collection_key is not None:
            _validate_key(collection_key, "collection_key")
        if tag is not None:
            tag = _bounded_string(tag, "tag", 1, 500)
        self._validate_page(limit, start)
        self._validate_sort(sort, direction)

        if collection_key:
            path = f"/collections/{collection_key}/items"
        else:
            path = "/items"
        if top_level_only:
            path += "/top"
        params: dict[str, object] = {
            "q": query,
            "qmode": qmode,
            "sort": sort,
            "direction": direction,
            "limit": limit,
            "start": start,
        }
        if item_type:
            params["itemType"] = item_type
        if tag:
            params["tag"] = tag
        return self._paged_items(path, params, limit, start)

    def get_item(self, item_key: str) -> dict[str, object]:
        _validate_key(item_key, "item_key")
        raw = self._get_raw_item(self.read_client, item_key)
        return {"item": self._normalize_item(raw, self.config.read_backend)}

    def list_collections(
        self,
        *,
        parent_collection_key: str | None = None,
        top_level_only: bool = False,
        limit: int = 50,
        start: int = 0,
    ) -> dict[str, object]:
        self._validate_page(limit, start)
        if parent_collection_key:
            _validate_key(parent_collection_key, "parent_collection_key")
            path = f"/collections/{parent_collection_key}/collections"
        elif top_level_only:
            path = "/collections/top"
        else:
            path = "/collections"
        response = self.read_client.get(
            path,
            query={"sort": "title", "direction": "asc", "limit": limit, "start": start},
        )
        rows = _object_list(response.data, "collection list")
        return {
            "collections": [
                normalize_collection(
                    row,
                    self.config,
                    self.config.read_backend,
                    clock=self.clock,
                )
                for row in rows
            ],
            "page": _page(response, start, limit, len(rows)),
        }

    def get_collection_items(
        self,
        collection_key: str,
        *,
        top_level_only: bool = True,
        sort: str = "dateModified",
        direction: str = "desc",
        limit: int = 20,
        start: int = 0,
    ) -> dict[str, object]:
        _validate_key(collection_key, "collection_key")
        self._validate_page(limit, start)
        self._validate_sort(sort, direction)
        path = f"/collections/{collection_key}/items"
        if top_level_only:
            path += "/top"
        return self._paged_items(
            path,
            {"sort": sort, "direction": direction, "limit": limit, "start": start},
            limit,
            start,
        )

    def get_item_children(
        self,
        item_key: str,
        *,
        item_type: str | None = None,
        limit: int = 50,
        start: int = 0,
    ) -> dict[str, object]:
        _validate_key(item_key, "item_key")
        self._validate_page(limit, start)
        params: dict[str, object] = {"limit": limit, "start": start, "sort": "dateAdded"}
        if item_type:
            params["itemType"] = _bounded_string(item_type, "item_type", 1, 100)
        return self._paged_items(f"/items/{item_key}/children", params, limit, start)

    def get_annotations(
        self,
        item_key: str,
        *,
        limit: int = 50,
        start: int = 0,
    ) -> dict[str, object]:
        _validate_key(item_key, "item_key")
        self._validate_page(limit, start)
        target = self._get_raw_item(self.read_client, item_key)
        target_data = _item_data(target)
        item_type = target_data.get("itemType")
        if item_type == "attachment":
            attachments = [target]
        elif item_type in {"note", "annotation"}:
            raise IntegrationError(
                "INVALID_ARGUMENT",
                "Annotations can be requested for a bibliographic item or attachment only",
            )
        else:
            attachments = [
                child
                for child in self._fetch_all_children(item_key, hard_limit=100)
                if _item_data(child).get("itemType") == "attachment"
            ]

        annotations: list[dict[str, object]] = []
        truncated_scan = False
        for attachment in attachments:
            attachment_key = _raw_key(attachment)
            remaining = 500 - len(annotations)
            if remaining <= 0:
                truncated_scan = True
                break
            children = self._fetch_all_children(attachment_key, hard_limit=remaining)
            for child in children:
                if _item_data(child).get("itemType") == "annotation":
                    annotations.append(child)
            if len(children) >= remaining:
                truncated_scan = True
                break
        annotations.sort(key=lambda row: str(_item_data(row).get("annotationSortIndex", "")))
        selected = annotations[start : start + limit]
        result: dict[str, object] = {
            "annotations": [
                self._normalize_item(annotation, self.config.read_backend)
                for annotation in selected
            ],
            "page": {
                "start": start,
                "limit": limit,
                "returned": len(selected),
                "total": len(annotations),
                "has_more": start + len(selected) < len(annotations) or truncated_scan,
                "next_start": start + len(selected)
                if start + len(selected) < len(annotations) or truncated_scan
                else None,
            },
        }
        if truncated_scan:
            result["warnings"] = ["Annotation discovery stopped at the 500-item safety cap"]
        return result

    def get_fulltext(
        self,
        item_key: str,
        *,
        attachment_key: str | None = None,
        offset: int = 0,
        max_chars: int | None = None,
    ) -> dict[str, object]:
        _validate_key(item_key, "item_key")
        if attachment_key:
            _validate_key(attachment_key, "attachment_key")
        if isinstance(offset, bool) or not isinstance(offset, int) or offset < 0:
            raise IntegrationError("INVALID_ARGUMENT", "offset must be a non-negative integer")
        effective_max = self.config.max_fulltext_chars if max_chars is None else max_chars
        if (
            isinstance(effective_max, bool)
            or not isinstance(effective_max, int)
            or not 1 <= effective_max <= self.config.max_fulltext_chars
        ):
            raise IntegrationError(
                "INVALID_ARGUMENT",
                f"max_chars must be between 1 and {self.config.max_fulltext_chars}",
            )

        target = self._get_raw_item(self.read_client, item_key)
        target_data = _item_data(target)
        if target_data.get("itemType") == "attachment":
            selected = target
            if attachment_key and attachment_key != item_key:
                raise IntegrationError(
                    "INVALID_ARGUMENT",
                    "attachment_key does not match the attachment item_key",
                )
        else:
            attachments = [
                child
                for child in self._fetch_all_children(item_key, hard_limit=100)
                if _item_data(child).get("itemType") == "attachment"
                and _item_data(child).get("contentType") == "application/pdf"
            ]
            if attachment_key:
                matches = [entry for entry in attachments if _raw_key(entry) == attachment_key]
                if not matches:
                    raise IntegrationError(
                        "NOT_FOUND",
                        "The requested PDF attachment is not a child of the item",
                    )
                selected = matches[0]
            elif not attachments:
                raise IntegrationError("NOT_FOUND", "No indexed PDF attachment was found for the item")
            elif len(attachments) > 1:
                raise IntegrationError(
                    "AMBIGUOUS_ATTACHMENT",
                    "The item has multiple PDF attachments; specify attachment_key",
                    details={
                        "candidates": [
                            {
                                "key": _raw_key(entry),
                                "title": _item_data(entry).get("title"),
                                "filename": _item_data(entry).get("filename"),
                            }
                            for entry in attachments
                        ]
                    },
                )
            else:
                selected = attachments[0]

        selected_key = _raw_key(selected)
        response = self.read_client.get(f"/items/{selected_key}/fulltext")
        if not isinstance(response.data, dict) or not isinstance(response.data.get("content"), str):
            raise IntegrationError(
                "FULLTEXT_UNAVAILABLE",
                "Zotero did not return indexed full text for the attachment",
            )
        content = response.data["content"]
        chunk = content[offset : offset + effective_max]
        return {
            "attachment_ref": item_ref(
                self.config,
                selected_key,
                _optional_int(selected.get("version")),
            ),
            "content": chunk,
            "offset": offset,
            "returned_chars": len(chunk),
            "total_chars": len(content),
            "truncated": offset + len(chunk) < len(content),
            "next_offset": offset + len(chunk) if offset + len(chunk) < len(content) else None,
            "indexed_pages": _optional_int(response.data.get("indexedPages")),
            "total_pages": _optional_int(response.data.get("totalPages")),
            "provenance": {
                "backend": self.config.read_backend,
                "retrieved_at": self.clock().isoformat(),
            },
        }

    def get_citation_key(self, item_key: str) -> dict[str, object]:
        _validate_key(item_key, "item_key")
        if not self.config.better_bibtex_enabled:
            raise IntegrationError(
                "OPTIONAL_CAPABILITY_UNAVAILABLE",
                "Better BibTeX citation-key lookup is disabled",
            )
        lookup_key = item_key
        if self.config.better_bibtex_library_id:
            lookup_key = f"{self.config.better_bibtex_library_id}:{item_key}"
        result = self.bbt_client.citation_keys([lookup_key])
        citation_key = result.get(lookup_key) or result.get(item_key)
        if not citation_key:
            raise IntegrationError("NOT_FOUND", "Better BibTeX did not return a citation key")
        return {
            "item_ref": item_ref(self.config, item_key, None),
            "citation_key": citation_key,
            "provenance": {
                "backend": "better-bibtex-json-rpc",
                "retrieved_at": self.clock().isoformat(),
            },
        }

    def create_child_note(
        self,
        parent_item_key: str,
        note_html: str,
        idempotency_key: str,
        *,
        tags: list[str] | None = None,
    ) -> dict[str, object]:
        self._assert_write_ready()
        _validate_key(parent_item_key, "parent_item_key")
        note_html = self._validate_note_html(note_html)
        if not re.fullmatch(r"[A-Fa-f0-9]{32}", idempotency_key):
            raise IntegrationError(
                "INVALID_ARGUMENT",
                "idempotency_key must contain exactly 32 hexadecimal characters",
            )
        normalized_tags = self._validate_tags(tags or [])
        parent = self._get_raw_item(self.write_client, parent_item_key)
        self._assert_item_in_write_scope(parent)
        response = self.write_client.post(
            "/items",
            [
                {
                    "itemType": "note",
                    "parentItem": parent_item_key,
                    "note": note_html,
                    "tags": [{"tag": tag} for tag in normalized_tags],
                }
            ],
            headers={"Zotero-Write-Token": idempotency_key.lower()},
        )
        created_key = _created_item_key(response)
        created = self._get_raw_item(self.write_client, created_key)
        return {
            "created": self._normalize_item(created, "web"),
            "effect": "created_child_note",
        }

    def update_note(
        self,
        note_item_key: str,
        expected_version: int,
        note_html: str,
    ) -> dict[str, object]:
        self._assert_write_ready()
        _validate_key(note_item_key, "note_item_key")
        expected_version = _validate_version(expected_version)
        note_html = self._validate_note_html(note_html)
        current = self._get_raw_item(self.write_client, note_item_key)
        if _item_data(current).get("itemType") != "note":
            raise IntegrationError("INVALID_ARGUMENT", "The target item is not a Zotero note")
        self._assert_expected_version(current, expected_version)
        self._assert_item_in_write_scope(current)
        self.write_client.patch(
            f"/items/{note_item_key}",
            {"note": note_html},
            headers={"If-Unmodified-Since-Version": str(expected_version)},
        )
        updated = self._get_raw_item(self.write_client, note_item_key)
        return {"updated": self._normalize_item(updated, "web"), "effect": "updated_note"}

    def update_item_fields(
        self,
        item_key: str,
        expected_version: int,
        fields: dict[str, str],
    ) -> dict[str, object]:
        self._assert_write_ready()
        _validate_key(item_key, "item_key")
        expected_version = _validate_version(expected_version)
        if not isinstance(fields, dict) or not fields:
            raise IntegrationError("INVALID_ARGUMENT", "fields must be a non-empty object")
        unknown = sorted(set(fields) - set(_SCALAR_FIELD_MAP))
        if unknown:
            raise IntegrationError(
                "INVALID_ARGUMENT",
                "Unsupported metadata fields",
                details={"fields": unknown, "allowed": sorted(_SCALAR_FIELD_MAP)},
            )
        if len(fields) > 8:
            raise IntegrationError("LIMIT_EXCEEDED", "At most 8 metadata fields may be updated")
        patch: dict[str, str] = {}
        for stable_name, value in fields.items():
            if not isinstance(value, str):
                raise IntegrationError(
                    "INVALID_ARGUMENT",
                    f"Metadata field {stable_name} must be a string",
                )
            max_length = 20_000 if stable_name in {"abstract", "extra"} else 2_000
            if len(value) > max_length:
                raise IntegrationError(
                    "LIMIT_EXCEEDED",
                    f"Metadata field {stable_name} exceeds {max_length} characters",
                )
            patch[_SCALAR_FIELD_MAP[stable_name]] = value

        current = self._get_raw_item(self.write_client, item_key)
        item_type = _item_data(current).get("itemType")
        if item_type in {"note", "attachment", "annotation"}:
            raise IntegrationError(
                "INVALID_ARGUMENT",
                "Scalar metadata updates are limited to bibliographic items",
            )
        self._assert_expected_version(current, expected_version)
        self._assert_item_in_write_scope(current)
        self.write_client.patch(
            f"/items/{item_key}",
            patch,
            headers={"If-Unmodified-Since-Version": str(expected_version)},
        )
        updated = self._get_raw_item(self.write_client, item_key)
        return {
            "updated": self._normalize_item(updated, "web"),
            "effect": "updated_scalar_metadata",
            "changed_fields": sorted(fields),
        }

    @property
    def write_client(self) -> ZoteroApiClient:
        if self._write_client is None:
            self._write_client = ZoteroApiClient(
                self.config,
                "web",
                environ=self.environ,
            )
        return self._write_client

    @property
    def bbt_client(self) -> BetterBibtexClient:
        if self._bbt_client is None:
            self._bbt_client = BetterBibtexClient(self.config)
        return self._bbt_client

    def _paged_items(
        self,
        path: str,
        params: dict[str, object],
        limit: int,
        start: int,
    ) -> dict[str, object]:
        response = self.read_client.get(path, query=params)
        rows = _object_list(response.data, "item list")
        return {
            "items": [self._normalize_item(row, self.config.read_backend) for row in rows],
            "page": _page(response, start, limit, len(rows)),
        }

    def _fetch_all_children(self, item_key: str, *, hard_limit: int) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        start = 0
        while len(rows) < hard_limit:
            limit = min(100, hard_limit - len(rows))
            response = self.read_client.get(
                f"/items/{item_key}/children",
                query={"limit": limit, "start": start},
            )
            page_rows = _object_list(response.data, "child item list")
            rows.extend(page_rows)
            total = _header_int(response, "total-results")
            if not page_rows or len(page_rows) < limit or (total is not None and len(rows) >= total):
                break
            start += len(page_rows)
        return rows

    def _get_raw_item(self, client: ZoteroApiClient, item_key: str) -> dict[str, object]:
        response = client.get(f"/items/{item_key}")
        if not isinstance(response.data, dict):
            raise IntegrationError(
                "BACKEND_PROTOCOL_ERROR",
                "Zotero returned an invalid item response",
            )
        return response.data

    def _normalize_item(self, raw: object, backend: str) -> dict[str, object]:
        return normalize_item(raw, self.config, backend, clock=self.clock)

    def _validate_page(self, limit: int, start: int) -> None:
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= self.config.max_page_size:
            raise IntegrationError(
                "INVALID_ARGUMENT",
                f"limit must be between 1 and {self.config.max_page_size}",
            )
        if isinstance(start, bool) or not isinstance(start, int) or start < 0:
            raise IntegrationError("INVALID_ARGUMENT", "start must be a non-negative integer")

    @staticmethod
    def _validate_sort(sort: str, direction: str) -> None:
        if sort not in _SORT_FIELDS:
            raise IntegrationError("INVALID_ARGUMENT", "sort is not supported")
        if direction not in {"asc", "desc"}:
            raise IntegrationError("INVALID_ARGUMENT", "direction must be 'asc' or 'desc'")

    def _assert_write_ready(self) -> None:
        self.config.validate_write_ready(self.environ)

    def _assert_expected_version(self, raw: dict[str, object], expected: int) -> None:
        actual = _optional_int(raw.get("version"))
        if actual != expected:
            raise IntegrationError(
                "VERSION_CONFLICT",
                "The supplied expected_version does not match the current Zotero item version",
                details={"expected_version": expected, "current_version": actual},
            )

    def _assert_item_in_write_scope(self, raw: dict[str, object]) -> None:
        if self.config.write_scope == "library":
            return
        data = _item_data(raw)
        if data.get("itemType") in {"note", "attachment", "annotation"} and data.get("parentItem"):
            parent_key = str(data["parentItem"])
            parent = self._get_raw_item(self.write_client, parent_key)
            data = _item_data(parent)
        collections = set(entry for entry in data.get("collections", []) if isinstance(entry, str))
        allowed = set(self.config.allowed_write_collection_keys)
        if not collections.intersection(allowed):
            raise IntegrationError(
                "WRITE_SCOPE_DENIED",
                "The target item is outside the configured Zotero write collections",
                details={"allowed_collection_keys": sorted(allowed)},
            )

    def _validate_note_html(self, value: str) -> str:
        value = _bounded_string(value, "note_html", 1, self.config.max_note_chars)
        if _ACTIVE_HTML.search(value):
            raise IntegrationError(
                "INVALID_ARGUMENT",
                "note_html contains active content that is not allowed",
            )
        return value

    @staticmethod
    def _validate_tags(tags: list[str]) -> list[str]:
        if len(tags) > 20:
            raise IntegrationError("LIMIT_EXCEEDED", "At most 20 tags may be supplied")
        normalized: list[str] = []
        for tag in tags:
            normalized.append(_bounded_string(tag, "tag", 1, 200))
        return normalized


def _validate_key(value: str, field: str) -> None:
    if not isinstance(value, str) or not ZOTERO_KEY_PATTERN.fullmatch(value):
        raise IntegrationError("INVALID_ARGUMENT", f"{field} is not a valid Zotero object key")


def _bounded_string(value: object, field: str, minimum: int, maximum: int) -> str:
    if not isinstance(value, str) or not minimum <= len(value) <= maximum:
        raise IntegrationError(
            "INVALID_ARGUMENT",
            f"{field} must contain between {minimum} and {maximum} characters",
        )
    return value


def _validate_version(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise IntegrationError("INVALID_ARGUMENT", "expected_version must be a non-negative integer")
    return value


def _object_list(value: object, label: str) -> list[dict[str, object]]:
    if not isinstance(value, list) or any(not isinstance(entry, dict) for entry in value):
        raise IntegrationError(
            "BACKEND_PROTOCOL_ERROR",
            f"Zotero returned an invalid {label}",
        )
    return value


def _item_data(raw: dict[str, object]) -> dict[str, object]:
    data = raw.get("data")
    if not isinstance(data, dict):
        raise IntegrationError(
            "BACKEND_PROTOCOL_ERROR",
            "Zotero item does not contain editable data",
        )
    return data


def _raw_key(raw: dict[str, object]) -> str:
    data = raw.get("data") if isinstance(raw.get("data"), dict) else {}
    key = raw.get("key") or data.get("key")
    if not isinstance(key, str):
        raise IntegrationError("BACKEND_PROTOCOL_ERROR", "Zotero item does not contain a key")
    return key


def _optional_int(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _header_int(response: JsonResponse, name: str) -> int | None:
    value = response.headers.get(name)
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _page(response: JsonResponse, start: int, limit: int, returned: int) -> dict[str, object]:
    total = _header_int(response, "total-results")
    has_more = start + returned < total if total is not None else returned == limit
    return {
        "start": start,
        "limit": limit,
        "returned": returned,
        "total": total,
        "has_more": has_more,
        "next_start": start + returned if has_more else None,
    }


def _created_item_key(response: JsonResponse) -> str:
    if not isinstance(response.data, dict):
        raise IntegrationError(
            "BACKEND_PROTOCOL_ERROR",
            "Zotero create response is not an object",
        )
    successful = response.data.get("successful", response.data.get("success"))
    if not isinstance(successful, dict) or "0" not in successful:
        failed = response.data.get("failed")
        raise IntegrationError(
            "WRITE_FAILED",
            "Zotero did not create the note",
            details={"failed": failed} if isinstance(failed, dict) else {},
        )
    created = successful["0"]
    if isinstance(created, str):
        key = created
    elif isinstance(created, dict):
        data = created.get("data") if isinstance(created.get("data"), dict) else {}
        key = created.get("key") or data.get("key")
    else:
        key = None
    if not isinstance(key, str) or not ZOTERO_KEY_PATTERN.fullmatch(key):
        raise IntegrationError(
            "BACKEND_PROTOCOL_ERROR",
            "Zotero create response does not contain a valid item key",
        )
    return key
