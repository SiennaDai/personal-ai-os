# Research Agent

The Research Agent is the canonical Academic Research Specialist Agent for literature discovery, paper analysis, evidence synthesis, research-gap analysis, and source-grounded research design.

Runtime hierarchy:

```text
External Project -> Codex Main Runtime -> Research Specialist Agent -> Skills
```

Canonical instructions are in [AGENT.md](AGENT.md). Generate runtime projections through the repository-level [sync command](../../scripts/sync-runtime.sh).

The [Zotero Integration](../../integrations/zotero/README.md) and [Obsidian Integration](../../integrations/obsidian/README.md) can be used when their MCP runtimes are configured and healthy. Zotero remains the bibliographic source of truth, Obsidian remains the long-term knowledge layer, and Project research artifacts are not published automatically. In Discovery Mode, a write-enabled local deployment may use the narrowly configured `临时工作区` collection as a standing destination for verified, deduplicated candidates; when the separate attachment gate is enabled, lawful verified PDFs can be staged outside the repository and imported without replacement. The Agent preserves Project isolation and degrades explicitly when an Integration is unavailable.
