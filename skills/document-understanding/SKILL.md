---
name: document-understanding
description: Transform academic PDFs, PPT/PPTX files, DOCX files, images, screenshots, notebooks, and code files into faithful structured Markdown. Use when Codex needs to extract semantic content, recover document structure, preserve equations and code, identify figures or tables, or prepare learning material for downstream knowledge extraction. Do not use for PDF editing or document redesign.
---

# Document Understanding

Transform raw academic material into a structured representation without changing its meaning.

## Process

1. Inspect the source with tools appropriate to its format. Process all relevant pages, slides, cells, or files unless the user limits the scope.
2. Recover the logical structure: title, sections, headings, lists, examples, exercises, code, and other meaningful blocks.
3. Extract text faithfully. Preserve technical terms, symbols, variable names, and source order when order carries meaning.
4. Preserve equations in Markdown-compatible LaTeX. Do not silently simplify or repair an equation; record suspected extraction errors under uncertainties.
5. Identify figures and tables when possible. Capture captions, labels, headers, and their relationship to nearby text. Describe visual evidence only when it is legible.
6. Produce structured Markdown and distinguish source content from interpretation.
7. Review the result for omissions, broken structure, corrupted symbols, and unsupported reconstruction.

## Format-specific guidance

- For slides, retain slide boundaries when they clarify sequence or context.
- For notebooks, preserve Markdown cells, code cells, outputs, and execution relationships when observable.
- For code files, preserve code exactly in fenced blocks and summarize structure separately.
- For images and screenshots, transcribe only visible content and mark unreadable regions.
- For PDFs and documents, focus on semantic understanding rather than editing, layout recreation, or visual redesign.

## Output

Use the repository's Markdown artifact conventions when saving an artifact. Include, as applicable:

- source identification and processed scope
- hierarchical content
- equations and code
- figures and tables with source locators
- uncertainties, unreadable regions, and extraction limitations

Use page, slide, section, cell, or line locators when available. Never invent missing text, equations, citations, or visual details.
