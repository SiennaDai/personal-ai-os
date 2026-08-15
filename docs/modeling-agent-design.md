# Modeling Agent Design Decision

## Status

Implemented and runtime-verified on 2026-08-15 with Codex CLI 0.147.0. The frozen Codex-native architecture, WSL canonical-source policy, Project isolation, and existing Learning, Research, Writing, and Coding Agent semantics remain unchanged.

The Agent does not require an integration to define its core behavior. Zotero, Obsidian, data-platform, solver-service, experiment-tracking, and remote-compute integration design and implementation remain deferred until all planned Specialist Agents are complete.

## 1. Agent functional definition

### Mission

The Modeling Agent turns real-world questions into explicit, solvable, auditable mathematical or computational models; selects and executes proportionate solution strategies; evaluates whether models are fit for their stated use; and interprets trade-offs, uncertainty, sensitivity, and decision implications.

It owns the model contract and the connection between the real system, the formal representation, the computation, the validation evidence, and the resulting decision. It does not become a general software-development, research, teaching, or writing Agent.

### Primary responsibilities

1. Establish the question, intended use or decision, system boundary, time horizon, required output, acceptance criteria, risk, and Project context.
2. Infer the task mode and sequence the minimum relevant capabilities and tools.
3. Separate observed facts, sourced estimates, user choices, assumptions, derived quantities, and unresolved unknowns.
4. Select the simplest adequate model family and maintain traceability from real requirements to formal elements.
5. Choose an analytical or computational solution strategy appropriate to model structure, scale, precision, and available Project tools.
6. Validate conceptual, formal, dimensional, numerical, empirical, sensitivity, uncertainty, robustness, and decision properties as applicable.
7. Interpret results inside a named domain of validity and keep all artifacts in the external Project.

### Task categories

| Category | User intent | Typical input | Expected output | Interaction |
|---|---|---|---|---|
| Model formulation | Translate a real situation or incomplete model into a formal specification | problem brief, domain rules, objectives, constraints, equations, parameter ranges, data schema | Markdown model specification, assumption ledger, notation, traceability, solution and validation plan | iterative only when a consequential choice is missing |
| Solution and analysis | Derive, solve, simulate, estimate, calibrate, or analyze an adequately specified model | formal equations, model file, parameter set, data, solver requirements | derivation, bounded script or notebook, solver result, solution record, limitations | normally single-turn for bounded work; iterative for scale, tool, or method decisions |
| Model validation | Determine whether a model, implementation, result, or claim is fit for a stated use | specification, implementation, data, calibration record, outputs, benchmarks, acceptance criteria | Markdown validation report with evidence, scoped assessment, sensitivity and uncertainty results | iterative when required evidence or validation criteria are missing |
| Decision and scenario analysis | Compare alternatives or identify robust choices and decision reversals | validated or explicitly provisional model, choices, risk preferences, scenarios, parameter ranges | decision table or memo, thresholds, trade-offs, robust actions, value-of-information priorities | iterative when preferences or scenario bounds materially control the result |

### Modes

- **Formulation Mode:** creates or repairs a model specification and its traceability and validation plan.
- **Solution Mode:** derives or executes a solution for a sufficiently complete model.
- **Validation Mode:** tests a model and its claims against a stated purpose without silently repairing it.
- **Decision Analysis Mode:** uses a validated or explicitly provisional model to compare alternatives, scenarios, trade-offs, and decision reversals.

These modes are justified because they change prerequisites, orchestration, Skill selection, mutation and computation behavior, evidence requirements, and artifact form. A task may move from Formulation to Solution or Validation when the required contract exists. Explicit user mode selection takes precedence.

### Inputs

Inputs may include user questions, problem statements, mathematical expressions, constraints, objectives, parameter tables, data and schemas, domain rules, causal assumptions, probability distributions, priors, existing model specifications, solver files, code, notebooks, model outputs, calibration records, residuals, benchmarks, scenarios, screenshots, diagrams, and technical documents.

The Agent does not impose a file-type restriction. Complex raw documents use `document-understanding` only when structural recovery is needed.

