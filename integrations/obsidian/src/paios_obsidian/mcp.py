"""Dependency-free MCP stdio surface for the Obsidian Integration."""

from __future__ import annotations

import copy
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import DEFAULT_CONFIG_PATH, load_config
from .errors import IntegrationError
from .service import ObsidianService


SERVER_VERSION = "1.0.0"
CONTRACT_VERSION = "1.0"
LATEST_PROTOCOL_VERSION = "2025-06-18"
SUPPORTED_PROTOCOL_VERSIONS = {"2025-06-18", "2025-03-26", "2024-11-05"}
MAX_MESSAGE_BYTES = 12_000_000

SERVER_INSTRUCTIONS = (
    "Obsidian is the long-term knowledge layer, not the active Project. Use these tools only for "
    "external Vault I/O; Agents and Skills own content and knowledge decisions. Keep Project work "
    "in the Project by default. Publication needs explicit user intent. Preserve note refs and "
    "SHA-256 revisions. Never retry a revision conflict by silently overwriting. No delete, move, "
    "rename, append, property/task mutation, attachment write, arbitrary CLI, or bulk operation exists."
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

NOTE_SCHEMA = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "system": {"type": "string", "enum": ["obsidian"]},
        "kind": {"type": "string", "enum": ["note"]},
        "vault": {
            "type": "object",
            "properties": {"alias": {"type": "string"}},
            "required": ["alias"],
        },
        "path": {"type": "string"},
        "revision": {"type": "string"},
        "size_bytes": {"type": "integer"},
        "modified_ns": {"type": "integer"},
    },
    "required": [
        "id",
        "system",
        "kind",
        "vault",
        "path",
        "revision",
        "size_bytes",
        "modified_ns",
    ],
}

