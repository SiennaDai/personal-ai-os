---
name: visualization
description: Select and create clear diagrams, charts, plots, maps, and visual explanations from structured concepts, processes, comparisons, or data. Use to clarify relationships, sequences, hierarchies, comparisons, trends, or distributions. Do not use when prose or a compact table is clearer, and do not invent semantic relationships or data.
---

# Visualization

Create the smallest visual that materially improves understanding.

## Process

1. State the question the visual must answer and identify the critical relationship or pattern.
2. Inspect the source content or data. Preserve units, labels, direction, ordering, uncertainty, and provenance.
3. Choose the simplest suitable form:
   - table for exact mappings or compact comparisons
   - flowchart for processes and decisions
   - sequence diagram for interactions over time
   - hierarchy or mind map for containment and taxonomy
   - network or concept map for non-hierarchical relationships
   - line chart for trends, bar chart for comparisons, histogram for distributions, and scatter plot for associations
4. Remove elements that do not support the visual's question. Split dense visuals instead of shrinking labels or creating an unreadable graph.
5. Produce Markdown-native output by default. Prefer Mermaid for compatible diagrams and fenced source that remains editable in Git and Obsidian.
6. Validate labels, edges, values, scales, legends, syntax, and accessibility. Ensure the surrounding text communicates the key conclusion without relying on color alone.

## Quality rules

- Keep labels short but unambiguous.
- Use consistent direction and visual encoding.
- Avoid orphan nodes, redundant edges, distorted axes, decorative dimensions, and unsupported precision.
- Distinguish missing data from zero and correlation from causation.
- Use color sparingly and assign it semantic meaning.
- Include a concise text summary for accessibility and non-rendering environments.
- Do not create a visual when a sentence or small table is clearer.

## Coordination

Use `knowledge-mapping` to establish the nodes, relationship types, and evidence for concept or dependency graphs. This Skill controls visual selection and presentation; it must not invent semantic relationships.

If the requested target format requires HTML, SVG, PNG, or another rendered artifact, use an available rendering capability while retaining Markdown or text-based source when practical. Do not introduce a rendering dependency solely for a simple Markdown artifact.
