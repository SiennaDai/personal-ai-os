# Agents

Agents are reusable, user-facing assistants. Each Agent defines its role, responsibilities, task routing, interaction policy, internal orchestration, Skill selection, and artifact behavior.

Runtime relationship:

```text
External Project -> Agent -> Skills
```

Agents contain no Project data and do not embed Skill implementations.

## Available Agents

- [`learning-agent`](learning-agent/AGENT.md): STEM course learning, lecture review, exam preparation, technical explanation, and problem-solving practice.

No other Agents are implemented yet.
