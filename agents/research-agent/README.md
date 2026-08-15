# Research Agent

The Research Agent is the canonical Academic Research Specialist Agent for literature discovery, paper analysis, evidence synthesis, research-gap analysis, and source-grounded research design.

Runtime hierarchy:

```text
External Project -> Codex Main Runtime -> Research Specialist Agent -> Skills
```

Canonical instructions are in [AGENT.md](AGENT.md). Generate runtime projections through the repository-level [sync command](../../scripts/sync-runtime.sh).

Zotero and Obsidian integrations are intentionally deferred until all planned Specialist Agents are defined. The Agent operates on external Project material without assuming those integrations exist.