PAGE_SCHEMA = {
    "type": "object",
    "properties": {
        "start": {"type": "integer"},
        "limit": {"type": "integer"},
        "returned": {"type": "integer"},
        "has_more": {"type": "boolean"},
        "next_start": {"type": ["integer", "null"]},
    },
    "required": ["start", "limit", "returned", "has_more", "next_start"],
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

    def effective_input_schema(
        self,
        *,
        max_page_size: int | None = None,
        max_read_chars: int | None = None,
    ) -> dict[str, object]:
        schema = copy.deepcopy(self.input_schema)
        properties = schema.get("properties")
        if not isinstance(properties, dict):
            return schema
        if max_page_size is not None and isinstance(properties.get("limit"), dict):
            default = properties["limit"].get("default")
            if isinstance(default, int) and not isinstance(default, bool):
                properties["limit"]["default"] = min(default, max_page_size)
        if max_read_chars is not None and isinstance(properties.get("max_chars"), dict):
            properties["max_chars"]["default"] = max_read_chars
        return schema

    def as_mcp(
        self,
        *,
        max_page_size: int | None = None,
        max_read_chars: int | None = None,
    ) -> dict[str, object]:
        return {
            "name": self.name,
            "title": self.title,
            "description": self.description,
            "inputSchema": self.effective_input_schema(
                max_page_size=max_page_size,
                max_read_chars=max_read_chars,
            ),
            "outputSchema": _envelope_schema(TOOL_DATA_SCHEMAS[self.name]),
            "annotations": self.annotations,
        }


def _object_schema(
    properties: dict[str, object],
    required: list[str] | None = None,
) -> dict[str, object]:
    result: dict[str, object] = {
        "type": "object",
        "properties": properties,
        "additionalProperties": False,
    }
    if required:
        result["required"] = required
    return result


def _read_annotations(title: str) -> dict[str, object]:
    return {
        "title": title,
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    }


def _write_annotations(title: str, *, destructive: bool) -> dict[str, object]:
    return {
        "title": title,
        "readOnlyHint": False,
        "destructiveHint": destructive,
        "idempotentHint": True,
        "openWorldHint": False,
    }


_PATH = {"type": "string", "minLength": 1, "maxLength": 2_000}
_REF = {"type": "string", "minLength": 1, "maxLength": 6_000}
_START = {"type": "integer", "minimum": 0, "default": 0}
_LIMIT = {"type": "integer", "minimum": 1, "maximum": 100, "default": 50}
_CONTENT = {"type": "string", "maxLength": 10_000_000}
_EXPECTED_REVISION = {"type": "string", "pattern": "^sha256:[0-9a-f]{64}$"}

READ_TOOLS = [
    ToolSpec(
        "obsidian_status",
        "Check Obsidian status",
        "Check confined Vault access, aggregate note counts, optional official CLI semantics, and default-off write readiness without returning note paths or content.",
        _object_schema({}),
        _read_annotations("Check Obsidian status"),
    ),
    ToolSpec(
        "obsidian_list_notes",
        "List Obsidian notes",
        "List bounded Markdown note summaries in stable Vault-relative path order. Returns exact refs and SHA-256 revisions but no note content.",
        _object_schema({"folder": _PATH, "start": _START, "limit": _LIMIT}),
        _read_annotations("List Obsidian notes"),
    ),
    ToolSpec(
        "obsidian_search_notes",
        "Search Obsidian notes",
        "Run either bounded literal Markdown search or official Obsidian query search. Select mode explicitly; Obsidian mode never silently falls back.",
        _object_schema(
            {
                "query": {"type": "string", "minLength": 1, "maxLength": 1_000},
                "mode": {"type": "string", "enum": ["literal", "obsidian"]},
                "folder": _PATH,
                "case_sensitive": {"type": "boolean", "default": False},
                "include_excerpt": {"type": "boolean", "default": False},
                "start": _START,
                "limit": _LIMIT,
            },
            ["query", "mode"],
        ),
        _read_annotations("Search Obsidian notes"),
    ),
    ToolSpec(
        "obsidian_get_note",
        "Read exact Obsidian note",
        "Read one exact Markdown note by canonical ref or Vault-relative path. Returns a bounded content slice, full-file SHA-256 revision, and optional official-CLI properties.",
        _object_schema(
            {
                "ref": _REF,
                "path": _PATH,
                "offset": {"type": "integer", "minimum": 0, "default": 0},
                "max_chars": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 200_000,
                    "default": 50_000,
                },
                "include_properties": {"type": "boolean", "default": False},
            }
        ),
        _read_annotations("Read exact Obsidian note"),
    ),
    ToolSpec(
        "obsidian_get_links",
        "Read Obsidian links",
        "Use the official Obsidian semantic index to return bounded outgoing links, backlinks, or both for one exact note, preserving resolved and unresolved state.",
        _object_schema(
            {
                "ref": _REF,
                "path": _PATH,
                "direction": {
                    "type": "string",
                    "enum": ["outgoing", "backlinks", "both"],
                    "default": "both",
                },
                "limit": {"type": "integer", "minimum": 1, "maximum": 1_000, "default": 200},
            }
        ),
        _read_annotations("Read Obsidian links"),
    ),
]

WRITE_TOOLS = [
    ToolSpec(
        "obsidian_publish_note",
        "Publish new Obsidian note",
        "Create one complete UTF-8 Markdown note inside an allowlisted non-root write directory. Never overwrites different existing content; an identical retry is already_present.",
        _object_schema({"path": _PATH, "content": _CONTENT}, ["path", "content"]),
        _write_annotations("Publish new Obsidian note", destructive=False),
        write=True,
    ),
    ToolSpec(
        "obsidian_update_note",
        "Replace Obsidian note",
        "Replace one complete UTF-8 Markdown note inside an allowlisted write directory only when expected_revision matches its exact current SHA-256.",
        _object_schema(
            {
                "ref": _REF,
                "path": _PATH,
                "content": _CONTENT,
                "expected_revision": _EXPECTED_REVISION,
            },
            ["content", "expected_revision"],
        ),
        _write_annotations("Replace Obsidian note", destructive=True),
        write=True,
    ),
]


