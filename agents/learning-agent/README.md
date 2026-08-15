# Learning Agent

The Learning Agent is the canonical STEM Learning Specialist Agent used by the user-facing Codex Main Runtime. It owns learning-mode selection, internal task orchestration, Skill routing, interaction policy, and artifact behavior.

Runtime hierarchy:

```text
External Project -> Codex Main Runtime -> Learning Specialist Agent -> Skills
```

The canonical instructions are in [AGENT.md](AGENT.md). The historical standalone Course Learning Workflow is preserved at [`archive/workflows/course-learning/WORKFLOW.md`](../../archive/workflows/course-learning/WORKFLOW.md).

The [Zotero Integration](../../integrations/zotero/README.md) can supply exact source I/O when its MCP runtime is configured and healthy. It does not replace Research Agent routing for open-ended discovery or paper analysis, and it never turns a learning artifact into an automatic Zotero write.

The [Obsidian Integration](../../integrations/obsidian/README.md) can retrieve durable knowledge and publish an explicitly authorized Knowledge Artifact when its MCP runtime is configured and healthy. Learning artifacts remain in the external Project by default.

## Codex runtime synchronization

On WSL, Codex discovers the generated runtime Agent from `~/.codex/agents/learning_agent.toml`. From the canonical repository, generate or refresh the Agent and Skill projections with:

```bash
./scripts/sync-runtime.sh
```

The generated TOML is a runtime projection, not an independently maintained source. Re-run the script after changing `AGENT.md`.

Skills remain canonical under `skills/` and are symbolically linked into `~/.agents/skills/` for user-level discovery. See [WSL runtime deployment](../../docs/runtime-deployment.md) for validation and recovery.

`sync-runtime.ps1` is retained only as legacy Windows support. It does not define the canonical deployment path.
