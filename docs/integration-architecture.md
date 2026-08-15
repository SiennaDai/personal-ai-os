# Integration Layer Architecture

## Status

Approved architecture baseline. Zotero and Obsidian are implemented and deployed with default-read-only MCP surfaces. Obsidian contract `1.0` freezes its hybrid backend and safety boundary; opt-in production write validation and interactive cross-integration regression testing remain separate follow-up checks.

## Purpose and scope

The Integration Layer gives the Codex runtime narrow, testable access to external systems without moving external-system behavior into Agents or Skills. It defines stable capabilities, data boundaries, safety policy, configuration ownership, and verification requirements.

This document freezes the common Integration Layer architecture. It does not select a Zotero or Obsidian backend, define their final tool inventories, implement an MCP server or adapter, register runtime configuration, or authorize external reads or writes.

## Runtime architecture

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

The Codex Main Runtime remains user-facing. The executing Specialist Agent decides whether an external-system operation is needed and combines the result with relevant Skills. MCP supplies the Codex-facing tool surface. The Integration boundary owns stable external-I/O semantics and safety. The backend performs the system-specific operation.

An integration is a runtime capability, not a separately invoked Workflow and not a component embedded inside one Agent. Multiple Agents may use the same integration when the task requires it.

## Layer responsibilities

| Layer | Owns | Does not own |
|---|---|---|
| External Project | Current files, task context, working artifacts, and Project-specific decisions | Canonical Agent or Skill configuration, bibliographic truth, or the long-term knowledge base |
| Codex Main Runtime | User interaction, delegation, permissions, and the active tool environment | External-system domain truth |
| Specialist Agent | Domain orchestration, routing, artifact classification, and decisions about when an integration is appropriate | Backend protocols, credentials, or system-specific data translation |
| Skill | Reusable reasoning, methodology, and cognitive procedures | External-system access or publication |
| Integration | Stable external-I/O contract, safety policy, normalization, configuration boundary, and operational checks | Domain reasoning, artifact-value decisions, or cross-integration orchestration |
| MCP surface | Codex-facing tool transport, schemas, descriptions, server instructions, and runtime approval metadata | Source-of-truth ownership or domain reasoning |
| Adapter | Translation between the stable Integration contract and backend-specific behavior | Agent orchestration or independent domain decisions |
| Backend | Concrete API, local service, filesystem, or other justified access mechanism | AI-OS policy |
| External System | Canonical domain data and system-native behavior | Project task orchestration |

The adapter is a logical implementation boundary. It may be a thin pass-through when an adopted MCP server already satisfies the contract. A custom facade or server is justified when translation, safety enforcement, stability, or missing behavior requires it.

## Information ownership

The following distinction is invariant:

```text
Zotero    → Sources
Project   → Work
Obsidian  → Knowledge
```

### Zotero

Zotero is the bibliographic source of truth for papers, bibliographic metadata, identifiers, citations, collections, attachments, and other Zotero-native records. An integration may retrieve or perform explicitly authorized operations on those records, but it must not create a competing bibliographic truth in Project or Obsidian artifacts.

### External Project

The external Project is the active work context. Searches, analyses, drafts, evidence matrices, learning materials, models, code, and other task-specific artifacts remain in the Project by default.

### Obsidian

Obsidian is the long-term knowledge layer for durable Markdown knowledge and explicit relationships. A Project artifact does not enter Obsidian merely because an Agent classifies it as reusable. Publication requires explicit user authorization by default.

## Integration invariants

1. Integrations perform external-system I/O; they do not perform domain reasoning.
2. Agents orchestrate integrations; integrations never call Agents or other integrations to compose workflows.
3. External systems remain their domain sources of truth.
4. Stable Integration contracts shield Agents from backend-specific formats and connection details.
5. MCP is the Codex-facing delivery interface; the semantic contract remains an AI-OS responsibility.
6. Integrations are independently deployable and testable. Zotero and Obsidian implementations do not depend on each other.
7. Machine-specific paths, credentials, tokens, personal data, and external-system content never enter the canonical repository.
8. Read, create, update, destructive, and bulk operations have distinct safety behavior.
9. Default validation and doctor checks are non-mutating.
10. Complete initial delivery does not imply an immutable implementation; contract compatibility and migration remain explicit.

## MCP decision

Every implemented Integration exposes its Codex-facing capabilities through MCP. This makes tool discovery, structured input and output, runtime policy, and cross-Agent reuse consistent without embedding backend code in Agent definitions.

The architecture does not require every Integration to own a new MCP server. The per-integration design must choose among:

- adopting a maintained MCP server whose behavior already satisfies the contract;
- wrapping an existing MCP server or backend with an AI-OS-owned facade;
- implementing an AI-OS-owned MCP server when no suitable implementation exists.

Adopted third-party packages must be version-pinned, license-reviewed, covered by contract tests, and updated intentionally. Managed remote servers must have an explicit compatibility and change-monitoring policy when the provider does not expose a pinnable version. Runtime commands must not silently select an unpinned latest package.

