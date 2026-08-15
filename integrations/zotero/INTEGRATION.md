# Zotero Integration Contract

## Contract status

- Contract version: `1.0`
- MCP server version: `1.0.0`
- Status: implemented; read-only runtime deployment is the default
- Source of truth: Zotero
- Canonical transport: local MCP over stdio

This contract is the stable AI-OS boundary for Zotero. It follows the common [Integration Layer Architecture](../../docs/integration-architecture.md). Compatible additions may extend the contract; any removal, semantic change, or incompatible schema change requires a new contract version and an explicit migration.

## Purpose and ownership

The Integration performs narrow external-system I/O against one configured Zotero library. It retrieves Zotero records, preserves their native identity and version, normalizes backend JSON for Agents, and performs only explicitly enabled single-object writes.

Zotero remains authoritative for:

- bibliographic items and metadata;
- collections and collection membership;
- attachments and indexed full text;
- Zotero notes and PDF annotations;
- native item keys and object versions;
- Better BibTeX citation keys when that optional extension is available.

The Integration does not:

- evaluate source quality, summarize papers, synthesize evidence, or write literature reviews;
- decide whether an item, note, or Project Artifact is important;
- copy bibliographic truth into the Project or Obsidian as a competing record;
- orchestrate Agents, Skills, or the Obsidian Integration;
- discover literature outside the configured Zotero library;
- enrich DOI or other metadata through third-party services;
- directly read or write `zotero.sqlite`;
- expose arbitrary files, attachment bytes, delete, bulk mutation, collection mutation, tag replacement, creator replacement, or file upload.

Research, learning, writing, coding, and modeling decisions remain with the executing Agent and its Skills. Search results and bibliographic metadata are not equivalent to inspected full-text evidence.

## Backend decision

The Integration owns a small dependency-free facade rather than adopting a general-purpose third-party Zotero MCP server. This keeps the tool inventory, stable output schema, safety annotations, write gates, response bounds, and error taxonomy under the AI-OS contract.

| Capability | Selected backend | Rationale |
|---|---|---|
| Default reads | Zotero API v3 local endpoint at loopback `/api` | Official boundary; fast, offline-capable, and avoids direct SQLite coupling |
| WSL-to-Windows read transport | Windows system `curl.exe` subprocess | Reaches Windows loopback without port forwarding or opening Zotero to another interface |
| Optional web reads | Zotero Web API v3 | Supports a configured remote library when explicitly selected |
| Indexed full text | Zotero API v3 full-text endpoint | Preserves Zotero attachment identity and indexing state |
| Citation keys | Better BibTeX JSON-RPC `item.citationkey` | Narrow optional access to the installed citekey authority |
| Controlled writes | Zotero Web API v3 | Available on the installed Zotero 9 environment; supports API-key permissions and version preconditions |
| Codex delivery | AI-OS-owned MCP stdio server | Stable structured output and an intentionally small safety surface |

The official local API must stay on loopback and must never be port-forwarded or exposed to another host. Under WSL, `local_transport = "auto"` selects the fixed Windows system curl path and invokes it without a shell so the request originates in the Windows network namespace. Direct Linux HTTP remains available for a native Linux Zotero process. Neither transport follows redirects. The configured Web API origin is restricted to `https://api.zotero.org` so an API key cannot be redirected to an arbitrary service.

Zotero 10 and later can authorize local API writes at runtime, but contract `1.0` does not implement that authorization flow. Adding it later may be backward-compatible if it preserves the same tool semantics and safety rules. The current Web write backend always re-reads the target from the Web API before enforcing scope and version; a later local read may lag until Zotero synchronizes.

Primary backend references:

