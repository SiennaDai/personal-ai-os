# Personal AI OS

The WSL repository at `/home/sienna/projects/personal-ai-os` is the only canonical editable source for the AI-OS architecture, Specialist Agent definitions, Skills, integrations, deployment scripts, and evals. Any Windows clone is a legacy, non-canonical copy.

Runtime architecture: External Project → Codex Main Runtime → Specialist Agent → Skills and MCP-backed Integrations.

- [Architecture](docs/architecture.md)
- [Integration Layer architecture](docs/integration-architecture.md)
- [Specialist Agent definitions](agents/README.md)
- [Skill definitions](skills/README.md)
- [WSL runtime deployment](docs/runtime-deployment.md)
- [Integrations](integrations/)
- [Zotero Integration](integrations/zotero/README.md)
- [Obsidian Integration](integrations/obsidian/README.md)
- [Evaluation foundation](evals/README.md)
- [Historical design records](archive/README.md)

Course notes, research papers, project data, and Obsidian knowledge-base content remain outside this repository.

The Zotero and Obsidian Integrations are implemented with default-read-only bootstrap surfaces. Zotero contract `1.2` uses the Zotero 10 Local API for reads, narrowly gated single-object writes, and separately gated staged-PDF import; the Research Agent can stage verified, deduplicated discovery records and available lawful PDFs in an explicitly scoped `临时工作区`. Obsidian uses the Vault filesystem as its exact Markdown data plane and the enabled official CLI as an optional semantic plane.
