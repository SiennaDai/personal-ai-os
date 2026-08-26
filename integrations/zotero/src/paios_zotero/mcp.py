"""Dependency-free MCP stdio surface for the Zotero Integration."""

from __future__ import annotations

import copy
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from .config import DEFAULT_CONFIG_PATH, load_config
from .errors import IntegrationError
from .service import ZoteroService


SERVER_VERSION = "1.2.0"
CONTRACT_VERSION = "1.2"
LATEST_PROTOCOL_VERSION = "2025-06-18"
SUPPORTED_PROTOCOL_VERSIONS = {"2025-06-18", "2025-03-26", "2024-11-05"}
MAX_MESSAGE_BYTES = 1_000_000

SERVER_INSTRUCTIONS = (
    "Zotero is the bibliographic source of truth. These tools perform I/O, not research reasoning. "
    "Keep metadata and full text distinct and preserve item refs and versions. Writes appear only "
    "when locally enabled; updates require expected_version. PDF upload is separately gated and "
    "accepts only staged files inside configured roots. No delete or bulk mutation is exposed."
)

ERROR_SCHEMA = {
    "type": "object",
    "properties": {
        "code": {"type": "string"},
        "message": {"type": "string"},
        "retryable": {"type": "boolean"},
        "details": {"type": "object"},
    },
    "required": ["code", "message", "retryable"],
}

REF_SCHEMA = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "system": {"type": "string", "enum": ["zotero"]},
        "kind": {"type": "string", "enum": ["item", "collection"]},
        "library": {
            "type": "object",
            "properties": {
                "alias": {"type": "string"},
                "type": {"type": "string", "enum": ["user", "group"]},
                "id": {"type": "string"},
            },
            "required": ["alias", "type", "id"],
        },
        "key": {"type": "string"},
        "version": {"type": "integer"},
    },
    "required": ["id", "system", "kind", "library", "key"],
}

PROVENANCE_SCHEMA = {
    "type": "object",
    "properties": {
        "backend": {"type": "string"},
        "retrieved_at": {"type": "string"},
        "canonical_url": {"type": ["string", "null"]},
    },
    "required": ["backend", "retrieved_at"],
}

ITEM_SCHEMA = {
    "type": "object",
    "properties": {
        "ref": REF_SCHEMA,
        "item_type": {"type": "string"},
        "title": {"type": ["string", "null"]},
        "creators": {"type": "array", "items": {"type": "object"}},
        "date": {"type": ["string", "null"]},
        "parsed_date": {"type": ["string", "null"]},
        "abstract": {"type": ["string", "null"]},
        "publication": {"type": "object"},
        "identifiers": {"type": "object"},
        "url": {"type": ["string", "null"]},
        "language": {"type": ["string", "null"]},
        "pages": {"type": ["string", "null"]},
        "volume": {"type": ["string", "null"]},
        "issue": {"type": ["string", "null"]},
        "tags": {"type": "array", "items": {"type": "object"}},
        "collection_keys": {"type": "array", "items": {"type": "string"}},
        "parent_item_key": {"type": ["string", "null"]},
        "relations": {"type": "object"},
        "dates": {"type": "object"},
        "attachment": {"type": "object"},
        "note_html": {"type": ["string", "null"]},
        "annotation": {"type": "object"},
        "provenance": PROVENANCE_SCHEMA,
    },
    "required": [
        "ref",
        "item_type",
        "title",
        "creators",
        "date",
        "parsed_date",
        "abstract",
        "publication",
        "identifiers",
        "url",
        "language",
        "pages",
        "volume",
        "issue",
        "tags",
        "collection_keys",
        "parent_item_key",
        "relations",
        "dates",
        "provenance",
    ],
}

COLLECTION_SCHEMA = {
    "type": "object",
    "properties": {
        "ref": REF_SCHEMA,
        "name": {"type": "string"},
        "parent_collection_key": {"type": ["string", "null"]},
        "counts": {"type": "object"},
        "provenance": PROVENANCE_SCHEMA,
    },
    "required": ["ref", "name", "parent_collection_key", "counts", "provenance"],
}

PAGE_SCHEMA = {
    "type": "object",
    "properties": {
        "start": {"type": "integer"},
        "limit": {"type": "integer"},
        "returned": {"type": "integer"},
        "total": {"type": ["integer", "null"]},
        "has_more": {"type": "boolean"},
        "next_start": {"type": ["integer", "null"]},
    },
    "required": ["start", "limit", "returned", "total", "has_more", "next_start"],
}


