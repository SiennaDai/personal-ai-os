"""Stable Zotero Integration operations over official Zotero APIs."""

from __future__ import annotations

import hashlib
import os
import re
import stat
from datetime import datetime
from pathlib import Path
from typing import Mapping
from urllib.parse import urlsplit

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
_PAPER_CONTAINER_FIELDS = {
    "journalArticle": "publicationTitle",
    "conferencePaper": "proceedingsTitle",
    "preprint": "repository",
    "bookSection": "bookTitle",
    "thesis": "university",
    "report": "institution",
}
_PAPER_OPTIONAL_FIELDS = {
    "abstract": ("abstractNote", 20_000),
    "date": ("date", 2_000),
    "url": ("url", 2_000),
    "doi": ("DOI", 2_000),
    "language": ("language", 2_000),
    "volume": ("volume", 200),
    "issue": ("issue", 200),
    "pages": ("pages", 500),
    "extra": ("extra", 20_000),
}
_ACTIVE_HTML = re.compile(
    r"<(?:script|iframe|object|embed)\b|javascript\s*:|\bon[a-z]+\s*=",
    re.IGNORECASE,
)
_CONTRACT_VERSION = "1.2"
_ZOTERO_KEY_ALPHABET = "23456789ABCDEFGHIJKLMNPQRSTUVWXYZ"


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
            "backend": "local",
            "scope": self.config.write_scope,
            "ready": False,
            "authorization": "requested_on_first_write",
            "pdf_attachment_upload": {
                "enabled": self.config.attachment_upload_enabled,
                "allowed_root_count": len(self.config.allowed_pdf_import_roots),
                "max_pdf_bytes": self.config.max_pdf_bytes,
            },
        }
        if self.config.write_enabled:
            try:
                self.config.validate_write_ready(self.environ)
                capability = self.write_client.local_write_capability()
                write_status.update(capability)
                write_status["ready"] = True
            except IntegrationError as exc:
                write_status["error"] = exc.as_dict()

        overall_ok = bool(read_status["available"]) and (
            not self.config.write_enabled or bool(write_status["ready"])
        )
        return {
            "overall_ok": overall_ok,
            "checked_at": self.clock().isoformat(),
            "contract_version": _CONTRACT_VERSION,
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
        self._validate_idempotency_key(idempotency_key)
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
            "created": self._normalize_item(created, "local"),
            "effect": "created_child_note",
        }

    def create_bibliographic_item(
        self,
        item_type: str,
        title: str,
        collection_key: str,
        idempotency_key: str,
        *,
        creators: list[dict[str, str]] | None = None,
        container_title: str | None = None,
        fields: dict[str, str] | None = None,
        tags: list[str] | None = None,
    ) -> dict[str, object]:
        """Create one bounded bibliographic record in an allowed collection."""

        self._assert_write_ready()
        if item_type not in _PAPER_CONTAINER_FIELDS:
            raise IntegrationError("INVALID_ARGUMENT", "item_type is not a supported paper type")
        title = _bounded_string(title, "title", 1, 2_000)
        _validate_key(collection_key, "collection_key")
        self._validate_idempotency_key(idempotency_key)
        self._assert_collection_in_write_scope(collection_key)

        item: dict[str, object] = {
            "itemType": item_type,
            "title": title,
            "creators": self._validate_creators(creators or []),
            "tags": [{"tag": tag} for tag in self._validate_tags(tags or [])],
            "collections": [collection_key],
        }
        if container_title is not None:
            item[_PAPER_CONTAINER_FIELDS[item_type]] = _bounded_string(
                container_title,
                "container_title",
                1,
                2_000,
            )
        supplied_fields = fields or {}
        unknown = sorted(set(supplied_fields) - set(_PAPER_OPTIONAL_FIELDS))
        if unknown:
            raise IntegrationError(
                "INVALID_ARGUMENT",
                "Unsupported bibliographic fields",
                details={"fields": unknown, "allowed": sorted(_PAPER_OPTIONAL_FIELDS)},
            )
        for stable_name, value in supplied_fields.items():
            native_name, max_length = _PAPER_OPTIONAL_FIELDS[stable_name]
            item[native_name] = _bounded_string(value, stable_name, 1, max_length)

        response = self.write_client.post(
            "/items",
            [item],
            headers={"Zotero-Write-Token": idempotency_key.lower()},
        )
        created_key = _created_item_key(response, "bibliographic item")
        created = self._get_raw_item(self.write_client, created_key)
        return {
            "created": self._normalize_item(created, "local"),
            "effect": "created_bibliographic_item",
            "destination_collection_ref": collection_ref(
                self.config,
                collection_key,
                None,
            ),
        }

    def import_pdf_attachment(
        self,
        parent_item_key: str,
        expected_parent_version: int,
        pdf_path: str,
        operation_id: str,
        *,
        source_url: str | None = None,
        title: str = "Full Text PDF",
    ) -> dict[str, object]:
        """Import one staged PDF as a stored child attachment."""

        self.config.validate_attachment_upload_ready()
        _validate_key(parent_item_key, "parent_item_key")
        expected_parent_version = _validate_version(expected_parent_version)
        self._validate_idempotency_key(operation_id)
        title = _bounded_string(title, "title", 1, 2_000)
        source_url = self._validate_source_url(source_url)

        parent = self._get_raw_item(self.write_client, parent_item_key)
        if _item_data(parent).get("itemType") in {"note", "attachment", "annotation"}:
            raise IntegrationError(
                "INVALID_ARGUMENT",
                "PDF attachments require a bibliographic parent item",
            )
        self._assert_expected_version(parent, expected_parent_version)
        self._assert_item_in_write_scope(parent)

        attachment_key = _operation_item_key(operation_id, parent_item_key)
        with self._open_validated_pdf(pdf_path) as pdf:
            file_info = self._hash_pdf(pdf)
            filename = Path(pdf_path).name
            existing = self._find_existing_pdf(parent_item_key, file_info["md5"], attachment_key)
            if existing is not None:
                return self._pdf_result(existing, "pdf_already_attached", file_info, source_url)

            attachment = self._get_optional_item(attachment_key)
            if attachment is None:
                try:
                    attachment = self._create_pdf_attachment_item(
                        attachment_key,
                        parent_item_key,
                        filename,
                        title,
                        source_url,
                        operation_id,
                    )
                except IntegrationError as exc:
                    raise self._pdf_partial_error(
                        exc,
                        "create_attachment",
                        parent_item_key,
                        attachment_key,
                    ) from exc
            else:
                self._assert_resumable_attachment(attachment, parent_item_key, filename)
                if _item_data(attachment).get("md5") == file_info["md5"]:
                    return self._pdf_result(
                        attachment,
                        "pdf_already_attached",
                        file_info,
                        source_url,
                    )

            stage = "authorize_upload"
            try:
                authorization = self.write_client.post_form(
                    f"/items/{attachment_key}/file",
                    {
                        "md5": file_info["md5"],
                        "filename": filename,
                        "filesize": file_info["size"],
                        "mtime": file_info["mtime_ms"],
                    },
                    headers={"If-None-Match": "*"},
                )
                if not isinstance(authorization.data, dict):
                    raise IntegrationError(
                        "BACKEND_PROTOCOL_ERROR",
                        "Zotero returned an invalid PDF upload authorization",
                    )
                if authorization.data.get("exists") == 1:
                    verified = self._verify_uploaded_pdf(
                        attachment_key,
                        parent_item_key,
                        file_info["md5"],
                    )
                    return self._pdf_result(
                        verified,
                        "pdf_already_attached",
                        file_info,
                        source_url,
                    )

                upload_url = authorization.data.get("url")
                upload_key = authorization.data.get("uploadKey")
                content_type = authorization.data.get("contentType")
                if (
                    not isinstance(upload_url, str)
                    or not isinstance(upload_key, str)
                    or not upload_key
                    or not isinstance(content_type, str)
                    or authorization.data.get("prefix", "") != ""
                    or authorization.data.get("suffix", "") != ""
                ):
                    raise IntegrationError(
                        "BACKEND_PROTOCOL_ERROR",
                        "Zotero returned unsupported local PDF upload parameters",
                    )

                stage = "upload_bytes"
                pdf.seek(0)
                self.write_client.post_upload(
                    upload_url,
                    pdf,
                    file_info["size"],
                    content_type,
                )

                stage = "register_upload"
                self.write_client.post_form(
                    f"/items/{attachment_key}/file",
                    {"upload": upload_key},
                    headers={"If-None-Match": "*"},
                )

                stage = "verify_upload"
                verified = self._verify_uploaded_pdf(
                    attachment_key,
                    parent_item_key,
                    file_info["md5"],
                )
                return self._pdf_result(
                    verified,
                    "imported_pdf_attachment",
                    file_info,
                    source_url,
                )
            except IntegrationError as exc:
                raise self._pdf_partial_error(
                    exc,
                    stage,
                    parent_item_key,
                    attachment_key,
                ) from exc

    def add_item_to_collection(
        self,
        item_key: str,
        expected_version: int,
        collection_key: str,
    ) -> dict[str, object]:
        """Append one allowed collection without removing any existing membership."""

        self._assert_write_ready()
        _validate_key(item_key, "item_key")
        _validate_key(collection_key, "collection_key")
        expected_version = _validate_version(expected_version)
        self._assert_collection_in_write_scope(collection_key)
        current = self._get_raw_item(self.write_client, item_key)
        if _item_data(current).get("itemType") in {"note", "attachment", "annotation"}:
            raise IntegrationError(
                "INVALID_ARGUMENT",
                "Collection membership can be added only to a bibliographic item",
            )
        self._assert_expected_version(current, expected_version)
        collections = _collection_keys(_item_data(current).get("collections", []))
        if collection_key in collections:
            return {
                "updated": self._normalize_item(current, "local"),
                "effect": "already_in_collection",
                "destination_collection_ref": collection_ref(self.config, collection_key, None),
            }
        self.write_client.patch(
            f"/items/{item_key}",
            {"collections": [*collections, collection_key]},
            headers={"If-Unmodified-Since-Version": str(expected_version)},
        )
        updated = self._get_raw_item(self.write_client, item_key)
        return {
            "updated": self._normalize_item(updated, "local"),
            "effect": "added_to_collection",
            "destination_collection_ref": collection_ref(self.config, collection_key, None),
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
        return {"updated": self._normalize_item(updated, "local"), "effect": "updated_note"}

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
            "updated": self._normalize_item(updated, "local"),
            "effect": "updated_scalar_metadata",
            "changed_fields": sorted(fields),
        }

    @property
    def write_client(self) -> ZoteroApiClient:
        if self._write_client is None:
            self._write_client = ZoteroApiClient(
                self.config,
                "local",
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
        collections = set(_collection_keys(data.get("collections", [])))
        allowed = set(self.config.allowed_write_collection_keys)
        if collections.intersection(allowed):
            return
        allowed_names = set(self.config.allowed_write_collection_names)
        if allowed_names and any(
            self._collection_name(key) in allowed_names for key in collections
        ):
            return
        raise IntegrationError(
            "WRITE_SCOPE_DENIED",
            "The target item is outside the configured Zotero write collections",
            details={
                "allowed_collection_keys": sorted(allowed),
                "allowed_collection_names": sorted(allowed_names),
            },
        )

    def _assert_collection_in_write_scope(self, collection_key: str) -> None:
        if self.config.write_scope == "library":
            self._collection_name(collection_key)
            return
        if collection_key in self.config.allowed_write_collection_keys:
            self._collection_name(collection_key)
            return
        name = self._collection_name(collection_key)
        if name not in self.config.allowed_write_collection_names:
            raise IntegrationError(
                "WRITE_SCOPE_DENIED",
                "The destination collection is outside the configured Zotero write scope",
                details={"collection_key": collection_key, "collection_name": name},
            )

    def _collection_name(self, collection_key: str) -> str:
        response = self.write_client.get(f"/collections/{collection_key}")
        if not isinstance(response.data, dict) or not isinstance(response.data.get("data"), dict):
            raise IntegrationError(
                "BACKEND_PROTOCOL_ERROR",
                "Zotero returned an invalid collection response",
            )
        name = response.data["data"].get("name")
        if not isinstance(name, str):
            raise IntegrationError(
                "BACKEND_PROTOCOL_ERROR",
                "Zotero collection does not contain a name",
            )
        return name

    def _validate_note_html(self, value: str) -> str:
        value = _bounded_string(value, "note_html", 1, self.config.max_note_chars)
        if _ACTIVE_HTML.search(value):
            raise IntegrationError(
                "INVALID_ARGUMENT",
                "note_html contains active content that is not allowed",
            )
        return value

    def _open_validated_pdf(self, value: str):  # noqa: ANN201
        if not isinstance(value, str) or not value or len(value) > 4_096:
            raise IntegrationError("INVALID_ARGUMENT", "pdf_path must be a non-empty local path")
        candidate = Path(value).expanduser()
        if not candidate.is_absolute():
            raise IntegrationError("INVALID_ARGUMENT", "pdf_path must be absolute")
        lexical = Path(os.path.abspath(candidate))
        allowed_root: Path | None = None
        for configured in self.config.allowed_pdf_import_roots:
            root = Path(os.path.abspath(Path(configured).expanduser()))
            try:
                lexical.relative_to(root)
            except ValueError:
                continue
            allowed_root = root
            break
        if allowed_root is None:
            raise IntegrationError(
                "FILE_SCOPE_DENIED",
                "The staged PDF is outside the configured import roots",
            )
        try:
            resolved_root = allowed_root.resolve(strict=True)
            resolved = lexical.resolve(strict=True)
            resolved.relative_to(resolved_root)
        except (OSError, ValueError) as exc:
            raise IntegrationError(
                "FILE_SCOPE_DENIED",
                "The staged PDF path is unavailable or escapes its configured import root",
            ) from exc
        if not allowed_root.is_dir():
            raise IntegrationError("FILE_SCOPE_DENIED", "PDF import roots must be directories")
        if allowed_root.is_symlink():
            raise IntegrationError("FILE_SCOPE_DENIED", "PDF import roots cannot be symbolic links")
        current = allowed_root
        for part in lexical.relative_to(allowed_root).parts:
            current = current / part
            if current.is_symlink():
                raise IntegrationError(
                    "FILE_SCOPE_DENIED",
                    "The staged PDF path cannot contain symbolic links",
                )
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        try:
            descriptor = os.open(resolved, flags)
            handle = os.fdopen(descriptor, "rb")
        except OSError as exc:
            raise IntegrationError("FILE_UNAVAILABLE", "Cannot open the staged PDF") from exc
        metadata = os.fstat(handle.fileno())
        if not stat.S_ISREG(metadata.st_mode):
            handle.close()
            raise IntegrationError("INVALID_PDF", "The staged PDF must be a regular file")
        if metadata.st_size > self.config.max_pdf_bytes:
            handle.close()
            raise IntegrationError(
                "LIMIT_EXCEEDED",
                "The staged PDF exceeds the configured byte limit",
                details={"max_pdf_bytes": self.config.max_pdf_bytes},
            )
        if metadata.st_size < 5 or handle.read(5) != b"%PDF-":
            handle.close()
            raise IntegrationError("INVALID_PDF", "The staged file does not have a PDF signature")
        handle.seek(0)
        return handle

    @staticmethod
    def _hash_pdf(handle) -> dict[str, object]:  # noqa: ANN001
        before = os.fstat(handle.fileno())
        md5 = hashlib.md5(usedforsecurity=False)
        sha256 = hashlib.sha256()
        size = 0
        while chunk := handle.read(64 * 1024):
            md5.update(chunk)
            sha256.update(chunk)
            size += len(chunk)
        metadata = os.fstat(handle.fileno())
        if (
            size != metadata.st_size
            or (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
            != (metadata.st_dev, metadata.st_ino, metadata.st_size, metadata.st_mtime_ns)
        ):
            raise IntegrationError("FILE_CHANGED", "The staged PDF changed while it was read")
        handle.seek(0)
        return {
            "size": size,
            "mtime_ms": metadata.st_mtime_ns // 1_000_000,
            "md5": md5.hexdigest(),
            "sha256": sha256.hexdigest(),
        }

    def _find_existing_pdf(
        self,
        parent_item_key: str,
        md5: str,
        resumable_key: str,
    ) -> dict[str, object] | None:
        response = self.write_client.get(
            f"/items/{parent_item_key}/children",
            query={"itemType": "attachment", "limit": 100},
        )
        children = _object_list(response.data, "attachment list")
        other_pdfs: list[dict[str, object]] = []
        for child in children:
            data = _item_data(child)
            if data.get("contentType") != "application/pdf":
                continue
            if data.get("md5") == md5:
                return child
            if _raw_key(child) != resumable_key:
                other_pdfs.append(child)
        if other_pdfs:
            raise IntegrationError(
                "PDF_ATTACHMENT_EXISTS",
                "The Zotero item already has a different PDF attachment",
                details={
                    "attachments": [
                        {
                            "key": _raw_key(child),
                            "filename": _item_data(child).get("filename"),
                        }
                        for child in other_pdfs
                    ]
                },
            )
        return None

    def _get_optional_item(self, item_key: str) -> dict[str, object] | None:
        try:
            return self._get_raw_item(self.write_client, item_key)
        except IntegrationError as exc:
            if exc.code == "NOT_FOUND":
                return None
            raise

    def _create_pdf_attachment_item(
        self,
        attachment_key: str,
        parent_item_key: str,
        filename: str,
        title: str,
        source_url: str | None,
        operation_id: str,
    ) -> dict[str, object]:
        item = {
            "key": attachment_key,
            "itemType": "attachment",
            "parentItem": parent_item_key,
            "linkMode": "imported_url" if source_url else "imported_file",
            "title": title,
            "accessDate": self.clock().isoformat().replace("+00:00", "Z"),
            "url": source_url or "",
            "note": "",
            "tags": [],
            "relations": {},
            "contentType": "application/pdf",
            "charset": "",
            "filename": filename,
            "md5": None,
            "mtime": None,
        }
        token = hashlib.sha256(f"{operation_id.lower()}:attachment".encode()).hexdigest()[:32]
        response = self.write_client.post(
            "/items",
            [item],
            headers={"Zotero-Write-Token": token},
        )
        created_key = _created_item_key(response, "PDF attachment")
        if created_key != attachment_key:
            raise IntegrationError(
                "BACKEND_PROTOCOL_ERROR",
                "Zotero did not preserve the requested attachment key",
            )
        return self._get_raw_item(self.write_client, attachment_key)

    @staticmethod
    def _assert_resumable_attachment(
        attachment: dict[str, object],
        parent_item_key: str,
        filename: str,
    ) -> None:
        data = _item_data(attachment)
        if (
            data.get("itemType") != "attachment"
            or data.get("parentItem") != parent_item_key
            or data.get("contentType") != "application/pdf"
            or data.get("filename") != filename
        ):
            raise IntegrationError(
                "IDEMPOTENCY_CONFLICT",
                "The PDF operation key belongs to a different Zotero attachment",
            )

    def _verify_uploaded_pdf(
        self,
        attachment_key: str,
        parent_item_key: str,
        md5: str,
    ) -> dict[str, object]:
        attachment = self._get_raw_item(self.write_client, attachment_key)
        data = _item_data(attachment)
        if (
            data.get("itemType") != "attachment"
            or data.get("parentItem") != parent_item_key
            or data.get("contentType") != "application/pdf"
            or data.get("md5") != md5
        ):
            raise IntegrationError(
                "UPLOAD_VERIFICATION_FAILED",
                "Zotero did not report the expected uploaded PDF",
            )
        return attachment

    def _pdf_result(
        self,
        attachment: dict[str, object],
        effect: str,
        file_info: dict[str, object],
        source_url: str | None,
    ) -> dict[str, object]:
        return {
            "attachment": self._normalize_item(attachment, "local"),
            "effect": effect,
            "file": {
                "size": file_info["size"],
                "md5": file_info["md5"],
                "sha256": file_info["sha256"],
            },
            "source_url": source_url,
        }

    @staticmethod
    def _pdf_partial_error(
        error: IntegrationError,
        stage: str,
        parent_item_key: str,
        attachment_key: str,
    ) -> IntegrationError:
        details = dict(error.details)
        details.update(
            {
                "stage": stage,
                "parent_item_key": parent_item_key,
                "attachment_item_key": attachment_key,
                "recoverable_with_same_operation_id": True,
            }
        )
        return IntegrationError(
            error.code,
            error.message,
            retryable=error.retryable,
            details=details,
        )

    @staticmethod
    def _validate_source_url(value: str | None) -> str | None:
        if value is None:
            return None
        value = _bounded_string(value, "source_url", 1, 2_000)
        parsed = urlsplit(value)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username
            or parsed.password
        ):
            raise IntegrationError("INVALID_ARGUMENT", "source_url must be an HTTP(S) URL")
        return value

    @staticmethod
    def _validate_tags(tags: list[str]) -> list[str]:
        if len(tags) > 20:
            raise IntegrationError("LIMIT_EXCEEDED", "At most 20 tags may be supplied")
        normalized: list[str] = []
        for tag in tags:
            normalized.append(_bounded_string(tag, "tag", 1, 200))
        return normalized

    @staticmethod
    def _validate_idempotency_key(value: str) -> None:
        if not re.fullmatch(r"[A-Fa-f0-9]{32}", value):
            raise IntegrationError(
                "INVALID_ARGUMENT",
                "idempotency_key must contain exactly 32 hexadecimal characters",
            )

    @staticmethod
    def _validate_creators(creators: list[dict[str, str]]) -> list[dict[str, str]]:
        if len(creators) > 100:
            raise IntegrationError("LIMIT_EXCEEDED", "At most 100 creators may be supplied")
        normalized: list[dict[str, str]] = []
        for index, creator in enumerate(creators):
            if not isinstance(creator, dict):
                raise IntegrationError("INVALID_ARGUMENT", f"creators[{index}] must be an object")
            unknown = set(creator) - {"creator_type", "first_name", "last_name", "name"}
            if unknown:
                raise IntegrationError(
                    "INVALID_ARGUMENT",
                    f"creators[{index}] contains unsupported fields",
                    details={"fields": sorted(unknown)},
                )
            creator_type = creator.get("creator_type", "author")
            if creator_type not in {"author", "editor", "contributor"}:
                raise IntegrationError(
                    "INVALID_ARGUMENT",
                    f"creators[{index}].creator_type is not supported",
                )
            name = creator.get("name")
            first_name = creator.get("first_name")
            last_name = creator.get("last_name")
            if name and (first_name or last_name):
                raise IntegrationError(
                    "INVALID_ARGUMENT",
                    f"creators[{index}] must use either name or first/last names",
                )
            if name:
                normalized.append(
                    {
                        "creatorType": creator_type,
                        "name": _bounded_string(name, f"creators[{index}].name", 1, 500),
                    }
                )
            elif last_name:
                entry = {
                    "creatorType": creator_type,
                    "lastName": _bounded_string(
                        last_name,
                        f"creators[{index}].last_name",
                        1,
                        500,
                    ),
                    "firstName": "",
                }
                if first_name:
                    entry["firstName"] = _bounded_string(
                        first_name,
                        f"creators[{index}].first_name",
                        1,
                        500,
                    )
                normalized.append(entry)
            else:
                raise IntegrationError(
                    "INVALID_ARGUMENT",
                    f"creators[{index}] requires name or last_name",
                )
        return normalized


def _validate_key(value: str, field: str) -> None:
    if not isinstance(value, str) or not ZOTERO_KEY_PATTERN.fullmatch(value):
        raise IntegrationError("INVALID_ARGUMENT", f"{field} is not a valid Zotero object key")


def _operation_item_key(operation_id: str, parent_item_key: str) -> str:
    digest = hashlib.sha256(f"{operation_id.lower()}:{parent_item_key}:pdf".encode()).digest()
    value = int.from_bytes(digest[:5], "big")
    return "".join(
        _ZOTERO_KEY_ALPHABET[(value >> shift) & 31]
        for shift in range(35, -1, -5)
    )


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


def _collection_keys(value: object) -> list[str]:
    if not isinstance(value, list) or any(
        not isinstance(entry, str) or not ZOTERO_KEY_PATTERN.fullmatch(entry)
        for entry in value
    ):
        raise IntegrationError(
            "BACKEND_PROTOCOL_ERROR",
            "Zotero item contains invalid collection membership data",
        )
    return list(value)


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


def _created_item_key(response: JsonResponse, label: str = "note") -> str:
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
            f"Zotero did not create the {label}",
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
