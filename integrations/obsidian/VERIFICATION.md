# Obsidian Integration Verification

Verification date: 2026-08-15.

## Outcome

Implementation `1.0.0` is deployed in the audited WSL runtime with a healthy required filesystem plane and healthy optional official-CLI semantic plane. Codex registration and MCP stdio negotiation pass. The canonical bootstrap remains default-read-only with five tools. In this explicitly authorized local deployment, writes are enabled for exactly one existing non-root directory, so the runtime inventory contains five read tools and two write tools.

The live write smoke created and conflict-protected updated exactly one uniquely named Markdown note in the designated directory. It did not move, rename, or delete anything, and it left that note in place for manual inspection and cleanup. Live read and doctor outputs remained privacy-preserving. The write smoke returned only the test note's canonical Vault-relative ref, revision, and bounded metadata; it did not return the machine path, native Vault selector, or note content.

## Evidence

| Layer | Fresh result |
|---|---|
| Obsidian unit, contract, adapter, safety, and MCP tests | `46/46` passed |
| Shared Integration validation | Zotero `38/38`; Obsidian `46/46`; tool inventories and shell syntax passed |
| Runtime Agent synchronization | Five Agents and sixteen Skills validated and deployed |
| Deployment idempotency | A second sync preserved the runtime file and both owned MCP registrations |
| Codex registration | Enabled owned `obsidian` stdio entry verified |
| MCP negotiation | Protocol `2025-06-18`; enabled runtime inventory returned five read tools and two write tools |
| Filesystem doctor | Ready; one configured read root; aggregate enumeration completed without truncation |
| Official CLI doctor | Enabled, reachable, supported `1.13.7`, and resolved to the same Vault |
| Live read smoke | List, exact read, literal search, Obsidian-query search, parsed properties, and links/backlinks all exercised |
| Write readiness | Enabled and ready for exactly one existing non-root write directory |
| Codex write policy | Server policy set to `writes`, preserving normal reads while requiring approval for tools not marked read-only |
| Live write smoke | One note created, read back, replaced with its exact expected revision, and read back at the new revision |
| Cleanup | Test note intentionally retained for manual inspection and deletion in Obsidian |

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

The mutating check must be separately authorized and pointed at an allowlisted test root:

```bash
python3 integrations/obsidian/src/obsidian_mcp_server.py \
  --config ~/.config/personal-ai-os/integrations.toml \
  write-smoke \
  --test-root <designated-write-root> \
  --confirm CREATE_AND_UPDATE_OBSIDIAN_TEST_NOTE
```

Runtime deployment and ownership verification use:

```bash
./scripts/sync-runtime.sh
./scripts/sync-integrations.sh
codex mcp get obsidian --json
```

## Deliberately unverified

- Obsidian UI inspection and manual deletion of the retained smoke note remain a user action.
- Normal create and atomic replacement completed on the WSL-to-Windows Vault filesystem, but crash consistency under a forced process, host, or storage interruption has not been tested.
- The interactive cross-Agent prompt suite and a real Zotero → Project → explicit Obsidian publication flow remain regression exercises; neither blocks default-read-only operation.

These omissions do not expand write authority. The live result proves only the explicitly authorized single-note smoke inside the configured non-root scope; every ordinary publication still requires an explicit target and user-authorized write, and every replacement still requires the exact current revision.
