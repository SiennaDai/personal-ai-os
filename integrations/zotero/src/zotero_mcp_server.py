#!/usr/bin/env python3
"""CLI and MCP stdio entry point for the Personal AI-OS Zotero Integration."""

from __future__ import annotations

import sys

# The registered runtime points at canonical source; never create bytecode artifacts there.
sys.dont_write_bytecode = True

import argparse
import json
import secrets
from datetime import datetime, timezone
from pathlib import Path

from paios_zotero.config import DEFAULT_CONFIG_PATH, load_config
from paios_zotero.errors import IntegrationError
from paios_zotero.mcp import CONTRACT_VERSION, ZoteroMcpServer
from paios_zotero.service import ZoteroService
from paios_zotero.smoke import run_read_smoke


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Personal AI-OS Zotero MCP Integration")
    parser.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG_PATH),
        help="Path to the unified integrations TOML",
    )
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("serve", help="Run the MCP stdio server")
    subparsers.add_parser("doctor", help="Run non-mutating configuration and connectivity checks")
    subparsers.add_parser(
        "read-smoke",
        help="Exercise representative live reads without returning library content",
    )
    subparsers.add_parser("validate-config", help="Validate configuration without connecting")
    subparsers.add_parser("list-tools", help="Print the currently exposed MCP tool inventory")
    registration = subparsers.add_parser(
        "verify-registration",
        help="Verify a codex mcp get --json document read from stdin",
    )
    registration.add_argument("--expected-command", required=True)
    registration.add_argument("--expected-arg", action="append", default=[])
    smoke = subparsers.add_parser(
        "write-smoke",
        help="Explicitly create and update one test child note; never deletes it",
    )
    smoke.add_argument("--parent-item-key", required=True)
    smoke.add_argument(
        "--confirm",
        required=True,
        help="Must equal CREATE_AND_UPDATE_ZOTERO_TEST_NOTE",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    command = args.command or "serve"
    if command == "serve":
        ZoteroMcpServer(args.config).run()
        return 0
    try:
        if command == "validate-config":
            config = load_config(args.config)
            _print_json(
                {
                    "contract_version": CONTRACT_VERSION,
                    "ok": True,
                    "configuration": config.public_summary(),
                }
            )
            return 0
        if command == "list-tools":
            tools = ZoteroMcpServer(args.config).tool_documents()
            _print_json(
                {
                    "contract_version": CONTRACT_VERSION,
                    "tools": tools,
                }
            )
            return 0
        if command == "verify-registration":
            try:
                document = json.load(sys.stdin)
            except json.JSONDecodeError as exc:
                raise IntegrationError(
                    "RUNTIME_CONFIG_CONFLICT",
                    "Codex returned invalid MCP registration JSON",
                ) from exc
            transport = document.get("transport", document) if isinstance(document, dict) else {}
            actual_command = transport.get("command") if isinstance(transport, dict) else None
            actual_args = transport.get("args", []) if isinstance(transport, dict) else []
            if actual_command != args.expected_command or actual_args != args.expected_arg:
                raise IntegrationError(
                    "RUNTIME_CONFIG_CONFLICT",
                    "The existing Codex Zotero MCP registration is not owned by this repository",
                    details={
                        "actual_command": actual_command,
                        "actual_args": actual_args,
                        "expected_command": args.expected_command,
                        "expected_args": args.expected_arg,
                    },
                )
            _print_json({"contract_version": CONTRACT_VERSION, "ok": True})
            return 0
        if command == "doctor":
            status = ZoteroService(load_config(args.config)).status()
            _print_json(status)
            return 0 if status["overall_ok"] else 1
        if command == "read-smoke":
            result = run_read_smoke(ZoteroService(load_config(args.config)))
            _print_json(result)
            return 0 if result["overall_ok"] else 1
        if command == "write-smoke":
            if args.confirm != "CREATE_AND_UPDATE_ZOTERO_TEST_NOTE":
                raise IntegrationError(
                    "CONFIRMATION_REQUIRED",
                    "write-smoke requires the exact confirmation token",
                )
            service = ZoteroService(load_config(args.config))
            marker = datetime.now(timezone.utc).isoformat()
            created_result = service.create_child_note(
                args.parent_item_key,
                f"<p>Personal AI-OS Zotero write smoke test created {marker}.</p>",
                secrets.token_hex(16),
                tags=["personal-ai-os-write-smoke"],
            )
            created = created_result["created"]
            ref = created["ref"]
            updated_result = service.update_note(
                ref["key"],
                ref["version"],
                f"<p>Personal AI-OS Zotero write smoke test created and updated {marker}.</p>",
            )
            _print_json(
                {
                    "contract_version": CONTRACT_VERSION,
                    "ok": True,
                    "created_and_updated": updated_result["updated"]["ref"],
                    "cleanup": "Delete this test note manually in Zotero after inspection; the Integration exposes no delete operation.",
                }
            )
            return 0
    except IntegrationError as exc:
        _print_json(
            {
                "contract_version": CONTRACT_VERSION,
                "ok": False,
                "error": exc.as_dict(),
            }
        )
        return 1
    return 2


def _print_json(value: object) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    sys.exit(main())
