"""Privacy-preserving live read smoke checks for Obsidian."""

from __future__ import annotations

import secrets

from .errors import IntegrationError
from .service import ObsidianService


def run_read_smoke(service: ObsidianService) -> dict[str, object]:
    """Exercise representative reads while returning no note identity or content."""

    status = service.status()
    filesystem_ready = bool(status["filesystem"]["ready"])
    cli_ready = bool(status["cli"]["ready"])
    result: dict[str, object] = {
        "contract_version": "1.0",
        "ok": False,
        "overall_ok": False,
        "filesystem_ready": filesystem_ready,
        "cli_enabled": service.config.cli_enabled,
        "cli_ready": cli_ready,
        "exercised": {
            "list": False,
            "exact_read": False,
            "literal_search": False,
            "obsidian_search": False,
            "properties": False,
            "links": False,
        },
        "note_available": False,
    }
    if not filesystem_ready:
        return result

    listing = service.list_notes(limit=1)
    result["exercised"]["list"] = True
    notes = listing["notes"]
    result["note_available"] = bool(notes)
    token = "paios-read-smoke-no-match-" + secrets.token_hex(16)
    literal = service.search_notes(token, "literal", limit=1)
    if literal["matches"]:
        raise IntegrationError(
            "BACKEND_PROTOCOL_ERROR",
            "The generated no-match literal search token unexpectedly matched",
        )
    result["exercised"]["literal_search"] = True

    note_path: str | None = None
    if notes:
        note_path = str(notes[0]["path"])
        service.get_note(path=note_path, max_chars=min(1_000, service.config.max_read_chars))
        result["exercised"]["exact_read"] = True

    if cli_ready:
        semantic = service.search_notes(token, "obsidian", limit=1)
        if semantic["matches"]:
            raise IntegrationError(
                "BACKEND_PROTOCOL_ERROR",
                "The generated no-match Obsidian search token unexpectedly matched",
            )
        result["exercised"]["obsidian_search"] = True
        if note_path is not None:
            service.get_note(path=note_path, max_chars=1, include_properties=True)
            result["exercised"]["properties"] = True
            service.get_links(path=note_path, direction="both", limit=10)
            result["exercised"]["links"] = True

    required = ["list", "literal_search"]
    if notes:
        required.append("exact_read")
    if service.config.cli_enabled:
        required.append("obsidian_search")
        if notes:
            required.extend(["properties", "links"])
    overall_ok = all(result["exercised"][name] for name in required)
    result["ok"] = overall_ok
    result["overall_ok"] = overall_ok
    return result
