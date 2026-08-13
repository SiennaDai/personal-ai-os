---
name: knowledge-mapping
description: Build source-grounded concept maps, prerequisite graphs, and typed knowledge-relationship models from structured material. Use to expose dependencies, composition, contrast, applications, foundational concepts, or graph structure. Do not use for presentation-only styling or to infer relationships without source support.
---

# Knowledge Mapping

Model knowledge as concepts and explicit relationships without inventing connections.

## Process

1. Define the map's question and scope. Prefer a focused map over a complete but unreadable graph.
2. Use structured knowledge units as input. Invoke `knowledge-extraction` first when concepts and prerequisites have not been identified.
3. Normalize duplicate names and choose one stable label for each concept.
4. Create only meaningful nodes. Keep explanations in node notes rather than expanding them into unnecessary nodes.
5. Create directed, typed edges and state what each direction means.
6. Attach source locators or evidence to relationships when available. Mark inferred edges explicitly.
7. Validate the graph for duplicate nodes, unsupported edges, unexplained cycles, broken references, and isolated nodes.
8. Return the semantic map in Markdown. Use `visualization` when a rendered or presentation-oriented view is required.

## Relationship types

Use a small vocabulary appropriate to the material. Common types include:

- `requires`: the source concept depends on the target prerequisite
- `part-of`: the source concept is a component of the target
- `generalizes`: the source concept broadens the target
- `specializes`: the source concept narrows the target
- `contrasts-with`: the concepts differ in a meaningful way
- `applies-to`: the source concept is used in the target context
- `derived-from`: the source result follows from the target
- `example-of`: the source is an instance of the target

Add a new type only when none of these expresses the relationship accurately. Do not collapse different relationship meanings into a generic `related-to` edge unless the source supports nothing more precise.

## Output

Include, as applicable:

- map purpose and scope
- concept table with concise definitions and source locators
- relationship table with source, type, target, evidence, and inference status
- prerequisite ordering or learning path
- hubs, gaps, isolated concepts, conflicts, and uncertain edges
- optional Mermaid graph using the same semantic model

Keep the machine-readable relationship direction consistent between tables and diagrams. Do not treat visual proximity as evidence of a relationship.
