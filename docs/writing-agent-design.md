# Writing Agent Design Decision

## Status

Implemented and runtime-verified on 2026-08-15 with Codex CLI 0.147.0. The frozen runtime architecture, WSL canonical-source policy, Project isolation, and existing Learning and Research Agent semantics remain unchanged.

## 1. Agent functional definition

### Mission

The Writing Agent turns an approved purpose, audience, source set, brief, outline, or existing draft into clear, coherent, source-faithful written artifacts. It supports drafting, substantive revision, line editing, proofreading, and audience or genre adaptation without taking ownership of upstream research.

### Primary responsibilities

1. Establish the writing purpose, audience, genre, target language, constraints, source authority, and requested level of change.
2. Select an operating mode and an economical writing strategy.
3. Coordinate reusable capabilities without asking the user to select Skills manually.
4. Preserve verified facts, citations, quotations, technical meaning, authorial voice, and protected wording.
5. Expose missing evidence, unsupported claims, ambiguities, and decisions that require author approval instead of inventing content.
6. Produce Markdown-first artifacts in the external Project and apply proportional quality control.

### Task categories

| Category | User intent | Typical input | Expected output | Interaction |
|---|---|---|---|---|
| Composition | Create a new document from known material | brief, outline, notes, source-grounded research artifact, constraints | outline, section draft, or complete draft | single-turn for bounded work; iterative for consequential documents |
| Revision | Improve argument, organization, coherence, or flow | existing draft, goals, reviewer feedback | revised draft plus a concise decision or change note when useful | normally iterative when changes are substantial |
| Editing | Improve clarity, consistency, grammar, and mechanics | draft and style constraints | minimally changed clean copy, optionally with an edit summary | usually single-turn |
| Adaptation | Recast material for another audience, genre, length, tone, or language | source text, target brief, protected meaning | adapted draft with material omissions or uncertainties disclosed | single-turn or iterative depending on transformation risk |

### Modes

- **Composition Mode:** builds a content inventory and document spine, then drafts from approved material.
- **Revision Mode:** may change structure, argument order, emphasis, and paragraph function while preserving source fidelity.
- **Editing Mode:** performs bounded line editing or proofreading with minimal semantic change.
- **Adaptation Mode:** changes audience, genre, length, tone, or language while preserving the requested meaning and evidence status.

The Agent infers the mode unless the user overrides it. These modes are justified because they change permitted edit depth, interaction, artifact behavior, quality checks, and Skill routing.

### Inputs

Realistic inputs include user instructions, briefs, outlines, Markdown or text, DOCX/PDF/PPTX drafts, screenshots, source-grounded research artifacts, citation lists, reviewer feedback, style guides, templates, data summaries, equations, code excerpts, and publication constraints. The Agent does not impose a file-type restriction when Codex can inspect the material safely.

### Outputs and artifacts

- **Project Artifacts:** briefs, outlines, drafts, revised manuscripts, edit memos, reviewer-response drafts, reports, proposals, articles, documentation, executive summaries, and audience adaptations. These remain in the external Project.
- **Knowledge Artifact candidates:** stable, reusable writing guidance, templates, or style decisions that the user explicitly identifies for long-term reuse. They are not published automatically.

Markdown is the canonical editable textual format. A requested delivery format may be derived when suitable tooling exists, but it does not replace the Markdown source by default.

### Explicit boundaries

- Literature discovery, paper analysis, evidence synthesis, and research-gap analysis belong to the Research Agent.
- Course instruction, exam preparation, and learning assessment belong to the Learning Agent.
- Software implementation and substantial computational experiments belong to the Coding Agent.
- Mathematical model formulation, solution, validation, and decision analysis belong to the Modeling Agent.
- The Agent does not invent facts, citations, quotations, data, results, or source support.
- It does not silently perform a deeper rewrite than the user authorized.
- It does not treat generic “humanizer” or detector-evasion behavior as a writing objective.
- It does not write to Zotero or Obsidian. Their integrations remain deferred and are not required to define this Agent.

Language is part of the writing brief. Preserve the draft language when revising; otherwise follow an explicit target language, then the user's language when no target is specified. Do not force English-first prose or Chinese terminology annotations into a deliverable unless the user, genre, or audience calls for them.

