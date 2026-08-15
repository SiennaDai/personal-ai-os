#!/usr/bin/env bash
set -euo pipefail

readonly REPOSITORY_ROOT="/home/sienna/projects/personal-ai-os"
readonly ZOTERO_SERVER="$REPOSITORY_ROOT/integrations/zotero/src/zotero_mcp_server.py"
readonly OBSIDIAN_SERVER="$REPOSITORY_ROOT/integrations/obsidian/src/obsidian_mcp_server.py"
readonly EXAMPLE_CONFIG="$REPOSITORY_ROOT/integrations/config.example.toml"
readonly RUNTIME_CONFIG_ROOT="$HOME/.config/personal-ai-os"
readonly RUNTIME_CONFIG="$RUNTIME_CONFIG_ROOT/integrations.toml"
readonly PYTHON_COMMAND="/usr/bin/python3"

fail() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

[[ -f "$ZOTERO_SERVER" ]] || fail "missing Zotero MCP server: $ZOTERO_SERVER"
[[ -f "$OBSIDIAN_SERVER" ]] || fail "missing Obsidian MCP server: $OBSIDIAN_SERVER"
[[ -f "$EXAMPLE_CONFIG" ]] || fail "missing Integration example configuration: $EXAMPLE_CONFIG"
command -v codex >/dev/null 2>&1 || fail "codex CLI is unavailable"
[[ -x "$PYTHON_COMMAND" ]] || fail "required Python runtime is unavailable: $PYTHON_COMMAND"

"$REPOSITORY_ROOT/scripts/validate-integrations.sh"
install -d -m 700 "$RUNTIME_CONFIG_ROOT"
if [[ ! -e "$RUNTIME_CONFIG" ]]; then
  initial_config="$(mktemp "${TMPDIR:-/tmp}/paios-initial-integrations.XXXXXX")"
  awk '/^\[obsidian\]$/ { exit } { print }' "$EXAMPLE_CONFIG" >"$initial_config"
  install -m 600 "$initial_config" "$RUNTIME_CONFIG"
  unlink "$initial_config"
  printf 'Installed read-only Integration configuration: %s\n' "$RUNTIME_CONFIG"
else
  [[ -f "$RUNTIME_CONFIG" && ! -L "$RUNTIME_CONFIG" ]] || \
    fail "runtime Integration configuration must be a regular file: $RUNTIME_CONFIG"
fi

python3 -B "$ZOTERO_SERVER" --config "$RUNTIME_CONFIG" validate-config >/dev/null
if ! python3 -B "$OBSIDIAN_SERVER" --config "$RUNTIME_CONFIG" validate-runtime-config >/dev/null 2>&1; then
  [[ -n "${PAIOS_OBSIDIAN_VAULT_PATH:-}" ]] || \
    fail "runtime config lacks a valid [obsidian] table; set PAIOS_OBSIDIAN_VAULT_PATH for default-off bootstrap"
  bootstrap_args=(
    "$OBSIDIAN_SERVER"
    "--config"
    "$RUNTIME_CONFIG"
    "bootstrap-config"
    "--vault-path"
    "$PAIOS_OBSIDIAN_VAULT_PATH"
  )
  if [[ -n "${PAIOS_OBSIDIAN_CLI_COMMAND:-}" || -n "${PAIOS_OBSIDIAN_CLI_VAULT_SELECTOR:-}" ]]; then
    [[ -n "${PAIOS_OBSIDIAN_CLI_COMMAND:-}" && -n "${PAIOS_OBSIDIAN_CLI_VAULT_SELECTOR:-}" ]] || \
      fail "Obsidian CLI bootstrap requires both PAIOS_OBSIDIAN_CLI_COMMAND and PAIOS_OBSIDIAN_CLI_VAULT_SELECTOR"
    bootstrap_args+=(
      "--cli-command"
      "$PAIOS_OBSIDIAN_CLI_COMMAND"
      "--cli-vault-selector"
      "$PAIOS_OBSIDIAN_CLI_VAULT_SELECTOR"
    )
  fi
  python3 -B "${bootstrap_args[@]}" >/dev/null
  printf 'Added default-off Obsidian runtime configuration\n'
fi
python3 -B "$OBSIDIAN_SERVER" --config "$RUNTIME_CONFIG" validate-runtime-config >/dev/null
printf 'Preserved validated Integration configuration: %s\n' "$RUNTIME_CONFIG"

registration_files=()
cleanup() {
  local file
  for file in "${registration_files[@]}"; do
    unlink "$file" 2>/dev/null || true
  done
}
trap cleanup EXIT

register_server() {
  local name="$1" server="$2" registration_json argument
  local expected_args=(
    "$server"
    "--config"
    "$RUNTIME_CONFIG"
    "serve"
  )
  local verify_args=(--expected-command "$PYTHON_COMMAND")
  registration_json="$(mktemp "${TMPDIR:-/tmp}/paios-${name}-registration.XXXXXX")"
  registration_files+=("$registration_json")

  for argument in "${expected_args[@]}"; do
    verify_args+=("--expected-arg=$argument")
  done
  if codex mcp get "$name" --json >"$registration_json" 2>/dev/null; then
    python3 -B "$server" verify-registration "${verify_args[@]}" <"$registration_json" >/dev/null
    printf 'Preserved verified Codex MCP registration: %s\n' "$name"
  else
    codex mcp add "$name" -- "$PYTHON_COMMAND" "${expected_args[@]}"
    codex mcp get "$name" --json >"$registration_json"
    python3 -B "$server" verify-registration "${verify_args[@]}" <"$registration_json" >/dev/null
    printf 'Registered Codex MCP server: %s\n' "$name"
  fi
}

register_server zotero "$ZOTERO_SERVER"
register_server obsidian "$OBSIDIAN_SERVER"

printf 'Default exposure: read-only (Zotero 9 tools; Obsidian 5 tools)\n'
printf 'Zotero doctor: python3 %s --config %s doctor\n' "$ZOTERO_SERVER" "$RUNTIME_CONFIG"
printf 'Obsidian doctor: python3 %s --config %s doctor\n' "$OBSIDIAN_SERVER" "$RUNTIME_CONFIG"
