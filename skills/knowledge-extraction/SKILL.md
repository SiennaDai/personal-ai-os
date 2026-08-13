---
name: knowledge-extraction
description: Convert structured learning or research material into reusable knowledge units covering concepts, definitions, relationships, assumptions, examples, methods, and prerequisites. Use for lecture-mode or research-mode extraction and source-grounded Markdown preparation. Do not use before raw or unreadable source material has been structured, and do not invent unsupported knowledge.
---

# Knowledge Extraction

Extract reusable, source-grounded knowledge from structured material.

## Process

1. Confirm the supplied material is readable and structured enough to analyze. Use `document-understanding` first when raw source extraction is still required.
2. Select lecture mode, research mode, or a minimal general schema from the material and the user's goal. Do not force a mode when neither fits.
3. Identify atomic knowledge units and separate source claims from inferred relationships.
4. Preserve provenance with page, slide, section, cell, line, or citation locators when available.
5. Link related units and prerequisites without duplicating their full content.
6. Mark absent, ambiguous, conflicting, or inferred information explicitly.
7. Return concise Markdown suitable for reuse by other Skills or storage in a Project.

## Core schema

Extract only fields supported by the source:

- concepts
- definitions
- relationships
- assumptions
- examples
- methods
- prerequisites

For each unit, prefer a stable name, concise statement, source locator, and relevant links to other units.

## Lecture mode

Organize the result around:

- key concepts
- formulas, including symbol meanings and conditions
- prerequisites
- worked or illustrative examples
- exam relevance when stated or reasonably inferable; label inference

## Research mode

Organize the result around:

- research question
- method
- contribution
- limitation

Keep author claims distinct from the extractor's interpretation. Do not invent novelty, evidence, or limitations not supported by the material.

## Boundaries

Do not add project-specific facts to the Skill definition. Do not replace Zotero bibliographic records; reference Zotero identifiers or source metadata when available. Follow the repository's Markdown artifact conventions for saved outputs.
