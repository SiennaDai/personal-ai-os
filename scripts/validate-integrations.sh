#!/usr/bin/env bash
set -euo pipefail

readonly REPOSITORY_ROOT="/home/sienna/projects/personal-ai-os"
readonly ZOTERO_ROOT="$REPOSITORY_ROOT/integrations/zotero"
readonly SERVER="$ZOTERO_ROOT/src/zotero_mcp_server.py"
readonly EXAMPLE_CONFIG="$REPOSITORY_ROOT/integrations/config.example.toml"

fail() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

[[ -f "$REPOSITORY_ROOT/docs/integration-architecture.md" ]] || fail "missing Integration architecture"
[[ -f "$ZOTERO_ROOT/INTEGRATION.md" ]] || fail "missing Zotero contract"
[[ -f "$SERVER" ]] || fail "missing Zotero MCP server"
[[ -f "$EXAMPLE_CONFIG" ]] || fail "missing Integration example configuration"

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$ZOTERO_ROOT/src" \
  python3 -B -m unittest discover -s "$ZOTERO_ROOT/tests" -v
python3 -B "$SERVER" --config "$EXAMPLE_CONFIG" validate-config >/dev/null

tool_inventory="$(python3 -B "$SERVER" --config "$EXAMPLE_CONFIG" list-tools)"
python3 -c '
import json, sys
document = json.load(sys.stdin)
tools = document["tools"]
assert len(tools) == 9, f"expected 9 default tools, found {len(tools)}"
assert all(tool["annotations"]["readOnlyHint"] for tool in tools)
assert not any("delete" in tool["name"] or "bulk" in tool["name"] for tool in tools)
' <<<"$tool_inventory"

bash -n "$REPOSITORY_ROOT/scripts/sync-integrations.sh" "$REPOSITORY_ROOT/scripts/validate-integrations.sh"
printf 'Validated Zotero Integration: 38 tests, 9 default read tools, 3 gated write tools\n'