def _envelope_schema(data_schema: dict[str, object]) -> dict[str, object]:
    return {
        "type": "object",
        "properties": {
            "contract_version": {"type": "string"},
            "ok": {"type": "boolean"},
            "data": data_schema,
            "error": ERROR_SCHEMA,
        },
        "required": ["contract_version", "ok"],
    }


@dataclass(frozen=True)
class ToolSpec:
    name: str
    title: str
    description: str
    input_schema: dict[str, object]
    annotations: dict[str, object]
    write: bool = False

    def effective_input_schema(self, max_page_size: int | None = None) -> dict[str, object]:
        schema = copy.deepcopy(self.input_schema)
        if max_page_size is None:
            return schema
        properties = schema.get("properties")
        limit = properties.get("limit") if isinstance(properties, dict) else None
        if isinstance(limit, dict):
            default = limit.get("default")
            if isinstance(default, int) and not isinstance(default, bool):
                limit["default"] = min(default, max_page_size)
        return schema

    def as_mcp(self, *, max_page_size: int | None = None) -> dict[str, object]:
        return {
            "name": self.name,
            "title": self.title,
            "description": self.description,
            "inputSchema": self.effective_input_schema(max_page_size),
            "outputSchema": _envelope_schema(TOOL_DATA_SCHEMAS[self.name]),
            "annotations": self.annotations,
        }


def _read_annotations(title: str) -> dict[str, object]:
    return {
        "title": title,
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    }


def _write_annotations(title: str, *, destructive: bool, idempotent: bool) -> dict[str, object]:
    return {
        "title": title,
        "readOnlyHint": False,
        "destructiveHint": destructive,
        "idempotentHint": idempotent,
        "openWorldHint": False,
    }


def _object_schema(
    properties: dict[str, object],
    required: list[str] | None = None,
) -> dict[str, object]:
    schema: dict[str, object] = {
        "type": "object",
        "properties": properties,
        "additionalProperties": False,
    }
    if required:
        schema["required"] = required
    return schema


_KEY = {"type": "string", "pattern": "^[23456789ABCDEFGHIJKLMNPQRSTUVWXYZ]{8}$"}
_LIMIT = {"type": "integer", "minimum": 1, "maximum": 100, "default": 20}
_LIMIT_50 = {"type": "integer", "minimum": 1, "maximum": 100, "default": 50}
_START = {"type": "integer", "minimum": 0, "default": 0}
_SORT = {
    "type": "string",
    "enum": [
        "dateModified",
        "dateAdded",
        "title",
        "creator",
        "date",
        "publicationTitle",
        "itemType",
    ],
    "default": "dateModified",
}
_DIRECTION = {"type": "string", "enum": ["asc", "desc"], "default": "desc"}

