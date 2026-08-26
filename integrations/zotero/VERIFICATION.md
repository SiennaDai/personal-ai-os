# Zotero Integration Verification

## Contract 1.1 evidence (2026-08-25)

- Static suite passed: 44 tests.
- Default inventory remains nine read-only tools.
- An enabled configuration exposes five gated write tools and no delete, bulk, collection-removal, or file-upload tool.
- Isolated tests cover the Zotero 10 `/api/local/authorize` handshake, `Zotero-Server-ID` binding, header-only local key handling, exact-name collection scope, bounded bibliographic creation, append-only collection membership, write tokens, and version-protected updates.
- `./scripts/validate-integrations.sh` passes both Integration suites and shell validation.
- The Research Agent definition now performs conservative deduplication and bounded metadata import into an exact `临时工作区` scope, with a read-only opt-out.
- A live read-only doctor reached Zotero `10.0.1` and Better BibTeX `9.0.59`, observed the Zotero server identity, and reported local writes enabled and ready without opening an authorization dialog.
- A live read-only collection lookup found exactly one `临时工作区`; the untracked runtime configuration is scoped to that collection's native key rather than to all future collections with the same name.

No live Zotero write was performed while recording this update. Desktop authorization and a live staging import remain first-use checks, so the evidence proves readiness and scope but not a completed production mutation. No personal library content or local authorization key was written to this repository.

## Previous contract 1.0 evidence

### Evidence date and environment

Fresh evidence recorded on 2026-08-15 in the canonical WSL runtime:

- Codex CLI `0.147.0`
- Python `3.12.3`
- Zotero `9.0.6` on Windows
- Better BibTeX `9.0.55`
- MCP contract `1.0`; server `1.0.0`

This file records capability evidence, not personal library content. It contains no titles, creators, item keys, notes, annotations, full text, citekeys, paths to attachments, or credentials.

### Verification matrix

| Layer | Evidence | Result | What it proves |
|---|---|---|---|
| Static and contract | `./scripts/validate-integrations.sh` | Passed: 38 tests | Configuration strictness, normalization, direct and Windows-loopback HTTP behavior, response bounds, error mapping, write gates, scoped note create/update, scalar update conflicts, MCP lifecycle, stdio framing, configuration-aware page-limit clamping/defaults, tool annotations, tool-specific output schemas, structured errors, and privacy-safe smoke summarization |
| Default tool policy | MCP inventory from example and installed runtime config | Passed: 9 read tools; 3 write tools hidden | Default deployment exposes no mutation; delete and bulk tools are absent |
| Deployment idempotency | `./scripts/sync-integrations.sh` run twice | Passed | Existing runtime TOML is preserved and the exact repository-owned MCP registration is accepted on rerun |
| Agent runtime projection | `./scripts/sync-runtime.sh` | Passed: 5 Agents, 16 Skills | Updated Zotero routing is present in generated Agent runtimes |
| Windows-loopback bridge | Direct Windows system curl discriminator plus doctor | Passed | WSL can reach Windows Zotero without port forwarding; the server selects `windows-curl` |
| Read-only doctor | `zotero_mcp_server.py ... doctor` | Passed | Local API is enabled and readable; Better BibTeX is reachable; writes remain disabled |
| Codex MCP path | New read-only `codex exec` calling `zotero_status` exactly once | Passed | Codex discovers the registered server, initializes it, calls the tool, and consumes structured status output |
| Privacy-safe read smoke | `zotero_mcp_server.py ... read-smoke` against a non-empty library | Passed | Status, collections, search, exact item, children, annotations, bounded full text, and citekey paths work without emitting personal records; writes remained disabled |
| Representative-record MCP reads | Six JSON-RPC `tools/call` requests through the stdio server | Passed | One exact search match was returned; exact item and three children were readable; annotations returned a valid empty result; one 15-page PDF had 39,602 indexed characters; a bounded 1,000-character slice and a non-empty Better BibTeX citekey were returned |
| Codex representative-record E2E | Fresh read-only `codex exec` using the registered server | Passed after compatibility fix | Codex requested a page limit of 100; the server preserved the configured 50-record cap, returned one exact match, and Codex completed item, children, annotations, 200-character full-text, and citekey calls before emitting aggregate-only evidence |
| Live Research Agent routing | Four read-only `codex exec` delegation attempts | Blocked before subagent execution | Two attempts timed out while refreshing models; one reproduced Codex `0.147.0` rejecting explicit Agent type with a full-history fork; the explicit `fork_turns = none` retry did not produce a spawn before waiting. No Research Agent Zotero call occurred, so this layer is not counted as passed |

### Live read coverage

After a representative public paper became available in the configured library, the read smoke and direct MCP calls exercised:

- exact-title search with one match;
- exact item normalization and canonical-ref version state;
- child attachment and note retrieval;
- annotation discovery with a valid zero-annotation result;
- indexed PDF full-text slicing and pagination state;
- Better BibTeX citekey lookup.

Non-empty annotation normalization, multiple-PDF ambiguity handling, and multi-page result pagination remain fixture-backed rather than live-exercised.

The first representative-record Codex run exposed a page-limit compatibility failure: Codex selected 100 while the local safety cap was 50. A second fresh run still selected 100 after the tool schema default was capped, showing that schema guidance alone was insufficient for this client behavior. The server now treats the protocol-level limit as a requested upper bound and clamps it before backend I/O. The third identical run passed while the returned page state confirmed an effective limit of 50.

### Writes

No live Integration write was attempted. The representative record was already present when the post-request deduplication search ran, so the Integration neither created it nor created a duplicate. Writes remain disabled, and no Web API user ID or API key is configured. Create/update behavior is covered only by isolated contract tests.

Before claiming live write support, separately configure a narrow scope and Codex `writes` approval mode, designate a test parent, obtain explicit authorization, run the opt-in smoke command, inspect the resulting note, and clean it up manually in Zotero.
