# Obsidian Integration Design Audit

## Scope

This audit records the evidence used to freeze Obsidian Integration contract `1.0`. It is intentionally privacy-preserving: no note body was read, no Vault file was created or changed, and no machine-specific Vault path, Vault name, registry identifier, username, or CLI installation path is recorded here.

Audit date: 2026-08-15.

## Local environment observations

The audited environment is Obsidian Desktop on Windows with Codex running in WSL2.

| Observation | Result |
|---|---|
| Application and installer version | `1.13.7` / `1.13.7` |
| Registered Vaults | Two; one active |
| Markdown files | One in each registered Vault at audit time |
| Other user files | None detected in either Vault at audit time |
| Vault symlinks or Git repositories | None detected |
| Connected Obsidian Sync configuration | None detected |
| Active-Vault community plugins relevant to architecture | Dataview and Zotero Integration |
| Local REST API plugin | Not installed |
| Official CLI | Installed, enabled during the audit, and reachable |

Plugin presence is observational, not an architectural dependency. The Obsidian Zotero Integration plugin does not replace Agent-owned cross-system orchestration, and Dataview does not become an Integration query backend in contract `1.0`.

## Privacy-preserving CLI probe

The official Windows terminal redirector was invoked directly with an explicit native Vault selector. The following read-only aggregate probes succeeded with exit code zero:

| Probe | Aggregate result |
|---|---:|
| `version` | `1.13.7 (installer 1.13.7)` |
| Markdown file count | 1 |
| Search for a generated guaranteed-no-match token | 0 |
| Distinct property count | 3 |
| Unresolved-link count | 1 |

The probe did not invoke `read`, `search:context`, recent-file listing, path listing, property values, link sources, or any mutating command. It established live CLI availability, explicit Vault targeting, scalar output, search execution, property-index access, and link-index access without disclosing note data.

The initial sequential probe included interactive execution-approval and application-startup overhead and therefore was not a CLI latency benchmark. After approval and with the application available, individual read commands completed in roughly `0.2–0.4` seconds in this environment. The CLI remains more lifecycle-dependent than direct file access, so the final design does not put exact content reads, revisions, or writes behind it.

## Official capability evidence

### Vault files

Obsidian documents a Vault as a local folder whose notes are Markdown plain text, supports external editors and file managers, and automatically refreshes external changes. This makes the filesystem the strongest available boundary for exact bytes, hashes, scoped paths, and atomic create/update behavior. See [How Obsidian stores data](https://help.obsidian.md/Files%2Band%2Bfolders/How%2BObsidian%2Bstores%2Bdata).

### Official CLI

The official CLI supports explicit Vault targeting and exposes file, search, link, backlink, property, tag, and other application-aware commands. It also exposes broad mutation, plugin, developer, and arbitrary command surfaces. A facade must therefore use a fixed command allowlist instead of proxying native CLI input. See [Obsidian CLI](https://help.obsidian.md/cli).

### Properties and links

Obsidian properties are YAML-backed typed metadata, while internal links can use wikilink or Markdown syntax and may be updated by the application on rename. The semantic index is more appropriate than a home-grown parser for resolved links, backlinks, and typed property reads. See [Properties](https://help.obsidian.md/Editing%2Band%2Bformatting/Properties) and [Internal links](https://help.obsidian.md/Linking%2Bnotes%2Band%2Bfiles/Internal%2Blinks).

### URI and Sync

Obsidian URI supports launch-oriented actions such as opening, searching, creating, appending, and overwriting, but it does not provide the structured result and optimistic concurrency boundary required here. Sync and File Recovery history are recovery/version features rather than a portable note revision protocol. See [Obsidian URI](https://help.obsidian.md/Extending%2BObsidian/Obsidian%2BURI) and [Version history](https://help.obsidian.md/Obsidian%2BSync/Version%2Bhistory).

## Candidate assessment

| Candidate | Decision | Reason |
|---|---|---|
| Direct Vault filesystem | Selected as required data plane | Officially supported external-file behavior; exact bytes; app-independent reads; enforceable scopes, hashes, and atomic replacement |
| Official Obsidian CLI | Selected as optional semantic plane | Product-native search, links, backlinks, and properties; enabled and verified locally; depends on compatible running app and has a broad native command surface |
| Obsidian URI | Rejected as backend | Launch/action oriented; no stable structured response or revision precondition |
| Community Local REST API | Not adopted | Not installed; adds port, token, plugin, and compatibility ownership without replacing filesystem conflict controls |
| Direct `.obsidian` or cache access | Rejected | Internal implementation state, not a stable public contract |
| Obsidian Sync/File Recovery history | Excluded | Recovery behavior is not the Integration's portable concurrency model |
| Dataview | Excluded from contract `1.0` | Installed plugin is not guaranteed across Vaults and would couple the contract to plugin-specific query semantics |
| Zotero Integration community plugin | Excluded from orchestration | Plugin presence must not create direct Zotero-to-Obsidian coupling |

## Frozen conclusion

The selected architecture is:

```text
Codex / Specialist Agent
        ↓ MCP stdio
AI-OS Obsidian facade
        ├── Vault filesystem
        │     exact Markdown + SHA-256 revisions + safe create/update
        └── official Obsidian CLI (optional)
              search + links/backlinks + parsed properties
```

The CLI changes the design materially, but it does not replace the filesystem. It supplies Obsidian-native semantic knowledge while the filesystem supplies the exact, conflict-protected data plane. No community plugin is required.

Implementation `1.0.0`, default-read-only runtime registration, and privacy-preserving live retrieval were subsequently verified. No production Vault write has been performed; the opt-in write smoke remains deliberately pending. The full behavior is defined in [INTEGRATION.md](INTEGRATION.md), with completion evidence in [VERIFICATION.md](VERIFICATION.md).
