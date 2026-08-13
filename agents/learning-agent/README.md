# Learning Agent

The Learning Agent is the canonical user-facing STEM learning assistant. It owns learning-mode selection, internal task orchestration, Skill routing, interaction policy, and artifact behavior.

Runtime hierarchy:

```text
External Project -> Learning Agent -> Skills
```

The canonical instructions are in [AGENT.md](AGENT.md). The historical standalone Course Learning Workflow is preserved at [`archive/workflows/course-learning/WORKFLOW.md`](../../archive/workflows/course-learning/WORKFLOW.md).

## Codex runtime synchronization

Codex discovers the runtime Agent from `~/.codex/agents/learning-agent.toml`. Generate or refresh that file from canonical `AGENT.md`:

```powershell
powershell -ExecutionPolicy Bypass -File .\agents\learning-agent\sync-runtime.ps1
```

The generated TOML is a runtime projection, not an independently maintained source. Re-run the script after changing `AGENT.md`.

Skills remain canonical under `skills/` and are linked into `~/.agents/skills/` for user-level discovery. Prefer symbolic links; use NTFS directory junctions on Windows when symlink privilege is unavailable.
