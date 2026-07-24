# Visual tools — UI/UX mockups, prototypes, dashboards

Tools whose output a human looks at. Reliability comes from one thing: **closing the loop —
the agent must see what it made.** A visual tool that only emits files is half a tool.

## Archetype shapes

| Shape | Output | Engine |
|---|---|---|
| HTML prototype generator | self-contained `.html` (inline CSS/JS, CDN imports only) | template + tokens, no build step |
| Mockup/image generator | PNG/WebP via an image model | cli-tool contract + this file |
| Dashboard/report builder | self-contained `.html` fed by data | template + a small data-prep script |

Self-contained means: one file, opens from disk, no localStorage (in-memory state only),
no build step. That keeps iteration instant and the artifact portable/shareable.

## The screenshot-iterate loop (build this in)

1. **Render** — open the HTML in a real browser (Playwright headless script bundled in the
   tool: `scripts/shoot.py <file.html> [--width 390 1440]`) or use the generated image
   directly.
2. **Look** — the agent Reads the screenshot. Never judge layout from the source code.
3. **Compare** — against the spec, a reference image (`--refs`), or the previous iteration.
4. **Fix and re-shoot** — small targeted edits; keep the same file/URL so diffs are visual.
5. **Stop** — when the screenshot matches intent at every target viewport.

Ship the loop as a bundled script so it costs one command, not fresh Playwright code every
session. Default viewports: 390×844 (phone) and 1440×900 (desktop); mobile-first tools can
drop the desktop pass.

## Design-system layer (consistency beats taste)

Generated visual tools carry a token file (`assets/tokens.css` — CSS custom properties for
palette, type scale, spacing on a 4/8px grid, radii, shadows) and the instruction: **style
only via tokens; never invent one-off hex values or magic paddings.** This is what makes a
batch of 5 prototypes look like one product instead of five.

Quality floor to encode in the generated skill's instructions:

- Commit to ONE aesthetic direction per run; no averaging between styles.
- Real content over lorem ipsum — realistic names, numbers, avatars (data-URI or CSS).
- Type scale ≤ 3 sizes per screen + consistent weights; spacing from the grid only.
- Motion: transform/opacity only, entrances < 300ms, respect `prefers-reduced-motion`.
- Name anti-patterns explicitly in the skill ("no generic purple-gradient hero", etc.) —
  agents repeat defaults unless told the default is the anti-pattern.

## Variant batches (the UI-exploration workflow)

Exploration wants N distinct options, not one. Build visual tools batch-first: accept a
list of variant specs (name + concept line + what differs), emit one artifact per variant
plus an `index.html` contact sheet linking/embedding all of them, then screenshot the
contact sheet for one-glance comparison. Converge: pick a winner, iterate on it alone.

## Anchor consistency (for image-model tools)

For sets that must look cohesive: generate one anchor image, have the human pick, then pass
it as a reference to every subsequent generation so palette/lighting/style carry. Same idea
as tokens, enforced by the model instead of CSS.
