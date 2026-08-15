# Research Agent Architecture Checks

## Agent boundary

- With a course lecture: `Help me learn this lecture for an exam.` Expected: route to Learning Agent, not Research Agent.
- With an academic paper: `Have the Research Agent read this paper and analyze its method.` Expected: Paper Analysis Mode; do not route paper reading to Learning Agent.

## Mode routing

- `Find recent work related to this research question.` Expected: Discovery Mode.
- `Compare the evidence in these three papers.` Expected: Evidence Synthesis Mode.
- `Use Research Design Mode to turn these gaps into a testable study.` Expected: explicit override is honored.

## Implicit Skill routing

- For one supplied paper: expect `document-understanding` and `knowledge-extraction`; use `stem-reasoning` only for genuine technical analysis. Do not use `literature-search` without a discovery need.
- For academic discovery: expect `literature-search`; do not claim that candidate metadata is inspected evidence.
- For several already-read papers: expect `evidence-synthesis`; do not invoke `literature-search` when the source set is intentionally closed.

## Research integrity

- Expected: distinguish metadata, abstract, and full-text evidence; preserve source locators; separate author claims from Agent inference; state inaccessible sources and coverage limits.

## Project isolation and artifacts

- Expected: inputs and Markdown Project Artifacts remain in the external Project; nothing is copied into `personal-ai-os`; no Zotero or Obsidian write is attempted while integrations are unavailable.
