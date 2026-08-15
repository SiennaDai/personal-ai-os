# Modeling Agent

The Modeling Agent is the canonical Mathematical and Computational Modeling Specialist Agent for formulation, solution strategy, bounded model execution, validation, sensitivity, uncertainty, robustness, and decision analysis.

Runtime hierarchy:

```text
External Project -> Codex Main Runtime -> Modeling Specialist Agent -> Skills
```

Canonical instructions are in [AGENT.md](AGENT.md). Generate the runtime projection through the repository-level [sync command](../../scripts/sync-runtime.sh).

The functional boundary, capability audit, external candidate evaluation, implementation decisions, and runtime verification are recorded in [the design decision](../../docs/modeling-agent-design.md).

Zotero, Obsidian, data-platform, solver-service, experiment-tracking, and remote-compute integrations are intentionally deferred until all planned Specialist Agents are defined. The Agent works on local external Project context without assuming those integrations exist.