_MATCH_SCHEMA = {
    "type": "object",
    "properties": {
        "note": NOTE_SCHEMA,
        "excerpt": {"type": "string"},
        "excerpt_start": {"type": "integer"},
        "excerpt_truncated": {"type": "boolean"},
    },
    "required": ["note"],
}

_LINK_SCHEMA = {
    "type": "object",
    "properties": {
        "target": {"type": "string"},
        "resolved": {"type": "boolean"},
        "note": NOTE_SCHEMA,
        "count": {"type": "integer"},
    },
    "required": ["target", "resolved"],
}

TOOL_DATA_SCHEMAS: dict[str, dict[str, object]] = {
    "obsidian_status": {
        "type": "object",
        "properties": {
            "state": {"type": "string"},
            "overall_ok": {"type": "boolean"},
            "vault_alias": {"type": "string"},
            "configuration": {"type": "object"},
            "filesystem": {"type": "object"},
            "cli": {"type": "object"},
            "writes": {"type": "object"},
            "counts": {"type": "object"},
        },
        "required": ["state", "vault_alias", "filesystem", "cli", "writes", "counts"],
    },
    "obsidian_list_notes": {
        "type": "object",
        "properties": {
            "notes": {"type": "array", "items": NOTE_SCHEMA},
            "page": PAGE_SCHEMA,
            "truncated": {"type": "boolean"},
            "retrieved_at": {"type": "string"},
        },
        "required": ["notes", "page", "retrieved_at"],
    },
    "obsidian_search_notes": {
        "type": "object",
        "properties": {
            "mode": {"type": "string"},
            "query": {"type": "string"},
            "matches": {"type": "array", "items": _MATCH_SCHEMA},
            "page": PAGE_SCHEMA,
            "truncated": {"type": "boolean"},
            "scanned_files": {"type": "integer"},
            "scanned_bytes": {"type": "integer"},
            "skipped_files": {"type": "integer"},
            "retrieved_at": {"type": "string"},
        },
        "required": ["mode", "query", "matches", "page", "truncated", "retrieved_at"],
    },
    "obsidian_get_note": {
        "type": "object",
        "properties": {
            "note": NOTE_SCHEMA,
            "content": {"type": "string"},
            "content_page": {"type": "object"},
            "properties": {"type": "object"},
            "provenance": {"type": "object"},
            "retrieved_at": {"type": "string"},
        },
        "required": ["note", "content", "content_page", "provenance", "retrieved_at"],
    },
    "obsidian_get_links": {
        "type": "object",
        "properties": {
            "note": NOTE_SCHEMA,
            "outgoing": {"type": "array", "items": _LINK_SCHEMA},
            "backlinks": {"type": "array", "items": _LINK_SCHEMA},
            "truncated": {"type": "boolean"},
            "provenance": {"type": "object"},
            "retrieved_at": {"type": "string"},
        },
        "required": ["note", "truncated", "provenance", "retrieved_at"],
    },
    "obsidian_publish_note": {
        "type": "object",
        "properties": {
            "state": {"type": "string", "enum": ["created", "already_present"]},
            "note": NOTE_SCHEMA,
            "semantic_index": {"type": "string"},
        },
        "required": ["state", "note", "semantic_index"],
    },
    "obsidian_update_note": {
        "type": "object",
        "properties": {
            "state": {"type": "string", "enum": ["updated", "already_current"]},
            "note": NOTE_SCHEMA,
            "previous_revision": {"type": "string"},
            "semantic_index": {"type": "string"},
        },
        "required": ["state", "note", "previous_revision", "semantic_index"],
    },
}


