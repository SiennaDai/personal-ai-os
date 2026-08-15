# Research Agent Design Decision

## Status

Approved for implementation. Runtime architecture and Project isolation remain unchanged.

## Functional boundary

The Research Agent owns academic literature discovery, paper reading and analysis, cross-source evidence synthesis, research-gap analysis, and literature-grounded research design. The Learning Agent remains limited to learning course knowledge. Writing, Coding, and Modeling Agents own publication writing, software implementation, and mathematical or computational modeling respectively.

Modes are Discovery, Paper Analysis, Evidence Synthesis, and Research Design. Markdown Project Artifacts remain in the external Project; only user-confirmed Knowledge Artifacts may later enter the long-term knowledge layer.

## Skill decisions

- Reuse unchanged: `document-understanding`, `knowledge-extraction`, `stem-reasoning`, `knowledge-mapping`, and `visualization`.
- Adapt: `literature-search` and `evidence-synthesis`.
- Do not add: a duplicate paper-reading Skill, academic-writing Skill, citation-management Skill, research-planning Skill, or meta-analysis Skill.

`literature-search` adapts the modular engine-selection and reproducible-search ideas in [jxtse/scientific-research-skills](https://github.com/jxtse/scientific-research-skills) with multi-source and deduplication ideas from [paper-search-pro](https://github.com/O0000-code/paper-search-pro). It removes platform-specific paths, required third-party LLM services, HTML reporting, and bundled dependency assumptions.

`evidence-synthesis` adapts the cross-paper comparison, convergence, conflict, and gap methodology in [ByteDance DeerFlow's systematic-literature-review](https://github.com/bytedance/deer-flow/tree/main/skills/public/systematic-literature-review), informed by the reproducibility and appraisal principles in [K-Dense scientific-agent-skills](https://github.com/K-Dense-AI/scientific-agent-skills/tree/main/skills/literature-review). It removes arXiv-only retrieval, platform-specific subagent tooling, forced visuals, PDF production, and final publication writing.

The adapted Skills contain no copied scripts and introduce no runtime dependency. Referenced sources are MIT or Apache-2.0 licensed; preserve this design record as provenance for the methodological adaptation.

## Integration decision

Zotero and Obsidian integration design and implementation are deferred until all planned Specialist Agents are complete. If a future Agent cannot be defined without an integration contract, only the minimum interface may be specified at that time. No integration implementation is authorized during Agent development.