MCP server instructions may describe operational constraints that apply across tools, such as call ordering, rate limits, conflict checks, and safe write procedures. Domain reasoning and artifact classification remain in Agents and Skills.

## Stable contract requirements

Each Integration receives a canonical `INTEGRATION.md` when its design begins. That contract must define the following before implementation is considered complete.

### Purpose and capabilities

- responsibilities and explicit non-responsibilities;
- required capabilities needed for the accepted use cases;
- optional capabilities that depend on a backend or locally installed extension;
- capability-discovery behavior when optional functions are unavailable.

### Identity and provenance

- stable references for external objects;
- source-system identity and native canonical identifiers;
- version, revision, or modification information when the external system exposes it;
- provenance sufficient for downstream artifacts to trace their inputs.

Normalization must not erase canonical external identifiers or silently turn incomplete metadata into asserted fact. Backend-native fields may be preserved in a clearly separated extension field when lossless access is needed.

### Tool semantics

- tool name, purpose, and risk class;
- complete input and output schemas;
- pagination, ordering, filtering, and result limits;
- maximum content size and handling of large full text or attachments;
- idempotency and retry behavior;
- timeout and partial-result behavior;
- error taxonomy, including invalid configuration, not found, permission denied, conflict, backend unavailable, and unsupported capability.

### Concurrency and mutation

Updates and overwrites must use an available version, revision, hash, or modification-time precondition rather than silently replacing unknown newer content. Filesystem writes must be atomic where practical. Create and update tools must return the resulting canonical reference and revision state.

### Compatibility

The contract records a compatibility version independently from roadmap labels. Backward-compatible additions, breaking schema changes, backend upgrades, and migrations must be distinguishable and documented. Delivering Zotero or Obsidian as one complete implementation does not remove this requirement.

## Safety model

Integration operations use four risk classes:

| Class | Examples | Default policy |
|---|---|---|
| Read | Search, metadata lookup, note read, capability discovery | Available when configured; no mutation |
| Create | Create a new external record or note | Controlled write with explicit scope and a returned canonical reference |
| Update | Change or overwrite an existing record or note | Controlled write with conflict protection and preview where practical |
| Destructive or bulk | Delete, move across protected boundaries, or mutate many records | Disabled or omitted by default; requires separate justification and explicit authorization |

Safety is enforced at multiple boundaries:

- the Integration contract declares the risk and effects of each tool;
- the MCP surface accurately identifies read-only and mutating operations;
- Codex runtime configuration uses server and tool allowlists and approval policy;
- the adapter enforces target roots, identifiers, preconditions, and operation limits;
- the Agent obtains any required semantic authorization from the user.

### Publication authorization

Artifact classification and external publication are separate decisions:

```text
Agent classification
      ↓
Knowledge Artifact candidate
      ↓
Explicit user authorization
      ↓
Runtime tool approval when required
      ↓
Obsidian Integration write
```

Runtime approval is an execution safeguard; it does not by itself establish that the user wants a Project artifact stored permanently. A future standing publication policy is permitted only when the user explicitly defines its scope and may revoke it.

### Scope isolation

Filesystem-backed integrations must use configured allowlisted roots, canonicalize paths, reject traversal and symlink escapes, and avoid arbitrary filesystem access. External-service integrations must restrict operations to configured accounts, libraries, collections, or equivalent scopes where the backend permits it.

## Configuration planes

Configuration is unified conceptually but separated by ownership and sensitivity:

| Plane | Location | Contents |
|---|---|---|
| Canonical source | `personal-ai-os/integrations/` | Contracts, non-secret examples, dependency declarations, and deployment logic |
| Codex MCP runtime | `~/.codex/config.toml` | Server registration, transport, enablement, tool allowlists, timeouts, and approval policy |
| Integration runtime | `~/.config/personal-ai-os/integrations.toml` | Machine-specific non-secret backend selection, paths, library identifiers, and operational settings |
| Secret source | Environment, OAuth storage, or an appropriate secret store | API keys, bearer tokens, credentials, and refreshable authorization |

Secrets must not be placed in tracked examples. Prefer forwarding named environment variables or using OAuth rather than storing secret values in either repository or generated runtime configuration.

Deployment automation may modify only entries it can prove it owns. It must preserve unrelated Codex and user configuration, be safe to rerun, and fail rather than overwrite an unexpected value. The exact merge or registration mechanism is deferred until the first Integration implementation demonstrates the required behavior.

The personal AI-OS integrations are cross-Project runtime capabilities, so their normal registration is user-scoped. A Project-scoped registration is an explicit exception and must not become Project-specific canonical configuration in this repository.

