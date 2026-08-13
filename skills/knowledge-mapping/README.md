# Knowledge Mapping

## Design rationale

This skill is built from scratch. Search identified broader ingestion systems and tool-specific graph generators, but no mature component matched the required minimum: a project-independent semantic model for concepts, prerequisites, and typed relationships.

The skill separates knowledge modeling from rendering. `knowledge-mapping` establishes nodes and evidence-backed edges; `visualization` presents them.

## Input and output

- **Input:** structured concepts and relationships, normally from `knowledge-extraction`, plus an optional mapping question or scope.
- **Output:** a Markdown concept inventory, typed edge list, prerequisite ordering, validation findings, and an optional Mermaid representation.
