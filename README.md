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
- [Evaluation foundation](evals/README.md)
- [Historical design records](archive/README.md)

Course notes, research papers, project data, and Obsidian knowledge-base content remain outside this repository.

The Zotero Integration is implemented with a default read-only MCP surface. Obsidian remains the next Integration phase.
