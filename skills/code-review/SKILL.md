---
name: code-review
description: Perform a read-only, scoped review of a working tree, staged diff, commit range, branch diff, focused file set, or pasted code for concrete correctness, security, compatibility, reliability, and test risks. Use when the user asks for code review, diff review, merge-safety assessment, or implementation audit. Do not edit code, fix findings, publish comments, or review general prose.
---

# Code Review

Find actionable defects that the change introduces or fails to address. Ground every finding in an expected behavior and an observable failure path; do not reward review volume.

## Keep the review read-only

Do not edit files, stage changes, commit, reset, checkout, rebase, merge, push, publish comments, or alter remote state. A request to review does not authorize fixes. Use read-only Git and repository inspection; run a Project command only when it is safe, allowed, and materially strengthens the evidence.

## Establish scope and authority

Resolve:

- review target: working tree, staged changes, commit range, branch comparison, files, or pasted code;
- precise baseline and target when Git is available;
- user request, acceptance criteria, issue, specification, API or data contract, migration decision, and repository rules;
- changed-file inventory and important generated or dependency files;
- known test results and environment limitations.

Choose the narrowest scope that answers the request. Do not silently review the entire repository, but trace outside changed lines where callers, callees, contracts, shared state, or data flow can expose a regression.

## Understand intent before judging

Read the complete relevant diff and enough surrounding code to understand current behavior. Use explicit user and Project requirements as product authority. Treat tests, current implementation, and history as behavioral evidence, not unquestionable intent.

When a possible issue depends on an unconfirmed product choice, ask or report it as a question rather than asserting a defect.

## Review by propagated risk

Prioritize dimensions that the change can affect:

- correctness, control flow, state transitions, edge cases, and error paths;
- input validation, authorization, trust boundaries, secrets, privacy, and unsafe external effects;
- public APIs, CLI behavior, configuration, serialization, persistence, schemas, and backward compatibility;
- migrations, rollback, cleanup, partial failure, retries, idempotency, ordering, caching, concurrency, and races;
- resource use and performance only where a credible regression path exists;
- positive, negative, boundary, regression, integration, and migration test coverage;
- requirement completeness and unintended behavior changes.

Do not report pure style preferences, speculative future abstractions, broad refactors without a failure mode, or issues outside the requested scope.

## Finding acceptance test

Accept a finding only when you can state:

1. the governing expectation or invariant;
2. the concrete location and affected execution path;
3. the input, state, or condition that triggers the problem;
4. the observable impact;
5. why existing handling or tests do not prevent it;
6. confidence and any material assumption.

Re-read the cited code before reporting. Merge duplicate manifestations of the same root issue. Reduce severity or use a question when evidence is incomplete; never invent a defect to make the review look thorough.

## Severity

- **Blocker:** credible security compromise, destructive data loss, or a change that cannot safely ship.
- **Major:** material correctness, compatibility, availability, privacy, or reliability regression.
- **Minor:** localized but concrete defect or meaningful test gap with limited impact.
- **Question:** intent or authority must be resolved before the implementation can be judged; not counted as a defect.

Severity reflects impact and likelihood, not code size or reviewer preference.

## Output findings first

Order findings by severity. For each finding include:

- concise title;
- severity;
- specific file and line or smallest useful line range;
- triggering condition;
- observed or logically demonstrated impact;
- expected-behavior basis;
- concise remediation direction when useful;
- confidence or unresolved assumption.

Then state the reviewed scope, verification performed, and material blind spots. If no qualifying findings exist, say so directly and list residual risks or untested surfaces; do not replace findings with praise or a generic code summary.

## Coordination

Use `stem-reasoning` only for algorithmic or formal-correctness questions. Use `software-verification` for implementation completion, not as a substitute for review judgment. If the user later authorizes fixes, end the read-only review and let the Coding Agent begin a separate Implementation or Debugging task.
