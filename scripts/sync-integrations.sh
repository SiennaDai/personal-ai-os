#!/usr/bin/env bash
set -euo pipefail

readonly REPOSITORY_ROOT="/home/sienna/projects/personal-ai-os"
readonly SERVER="$REPOSITORY_ROOT/integrations/zotero/src/zotero_mcp_server.py"
readonly EXAMPLE_CONFIG="$REPOSITORY_ROOT/integrations/config.example.toml"
readonly RUNTIME_CONFIG_ROOT="$HOME/.config/personal-ai-os"
readonly RUNTIME_CONFIG="$RUNTIME_CONFIG_ROOT/integrations.toml"
readonly PYTHON_COMMAND="/usr/bin/python3"

fail() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

[[ -f "$SERVER" ]] || fail "missing Zotero MCP server: $SERVER"
[[ -f "$EXAMPLE_CONFIG" ]] || fail "missing Integration example configuration: $EXAMPLE_CONFIG"
command -v codex >/dev/null 2>&1 || fail "codex CLI is unavailable"
[[ -x "$PYTHON_COMMAND" ]] || fail "required Python runtime is unavailable: $PYTHON_COMMAND"

"$REPOSITORY_ROOT/scripts/validate-integrations.sh"
install -d -m 700 "$RUNTIME_CONFIG_ROOT"
if [[ ! -e "$RUNTIME_CONFIG" ]]; then
  install -m 600 "$EXAMPLE_CONFIG" "$RUNTIME_CONFIG"
  printf 'Installed read-only Integration configuration: %s\n' "$RUNTIME_CONFIG"
else
  [[ -f "$RUNTIME_CONFIG" && ! -L "$RUNTIME_CONFIG" ]] || \
    fail "runtime Integration configuration must be a regular file: $RUNTIME_CONFIG"
  python3 -B "$SERVER" --config "$RUNTIME_CONFIG" validate-config >/dev/null
  printf 'Preserved existing Integration configuration: %s\n' "$RUNTIME_CONFIG"
fi

readonly EXPECTED_ARGS=(
  "$SERVER"
  "--config"
  "$RUNTIME_CONFIG"
  "serve"
)
registration_json="$(mktemp "${TMPDIR:-/tmp}/paios-zotero-registration.XXXXXX")"
trap 'unlink "$registration_json" 2>/dev/null || true' EXIT

if codex mcp get zotero --json >"$registration_json" 2>/dev/null; then
  verify_args=(--expected-command "$PYTHON_COMMAND")
  for argument in "${EXPECTED_ARGS[@]}"; do
    verify_args+=("--expected-arg=$argument")
  done
  python3 -B "$SERVER" verify-registration "${verify_args[@]}" <"$registration_json" >/dev/null
  printf 'Preserved verified Codex MCP registration: zotero\n'
else
  codex mcp add zotero -- "$PYTHON_COMMAND" "${EXPECTED_ARGS[@]}"
  codex mcp get zotero --json >"$registration_json"
  verify_args=(--expected-command "$PYTHON_COMMAND")
  for argument in "${EXPECTED_ARGS[@]}"; do
    verify_args+=("--expected-arg=$argument")
  done
  python3 -B "$SERVER" verify-registration "${verify_args[@]}" <"$registration_json" >/dev/null
  printf 'Registered Codex MCP server: zotero\n'
fi

printf 'Default exposure: read-only (9 tools)\n'
printf 'Read-only doctor: python3 %s --config %s doctor\n' "$SERVER" "$RUNTIME_CONFIG"
