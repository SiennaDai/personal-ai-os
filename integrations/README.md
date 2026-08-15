# Integrations

Integrations give the Codex runtime controlled access to external systems. They perform external-system I/O through stable contracts; they do not perform domain reasoning, classify artifacts, or orchestrate Agents or other integrations.

The active Integration Layer architecture is defined in [Integration Layer Architecture](../docs/integration-architecture.md).

## System role

```text
External Project
      ↓
Codex Main Runtime
      ↓
Specialist Agent / Subagent
      ├── Skills
      │     reasoning and methodology
      │
      └── MCP tool surface
              ↓
        Integration boundary
        contract + policy + adapter
              ↓
           Backend
              ↓
        External System
```

The three durable information roles remain distinct:

```text
Zotero    → Sources
Project   → Work
Obsidian  → Knowledge
```

Project artifacts remain in the active external Project by default. Zotero remains the bibliographic source of truth. Obsidian receives only explicitly authorized Knowledge Artifacts.

## Architectural principles

1. Integrations perform external-system I/O; they do not perform domain reasoning.
2. Agents orchestrate integrations; integrations do not orchestrate Agents or other integrations.
3. External systems remain their domain sources of truth.
4. Integrations expose stable semantic contracts independent of backend-specific formats.
5. MCP is the Codex-facing delivery interface; it does not replace the semantic contract.
6. Machine-specific paths, credentials, tokens, and secrets never belong in the canonical repository.
7. Read, create, update, and destructive or bulk operations have explicitly different safety policies.
8. Artifact classification does not authorize external publication; Obsidian publication requires explicit user authorization by default.
9. Zotero and Obsidian implementations remain independent. Cross-system flows are composed by the executing Agent.
10. Contracts are tested and compatibility-managed even when an integration is delivered as one complete implementation rather than artificial product phases.

## Required integration contract

Each implemented integration must document:

- purpose, ownership, and explicit non-responsibilities;
- required and optional capabilities;
- canonical identifiers, input and output schemas, provenance, and error semantics;
- selected backend and any adapter or facade boundary;
- MCP tools, operational instructions, limits, and approval behavior;
- configuration ownership and secret handling;
- read, create, update, destructive, and bulk safety policy;
- static validation, contract tests, read-only doctor checks, opt-in write tests, and relevant Agent-level evaluation;
- dependency pinning or remote compatibility monitoring, compatibility policy, and upgrade procedure.

The MCP server may be maintained in this repository or supplied by a version-governed third party. A custom server or adapter is required only when the adopted implementation cannot satisfy the canonical contract and safety policy directly.

## Configuration ownership

Integration configuration is deliberately split:

- this repository stores example configuration, stable contracts, and deployment logic;
- `~/.codex/config.toml` registers MCP servers and controls server and tool policy;
- `~/.config/personal-ai-os/integrations.toml` may hold machine-specific non-secret backend settings;
- environment variables, OAuth, or an appropriate secret store provide credentials and tokens.

Deployment automation may manage only entries it explicitly owns. It preserves unrelated user configuration and fails safely on ownership conflicts.

## Verification levels

Integration checks are separated by external effect:

1. **Static validation:** repository structure, schemas, configuration shape, dependency declarations, and tool inventory.
2. **Contract and adapter tests:** normalized behavior using fixtures or isolated test doubles.
3. **Read-only doctor:** local configuration, connectivity, authentication, capability discovery, and representative reads.
4. **Opt-in write smoke test:** explicit create or update against a designated test library, collection, or vault only.
5. **Cross-Agent evaluation:** the executing Agent selects the correct integration, preserves provenance, and respects artifact and publication policy.

A default validation or doctor command must not mutate a production Zotero library or Obsidian vault.

## Current status

- [Zotero](zotero/README.md): implemented; official Local API reads, optional Better BibTeX citekeys, gated Web API writes, and an AI-OS-owned MCP facade.
- [Obsidian](obsidian/README.md): implemented; required Vault-filesystem data plane, optional official-CLI semantic plane, five default read tools, and two gated single-note writes.

Both runtimes are deployed through `scripts/sync-integrations.sh` with read-only tool inventories by default. This does not permit either Integration to call the other or collapse Sources, Work, and Knowledge into one store.
