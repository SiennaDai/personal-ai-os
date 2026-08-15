# Writing Agent Architecture Checks

## Agent boundary

- With a supplied research synthesis: `Have the Writing Agent turn this approved synthesis into a concise report for technical managers.` Expected: Composition Mode; do not perform a new literature search.
- With an academic paper: `Find related papers and determine whether this claim is supported.` Expected: route to Research Agent, not Writing Agent.
- With course material: `Teach me this chapter and quiz me.` Expected: route to Learning Agent, not Writing Agent.

## Mode and change-depth routing

- `Draft a two-page decision memo from this brief and approved evidence table.` Expected: Composition Mode and `structured-writing`.
- `Reorganize this draft so the recommendation follows from the evidence.` Expected: Revision Mode and substantive `writing-revision`.
- `Proofread this without changing my phrasing unless it is grammatically wrong.` Expected: Editing Mode at proofreading depth; no structural rewrite.
- `Adapt this technical note into a Chinese executive summary.` Expected: Adaptation Mode; preserve factual content while changing audience and language.

## Implicit Skill routing

- For a clear Markdown brief: expect `structured-writing`; do not invoke `document-understanding`, `literature-search`, or `evidence-synthesis` without need.
- For an existing readable draft: expect `writing-revision`; do not invoke `structured-writing` for a bounded edit.
- For a complex DOCX draft: `document-understanding` may precede the relevant writing Skill.
- Invoke `stem-reasoning` or `visualization` only when technical validation or a material visual need is present.

## Writing integrity

- Expected: preserve facts, citations, quotations, numbers, technical meaning, and protected wording; expose unsupported claims and missing evidence instead of inventing content.
- Expected: honor the requested edit depth and do not optimize for detector evasion.

## Project isolation, artifacts, and language

- Expected: inputs and Markdown Project Artifacts remain in the external Project; nothing is copied into `personal-ai-os`; no Zotero or Obsidian write is attempted.
- Expected: target language follows the writing brief. When no target is stated, preserve the draft language or follow the user's language instead of forcing English-first output.
