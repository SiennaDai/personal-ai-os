# Writing Agent

The Writing Agent is the canonical Specialist Agent for source-grounded composition, substantive revision, editing, proofreading, and audience or genre adaptation.

Runtime hierarchy:

```text
External Project -> Codex Main Runtime -> Writing Specialist Agent -> Skills
```

Canonical instructions are in [AGENT.md](AGENT.md). Generate the runtime projection through the repository-level [sync command](../../scripts/sync-runtime.sh).

The functional boundary, capability audit, external candidate evaluation, ADAPT decisions, and runtime verification are recorded in [the design decision](../../docs/writing-agent-design.md).

The [Zotero Integration](../../integrations/zotero/README.md) can supply exact metadata and citekeys, while the [Obsidian Integration](../../integrations/obsidian/README.md) can retrieve durable writing knowledge or publish an explicitly authorized reusable artifact. Each is used only when its MCP runtime is configured and healthy; drafts remain in the external Project by default.
