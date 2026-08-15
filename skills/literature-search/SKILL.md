---
name: literature-search
description: Find, verify, expand, deduplicate, and screen academic literature with a reproducible search trail. Use for literature discovery, seed-paper expansion, citation chaining, candidate bibliography creation, or search coverage analysis. Do not use to claim evidence from unread full text or to synthesize conclusions across studies.
---

# Literature Search

Find traceable candidate literature without confusing discovery metadata with verified evidence.

## Process

1. Define the research question, scope, time range, languages, source types, and inclusion or exclusion constraints. Ask only for missing information that would materially change the search.
2. Decompose the question into core concepts. Generate precise synonyms, abbreviations, related terms, and controlled vocabulary when the domain supports it. Preserve the original question alongside every derived query.
3. Select complementary sources available in the current runtime. Match sources to the discipline and task; do not imply that one index provides universal coverage.
4. Run broad discovery queries, then refine them based on observed relevance. Record each source, exact query, filters, date, and result scope. Never silently replace an unsuccessful query.
5. Verify candidate identity against authoritative metadata when possible: title, authors, year, venue, DOI or stable identifier, version, and canonical URL. Mark fields that remain unverified.
6. When seed papers are available, perform backward and forward citation expansion when tools permit. Keep directly retrieved candidates distinct from citation-derived candidates.
7. Normalize identifiers and deduplicate records. Preserve meaningful versions such as a preprint and later published article, but link them as related versions.
8. Screen candidates against explicit relevance criteria. Record inclusion, exclusion, and uncertain decisions with short reasons; do not rank by citation count alone.
9. Stop when the requested scope is met, available sources are exhausted, or additional iterations yield little relevant material. Describe the actual stopping condition rather than claiming completeness.

## Evidence states

Label what was actually inspected:

- **Metadata only:** identity and bibliographic fields
- **Abstract inspected:** abstract-level relevance, not full evidence
- **Full text available:** available for later document understanding
- **Full text inspected:** eligible for source-grounded extraction

Do not infer methods, findings, limitations, or causal claims from title metadata. Do not present an abstract-only conclusion as full-text verification.

## Output

Return Markdown containing, as applicable:

- research question and scope
- sources and search log
- normalized candidate table with stable identifiers
- evidence state for each candidate
- inclusion, exclusion, and uncertainty decisions
- seed and citation-chain relationships
- duplicates or linked versions
- coverage limitations and unresolved retrieval needs
- recommended next reading or screening step

Keep bibliographic identity compatible with a future reference-manager integration, but do not create or modify external library records unless a separately authorized integration is available.

## Quality rules

- Treat search results as candidates, not evidence.
- Never invent citations, identifiers, result counts, queries, or database coverage.
- Prefer primary scholarly indexes and publisher or repository records for verification.
- Distinguish retractions, corrections, preprints, accepted manuscripts, and published versions when known.
- Respect access controls and licenses; do not bypass paywalls or download restrictions.
- State when tooling, credentials, indexing, language, or access limits the search.
