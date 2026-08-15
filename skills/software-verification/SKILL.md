---
name: software-verification
description: Verify software behavior and completion claims against acceptance criteria using fresh, proportional evidence. Use after implementing, fixing, refactoring, or migrating software; when asked to test or validate a change; and before claiming code is complete or passing. Do not use for root-cause diagnosis, read-only code review, formal mathematical proof, or unrequested infrastructure changes.
---

# Software Verification

Establish what must be observably true, gather the smallest sufficient fresh evidence, and report exactly what that evidence proves.

## Establish the verification contract

Identify:

- requested behavior and acceptance criteria;
- changed components and affected execution paths;
- risk level and important failure modes;
- supported environment and Project-native commands;
- unavailable credentials, services, hardware, data, or tooling;
- claims that the final response may need to make.

Resolve repository instructions, build manifests, test configuration, and existing test patterns before choosing commands. Do not substitute a convenient check for the behavior the user actually requested.

## Build a proportional evidence plan

Select only the layers that can detect relevant failures:

| Evidence layer | Use when it proves |
|---|---|
| Diff and state inspection | intended files changed, unrelated work was preserved, generated artifacts are understood |
| Formatting, lint, or static analysis | syntax, style, type, or static contract compliance |
| Build or compile | code and assets assemble for the target configuration |
| Focused automated test | the changed behavior and its important boundary or error case |
| Broader unit or integration suite | affected callers, components, or contracts still work together |
| End-to-end or runtime check | the user-visible or system-visible outcome occurs through the real path |
| Manual inspection | behavior that cannot be automated economically, with exact observations recorded |

Map every material acceptance criterion to at least one relevant observation or mark it unverified. Passing lint is not proof of runtime behavior; an HTTP success status is not proof that the intended provider, code path, or state transition was used.

## Design useful tests

- Prefer a focused regression test for a bug or behavior change when the Project has a suitable harness.
- Demonstrate that a new regression test can detect the missing or broken behavior when practical. A red–green sequence is strong evidence, not a universal ritual.
- Test observable behavior and contracts rather than private implementation details or mocks alone.
- Cover important positive, negative, boundary, failure, compatibility, and migration cases according to risk.
- Follow existing Project test organization and helpers. Do not create a parallel framework for one change.
- Do not weaken assertions, delete coverage, or change expected behavior merely to make a test pass.

## Execute from narrow to broad

1. Run the fastest focused check that exercises the changed behavior.
2. Read the full relevant output, exit status, failure count, warnings, and skipped tests.
3. Resolve failures caused by the authorized change before expanding scope.
4. Run broader affected suites, builds, or runtime checks when they add confidence.
5. Inspect the final diff and repository state after commands that may generate files.

Use fresh results from the current code state. Do not present an earlier run, another Agent's assertion, or a partial command as current proof. Independently inspect delegated work before relying on it.

Do not install packages, contact remote services, start production workloads, rewrite snapshots, migrate live data, or alter infrastructure solely to complete verification unless the user authorized that action. When required tooling is missing, report the blocked layer and continue with safe independent evidence.

## Interpret results precisely

Classify each planned check:

- **Passed:** the command or observation succeeded and demonstrates the mapped criterion.
- **Failed:** behavior or a Project check does not meet the criterion.
- **Blocked:** the check cannot run because a named prerequisite is unavailable.
- **Not run:** deliberately omitted, with a reason and the residual risk.

Separate failures introduced by the change from pre-existing or unrelated failures when evidence supports that distinction. Never hide warnings, skips, flakiness, environment mismatches, or incomplete coverage behind a general “tests pass” statement.

## Report evidence before conclusions

Return a concise record containing, as applicable:

- acceptance criterion or risk checked;
- exact command or manual procedure;
- result and important counts or observations;
- what the evidence proves;
- failed, blocked, or untested surfaces;
- final claim limited to that evidence.

Do not claim a bug is fixed unless the original failure or a faithful regression is now absent through the relevant path. Do not claim the whole Project passes after a focused test alone.

## Coordination

Use `systematic-debugging` first when the reason for a failure is unknown. Use this Skill after a root-cause fix or implementation. In a read-only review, let `code-review` own the review contract and use verification commands only when they are safe and materially improve confidence.
