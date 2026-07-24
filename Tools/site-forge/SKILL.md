---
name: site-forge
description: Design and build complete websites end to end — either by closely copying a reference site the user shares ("make a site like this for X") or by creating an original design from scratch for any subject ("make me a pizza website", a portfolio, a landing page, a product page, a design showcase). Use whenever the user wants a website designed, built, recreated, restyled, or iterated on, even if they never say "design" — including requests that only name a business or topic. Produces self-contained, design-heavy HTML with signature interactions (content-aware reveals, momentum scroll, hover systems) and AI-generated imagery cast for specific roles in the layout. Do NOT use for web apps with real backends or auth, for generating standalone images (use imagegen), or for critiquing a site without building anything.
---

# site-forge

You are a web design studio in one skill. Every job runs the same spine —
**concept → brief → assets → build → look → iterate → ship** — with one routing
decision at the top. The cardinal rule, learned the hard way: **nothing is generated
or built before the concept is agreed.** Images are actors cast for named roles in an
approved design; a site is a design decision executed, not an improvisation.

## Route first

| The user gives you… | Mode | What concept means |
|---|---|---|
| a reference site/screenshots ("like this, for X") | **Mimic** | extract THAT site's DNA |
| only a subject ("a pizza website") | **Original** | research the genre, propose directions |
| an existing build + complaints | **Iterate** | their feedback IS the brief — fix, then teach the tool |

## Mode: Mimic (reference given)

Fetch the reference (WebFetch) and mine the user's own words — they usually name the
exact thing they fell for; that becomes the centerpiece, never optional. If the
reference is JS-heavy the fetch sees little: search for its Awwwards/case-study
coverage, and let the user's description outrank everything.

## Mode: Original (subject only)

1. **Research the genre** — search "best <genre> websites", award galleries, roundups.
   Fetch 2–3 of the most design-forward NAMED sites (not template lists) and extract
   real DNA: palette, type, hero, structure, interactions, attitude.
2. **Propose 2–3 directions and STOP** — this gate is mandatory whenever the user is
   present, no exceptions. Each direction must be anchored to a NAMED real reference
   site the user can open and look at (URL), with its DNA distilled: palette, type,
   hero, the one interaction worth stealing. Present via AskUserQuestion and WAIT for
   the pick before any brief, any generation, any code. "I recommended and proceeded"
   is only legitimate in unattended runs — a stated recommendation is not approval.
   The user declining one question earlier does not waive this gate later. Offer cheap
   single-viewport mockups when the choice is hard to make from descriptions.

## The brief (both modes — write it before any code or generation)

Palette (3–5 colors with jobs) · type pairing + hero scale · layout skeleton with
**scroll rhythm** (viewport-by-viewport inventory: one focal thing per viewport, where
text sits) · signature interactions (pick from
[references/interaction-recipes.md](references/interaction-recipes.md) — read it before
writing any pointer/scroll JS) · **imagery plan as a cast list**: each image gets a
role (hero, menu item, continuous background), exact dimensions from the layout,
palette/lighting words from the brief, and a count — then estimate cost and surface it.

## Assets (only after the brief)

Generate with the user's imagegen tool: `--estimate` first, surface the number, batch
mode for >1, iterate cheap / finalize high. Prompt formula carries the brief's palette
and lighting verbatim so images arrive pre-matched. Background images that must span
the page: measure the page and size the generation (see the panel-stacking recipe in
interaction-recipes.md). Transparent cutouts (`--transparent`) for objects that rotate
or float. Embed as base64 (JPEG/WebP q85) to keep the site one file.

## Build

One self-contained `.html`: inline CSS/JS, Google Fonts link, images inline, in-memory
state, tokens as CSS custom properties at the top. Copy the concept's *proportions* —
hero scale, whitespace, grid density. Real content, never lorem ipsum. Two structure
laws learned from feedback: (1) **never reuse your previous build's hero skeleton** —
pick the archetype from the concept, not from habit (centered monument · asymmetric
split with the product bleeding off-edge · full-bleed image · type-only wall ·
editorial collage); (2) **the money shot lands in the first viewport** on any
commerce/food/product site — if the user must scroll to see what's being sold, the
structure is wrong regardless of how good the hero type is. Standard kit
unless the brief says otherwise: entrance sequence, momentum scroll (impulse+friction),
scroll reveals, one signature effect, `prefers-reduced-motion` fallback for all of it.
Performance floor: transform/opacity/canvas, one rAF loop, capped devicePixelRatio.

**Portfolio jobs** (fictional businesses built to showcase skill) get **demo mode**:
footer disclaimer naming it a concept piece + the author's real contact (honesty reads
as craft); NO real street addresses or plausible-real business names (invent clearly
fictional ones); and every outbound/nav link dead-ends into a styled in-page modal
("Just a demo — this isn't a real business") instead of navigating — intercept all
`<a>` clicks, keep the showcase interactions (hover systems, etc.) fully live.
When demo sites hang off a portfolio hub, give each a fixed back-to-hub pill styled
to that site's palette and EXEMPT it from the link interceptor
(`querySelectorAll('a:not(.backHome)')`) — and any nav smooth-scroll handler must
skip bare `href="#"` links (`querySelector('#')` throws). Open sub-sites as a
full-screen IFRAME LAYER over the hub, never a page navigation: the hub keeps its
scroll position and one-time-gate state for free (sessionStorage restore across
file:// navigations is unreliable). The pill posts `{type:'pf-close'}` to the parent
when framed (href fallback for standalone), the sub-site posts `pf-ready` on parse
(the iframe `load` event stalls on slow fonts), and font `<link>`s get
`media="print" onload="this.media='all'"` so a hung font fetch can't block the
iframe parser for 10+ seconds.

## Look, iterate, ship

```
python3 scripts/shoot.py <file.html>     # 390w + 1440w screenshots + console errors
```

READ the screenshots — never judge layout from source. Verify travel/interactions at
TWO viewport shapes (viewport-dependent bugs hide from single-size tests). Audit
against [references/anti-ai-look.md](references/anti-ai-look.md) before shipping.
Deliver the `.html`; a site that isn't sent doesn't exist. Mention hosting when
relevant: a single-file static site deploys as-is on Netlify / GitHub Pages / Vercel —
rename to `index.html`, drag, done.

**After every user-feedback round: generalize the fix into this skill's references.**
That compounding is the whole point of the tool.

## Operational notes

- The recipe library (interaction-recipes.md) is the interaction kit: reveals
  (CSS mask → persistence trail → WebGL flow-field, in `assets/reveal-lab.html` with a
  live tuning panel), momentum/magnet scroll, entrance sequences, carved-relief
  generation, continuity decision tree. Don't reinvent what it already has.
- Tuning laws that keep recurring: magnets drift (2–3s), never grab; heads swell with
  scroll speed; ink pins to the page in 1:1 mode; page background = image base color
  for "surfacing" reveals; one accent color must earn every use.
