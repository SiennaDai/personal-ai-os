# Document Understanding

## Design rationale

This skill is implemented as a format-aware semantic extraction procedure rather than a PDF editor. Existing document tools can expose text and visuals, but the reusable capability defined here is faithful academic structure recovery across formats.

No external skill code is copied and no runtime dependency is added.

## Input and output

- **Input:** PDF, PPT/PPTX, DOCX, image, screenshot, notebook, or code material, plus an optional scope.
- **Output:** structured Markdown that preserves source hierarchy, equations, code, figures, tables, provenance, and uncertainties where available.
