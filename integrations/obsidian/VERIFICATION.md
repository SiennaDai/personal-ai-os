# Obsidian Integration Verification

Verification date: 2026-08-15.

## Outcome

Implementation `1.0.0` is deployed in the audited WSL runtime with a healthy required filesystem plane and healthy optional official-CLI semantic plane. Codex registration and MCP stdio negotiation pass. The default inventory contains exactly five read-only tools; both write tools are absent because writes are disabled and no write root is configured.

No Vault file was created, changed, moved, renamed, or deleted during this verification. Live outputs were privacy-preserving: they did not return the machine path, native Vault selector, note identity, note path, content, properties, links, backlinks, or search matches.

## Evidence

| Layer | Fresh result |
|---|---|
| Obsidian unit, contract, adapter, safety, and MCP tests | `46/46` passed |
| Shared Integration validation | Zotero `38/38`; Obsidian `46/46`; tool inventories and shell syntax passed |
| Runtime Agent synchronization | Five Agents and sixteen Skills validated and deployed |
| Deployment idempotency | A second sync preserved the runtime file and both owned MCP registrations |
| Codex registration | Enabled owned `obsidian` stdio entry verified |
| MCP negotiation | Protocol `2025-06-18`; `tools/list` returned five read-only tools; writes hidden |
| Filesystem doctor | Ready; one configured read root; aggregate enumeration completed without truncation |
| Official CLI doctor | Enabled, reachable, supported `1.13.7`, and resolved to the same Vault |
| Live read smoke | List, exact read, literal search, Obsidian-query search, parsed properties, and links/backlinks all exercised |
| Write readiness | Disabled; zero configured write roots; no production write attempted |

The live read smoke intentionally consumes a bounded note internally only to prove the exact-read path, then emits booleans rather than note data. The guaranteed-no-match semantic search prevents a search result identity from appearing in the verification output.

## Commands

The reproducible repository check is:

```bash
./scripts/validate-integrations.sh
```

The privacy-preserving live checks are:

```bash
python3 integrations/obsidian/src/obsidian_mcp_server.py \
  --config ~/.config/personal-ai-os/integrations.toml doctor

python3 integrations/obsidian/src/obsidian_mcp_server.py \
  --config ~/.config/personal-ai-os/integrations.toml read-smoke
```

Runtime deployment and ownership verification use:

```bash
./scripts/sync-runtime.sh
./scripts/sync-integrations.sh
codex mcp get obsidian --json
```

## Deliberately unverified

- The opt-in write smoke has not been run against the long-term Vault. Create and conflict-protected update are verified only with isolated temporary Vaults.
- Atomic replacement and durability have not been live-proven on the WSL-to-Windows production Vault filesystem.
- The interactive cross-Agent prompt suite and a real Zotero → Project → explicit Obsidian publication flow remain regression exercises; neither blocks default-read-only operation.

These omissions are safety boundaries, not implicit authorization to enable writes. A live write check requires a designated non-root test directory, explicit user authorization, visible write tools, Codex write approval, and manual cleanup review.
