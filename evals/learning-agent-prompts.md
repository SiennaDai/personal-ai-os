# Learning Agent Architecture Checks

## Mode routing

- `Have the Learning Agent teach me why convexity matters in optimization.` Expected: Mastery Mode behavior without requiring a mode label.
- `Use Exam Mode to quiz me on KKT conditions.` Expected: explicit override is honored.

## Implicit Skill routing

- With a small external optimization note: `Have the Learning Agent analyze this note and explain the key derivation. Choose Skills automatically.` Expected: document understanding and STEM reasoning are relevant; assessment, mapping, and visualization are not used without need.

## Project isolation

- Expected: input and output remain in the external Project; nothing is copied into `personal-ai-os`; no unrelated writable root is added.

## Artifact classification

- `Create a study summary for this Project.` Expected: Markdown-first Project Artifact, not a Knowledge Artifact or automatic Obsidian publication.

## Language convention

- Expected: English-first output with a concise Chinese annotation on the first occurrence of a difficult technical term, such as `Convexity (Chinese: 凸性)`.
