---
name: model-validation
description: Assess whether a mathematical or computational model and its results are fit for a stated use through conceptual, structural, dimensional, numerical, empirical, sensitivity, uncertainty, robustness, and decision checks. Use for validation reports, stress tests, scenario or sensitivity analysis, independent recomputation, calibration-versus-validation review, or model-claim audits. Do not use for general software completion testing or raw data profiling.
---

# Model Validation

Test the model and its claims against the use they must support. Select checks proportionally; no single checklist proves every kind of model valid.

## Establish the validation contract

Inventory:

- the model version, specification, implementation, data, parameter set, and reported outputs in scope;
- the intended question, decision, population, environment, time horizon, and loss from being wrong;
- the claims being made and the evidence offered for each claim;
- the calibration data, validation data, benchmarks, tolerances, and acceptance criteria;
- unavailable artifacts or conditions that limit what can be verified.

Keep model validity, implementation correctness, input-data quality, and decision usefulness distinct. A failure in one may mimic another.

## Select and perform relevant checks

### Conceptual validity

Check whether the system boundary, mechanisms, entities, time scale, causal direction, objectives, and exclusions match the real question. Identify important omitted behavior, unjustified proxies, circular definitions, and assumptions that determine the conclusion.

### Formal and structural validity

Check notation, dimensions, units, signs, domains, equations, constraints, conservation laws, initial or boundary conditions, probability normalization, and logical consistency. Assess feasibility, identifiability, observability, stability, or well-posedness when applicable.

### Numerical and computational validity

Recompute the highest-impact result independently when practical. Use analytical solutions, hand-solvable cases, invariants, limiting cases, alternative formulations, or trusted benchmarks. Inspect solver status, residuals, convergence, tolerances, random seeds, numerical conditioning, discretization, and infeasibility diagnostics. Confirm that the implementation matches the formal specification.

If evidence points to a software defect rather than a model defect, report the distinction and hand root-cause debugging or production-code repair to the Coding Agent.

### Empirical or predictive validity

Keep calibration and validation separate. Evaluate against held-out, out-of-sample, historical, experimental, or otherwise independent evidence when the intended use requires it. Select metrics and baselines that match the decision; inspect residual patterns, error distributions, interval coverage, subgroup behavior, overfitting, leakage, and domain shift rather than relying on one aggregate fit statistic.

### Sensitivity, uncertainty, and robustness

Identify inputs and structural assumptions that could change the conclusion. Use defensible ranges and coherent scenarios from evidence or explicit user choices.

- Vary one factor locally only when interactions are not material.
- Use global or joint variation when nonlinearities, interactions, thresholds, or correlated inputs matter.
- Distinguish parameter uncertainty, measurement uncertainty, structural uncertainty, and scenario uncertainty.
- Record decision reversals, feasibility loss, threshold crossings, and fragile optima.
- Compare plausible alternatives and stress cases without assigning invented probabilities.

Sensitivity shows how outputs respond to inputs; it does not by itself establish how probable those inputs are.

### Decision adequacy

Check whether the model differentiates the available decisions at the required precision and whether conclusions remain useful under material uncertainty. Make risk preferences, trade-offs, constraints, and consequences visible. Do not recommend an action that relies on an unvalidated region of the model.

## Rate the result

Use one of these scoped assessments:

- **Fit for stated use:** material checks passed and remaining limitations do not change the decision.
- **Fit with limitations:** usable only under named assumptions, ranges, or caveats.
- **Not fit for stated use:** a material defect or unsupported claim can change the conclusion.
- **Not verifiable with available evidence:** required artifacts, data, benchmarks, or execution are unavailable.

Never describe a model as universally “validated.” State the precise use, domain, version, and evidence to which the assessment applies.

## Output

Produce a concise Markdown validation record with:

- validation scope and intended use;
- overall scoped assessment;
- model, implementation, data, and claim inventory;
- checks performed, evidence, result, and what each check proves;
- issues ordered by decision impact;
- sensitivity, uncertainty, robustness, and decision-reversal findings;
- unverified surfaces, accepted limitations, and domain-of-validity boundaries;
- required repairs, evidence, or next validation actions.

Classify the result as a Project Artifact unless the user explicitly selects a stable reusable validation method as a Knowledge Artifact candidate.

## Quality rules

- Use fresh results from the current model state for completion claims.
- Do not treat solver convergence, plausible output, good in-sample fit, or a passing code test as sufficient model validation.
- Do not use calibration data as independent validation evidence.
- Do not infer “no effect” from a non-significant result without precision or power evidence.
- Do not hide failed checks, unstable results, excluded cases, or out-of-domain use.
- Separate observed evidence, assumptions, inference, and unknowns.
- Prefer a qualified limitation over a fabricated benchmark or scenario probability.

## Coordination

Use `model-formulation` when a defect requires reformulating the model. Use `stem-reasoning` for formal derivations and independent mathematical checks. Use `visualization` only when a sensitivity surface, Pareto front, residual pattern, uncertainty interval, or scenario comparison is materially clearer visually. Route raw-data quality work, literature evidence, production software verification, and publication writing to their owning Agent or capability.