- [Zotero Web API v3 basics](https://www.zotero.org/support/dev/web_api/v3/basics)
- [Zotero local API](https://www.zotero.org/support/dev/web_api/v3/local_api)
- [Zotero full-text content](https://www.zotero.org/support/dev/web_api/v3/fulltext_content)
- [Zotero write requests](https://www.zotero.org/support/dev/web_api/v3/write_requests)
- [Better BibTeX JSON-RPC](https://retorque.re/zotero-better-bibtex/exporting/json-rpc/index.html)
- [Codex MCP configuration](https://learn.chatgpt.com/docs/extend/mcp?surface=cli)

## Capability discovery

`zotero_status` is the non-mutating capability check. It reports:

- parsed configuration without secret values;
- representative read connectivity and the library version header when available;
- Better BibTeX enablement, availability, and reported versions;
- whether writes are enabled and locally ready;
- an overall result used by the doctor command.

Better BibTeX is optional. Its failure does not make ordinary Zotero reads unhealthy. Write tools are not returned by `tools/list` unless `write_enabled = true` passes static configuration validation. A direct call to a hidden or disabled write tool is rejected.

## MCP tool inventory

### Default read tools

| Tool | Semantics | Important limits |
|---|---|---|
| `zotero_status` | Non-mutating configuration and connectivity check | Returns no library content |
| `zotero_search_items` | Search normalized items by Zotero `q`/`qmode`, type, collection, or tag | Non-empty query; paginated; top-level items by default |
| `zotero_get_item` | Retrieve one exact item by native key | One configured library only |
| `zotero_list_collections` | List all, top-level, or direct child collections | Paginated |
| `zotero_get_collection_items` | Retrieve items in one collection | Paginated; top-level items by default |
| `zotero_get_item_children` | Retrieve direct child notes, attachments, or annotations | Paginated; optional native `itemType` filter |
| `zotero_get_annotations` | Traverse an item or attachment to normalized PDF annotations | Maximum 500 discovered child objects per call |
| `zotero_get_fulltext` | Return one bounded character slice of indexed PDF full text | Multiple PDFs require an explicit attachment key |
| `zotero_get_citation_key` | Resolve one Better BibTeX citekey | Optional BBT capability; no key regeneration |

All nine tools have MCP `readOnlyHint = true`, `destructiveHint = false`, `idempotentHint = true`, and `openWorldHint = false`. The configured Zotero library is treated as a closed external scope.

### Gated write tools

| Tool | Risk class | Semantics and guard |
|---|---|---|
| `zotero_create_child_note` | Create | Creates one child note under an existing in-scope item; requires a caller-supplied 32-hex-character idempotency token |
| `zotero_update_note` | Update | Replaces one note body; requires the exact current item version |
| `zotero_update_item_fields` | Update | Patches up to eight allowlisted scalar fields on one bibliographic item; requires the exact current item version |

Create is marked non-destructive and non-idempotent in MCP metadata because reusing a Zotero write token yields a conflict instead of a second success. Updates are marked destructive because they replace existing values and idempotent because an identical request cannot apply twice with the same version.

The scalar update allowlist is:

```text
title
abstract
date
short_title
url
doi
isbn
issn
language
rights
extra
```

Arrays and structured fields are deliberately omitted: creators, tags, collection membership, relations, attachments, and annotation positions cannot be replaced by this tool. No delete or bulk tool exists.

## Stable identity and provenance

Every item reference has this logical form:

```json
{
  "id": "zotero:personal:item:ABCD2345",
  "system": "zotero",
  "kind": "item",
  "library": {
    "alias": "personal",
    "type": "user",
    "id": "123456"
  },
  "key": "ABCD2345",
  "version": 42
}
```

Collection references use `kind = "collection"` and `zotero:<alias>:collection:<key>`. The configured `library_alias` is the stable AI-OS scope name; the native numeric library ID remains present. Zotero's native eight-character key is never replaced or inferred. A version is omitted only when an optional backend lookup cannot supply it, such as a standalone Better BibTeX citekey result.

Normalized items preserve:

- item type, title, creators, date, parsed date, and abstract;
- publication title, publisher, place, and series;
- DOI, ISBN, ISSN, and PMID when supplied by Zotero;
- URL, language, pages, volume, and issue;
- tags, collection keys, parent key, relations, and native dates;
- attachment, note, or annotation fields when applicable;
- retrieval backend, retrieval time, and canonical Zotero URL when supplied.

Normalization does not assert missing data and does not expose a backend-native `raw` escape hatch. Backward-compatible normalized fields can be added later; Agents must not depend on undocumented Zotero-native JSON.

## Result envelope

Every successful tool call returns both MCP text content containing serialized JSON and identical `structuredContent`:

```json
{
  "contract_version": "1.0",
  "ok": true,
  "data": {}
}
```

Expected Integration failures remain MCP tool results with `isError = true`:

```json
{
  "contract_version": "1.0",
  "ok": false,
  "error": {
    "code": "NOT_FOUND",
    "message": "The requested Zotero object was not found",
    "retryable": false,
    "details": {}
  }
}
```

JSON-RPC errors are reserved for malformed protocol requests, an unknown or disabled tool name, and unsupported methods.

## Pagination, ordering, and content bounds

Paginated results include:

```json
{
  "start": 0,
  "limit": 20,
  "returned": 20,
  "total": 57,
  "has_more": true,
  "next_start": 20
}
```

The runtime `max_page_size` defaults to 50 and cannot exceed 100. MCP page limits are requested upper bounds from 1 through 100; the server clamps both explicit and default limits to the configured cap before backend I/O. Search defaults to `dateModified desc`; collection listing uses title order; child listing uses `dateAdded`. The backend `Total-Results` header is authoritative when supplied.

Full text defaults to at most 20,000 characters per call and returns `offset`, `returned_chars`, `total_chars`, `truncated`, and `next_offset`. The configured per-call character limit cannot exceed 100,000. The whole backend response is also byte-bounded. If a parent has multiple PDF attachments, the tool returns `AMBIGUOUS_ATTACHMENT` with candidates instead of silently choosing one.

Note bodies default to a maximum of 50,000 characters. The server rejects active HTML constructs such as scripts, embedded frames, JavaScript URLs, and event-handler attributes. It does not silently rewrite note content.

## Error taxonomy

| Code | Meaning | Retry behavior |
|---|---|---|
| `CONFIG_NOT_FOUND`, `CONFIG_INVALID` | Missing or invalid local settings | Fix configuration |
| `INVALID_ARGUMENT`, `LIMIT_EXCEEDED` | Contract input or bound violation | Correct the request |
| `AUTHENTICATION_REQUIRED`, `PERMISSION_DENIED` | Missing/invalid API key, local API disabled, or insufficient permission | Fix credentials or Zotero settings |
| `NOT_FOUND`, `FULLTEXT_UNAVAILABLE`, `AMBIGUOUS_ATTACHMENT` | Object/content absent or selection underspecified | Inspect refs and select explicitly |
| `BACKEND_UNAVAILABLE`, `RATE_LIMITED` | Zotero/BBT unreachable, server error, or rate limit | Retry only when `retryable = true`; honor retry metadata |
| `BACKEND_PROTOCOL_ERROR`, `OPTIONAL_BACKEND_ERROR` | Unexpected backend response | Diagnose backend/version compatibility |
| `UNSUPPORTED_CAPABILITY`, `OPTIONAL_CAPABILITY_UNAVAILABLE` | Backend or optional BBT function unavailable | Use a supported capability or change configuration |
| `WRITE_DISABLED`, `WRITE_SCOPE_DENIED`, `CONFIRMATION_REQUIRED` | A write safety gate rejected the operation | Obtain authority and configure a narrow scope |
| `VERSION_CONFLICT`, `BACKEND_CONFLICT` | Stale object version, reused write token, or locked library | Re-read; do not silently retry a mutation |
| `WRITE_FAILED` | Zotero rejected an individual create | Inspect returned failure details |

Backend messages are bounded before inclusion in error details. Secrets and request arguments are never logged.

## Write safety and concurrency

Writes require all of these independent conditions:

1. `write_enabled = true` in the untracked runtime configuration.
2. `web_library_id` names the intended native user or group library.
3. The environment variable named by `api_key_env` supplies a write-capable Zotero API key.
4. `write_scope` is explicitly `collections` with at least one allowlisted collection key, or intentionally `library`.
5. The write tool is visible to Codex and accurately marked mutating.
6. Codex uses `default_tools_approval_mode = "writes"` or a stricter policy.
7. The executing Agent has explicit semantic authorization from the user for that mutation.

Collection-scoped writes re-read the target through the Web API. A child note or attachment is checked through its parent bibliographic item. An item outside all allowlisted collections is rejected.

Updates preflight the current object version and send `If-Unmodified-Since-Version`. A mismatch returns `VERSION_CONFLICT`; the Integration never fetches a new version and silently overwrites it. Creates send Zotero's `Zotero-Write-Token`. Retrying a create requires deliberate handling of an ambiguous result and must not substitute a new token automatically.

## Configuration and secrets

Canonical non-secret settings are documented in [`../config.example.toml`](../config.example.toml). Runtime settings live at:

```text
~/.config/personal-ai-os/integrations.toml
```

Codex registers the stdio server in:

```text
~/.codex/config.toml
```

The Zotero API key remains in the environment under the configured name, normally `ZOTERO_API_KEY`. It must not be written into this repository, the Integration TOML, MCP arguments, test fixtures, logs, or Project artifacts. When writes are later enabled, the MCP registration must forward only that named variable with `env_vars = ["ZOTERO_API_KEY"]` and use `default_tools_approval_mode = "writes"` or `"prompt"`.

The configuration loader rejects unknown Zotero fields, an unknown local transport, non-loopback local/BBT URLs, an unofficial Web API origin, invalid IDs, unsafe write combinations, and out-of-range limits. `local_transport` accepts only `auto`, `direct`, or `windows`; it never accepts an arbitrary executable. The deployment script installs the example only when no runtime configuration exists and never overwrites an existing file.

## Deployment and operations

Static validation:

```bash
./scripts/validate-integrations.sh
```

Idempotent read-only deployment:

```bash
./scripts/sync-integrations.sh
```

The sync command validates the repository, installs a mode-`600` runtime configuration only when absent, registers the exact pinned local Python entry point with `codex mcp add`, and rejects an existing registration with a different command or argument list. It does not start Zotero, add credentials, enable writes, or mutate a Zotero library.

Read-only doctor:

```bash
python3 integrations/zotero/src/zotero_mcp_server.py \
  --config ~/.config/personal-ai-os/integrations.toml doctor
```

The doctor performs no mutations. Zotero must be running with local API access enabled. Better BibTeX failure is reported separately as an optional degradation.

Privacy-preserving representative read smoke:

```bash
python3 integrations/zotero/src/zotero_mcp_server.py \
  --config ~/.config/personal-ai-os/integrations.toml read-smoke
```

This command exercises library, collection, exact-item, search, child, annotation, full-text, and citekey paths where representative records exist. It returns only pass/fail state and capability booleans—never titles, creators, item keys, note content, annotations, full text, or citekeys. An empty library or a bounded sample without a PDF is reported as not exercised rather than fabricated success.

An opt-in write smoke test exists but must not be run without explicit authorization and a designated test parent item:

```bash
python3 integrations/zotero/src/zotero_mcp_server.py \
  --config ~/.config/personal-ai-os/integrations.toml \
  write-smoke \
  --parent-item-key ABCD2345 \
  --confirm CREATE_AND_UPDATE_ZOTERO_TEST_NOTE
```

It creates and updates exactly one tagged child note, reports its canonical ref, and never deletes it. Cleanup is a separate manual Zotero action so a failed test cannot trigger broad or unreviewed deletion.

## Verification requirements

Completion evidence is layered:

1. Static and contract tests validate configuration, direct and Windows-loopback transports, normalization, HTTP bounds, errors, scope, version conflicts, MCP lifecycle, tool inventory, annotations, structured output, and stdio framing without personal data or a live service.
2. The doctor validates the configured real read backend and optional Better BibTeX without returning library content.
3. A representative live read validates search, exact item retrieval, collections, children, full text, and citekey only when suitable records exist.
4. A write smoke test remains unverified until separately authorized against a designated test item.
5. Cross-Agent evaluation verifies that Agents distinguish metadata from evidence, preserve refs, keep Project Artifacts in the Project, and request authority before writes.

No static test or read-only doctor proves or authorizes production writes.

Current environment-specific evidence and deliberately unverified surfaces are recorded in [VERIFICATION.md](VERIFICATION.md).

## Agent usage policy

- Research Agent: use Zotero as the primary library source for candidate discovery, metadata, attachments, annotations, and full text; apply research Skills only after retrieval.
- Writing Agent: use Zotero refs, versions, metadata, and citekeys for citation-grounded work; do not infer source claims from metadata.
- Learning and Modeling Agents: use Zotero when a task genuinely needs source I/O; hand literature discovery or evidence synthesis to the Research Agent where appropriate.
- Coding Agent: may use Zotero when reproducing or implementing a paper, but Zotero is not a general code or package integration.

Agent routing is guidance, not an Agent-name ACL. Tool risk, configured scope, runtime approval, and user authorization enforce permissions.
