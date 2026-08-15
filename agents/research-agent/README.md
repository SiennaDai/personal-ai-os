# Research Agent

The Research Agent is the canonical Academic Research Specialist Agent for literature discovery, paper analysis, evidence synthesis, research-gap analysis, and source-grounded research design.

Runtime hierarchy:

```text
External Project -> Codex Main Runtime -> Research Specialist Agent -> Skills
```

Canonical instructions are in [AGENT.md](AGENT.md). Generate runtime projections through the repository-level [sync command](../../scripts/sync-runtime.sh).

The [Zotero Integration](../../integrations/zotero/README.md) is implemented and can be used when its MCP runtime is configured and healthy. Obsidian remains unavailable until its separate implementation is deployed and verified. The Agent preserves Project isolation and degrades explicitly when an Integration is unavailable.