### Outputs and artifacts

- **Markdown Project Artifacts:** model specification, assumption or parameter ledger, solution record, calibration note, validation report, sensitivity or robustness analysis, scenario comparison, and decision memo.
- **Project-native artifacts:** bounded scripts, notebooks, solver inputs, configuration, data transformations, plots, and computed outputs needed to perform the modeling task.
- **Knowledge Artifact candidates:** stable reusable model abstractions or validation methods only when the user explicitly selects them for long-term reuse.

Markdown remains canonical for durable prose. Executable and machine-readable artifacts retain their Project-native formats.

### Explicit boundaries

- Literature discovery, paper reading, evidence synthesis, and literature-grounded parameter support belong to the Research Agent.
- Course teaching, guided practice, and assessment belong to the Learning Agent.
- Publication-quality drafting and revision belong to the Writing Agent.
- Production software, repository-wide implementation, debugging, testing, and deployment belong to the Coding Agent.
- The Modeling Agent may create bounded transparent calculations, scripts, notebooks, or solver inputs solely to formulate, solve, or validate a model. It must hand off maintainable services, packages, pipelines, interfaces, or substantial software engineering.
- It does not invent objectives, constraints, data, parameter values, probabilities, priors, empirical relationships, solver output, or validation evidence.
- It does not claim universal model validity; every assessment is scoped to a use, domain, version, and evidence state.
- It does not assume a Zotero, Obsidian, data-platform, solver, experiment-tracking, or remote-compute integration exists.

Default durable technical artifacts are English-first with concise Chinese annotation on first occurrence of difficult terminology when useful. An explicit user language or Project convention overrides that default.

## 2. Capability map

| Capability | Type | Reason |
|---|---|---|
| Mode, risk, scope, model-use, and task routing | Agent Logic | Controls orchestration, prerequisites, authority, and artifact behavior |
| Model-family and solution-strategy selection | Agent Logic | Depends on the whole problem contract and available Project context |
| Sequence formulation, solution, validation, and decision analysis | Agent Logic | Specialist-level orchestration rather than a portable atomic capability |
| Translate a real-world problem into an auditable formal model | New Skill | Coherent, reusable, independently testable across domains and Agents |
| Validate model fitness, sensitivity, uncertainty, robustness, and claims | New Skill | Coherent reusable method distinct from software testing and data profiling |
| Mathematical derivation, proof, algorithms, and formal solution analysis | Existing Skill | `stem-reasoning` already covers this boundary |
| Recover a complex source specification, diagram, or notebook | Existing Skill | `document-understanding` already covers faithful structure recovery |
| Present a Pareto front, trajectory, sensitivity surface, residual pattern, or scenario comparison | Existing Skill | `visualization` already owns visual selection and presentation |
| Literature-supported structure, parameters, priors, or benchmarks | Specialist handoff | Research Agent owns discovery, paper analysis, and evidence synthesis |
| Solver libraries, symbolic systems, statistical packages, and simulation engines | External tool | Selected from Project requirements; a tool is not the general modeling method |
| Project rules, data definitions, domain constraints, and accepted tolerances | Project-specific | Must remain in the external Project |
| Zotero, Obsidian, data platforms, remote solvers, experiment tracking, and compute services | Integration | Deferred and unnecessary for the local core Agent |

## 3. Existing Skill audit

| Capability | Existing Skill | Coverage | Recommendation |
|---|---|---:|---|
| Formal mathematics, optimization, statistics, algorithms, and derivations | `stem-reasoning` | Full for reasoning and solving; partial for the full modeling cycle | Reuse unchanged in Solution Mode and for nontrivial checks |
| Complex document or notebook recovery | `document-understanding` | Full | Reuse unchanged only when normal file reading is insufficient |
| Charts, diagrams, and model-result visuals | `visualization` | Full for presentation | Reuse unchanged after model semantics and data are established |
| Source-grounded assumptions or parameter evidence | `literature-search`, `document-understanding`, `knowledge-extraction`, `evidence-synthesis` | Full within research tasks | Handoff to Research Agent rather than route the normal Modeling path through research Skills |
| Software behavior and completion evidence | `software-verification` | Partial but wrong primary object | Keep with Coding Agent; software tests do not establish model validity |
| Real-world-to-formal model formulation | none | None | Add `model-formulation` |
| Model validity, sensitivity, uncertainty, robustness, and decision adequacy | none | None | Add `model-validation` |

