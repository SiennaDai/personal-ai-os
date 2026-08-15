#!/usr/bin/env bash
set -euo pipefail

readonly REPOSITORY_ROOT="/home/sienna/projects/personal-ai-os"
readonly AGENT_SOURCE="$REPOSITORY_ROOT/agents/learning-agent/AGENT.md"
readonly AGENT_RUNTIME="$HOME/.codex/agents/learning_agent.toml"
readonly SKILLS=(assessment document-understanding education-learning knowledge-extraction knowledge-mapping stem-reasoning visualization)

fail() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
[[ -f "$AGENT_RUNTIME" ]] || fail "missing Agent runtime: $AGENT_RUNTIME"
grep -q '^name = "learning_agent"$' "$AGENT_RUNTIME" || fail "invalid Agent name"
grep -q '^description = ".\+"$' "$AGENT_RUNTIME" || fail "missing Agent description"
grep -q "^developer_instructions = '''$" "$AGENT_RUNTIME" || fail "missing Agent developer_instructions"

source_body="$(mktemp "${TMPDIR:-/tmp}/learning-agent-source.XXXXXX")"
runtime_body="$(mktemp "${TMPDIR:-/tmp}/learning-agent-runtime.XXXXXX")"
cleanup() {
  [[ ! -e "$source_body" ]] || unlink "$source_body"
  [[ ! -e "$runtime_body" ]] || unlink "$runtime_body"
}
trap cleanup EXIT
awk 'NR == 1 && $0 == "---" { frontmatter=1; next } frontmatter && $0 == "---" { frontmatter=0; next } !frontmatter { print }' "$AGENT_SOURCE" > "$source_body"
awk -v delimiter="'''" '$0 == "developer_instructions = " delimiter { instructions=1; next } instructions && $0 == delimiter { exit } instructions { print }' "$AGENT_RUNTIME" > "$runtime_body"
cmp -s "$source_body" "$runtime_body" || fail "runtime instructions differ from canonical AGENT.md"

for skill in "${SKILLS[@]}"; do
  runtime_path="$HOME/.agents/skills/$skill"
  source_path="$REPOSITORY_ROOT/skills/$skill"
  [[ -L "$runtime_path" ]] || fail "Skill runtime is not a symlink: $runtime_path"
  [[ "$(readlink -f "$runtime_path")" == "$source_path" ]] || fail "Skill runtime does not resolve to canonical source: $runtime_path"
  [[ -f "$runtime_path/SKILL.md" ]] || fail "missing Skill definition: $runtime_path/SKILL.md"
  grep -q '^name: .\+' "$runtime_path/SKILL.md" || fail "missing Skill name: $skill"
  grep -q '^description: .\+' "$runtime_path/SKILL.md" || fail "missing Skill description: $skill"
done

printf 'Validated: %s\n' "$AGENT_RUNTIME"
printf 'Skills: %s\n' "${SKILLS[*]}"
printf 'Canonical: %s\n' "$REPOSITORY_ROOT"
