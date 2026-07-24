---
name: webgen
description: Build quality static websites by driving a local CLI that scaffolds token-driven sites, screenshots them at multiple widths, and gates them through static + runtime quality checks. Use when you need to actually PRODUCE a website — build, create, clone, or recreate a landing page, marketing site, portfolio, or product page; rebuild a page in the style of a reference URL; or verify/screenshot/fix an existing static site. This is the tool to call when the user wants a website made (for the images ON the site, pair with the imagegen skill).
---

# webgen

A single CLI that turns you into a disciplined website builder. You call it from the
shell, read **one JSON object from stdout**, and act on it. Progress streams to
**stderr**. Exit code 0 on full success, 1 if anything failed.

**Engine:** `python3 /home/claude/WebPort/webgen.py`

## When to invoke

- "Build / create / make me a website / landing page / marketing site / portfolio."
- "Recreate / clone this site" (you have a reference URL — start with `capture`).
- "Screenshot my site / does it look right on mobile?" → `shot`.
- "Check / audit this static site" → `check`.

## When NOT to invoke

- The user wants a React/Next.js **app** with server logic — scaffold that with the
  framework's own tooling (you can still use `shot` and `check` on its built output).
- The user only wants copy or a design critique authored, no files produced.
- The user wants images generated — that's the **`imagegen`** skill. Common pairing:
  build the page here with placeholder blocks, then fill `assets/` via imagegen
  with `--out <site>/assets`.

## The build loop (this is the method — follow it)

webgen enforces a workflow that produces quality sites. Do the steps in order;
skipping ahead is how sites end up inconsistent.

1. **`capture` the reference** (if one exists) — get its section list, palette,
   fonts, and a full-page reference screenshot to compare against later.
2. **`init` the project** — scaffolds `index.html` with placeholder sections,
   `css/tokens.css`, `css/styles.css`, `js/main.js`, and a `webgen.json` manifest.
3. **Define tokens FIRST.** Edit `css/tokens.css` before writing any section.
   Colors, two font roles, a type scale, spacing. Every section must use
   `var(--…)` — `check` warns when it finds hardcoded hex colors elsewhere.
   This is the anchor workflow: tokens are to a site what an anchor image is to
   an image series.
4. **Build section by section, top to bottom.** Replace one `<!-- TODO section: … -->`
   placeholder at a time. Leftover TODO placeholders are `check` **errors**, so the
   manifest of what's unfinished is always visible.
5. **`shot` after every 1–2 sections** and actually READ the screenshots at both
   widths. Compare against the reference screenshot. Fix what looks wrong before
   moving on — do not build eight sections blind and screenshot once at the end.
6. **`check` before declaring done.** It must exit 0. Then take a final full-page
   `shot` at `1440,768,390` and look at all three.

## How to call it

```
python3 /home/claude/WebPort/webgen.py init <dir> --name "Acme" --desc "…" [--sections nav,hero,footer]
python3 /home/claude/WebPort/webgen.py capture <url> [--out spec.json]
python3 /home/claude/WebPort/webgen.py shot <dir|file|url> [--widths 1440,390] [--out dir] [--wait ms]
python3 /home/claude/WebPort/webgen.py check <dir> [--widths 1440,390] [--static-only]
python3 /home/claude/WebPort/webgen.py serve <dir> [--port N]
```

stdout is ALWAYS one JSON object — parse it and check `ok`. `shot`/`check`/`capture`
serve directories on a local ephemeral port automatically; you never need `serve`
for the loop (it exists for a human who wants to look around).

`shot` result:
```json
{"ok": true, "title": "Acme", "shots": [{"width": 1440, "path": "/abs/…/shot_…_1440w.png"},
 {"width": 390, "path": "/abs/…/shot_…_390w.png"}],
 "console_errors": [], "failed_requests": [], "horizontal_overflow_px": {}, "errors": []}
```

`shots[*].path` are **absolute paths — Read them**. A screenshot you did not look
at might as well not exist. `ok:false` here means console errors or failed
requests — fix those before styling anything.

## What `check` gates (exit 0 = shippable)

**Static:** leftover `<!-- TODO -->` placeholders, missing viewport meta / title /
img alt (errors); missing meta description, `href="#"` placeholder links,
hardcoded hex colors outside `tokens.css` (warnings).
**Runtime (headless Chromium):** console errors, failed asset requests, and
**horizontal overflow** at each width — the classic broken-mobile symptom — all
errors.

Warnings don't fail the run but fix them anyway unless the user said otherwise.

## `capture` — reference-site spec

```
python3 /home/claude/WebPort/webgen.py capture https://example.com
```

Returns a spec JSON plus a full-page **reference screenshot**. The spec carries
everything the fidelity contract below needs: top-to-bottom section outline with
headings and heights, dominant palette with usage counts, font families +
`@font-face` rules + font `<link>` URLs, heading sizes, content width, a
**motion table** (every element with a real transition/animation: property,
duration, easing, iteration count), extracted **`@keyframes`** rules, and
probed **hover states** (before/after style diffs on buttons and nav links).
Capture also performs a full scroll pass first, so scroll-triggered reveals are
in their fired state. Use the spec to fill `tokens.css` and choose `--sections`
for `init`; keep the reference screenshot open in the loop for side-by-side
comparison.

## Cloning a reference 1:1 — the fidelity contract

When the task is "recreate/clone this site", **1:1 is the standard, not the
aspiration**. Match, exactly:

