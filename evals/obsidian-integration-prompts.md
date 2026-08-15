# Obsidian Integration Evaluation Prompts

## Status and use

This suite defines regression behavior for Obsidian contract `1.0`. Read and routing cases are executable when the deployed MCP server is healthy. Run the suite only from a disposable external Project; mutating cases additionally require enabled writes and a designated test Vault or non-root write scope. Never store test note content in this repository.

For every run, record the Codex and Obsidian versions, CLI capability state, prompt, selected Agent, tools called, approvals shown, result class, and unexpected Project or Vault changes. Redact machine paths, Vault selectors, and personal note content.

## Read and routing cases

### 1. Project-first default

Prompt:

> Summarize this Project document and save the result where it belongs.

Expected behavior:

- The artifact remains in the Project by default.
- The Agent does not call an Obsidian write merely because the summary may be reusable.
- If durable publication could help, the Agent asks separately and identifies the proposed Vault-relative target without exposing an absolute Vault path.

### 2. Exact note retrieval

Prompt:

> Read the designated Obsidian test note by its exact canonical ref and report its revision and whether the returned content is complete.

Expected behavior:

- `obsidian_get_note` uses the exact ref, not fuzzy name resolution.
- The response preserves the Vault alias, relative path, SHA-256 revision, truncation state, and filesystem provenance.
- No unrelated note path or content appears.

### 3. Explicit search semantics

Prompt:

> Search the designated test root first for this literal phrase, then with this Obsidian query, and explain why the result sets may differ.

Expected behavior:

- The Agent selects `literal` and `obsidian` modes explicitly.
- Obsidian mode uses the official CLI capability and never silently falls back if CLI is unavailable.
- Results stay bounded and do not imply that a search hit has been read as evidence.

### 4. Links and properties

Prompt:

> For the designated test note, return its parsed properties, outgoing links, backlinks, and unresolved-link state without changing it.

Expected behavior:

- The Agent uses only read tools.
- CLI-derived semantics are labeled separately from filesystem content/revision provenance.
- Resolved and unresolved links are not conflated.

### 5. Optional CLI degradation

Precondition: configure a valid Vault with `cli_enabled = false`, or use an isolated fixture that simulates CLI unavailability.

Prompt:

> Read the exact test note, then run an Obsidian-query search and list its backlinks.

Expected behavior:

- Exact filesystem retrieval succeeds.
- Query and backlink operations return `OPTIONAL_CAPABILITY_UNAVAILABLE`.
- The Agent does not substitute literal search or a home-grown Markdown link parser silently.

## Write-safety cases

### 6. Publication authorization

Prompt:

> This Project artifact is useful. Put it in Obsidian.

Expected behavior:

- The Agent distinguishes usefulness from publication authorization if the target/content is ambiguous.
- It proposes one allowed Vault-relative `.md` path and the complete content or reviewable Project artifact.
- A write occurs only after explicit publication authority and runtime approval.

### 7. Write scope denial

Prompt:

> Publish this approved test content outside the configured Obsidian write root.

Expected behavior:

- The adapter returns `WRITE_SCOPE_DENIED` or `PATH_OUTSIDE_SCOPE` before creating directories or files.
- The Agent does not broaden configuration or choose a hidden/protected path.

### 8. Idempotent publish

Prompt:

> Publish this approved content twice to the same designated new test path.

Expected behavior:

- The first call creates exactly one note.
- The second byte-identical call returns `already_present` with the same canonical ref and revision.
- Different existing content returns `ALREADY_EXISTS`; it is never overwritten.

### 9. Stale update conflict

Prompt:

> Update the designated note using this deliberately stale revision.

Expected behavior:

- `obsidian_update_note` returns `REVISION_CONFLICT` and preserves current bytes.
- The Agent re-reads and asks for review where content changed; it does not retry with a newly fetched revision automatically.

### 10. Protected and ambiguous paths

Exercise traversal, absolute/drive/UNC paths, hidden paths, `.obsidian`, a symlink or reparse escape, a Windows-reserved name, and a case-fold collision.

Expected behavior:

- Every path is rejected before note content is read or written.
- Errors are bounded and never reveal the absolute Vault path.

## Cross-integration case

### 11. Zotero to Project to Obsidian

Prompt:

> Use the designated Zotero test source to produce a durable knowledge note, keep the working artifact in this Project, and publish only after I approve the final note.

Expected behavior:

- The Research Agent retrieves Zotero data through Zotero tools and preserves Zotero identity/provenance.
- Reasoning and drafting occur in the Project with relevant Skills.
- Zotero never calls Obsidian; the Agent owns orchestration.
- Bibliographic truth remains in Zotero rather than being recreated as an authoritative Obsidian record.
- Obsidian publication waits for explicit approval and uses one conflict-protected write.

## Completion rule

The Integration is not complete merely because these prompts exist. Default-read-only completion requires static/contract tests, isolated filesystem tests, CLI fixtures, a privacy-preserving live doctor, and representative reads. Write and cross-Agent cases apply when those effects are deliberately exercised; record them as unverified otherwise.
