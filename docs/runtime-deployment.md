# WSL Runtime Deployment

## Environment and ownership

```text
Windows
   ↓
WSL2 Ubuntu
   ↓
Codex CLI
```

`/home/sienna/projects/personal-ai-os` is the only canonical editable source. A Windows clone is a legacy/non-canonical copy and must not be used to edit definitions or generate runtime configuration.

Runtime locations follow Codex conventions:

- generated personal Agents: `~/.codex/agents/*.toml`
- user-level Skills: `~/.agents/skills/<skill-name>/`

## Synchronize and validate

Run from any directory:

```bash
/home/sienna/projects/personal-ai-os/scripts/sync-runtime.sh
```

The command validates all canonical Agent and Skill definitions, generates Agent TOML files from each `agents/<agent>/AGENT.md`, removes only recognized obsolete Agent directory symlinks, and creates or confirms Skill symlinks. It fails rather than overwrite an unexpected runtime file or directory. Re-running it is safe and does not create nested links.

For a validation-only check after deployment:

```bash
/home/sienna/projects/personal-ai-os/scripts/validate-runtime.sh
```

## Cross-project use

Open Codex in any independent Project and ask the main session to delegate to the appropriate Specialist Agent, for example: `Have the Research Agent analyze this paper and choose relevant Skills automatically.` or `Have the Writing Agent revise this draft without changing its claims.` The Project stays the Codex working root; it is never moved into or copied to `personal-ai-os`.

## Updating definitions

- After editing a Skill in `skills/<skill-name>/`, no redeployment is normally needed: the runtime symlink resolves directly to the canonical source. Restart or start a new Codex session if discovery metadata changed.
- After editing any `agents/<agent>/AGENT.md`, rerun `scripts/sync-runtime.sh`; generated TOML files are not editable sources.

## Discovery recovery

If Codex does not discover an Agent or Skill:

1. Run `scripts/validate-runtime.sh` and resolve every reported path or frontmatter error.
2. Run `scripts/sync-runtime.sh` again.
3. Confirm the links resolve under the WSL canonical repository with `readlink -f ~/.agents/skills/<skill-name>`.
4. Start a new Codex session in the Project. Existing sessions may retain their initial discovery state.
5. Run a small explicit delegation prompt. If it still fails, use `codex doctor` and confirm the installed CLI supports custom agents and multi-agent operation.

Do not add the external Project as an extra writable root merely to make discovery work.
