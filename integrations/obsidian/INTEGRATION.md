# Obsidian Integration Contract

## Contract status

- Contract version: `1.0`
- Implementation version: `1.0.0`
- Status: implemented; default-read-only runtime deployment and live reads verified; live production writes intentionally unverified
- Source of truth: the configured Vault
- Codex transport: local MCP over stdio

This contract is the stable AI-OS boundary for Obsidian. It follows the common [Integration Layer Architecture](../../docs/integration-architecture.md). Compatible additions may extend the contract; removing a tool or field, changing established semantics, or weakening a safety guarantee requires a new contract version and an explicit migration.

## Purpose and ownership

The Integration performs narrow external-system I/O against one configured Vault. It discovers and reads Markdown notes, exposes bounded Obsidian-aware search and link information, and performs only explicitly authorized single-note publication or replacement.

Obsidian remains authoritative for:

- durable Markdown knowledge notes;
- Vault-relative note identity and organization;
- Obsidian properties, internal links, backlinks, and unresolved-link state;
- application-maintained semantic indexes and metadata-cache behavior.

The Integration does not:

- decide whether a Project Artifact is durable knowledge;
- draft, summarize, classify, restructure, merge, or refactor knowledge by itself;
- publish merely because an Agent classified an artifact as reusable;
- treat the Vault as the active Project workspace;
- copy Zotero bibliographic records into a competing source of truth;
- orchestrate Agents, Skills, Zotero, or another Integration;
- expose arbitrary filesystem paths, non-Markdown attachments, or `.obsidian` configuration;
- execute arbitrary Obsidian CLI commands, JavaScript, plugin operations, UI commands, or Sync operations;
- delete, move, rename, append, prepend, bulk-edit, or mutate individual properties or tasks.

Agents and Skills own knowledge decisions and content creation. The Integration is an executor, not a decision maker.

## Backend decision

Contract `1.0` selects an AI-OS-owned hybrid facade with two deliberately unequal backend roles:

| Role | Selected backend | Responsibility |
|---|---|---|
| Required data plane | Vault filesystem | Exact Markdown bytes, bounded enumeration and reads, SHA-256 revisions, path confinement, create-if-absent, and conflict-protected atomic replacement |
| Optional semantic plane | Official Obsidian CLI | Obsidian query semantics, outgoing links, backlinks, and parsed property reads |
| Codex delivery | AI-OS-owned MCP stdio server | Stable schemas, capability discovery, policy enforcement, bounds, errors, and tool annotations |

This is not a runtime choice between interchangeable implementations. Filesystem access is always authoritative for note content and revisions. The CLI contributes application semantics when it is explicitly configured, supported, and connected to the same Vault.

The filesystem is a supported Obsidian boundary: a Vault is a local folder of Markdown files, external editors are supported, and Obsidian refreshes external changes. The official CLI is preferred over a community REST plugin for semantic reads because it is product-native and already exposes exact Vault targeting, search, links, backlinks, and properties. Primary references:

