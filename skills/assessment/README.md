# Assessment

## Design rationale

This skill adapts assessment-validity, rubric, formative-feedback, and gap-analysis patterns from [Education Agent Skills](https://github.com/GarethManning/education-agent-skills). It consolidates them into one minimal evaluator for answers, homework solutions, and demonstrated understanding, while delegating interactive teaching to `education-learning`. No source code or text is copied.

## Input and output

- **Input:** a task, learner response, learning target, and optional rubric or reference evidence.
- **Output:** an evidence-based judgment, categorized errors, justified score when possible, corrective feedback, and a next check.
