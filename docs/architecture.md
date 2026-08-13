# Architecture v1

## Purpose and scope

`personal-ai-os` is the canonical editable source for reusable Agent definitions, Skill definitions, integration specifications, artifact conventions, and AI operating principles.

It does not store course materials, papers, project-specific files, personal notes, or Obsidian vault content. Projects and their artifacts remain independent and isolated outside this repository.

## Runtime architecture

```text
External Project -> Agent -> Skills
```

### Project

A Project is an isolated, task-specific working context. It supplies files, goals, constraints, and artifacts without moving them into `personal-ai-os`.

### Agent

An Agent is a reusable, user-facing assistant shared across unrelated Projects. It owns role, responsibilities, task routing, interaction policy, internal orchestration, Skill selection, and artifact behavior.

### Skill

A Skill is a modular reusable capability shared across Agents. Skills contain no Project-specific information. Codex discovers Skills from their `name` and `description`, then progressively loads `SKILL.md` when a task matches.

## Workflow status

Workflow is not a separately invoked runtime layer. A workflow may describe an Agent's internal orchestration, but that logic lives in the corresponding Agent definition. Historical standalone Workflow documents are retained under `archive/workflows/` as design history.

## Canonical source and Codex runtime

- **Canonical Agent source:** `personal-ai-os/agents/<agent>/`
- **Codex personal Agent runtime:** `~/.codex/agents/*.toml`
- **Canonical Skill source:** `personal-ai-os/skills/<skill>/`
- **Codex personal Skill discovery:** `~/.agents/skills/<skill>/`

Runtime Agent TOML files are generated from canonical Agent instructions. They are deployment projections, not separately maintained design documents. User-level Skill directories should link to canonical repository Skill directories so repository changes propagate without copying. Prefer symbolic links; NTFS directory junctions are the Windows fallback when symlink privilege is unavailable.

Do not confuse `skills/<skill>/agents/openai.yaml`, which is Skill metadata, with `~/.codex/agents/*.toml`, which defines Codex custom Agents.

## Artifact principle

Markdown is the canonical durable artifact format because it is human-readable, version-controllable, compatible with Obsidian and Git, and convertible to other formats.

## External systems

### Zotero

Zotero is the bibliographic source of truth for papers, metadata, citations, and the PDF library. AI-generated notes reference Zotero information rather than replacing it.

### Obsidian

Obsidian is the long-term knowledge management system for connected concepts, permanent notes, and the knowledge graph. It consumes Markdown artifacts.

### Git

Git provides version control for canonical AI-OS configuration, Agent definitions, Skills, and archived design history. Project repositories remain separate.
