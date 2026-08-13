---
name: stem-reasoning
description: Provide rigorous reasoning for mathematics, optimization, statistics, computer science, AI, and machine learning. Use for intuition, formal definitions, derivations, proofs, algorithms, applications, and technical reasoning gaps. Do not use for raw document extraction or evidence-based grading when assessment criteria are required.
---

# STEM Reasoning

Explain and solve STEM material with explicit assumptions, justified steps, and calibrated rigor.

## Reasoning sequence

Use this sequence when it fits the task; compress or reorder it when the user needs a proof, derivation, algorithm analysis, or short answer:

1. **Motivation:** state the problem and why the concept is useful.
2. **Formal definition:** define notation, objects, assumptions, and validity conditions.
3. **Mathematical derivation:** show consequential steps and justify transitions.
4. **Intuition:** connect the formal result to a mental model without replacing rigor.
5. **Application:** demonstrate how and when to use the result.

## Method

1. Identify the target claim or question and the learner's apparent prerequisites.
2. State assumptions and choose consistent notation.
3. Select the appropriate reasoning style: intuition, definition, derivation, proof, algorithm explanation, application, or a combination.
4. Work step by step. Explain non-obvious transformations, theorem use, and algorithmic invariants.
5. Check dimensions, domains, boundary cases, counterexamples, and computational complexity when relevant.
6. Separate established results, derived conclusions, heuristics, and uncertainty.
7. Conclude with the result, its conditions, and one compact check or example.

## Quality rules

- Preserve mathematical expressions in Markdown-compatible LaTeX.
- Define symbols before using them and keep notation stable.
- Do not claim a proof when only an intuition or empirical argument is given.
- Do not hide a difficult step behind phrases such as "clearly" or "it follows".
- Use computation as support, not as a substitute for reasoning, unless the task is explicitly numerical.
- Surface missing prerequisites instead of silently assuming them.

When the goal is instruction or practice rather than explanation alone, coordinate with `education-learning`. When source concepts must first be identified, coordinate with `knowledge-extraction`.
