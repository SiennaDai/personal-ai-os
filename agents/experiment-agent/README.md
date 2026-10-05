# Experiment Agent

The Experiment Agent is the canonical specialist for literature-grounded experiment planning, `benchmark-experiments` preparation, user-triggered result analysis, and Obsidian research-record maintenance.

Runtime hierarchy:

```text
benchmark-experiments Project -> Codex Main Runtime -> Experiment Specialist Agent -> Skills and MCP Integrations
```

Canonical instructions are in [AGENT.md](AGENT.md). Generate the runtime projection through the repository-level sync command: [sync-runtime.sh](../../scripts/sync-runtime.sh) on WSL or [sync-windows-runtime.ps1](../../scripts/sync-windows-runtime.ps1) on Windows.

The Agent is platform-adapted rather than research-topic-specific. It uses the existing Research Agent for literature discovery and source reading, keeps bibliographic truth in Zotero, and stores long-term topic structure and decisions in the bounded Obsidian write root. Recipes, scripts, run artifacts, reports, and source provenance remain in the external `benchmark-experiments` Project.
