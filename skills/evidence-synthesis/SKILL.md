---
name: evidence-synthesis
description: Compare and synthesize claims across multiple research sources with explicit provenance, study comparability, evidence quality, conflicts, uncertainty, and gaps. Use for evidence matrices, cross-paper comparisons, narrative or scoping syntheses, and source-grounded research conclusions. Do not use for literature discovery, single-paper reading, or unsupported meta-analysis.
---

# Evidence Synthesis

Build conclusions that remain traceable to inspected sources and calibrated to the evidence base.

## Process

1. Define the synthesis question, included source set, unit of analysis, and intended review type. Do not label a review systematic unless its search and screening process supports that claim.
2. Confirm that each source is readable and sufficiently structured. Use `document-understanding` for raw documents and `knowledge-extraction` for source-level research questions, methods, findings, assumptions, contributions, and limitations.
3. Record evidence state and provenance for every source. Exclude or clearly limit sources supported only by metadata or abstracts.
4. Build a normalized comparison matrix using only applicable fields, such as population or context, design, data, intervention or exposure, comparator, outcomes, method, assumptions, effect direction, uncertainty, and limitations.
5. Assess credibility and comparability using criteria appropriate to the domain and study design. State the criteria; do not force all evidence into one universal score or treat venue prestige and citation count as quality.
6. Group sources by meaningful questions, methods, populations, mechanisms, or findings. Identify convergences, disagreements, heterogeneity, and sources that cannot be directly compared.
7. Construct each synthesis claim with supporting sources, contradicting sources, important qualifications, and confidence. Keep source claims separate from the synthesizer's inference.
8. Investigate plausible reasons for conflict, including design, measurement, sample, setting, assumptions, version, and statistical uncertainty. Present alternatives when the evidence cannot distinguish them.
9. Identify gaps only relative to the observed evidence base. Separate missing evidence, under-studied contexts, methodological weaknesses, and genuinely unresolved findings.
10. Review the synthesis for unsupported generalization, double-counted study versions, selective citation, causal overreach, and omitted uncertainty.

## Quantitative boundaries

Do not perform or imply a meta-analysis merely because numerical results are present. Quantitative pooling requires compatible estimands, outcomes, designs, and uncertainty information plus an explicit method. When those conditions are absent, use a structured narrative comparison and explain why pooling is inappropriate.

## Output

Return Markdown containing, as applicable:

- synthesis question, scope, and included evidence
- source and evidence-state table
- normalized evidence matrix
- appraisal criteria and important limitations
- themes or analytical groupings
- claim–evidence–source table
- convergence, conflict, heterogeneity, and non-comparability
- confidence and uncertainty for each major conclusion
- evidence gaps and research implications
- provenance locators and unresolved source needs

Classify the result as a Project Artifact unless the user explicitly identifies a stable, reusable Knowledge Artifact.

## Quality rules

- Never invent study details, quality judgments, effect sizes, citations, or source locators.
- Do not equate the number of agreeing papers with independent evidence; identify shared datasets, overlapping samples, and linked versions when known.
- Do not turn absence of retrieved evidence into evidence of absence.
- Treat preprints, retractions, corrections, and superseded versions according to their status.
- Prefer a qualified conclusion over a forced consensus.
