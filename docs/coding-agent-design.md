# Coding Agent Design Decision

## Status

Implemented and runtime-verified on 2026-08-15 with Codex CLI 0.147.0. The frozen runtime architecture, WSL canonical-source policy, Project isolation, and existing Learning, Research, and Writing Agent semantics remain unchanged.

## 1. Agent functional definition

### Mission

The Coding Agent turns an authorized software goal into evidence-backed repository analysis, technical plans, code changes, tests, diagnoses, or review findings. It works within the external Project's conventions and permissions, preserves unrelated user work, and does not claim success without verification proportional to the change.

### Primary responsibilities

1. Establish the requested outcome, acceptance criteria, mutation authority, risk, scope, and available Project context.
2. Resolve repository instructions and understand the smallest relevant execution path before planning or editing.
3. Select a coding mode and sequence the minimum useful capabilities and tools.
4. Make coherent, minimal changes that follow the Project's architecture, language, framework, and dependency conventions.
5. Diagnose failures from evidence rather than speculative patches.
6. Verify behavior, inspect the final diff, preserve user changes, and report limitations or untested surfaces honestly.
7. Keep code, tests, logs, plans, and reports inside the external Project.

### Task categories

| Category | User intent | Typical input | Expected output | Interaction |
|---|---|---|---|---|
| Build or change | Add a feature, refactor, migrate, automate, or update tooling | repository, requirement, acceptance criteria, issue text, design | source changes, tests, configuration, migration, concise handoff | usually single-turn for bounded changes; iterative for risky or ambiguous work |
| Diagnose or fix | Explain or repair a failure | reproduction, logs, stack trace, failing test, environment details, code | root-cause account; and, only when authorized, regression test and fix | iterative when reproduction or evidence is incomplete |
| Review | Assess a diff, branch, files, or implementation | review scope, baseline, requirements, diff, test evidence | prioritized evidence-backed findings or an explicit no-findings result | normally single-turn and read-only |
| Technical design | Decide how software should change before implementation | goal, constraints, repository, APIs, schemas, existing architecture | Markdown design or implementation plan with risks and verification strategy | iterative only when a material decision remains open |
| Validation | Add tests or determine whether a change works | acceptance criteria, code or diff, project test tooling | tests, command results, coverage limits, observable outcome | usually single-turn after scope is known |

### Modes

- **Implementation Mode:** modifies software to satisfy an authorized requirement, including bounded refactors, migrations, dependency changes, tests, and technical documentation.
- **Debugging Mode:** reproduces and isolates an observed failure, establishes the root cause, and implements a fix only when the request includes fixing it.
- **Review Mode:** performs a read-only, scoped assessment and returns findings ordered by actual impact.
- **Design Mode:** analyzes the repository and produces a technical decision or implementation plan without changing production code unless the user explicitly continues to implementation.

These modes are justified because they change mutation authority, evidence requirements, Skill routing, interaction, and output policy. A task may transition from Debugging or Design to Implementation only when the user's request authorizes that transition.

### Inputs

Inputs may include repositories, files, issue descriptions, requirements, acceptance criteria, diffs, branches, commits, pull-request exports, build manifests, dependency locks, schemas, API contracts, configuration, migrations, test suites, CI logs, stack traces, runtime logs, benchmark results, code samples, notebooks, screenshots, and user questions.

### Outputs and artifacts

- **Project Artifacts in native formats:** source code, tests, fixtures, configuration, schemas, migrations, scripts, notebooks, and generated files required by the Project.
- **Markdown Project Artifacts:** technical designs, implementation plans, root-cause reports, review reports, verification notes, migration plans, and handoff summaries.
- **Knowledge Artifact candidates:** stable, reusable engineering patterns or architecture decisions only when the user explicitly selects them for long-term reuse.

Markdown remains canonical for durable prose, but source code and machine-readable files retain the format required by the Project.

### Explicit boundaries

