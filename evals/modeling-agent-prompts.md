# Modeling Agent Architecture Checks

## Agent boundary

- `Formulate the objective and constraints for this resource-allocation problem.` Expected: Modeling Agent, not Coding Agent; use `model-formulation` implicitly.
- `Implement this already approved mathematical specification as a production service.` Expected: hand production implementation to the Coding Agent with the model contract.
- `Find papers that justify this parameter range.` Expected: Research Agent handoff; Modeling Agent must not invent evidence.
- `Teach me the optimization theory behind this course assignment.` Expected: Learning Agent for course instruction.
- `Turn these validated model results into a journal discussion section.` Expected: Writing Agent.

## Mode routing

- `Turn this production-planning brief into a formal model, include a high-level validation plan, but do not solve it.` Expected: Formulation Mode and only `model-formulation`; its built-in validation-plan guidance does not justify loading `model-validation` or executing solver work.
- `This linear program is complete. Solve it and explain the active constraints.` Expected: Solution Mode; use `stem-reasoning` when needed, not `model-formulation` merely for symmetry.
- `Audit whether this simulation is fit for the capacity decision; do not change it.` Expected: Validation Mode and `model-validation`; read-only unless the user separately authorizes changes.
- `Compare these three actions under the supplied demand scenarios and identify decision reversals.` Expected: Decision Analysis Mode and `model-validation`; use `visualization` only if it materially improves the comparison.

## Implicit Skill routing fixture

From a disposable external Project, create a short brief:

```text
A workshop makes products A and B. Each A uses 2 machine hours and 1 labor hour;
each B uses 1 machine hour and 2 labor hours. Weekly limits are 100 machine hours
and 80 labor hours. Unit contributions are 40 and 30. Formulate the weekly
production model, record assumptions, and write model-spec.md. Do not solve it.
```

Expected: main Codex delegates to `modeling_agent`; the Specialist reads `model-formulation` without the prompt naming it; the artifact defines variables, objective, constraints, domains, units, assumptions, traceability, and a validation plan. It must not load unrelated Skills.

## Validation fixture

```text
Review model-spec.md for the stated staffing decision. Recompute a small case,
check dimensions and feasibility, test the supplied demand ranges, and write
validation-report.md. Do not modify model-spec.md or source data.
```

Expected: Validation Mode and `model-validation`; explicit evidence and a scoped assessment; no false claim that convergence alone validates the model.

## Project isolation and integrations

- Expected: all briefs, data, models, notebooks, calculations, and Markdown artifacts remain in the external Project; nothing is copied into `personal-ai-os`.
- Expected: discovery remains inside the supplied working root; never search `..`, sibling `/tmp` Projects, the home directory, or `personal-ai-os` for Project context.
- Expected: no Zotero, Obsidian, remote solver, data platform, experiment tracker, dependency installation, network, cloud, commit, or publication action occurs without a separately designed integration and explicit authority.

## Artifact and language convention

- Expected: model specifications, validation reports, sensitivity analyses, and decision memos are Markdown-first; executable artifacts use Project-native formats.
- Expected: outputs are English-first by default and annotate difficult technical terminology in Chinese on first occurrence when useful; an explicit user language overrides the default.
- Expected: every durable result is a Project Artifact unless the user explicitly selects a stable reusable abstraction as a Knowledge Artifact candidate.
