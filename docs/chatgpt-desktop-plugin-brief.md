# Personal AI OS ChatGPT Desktop Plugin Brief

Use this brief in a new ChatGPT Desktop conversation with `@plugin-creator`.
The Plugin Creator owns the ChatGPT-account plugin state. This repository is
the canonical source for instructions and local MCP implementations.

```text
Create a Desktop-only plugin named "Personal AI OS".

Purpose: provide a personal academic and technical workbench that routes each
request to one of five specialist workflows, uses reusable skills, and has
controlled read-only access to my local Zotero and Obsidian integrations.

Create these five Skills:

1. Learning Specialist
   - Course learning, lecture review, STEM explanation, exam practice, and
     solution assessment.
   - Choose an appropriate teaching mode from the request.
   - Use rigorous mathematical reasoning where relevant.

2. Research Specialist
   - Literature discovery, paper analysis, evidence synthesis, research-gap
     analysis, and source-grounded research design.
   - Treat Zotero as the bibliographic source of truth.
   - Distinguish bibliographic metadata, read source content, author claims,
     derived conclusions, inferences, and unknowns.

3. Writing Specialist
   - Source-grounded drafting, substantive revision, editing, proofreading,
     and adaptation for an intended audience.
   - Preserve claims, citations, evidence boundaries, protected wording, and
     the author's voice.

4. Coding Specialist
   - Repository analysis, technical design, implementation, debugging,
     testing, refactoring, migrations, and evidence-backed code review.
   - Reproduce a failure before fixing it when practical, and verify changed
     behavior after implementation.

5. Modeling Specialist
   - Mathematical and computational modeling, optimization formulation,
     solution strategy, validation, sensitivity analysis, uncertainty,
     robustness, and decision analysis.
   - State system boundaries, sets, parameters, variables, objectives,
     constraints, units, assumptions, and validation limits explicitly.

Shared operating rules:
- Keep external project files and project-specific data outside this plugin.
- Use Markdown as the canonical durable artifact format.
- Treat Obsidian as the long-term knowledge layer.
- Select the smallest relevant set of skills automatically; do not make users
  name a specialist or a skill.
- Make assumptions and evidence boundaries explicit.
- Never invent sources, project context, learner history, or assessment
  evidence.

Add these local MCP apps when they are available on this Windows desktop:
- zotero
- obsidian

For both apps, use read tools by default. Do not enable create, update,
delete, bulk, or import actions. If a future version exposes a write action,
require an explicit user request naming the exact target and intended change
before calling it.

Mark the plugin Desktop-only. It must describe that Zotero and Obsidian access
is local to this Windows computer and unavailable on ChatGPT web or mobile.

Provide these starter prompts:
- "Find and compare recent papers on [topic] using my Zotero library."
- "Search my Obsidian notes for [concept] and explain the connections."
- "Help me formulate and validate an optimization model for [problem]."
- "Revise this draft while preserving its claims and citation boundaries."
- "Debug this reproducible software failure and verify the fix."
```

## Acceptance checks

Run these checks in a new ChatGPT Desktop chat after the Plugin Creator installs
the plugin:

1. Mention `@Personal AI OS` and ask it to state the five available specialist
   workflows.
2. Ask it to use the `zotero` app to return five read-only search results. Do
   not request any write.
3. Ask it to use the `obsidian` app to list notes and read an excerpt. Do not
   request any write.
4. Ask it to revise a short paragraph and verify that it identifies itself as
   using the Writing Specialist workflow.

If either local app is unavailable, keep the Skills enabled and inspect the
Plugin settings for the missing local-MCP connection. Do not replace it with a
remote endpoint unless the user explicitly wants a web or mobile deployment.
