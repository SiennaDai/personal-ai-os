# Zotero Integration

## Status

Implemented as an AI-OS-owned MCP stdio facade with a default read-only runtime. The stable contract is [INTEGRATION.md](INTEGRATION.md).

Zotero remains the bibliographic source of truth. The Integration performs external I/O only; Agents and Skills own source evaluation, paper reading, synthesis, and writing.

## Runtime shape

```text
Codex / Specialist Agent
        ↓ MCP stdio
AI-OS Zotero facade
        ├── official Zotero Local API v3 (default reads)
        │     └── Windows system curl bridge when running in WSL
        ├── Better BibTeX JSON-RPC (optional citekeys)
        └── official Zotero Web API v3 (gated writes)
```

The implementation uses only the Python standard library and never reads `zotero.sqlite` directly. In WSL it reaches Windows loopback through the fixed Windows system `curl.exe`, so port 23119 stays private. Default configuration exposes nine read-only tools. Three single-object write tools are implemented but hidden until writes, credentials, scope, approval policy, and user authorization are all configured. Delete and bulk mutation are absent.

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

Write enablement and the explicitly mutating smoke-test procedure are documented only in [the contract](INTEGRATION.md#write-safety-and-concurrency). Do not treat tool availability or runtime approval as semantic authorization to change Zotero.
