# Agents

Agents are reusable Codex custom Specialist Agents/subagents. Each Agent defines its role, responsibilities, task routing, interaction policy, internal orchestration, Skill-selection guidance, and artifact behavior. Codex remains the user-facing main runtime.

Runtime relationship:

```text
External Project -> Codex Main Runtime -> Specialist Agent -> Skills
```

Agents contain no Project data and do not embed Skill implementations.

## Available Agents

- [`learning-agent`](learning-agent/AGENT.md): STEM course learning, lecture review, exam preparation, technical explanation, and problem-solving practice.

No other Agents are implemented yet.
