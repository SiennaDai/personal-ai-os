---
name: systematic-debugging
description: Investigate bugs, failing tests, build errors, crashes, performance regressions, flaky behavior, and other unexplained software failures using reproducible evidence and explicit hypotheses. Use before proposing or applying a fix when the root cause is not already demonstrated. Do not use for routine implementation, final verification, code review, or speculative production changes.
---

# Systematic Debugging

Move from observation to a supported causal mechanism before changing behavior. Scale the process to the risk, but do not replace evidence with a plausible patch.

## 1. Define the incident

Record:

- observed behavior and exact error;
- expected behavior and its authority;
- reproduction steps, frequency, and smallest known input;
- relevant environment, version, configuration, and timing;
- recent code, dependency, data, or infrastructure changes;
- whether the user requested diagnosis only or also authorized a fix.

Read complete error messages and the relevant stack, logs, or test output. Preserve evidence before rerunning commands that overwrite it. Never print secrets, tokens, private payloads, or an unfiltered environment merely to inspect configuration.

## 2. Reproduce safely

Use the smallest deterministic reproduction available. Confirm that it fails for the expected reason rather than a setup error. Reduce the input, command, component, or environment while preserving the symptom.

If reproduction is unsafe, destructive, production-only, intermittent, or unavailable:

- do not simulate certainty;
- use existing logs, traces, state, history, and bounded diagnostics;
- state what additional observation would distinguish the leading explanations;
- stop before a risky experiment that lacks authority.

## 3. Trace the failing path

Map the relevant flow across callers, data transformations, state transitions, component boundaries, configuration, persistence, concurrency, and external dependencies. Locate where observed state first diverges from expected state.

Compare with:

- a nearby working path or input;
- the last known good revision or environment when available;
- established repository patterns and contracts;
- recent changes that intersect the failing path.

List material differences without assuming that a familiar symptom identifies the cause.

## 4. Test explicit hypotheses

For each serious hypothesis, state:

```text
Hypothesis: specific mechanism
Because: evidence it explains
Prediction: observable result if true
Experiment: smallest safe discriminator
Outcome: observation
Decision: supported, weakened, or rejected
```

Change one material variable at a time. Prefer read-only inspection, a focused test, temporary diagnostic output, or a controlled local experiment. Remove temporary instrumentation before delivery unless it is intentionally retained and tested.

When an experiment rejects a hypothesis, incorporate the new evidence before trying another change. Repeated failed fixes, expanding shared-state problems, or a required wide refactor indicate that the architecture or initial problem statement needs reconsideration; surface that decision instead of stacking patches.

## 5. Establish the root cause

A root-cause conclusion should identify a specific mechanism that:

- explains the original symptom and relevant error path;
- is consistent with the reproduction and environment;
- accounts for why a working comparison does not fail;
- predicts an observable change when corrected;
- distinguishes cause from downstream damage or masking behavior.

If the evidence supports only a likely cause, label confidence and alternatives. “Could not reproduce” is a valid result when accompanied by the investigation performed and the next discriminating evidence needed.

## 6. Fix only when authorized

For a diagnosis-only request, stop with the causal account and recommended next step. When a fix is authorized:

1. add or identify the smallest faithful regression check when practical;
2. change the root mechanism rather than suppressing its symptom;
3. avoid unrelated refactoring and dependency changes;
4. consider compatibility, cleanup, rollback, and failure behavior;
5. use `software-verification` to test the original outcome and affected paths.

Do not hide a race with arbitrary sleeps, hide an error with retries, broaden exception handling, loosen validation, or delete a failing test unless the intended contract supports that change.

## Output

Report the reproduction, evidence path, root cause or leading hypothesis, ruled-out alternatives when useful, fix scope if authorized, verification result, and remaining uncertainty. Keep logs and diagnostic artifacts inside the external Project and exclude sensitive values.
