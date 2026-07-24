# Avoiding the AI-generated look

Audit every build against these before shipping. The telltales cluster into five groups;
each has a cheap antidote.

## Typography
- **Tell:** Inter/system sans everywhere, one weight, no typographic opinion.
- **Fix:** a distinctive display face paired with one workhorse (serif display for
  culture/luxury, mono for dev tools, grotesque for fashion) — chosen from the
  *reference's* personality, plus deliberate casing/tracking habits used consistently.

## Color
- **Tell:** purple→blue gradient heroes, glassmorphism cards, decorative color with no
  meaning.
- **Fix:** the reference's palette exactly, 3–5 colors, each with a *job* (bg / ink /
  one accent). No gradient unless the reference has one.

## Layout
- **Tell:** perfectly uniform card grids — identical heights, identical 16px radius,
  identical padding; oversized hero + three feature cards + CTA, centered everything.
- **Fix:** editorial irregularity on purpose: stagger alternate cards, vary one aspect
  ratio, sharp corners unless the reference rounds them, one asymmetric detail per
  section. Symmetry only where the reference is symmetric. Caution: "01/02" index
  numbers beside titles have become an AI-design cliché themselves — use only if the
  reference actually has them. Same for accent-colored ornaments (numerals, italic
  phrases): default them to faint ink; a lone accent color must earn every use.

## Dark-mode traps
- **Tell:** ember/amber orange as the accent on near-black (THE default AI dark
  palette), glowing particle fields drifting in the background, colored italic hero
  words, orange text highlights on hover.
- **Fix:** dark pages read expensive when the background is FLAT and the photography
  carries all the warmth. Text stays monochrome (hierarchy via size/weight/italic,
  ink vs dim); the accent appears only on interaction (hover, selection, one hairline)
  and leans away from orange — deep red, oxblood, or none.

## Full-bleed image transitions
- **Tell:** a full-bleed photo band dropped between flat sections as a raw rectangle —
  hard edges, no relationship to the background.
- **Fix:** mask the image into the page: `mask-image: linear-gradient(transparent,
  #000 25%, #000 72%, transparent)` so it emerges from the background color (works
  best when the photo's own edges are near the page color). An image should never
  have four visible edges on an editorial page.

## Surface & imagery
- **Tell:** flat, too-clean surfaces; generic stock photos; smooth plastic AI
  illustrations.
- **Fix:** texture — subtle film grain overlay (tiled noise canvas at ~5% alpha,
  `mix-blend-mode:overlay`); procedural or real imagery with irregularity baked in
  (varied seeds, hand-drawn-feeling paths); shadows/highlights implying a light
  direction.

## Copy & motion
- **Tell:** "Your all-in-one platform" vagueness; identical fade-ins on everything;
  buttons that snap; motion with no purpose.
- **Fix:** specific, voiced copy (names, numbers, dates — would a curator/founder
  actually say this?); animation only where it tells the story (entrance, signature
  effect, staggered reveals); everything eased on one curve family; hover states on
  every interactive element.

## The one-question audit
Squint test: could this exact page be about any other company/topic with a logo swap?
If yes, it's slop — add the details only *this* subject could have.
