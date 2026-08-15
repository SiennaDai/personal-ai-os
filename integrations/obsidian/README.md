# Obsidian Integration

## Status

Contract `1.0` and implementation `1.0.0` are complete. The audited WSL runtime is deployed default-read-only: the Vault filesystem and enabled official CLI pass the privacy-preserving doctor and read smoke. The canonical behavior is defined in [INTEGRATION.md](INTEGRATION.md), design evidence is recorded in [AUDIT.md](AUDIT.md), and fresh completion evidence is recorded in [VERIFICATION.md](VERIFICATION.md).

The live production Vault has not been mutated. Create and update are implemented and isolated-test verified, but remain hidden until a user deliberately configures a non-root write scope and enables writes.

## Runtime shape

```text
Codex / Specialist Agent
        ↓ MCP stdio
AI-OS Obsidian facade
        ├── Vault filesystem (required)
        │     exact Markdown, revisions, scoped create/update
        └── official Obsidian CLI (optional semantic plane)
              search, links/backlinks, parsed properties
```

The filesystem is authoritative for content and SHA-256 revisions. The enabled official CLI adds Obsidian-native semantics but never receives arbitrary commands and is not used for writes. Obsidian URI, community REST plugins, Sync history, internal caches, delete, move, rename, append, prepend, property/task mutation, and bulk operations are outside contract `1.0`.

## MCP tools

Default deployment exposes five read-only tools:

- `obsidian_status`
- `obsidian_list_notes`
- `obsidian_search_notes`
- `obsidian_get_note`
- `obsidian_get_links`

Two single-note writes are implemented but dynamically absent from `tools/list` while `write_enabled = false`:

- `obsidian_publish_note` — create-if-absent
- `obsidian_update_note` — complete replacement with an exact current revision

No destructive or bulk tool exists. Project artifacts remain in their external Project by default. A current user request can authorize publication when its content and destination are explicit; Knowledge Artifact classification alone never does.

## Configure and deploy

Machine-specific settings belong only in `~/.config/personal-ai-os/integrations.toml`. The tracked shape is in [`../config.example.toml`](../config.example.toml). On first deployment, provide the active Vault path and, optionally, both official-CLI values to the shared sync command:

```bash
PAIOS_OBSIDIAN_VAULT_PATH=/absolute/path/to/Vault \
PAIOS_OBSIDIAN_CLI_COMMAND=/absolute/path/to/Obsidian.com \
PAIOS_OBSIDIAN_CLI_VAULT_SELECTOR=native-vault-id-or-name \
./scripts/sync-integrations.sh
```

The bootstrap always sets `write_enabled = false` and an empty write-root list. The sync command preserves unrelated runtime configuration, validates the local Vault, verifies an enabled CLI targets that same Vault, and owns only the repository's `obsidian` MCP registration. It never starts Obsidian, enables its CLI, installs plugins, creates a Vault, or writes note content.

If CLI semantics are not wanted, omit both CLI variables. Exact list, literal search, reads, revisions, create, and update remain filesystem capabilities; Obsidian-query search, parsed properties, and links then report an unavailable optional capability.

Start a new Codex session after initial MCP registration or any tool-inventory change.

## Validate and operate

Run all dependency-free contract tests:

```bash
./scripts/validate-integrations.sh
```

Run live non-mutating checks:

```bash
python3 integrations/obsidian/src/obsidian_mcp_server.py \
  --config ~/.config/personal-ai-os/integrations.toml doctor

python3 integrations/obsidian/src/obsidian_mcp_server.py \
  --config ~/.config/personal-ai-os/integrations.toml read-smoke
```

The doctor returns aggregate configuration and capability evidence. The read smoke exercises representative reads while suppressing note identities, paths, properties, links, matches, and content.

## Deliberately enable writes

Write enablement is a separate operational decision:

1. Choose one or more existing, non-root Vault subdirectories.
2. Set those paths in `allowed_write_roots` and set `write_enabled = true` in the untracked runtime configuration.
3. Configure Codex to approve writes or use a stricter policy for this server, following the [official Codex MCP configuration guide](https://learn.chatgpt.com/docs/extend/mcp?surface=cli).
4. Rerun validation and sync, then start a new Codex session so the two write tools enter its inventory.
5. Treat an exact user publication request as the semantic gate for every create or replacement; retrieve the current revision before any update.

An optional `write-smoke` creates and updates one uniquely named note only after the exact confirmation token is supplied. It never deletes the note; cleanup remains an explicit, manual Vault action. Do not run it against the long-term Vault without a designated test root and deliberate authorization.