Extending `stem-reasoning` into problem framing and requirement traceability would blur mathematical reasoning with modeling orchestration. Extending `software-verification` would conflate correct implementation with a valid model. A dedicated sensitivity Skill is unnecessary because sensitivity is one validation method and depends on the same model-use contract.

## 4. External search results

The search followed official or first-party sources first, then maintained open-source Agent Skills. No repository was cloned and no external Skill implementation was copied into this repository.

### OpenAI `validate-data`

- Source: [OpenAI role-specific plugins](https://github.com/openai/role-specific-plugins/tree/main/plugins/data-analytics/skills/validate-data)
- License and maintenance: MIT; repository was not archived and showed a 2026-07-13 push when checked on 2026-08-15.
- Relevance: strong inventory → methodology and assumptions → data → independent calculation → reasonableness → conclusion → scoped confidence sequence. It emphasizes decision impact, reproducibility, unverified claims, and proportionate checks.
- Limitation: built for business/data-analysis artifacts, connectors, metrics, SQL, dashboards, and stakeholder sharing. It does not cover model structure, identifiability, solver status, calibration/validation separation, numerical conditioning, or model-domain boundaries.

### OpenAI `jupyter-notebooks`

- Source: [OpenAI role-specific plugins](https://github.com/openai/role-specific-plugins/tree/main/plugins/data-analytics/skills/jupyter-notebooks)
- License and maintenance: MIT, same maintained first-party repository.
- Relevance: strong notebook structure, reproducibility, top-to-bottom execution, explicit assumptions, and result checks.
- Limitation: owns an artifact surface, not modeling semantics. It optionally adds Jupyter dependencies and assumes data-analytics routing. A general Modeling Agent must not require notebooks.

### OpenAI `market-sizing`

- Source: [OpenAI role-specific plugins](https://github.com/openai/role-specific-plugins/tree/main/plugins/data-analytics/skills/market-sizing)
- License and maintenance: MIT, same maintained first-party repository.
- Relevance: useful formulation pattern: define the decision boundary, choose a simple model, separate facts from assumptions, expose the calculation chain, and test decision-useful sensitivity.
- Limitation: specific to TAM/SAM/SOM and business data sources; mandatory report and connector assumptions do not fit a domain-general Modeling Agent.

### K-Dense `pymoo`, `SimPy`, `statsmodels`, and `SymPy`

- Sources: [pymoo](https://github.com/K-Dense-AI/scientific-agent-skills/tree/main/skills/pymoo), [SimPy](https://github.com/K-Dense-AI/scientific-agent-skills/tree/main/skills/simpy), [statsmodels](https://github.com/K-Dense-AI/scientific-agent-skills/tree/main/skills/statsmodels), and [SymPy](https://github.com/K-Dense-AI/scientific-agent-skills/tree/main/skills/sympy)
- License and maintenance: individual Apache-2.0, MIT, BSD-3-Clause, or upstream SymPy terms; the parent repository was active with a 2026-08-14 push when checked on 2026-08-15.
- Relevance: high-quality, concrete guidance for multi-objective optimization, discrete-event simulation, statistical modeling, symbolic mathematics, diagnostics, and reproducible examples.
- Limitation: each is library-specific and requires Python packages or bundled references and scripts. None decides whether its model family is appropriate, formulates a domain-general model, or establishes fitness for a real decision.

### K-Dense `uncertainty-and-units`

- Source: [K-Dense Scientific Agent Skills](https://github.com/K-Dense-AI/scientific-agent-skills/tree/main/skills/uncertainty-and-units)
- License: MIT.
- Relevance: particularly strong on explicit measurement models, units, correlated uncertainty, sensitivity coefficients, Monte Carlo cross-checks, plausibility, and disciplined uncertainty reporting.
- Limitation: specializes in metrology and physical quantities; it requires Pint, uncertainties, NumPy, and SciPy for its numerical tools. Adopting it as the general validation capability would overfit one domain and add unnecessary dependencies.

### K-Dense Science Superpowers

- Sources: [designing-the-analysis](https://github.com/K-Dense-AI/science-superpowers/tree/main/skills/designing-the-analysis) and [verifying-results-before-claiming](https://github.com/K-Dense-AI/science-superpowers/tree/main/skills/verifying-results-before-claiming)
- License and maintenance: MIT license file; repository showed a 2026-08-13 push when checked on 2026-08-15.
- Relevance: makes assumptions, decision rules, confounds, validity threats, known-answer simulation, fresh execution, and actual-output inspection explicit.
- Limitation: embeds a complete computational-science methodology with fixed paths, preregistration, frequent commits, mandatory cross-Skills, and subagent workflow. It targets confirmatory scientific analysis rather than general mathematical and decision modeling.

### K-Dense `what-if-oracle`

- Source: [K-Dense Scientific Agent Skills](https://github.com/K-Dense-AI/scientific-agent-skills/tree/main/skills/what-if-oracle)
- License: CC BY-NC-SA 4.0 with commercial use requiring a separate license.
- Relevance: scenario framing, trigger conditions, robust actions, and second-order effects.
- Limitation: forces four-to-six narrative branches, arbitrary probability distributions, unsupported golden-ratio weighting, decorative output, and speculative claims. The license and methodology are unsuitable for adoption.

The OpenAI Skills catalog confirms the concise `SKILL.md` and progressive-disclosure packaging used here: [openai/skills](https://github.com/openai/skills). No popularity metric was used as a quality or selection criterion.

## 5. Candidate evaluation matrix

Scores are 0–5, where 5 is strongest. Dependency cost and overlap risk use 5 for the lowest cost or risk.

| Capability | Candidate | Functional fit | Architecture fit | Instruction quality | Dependency cost | Maintainability | License | Overlap risk | Decision |
|---|---|---:|---:|---:|---:|---:|---|---:|---|
| General model validation | OpenAI `validate-data` | 4 | 5 | 5 | 5 | 5 | MIT | 5 | ADAPT |
| Reproducible result claims | Science Superpowers `verifying-results-before-claiming` | 3 | 3 | 3 | 4 | 4 | MIT | 4 | Supporting reference |
| Model formulation | OpenAI `market-sizing` | 3 | 4 | 5 | 4 | 5 | MIT | 4 | Supporting reference; too domain-specific to adapt |
| Model execution artifact | OpenAI `jupyter-notebooks` | 3 | 4 | 5 | 2 | 5 | MIT | 4 | Do not make core; use Project tooling when appropriate |
| Optimization solving | K-Dense `pymoo` | 3 | 3 | 4 | 2 | 4 | Apache-2.0 | 5 | Context-dependent future option, not core |
| Simulation solving | K-Dense `SimPy` | 3 | 3 | 5 | 3 | 4 | MIT | 5 | Context-dependent future option, not core |
| Statistical or symbolic solving | K-Dense `statsmodels` / `SymPy` | 3 | 3 | 4 | 2 | 4 | BSD-3-Clause / upstream | 5 | Context-dependent future options, not core |
| Physical uncertainty | K-Dense `uncertainty-and-units` | 3 | 3 | 5 | 1 | 4 | MIT | 3 | Keep as a future domain-specific option |
| Scenario analysis | K-Dense `what-if-oracle` | 2 | 2 | 2 | 5 | 3 | CC BY-NC-SA 4.0 | 2 | Reject |

## 6. Adopt / Adapt / DIY decision ledger

### Model formulation

- **Decision:** DIY.
- **Chosen candidate/reference:** no directly suitable reusable Skill; OpenAI `market-sizing` and K-Dense tool Skills are design references only.
- **Reason:** available Skills are either domain-specific, tool-specific, contest-oriented, or monolithic. Adapting them would require replacing most semantics and would still risk overlap with Agent orchestration.
- **What is added:** a compact capability for the model-use contract, input-status ledger, model-class selection, formal specification, requirement traceability, basic formulation checks, solution requirements, and validation plan.
- **Dependencies:** none.
- **Risks:** becoming another general problem-solving Agent. Mitigation: stop at an auditable specification and coordinate derivation with `stem-reasoning`, validation with `model-validation`, and production implementation with Coding.

### Model validation

- **Decision:** ADAPT.
- **Chosen candidate:** OpenAI `validate-data`; Science Superpowers verification and K-Dense uncertainty practices are supporting references.
- **Keep:** artifact and claim inventory, purpose alignment, assumption review, independent recalculation, reasonableness checks, evidence-to-conclusion traceability, proportional validation, prioritized issues, unverified surfaces, and scoped confidence.
- **Remove:** data-analytics plugin routing, business KPI language, SQL and dashboard defaults, connector lanes, mandatory stakeholder-report handoff, and raw data-quality ownership.
- **Modify:** change the validated object from a data-analysis artifact to a mathematical or computational model and its stated use.
- **Add:** conceptual and structural validity, dimensions and conservation, feasibility and identifiability, solver status and numerical behavior, specification-to-implementation consistency, calibration-versus-validation separation, sensitivity and uncertainty types, robustness, decision reversals, and domain-of-validity boundaries.
- **Dependencies:** none.
- **Risks:** overlap with `software-verification`. Mitigation: explicitly separate model fitness from software correctness and hand implementation defects to Coding.

### Sensitivity, uncertainty, robustness, and scenarios

- **Decision:** keep inside `model-validation`; do not add another Skill.
- **Reference:** OpenAI `market-sizing` for simple decision-useful sensitivity and K-Dense `uncertainty-and-units` for rigorous domain-specific methods.
- **Reason:** these checks share the same model-use, evidence, uncertainty, and decision contract. A separate generic Skill would compete for the same trigger and fragment the validation result.
- **Risk:** insufficient depth in specialized metrology or uncertainty quantification. Mitigation: evaluate a domain-specific Skill later when repeated Project demand justifies it.

### Model solving and execution

- **Decision:** reuse `stem-reasoning`, Agent logic, and Project-native tools; no new Skill.
- **Reason:** solution methods vary by model class, and mature libraries already implement solvers. A generic `model-solving` Skill would either duplicate `stem-reasoning` or become a monolithic catalog.
- **Risk:** repeated library-specific work. Mitigation: evaluate a narrow tool Skill only after concrete repeated demand.

### Adopt decisions

None. No candidate is both domain-general and low-modification enough to adopt unchanged.

## 7. Proposed final Skill pool

### Reuse unchanged

- `stem-reasoning`
- `document-understanding`
- `visualization`

### Adopt

None.

### Adapt

- `model-validation`

### DIY

- `model-formulation`

### Not needed as separate Skills

- model-solving
- sensitivity-analysis
- scenario-analysis
- optimization-modeling
- statistical-modeling
- simulation-modeling
- notebook-modeling
- solver-selection
- parameter-management

### Intentionally outside the normal route

- research and literature Skills
- learning and assessment Skills
- writing Skills
- debugging, software-verification, and code-review Skills
- tool-specific solver Skills and deferred integrations

## 8. Agent-to-Skill routing map

```text
User modeling request
        ↓
Modeling Agent establishes question, decision, scope, evidence state, risk, and mode
        ↓
Real-world problem or incomplete model?
        └─ yes → model-formulation
                    └─ nontrivial derivation or formal reasoning? → stem-reasoning
        ↓
Complete model needs derivation, optimization, estimation, or simulation?
        └─ yes → stem-reasoning + Project-native tools as needed
        ↓
Validation, sensitivity, uncertainty, robustness, or scenario stress test?
        └─ yes → model-validation
        ↓
Complex raw source specification?
        └─ yes → document-understanding
Result relationship materially clearer visually?
        └─ yes → visualization
Literature evidence required?
        └─ yes → Research Agent handoff
Production implementation or software defect?
        └─ yes → Coding Agent handoff
        ↓
Modeling Agent interprets within the stated domain, classifies artifacts, and reports limits
```

Core, task-shaped Skills are `model-formulation` and `model-validation`. Context-dependent Skills are `stem-reasoning`, `document-understanding`, and `visualization`. The user does not need to name any Skill.

## 9. Implementation order

1. Implement `model-formulation` with no dependencies or bundled resources.
2. Implement `model-validation`, preserving attribution in this decision record rather than copying external instruction text.
3. Implement the Modeling Agent definition with clear handoffs to Research, Coding, Writing, and Learning.
4. Add runtime sync and validation entries, documentation indexes, and focused eval prompts.
5. Deploy from the WSL canonical source and verify formulation, validation/decision routing, language behavior, and Project isolation from unrelated Projects.

## 10. Open questions

None block implementation. Integration interfaces are not required for the core Agent, so they remain deferred with implementation. Tool-specific solver, notebook, metrology, uncertainty-quantification, experiment-tracking, and remote-compute capabilities should be evaluated only after repeated concrete demand demonstrates a reusable gap.

## Runtime verification

The canonical sync command was run repeatedly, including twice after the final routing refinement. Every run generated and validated five Agent TOML projections and sixteen canonical Skill links. `~/.codex/agents/modeling_agent.toml` parsed with exactly `name`, `description`, and `developer_instructions`; the repository validator confirmed that its instructions match canonical `agents/modeling-agent/AGENT.md`. Both new Skill links resolved to the WSL repository.

Fresh non-interactive Codex Main Runtime sessions with multi-agent support were started from unrelated Git Projects under `/tmp`, without adding writable roots and without naming Skills in their prompts:

1. **Formulation:** the verified invocation began `Have the Modeling Agent turn brief.md into an auditable model specification...`. The main runtime delegated to a subagent whose session metadata recorded `agent_role: modeling_agent`. The Specialist read only `~/.agents/skills/model-formulation/SKILL.md`, created a Markdown model specification, included a high-level validation plan, annotated difficult terminology in Chinese on first occurrence, did not solve or validate the model, and changed no Project input.
2. **Validation and decision stress test:** the verified invocation began `Have the Modeling Agent validate model-spec.md for its stated staffing decision...`. The delegated Specialist read `model-validation` and the relevant `stem-reasoning` Skill for independent recomputation. It found that the reported `(p=8,h=80)` decision was not optimal at demand 400, failed demand 520 by 120 hours, and could not support the stated cross-scenario decision. It kept solver convergence separate from model validity and recorded conditional robust and adaptive interpretations without inventing scenario probabilities.

The validation Project's tracked `model-spec.md` SHA-256 remained `c9cadb1a3297c9820cf5486e7f1d48984e5397b887d36f28874e382a044ca9da` before and after the session. Subagent execution records referenced only their respective Project roots and the selected runtime Skill files: no parent search, sibling Project, home context, or canonical-repository context was accessed. No test source or generated artifact appeared in `personal-ai-os`, and no integration, network, dependency installation, commit, push, or external publication action occurred inside the test Projects. The CLI-created `main-response.md` files are harness captures written after each subagent's own final scope check; the Specialist-created artifacts were `model-spec.md` and `validation-report.md` respectively.

An initial formulation forward test also produced a correct isolated artifact, but it read `model-validation` merely to expand the high-level validation plan. That run was not accepted as final routing evidence. The Agent and `model-formulation` Skill were tightened so the formulation capability owns its initial validation-plan section; the runtime was regenerated and the fresh formulation run then selected only `model-formulation`.

Current CLI warning: an initial custom-agent call that combines an explicit Agent type with a full-history fork is rejected by Codex CLI 0.147.0. In both accepted runs, the main runtime preserved the requested scope, retried with isolated/scoped context, and completed the real `modeling_agent` delegation. The user-facing method remains `Have the Modeling Agent ...`; users do not need to choose fork settings or name Skills.
