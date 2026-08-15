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
- Zotero MCP registration: the owned `mcp_servers.zotero` entry in `~/.codex/config.toml`
- Obsidian MCP registration: the owned `mcp_servers.obsidian` entry in `~/.codex/config.toml`
- machine-specific Integration settings: `~/.config/personal-ai-os/integrations.toml`

Secrets are provided through environment variables, OAuth storage, or another appropriate secret source rather than tracked configuration. The Zotero and Obsidian Integrations are implemented and deployed separately from Agent/Skill projections. See [Integration Layer Architecture](integration-architecture.md), the [Zotero contract](../integrations/zotero/INTEGRATION.md), and the [Obsidian contract](../integrations/obsidian/INTEGRATION.md).

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

## Synchronize and validate Integrations

Deploy or verify the default-read-only Zotero and Obsidian configuration and MCP registrations with:

```bash
/home/sienna/projects/personal-ai-os/scripts/sync-integrations.sh
```

The command validates canonical files first, preserves an existing valid runtime file, registers the exact repository-owned stdio commands, and fails on an unexpected existing registration. Under WSL, the default Zotero local transport uses Windows system `curl.exe` to reach Zotero's Windows-only loopback listener without exposing the port. The command does not start either application or enable writes.

On first Obsidian deployment, supply `PAIOS_OBSIDIAN_VAULT_PATH`. To enable the optional official-CLI semantic plane at bootstrap, also supply both `PAIOS_OBSIDIAN_CLI_COMMAND` and `PAIOS_OBSIDIAN_CLI_VAULT_SELECTOR`. These values are validated and written only to the untracked machine-local configuration; bootstrap always leaves writes disabled.

Run dependency-free static and contract checks without external-system access:

```bash
/home/sienna/projects/personal-ai-os/scripts/validate-integrations.sh
```

With Zotero running and local API access enabled, run the non-mutating live doctor:

```bash
python3 /home/sienna/projects/personal-ai-os/integrations/zotero/src/zotero_mcp_server.py \
  --config ~/.config/personal-ai-os/integrations.toml doctor
```

With the configured Vault available and Obsidian running when CLI semantics are enabled, run the non-mutating Obsidian checks:

```bash
python3 /home/sienna/projects/personal-ai-os/integrations/obsidian/src/obsidian_mcp_server.py \
  --config ~/.config/personal-ai-os/integrations.toml doctor

python3 /home/sienna/projects/personal-ai-os/integrations/obsidian/src/obsidian_mcp_server.py \
  --config ~/.config/personal-ai-os/integrations.toml read-smoke
```

Start a new Codex session after initial MCP registration or a material tool-inventory change. Both default deployments expose only read tools. Write enablement requires the separate configuration, scope, Codex approval-policy, precondition, and user-authorization gates in the corresponding contract.

## Cross-project use

Open Codex in any independent Project and ask the main session to delegate to the appropriate Specialist Agent, for example: `Have the Research Agent analyze this paper and choose relevant Skills automatically.`, `Have the Writing Agent revise this draft without changing its claims.`, `Have the Coding Agent fix this reproducible bug and verify it.`, or `Have the Modeling Agent formulate and validate this optimization model.` The Project stays the Codex working root; it is never moved into or copied to `personal-ai-os`.

## Updating definitions

- After editing a Skill in `skills/<skill-name>/`, no redeployment is normally needed: the runtime symlink resolves directly to the canonical source. Restart or start a new Codex session if discovery metadata changed.
- After editing any `agents/<agent>/AGENT.md`, rerun `scripts/sync-runtime.sh`; generated TOML files are not editable sources.
- After changing either MCP implementation, contract, or runtime settings, run `scripts/validate-integrations.sh`; rerun `scripts/sync-integrations.sh` when registration or initial local configuration must be checked.

## Discovery recovery

If Codex does not discover an Agent or Skill:

1. Run `scripts/validate-runtime.sh` and resolve every reported path or frontmatter error.
2. Run `scripts/sync-runtime.sh` again.
3. Confirm the links resolve under the WSL canonical repository with `readlink -f ~/.agents/skills/<skill-name>`.
4. Start a new Codex session in the Project. Existing sessions may retain their initial discovery state.
5. Run a small explicit delegation prompt. If it still fails, use `codex doctor` and confirm the installed CLI supports custom agents and multi-agent operation.

Do not add the external Project as an extra writable root merely to make discovery work.