READ_TOOLS = [
    ToolSpec(
        "zotero_status",
        "Check Zotero status",
        "Check configuration, representative read connectivity, optional Better BibTeX readiness, and non-mutating write readiness without returning library content.",
        _object_schema({}),
        _read_annotations("Check Zotero status"),
    ),
    ToolSpec(
        "zotero_search_items",
        "Search Zotero items",
        "Search the configured Zotero library and return normalized items with canonical refs, versions, metadata provenance, and pagination. Search results are metadata, not inspected evidence.",
        _object_schema(
            {
                "query": {"type": "string", "minLength": 1, "maxLength": 500},
                "qmode": {
                    "type": "string",
                    "enum": ["titleCreatorYear", "everything"],
                    "default": "titleCreatorYear",
                },
                "item_type": {"type": "string", "minLength": 1, "maxLength": 100},
                "collection_key": _KEY,
                "tag": {"type": "string", "minLength": 1, "maxLength": 500},
                "top_level_only": {"type": "boolean", "default": True},
                "sort": _SORT,
                "direction": _DIRECTION,
                "limit": _LIMIT,
                "start": _START,
            },
            ["query"],
        ),
        _read_annotations("Search Zotero items"),
    ),
    ToolSpec(
        "zotero_get_item",
        "Get Zotero item",
        "Retrieve one Zotero item by its native eight-character key and return normalized metadata, canonical ref, current version, and provenance.",
        _object_schema({"item_key": _KEY}, ["item_key"]),
        _read_annotations("Get Zotero item"),
    ),
    ToolSpec(
        "zotero_list_collections",
        "List Zotero collections",
        "List all, top-level, or direct child collections in the configured Zotero library with canonical refs and pagination.",
        _object_schema(
            {
                "parent_collection_key": _KEY,
                "top_level_only": {"type": "boolean", "default": False},
                "limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 100,
                    "default": 50,
                },
                "start": _START,
            }
        ),
        _read_annotations("List Zotero collections"),
    ),
    ToolSpec(
        "zotero_get_collection_items",
        "Get Zotero collection items",
        "Retrieve paginated items from one collection. Returns normalized Zotero source records; it does not analyze or rank their research quality.",
        _object_schema(
            {
                "collection_key": _KEY,
                "top_level_only": {"type": "boolean", "default": True},
                "sort": _SORT,
                "direction": _DIRECTION,
                "limit": _LIMIT,
                "start": _START,
            },
            ["collection_key"],
        ),
        _read_annotations("Get Zotero collection items"),
    ),
    ToolSpec(
        "zotero_get_item_children",
        "Get Zotero item children",
        "Retrieve direct Zotero child items such as notes, attachments, or annotations, with an optional Zotero itemType filter.",
        _object_schema(
            {
                "item_key": _KEY,
                "item_type": {"type": "string", "minLength": 1, "maxLength": 100},
                "limit": _LIMIT_50,
                "start": _START,
            },
            ["item_key"],
        ),
        _read_annotations("Get Zotero item children"),
    ),
    ToolSpec(
        "zotero_get_annotations",
        "Get Zotero annotations",
        "Retrieve normalized Zotero PDF annotations for a bibliographic item or attachment. Discovery is bounded and paginated.",
        _object_schema(
            {"item_key": _KEY, "limit": _LIMIT_50, "start": _START},
            ["item_key"],
        ),
        _read_annotations("Get Zotero annotations"),
    ),
    ToolSpec(
        "zotero_get_fulltext",
        "Get Zotero indexed full text",
        "Read a bounded character slice of Zotero-indexed PDF full text. If an item has multiple PDFs, first choose an explicit attachment_key.",
        _object_schema(
            {
                "item_key": _KEY,
                "attachment_key": _KEY,
                "offset": {"type": "integer", "minimum": 0, "default": 0},
                "max_chars": {"type": "integer", "minimum": 1, "maximum": 100000},
            },
            ["item_key"],
        ),
        _read_annotations("Get Zotero indexed full text"),
    ),
    ToolSpec(
        "zotero_get_citation_key",
        "Get Better BibTeX citation key",
        "Resolve the current Better BibTeX citation key for one Zotero item. This optional read requires Better BibTeX to be enabled and running.",
        _object_schema({"item_key": _KEY}, ["item_key"]),
        _read_annotations("Get Better BibTeX citation key"),
    ),
]

