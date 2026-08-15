# Coding Agent

The Coding Agent is the canonical Software Engineering Specialist Agent for repository analysis, technical design, implementation, debugging, testing, refactoring, migrations, and read-only code review.

Runtime hierarchy:

```text
External Project -> Codex Main Runtime -> Coding Specialist Agent -> Skills
```

Canonical instructions are in [AGENT.md](AGENT.md). Generate the runtime projection through the repository-level [sync command](../../scripts/sync-runtime.sh).

The functional boundary, capability audit, external candidate evaluation, ADAPT decisions, and runtime verification are recorded in [the design decision](../../docs/coding-agent-design.md).

The [Zotero Integration](../../integrations/zotero/README.md) may supply an exact paper source for a reproduction task, while the [Obsidian Integration](../../integrations/obsidian/README.md) may retrieve durable technical knowledge or publish an explicitly authorized reusable artifact. Each is used only when its MCP runtime is configured and healthy. Remote GitHub, CI, issue-tracker, cloud, and deployment integrations remain outside the current Integration scope.
