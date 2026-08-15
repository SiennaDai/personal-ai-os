#!/usr/bin/env bash
set -euo pipefail

readonly REPOSITORY_ROOT="/home/sienna/projects/personal-ai-os"
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

validate_agent() {
  local directory="$1" source_path agent_name runtime_path source_body runtime_body
  source_path="$REPOSITORY_ROOT/agents/$directory/AGENT.md"
  agent_name="$(frontmatter_field "$source_path" name)"
  runtime_path="$HOME/.codex/agents/$agent_name.toml"
  [[ -f "$runtime_path" ]] || fail "missing Agent runtime: $runtime_path"
  grep -q "^name = \"$agent_name\"$" "$runtime_path" || fail "invalid Agent name: $runtime_path"
  grep -q '^description = ".\+"$' "$runtime_path" || fail "missing Agent description: $runtime_path"
  grep -q "^developer_instructions = '''$" "$runtime_path" || fail "missing Agent developer_instructions: $runtime_path"

  source_body="$(mktemp "${TMPDIR:-/tmp}/${agent_name}-source.XXXXXX")"
  runtime_body="$(mktemp "${TMPDIR:-/tmp}/${agent_name}-runtime.XXXXXX")"
  awk 'NR == 1 && $0 == "---" { frontmatter=1; next } frontmatter && $0 == "---" { frontmatter=0; next } !frontmatter { print }' "$source_path" > "$source_body"
  awk -v delimiter="'''" '$0 == "developer_instructions = " delimiter { instructions=1; next } instructions && $0 == delimiter { exit } instructions { print }' "$runtime_path" > "$runtime_body"
  cmp -s "$source_body" "$runtime_body" || fail "runtime instructions differ from canonical source: $agent_name"
  unlink "$source_body"
  unlink "$runtime_body"
}

for directory in "${AGENT_DIRECTORIES[@]}"; do
  validate_agent "$directory"
done

for skill in "${SKILLS[@]}"; do
  runtime_path="$HOME/.agents/skills/$skill"
  source_path="$REPOSITORY_ROOT/skills/$skill"
  [[ -L "$runtime_path" ]] || fail "Skill runtime is not a symlink: $runtime_path"
  [[ "$(readlink -f "$runtime_path")" == "$source_path" ]] || fail "Skill runtime does not resolve to canonical source: $runtime_path"
  [[ -f "$runtime_path/SKILL.md" ]] || fail "missing Skill definition: $runtime_path/SKILL.md"
  grep -q "^name: $skill$" "$runtime_path/SKILL.md" || fail "invalid Skill name: $skill"
  grep -q '^description: .\+' "$runtime_path/SKILL.md" || fail "missing Skill description: $skill"
done

printf 'Validated Agents: learning_agent research_agent\n'
printf 'Validated Skills: %s\n' "${SKILLS[*]}"
printf 'Canonical: %s\n' "$REPOSITORY_ROOT"