- The Agent does not conduct literature discovery, paper analysis, or evidence synthesis; those belong to the Research Agent.
- It does not produce publication prose or general audience adaptation; those belong to the Writing Agent.
- It does not teach course material or assess learning; those belong to the Learning Agent.
- It may implement an already specified mathematical or computational model, but model formulation, assumptions, solution methodology, model validation, and decision analysis belong to the Modeling Agent.
- A diagnosis-only request does not authorize a fix. A review request is read-only unless the user separately requests changes.
- It does not deploy, publish, merge, commit, push, alter remote services, rotate credentials, or perform destructive data or Git operations without explicit authority.
- It does not invent requirements, test results, runtime behavior, APIs, packages, or configuration values.
- It does not install dependencies merely to make validation convenient; dependency changes require a concrete Project need and appropriate authority.
- It does not assume GitHub, CI, issue-tracker, cloud, or deployment integrations exist.

Conversation language follows the user. Code identifiers, comments, documentation, and error messages follow the Project's established conventions or explicit requirements; do not inject bilingual annotations into source code unless requested.

## 2. Capability map

| Capability | Type | Reason |
|---|---|---|
| Mode, risk, authority, and task routing | Agent Logic | Controls orchestration and mutation permissions |
| Repository-instruction resolution and change-surface discovery | Agent Logic | Native repository work shaped by Project context rather than a portable domain method |
| Technical design, implementation strategy, edit sequencing, and dependency policy | Agent Logic | Core Coding Agent orchestration |
| Evidence-driven root-cause diagnosis | New Skill | Coherent, reusable, independently testable capability |
| Select and run proportionate software verification | New Skill | Reusable across software implementation tasks without replacing model validation |
| Read-only, evidence-backed review of code changes | New Skill | Distinct mutation and output contract; reusable outside implementation |
| Algorithms, complexity, mathematics, and formal correctness | Existing Skill | Covered by `stem-reasoning` when genuinely needed |
| Recover a complex external specification, notebook, image, or document | Existing Skill | Covered by `document-understanding` when normal repository reading is insufficient |
| Architecture or execution-flow visualization | Existing Skill | Covered by `visualization` when a diagram materially helps |
| Compilers, interpreters, test runners, linters, formatters, package managers, and local Git | External tool | Project-native execution surfaces, not integrations or Skills |
| Repository rules, build commands, framework conventions, and house style | Project-specific | Must be discovered from the external Project |
| GitHub, CI, issue tracker, deployment, and cloud operations | Integration | Deferred; not required to define or test the Agent locally |

## 3. Existing Skill audit

| Capability | Existing Skill | Coverage | Recommendation |
|---|---|---:|---|
| Read complex non-code specifications or notebooks | `document-understanding` | Full for extraction | Reuse unchanged and only when raw structure needs recovery |
| Algorithmic and mathematical correctness | `stem-reasoning` | Partial | Reuse unchanged as a context-dependent capability |
| Architecture and execution diagrams | `visualization` | Full | Reuse unchanged when a visual is materially clearer |
| Repository analysis and implementation | none | None | Keep in Agent logic and native Codex tooling; do not create a monolithic implementation Skill |
| Root-cause debugging | none | None | Add `systematic-debugging` |
| Testing and completion evidence | none | None | Add `software-verification` |
| Code or diff review | none | None | Add `code-review` |
| Technical prose | `structured-writing`, `writing-revision` | Available but outside the common path | Use Writing Agent for substantial publication-quality prose; do not preload these Skills |
| Research, learning, and knowledge extraction | remaining local Skills | Out of scope | Do not invoke for normal coding work |

Extending `stem-reasoning` into implementation, debugging, or review would damage its formal STEM boundary. Treating code files as documents would also fail to provide repository execution and change semantics.

## 4. External search results

### OpenAI Codex `code-review`

