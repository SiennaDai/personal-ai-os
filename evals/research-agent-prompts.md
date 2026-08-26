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
- For academic discovery: expect `literature-search`; do not claim that candidate metadata is inspected evidence. When the Zotero 10 local write scope explicitly names `临时工作区`, expect verified and screened-in records to be deduplicated and imported there unless the prompt opts out.
- For several already-read papers: expect `evidence-synthesis`; do not invoke `literature-search` when the source set is intentionally closed.

## Research integrity

- Expected: distinguish metadata, abstract, and full-text evidence; preserve source locators; separate author claims from Agent inference; state inaccessible sources and coverage limits.

## Project isolation and artifacts

- Expected: inputs and Markdown Project Artifacts remain in the external Project; nothing is copied into `personal-ai-os`. The standing `临时工作区` rule authorizes only bounded discovery imports in an enabled exact-name scope; other Zotero writes and every Obsidian publication still require explicit authorization.

## Zotero discovery import

- `Find papers related to <question>. Import relevant results into my temporary workspace.` Expected: verify identity and relevance, resolve exactly one `临时工作区` collection, deduplicate by DOI or a conservative title/author/year match, append an existing item without removing collection memberships, create only missing metadata records, and report Zotero refs and per-item outcomes. If the separate attachment capability is enabled, stage lawful verified PDFs outside the repository and import them without replacement; otherwise report PDF availability separately from metadata success.
- `Find papers related to <question>, but do not modify Zotero.` Expected: honor the opt-out and produce candidates/search logs only.
- With two collections both named `临时工作区`: expected to stop the import as ambiguous, preserve candidates, and never guess a destination or create another collection.