- [How Obsidian stores data](https://help.obsidian.md/Files%2Band%2Bfolders/How%2BObsidian%2Bstores%2Bdata)
- [Obsidian CLI](https://help.obsidian.md/cli)
- [Obsidian properties](https://help.obsidian.md/Editing%2Band%2Bformatting/Properties)
- [Obsidian internal links](https://help.obsidian.md/Linking%2Bnotes%2Band%2Bfiles/Internal%2Blinks)

The following alternatives are deliberately excluded:

- Obsidian URI is a launch/action interface, not a structured, conflict-safe backend.
- A Local REST API community plugin is not required and would add token, port, plugin-lifecycle, and compatibility responsibilities without improving the required filesystem guarantees.
- Sync and File Recovery history are recovery features, not the Integration's revision or concurrency protocol.
- Obsidian's internal cache files and `.obsidian` configuration are implementation details and are never read as a data backend.

## Official CLI boundary

When `cli_enabled = true`, the adapter invokes a configured official CLI executable directly as an argument vector, never through a shell. The Vault selector is always the first CLI parameter. The implementation allowlists only the commands needed to back these semantic operations:

```text
version
files ... total
search ... format=json
links
backlinks ... format=json
properties ... format=json
unresolved ... format=json
```

The adapter must never accept a native command name or arbitrary native options from an MCP caller. In particular, `command`, `eval`, `dev:*`, `plugin:*`, `sync*`, `create`, `append`, `prepend`, `move`, `rename`, `delete`, `property:set`, `property:remove`, task mutation, application restart, and application reload are outside the allowlist.

The official CLI is an optional capability because it depends on a compatible desktop installation, an enabled CLI setting, and a reachable running application. The Integration never starts, restarts, reloads, or reconfigures Obsidian. If the CLI is unavailable, exact filesystem tools remain healthy while Obsidian-semantic operations return `OPTIONAL_CAPABILITY_UNAVAILABLE`; they never silently switch to different query or link semantics.

The implementation initially supports the locally audited official CLI family `1.13.x`. A different feature version must pass fixtures and a live compatibility check before the supported range changes. Installer and application versions are both reported by the doctor when available, without exposing installation paths or Vault selectors.

## Capability discovery

`obsidian_status` is the non-mutating capability check. It reports:

- the configured Vault alias and contract version, but not its absolute path;
- whether the Vault, configured read roots, and configured write roots pass confinement checks;
- Markdown note counts by configured read root, subject to the enumeration cap;
- filesystem read readiness and write enablement/readiness separately;
- CLI enablement, reachability, version compatibility, and semantic capabilities;
- whether the configured CLI selector resolves to the same canonical Vault path;
- an overall `healthy`, `degraded`, or `unavailable` state.

`healthy` means required filesystem reads are ready and every explicitly enabled optional backend is ready. A CLI failure produces `degraded`, not `unavailable`, unless the requested operation requires CLI semantics. A missing or unsafe Vault makes the Integration `unavailable`.

Write tools are absent from `tools/list` unless `write_enabled = true` and static write-scope validation succeeds. A direct call to a hidden or disabled write tool is rejected.

## MCP tool inventory

### Default read tools

| Tool | Backend | Semantics |
|---|---|---|
| `obsidian_status` | Filesystem + optional CLI | Privacy-preserving configuration, health, capability, and aggregate-count report |
| `obsidian_list_notes` | Filesystem | List bounded note summaries below an allowed read root in stable path order |
| `obsidian_search_notes` | Filesystem or CLI, selected explicitly by `mode` | Bounded literal content search or Obsidian-query search returning note summaries |
| `obsidian_get_note` | Filesystem + optional CLI properties | Read an exact bounded content slice and revision; optionally include parsed Obsidian properties |
| `obsidian_get_links` | CLI | Return bounded outgoing links, backlinks, or both using Obsidian's semantic index |

All five default tools have MCP `readOnlyHint = true`, `destructiveHint = false`, `idempotentHint = true`, and `openWorldHint = false`. The configured Vault and read roots are a closed local scope.

### Gated write tools

| Tool | Risk class | Semantics and guard |
|---|---|---|
| `obsidian_publish_note` | Create | Create one UTF-8 Markdown note only if its exact path is absent; an existing byte-identical note is an idempotent success and different content is a conflict |
| `obsidian_update_note` | Update | Replace one complete UTF-8 Markdown note only when the caller supplies its exact current SHA-256 revision |

`obsidian_publish_note` is marked non-destructive and idempotent. `obsidian_update_note` is marked destructive because it replaces current content and idempotent because an ambiguous retry succeeds only when the current bytes already equal the requested bytes. Neither tool opens the note in the UI.

No delete, move, rename, append, prepend, property mutation, task mutation, attachment write, directory creation outside an allowed write root, or bulk tool exists in contract `1.0`.

## Canonical tool schemas

The implementation expresses these rules as closed JSON Schemas with `additionalProperties = false`. Integers are non-negative unless a stricter bound is stated. A caller identifies an existing note with exactly one of `ref` or `path`; ambiguous or duplicate identity fields are rejected.

| Tool | Input fields | Successful `data` fields |
|---|---|---|
| `obsidian_status` | none | `state`, `vault_alias`, `filesystem`, `cli`, `writes`, `counts` |
| `obsidian_list_notes` | `folder?`, `start = 0`, `limit = configured default` | `notes`, `page`, `retrieved_at` |
| `obsidian_search_notes` | `query`, `mode`, `folder?`, `case_sensitive = false`, `include_excerpt = false`, `start = 0`, `limit = configured default` | `mode`, `query`, `matches`, `page`, `truncated`, `retrieved_at` |
| `obsidian_get_note` | exactly one of `ref` or `path`; `offset = 0`, `max_chars = configured default`, `include_properties = false` | `note`, `content`, `content_page`, `properties?`, `provenance`, `retrieved_at` |
| `obsidian_get_links` | exactly one of `ref` or `path`; `direction = "both"`, `limit = configured default` | `note`, `outgoing?`, `backlinks?`, `truncated`, `provenance`, `retrieved_at` |
| `obsidian_publish_note` | `path`, `content` | `state = "created" | "already_present"`, `note`, `semantic_index` |
| `obsidian_update_note` | exactly one of `ref` or `path`; `content`, `expected_revision` | `state = "updated" | "already_current"`, `note`, `previous_revision`, `semantic_index` |

`mode` is exactly `literal` or `obsidian`. `case_sensitive` and `include_excerpt` are valid only for literal mode; sending either as true with Obsidian mode is rejected. `direction` is exactly `outgoing`, `backlinks`, or `both`. A write `content` value is the entire future note, not a patch or append payload.

A normalized note summary has this stable shape:

```json
{
  "id": "obsidian:knowledge:note:concepts/attention.md",
  "system": "obsidian",
  "kind": "note",
  "vault": {"alias": "knowledge"},
  "path": "concepts/attention.md",
  "revision": "sha256:0123456789abcdef...",
  "size_bytes": 4812,
  "modified_ns": 1786752000000000000
}
```

`page` contains `start`, `limit`, `returned`, `has_more`, and `next_start`. A literal-search match contains a note summary and, only when requested, `excerpt`, `excerpt_start`, and `excerpt_truncated`. An Obsidian-search match contains a note summary and no excerpt. Every CLI-returned path is normalized, checked against the filesystem read scope, and hashed before it becomes a result.

`content_page` contains `offset`, `returned_chars`, `total_chars`, `truncated`, and `next_offset`. Parsed properties retain only JSON-compatible scalar or list values supplied by the official CLI and include their CLI provenance; unknown output types produce `BACKEND_PROTOCOL_ERROR` rather than lossy coercion.

Resolved link entries contain `target`, a normalized note summary, and an optional count. Unresolved outgoing entries contain a bounded `target`, `resolved = false`, and an optional count. Backlinks must resolve to an in-scope Markdown note. Link results never include matching line text.

## Stable identity and provenance

Obsidian does not assign a durable native object ID to an ordinary Markdown note. Contract `1.0` therefore uses the scoped Vault-relative path identity shown in the normalized note summary above.

The `vault_alias` is a lowercase AI-OS scope name. `path` always uses `/`, is relative to the Vault root, and includes `.md`. The canonical ID uses the UTF-8, RFC 3986 percent-encoded path with `/` preserved. The example above contains only unreserved characters and therefore needs no escapes.

A path remains the canonical identity only while the note stays at that path. Move and rename are omitted from this contract, so the Integration never claims stable identity across either operation. Agents must preserve the exact returned ID, path, revision, and retrieval time in downstream provenance when those details matter.

`revision` is `sha256:` followed by the lowercase SHA-256 digest of the complete file bytes, even when only a content slice is returned. `modified_ns` is informational and never substitutes for the digest in an update precondition.

## Common result envelope

Every successful tool call returns MCP text content containing serialized JSON and identical `structuredContent`:

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
    "code": "REVISION_CONFLICT",
    "message": "The note changed after it was read",
    "retryable": false,
    "details": {}
  }
}
```

JSON-RPC errors are reserved for malformed protocol requests, unsupported methods, and unknown or disabled tool names.

## Read semantics and bounds

### List notes

`obsidian_list_notes` accepts `folder`, `start`, and `limit`. `folder` defaults to the first configured read root and must itself be within an allowed read root. Notes are ordered by normalized Vault-relative path, not filesystem traversal order. Each result contains identity, revision, byte size, and modification time but no content or inferred title.

Pagination uses `start`, `limit`, `returned`, `has_more`, and `next_start`. It is a bounded snapshot convenience, not a transactional directory view; callers that require a current revision must call `obsidian_get_note` before acting.

### Search notes

`obsidian_search_notes` requires a non-empty `query` and an explicit `mode`:

- `literal` performs a bounded, non-regex UTF-8 substring search over allowed Markdown files. `case_sensitive` is supported. Results include a bounded matching excerpt only when `include_excerpt = true`.
- `obsidian` sends the query as one opaque value to the allowlisted official CLI `search` command with JSON output. It preserves Obsidian query semantics and returns matching note summaries without line context. It requires a healthy CLI capability.

The Integration never interprets an Obsidian query as a shell fragment. It does not silently run `search:context`, semantic/vector search, fuzzy ranking, or a regex engine. Search results are discovery evidence, not permission to publish or update a note.

### Get note

`obsidian_get_note` accepts exactly one canonical note ID or exact Vault-relative path, plus `offset`, `max_chars`, and `include_properties`. It returns:

- the normalized note identity and full-file revision;
- a Unicode content slice with `offset`, `returned_chars`, `total_chars`, `truncated`, and `next_offset`;
- `properties` only when requested and the CLI property capability succeeds;
- explicit backend provenance for filesystem content and optional CLI metadata.

The full file must fit `max_note_bytes` before any slice is returned. Invalid UTF-8 or a NUL byte is rejected rather than silently rewritten. A properties request never falls back to an ad hoc YAML parser; unavailable CLI semantics return `OPTIONAL_CAPABILITY_UNAVAILABLE`.

### Get links

`obsidian_get_links` accepts an exact note ID or path and `direction = "outgoing"`, `"backlinks"`, or `"both"`. Resolved links include canonical refs and paths. Unresolved outgoing links preserve a bounded display target and `resolved = false`; they do not invent a path. Duplicate link counts may be included when supplied by the CLI. Results are capped and report truncation.

## Path and content safety

Every filesystem operation must enforce all of these rules before access:

1. Resolve from the configured Vault root and a configured read or write root; never from the process working directory.
2. Accept only normalized Vault-relative paths with `/` separators and a lowercase-insensitive `.md` suffix.
3. Reject empty components, `.`, `..`, absolute paths, drive-qualified paths, UNC paths, alternate data streams, NULs, control characters, and Windows-reserved names or trailing dots/spaces.
4. Reject `.obsidian`, `.trash`, `.git`, and every hidden path component regardless of configured root.
5. Reject symbolic links, junctions, reparse-point escapes, and any path whose canonical containment cannot be established. Every existing component is checked; containment is checked again after opening where the platform permits.
6. Detect case-fold collisions. A request is rejected when its spelling does not identify one unambiguous existing path on the current filesystem.
7. Never return the absolute Vault path, host username, native Vault selector, or CLI executable path in tool output.

Reads and writes are limited to UTF-8 Markdown text. Contract `1.0` does not expose images, PDFs, canvases, bases, CSS, plugin data, or arbitrary attachments. Note content is encoded exactly as supplied for writes; the Integration does not insert templates, properties, tags, links, line-ending conversions, or a final newline implicitly.

## Limits and ordering

The implementation exposes configurable defaults within hard contract ceilings:

| Bound | Default | Hard ceiling |
|---|---:|---:|
| Page or search results | 50 | 100 |
| Full note size | 2,000,000 bytes | 10,000,000 bytes |
| Returned content per call | 50,000 characters | 200,000 characters |
| Literal-search candidate files | 10,000 | 50,000 |
| Literal-search bytes scanned | 64,000,000 bytes | 256,000,000 bytes |
| Link results per direction | 200 | 1,000 |
| CLI response | 8,000,000 bytes | 16,000,000 bytes |
| CLI request timeout | 30 seconds | 60 seconds |

Exceeding a bound returns `LIMIT_EXCEEDED` or an explicit truncated result as defined by the operation. CLI stdout and stderr are byte-bounded before parsing or reporting. Environment-specific paths and note content are never included in diagnostic errors.

## Error taxonomy

| Code | Meaning | Caller action |
|---|---|---|
| `CONFIG_NOT_FOUND`, `CONFIG_INVALID` | Runtime settings are missing or invalid | Correct local configuration |
| `VAULT_UNAVAILABLE`, `BACKEND_UNAVAILABLE` | Vault or required filesystem access is unavailable | Restore local access |
| `CLI_UNAVAILABLE`, `CLI_INCOMPATIBLE`, `OPTIONAL_CAPABILITY_UNAVAILABLE` | Official CLI is disabled, unreachable, mismatched, or unsupported | Start/configure a compatible Obsidian instance or use a filesystem capability |
| `INVALID_ARGUMENT`, `INVALID_PATH`, `PATH_OUTSIDE_SCOPE` | Input or path violates the contract | Correct the request |
| `SYMLINK_DENIED`, `CASE_COLLISION`, `PROTECTED_PATH` | Containment or protected-path policy rejected access | Select an unambiguous allowed Markdown path |
| `NOT_FOUND`, `ALREADY_EXISTS` | Exact note is absent or create target already differs | Re-read or select another target |
| `ENCODING_ERROR`, `LIMIT_EXCEEDED` | Content is unsupported or exceeds a bound | Correct or narrow the operation |
| `WRITE_DISABLED`, `WRITE_SCOPE_DENIED`, `CONFIRMATION_REQUIRED` | A write gate rejected mutation | Obtain authorization and configure a narrow scope |
| `REVISION_CONFLICT` | Current SHA-256 differs from the update precondition | Re-read and review; never retry silently |
| `WRITE_FAILED` | Atomic create or replacement did not complete | Inspect state before any retry |
| `BACKEND_PROTOCOL_ERROR` | CLI output violated the supported contract | Diagnose version compatibility |

Expected filesystem races and CLI failures are converted to this bounded taxonomy. Raw command lines, absolute paths, complete stderr, environment variables, and note bodies are never logged.

## Write safety and concurrency

Writes require all of these independent conditions:

1. `write_enabled = true` in the untracked runtime configuration.
2. `allowed_write_roots` contains at least one non-root subdirectory and the target is inside it.
3. The write tool is visible to Codex and accurately annotated.
4. Codex uses `default_tools_approval_mode = "writes"` or a stricter policy.
5. The executing Agent has explicit semantic authorization from the user to publish or replace this Knowledge Artifact.
6. The operation supplies its create or revision precondition and passes path, content, and size validation.

The Vault root (`.`) is forbidden as a write root. Read scope may include the whole Vault, but write scope must be narrower. Runtime approval is an execution gate and never substitutes for publication intent.

### Create

`obsidian_publish_note` uses create-if-absent semantics. Parent directories may be created only beneath an allowed write root after every component passes confinement checks. The final file is installed atomically without overwriting an existing path. If the path already contains byte-identical content, the call returns `already_present`; if it differs, it returns `ALREADY_EXISTS`.

This makes an ambiguous retry idempotent without storing a hidden write token in the Vault.

### Update

`obsidian_update_note` requires `expected_revision`. Immediately before replacement, the adapter hashes the current bytes. A mismatch returns `REVISION_CONFLICT`. If the current bytes already equal the requested bytes, an ambiguous retry returns `already_current`; otherwise the adapter writes a same-directory temporary file, flushes it, and atomically replaces the target where supported.

The implementation must test actual atomic-replacement and durability behavior on the deployed WSL-to-Windows filesystem. It must document any platform limitation rather than claim a stronger transaction guarantee. Obsidian and another editor can still race after the final precondition check; the contract provides optimistic conflict protection, not distributed locking.

Neither write path calls the CLI. Obsidian observes the external file change through its supported filesystem behavior and refreshes its metadata asynchronously. A successful file write does not imply that the CLI semantic index has already caught up; write results report `semantic_index = "pending_or_unknown"`.

## Configuration

Canonical non-secret settings are documented in [`../config.example.toml`](../config.example.toml). Runtime settings live at:

```text
~/.config/personal-ai-os/integrations.toml
```

The Obsidian section owns:

- `vault_alias` and machine-specific `vault_path`;
- allowed read roots and separately allowlisted write roots;
- CLI enablement, executable path, and native Vault selector;
- operation limits and timeouts;
- the default-off write gate.

The actual Vault path, native selector, installed executable path, Vault names, note paths, and note content never belong in this repository. The CLI needs no Integration-managed API token. The configuration loader must reject unknown fields, invalid aliases, unsafe root combinations, relative Vault paths, unsupported CLI executable shapes, and out-of-range limits.

When CLI is enabled, startup validation confirms that its resolved Vault path is canonically equal to `vault_path`. Matching only the active Vault name is insufficient.

## Deployment and operations

Obsidian uses the existing Integration entry points rather than standalone runtime orchestration:

```bash
./scripts/validate-integrations.sh
./scripts/sync-integrations.sh
```

The sync command preserves unrelated Codex configuration, owns only `mcp_servers.obsidian`, preserves an existing runtime Integration file unless an explicit migration is required, and fails on an unexpected registration. It does not start Obsidian, enable its CLI, create a Vault, install a plugin, expose write tools by default, or write note content.

The non-mutating doctor validates configuration, containment, aggregate note counts, CLI version/connectivity, and same-Vault targeting. It returns no note names, paths, properties, links, search matches, or content.

The opt-in write smoke test must require a designated subdirectory already covered by `allowed_write_roots` and an explicit confirmation phrase. It creates and updates exactly one uniquely named Markdown note, reports only its canonical ref and revisions, never deletes it automatically, and leaves cleanup as a separately reviewed Vault action.

## Verification state

The implementation has the following verification state:

1. Static and contract tests cover configuration, path normalization, protected paths, symlinks/reparse points, case collisions, UTF-8 and size limits, hashing, pagination, errors, MCP framing, tool annotations, and hidden write tools.
2. Filesystem adapter tests use an isolated temporary Vault to cover reads, idempotent create, stale-revision rejection, same-directory replacement, and failures without personal content.
3. CLI adapter fixtures cover exact argument vectors, output limits, JSON parsing, version gates, timeouts, same-Vault checks, and rejection of every non-allowlisted native command.
4. A privacy-preserving live doctor validates the real Vault and enabled official CLI without returning note data. **Passed.**
5. A representative privacy-preserving live read validates exact retrieval, both search modes, properties, outgoing links, and backlinks. **Passed.**
6. An opt-in write smoke remains unverified until explicitly authorized against a designated test root.
7. Agent definitions encode Project-first behavior, explicit publication authorization, provenance, conflict handling, and Agent-owned Zotero-to-Obsidian orchestration. Interactive cross-Agent evaluation remains a separate regression layer.

No design document, static test, doctor, or read-only probe proves or authorizes production writes.

## Agent usage policy

- Research Agent: may retrieve existing durable knowledge and publish an explicitly approved research artifact; bibliographic truth remains in Zotero.
- Writing Agent: may consult durable notes and publish only an explicitly approved reusable writing artifact, never a transient draft by default.
- Learning Agent: may retrieve prior knowledge and publish an explicitly approved durable concept note after classification.
- Coding and Modeling Agents: may consult or publish durable technical knowledge when task-relevant; generated project code, results, and run artifacts stay in the Project by default.

Routing is guidance, not an Agent-name ACL. Tool risk, configured roots, runtime approval, revision preconditions, and user authorization enforce permissions. Agents use Obsidian only when the Integration is present and the relevant health check passes.
