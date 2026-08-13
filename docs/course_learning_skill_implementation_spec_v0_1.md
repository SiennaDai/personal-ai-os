# Course Learning Workflow Skill Implementation Specification v0.1

> Historical specification. Its pre-v1 architecture constraints are superseded by [Architecture v1](architecture.md); retained for Skill design history.

## Context

This document is the implementation requirement for Codex.

The repository is:

`personal-ai-os`

The `skills/` directory is the AI capability layer of the personal AI
workspace.

The goal is to implement reusable Skills that can support the Course
Learning Workflow and later workflows.

Do not create a separate skill repository.

All skills belong inside:

    personal-ai-os/skills/

------------------------------------------------------------------------

# Skill Architecture Principle

Follow this hierarchy:

    Workflow
        |
        calls
        |
    Skills

A Skill is:

-   reusable across workflows
-   capability-oriented
-   independent from project-specific context

Do not create an Agent layer.

------------------------------------------------------------------------

# Required Skills

## 1. Document Understanding Skill

Directory:

    skills/document-understanding/

Purpose:

Transform raw learning materials into structured representations.

Supported inputs:

-   PDF
-   PPT/PPTX
-   DOCX
-   images
-   screenshots
-   notebooks
-   code files

Expected capabilities:

-   extract text
-   identify structure
-   preserve equations
-   identify figures/tables when possible
-   produce structured Markdown-compatible output

Important:

Do not build a PDF editor.

The goal is semantic understanding of academic materials.

Decision:

Status: - DIY/adapt

Reason:

Existing PDF skills mostly focus on creation/editing/OCR rather than
academic understanding.

------------------------------------------------------------------------

# 2. Knowledge Extraction Skill

Directory:

    skills/knowledge-extraction/

Purpose:

Convert structured materials into reusable knowledge units.

Expected extraction:

-   concepts
-   definitions
-   relationships
-   assumptions
-   examples
-   methods
-   prerequisites

Must support different schemas:

## Lecture mode

Extract:

-   key concepts
-   formulas
-   prerequisites
-   examples
-   exam relevance

## Research mode

Extract:

-   research question
-   method
-   contribution
-   limitation

Decision:

Status: - Adapt existing research-oriented approaches + DIY

Candidate reference:

Academic Research Agent Skill style workflows.

Do not copy blindly because course learning needs different outputs.

------------------------------------------------------------------------

# 3. STEM Reasoning Skill

Directory:

    skills/stem-reasoning/

Purpose:

Provide technical reasoning for STEM domains.

Target domains:

-   mathematics
-   optimization
-   statistics
-   computer science
-   AI
-   machine learning

Expected reasoning styles:

-   intuition
-   formal definition
-   derivation
-   proof
-   algorithm explanation
-   application

Preferred explanation structure:

    Motivation

    ↓

    Formal definition

    ↓

    Mathematical derivation

    ↓

    Intuition

    ↓

    Application

Decision:

Status: - Full DIY

Reason:

This represents personalized reasoning style rather than a generic tool
capability.

------------------------------------------------------------------------

# 4. Education Learning Skill

Directory:

    skills/education-learning/

Purpose:

Provide learning methodology.

Capabilities:

-   Socratic questioning
-   retrieval practice
-   misconception diagnosis
-   feedback loops
-   assessment strategies

Decision:

Status: - Adopt/adapt existing education-agent skill approaches

Candidate reference:

Education Agent Skills style workflows.

Required adaptation:

Must support STEM learning contexts.

It should work together with:

-   STEM Reasoning Skill
-   Knowledge Extraction Skill

------------------------------------------------------------------------

# Workflow Usage

Course Learning Workflow uses:

## Always required:

-   document-understanding
-   knowledge-extraction
-   stem-reasoning
-   education-learning

## Context-dependent:

-   knowledge-mapping
-   assessment
-   visualization

These are optional workflow calls, not unimportant skills.

------------------------------------------------------------------------

# Future Skills

The following may be added later:

## Knowledge Mapping Skill

Purpose:

Generate:

-   concept maps
-   dependency graphs
-   knowledge relationships

Status:

DIY later.

------------------------------------------------------------------------

## Assessment Skill

Purpose:

Evaluate:

-   homework solutions
-   answers
-   understanding

Status:

May be integrated into education-learning first.

------------------------------------------------------------------------

# Skills Not Needed

Do not create:

## Artifact Management Skill

Reason:

Markdown formatting and metadata conventions belong to:

    docs/artifact-conventions.md

not a Skill.

------------------------------------------------------------------------

# Implementation Requirements

For each Skill:

Create:

    skill-name/

    ├── SKILL.md
    ├── README.md
    └── supporting files if necessary

Before implementation:

1.  Check whether a mature existing skill can be reused.
2.  If adopting existing work, document:
    -   source
    -   purpose
    -   modifications
3.  If building from scratch, document:
    -   design rationale
    -   input/output expectations

Do not over-engineer.

Implement only the minimum reusable capability required by the
specification.

------------------------------------------------------------------------

# Current Task

Implement the initial Skill layer for the Course Learning Workflow.

After completion, report:

1.  Skills created
2.  Existing skills reused/adapted
3.  Files changed
4.  Design decisions
5.  Remaining TODOs

Do not implement future workflows yet.