- **Fonts** — the same families, loaded from the spec's `font_links` /
  `font_faces`. Same sizes, weights, letter-spacing, line-height per element
  role. Do not substitute a "similar" font silently.
- **Layout** — same section order, same content max-width, same column
  structure, same spacing rhythm, same breakpoints behavior. Verify by placing
  your `shot` next to the reference screenshot at the same width; differences
  you can see are bugs.
- **Color** — sampled values from the spec's palette, not approximations.
- **Motion** — every entry in the spec's `motion` table reproduced with its
  duration and easing; `keyframes` rules ported; `hover_states` diffs
  reimplemented so buttons and links respond identically. Scroll-reveal
  behavior rebuilt to fire the same way.
- **Interactive states** — hover, focus, sticky-nav behavior, carousels/
  accordions: same triggers, same feel.

**Content is the one deliberate exception:** written copy, logos, photography,
and other proprietary assets are NOT copied — use original placeholder text of
identical length/hierarchy and placeholder imagery with identical dimensions,
so the user can drop in their own content without any layout shift.

### The limitation protocol (when you can't match something)

You do not get to quietly downgrade fidelity. If something genuinely cannot be
matched, you must surface it to the user, explain *why*, and ask for what you
need. Only invoke this after actually trying — "capture didn't include it" is
not enough; take extra `shot`s of the reference at scroll positions, probe with
`--wait`, and read the keyframes first. Legitimate examples:

- **Commercial font** you cannot legally load → name the exact font, say so,
  propose the closest freely-licensed match, and ask the user to either accept
  it or provide a licensed font file.
- **Animation you truly cannot observe** — e.g. WebGL/canvas motion, video
  backgrounds, or JS-driven sequences that static screenshots cannot show →
  say precisely which element/section, show what you *did* capture, and ask
  the user to describe the motion (what moves, direction, duration, trigger).
- **Cross-origin stylesheets** the spec flags as unreadable → note which rules
  are invisible and reconstruct from screenshots, flagging the guess.

Report limitations in one batch, each as: *element → what's unmatchable → why →
what you need from the user*. Everything not on that list is expected to be 1:1,
and the final side-by-side screenshots are the proof.

## `film` — observe scroll-driven animation frame by frame

```
python3 /home/claude/WebPort/webgen.py film <dir|url> [--frames 24] [--width 1440] [--wait 350] [--out dir]
```

Scrolls the page top to bottom in equal steps and saves a viewport screenshot at
each position, with the scroll offset in every filename. This is how you observe
what `capture`'s static spec can't show: pinned/sticky sequences, parallax,
elements that move with scroll. Read the frames in order like a flipbook; the
delta between consecutive frames IS the animation. Use it both on the reference
site (what should the motion be?) and on your build (is my motion right?), and
compare frame pairs at matching scroll fractions.

## Flags

| flag | verb | values |
|------|------|--------|
| `--name`, `--desc` | init | site title + meta description |
| `--sections` | init | comma list; default `nav,hero,logos,features,metrics,how-it-works,cta,footer` |
| `--force` | init | re-scaffold over an existing project |
| `--widths` | shot, check | comma list of viewport widths, default `1440,390` |
| `--out` | shot, capture | output dir / spec path |
| `--wait` | shot | extra ms before shooting (animations, fonts) |
| `--viewport-only` | shot | crop to viewport instead of full page |
| `--static-only` | check | skip the headless-browser pass |
| `--port` | serve | fixed port (default: random free) |

## Recipes

**Recreate a reference site:**
```
python3 /home/claude/WebPort/webgen.py capture https://target.example --out spec.json
python3 /home/claude/WebPort/webgen.py init ./site --name "Acme" --sections nav,hero,logos,features,metrics,how-it-works,cta,footer
# edit css/tokens.css from spec.json palette/fonts, build sections one at a time…
python3 /home/claude/WebPort/webgen.py shot ./site            # …reading the PNGs each round
python3 /home/claude/WebPort/webgen.py check ./site           # must exit 0
```

**Fill the site's images with imagegen (companion skill):**
```
python3 <imagegen path>/imagegen.py batch prompts.jsonl --out ./site/assets
```

**Audit an already-built site:**
```
python3 /home/claude/WebPort/webgen.py check ./site --widths 1440,768,390
python3 /home/claude/WebPort/webgen.py shot ./site --widths 1440,768,390
```

## Quality bar (what "done" means)

- `check` exits 0 at `1440,768,390`.
- You have READ the final screenshots at all three widths and they match the
  reference's structure and polish: consistent spacing rhythm, one accent color
  used sparingly, real hover states, no orphan placeholder text.
- Every image has meaningful `alt`; the page works with JS disabled (JS is
  enhancement only).
- All colors/sizes flow from `tokens.css` — changing the accent token recolors
  the whole site.

## Operational notes for the agent

- **Always parse stdout as JSON**; progress and human chatter are on stderr.
  Check `ok`; failure detail is in `errors[*]` / `issues[*]`.
- **Read the screenshots.** The `shot` verb exists so you can see your work;
  paths in `shots[*].path` are absolute — pass them to your Read tool verbatim.
- **Tokens before sections, sections before polish.** Never write a raw hex
  color outside `tokens.css`.
- **Iterate in small bites** — shot after every section or two; a full-page
  screenshot is cheap and a rebuilt section is not.
- **`check` is the definition of done**, not your memory of what you wrote.
- Setup and repo layout live in `README.md`; `AGENTS.md` points here.
