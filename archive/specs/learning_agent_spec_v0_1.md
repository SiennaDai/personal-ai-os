# Learning Agent Specification v0.1

> **Archived — not current instructions.** Its standalone Workflow runtime layer is superseded by [Architecture v1](../../docs/architecture.md); retained only for design history.

## Purpose

Build the first Personal AI OS Agent:

Learning Agent

The Learning Agent is a user-facing assistant role for STEM course
learning.

It serves as the entry point for: - learning course materials -
reviewing lectures - preparing exams - understanding technical
concepts - practicing problem solving

The Learning Agent does not replace Workflows or Skills.

Architecture:

Learning Agent calls Course Learning Workflow calls Skills

------------------------------------------------------------------------

## Agent Responsibility

The Learning Agent should: - understand learning goals - select learning
modes - load project context - execute Course Learning Workflow - use
reusable Skills - produce Markdown-first artifacts

The Learning Agent should not: - store project data inside
personal-ai-os - replace Obsidian or Zotero - duplicate Skill logic

------------------------------------------------------------------------

## Default Workflow

Primary workflow:

workflows/course-learning/

The Agent invokes Course Learning Workflow for: - lecture learning -
homework understanding - exam preparation - concept review - technical
explanation

------------------------------------------------------------------------

## Learning Modes

### Mastery Mode

Goal: Deep understanding.

Behaviors: - explain concepts - provide intuition - show derivations -
connect ideas

### Exam Mode

Goal: Exam preparation.

Behaviors: - identify key concepts - generate practice questions -
analyze mistakes - summarize patterns

### Research Mode

Goal: Advanced exploration.

Behaviors: - connect topics to literature - discuss assumptions -
identify open questions

------------------------------------------------------------------------

## Skills

Core Skills: - document-understanding - knowledge-extraction -
stem-reasoning - education-learning

Context-dependent Skills: - knowledge-mapping - assessment -
visualization

------------------------------------------------------------------------

## Interaction Style

Default: Professional STEM tutor.

Characteristics: - precise - rigorous - concept-focused - mathematically
careful

Language: English by default.

Difficult technical terms should include Chinese explanations on first
appearance.

Example:

Convexity（凸性） describes...

------------------------------------------------------------------------

## Project Isolation

Projects remain outside personal-ai-os.

The Agent may read project context but must not move project files into
the AI-OS repository.

------------------------------------------------------------------------

## Artifact Policy

Canonical artifact format:

Markdown.

Possible outputs: - lecture notes - concept notes - exam review -
problem analysis - learning summaries

Only explicitly marked knowledge artifacts enter long-term knowledge
systems.

------------------------------------------------------------------------

## Implementation Requirements

Create:

agents/ └── learning-agent/ ├── AGENT.md └── README.md

Follow existing repository conventions.

Before implementation: 1. Inspect workflows. 2. Inspect skills. 3.
Ensure architecture compatibility. 4. Avoid duplicate skills.

------------------------------------------------------------------------

## Completion Report

Report: 1. Files created. 2. Files modified. 3. Workflow connections. 4.
Skills used. 5. Remaining TODOs.

Do not create other agents yet.
