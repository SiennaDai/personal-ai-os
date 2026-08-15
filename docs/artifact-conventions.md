# Artifact Conventions

## Canonical format

Markdown is the canonical format for durable AI artifacts. Other formats may be generated for delivery or interoperability, but Markdown remains the editable source when applicable.

## Frontmatter

Artifacts should use YAML frontmatter when structured metadata improves identification, discovery, or automation. Keep metadata minimal and use only fields relevant to the artifact.

Common fields include:

```yaml
---
title: Human-readable title
artifact_type: agent
status: draft
created: YYYY-MM-DD
updated: YYYY-MM-DD
references: []
---
```

`title` and `artifact_type` identify the artifact. Lifecycle dates, status, and references are optional unless a future artifact definition requires them. References to bibliographic material should point to Zotero information.

## Artifact types

Artifact types describe purpose rather than storage location. Initial categories may include Agent definitions, Skill definitions, integration specifications, conventions, operating principles, and archived Workflow design records. This is an extensible set, not a closed taxonomy.

Project-specific outputs are governed by their Project and remain outside this repository.

## Naming principles

- Use clear, durable names based on purpose rather than temporary context.
- Prefer lowercase kebab-case for file and directory names unless an established repository convention requires a canonical uppercase name.
- Use the `.md` extension for canonical artifacts.
- Avoid embedding versions or dates in names when frontmatter or version control can represent them.
- Keep names independent of project-specific identifiers.

Conventions should remain stable at the repository level and become more specific only when a defined artifact type requires it.