WRITE_TOOLS = [
    ToolSpec(
        "zotero_create_bibliographic_item",
        "Create Zotero bibliographic item",
        "Create one paper metadata record in an allowed collection through the Zotero 10 local API. This does not download or attach a PDF. Search for an existing DOI or exact title before creating a duplicate.",
        _object_schema(
            {
                "item_type": {
                    "type": "string",
                    "enum": [
                        "journalArticle",
                        "conferencePaper",
                        "preprint",
                        "bookSection",
                        "thesis",
                        "report",
                    ],
                },
                "title": {"type": "string", "minLength": 1, "maxLength": 2000},
                "collection_key": _KEY,
                "idempotency_key": {"type": "string", "pattern": "^[A-Fa-f0-9]{32}$"},
                "creators": {
                    "type": "array",
                    "maxItems": 100,
                    "default": [],
                    "items": _object_schema(
                        {
                            "creator_type": {
                                "type": "string",
                                "enum": ["author", "editor", "contributor"],
                                "default": "author",
                            },
                            "first_name": {"type": "string", "minLength": 1, "maxLength": 500},
                            "last_name": {"type": "string", "minLength": 1, "maxLength": 500},
                            "name": {"type": "string", "minLength": 1, "maxLength": 500},
                        }
                    ),
                },
                "container_title": {"type": "string", "minLength": 1, "maxLength": 2000},
                "fields": _object_schema(
                    {
                        "abstract": {"type": "string", "minLength": 1, "maxLength": 20000},
                        "date": {"type": "string", "minLength": 1, "maxLength": 2000},
                        "url": {"type": "string", "minLength": 1, "maxLength": 2000},
                        "doi": {"type": "string", "minLength": 1, "maxLength": 2000},
                        "language": {"type": "string", "minLength": 1, "maxLength": 2000},
                        "volume": {"type": "string", "minLength": 1, "maxLength": 200},
                        "issue": {"type": "string", "minLength": 1, "maxLength": 200},
                        "pages": {"type": "string", "minLength": 1, "maxLength": 500},
                        "extra": {"type": "string", "minLength": 1, "maxLength": 20000},
                    }
                ),
                "tags": {
                    "type": "array",
                    "items": {"type": "string", "minLength": 1, "maxLength": 200},
                    "maxItems": 20,
                    "default": [],
                },
            },
            ["item_type", "title", "collection_key", "idempotency_key"],
        ),
        _write_annotations("Create Zotero bibliographic item", destructive=False, idempotent=False),
        write=True,
    ),
    ToolSpec(
        "zotero_create_child_note",
        "Create Zotero child note",
        "Create one Zotero note under an existing in-scope item through the Zotero 10 local API. Requires a configured write scope and a caller-provided idempotency key.",
        _object_schema(
            {
                "parent_item_key": _KEY,
                "note_html": {"type": "string", "minLength": 1, "maxLength": 200000},
                "idempotency_key": {"type": "string", "pattern": "^[A-Fa-f0-9]{32}$"},
                "tags": {
                    "type": "array",
                    "items": {"type": "string", "minLength": 1, "maxLength": 200},
                    "maxItems": 20,
                    "default": [],
                },
            },
            ["parent_item_key", "note_html", "idempotency_key"],
        ),
        _write_annotations("Create Zotero child note", destructive=False, idempotent=False),
        write=True,
    ),
    ToolSpec(
        "zotero_update_note",
        "Update Zotero note",
        "Replace one in-scope Zotero note body through the Zotero 10 local API using an exact expected_version precondition.",
        _object_schema(
            {
                "note_item_key": _KEY,
                "expected_version": {"type": "integer", "minimum": 0},
                "note_html": {"type": "string", "minLength": 1, "maxLength": 200000},
            },
            ["note_item_key", "expected_version", "note_html"],
        ),
        _write_annotations("Update Zotero note", destructive=True, idempotent=True),
        write=True,
    ),
    ToolSpec(
        "zotero_update_item_fields",
        "Update Zotero metadata fields",
        "Patch up to eight allowlisted scalar fields on one in-scope bibliographic item using an exact expected_version. Arrays, creators, tags, collections, files, delete, and bulk mutation are not supported.",
        _object_schema(
            {
                "item_key": _KEY,
                "expected_version": {"type": "integer", "minimum": 0},
                "fields": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "maxLength": 2000},
                        "abstract": {"type": "string", "maxLength": 20000},
                        "date": {"type": "string", "maxLength": 2000},
                        "short_title": {"type": "string", "maxLength": 2000},
                        "url": {"type": "string", "maxLength": 2000},
                        "doi": {"type": "string", "maxLength": 2000},
                        "isbn": {"type": "string", "maxLength": 2000},
                        "issn": {"type": "string", "maxLength": 2000},
                        "language": {"type": "string", "maxLength": 2000},
                        "rights": {"type": "string", "maxLength": 2000},
                        "extra": {"type": "string", "maxLength": 20000},
                    },
                    "additionalProperties": False,
                    "minProperties": 1,
                    "maxProperties": 8,
                },
            },
            ["item_key", "expected_version", "fields"],
        ),
        _write_annotations("Update Zotero metadata fields", destructive=True, idempotent=True),
        write=True,
    ),
    ToolSpec(
        "zotero_add_item_to_collection",
        "Add Zotero item to collection",
        "Add one bibliographic item to an allowed collection without removing any existing collection membership. Requires the exact current local expected_version.",
        _object_schema(
            {
                "item_key": _KEY,
                "expected_version": {"type": "integer", "minimum": 0},
                "collection_key": _KEY,
            },
            ["item_key", "expected_version", "collection_key"],
        ),
        _write_annotations("Add Zotero item to collection", destructive=False, idempotent=True),
        write=True,
    ),
]

ATTACHMENT_WRITE_TOOLS = [
    ToolSpec(
        "zotero_import_pdf_attachment",
        "Import Zotero PDF attachment",
        "Import one staged local PDF as a stored child attachment of an in-scope bibliographic item. The file must be inside a configured import root. The operation is resumable with the same operation_id and never replaces an existing PDF.",
        _object_schema(
            {
                "parent_item_key": _KEY,
                "expected_parent_version": {"type": "integer", "minimum": 0},
                "pdf_path": {"type": "string", "minLength": 1, "maxLength": 4096},
                "operation_id": {"type": "string", "pattern": "^[A-Fa-f0-9]{32}$"},
                "source_url": {"type": "string", "minLength": 1, "maxLength": 2000},
                "title": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 2000,
                    "default": "Full Text PDF",
                },
            },
            ["parent_item_key", "expected_parent_version", "pdf_path", "operation_id"],
        ),
        _write_annotations("Import Zotero PDF attachment", destructive=False, idempotent=True),
        write=True,
    ),
]

