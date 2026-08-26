# Zotero Integration

## Status

Contract `1.1` is implemented as an AI-OS-owned MCP stdio facade with a default read-only bootstrap. The stable contract is [INTEGRATION.md](INTEGRATION.md).

Zotero remains the bibliographic source of truth. The Integration performs external I/O only; Agents and Skills own source evaluation, paper reading, synthesis, and writing.

## Runtime shape

```text
Codex / Specialist Agent
        ↓ MCP stdio
AI-OS Zotero facade
        ├── official Zotero 10 Local API v3 (reads + gated writes)
│     └── Windows system curl bridge when running in WSL
        ├── Better BibTeX JSON-RPC (optional citekeys)
        └── official Zotero Web API v3 (optional reads only)
```

The implementation uses only the Python standard library and never reads `zotero.sqlite` directly. In WSL it reaches Windows loopback through the fixed Windows system `curl.exe`, so port 23119 stays private. Default configuration exposes nine read-only tools. Five single-object write tools are hidden until writes and a narrow scope are configured: create bibliographic metadata, create a child note, update a note, update allowlisted scalar metadata, and append one collection membership. Delete, bulk mutation, collection removal, and attachment upload are absent.

On the first write, Zotero 10 displays its native authorization dialog for `Personal AI-OS`. The MCP process caches the returned local key only in memory, binds all writes to Zotero's server ID, and reacquires authorization after a one-use key expires. No zotero.org API key is needed for local writes.

## Setup

1. In Zotero, enable **Settings → Advanced → Allow other applications on this computer to communicate with Zotero**.
2. Keep Better BibTeX running if citekey lookup is wanted.
3. Deploy the read-only runtime:

   ```bash
   ./scripts/sync-integrations.sh
   ```

4. Start Zotero and run the non-mutating doctor:

   ```bash
   python3 integrations/zotero/src/zotero_mcp_server.py \
     --config ~/.config/personal-ai-os/integrations.toml doctor
   ```

5. Restart Codex after initial MCP registration, then inspect the server with `codex mcp get zotero --json` or `/mcp`.

Runtime machine settings are copied from [`../config.example.toml`](../config.example.toml) only when no local file exists. Secrets never belong in that file.

## Development checks

```bash
./scripts/validate-integrations.sh
```

The command runs all dependency-free configuration, adapter, HTTP, service, safety, and MCP contract tests. It does not connect to or mutate a personal Zotero library.

After doctor passes, exercise representative live read paths without printing library content:

```bash
python3 integrations/zotero/src/zotero_mcp_server.py \
  --config ~/.config/personal-ai-os/integrations.toml read-smoke
```

See [VERIFICATION.md](VERIFICATION.md) for the latest verified layers and residual gaps.

## Enable a narrow local write scope

Keep the canonical example read-only. In the untracked runtime configuration, a Research Agent staging setup uses:

```toml
write_enabled = true
write_scope = "collections"
allowed_write_collection_keys = []
allowed_write_collection_names = ["临时工作区"]
```

Restart Codex after changing the runtime configuration so the five write tools enter the MCP inventory. The first actual write opens Zotero's authorization dialog; choose **Allow** for one write or **Always Allow** for this local application. Tool availability is not general mutation authority: the Research Agent's standing permission is limited to verified, deduplicated discovery imports into `临时工作区`; other writes remain explicitly requested operations.

The write-smoke procedure and concurrency rules are documented in [the contract](INTEGRATION.md#write-safety-and-concurrency).
