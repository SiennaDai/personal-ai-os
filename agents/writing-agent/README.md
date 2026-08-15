# Writing Agent

The Writing Agent is the canonical Specialist Agent for source-grounded composition, substantive revision, editing, proofreading, and audience or genre adaptation.

Runtime hierarchy:

```text
External Project -> Codex Main Runtime -> Writing Specialist Agent -> Skills
```

Canonical instructions are in [AGENT.md](AGENT.md). Generate the runtime projection through the repository-level [sync command](../../scripts/sync-runtime.sh).

The functional boundary, capability audit, external candidate evaluation, ADAPT decisions, and runtime verification are recorded in [the design decision](../../docs/writing-agent-design.md).

Zotero and Obsidian integrations are intentionally deferred until all planned Specialist Agents are defined. The Agent consumes external Project material without assuming either integration exists.
