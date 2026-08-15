# Architecture v1

## Purpose and scope

`personal-ai-os` is the canonical editable source for reusable Agent definitions, Skill definitions, integration specifications, artifact conventions, and AI operating principles.

It does not store course materials, papers, project-specific files, personal notes, or Obsidian vault content. Projects and their artifacts remain independent and isolated outside this repository.

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
      └── Integrations through MCP
              ↓
        External Systems
```

### Project

A Project is an isolated, task-specific working context. It supplies files, goals, constraints, and artifacts without moving them into `personal-ai-os`.

### Agent

An Agent is a reusable Codex custom Specialist Agent/subagent shared across unrelated Projects. The Codex Main Runtime remains user-facing and delegates suitable work to the Agent. The Agent owns its domain role, orchestration and routing policies, interaction policy, artifact policy, and guidance for selecting relevant Skills.

### Skill

A Skill is a modular reusable capability shared across Agents. Skills contain no Project-specific information. Codex discovers Skills from their `name` and `description`, then progressively loads `SKILL.md` when a task matches.

### Integration

An Integration is a reusable, controlled external-system I/O capability shared across Agents. It exposes a stable semantic contract to Codex through MCP while isolating Agents from backend-specific protocols, paths, credentials, and data formats. Integrations do not perform domain reasoning, classify artifacts, or orchestrate Agents or other integrations.

The common contract, safety model, configuration planes, and verification requirements are defined in [Integration Layer Architecture](integration-architecture.md).

## Workflow status

Workflow is not a separately invoked runtime layer. A workflow may describe an Agent's internal orchestration, but that logic lives in the corresponding Agent definition. Historical standalone Workflow documents are retained under `archive/workflows/` as design history.

### Codex Main Runtime

Codex is the primary user-facing runtime. A user opens Codex in an isolated external Project, asks for an outcome, and Codex delegates to a Specialist Agent when appropriate. The user need not manually choose Skills, although explicit Skill invocation remains available.

### personal-ai-os

This repository is the canonical source for Specialist Agent definitions, Skills, Integration contracts and implementation, AI-OS architecture, deployment scripts, and evals. It is configuration infrastructure, not a Project container or a separate AI-OS launcher.

## Canonical source and Codex runtime

- **Only canonical editable source:** `/home/sienna/projects/personal-ai-os` in WSL
- **Windows clone:** legacy/non-canonical copy; do not edit it or generate runtime configuration from it

- **Canonical Agent source:** `personal-ai-os/agents/<agent>/`
- **Codex personal Agent runtime:** `~/.codex/agents/*.toml`
- **Canonical Skill source:** `personal-ai-os/skills/<skill>/`
- **Codex personal Skill discovery:** `~/.agents/skills/<skill>/`

Runtime Agent TOML files are generated from canonical Agent instructions. They are deployment projections, not separately maintained design documents. User-level Skill directories are symbolic links to canonical repository Skill directories, so repository changes propagate without copying.

Do not confuse `skills/<skill>/agents/openai.yaml`, which is Skill metadata, with `~/.codex/agents/*.toml`, which defines Codex custom Agents.

## Artifact principle

Markdown is the canonical durable artifact format because it is human-readable, version-controllable, compatible with Obsidian and Git, and convertible to other formats.

## External systems

The durable information roles remain distinct:

```text
Zotero    → Sources
Project   → Work
Obsidian  → Knowledge
```

Agents may compose external-system operations with Skills, but Integrations never call one another. Project artifacts stay in the active external Project by default.

### Zotero

Zotero is the bibliographic source of truth for papers, metadata, citations, and the PDF library. Its implemented MCP Integration uses official API boundaries and returns stable refs and versions; it does not perform research reasoning. AI-generated notes and Project artifacts reference Zotero information rather than replacing it.

### Obsidian

Obsidian is the long-term knowledge management system for connected concepts, permanent notes, and the knowledge graph. It consumes explicitly authorized Markdown Knowledge Artifacts; classification alone does not authorize publication.

### Git

Git provides version control for canonical AI-OS configuration, Agent definitions, Skills, and archived design history. Project repositories remain separate.
