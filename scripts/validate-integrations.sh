#!/usr/bin/env bash
set -euo pipefail

readonly REPOSITORY_ROOT="/home/sienna/projects/personal-ai-os"
readonly ZOTERO_ROOT="$REPOSITORY_ROOT/integrations/zotero"
readonly ZOTERO_SERVER="$ZOTERO_ROOT/src/zotero_mcp_server.py"
readonly OBSIDIAN_ROOT="$REPOSITORY_ROOT/integrations/obsidian"
readonly OBSIDIAN_SERVER="$OBSIDIAN_ROOT/src/obsidian_mcp_server.py"
readonly EXAMPLE_CONFIG="$REPOSITORY_ROOT/integrations/config.example.toml"

fail() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

[[ -f "$REPOSITORY_ROOT/docs/integration-architecture.md" ]] || fail "missing Integration architecture"
[[ -f "$ZOTERO_ROOT/INTEGRATION.md" ]] || fail "missing Zotero contract"
[[ -f "$ZOTERO_SERVER" ]] || fail "missing Zotero MCP server"
[[ -f "$OBSIDIAN_ROOT/INTEGRATION.md" ]] || fail "missing Obsidian contract"
[[ -f "$OBSIDIAN_ROOT/AUDIT.md" ]] || fail "missing Obsidian audit"
[[ -f "$OBSIDIAN_SERVER" ]] || fail "missing Obsidian MCP server"
[[ -f "$EXAMPLE_CONFIG" ]] || fail "missing Integration example configuration"

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$ZOTERO_ROOT/src" \
  python3 -B -m unittest discover -s "$ZOTERO_ROOT/tests" -v
python3 -B "$ZOTERO_SERVER" --config "$EXAMPLE_CONFIG" validate-config >/dev/null

tool_inventory="$(python3 -B "$ZOTERO_SERVER" --config "$EXAMPLE_CONFIG" list-tools)"
python3 -c '
import json, sys
document = json.load(sys.stdin)
tools = document["tools"]
assert len(tools) == 9, f"expected 9 default tools, found {len(tools)}"
assert all(tool["annotations"]["readOnlyHint"] for tool in tools)
assert not any("delete" in tool["name"] or "bulk" in tool["name"] for tool in tools)
' <<<"$tool_inventory"

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$OBSIDIAN_ROOT/src" \
  python3 -B -m unittest discover -s "$OBSIDIAN_ROOT/tests" -v
python3 -B "$OBSIDIAN_SERVER" --config "$EXAMPLE_CONFIG" validate-config >/dev/null

tool_inventory="$(python3 -B "$OBSIDIAN_SERVER" --config "$EXAMPLE_CONFIG" list-tools)"
python3 -c '
import json, sys
document = json.load(sys.stdin)
tools = document["tools"]
assert len(tools) == 5, f"expected 5 default tools, found {len(tools)}"
assert all(tool["annotations"]["readOnlyHint"] for tool in tools)
for tool in tools:
    assert not any(word in tool["name"] for word in ("delete", "move", "rename", "bulk"))
' <<<"$tool_inventory"

bash -n "$REPOSITORY_ROOT/scripts/sync-integrations.sh" "$REPOSITORY_ROOT/scripts/validate-integrations.sh"
printf 'Validated Zotero Integration: 44 tests, 9 default read tools, 5 gated write tools\n'
printf 'Validated Obsidian Integration: 46 tests, 5 default read tools, 2 gated write tools\n'