## 2. Capability map

| Capability | Type | Reason |
|---|---|---|
| Intent, audience, genre, mode, and edit-depth routing | Agent Logic | Controls orchestration and permission rather than a reusable procedure |
| Strategy, sequencing, interaction, artifact classification, and final quality gate | Agent Logic | High-level Agent ownership |
| Build an audience-driven structure and source-grounded draft | New Skill | Coherent, reusable capability for Writing and future Specialist Agents |
| Diagnose and revise existing prose at an authorized depth | New Skill | Independently testable and reusable across document types |
| Recover structure from non-Markdown or visually complex input | Existing Skill | Covered by `document-understanding` |
| Extract usable concepts, claims, assumptions, and examples from structured material | Existing Skill | Covered by `knowledge-extraction` when a source inventory is needed |
| Check or explain mathematics, algorithms, and technical meaning | Existing Skill | Covered by `stem-reasoning` when technical accuracy is material |
| Create a materially useful visual explanation | Existing Skill | Covered by `visualization` when prose or a table is insufficient |
| Discover or synthesize research evidence | Other Agent | Keep with the Research Agent instead of duplicating its routing |
| Zotero bibliographic access | Integration | Deferred; the Writer consumes exported metadata or Research artifacts for now |
| Obsidian publication | Integration | Deferred; no publication behavior is required for core writing |
| Project paths, house style, and repository-specific templates | Project-specific | Must remain in the external Project |

## 3. Existing Skill audit

| Capability | Existing Skill | Coverage | Recommendation |
|---|---|---:|---|
| Read complex source or draft files | `document-understanding` | Full | Reuse unchanged and only when raw structure requires recovery |
| Prepare a grounded content inventory | `knowledge-extraction` | Partial | Reuse unchanged; the Writing Skill owns document-purpose decisions |
| Validate technical meaning | `stem-reasoning` | Partial | Reuse unchanged and only for genuine technical content |
| Add diagrams or charts | `visualization` | Full | Reuse unchanged when a visual materially helps |
| Construct a purposeful draft | none | None | Add `structured-writing` |
| Revise, copyedit, proofread, or adapt prose | none | None | Add `writing-revision`; do not stretch `assessment` beyond learning evaluation |
| Literature discovery | `literature-search` | Full but out of scope | Route to Research Agent, not Writing Agent |
| Cross-paper evidence synthesis | `evidence-synthesis` | Full but out of scope | Route to Research Agent, not Writing Agent |
| Teaching and grading | `education-learning`, `assessment` | Full but out of scope | Do not invoke for normal writing work |
| Knowledge graphs | `knowledge-mapping` | Not needed | Do not confuse document structure with a concept graph |

Extending the existing Skills for drafting or revision would blur their current semantic boundaries. Two new Skills are the smallest non-overlapping pool.

## 4. External search results

Only serious candidates and useful references are retained here.

### OpenAI `build-report`

