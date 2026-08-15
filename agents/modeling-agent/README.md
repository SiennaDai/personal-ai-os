# Modeling Agent

The Modeling Agent is the canonical Mathematical and Computational Modeling Specialist Agent for formulation, solution strategy, bounded model execution, validation, sensitivity, uncertainty, robustness, and decision analysis.

Runtime hierarchy:

```text
External Project -> Codex Main Runtime -> Modeling Specialist Agent -> Skills
```

Canonical instructions are in [AGENT.md](AGENT.md). Generate the runtime projection through the repository-level [sync command](../../scripts/sync-runtime.sh).

The functional boundary, capability audit, external candidate evaluation, implementation decisions, and runtime verification are recorded in [the design decision](../../docs/modeling-agent-design.md).

The [Zotero Integration](../../integrations/zotero/README.md) can supply exact source I/O, while the [Obsidian Integration](../../integrations/obsidian/README.md) can retrieve durable modeling knowledge or publish an explicitly authorized reusable artifact. Each is used only when its MCP runtime is configured and healthy. Data-platform, solver-service, experiment-tracking, and remote-compute integrations remain outside the current implementation scope.
