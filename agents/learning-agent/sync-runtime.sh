#!/usr/bin/env bash
set -euo pipefail

readonly REPOSITORY_ROOT="/home/sienna/projects/personal-ai-os"
readonly AGENT_SOURCE="$REPOSITORY_ROOT/agents/learning-agent/AGENT.md"
readonly AGENT_RUNTIME="$HOME/.codex/agents/learning_agent.toml"
readonly OBSOLETE_AGENT_LINK="$HOME/.codex/agents/learning-agent"
readonly SKILL_RUNTIME_ROOT="$HOME/.agents/skills"
readonly SKILLS=(assessment document-understanding education-learning knowledge-extraction knowledge-mapping stem-reasoning visualization)

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

validate_markdown_definition() {
  local file="$1" expected_name="${2:-}" name description
  [[ -f "$file" ]] || fail "missing definition: $file"
  [[ "$(sed -n '1p' "$file")" == '---' ]] || fail "missing YAML frontmatter in $file"
  name="$(frontmatter_field "$file" name)"
  description="$(frontmatter_field "$file" description)"
  [[ -n "$name" ]] || fail "missing frontmatter field 'name' in $file"
  [[ -n "$description" ]] || fail "missing frontmatter field 'description' in $file"
  [[ -z "$expected_name" || "$name" == "$expected_name" ]] || fail "Skill name '$name' does not match directory '$expected_name'"
}

[[ -d "$REPOSITORY_ROOT" ]] || fail "canonical repository is not available at $REPOSITORY_ROOT"
[[ "$(cd "$REPOSITORY_ROOT" && pwd -P)" == "$REPOSITORY_ROOT" ]] || fail "canonical repository path does not resolve to itself: $REPOSITORY_ROOT"
validate_markdown_definition "$AGENT_SOURCE"
agent_name="$(frontmatter_field "$AGENT_SOURCE" name)"
agent_description="$(frontmatter_field "$AGENT_SOURCE" description)"
[[ "$agent_name" =~ ^[a-z][a-z0-9_]*$ ]] || fail "Learning Agent name is not a valid runtime identifier: $agent_name"
[[ "$agent_description" != *'"'* && "$agent_description" != *'\'* ]] || fail "Learning Agent description contains a character that requires TOML escaping"
grep -q "^title: Learning Agent$" "$AGENT_SOURCE" || fail "Learning Agent frontmatter title is invalid"
grep -q "^artifact_type: agent$" "$AGENT_SOURCE" || fail "Learning Agent artifact type is invalid"
grep -q "'''" "$AGENT_SOURCE" && fail "AGENT.md contains triple single quotes and cannot be embedded safely in TOML"

for skill in "${SKILLS[@]}"; do
  validate_markdown_definition "$REPOSITORY_ROOT/skills/$skill/SKILL.md" "$skill"
done

mkdir -p "$(dirname "$AGENT_RUNTIME")" "$SKILL_RUNTIME_ROOT"
if [[ -L "$OBSOLETE_AGENT_LINK" ]]; then
  [[ "$(readlink "$OBSOLETE_AGENT_LINK")" == "$REPOSITORY_ROOT/agents/learning-agent" ]] || fail "obsolete Agent link has an unexpected target: $OBSOLETE_AGENT_LINK"
  unlink "$OBSOLETE_AGENT_LINK"
elif [[ -e "$OBSOLETE_AGENT_LINK" ]]; then
  fail "obsolete Agent runtime path exists but is not the expected symlink: $OBSOLETE_AGENT_LINK"
fi

temporary_toml="$(mktemp "${TMPDIR:-/tmp}/learning_agent.toml.XXXXXX")"
cleanup() { [[ ! -e "$temporary_toml" ]] || unlink "$temporary_toml"; }
trap cleanup EXIT
{
  printf '%s\n' '# Generated from agents/learning-agent/AGENT.md by sync-runtime.sh.'
  printf '%s\n' '# Do not edit this runtime projection directly.'
  printf 'name = "%s"\n' "$agent_name"
  printf 'description = "%s"\n' "$agent_description"
  printf '%s\n' "developer_instructions = '''"
  awk 'NR == 1 && $0 == "---" { frontmatter=1; next } frontmatter && $0 == "---" { frontmatter=0; next } !frontmatter { print }' "$AGENT_SOURCE"
  printf '%s\n' "'''"
} > "$temporary_toml"
install -m 600 "$temporary_toml" "$AGENT_RUNTIME"

for skill in "${SKILLS[@]}"; do
  source_path="$REPOSITORY_ROOT/skills/$skill"
  runtime_path="$SKILL_RUNTIME_ROOT/$skill"
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
printf 'Deployment: 1 Agent, %d Skills\n' "${#SKILLS[@]}"