class RpcError(Exception):
    def __init__(self, code: int, message: str, data: object | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.data = data


class ObsidianMcpServer:
    def __init__(self, config_path: str | Path = DEFAULT_CONFIG_PATH) -> None:
        self.config_path = str(Path(config_path).expanduser())
        self.initialized = False
        self._service_signature: tuple[int, int] | None = None
        self._service: ObsidianService | None = None

    def available_tools(self) -> list[ToolSpec]:
        tools = list(READ_TOOLS)
        try:
            config = load_config(self.config_path)
        except IntegrationError:
            return tools
        if config.write_enabled:
            tools.extend(WRITE_TOOLS)
        return tools

    def tool_documents(self) -> list[dict[str, object]]:
        try:
            config = load_config(self.config_path)
            max_page_size = config.max_page_size
            max_read_chars = config.max_read_chars
        except IntegrationError:
            max_page_size = None
            max_read_chars = None
        return [
            tool.as_mcp(
                max_page_size=max_page_size,
                max_read_chars=max_read_chars,
            )
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
        protocol_version = requested if requested in SUPPORTED_PROTOCOL_VERSIONS else LATEST_PROTOCOL_VERSION
        return {
            "protocolVersion": protocol_version,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {
                "name": "personal-ai-os-obsidian",
                "title": "Personal AI-OS Obsidian Integration",
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
            raise RpcError(-32602, "Unknown or disabled Obsidian tool")
        try:
            service = self._cached_service()
            validate_value(
                arguments,
                spec.effective_input_schema(
                    max_page_size=service.config.max_page_size,
                    max_read_chars=service.config.max_read_chars,
                ),
                "arguments",
            )
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
        except Exception as exc:  # pragma: no cover - does not expose internals
            print(f"Unexpected tool error in {name}: {type(exc).__name__}", file=sys.stderr)
            envelope = {
                "contract_version": CONTRACT_VERSION,
                "ok": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "The Obsidian Integration encountered an internal error",
                    "retryable": False,
                },
            }
            return _tool_result(envelope, is_error=True)

    def _cached_service(self) -> ObsidianService:
        try:
            metadata = Path(self.config_path).stat()
            signature = (metadata.st_mtime_ns, metadata.st_size)
        except OSError:
            signature = None
        if self._service is None or signature != self._service_signature:
            self._service = ObsidianService(load_config(self.config_path))
            self._service_signature = signature
        return self._service

    @staticmethod
    def _dispatch(service: ObsidianService, name: str, args: dict[str, Any]) -> dict[str, object]:
        limit = min(args.get("limit", service.config.max_page_size), service.config.max_page_size)
        if name == "obsidian_status":
            return service.status()
        if name == "obsidian_list_notes":
            return service.list_notes(
                folder=args.get("folder"),
                start=args.get("start", 0),
                limit=limit,
            )
        if name == "obsidian_search_notes":
            return service.search_notes(
                args["query"],
                args["mode"],
                folder=args.get("folder"),
                case_sensitive=args.get("case_sensitive", False),
                include_excerpt=args.get("include_excerpt", False),
                start=args.get("start", 0),
                limit=limit,
            )
        if name == "obsidian_get_note":
            return service.get_note(
                ref=args.get("ref"),
                path=args.get("path"),
                offset=args.get("offset", 0),
                max_chars=args.get("max_chars"),
                include_properties=args.get("include_properties", False),
            )
        if name == "obsidian_get_links":
            link_limit = min(args.get("limit", service.config.max_link_results), service.config.max_link_results)
            return service.get_links(
                ref=args.get("ref"),
                path=args.get("path"),
                direction=args.get("direction", "both"),
                limit=link_limit,
            )
        if name == "obsidian_publish_note":
            return service.publish_note(args["path"], args["content"])
        if name == "obsidian_update_note":
            return service.update_note(
                args["content"],
                args["expected_revision"],
                ref=args.get("ref"),
                path=args.get("path"),
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
    elif expected_type == "array":
        if not isinstance(value, list):
            _argument_error(path, "must be an array")
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