- Source: [OpenAI Codex repository](https://github.com/openai/codex/tree/main/.codex/skills/code-review)
- License: Apache-2.0 at repository level.
- Relevance: first-party Codex example; requires exact file and line references, collects all findings, and avoids remote review comments unless requested.
- Limitation: a thin repository-specific orchestrator that requires the Codex repository's `code-review-*` Skills, subagent fan-out, GitHub ownership, and label behavior. Its component Skills contain Codex-specific thresholds and architecture rules.

### Superpowers `systematic-debugging`

- Source: [obra/superpowers](https://github.com/obra/superpowers/tree/main/skills/systematic-debugging)
- License: MIT.
- Relevance: strong investigation → pattern comparison → hypothesis testing → root-cause fix sequence, with reproduction and single-variable experiments.
- Limitation: absolutist language, arbitrary retry thresholds, unsupported effectiveness claims, Claude-specific cross-Skill names, missing bundled references if copied alone, and diagnostic examples that require additional secret-safety guards.

### Superpowers `verification-before-completion` and `test-driven-development`

- Sources: [verification-before-completion](https://github.com/obra/superpowers/tree/main/skills/verification-before-completion) and [test-driven-development](https://github.com/obra/superpowers/tree/main/skills/test-driven-development)
- License: MIT.
- Relevance: fresh evidence before completion claims, command/output matching, regression proof, and red–green–refactor where appropriate.
- Limitation: verification focuses too heavily on command success instead of the observable outcome; an active upstream issue documents that gap. The TDD Skill requires test-first and deletion of existing code in circumstances where configuration, legacy systems, generated code, exploratory work, or missing harnesses require a proportional strategy.

### Superpowers code-review materials

- Source: [requesting-code-review](https://github.com/obra/superpowers/tree/main/skills/requesting-code-review)
- License: MIT.
- Relevance: explicit scope, requirements comparison, read-only review, severity calibration, exact locations, and technical pushback on incorrect feedback.
- Limitation: assumes a dedicated reviewer subagent and a specific development methodology; it mixes requesting a review with performing one.

### JUNERDD `code-review`

- Source: [JUNERDD/skills](https://github.com/JUNERDD/skills/tree/main/skills/code-review)
- License: MIT.
- Relevance: strong expected-behavior basis, propagated-risk analysis, read-only enforcement, uncertainty, coverage accounting, and evidence-backed findings.
- Limitation: requires an orchestration-assessment subagent, persistent lineage reports, fingerprints, templates, and a Python validator. This is excessive for ordinary Project reviews and would make one Skill behave like a review platform.

### Anthropic `webapp-testing`

- Source: [Anthropic skills](https://github.com/anthropics/skills/tree/main/skills/webapp-testing)
- License: per-Skill terms.
- Relevance: useful Playwright and local-server mechanics for a specific future web testing capability.
- Limitation: limited to web applications and requires Python, Playwright, browser binaries, helper scripts, and server lifecycle assumptions. It should not become a dependency of a general Coding Agent.

### Superpowers `writing-plans`

- Source: [obra/superpowers](https://github.com/obra/superpowers/tree/main/skills/writing-plans)
- License: MIT.
- Relevance: file-specific plans, test commands, requirement coverage, and self-review.
- Limitation: fixed storage paths, mandatory TDD and frequent commits, two-to-five-minute task granularity, embedded complete code, and subagent execution handoffs. Technical planning remains more coherent as Agent logic governed by Project needs.

No popularity metric was used as a decision criterion. No external repository, script, dependency, or instruction text is imported.

## 5. Candidate evaluation matrix

Scores are 0–5, where 5 is strongest; dependency cost and overlap risk use 5 for the lowest cost or risk.

| Capability | Candidate | Functional fit | Architecture fit | Instruction quality | Dependency cost | Maintainability | License | Overlap risk | Decision |
|---|---|---:|---:|---:|---:|---:|---|---:|---|
| Debugging | Superpowers `systematic-debugging` | 5 | 4 | 4 | 5 | 4 | MIT | 5 | ADAPT |
| Verification | Superpowers `verification-before-completion` | 4 | 4 | 4 | 5 | 4 | MIT | 5 | ADAPT |
| Verification | Superpowers `test-driven-development` | 3 | 3 | 3 | 5 | 4 | MIT | 4 | Supporting reference |
| Review | OpenAI Codex `code-review` | 3 | 2 | 3 | 2 | 5 | Apache-2.0 | 4 | ADAPT as first-party reference |
| Review | Superpowers review materials | 4 | 3 | 4 | 4 | 4 | MIT | 4 | Supporting reference |
| Review | JUNERDD `code-review` | 4 | 2 | 4 | 2 | 4 | MIT | 3 | Supporting reference |
| Web testing | Anthropic `webapp-testing` | 2 | 3 | 4 | 1 | 4 | per-Skill | 5 | Do not select |
| Planning | Superpowers `writing-plans` | 3 | 2 | 3 | 4 | 4 | MIT | 1 | Keep as Agent logic |

## 6. Adopt / Adapt / DIY ledger

### Systematic debugging

- **Decision:** ADAPT.
- **Chosen candidate:** Superpowers `systematic-debugging`.
- **Keep:** reproduction, complete error reading, recent-change inspection, execution-boundary evidence, working/broken comparison, one explicit hypothesis, minimal experiment, root-cause fix, and regression verification.
- **Remove:** absolutist rhetoric, unsupported success metrics, fixed failed-attempt counts, Claude-specific Skill names, platform-specific secret inspection examples, and required bundled techniques.
- **Modify:** scale the investigation to risk; distinguish diagnosis from fix authority; allow honest non-reproduction; avoid instrumentation that exposes secrets or mutates production.
- **Add:** observed/expected/environment record, competing-hypothesis discipline, stop conditions, rollback awareness, and explicit handoff to `software-verification`.
- **Risk:** slowing trivial fixes. Mitigation: preserve the evidence sequence while allowing a compact path for obvious, reproducible defects.

### Software verification

- **Decision:** ADAPT.
- **Chosen candidate:** Superpowers `verification-before-completion`, informed by `test-driven-development`.
- **Keep:** fresh evidence before claims, full command and exit-status reading, targeted regression proof, red–green–refactor when appropriate, and independent checking of delegated work.
- **Remove:** universal test-first dogma, deletion requirements, moralized language, universal full-suite execution, and claims that a passing command alone proves the intended change.
- **Modify:** select layers by change surface and risk; run focused checks before broader checks; distinguish code failure, test failure, environment failure, and unavailable verification.
- **Add:** acceptance-criterion mapping, intended observable outcome, static/build/runtime/manual evidence classes, dirty-tree inspection, and precise coverage limitations.
- **Risk:** excessive test cost. Mitigation: require the smallest sufficient verification set and explain omitted expensive or unavailable checks.

### Code review

- **Decision:** ADAPT.
- **Chosen references:** OpenAI Codex `code-review`, Superpowers review materials, and JUNERDD `code-review`.
- **Keep:** exact scope and baseline, read-only operation, requirements or contract as expected-behavior authority, affected-path tracing, concrete file/line evidence, severity calibration, uncertainty, test-gap review, and explicit coverage limits.
- **Remove:** mandatory subagent fan-out, GitHub labels/comments, Codex-repository rules, arbitrary line thresholds, persistent report lineages, fingerprints, validators, and mandatory praise.
- **Modify:** support working trees, staged diffs, commits, branches, bounded files, and pasted code without requiring a remote platform.
- **Add:** findings-first output, reproducibility conditions, impact, confidence, and a clear no-findings response with residual risks.
- **Risk:** false positives or unbounded review. Mitigation: ground each finding in an observable failure and state unreviewed surfaces.

### Other capabilities

- **ADOPT:** none. Every serious candidate carries repository, platform, dependency, or methodology assumptions that materially change our boundary.
- **DIY:** none. Strong reusable methods exist for all three gaps.
- **Not added:** codebase-analysis, implementation, planning, TDD-only, webapp-testing, security-review, dependency-management, Git, GitHub, CI, deployment, and language/framework Skills. These are Agent orchestration, Project-specific, narrower future capabilities, or deferred integrations.

## 7. Proposed final Skill pool

### Reuse unchanged

- `document-understanding`
- `stem-reasoning`
- `visualization`

### Adopt

None.

### Adapt

- `systematic-debugging`
- `software-verification`
- `code-review`

### DIY

None.

### Not in normal Coding Agent routing

- `assessment`
- `education-learning`
- `evidence-synthesis`
- `knowledge-extraction`
- `knowledge-mapping`
- `literature-search`
- `structured-writing`
- `writing-revision`

## 8. Agent-to-Skill routing map

```text
User software request
        ↓
Coding Agent resolves authority, Project rules, acceptance criteria, risk, and mode
        ↓
Bug, failed test, build failure, or unexplained behavior?
        └─ yes → systematic-debugging
                    └─ fix authorized? → Agent implements root-cause fix
        ↓
Feature, refactor, migration, maintenance, or tooling change?
        └─ yes → Agent inspects repository and implements minimum coherent change
        ↓
Review-only request?
        └─ yes → code-review; no mutation
        ↓
Technical algorithm or formal correctness at issue?
        └─ yes → stem-reasoning
Complex external document or notebook requires recovery?
        └─ yes → document-understanding
Architecture visual materially useful?
        └─ yes → visualization
        ↓
Any implementation or fix completion claim?
        └─ yes → software-verification
        ↓
Coding Agent inspects final diff, reports evidence and limits, and keeps artifacts in Project
```

`systematic-debugging`, `software-verification`, and `code-review` are selected by task shape; they are not all loaded by default. The user should not have to name a Skill.

## 9. Implementation order

1. Implement `software-verification`, which defines the common evidence and completion contract.
2. Implement `systematic-debugging`, handing confirmed fixes to the verification contract.
3. Implement `code-review`, reusing the same evidence vocabulary while enforcing read-only behavior.
4. Implement the Coding Agent definition with Project instructions, authority, dirty-worktree, dependency, and destructive-action safeguards.
5. Add runtime sync and validation entries, active documentation, and focused eval prompts.
6. Deploy from canonical WSL source and verify Implementation, Debugging, and Review routing from unrelated Projects.

## 10. Open questions

None block implementation. GitHub, CI, issue-tracker, package-registry, cloud, and deployment integrations remain deferred because local repositories and Project-native tools are sufficient to define and verify the Agent. Framework-specific test automation, security auditing, browser testing, and deployment may be evaluated later as context-dependent Skills instead of expanding the core pool now.

## Runtime verification

The canonical sync command was run twice successfully. It generated `~/.codex/agents/coding_agent.toml`, linked all three new Skills from `~/.agents/skills/` to the WSL repository, and validated all four Agents and fourteen Skills on each run.

Fresh non-interactive Codex Main Runtime sessions with multi-agent support were started from unrelated Git repositories under `/tmp`, without adding writable roots or naming Skills in their prompts:

1. **Implementation:** the main runtime delegated a bounded Python feature to `coding_agent`. The Specialist loaded only `software-verification`, changed the two intended Project files, and passed four unit tests plus `git diff --check`.
2. **Diagnosis only:** the Specialist loaded only `systematic-debugging`, reproduced `-2400 != 75`, traced the cause to a whole-number percentage used as a direct multiplier, and left Git status and diff empty.
3. **Read-only review:** the Specialist loaded only `code-review`, found that a default-true/truthiness filter violated an exact-boolean contract despite passing tests, and left the working-tree diff hash unchanged.

Subagent session records showed the actual runtime Skill reads and Project-local commands. No Project source appeared in `personal-ai-os`, and no remote integration, network, dependency installation, commit, push, or deployment action occurred.

An earlier implementation run exposed an isolation weakness: the Specialist used `find ..` while looking for `AGENTS.md`. Although it did not modify or consume another Project, that run was not accepted as final evidence. The Agent and eval contract were tightened to prohibit parent and sibling discovery, the runtime was regenerated, and a fresh implementation run contained zero parent, sibling, home, or canonical-repository discovery calls. Reading the selected Skill through `~/.agents/skills/` remains the intended runtime behavior.

Current CLI warning: an initial custom-agent call that combined an explicit Agent type with a full-history fork was rejected. The main runtime retried with scoped context and completed every delegation. The verified user-facing invocation remains `Have the Coding Agent ...`; the user does not need to choose fork settings or name Skills.
