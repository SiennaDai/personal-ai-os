# Knowledge Extraction

## Design rationale

This skill uses one shared extraction process with small, extensible schemas instead of separate course and research implementations.

The research schema is informed by the evidence-traced artifact pattern in [Academic Research Agent Skill](https://github.com/ngtiendong/Academic-Research-Agent-Skill). It narrows that approach to knowledge extraction, removes its Agent layer and end-to-end research orchestration, and adds lecture-mode outputs. No source code or text is copied.

## Input and output

- **Input:** structured learning or research material, usually produced by `document-understanding`.
- **Output:** source-grounded Markdown knowledge units using lecture, research, or minimal general fields.
