# Writing Agent

The Writing Agent is the canonical Specialist Agent for source-grounded composition, substantive revision, editing, proofreading, and audience or genre adaptation.

Runtime hierarchy:

```text
External Project -> Codex Main Runtime -> Writing Specialist Agent -> Skills
```

Canonical instructions are in [AGENT.md](AGENT.md). Generate the runtime projection through the repository-level [sync command](../../scripts/sync-runtime.sh).

The functional boundary, capability audit, external candidate evaluation, ADAPT decisions, and runtime verification are recorded in [the design decision](../../docs/writing-agent-design.md).

The [Zotero Integration](../../integrations/zotero/README.md) is implemented and can supply exact metadata and citekeys when its MCP runtime is configured and healthy. Obsidian remains unavailable until its separate implementation is deployed and verified. The Agent degrades explicitly when Zotero cannot be reached.
