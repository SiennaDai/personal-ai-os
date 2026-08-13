# Course Learning Workflow v0.1

## 1. Purpose

The Course Learning Workflow transforms course materials into
understandable, applicable, and reusable knowledge.

Target domains:

-   Industrial Engineering and Operations Research (IEOR)
-   Mathematics
-   Computer Science
-   Artificial Intelligence
-   Machine Learning
-   Engineering

This workflow is designed for STEM-oriented learning.

------------------------------------------------------------------------

## 2. Workflow Mode

The workflow uses a hybrid mode:

-   Automatic mode selection by default
-   User-controlled mode switching when needed

Available modes:

### Mastery Mode

Purpose:

Build deep understanding.

Outputs:

-   Concept explanations
-   Intuition
-   Mathematical derivations
-   Applications

------------------------------------------------------------------------

### Exam Mode

Purpose:

Optimize exam preparation.

Outputs:

-   Key points
-   Common question types
-   Practice problems
-   Error analysis

------------------------------------------------------------------------

### Research Mode

Purpose:

Explore a topic beyond course requirements.

Outputs:

-   Theoretical background
-   Related research
-   Limitations
-   Open questions

------------------------------------------------------------------------

## 3. Input

The workflow accepts general learning materials.

Input category:

Learning Material

Examples:

-   Slides
-   Handouts
-   Textbook chapters
-   Research papers
-   Homework
-   Problem sets
-   Past exams
-   Screenshots
-   Handwritten notes
-   Code and notebooks

The workflow focuses on understanding and processing materials rather
than restricting file formats.

------------------------------------------------------------------------

## 4. Workflow Pipeline

## Stage 1: Material Understanding

Goal:

Understand what the material contains.

Outputs:

-   Topic identification
-   Learning objectives
-   Structure extraction
-   Required background knowledge

------------------------------------------------------------------------

## Stage 2: Knowledge Construction

Goal:

Transform raw materials into structured knowledge.

Default output:

-   Structured summary
-   Key concepts
-   Important definitions

Optional outputs:

-   Concept maps
-   Formula maps
-   Dependency graphs

These are generated when requested or when complexity justifies them.

------------------------------------------------------------------------

## Stage 3: Learning Mode Routing

The workflow selects:

-   Mastery Mode
-   Exam Mode
-   Research Mode

based on user intention and context.

Users can explicitly override the mode.

------------------------------------------------------------------------

## Stage 4: Interaction and Practice

Supported interactions:

### Explanation

Provide conceptual explanations, intuition, derivations, and examples.

### Problem Solving

Adaptive strategy:

-   Direct solution when requested
-   Guided reasoning when learning is preferred

### Socratic Learning

Guide users through questions and feedback instead of immediately
providing answers.

------------------------------------------------------------------------

## Stage 5: Knowledge Artifact Export

All long-term artifacts use Markdown as the canonical format.

Artifact categories:

### Course Artifacts

Stored within the related project.

Examples:

-   Lecture notes
-   Homework analysis
-   Exam review

### Knowledge Artifacts

Long-term reusable knowledge.

Examples:

-   Concept notes
-   Method notes
-   Theory notes

Only explicitly identified knowledge artifacts should enter the
long-term knowledge base.

------------------------------------------------------------------------

## 6. Output Language Convention

Default language:

English.

Rules:

-   Keep technical terminology in English.
-   Provide Chinese explanations for difficult concepts when first
    introduced.
-   Use standard international mathematical notation.

Example:

Convexity（凸性）describes a property of functions or sets that...

Later references:

Convexity

------------------------------------------------------------------------

## 7. Required Skills

Core Skills:

-   `document-understanding`
-   `knowledge-extraction`
-   `stem-reasoning`
-   `education-learning`

Context-dependent Skills:

-   `knowledge-mapping`
-   `assessment`
-   `visualization`

------------------------------------------------------------------------

## 8. Integration Principles

### Obsidian

Role:

Long-term knowledge management.

Only knowledge artifacts should be exported.

------------------------------------------------------------------------

### Zotero

Role:

Bibliographic source of truth.

Responsible for:

-   Papers
-   Metadata
-   Citations
-   PDF library

------------------------------------------------------------------------

### Git

Role:

Version control for AI-OS workflows and configurations.

------------------------------------------------------------------------

## 9. Design Principles

-   Workflow and Skill separation
-   Project context isolation
-   Markdown-first artifacts
-   Modular capability reuse
-   Incremental development