- Source: [OpenAI role-specific plugins](https://github.com/openai/role-specific-plugins/tree/main/plugins/data-analytics/skills/build-report)
- License: MIT at repository level.
- Relevance: strong audience/purpose/scope setup, evidence inventory, answer-first report spine, claim–evidence–implication structure, and final validation.
- Limitation: specialized for data reports, HTML, plugin surfaces, MCP tools, and Recharts. It is not a general writing Skill.

### Anthropic `doc-coauthoring`

- Source: [Anthropic skills](https://github.com/anthropics/skills/blob/main/skills/doc-coauthoring/SKILL.md)
- Relevance: useful context gathering, document structuring, iterative section drafting, and reader testing.
- Limitation: assumes Claude-specific tools and a prescriptive conversational process. The exact file's reuse license was not unambiguous during review, so its text is not copied; it is a methodological reference only.

### K-Dense `scientific-writing`

- Source: [K-Dense scientific-agent-skills](https://github.com/K-Dense-AI/scientific-agent-skills/tree/main/skills/scientific-writing)
- License: MIT declared by the Skill.
- Relevance: strong non-fabrication, evidence binding, scientific fidelity, and methods/results consistency safeguards.
- Limitation: manuscript-specific, dependency- and scaffold-heavy, and too broad for a general Writing Agent. Scientific reporting requirements should remain future context-specific behavior.

### forjd `better-writing`

- Source: [forjd/better-writing](https://github.com/forjd/better-writing)
- License: MIT.
- Relevance: audience and channel calibration, voice-sample authority, preservation of facts/citations/quotes, context-sensitive style, specificity without invention, and a useful final preflight.
- Limitation: centers “AI tells,” includes dialect and punctuation preferences that should not become universal policy, and offers little structural-revision method.

### Softaworks `writing-clearly-and-concisely`

- Source: [Softaworks agent-toolkit](https://github.com/softaworks/agent-toolkit/tree/main/skills/writing-clearly-and-concisely)
- License: MIT at repository level.
- Relevance: concise operational guidance for paragraph unity, concrete language, clarity, and economical prose.
- Limitation: English-centric, broadly triggered, and insufficient for structural revision, change authority, or source fidelity.

### Coreyhaines31 `copy-editing`

- Source: [marketingskills](https://github.com/coreyhaines31/marketingskills/tree/main/skills/copy-editing)
- License: MIT at repository level.
- Relevance: the focused-pass approach reduces conflicting edit goals.
- Limitation: conversion-copy assumptions, calls to action, emotional persuasion, and arbitrary scoring make it unsuitable for general writing.

No popularity metric was used as a quality proxy. No external repository, dependency, script, or instruction text is imported.

## 5. Candidate evaluation matrix

Scores are 0–5, where 5 is strongest; dependency cost and overlap risk use 5 for the lowest cost or risk.

| Capability | Candidate | Functional fit | Architecture fit | Instruction quality | Dependency cost | Maintainability | License | Overlap risk | Decision |
|---|---|---:|---:|---:|---:|---:|---|---:|---|
| Structured drafting | OpenAI `build-report` | 3 | 3 | 5 | 2 | 5 | MIT | 4 | ADAPT as a reference |
| Structured drafting | Anthropic `doc-coauthoring` | 4 | 3 | 4 | 4 | 4 | unclear for file | 3 | Reference only |
| Structured drafting | K-Dense `scientific-writing` | 3 | 2 | 4 | 1 | 3 | MIT | 2 | Do not select |
| Revision and editing | forjd `better-writing` | 4 | 4 | 4 | 5 | 4 | MIT | 4 | ADAPT |
| Revision and editing | Softaworks `writing-clearly-and-concisely` | 3 | 4 | 4 | 5 | 4 | MIT | 3 | Supporting reference |
| Revision and editing | Coreyhaines31 `copy-editing` | 2 | 3 | 3 | 5 | 4 | MIT | 3 | Do not select |

## 6. Adopt / Adapt / DIY ledger

### Structured drafting

- **Decision:** ADAPT.
- **References:** OpenAI `build-report`; Anthropic `doc-coauthoring` as a non-copied methodological reference.
- **Keep:** audience and purpose framing, source/content inventory, document spine, explicit section jobs, iterative drafting, reader-oriented validation.
- **Remove:** plugin and delivery-surface assumptions, Claude-specific tools, fixed question counts, mandatory brainstorming volume, forced section-by-section interaction, HTML/MCP/Recharts requirements.
- **Modify:** make the method genre-neutral, Markdown-first, source-grounded, proportional to risk, and compatible with isolated external Projects.
- **Add:** source-status tracking, missing-information placeholders, draft/final distinction, and explicit constraint validation.
- **Risk:** becoming a second orchestration Agent. Mitigation: the Skill executes drafting mechanics while the Writing Agent retains routing, interaction, and artifact policy.

### Revision and editing

- **Decision:** ADAPT.
- **Chosen candidate:** forjd `better-writing`, informed by Softaworks clarity guidance and the focused-pass method in `copy-editing`.
- **Keep:** audience/purpose/voice calibration, protection of facts/citations/quotes, contextual rather than blanket rules, specificity without invention, focused passes, and final preflight.
- **Remove:** detector-evasion framing, universal dialect defaults, punctuation bans, word blacklists, conversion-copy assumptions, emotional manipulation, and persona scoring.
- **Modify:** cover structural revision, line editing, proofreading, and adaptation under an explicit change-depth contract.
- **Add:** issue classification, authorial-voice preservation, factual and citation escalation, protected-span handling, and optional concise change notes.
- **Risk:** overlapping with composition. Mitigation: `structured-writing` constructs new prose from a brief; `writing-revision` transforms an existing text under bounded authority.

### Other capabilities

- **ADOPT:** none. No candidate cleanly matches the general, Markdown-first, integration-independent boundary without semantic changes.
- **DIY:** none. The two gaps have strong reusable methods worth adapting.
- **Not added:** citation management, citation audit, academic-writing, style-transfer, humanizer, document-formatting, and reviewer-response Skills. These are either integration concerns, narrower genres, harmful objectives, or coherent behavior within the two selected Skills.

## 7. Proposed final Skill pool

### Reuse unchanged

- `document-understanding`
- `knowledge-extraction`
- `stem-reasoning`
- `visualization`

### Adopt

None.

### Adapt

- `structured-writing`
- `writing-revision`

### DIY

None.

### Not needed for Writing Agent routing

- `assessment`
- `education-learning`
- `knowledge-mapping`
- `literature-search`
- `evidence-synthesis`

## 8. Agent-to-Skill routing map

```text
User writing request
        ↓
Writing Agent establishes purpose, audience, genre, language, constraints,
source authority, and permitted change depth
        ↓
Raw or visually complex source/draft?
        └─ yes → document-understanding
        ↓
Source material needs a grounded content inventory?
        └─ yes → knowledge-extraction
        ↓
New document or major new section?
        └─ yes → structured-writing
Existing prose being transformed?
        └─ yes → writing-revision
        ↓
Technical correctness genuinely at issue?
        └─ yes → stem-reasoning
Visual materially clearer than prose/table?
        └─ yes → visualization
        ↓
Writing Agent validates source fidelity, constraints, coherence, and artifact location
```

Core/common Skills are `structured-writing` and `writing-revision`, selected according to task shape rather than both by default. The other four are context-dependent. Literature discovery or evidence synthesis triggers a handoff to the Research Agent rather than implicit expansion of Writing Agent scope.

## 9. Implementation order

1. Implement `structured-writing`, because it establishes the common brief, content-inventory, document-spine, and drafting contracts.
2. Implement `writing-revision`, aligned with the first Skill's source-fidelity and constraint vocabulary.
3. Implement the Writing Agent definition and route each mode to the minimum relevant Skill set.
4. Add runtime sync and validation entries, focused architecture eval prompts, and active documentation links.
5. Deploy from canonical WSL source and verify discovery, implicit routing, artifact behavior, and Project isolation from an unrelated Project.

## 10. Open questions

None block implementation. Zotero and Obsidian interface design remains intentionally deferred because the Agent can be defined and verified against files and artifacts inside an external Project. Genre-specific scientific reporting, journal submission, office-document rendering, and knowledge-base publication may be evaluated later as context-dependent capabilities rather than being preloaded into this Agent.

## Runtime verification

The canonical sync command was run twice successfully. It generated `~/.codex/agents/writing_agent.toml`, linked both new Skills from `~/.agents/skills/` to the WSL repository, and validated all three Agents and eleven Skills on each run.

Two fresh non-interactive Codex Main Runtime sessions were started with multi-agent support from `/tmp/personal-ai-os-writing-test`, without adding another writable root or naming any Skill in the prompts:

1. The main runtime delegated an approved evidence-to-memo task to the configured `writing_agent`. The Specialist loaded `structured-writing` through its user-level runtime path, created a 419-word Markdown decision memo, and did not load unrelated Skills.
2. The main runtime delegated a bounded line edit to the same Specialist. It loaded only `writing-revision`, created an 82-word one-paragraph revision, preserved all supplied benchmark facts, and corrected an unsupported conclusion.

The subagent session records showed the actual Skill reads and Project-local writes. The input files were not written, no Project material appeared in `personal-ai-os`, and no Zotero, Obsidian, network, or other integration action occurred.

Current CLI warning: an initial custom-agent call that combined an explicit Agent type with a full-history fork was rejected. The main runtime retried with scoped context and completed both delegations. The verified user-facing invocation remains `Have the Writing Agent ...`; the user does not need to select a fork mode or name Skills.