Codex MCP registration and tool-policy behavior should remain aligned with the [official MCP configuration documentation](https://learn.chatgpt.com/docs/extend/mcp?surface=cli).

## Verification architecture

Verification is separated so routine checks cannot create external side effects.

### 1. Static validation

Runs without credentials or a live external system. It checks repository structure, contract completeness, configuration schemas, dependency pinning, MCP tool inventory, and policy declarations.

### 2. Contract and adapter tests

Use fixtures, isolated temporary storage, or controlled test doubles to verify normalization, errors, pagination, limits, path safety, conflict behavior, and compatibility without touching personal external-system data.

### 3. Read-only doctor

Checks local configuration, dependency availability, server startup, authentication, capability discovery, connectivity, and representative reads. It reports unsupported optional capabilities distinctly from broken required capabilities.

### 4. Opt-in write smoke test

Runs only after explicit authorization and only against a designated test library, collection, vault, or temporary isolated target. It verifies create and update behavior, conflict protection, and returned identifiers. Cleanup is explicit and must not rely on an unreviewed broad delete.

### 5. Cross-Agent evaluation

Uses a real Codex execution path to verify that relevant Agents:

- select integrations only when external I/O is necessary;
- choose the correct read or write operation;
- preserve source identity and provenance;
- keep Project Artifacts in the external Project by default;
- obtain explicit publication authorization;
- compose Zotero and Obsidian only through Agent orchestration.

Passing static validation does not establish live connectivity. Passing a doctor does not authorize or prove production writes. Each completion claim must name the level actually exercised.

## Agent routing and permissions

Expected use by Agent is guidance rather than a rigid ACL:

| Agent | Zotero | Obsidian |
|---|---|---|
| Learning | Context-dependent | Context-dependent |
| Research | Core | Important |
| Writing | Core | Context-dependent |
| Coding | Uncommon but permitted when task-relevant | Context-dependent |
| Modeling | Context-dependent | Context-dependent |

Access control applies to tools, operation classes, configured scopes, and user authorization rather than Agent names. Agent definitions should refer to stable semantic capabilities and artifact policy, not backend-specific commands or native response formats.

Agent definitions treat each Integration as available only when its implementation is deployed and its relevant health check passes. Zotero- and Obsidian-aware routing are active; unavailable or degraded optional capabilities still fail explicitly.

## Cross-integration orchestration

Integrations never call one another. A representative flow is:

```text
Zotero
  ↓
Research Agent
  ↓
Research Skills
  ↓
Project research artifact
  ↓
Explicit Knowledge Artifact publication decision
  ↓
Obsidian
```

The Project artifact remains a reviewable boundary between source retrieval, reasoning, and long-term publication. Direct Zotero-to-Obsidian synchronization is outside this Integration Layer.

## Repository shape

The target structure is intentionally small:

```text
integrations/
├── README.md
├── config.example.toml          # unified non-secret configuration example
├── zotero/
│   ├── README.md                # setup and operation guide
│   ├── INTEGRATION.md           # canonical contract
│   ├── src/                     # AI-OS-owned MCP facade and adapter
│   └── tests/                   # contract and adapter tests
└── obsidian/
    ├── README.md
    ├── INTEGRATION.md
    ├── AUDIT.md                 # privacy-preserving backend evidence
    ├── src/
    └── tests/
```

Shared production abstractions such as `common/`, `BaseIntegration`, `IntegrationManager`, or `IntegrationFactory` are not introduced speculatively. Repeated implementation evidence must justify any shared component.

`scripts/sync-integrations.sh` and `scripts/validate-integrations.sh` deploy and validate both implementations. Obsidian joins the existing entry points and does not create separate runtime orchestration.

## Implementation sequence

```text
Integration Layer Architecture
        ↓
Zotero contract + backend + implementation + deployment + verification
        ↓
Obsidian contract + backend + implementation + deployment + verification
        ↓
Cross-integration and cross-Agent evaluation
```

There are no artificial v1, v2, or MCP-later stages. Each Integration is complete only when its accepted capabilities, contract, safety policy, configuration, deployment, tests, doctor, and Agent usage are implemented and verified. Optional capabilities may remain explicitly unsupported when they are outside the accepted contract.

## Resolved and deferred per-integration decisions

Zotero-specific choices are frozen in [`integrations/zotero/INTEGRATION.md`](../integrations/zotero/INTEGRATION.md): official Local API reads, optional Better BibTeX citekeys, gated Web API writes, a dependency-free AI-OS MCP facade, stable tool names and schemas, and no delete or bulk surface.

Obsidian-specific choices are frozen in [`integrations/obsidian/INTEGRATION.md`](../integrations/obsidian/INTEGRATION.md): an AI-OS-owned MCP facade, required Vault-filesystem data plane, optional official-CLI semantic plane, SHA-256 optimistic concurrency, non-root write scopes, five default read tools, two gated single-note writes, and no delete, move, rename, append, prepend, property/task mutation, attachment, or bulk surface. The supporting local and official-interface evidence is in [`integrations/obsidian/AUDIT.md`](../integrations/obsidian/AUDIT.md).

Obsidian implementation `1.0.0` uses dependency-free Python 3 standard-library code. Future implementation or dependency changes may not alter the frozen contract without compatibility management. Whether a later Integration justifies a destructive or bulk tool remains deliberately unfrozen.
