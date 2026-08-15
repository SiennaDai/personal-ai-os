#!/usr/bin/env python3
"""CLI and MCP stdio entry point for the Personal AI-OS Obsidian Integration."""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import argparse
import json
import secrets
from datetime import datetime, timezone
from pathlib import Path

from paios_obsidian.cli import ObsidianCli
from paios_obsidian.config import (
    DEFAULT_CONFIG_PATH,
    ObsidianConfig,
    append_runtime_config,
    load_config,
)
from paios_obsidian.errors import IntegrationError
from paios_obsidian.filesystem import VaultFilesystem
from paios_obsidian.mcp import CONTRACT_VERSION, ObsidianMcpServer
from paios_obsidian.service import ObsidianService
from paios_obsidian.smoke import run_read_smoke


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Personal AI-OS Obsidian MCP Integration")
    parser.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG_PATH),
        help="Path to the unified integrations TOML",
    )
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("serve", help="Run the MCP stdio server")
    subparsers.add_parser("doctor", help="Run non-mutating configuration and capability checks")
    subparsers.add_parser(
        "read-smoke",
        help="Exercise representative live reads without returning note identity or content",
    )
    subparsers.add_parser("validate-config", help="Validate configuration without live access")
    subparsers.add_parser(
        "validate-runtime-config",
        help="Validate configuration and confined Vault availability without invoking the CLI",
    )
    subparsers.add_parser("list-tools", help="Print the currently exposed MCP tool inventory")

    registration = subparsers.add_parser(
        "verify-registration",
        help="Verify a codex mcp get --json document read from stdin",
    )
    registration.add_argument("--expected-command", required=True)
    registration.add_argument("--expected-arg", action="append", default=[])

    bootstrap = subparsers.add_parser(
        "bootstrap-config",
        help="Append a default-off Obsidian table to an existing unified runtime config",
    )
    bootstrap.add_argument("--vault-path", required=True)
    bootstrap.add_argument("--vault-alias", default="knowledge")
    bootstrap.add_argument("--read-root", action="append", default=[])
    bootstrap.add_argument("--cli-command", default="")
    bootstrap.add_argument("--cli-vault-selector", default="")

    smoke = subparsers.add_parser(
        "write-smoke",
        help="Explicitly create and update one test note; never deletes it",
    )
    smoke.add_argument("--test-root", required=True)
    smoke.add_argument(
        "--confirm",
        required=True,
        help="Must equal CREATE_AND_UPDATE_OBSIDIAN_TEST_NOTE",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    command = args.command or "serve"
    if command == "serve":
        ObsidianMcpServer(args.config).run()
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
        if command == "validate-runtime-config":
            config = load_config(args.config)
            filesystem = VaultFilesystem(config).status()
            if not filesystem["ready"]:
                raise IntegrationError(
                    str(filesystem["error_code"] or "VAULT_UNAVAILABLE"),
                    "The configured Obsidian Vault is unavailable",
                )
            _print_json(
                {
                    "contract_version": CONTRACT_VERSION,
                    "ok": True,
                    "vault_alias": config.vault_alias,
                    "filesystem_ready": True,
                    "writes_enabled": config.write_enabled,
                }
            )
            return 0
        if command == "list-tools":
            _print_json(
                {
                    "contract_version": CONTRACT_VERSION,
                    "tools": ObsidianMcpServer(args.config).tool_documents(),
                }
            )
            return 0
        if command == "verify-registration":
            _verify_registration(args.expected_command, args.expected_arg)
            _print_json({"contract_version": CONTRACT_VERSION, "ok": True})
            return 0
        if command == "bootstrap-config":
            cli_enabled = bool(args.cli_command or args.cli_vault_selector)
            if bool(args.cli_command) != bool(args.cli_vault_selector):
                raise IntegrationError(
                    "CONFIG_INVALID",
                    "CLI bootstrap requires both command and Vault selector",
                )
            config = ObsidianConfig(
                vault_alias=args.vault_alias,
                vault_path=args.vault_path,
                read_roots=tuple(args.read_root or ["."]),
                cli_enabled=cli_enabled,
                cli_command=args.cli_command,
                cli_vault_selector=args.cli_vault_selector,
            )
            filesystem_status = VaultFilesystem(config).status()
            if not filesystem_status["ready"]:
                raise IntegrationError(
                    "VAULT_UNAVAILABLE",
                    "The detected Vault failed confined filesystem validation",
                )
            cli_status = ObsidianCli(config).status()
            if cli_enabled and not cli_status["ready"]:
                raise IntegrationError(
                    str(cli_status["error_code"] or "CLI_UNAVAILABLE"),
                    "The configured official CLI failed live bootstrap validation",
                )
            append_runtime_config(args.config, config)
            _print_json(
                {
                    "contract_version": CONTRACT_VERSION,
                    "ok": True,
                    "vault_alias": config.vault_alias,
                    "filesystem_ready": True,
                    "cli_ready": bool(cli_status["ready"]),
                    "writes_enabled": False,
                }
            )
            return 0
        if command == "doctor":
            status = ObsidianService(load_config(args.config)).status()
            _print_json(status)
            return 0 if status["overall_ok"] else 1
        if command == "read-smoke":
            result = run_read_smoke(ObsidianService(load_config(args.config)))
            _print_json(result)
            return 0 if result["overall_ok"] else 1
        if command == "write-smoke":
            if args.confirm != "CREATE_AND_UPDATE_OBSIDIAN_TEST_NOTE":
                raise IntegrationError(
                    "CONFIRMATION_REQUIRED",
                    "write-smoke requires the exact confirmation token",
                )
            service = ObsidianService(load_config(args.config))
            marker = datetime.now(timezone.utc).isoformat()
            path = f"{args.test_root.rstrip('/')}/paios-write-smoke-{secrets.token_hex(8)}.md"
            created = service.publish_note(
                path,
                f"# Personal AI-OS write smoke\n\nCreated {marker}.\n",
            )
            updated = service.update_note(
                f"# Personal AI-OS write smoke\n\nCreated and updated {marker}.\n",
                str(created["note"]["revision"]),
                path=path,
            )
            _print_json(
                {
                    "contract_version": CONTRACT_VERSION,
                    "ok": True,
                    "created_and_updated": updated["note"],
                    "cleanup": "Inspect and delete this test note manually in Obsidian; the Integration exposes no delete operation.",
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


def _verify_registration(expected_command: str, expected_args: list[str]) -> None:
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
    if actual_command != expected_command or actual_args != expected_args:
        raise IntegrationError(
            "RUNTIME_CONFIG_CONFLICT",
            "The existing Codex Obsidian MCP registration is not owned by this repository",
            details={
                "actual_command": actual_command,
                "actual_args": actual_args,
                "expected_command": expected_command,
                "expected_args": expected_args,
            },
        )


def _print_json(value: object) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    sys.exit(main())
