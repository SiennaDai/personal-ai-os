#!/usr/bin/env bash
set -euo pipefail

readonly REPOSITORY_ROOT="/home/sienna/projects/personal-ai-os"
readonly AGENT_RUNTIME_ROOT="$HOME/.codex/agents"
readonly SKILL_RUNTIME_ROOT="$HOME/.agents/skills"
readonly AGENT_DIRECTORIES=(learning-agent research-agent)
readonly SKILLS=(assessment document-understanding education-learning evidence-synthesis knowledge-extraction knowledge-mapping literature-search stem-reasoning visualization)

fail() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

frontmatter_field() {
  local file="$1" field="$2"
  awk -v key="$field" '
    NR == 1 && $0 == "---" { in_frontmatter=1; next }
    in_frontmatter && $0 == "---" { exit }
    in_frontmatter && index($0, key ":") == 1 {
      value=substr($0, length(key) + 2)
      sub(/^[[:space:]]+/, "", value)
      sub(/[[:space:]]+$/, "", value)
      gsub(/^"|"$/, "", value)
      print value
      exit
    }
  ' "$file"
}

validate_definition() {
  local file="$1" expected_name="${2:-}" name description
  [[ -f "$file" ]] || fail "missing definition: $file"
  [[ "$(sed -n '1p' "$file")" == '---' ]] || fail "missing YAML frontmatter in $file"
  name="$(frontmatter_field "$file" name)"
  description="$(frontmatter_field "$file" description)"
  [[ -n "$name" ]] || fail "missing frontmatter field 'name' in $file"
  [[ -n "$description" ]] || fail "missing frontmatter field 'description' in $file"
  [[ -z "$expected_name" || "$name" == "$expected_name" ]] || fail "definition name '$name' does not match '$expected_name'"
}

generate_agent() {
  local directory="$1" source_path agent_name agent_description runtime_path obsolete_path temporary_toml
  source_path="$REPOSITORY_ROOT/agents/$directory/AGENT.md"
  validate_definition "$source_path"
  agent_name="$(frontmatter_field "$source_path" name)"
  agent_description="$(frontmatter_field "$source_path" description)"
  [[ "$agent_name" =~ ^[a-z][a-z0-9_]*$ ]] || fail "invalid Agent runtime name: $agent_name"
  [[ "$agent_description" != *'"'* && "$agent_description" != *'\'* ]] || fail "Agent description requires unsupported TOML escaping: $agent_name"
  grep -q '^artifact_type: agent$' "$source_path" || fail "invalid Agent artifact type: $source_path"
  grep -q "'''" "$source_path" && fail "Agent definition contains triple single quotes: $source_path"

  runtime_path="$AGENT_RUNTIME_ROOT/$agent_name.toml"
  obsolete_path="$AGENT_RUNTIME_ROOT/$directory"
  if [[ -L "$obsolete_path" ]]; then
    [[ "$(readlink "$obsolete_path")" == "$REPOSITORY_ROOT/agents/$directory" ]] || fail "obsolete Agent link has an unexpected target: $obsolete_path"
    unlink "$obsolete_path"
  elif [[ -e "$obsolete_path" ]]; then
    fail "obsolete Agent path exists but is not the expected symlink: $obsolete_path"
  fi

  temporary_toml="$(mktemp "${TMPDIR:-/tmp}/${agent_name}.toml.XXXXXX")"
  {
    printf '# Generated from agents/%s/AGENT.md by scripts/sync-runtime.sh.\n' "$directory"
    printf '%s\n' '# Do not edit this runtime projection directly.'
    printf 'name = "%s"\n' "$agent_name"
    printf 'description = "%s"\n' "$agent_description"
    printf '%s\n' "developer_instructions = '''"
    awk 'NR == 1 && $0 == "---" { frontmatter=1; next } frontmatter && $0 == "---" { frontmatter=0; next } !frontmatter { print }' "$source_path"
    printf '%s\n' "'''"
  } > "$temporary_toml"
  install -m 600 "$temporary_toml" "$runtime_path"
  unlink "$temporary_toml"
}

[[ -d "$REPOSITORY_ROOT" ]] || fail "canonical repository is unavailable: $REPOSITORY_ROOT"
[[ "$(cd "$REPOSITORY_ROOT" && pwd -P)" == "$REPOSITORY_ROOT" ]] || fail "canonical repository path does not resolve to itself"
mkdir -p "$AGENT_RUNTIME_ROOT" "$SKILL_RUNTIME_ROOT"

for directory in "${AGENT_DIRECTORIES[@]}"; do
  generate_agent "$directory"
done

for skill in "${SKILLS[@]}"; do
  source_path="$REPOSITORY_ROOT/skills/$skill"
  runtime_path="$SKILL_RUNTIME_ROOT/$skill"
  validate_definition "$source_path/SKILL.md" "$skill"
  if [[ -L "$runtime_path" ]]; then
    [[ "$(readlink "$runtime_path")" == "$source_path" ]] || fail "Skill link has an unexpected target: $runtime_path"
  elif [[ -e "$runtime_path" ]]; then
    fail "Skill runtime path exists and is not a symlink: $runtime_path"
  else
    ln -s "$source_path" "$runtime_path"
  fi
  [[ "$(readlink -f "$runtime_path")" == "$source_path" ]] || fail "Skill link does not resolve to canonical source: $runtime_path"
done

"$REPOSITORY_ROOT/scripts/validate-runtime.sh"
printf 'Deployment: %d Agents, %d Skills\n' "${#AGENT_DIRECTORIES[@]}" "${#SKILLS[@]}"
