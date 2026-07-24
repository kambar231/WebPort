---
name: __TOOL_NAME__
description: "TODO — what it produces (mockups / prototypes / dashboards) + 'Use whenever the user…' with exact phrases like 'mock up', 'prototype', 'show me options for' + 'Do NOT use for…' (e.g. production code, image generation via a model). 100–200 words, third person."
---

# __TOOL_NAME__

TODO: one-line premise. Output: self-contained HTML — one file, inline CSS/JS, CDN imports
only, in-memory state (no localStorage), opens from disk.

## Design system

Style ONLY via the tokens in `assets/tokens.css` (palette, type scale, 4/8px spacing grid,
radii, shadows) — one-off hex values and magic paddings are what make a set look like five
different products. Commit to one aesthetic direction per run. Real content, never lorem
ipsum. Type: ≤3 sizes per screen. Motion: transform/opacity only, entrances under 300ms,
respect `prefers-reduced-motion`.

TODO: name this tool's specific anti-patterns ("no generic purple-gradient hero", …).

## Workflow

1. Build the variant(s) from `assets/template.html` + tokens. For exploration, batch-first:
   N distinct variants + an `index.html` contact sheet embedding all of them.
2. **Screenshot** — `python3 scripts/shoot.py <file.html>` (390×844 + 1440×900 by default).
3. **Look at the screenshots** (Read them) — never judge layout from source code.
4. Compare against the spec / reference image / previous iteration; make targeted edits;
   re-shoot the same file so the diff is visual.
5. Stop when every target viewport matches intent. Then the human picks; iterate on the
   winner alone.

## Operational notes for the agent

- Keep each artifact one self-contained file — that's what makes iteration instant and the
  result shareable.
- shoot.py prints one JSON object on stdout with the screenshot paths; parse it.