_ITEMS_DATA_SCHEMA = {
    "type": "object",
    "properties": {
        "items": {"type": "array", "items": ITEM_SCHEMA},
        "page": PAGE_SCHEMA,
    },
    "required": ["items", "page"],
}

_COLLECTIONS_DATA_SCHEMA = {
    "type": "object",
    "properties": {
        "collections": {"type": "array", "items": COLLECTION_SCHEMA},
        "page": PAGE_SCHEMA,
    },
    "required": ["collections", "page"],
}

TOOL_DATA_SCHEMAS: dict[str, dict[str, object]] = {
    "zotero_status": {
        "type": "object",
        "properties": {
            "overall_ok": {"type": "boolean"},
            "checked_at": {"type": "string"},
            "contract_version": {"type": "string"},
            "configuration": {"type": "object"},
            "read": {"type": "object"},
            "better_bibtex": {"type": "object"},
            "write": {"type": "object"},
        },
        "required": [
            "overall_ok",
            "checked_at",
            "contract_version",
            "configuration",
            "read",
            "better_bibtex",
            "write",
        ],
    },
    "zotero_search_items": _ITEMS_DATA_SCHEMA,
    "zotero_get_item": {
        "type": "object",
        "properties": {"item": ITEM_SCHEMA},
        "required": ["item"],
    },
    "zotero_list_collections": _COLLECTIONS_DATA_SCHEMA,
    "zotero_get_collection_items": _ITEMS_DATA_SCHEMA,
    "zotero_get_item_children": _ITEMS_DATA_SCHEMA,
    "zotero_get_annotations": {
        "type": "object",
        "properties": {
            "annotations": {"type": "array", "items": ITEM_SCHEMA},
            "page": PAGE_SCHEMA,
            "warnings": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["annotations", "page"],
    },
    "zotero_get_fulltext": {
        "type": "object",
        "properties": {
            "attachment_ref": REF_SCHEMA,
            "content": {"type": "string"},
            "offset": {"type": "integer"},
            "returned_chars": {"type": "integer"},
            "total_chars": {"type": "integer"},
            "truncated": {"type": "boolean"},
            "next_offset": {"type": ["integer", "null"]},
            "indexed_pages": {"type": ["integer", "null"]},
            "total_pages": {"type": ["integer", "null"]},
            "provenance": PROVENANCE_SCHEMA,
        },
        "required": [
            "attachment_ref",
            "content",
            "offset",
            "returned_chars",
            "total_chars",
            "truncated",
            "next_offset",
            "indexed_pages",
            "total_pages",
            "provenance",
        ],
    },
    "zotero_get_citation_key": {
        "type": "object",
        "properties": {
            "item_ref": REF_SCHEMA,
            "citation_key": {"type": "string"},
            "provenance": PROVENANCE_SCHEMA,
        },
        "required": ["item_ref", "citation_key", "provenance"],
    },
    "zotero_create_bibliographic_item": {
        "type": "object",
        "properties": {
            "created": ITEM_SCHEMA,
            "effect": {"type": "string", "enum": ["created_bibliographic_item"]},
            "destination_collection_ref": REF_SCHEMA,
        },
        "required": ["created", "effect", "destination_collection_ref"],
    },
    "zotero_create_child_note": {
        "type": "object",
        "properties": {
            "created": ITEM_SCHEMA,
            "effect": {"type": "string", "enum": ["created_child_note"]},
        },
        "required": ["created", "effect"],
    },
    "zotero_update_note": {
        "type": "object",
        "properties": {
            "updated": ITEM_SCHEMA,
            "effect": {"type": "string", "enum": ["updated_note"]},
        },
        "required": ["updated", "effect"],
    },
    "zotero_update_item_fields": {
        "type": "object",
        "properties": {
            "updated": ITEM_SCHEMA,
            "effect": {"type": "string", "enum": ["updated_scalar_metadata"]},
            "changed_fields": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["updated", "effect", "changed_fields"],
    },
    "zotero_add_item_to_collection": {
        "type": "object",
        "properties": {
            "updated": ITEM_SCHEMA,
            "effect": {
                "type": "string",
                "enum": ["added_to_collection", "already_in_collection"],
            },
            "destination_collection_ref": REF_SCHEMA,
        },
        "required": ["updated", "effect", "destination_collection_ref"],
    },
    "zotero_import_pdf_attachment": {
        "type": "object",
        "properties": {
            "attachment": ITEM_SCHEMA,
            "effect": {
                "type": "string",
                "enum": ["imported_pdf_attachment", "pdf_already_attached"],
            },
            "file": {
                "type": "object",
                "properties": {
                    "size": {"type": "integer"},
                    "md5": {"type": "string"},
                    "sha256": {"type": "string"},
                },
                "required": ["size", "md5", "sha256"],
            },
            "source_url": {"type": ["string", "null"]},
        },
        "required": ["attachment", "effect", "file", "source_url"],
    },
}

class RpcError(Exception):
    def __init__(self, code: int, message: str, data: object | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.data = data


class ZoteroMcpServer:
    def __init__(self, config_path: str | Path = DEFAULT_CONFIG_PATH) -> None:
        self.config_path = str(Path(config_path).expanduser())
        self.initialized = False
        self._service: ZoteroService | None = None

    def available_tools(self) -> list[ToolSpec]:
        tools = list(READ_TOOLS)
        try:
            config = load_config(self.config_path)
        except IntegrationError:
            return tools
        if config.write_enabled:
            tools.extend(WRITE_TOOLS)
        if config.attachment_upload_enabled:
            tools.extend(ATTACHMENT_WRITE_TOOLS)
        return tools

    def tool_documents(self) -> list[dict[str, object]]:
        try:
            max_page_size = load_config(self.config_path).max_page_size
        except IntegrationError:
            max_page_size = None
        return [
            tool.as_mcp(max_page_size=max_page_size)
            for tool in self.available_tools()
        ]

    def run(self) -> None:
        for raw_line in sys.stdin.buffer:
            if len(raw_line) > MAX_MESSAGE_BYTES:
                self._write_error(None, -32600, "MCP message exceeds the server byte limit")
                continue
            try:
                message = json.loads(raw_line.decode("utf-8"))
                response = self.handle(message)
            except (UnicodeDecodeError, json.JSONDecodeError):
                self._write_error(None, -32700, "Invalid JSON")
                continue
            except Exception as exc:  # pragma: no cover - final transport guard
                print(f"Unexpected MCP server error: {type(exc).__name__}", file=sys.stderr)
                self._write_error(None, -32603, "Internal MCP server error")
                continue
            if response is not None:
                self._write(response)

    def handle(self, message: object) -> dict[str, object] | None:
        if not isinstance(message, dict) or message.get("jsonrpc") != "2.0":
            return self._error_response(None, -32600, "Invalid JSON-RPC request")
        method = message.get("method")
        if not isinstance(method, str):
            return self._error_response(message.get("id"), -32600, "Request method is missing")
        is_notification = "id" not in message
        request_id = message.get("id")
        try:
            if method == "initialize":
                if is_notification:
                    raise RpcError(-32600, "initialize must be a request")
                result = self._initialize(message.get("params"))
            elif method == "notifications/initialized":
                self.initialized = True
                return None
            elif method in {"notifications/cancelled", "notifications/progress"}:
                return None
            elif method == "ping":
                result = {}
            elif method == "tools/list":
                result = self._list_tools(message.get("params"))
            elif method == "tools/call":
                result = self._call_tool(message.get("params"))
            else:
                if is_notification:
                    return None
                raise RpcError(-32601, "Method not found")
        except RpcError as exc:
            if is_notification:
                return None
            return self._error_response(request_id, exc.code, exc.message, exc.data)
        if is_notification:
            return None
        return {"jsonrpc": "2.0", "id": request_id, "result": result}

    def _initialize(self, params: object) -> dict[str, object]:
        if not isinstance(params, dict):
            raise RpcError(-32602, "initialize params must be an object")
        requested = params.get("protocolVersion")
        protocol_version = (
            requested if requested in SUPPORTED_PROTOCOL_VERSIONS else LATEST_PROTOCOL_VERSION
        )
        return {
            "protocolVersion": protocol_version,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {
                "name": "personal-ai-os-zotero",
                "title": "Personal AI-OS Zotero Integration",
                "version": SERVER_VERSION,
            },
            "instructions": SERVER_INSTRUCTIONS,
        }

    def _list_tools(self, params: object) -> dict[str, object]:
        if params is not None and not isinstance(params, dict):
            raise RpcError(-32602, "tools/list params must be an object")
        if isinstance(params, dict) and params.get("cursor"):
            raise RpcError(-32602, "This server does not paginate its tool inventory")
        return {"tools": self.tool_documents()}

    def _call_tool(self, params: object) -> dict[str, object]:
        if not isinstance(params, dict):
            raise RpcError(-32602, "tools/call params must be an object")
        name = params.get("name")
        arguments = params.get("arguments", {})
        if not isinstance(name, str) or not isinstance(arguments, dict):
            raise RpcError(-32602, "tools/call requires a tool name and object arguments")
        available = {tool.name: tool for tool in self.available_tools()}
        spec = available.get(name)
        if spec is None:
            raise RpcError(-32602, "Unknown or disabled Zotero tool")
        try:
            config = load_config(self.config_path)
            validate_value(
                arguments,
                spec.effective_input_schema(config.max_page_size),
                "arguments",
            )
            if self._service is None or self._service.config != config:
                self._service = ZoteroService(config)
            service = self._service
            data = self._dispatch(service, name, arguments)
            envelope = {"contract_version": CONTRACT_VERSION, "ok": True, "data": data}
            return _tool_result(envelope, is_error=False)
        except IntegrationError as exc:
            envelope = {
                "contract_version": CONTRACT_VERSION,
                "ok": False,
                "error": exc.as_dict(),
            }
            return _tool_result(envelope, is_error=True)
        except Exception as exc:  # pragma: no cover - does not expose internals to the model
            print(f"Unexpected tool error in {name}: {type(exc).__name__}", file=sys.stderr)
            envelope = {
                "contract_version": CONTRACT_VERSION,
                "ok": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "The Zotero Integration encountered an internal error",
                    "retryable": False,
                },
            }
            return _tool_result(envelope, is_error=True)

    @staticmethod
    def _dispatch(service: ZoteroService, name: str, args: dict[str, Any]) -> dict[str, object]:
        default_page_limit = min(20, service.config.max_page_size)
        default_scan_limit = min(50, service.config.max_page_size)

        def page_limit(default: int) -> int:
            return min(args.get("limit", default), service.config.max_page_size)

        if name == "zotero_status":
            return service.status()
        if name == "zotero_search_items":
            return service.search_items(
                args["query"],
                qmode=args.get("qmode", "titleCreatorYear"),
                item_type=args.get("item_type"),
                collection_key=args.get("collection_key"),
                tag=args.get("tag"),
                top_level_only=args.get("top_level_only", True),
                sort=args.get("sort", "dateModified"),
                direction=args.get("direction", "desc"),
                limit=page_limit(default_page_limit),
                start=args.get("start", 0),
            )
        if name == "zotero_get_item":
            return service.get_item(args["item_key"])
        if name == "zotero_list_collections":
            return service.list_collections(
                parent_collection_key=args.get("parent_collection_key"),
                top_level_only=args.get("top_level_only", False),
                limit=page_limit(default_scan_limit),
                start=args.get("start", 0),
            )
        if name == "zotero_get_collection_items":
            return service.get_collection_items(
                args["collection_key"],
                top_level_only=args.get("top_level_only", True),
                sort=args.get("sort", "dateModified"),
                direction=args.get("direction", "desc"),
                limit=page_limit(default_page_limit),
                start=args.get("start", 0),
            )
        if name == "zotero_get_item_children":
            return service.get_item_children(
                args["item_key"],
                item_type=args.get("item_type"),
                limit=page_limit(default_scan_limit),
                start=args.get("start", 0),
            )
        if name == "zotero_get_annotations":
            return service.get_annotations(
                args["item_key"],
                limit=page_limit(default_scan_limit),
                start=args.get("start", 0),
            )
        if name == "zotero_get_fulltext":
            return service.get_fulltext(
                args["item_key"],
                attachment_key=args.get("attachment_key"),
                offset=args.get("offset", 0),
                max_chars=args.get("max_chars"),
            )
        if name == "zotero_get_citation_key":
            return service.get_citation_key(args["item_key"])
        if name == "zotero_create_bibliographic_item":
            return service.create_bibliographic_item(
                args["item_type"],
                args["title"],
                args["collection_key"],
                args["idempotency_key"],
                creators=args.get("creators", []),
                container_title=args.get("container_title"),
                fields=args.get("fields", {}),
                tags=args.get("tags", []),
            )
        if name == "zotero_create_child_note":
            return service.create_child_note(
                args["parent_item_key"],
                args["note_html"],
                args["idempotency_key"],
                tags=args.get("tags", []),
            )
        if name == "zotero_update_note":
            return service.update_note(
                args["note_item_key"],
                args["expected_version"],
                args["note_html"],
            )
        if name == "zotero_update_item_fields":
            return service.update_item_fields(
                args["item_key"],
                args["expected_version"],
                args["fields"],
            )
        if name == "zotero_add_item_to_collection":
            return service.add_item_to_collection(
                args["item_key"],
                args["expected_version"],
                args["collection_key"],
            )
        if name == "zotero_import_pdf_attachment":
            return service.import_pdf_attachment(
                args["parent_item_key"],
                args["expected_parent_version"],
                args["pdf_path"],
                args["operation_id"],
                source_url=args.get("source_url"),
                title=args.get("title", "Full Text PDF"),
            )
        raise IntegrationError("INTERNAL_ERROR", "Tool dispatch is not implemented")

    def _write(self, response: dict[str, object]) -> None:
        encoded = json.dumps(response, ensure_ascii=False, separators=(",", ":"))
        sys.stdout.write(encoded + "\n")
        sys.stdout.flush()

    def _write_error(self, request_id: object, code: int, message: str) -> None:
        self._write(self._error_response(request_id, code, message))

    @staticmethod
    def _error_response(
        request_id: object,
        code: int,
        message: str,
        data: object | None = None,
    ) -> dict[str, object]:
        error: dict[str, object] = {"code": code, "message": message}
        if data is not None:
            error["data"] = data
        return {"jsonrpc": "2.0", "id": request_id, "error": error}


def _tool_result(envelope: dict[str, object], *, is_error: bool) -> dict[str, object]:
    text = json.dumps(envelope, ensure_ascii=False, separators=(",", ":"))
    return {
        "content": [{"type": "text", "text": text}],
        "structuredContent": envelope,
        "isError": is_error,
    }


def validate_value(value: object, schema: dict[str, object], path: str) -> None:
    expected_type = schema.get("type")
    if expected_type == "object":
        if not isinstance(value, dict):
            _argument_error(path, "must be an object")
        properties = schema.get("properties", {})
        required = schema.get("required", [])
        for key in required if isinstance(required, list) else []:
            if key not in value:
                _argument_error(f"{path}.{key}", "is required")
        additional = schema.get("additionalProperties", True)
        for key, entry in value.items():
            if isinstance(properties, dict) and key in properties:
                child_schema = properties[key]
            elif additional is False:
                _argument_error(f"{path}.{key}", "is not allowed")
            elif isinstance(additional, dict):
                child_schema = additional
            else:
                continue
            if isinstance(child_schema, dict):
                validate_value(entry, child_schema, f"{path}.{key}")
        size = len(value)
        if isinstance(schema.get("minProperties"), int) and size < schema["minProperties"]:
            _argument_error(path, "has too few properties")
        if isinstance(schema.get("maxProperties"), int) and size > schema["maxProperties"]:
            _argument_error(path, "has too many properties")
    elif expected_type == "array":
        if not isinstance(value, list):
            _argument_error(path, "must be an array")
        if isinstance(schema.get("maxItems"), int) and len(value) > schema["maxItems"]:
            _argument_error(path, "has too many entries")
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, entry in enumerate(value):
                validate_value(entry, item_schema, f"{path}[{index}]")
    elif expected_type == "string":
        if not isinstance(value, str):
            _argument_error(path, "must be a string")
        if isinstance(schema.get("minLength"), int) and len(value) < schema["minLength"]:
            _argument_error(path, "is too short")
        if isinstance(schema.get("maxLength"), int) and len(value) > schema["maxLength"]:
            _argument_error(path, "is too long")
        pattern = schema.get("pattern")
        if isinstance(pattern, str) and re.fullmatch(pattern, value) is None:
            _argument_error(path, "has an invalid format")
    elif expected_type == "integer":
        if isinstance(value, bool) or not isinstance(value, int):
            _argument_error(path, "must be an integer")
        if isinstance(schema.get("minimum"), int) and value < schema["minimum"]:
            _argument_error(path, "is below the minimum")
        if isinstance(schema.get("maximum"), int) and value > schema["maximum"]:
            _argument_error(path, "is above the maximum")
    elif expected_type == "boolean" and not isinstance(value, bool):
        _argument_error(path, "must be a boolean")
    enum = schema.get("enum")
    if isinstance(enum, list) and value not in enum:
        _argument_error(path, "is not an allowed value")


def _argument_error(path: str, message: str) -> None:
    raise IntegrationError("INVALID_ARGUMENT", f"{path} {message}")
