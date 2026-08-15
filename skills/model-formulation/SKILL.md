---
name: model-formulation
description: Translate a real-world problem into an explicit, auditable mathematical or computational model specification. Use to choose a model family; define system boundaries, sets, parameters, variables, objectives, constraints, dynamics, assumptions, units, uncertainty, and traceability; or repair an underspecified formulation. Do not use merely to solve an already complete model or to validate reported results.
---

# Model Formulation

Turn an operational, scientific, engineering, or decision problem into the simplest formal model that is adequate for its stated use.

## Establish the modeling contract

Identify before formalizing:

- the real-world question and decision the model must support;
- the unit of analysis, system boundary, time horizon, and relevant actors or processes;
- the required outputs, success criteria, and acceptable approximation;
- available evidence, data, domain rules, and non-negotiable constraints;
- important unknowns that require a user decision or source-grounded input.

Do not replace a missing objective, constraint, parameter, causal assumption, or risk preference with a plausible invention. Label each input as an observed fact, sourced estimate, user choice, modeling assumption, derived quantity, or unresolved unknown.

## Choose the model class

Choose the model class from the question, decision, data, and uncertainty rather than from a preferred tool. Consider only relevant families, such as:

- optimization for selecting actions under objectives and constraints;
- statistical or probabilistic models for estimation, prediction, or uncertainty;
- dynamic or state-transition models for behavior over time;
- simulation for interacting, stochastic, or analytically intractable systems;
- decision or risk models for alternatives, outcomes, preferences, and uncertainty.

Prefer the least complex model that can answer the stated question. Explain why the selected class is adequate and what an important rejected alternative would change when the choice is consequential.

## Build the formal specification

Define only applicable elements:

1. **Scope and semantics:** state what the model represents and excludes.
2. **Sets and indices:** define entities, periods, locations, scenarios, or states.
3. **Parameters and inputs:** give meaning, units, admissible ranges, provenance, and uncertainty.
4. **Variables:** distinguish decision, state, observed, latent, and random variables; define domains and units.
5. **Relationships:** specify equations, transition rules, probability laws, or response functions.
6. **Objective or estimand:** connect the mathematical target to the real decision or question.
7. **Constraints and conditions:** include operational rules, conservation laws, initial or boundary conditions, feasibility, and logical restrictions.
8. **Assumptions:** make simplifications, independence claims, stationarity, linearity, distributional choices, and omitted mechanisms explicit.
9. **Solution requirements:** state expected solver class, precision, scale, data needs, and outputs without forcing a particular library prematurely.

Define notation before use and keep it stable. Preserve equations in Markdown-compatible LaTeX.

## Maintain requirement traceability

Map consequential real-world requirements to model elements. Use a compact table with columns such as:

| Requirement or fact | Model element | Status | Source or rationale |
|---|---|---|---|
| Production cannot exceed capacity | capacity constraint | represented | supplied rule |
| Demand is uncertain | scenario parameter | assumption pending | distribution not supplied |

Record real-world requirements that remain unmodeled and model elements that lack a clear real-world justification.

## Check the formulation

Before handing off the model:

- check dimensions, units, signs, domains, indexing, and boundary conditions;
- test a trivial, limiting, or hand-solvable case when one exists;
- look for missing, duplicated, contradictory, or non-binding constraints;
- check that the objective or estimand answers the stated question rather than a convenient proxy;
- assess basic feasibility, identifiability, observability, or well-posedness as applicable;
- distinguish uncertainty in inputs, model structure, and future scenarios;
- state what evidence or user choice is still required.

Do not call a formulation valid merely because it is syntactically complete or solvable.

## Output

Produce concise Markdown containing, as applicable:

- purpose, decision, scope, and exclusions;
- evidence and input-status ledger;
- assumptions and unresolved choices;
- notation and formal model;
- requirement-to-model traceability;
- expected outputs and solution requirements;
- initial formulation checks;
- validation and sensitivity plan.

Classify the result as a Project Artifact unless the user explicitly selects a stable reusable abstraction as a Knowledge Artifact candidate.

## Coordination

Use `stem-reasoning` for nontrivial derivations, proofs, algorithms, or solution analysis. This Skill already contains enough guidance for the initial high-level validation plan; do not load `model-validation` merely to include that section in a formulation artifact. Use `model-validation` when actually performing validation, designing detailed stress tests, or assessing fitness for use, sensitivity, uncertainty, robustness, or model claims. Use `document-understanding` first when a complex source specification is not yet structured. Request Research Agent evidence when assumptions or parameters require literature support, and hand production software implementation to the Coding Agent.
