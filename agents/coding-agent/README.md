# Coding Agent

The Coding Agent is the canonical Software Engineering Specialist Agent for repository analysis, technical design, implementation, debugging, testing, refactoring, migrations, and read-only code review.

Runtime hierarchy:

```text
External Project -> Codex Main Runtime -> Coding Specialist Agent -> Skills
```

Canonical instructions are in [AGENT.md](AGENT.md). Generate the runtime projection through the repository-level [sync command](../../scripts/sync-runtime.sh).

The functional boundary, capability audit, external candidate evaluation, ADAPT decisions, and runtime verification are recorded in [the design decision](../../docs/coding-agent-design.md).

Remote GitHub, CI, issue-tracker, cloud, and deployment integrations are intentionally deferred until all planned Specialist Agents are defined. The Agent works on local external Project context without assuming those integrations exist.
