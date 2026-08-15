---
name: writing-revision
description: Diagnose and revise existing prose while preserving facts, citations, protected wording, technical meaning, and authorial voice. Use for substantive revision, line editing, copyediting, proofreading, shortening, tone or audience adaptation, and translation of a draft. Do not use for a from-scratch draft, evidence discovery, or detector-evasion rewriting.
---

# Writing Revision

Improve an existing text under an explicit or conservatively inferred change-depth contract. Solve the reader's problem without silently changing what the author is claiming.

## Choose the permitted depth

Apply the user's requested level. If it is unspecified, choose the least invasive level that satisfies the request and state any consequential assumption.

- **Proofread:** correct spelling, grammar, punctuation, formatting, and obvious consistency errors. Do not recast the prose.
- **Line edit:** improve clarity, concision, rhythm, transitions, and sentence or paragraph flow while preserving organization and meaning.
- **Substantive revision:** reorder, merge, split, cut, or reframe material to improve argument, hierarchy, and coherence. Do not add unsupported evidence.
- **Adaptation:** change audience, genre, length, tone, or language while preserving the factual and evidential core unless the user authorizes a content change.

Treat quotations, citations, legal or policy language, equations, code, numbers, names, defined terms, and user-marked spans as protected unless explicitly authorized otherwise.

## Workflow

### 1. Establish the revision contract

Identify the document purpose, reader, genre, target language, style authority, requested depth, desired output, and protected content. When a voice sample or established draft exists, treat it as stronger evidence than generic style preferences.

### 2. Diagnose before editing

Find the small number of issue clusters that most affect the reader. Classify them as needed:

- factual or source-integrity risk;
- argument or document-structure problem;
- missing context or unsupported leap;
- paragraph purpose, ordering, or transition problem;
- sentence clarity, ambiguity, verbosity, or terminology problem;
- consistency, grammar, punctuation, or formatting problem;
- mismatch of audience, genre, tone, language, or length.

Do not mistake an unfamiliar personal style for an error. Preserve deliberate repetition, rhythm, technical vocabulary, and rhetorical choices that serve the document.

### 3. Revise in focused passes

Run only the passes justified by the contract, normally in this order:

1. **Integrity pass:** protect facts, claims, quotations, citations, numbers, equations, and code; flag unresolved conflicts.
2. **Structure pass:** repair the document spine, section jobs, ordering, and argument gaps when substantive revision is authorized.
3. **Paragraph pass:** improve unity, progression, transitions, and claim–support relationships.
4. **Sentence pass:** improve clarity, specificity, concision, syntax, and terminology while retaining voice.
5. **Mechanical pass:** correct grammar, spelling, punctuation, formatting, and internal consistency.

Separate these passes when combining them would hide semantic changes or cause needless churn.

### 4. Preserve source and author integrity

- Do not strengthen certainty, causality, novelty, or generality beyond the source text.
- Keep citations attached to the claims they support; never invent a citation, quotation, locator, or bibliographic detail.
- Do not replace a precise claim with a more vivid unsupported one.
- Keep terminology, notation, and abbreviations consistent without flattening meaningful distinctions.
- Follow the requested dialect or house style; do not impose universal punctuation bans, word blacklists, or generic “professional” voice.
- Do not optimize prose to evade AI detectors. Optimize it for the stated reader and purpose.

When a revision requires new literature, source verification, or evidence synthesis, flag the need for the Research Agent instead of filling the gap.

### 5. Verify the result

Compare the revision against the original and the contract. Confirm that:

- no protected fact, citation, quotation, number, equation, code fragment, or requirement was lost or altered accidentally;
- the requested problems were actually resolved;
- the voice and target language remain coherent;
- headings, terminology, references, and formatting are internally consistent;
- the final length and genre constraints are satisfied;
- placeholders and unresolved evidence questions remain visible.

For file edits, inspect the resulting diff when available.

### 6. Deliver proportionally

Return clean revised prose by default. Add a concise change note for substantive revisions, contested choices, or when the user requests rationale. For proofreading and small edits, avoid a verbose edit report unless a remaining ambiguity needs attention.

Keep durable text Markdown-first and inside the external Project.

## Boundaries

- Use `structured-writing` when the primary need is a new document or substantial new section from a brief and source material.
- Use `document-understanding` first when the source draft cannot yet be read faithfully in its native form.
- Use `stem-reasoning` only to protect genuinely technical meaning, not to expand the document's research claims.
- This Skill does not discover evidence, manage a citation library, render office documents, publish to a knowledge base, or authorize a deeper rewrite than requested.
