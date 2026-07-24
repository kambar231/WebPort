# Interaction recipes — the signature-effect library

Copy-adapt these; don't reinvent. Every recipe: transform/opacity/mask only, one rAF loop,
lerped pointer, `prefers-reduced-motion` fallback, and a `?debug=reveal` mode that freezes
the effect visibly for screenshots.

## 1. Mouse-reveal background (spotlight mask)

A full-bleed background image sits under the page, hidden by default; a soft circle
around the cursor reveals it, plus a few slow ambient "breathing" holes elsewhere.
Cheap and GPU-friendly: one extra layer + `mask-image` with multiple radial-gradients.

```html
<div class="reveal-bg" aria-hidden="true"></div> <!-- first child of body -->
<style>
.reveal-bg{position:fixed;inset:0;z-index:0;pointer-events:none;
  background:var(--reveal-image) center/cover fixed;
  -webkit-mask-image:var(--mask);mask-image:var(--mask);}
.content{position:relative;z-index:1;}  /* everything else stacks above */
@media (prefers-reduced-motion: reduce){
  .reveal-bg{mask-image:none;-webkit-mask-image:none;opacity:.12;}}
</style>
<script>
const bg=document.querySelector('.reveal-bg');
let mx=innerWidth/2,my=innerHeight*0.3,x=mx,y=my;
addEventListener('pointermove',e=>{mx=e.clientX;my=e.clientY});
const DEBUG=new URLSearchParams(location.search).has('debug');
// ambient holes: phase-offset sines so they drift + swell independently
const amb=[[.15,.25,180],[.8,.7,220],[.5,.85,150]];
function frame(t){
  x+=(mx-x)*.08; y+=(my-y)*.08;                       // lerp = trailing, organic
  let m=`radial-gradient(circle 240px at ${x}px ${y}px, #000 35%, transparent 75%)`;
  amb.forEach(([ax,ay,r],i)=>{
    const s=DEBUG?1:.55+.45*Math.sin(t/2800+i*2.1);   // breathe 0.1..1
    m+=`,radial-gradient(circle ${r*s}px at ${ax*100}vw ${ay*100}vh, rgba(0,0,0,${DEBUG?.9:.35+.35*s}) 30%, transparent 78%)`;
  });
  bg.style.webkitMaskImage=bg.style.maskImage=m;
  requestAnimationFrame(frame);
}
requestAnimationFrame(frame);
if(DEBUG){x=mx=innerWidth*.5;y=my=innerHeight*.45;}   // frozen state for shoot.py
</script>
```

Tuning: cursor circle 200–280px; `35%/75%` stops control edge softness; mask layers are
*additive* (any layer's opaque area reveals). Keep total layers ≤6.

### 1b. Persistence-trail reveal (the award-site mechanic — Codrops image-trail family)

The convincing reveal is not shapes drawn per frame — it's **paint with a lifetime**.
Pointers *paint* into a persistent buffer; the buffer ages; age is opacity:

- **Energy buffer** = offscreen canvas, same size as viewport. Each frame, two aging
  passes: (1) **DISPERSE** — redraw the buffer onto itself through `filter:blur(~2px)`
  (via a swap canvas + `copy` composite): the paint spreads outward like ink dropped
  in water, edges feathering as they age; (2) **DISSOLVE** — `destination-out` fill at
  ~3–4% alpha: every pixel decays by age, the oldest end of a wake dies first, the
  newest paint last. Blur + decay together = paint-on-water; decay alone = dry eraser.
- **Painting**: each pointer stamps a soft-edged disc (rim lightly noise-eaten so it's
  never geometric) at ~0.5 alpha along the segment travelled this frame (substamp every
  ~12px — never once per frame, or fast moves leave dots). Resting compounds stamps to
  fully solid; sweeping leaves a lighter wake. Solid head → fading tail is ONE
  continuous gradient of time, not two shapes. No halos, no pulsing, no sines.
- **Phantom cursors**: 1–2 more pointers at ~half strength painting into the same
  buffer, with a wander brain (random target, slow lerp ~.05, occasional 1–3s pause
  "to read", then a new target) — reads as someone else browsing the same page.
- **Composite**: energy buffer IS the mask: draw it to the visible canvas, then
  `source-in` + draw the image cover-fit. One rAF loop; 2D canvas is plenty.
- **Light pages change the metaphor.** On a dark bg a reveal reads as a flashlight; on
  a light bg (what the award sites do) it reads as relief emerging from the paper.
  Go all the way: **set the page background to the image's own base color** (mean of
  its brighter half) and pre-mix the revealed image toward that color in the shader
  (`stone = mix(BG, stone, ~0.7)`). Unrevealed and revealed then differ only by the
  carving's shadows — surfacing, never uncovering.
- **Scroll travel**: sample stone AND flow through a scroll-driven window
  (`suv = win.xy + uv*win.zw`; y pans top→bottom of the image across the page's scroll
  range, damped by a lerp). Calibration is what makes it FELT: the window's height must
  be ≤ ~40% of the image (zoom ~42% width on landscape) so it crosses the remaining
  ~60% while scrolling — at 60% width the drift is imperceptible and reads as a static
  background. Verify by revealing at the SAME screen spot at three scroll depths: the
  uncovered carving must clearly differ each time.
  **1:1 mode** (carving glued to the page — background scrolls at exactly content
  speed): track raw scroll pixels and pan the window by `scrollPx · winH/viewportH`;
  since a long page scrolls past more image than exists, set the stone AND flow
  textures to MIRRORED_REPEAT so the frieze reflects and continues seamlessly —
  never CLAMP (smears) or REPEAT (hard seam). Damping ~0.2 keeps it tracking tight.
  **Pin the ink to the page too**: in 1:1 mode the reveals belong to page coordinates,
  not the screen — advect the whole ink buffer by the per-frame scroll delta (add
  `-vec2(0, dScrollPx/viewportH)` to the sim backtrace, using the SAME damped scroll
  signal as the stone window so ink and carving move in lockstep). Reveal something,
  scroll down, and it slides up and away with the content — a reveal at (x, pageY)
  stays at (x, pageY). Two companions this needs: (a) connect each frame's deposit
  capsule to where the previous head NOW sits (`prevY + dScroll`) or fast scrolling
  chops the stroke into offset stamps; (b) **swell the head with scroll speed**
  (`r *= 1 + min(|dScrollPx|/~22, 1)·0.95`) — scrolling is brush motion, and without
  the swell a scroll-stroke reads as a thin streak.
- **Phantom quality bar**: ONE phantom beats several. Move it on eased quadratic-bezier
  arcs (bowed control point, smoothstep progress — never a straight lerp jump), let it
  rest between arcs, and make its strength dynamic: proportional to its speed plus a
  slow breathing sine, lerped so it swells while moving and fades while resting.
- Entrance: one big brushload at centre on load — it simply decays away through the
  same aging, no special-case animation.
- `?debug`: paint one S-stroke with alpha ramped along it (old→faint, new→solid) and
  freeze decay, so the trail gradient shows in a static screenshot.

### 1c. Content-aware WebGL reveal (the flagship — ink that follows the image)

When the reveal should feel guided by what it uncovers (ink runs along a branch toward
the trunk), upgrade 1b to a GPU flow-field sim. Reference implementation with a live
tuning panel: **`assets/reveal-lab.html`** — copy it, swap the background, tune, use
"Copy settings". Architecture (per the Kang edge-tangent-flow + stable-fluids research):

- **Backgrounds with real designs** (figures, friezes, sculpted scenes): procedural
  noise can't draw a figure — generate the relief with the user's imagegen tool
  instead. Prompt formula that keeps luminance usable as a heightfield: "white
  limestone/marble **bas-relief** of [subject], **shallow relief**, **soft raking
  light from upper left**, matte bone-white, **monochrome**, full-frame edge-to-edge,
  no text". Iterate cheap, finalize 4K. The lab accepts any image via drag & drop and
  derives height + flow from its luminance — figures' contours become the ink's roads.
- **Flow field from the image** (precomputed): luminance/height gradient → rotate 90°
  for the edge tangent (flow runs *along* features) → 3 passes of sign-aligned ETF
  smoothing → blend in a fraction of uphill gradient (`climb ≈ 0.3`) so ink migrates
  toward ridge crests. Store direction + edge strength; gate speed by edge strength so
  ink rests on flat ground.
- **Ping-pong sim** (WebGL2, RGBA16F, ~480×300): each frame, semi-Lagrangian backtrace
  `src = uv − v·dt` with `v = imageFlow·speed + strokeGust`, sampled with a small blur
  ring (dispersal), times decay ~0.985–0.99. Deposit = capsule (distance to the
  prev→cur pointer segment, gapless at any speed) whose rim radius **morphs with
  angular harmonics** `r(θ)=R(1+m(.5sin3θ+.33sin5θ+.22sin7θ))` animated over time.
- **Composite**: dual threshold — tight smoothstep for the solid head, wide for the
  dispersing wake — plus a "wet rim" specular from the mask gradient (`dFdx/dFdy`).
- Pitfalls: CLAMP_TO_EDGE + clamp backtrace UVs; needs EXT_color_buffer_float; cap
  devicePixelRatio ~1.5; fall back to recipe 1b (2D canvas) without WebGL2.

## 1d. Momentum scroll + magnetic sections (the reference's Lenis feel)

Native scrolling feels dry next to award sites. Two pieces, ~30 lines, no library:
- **Inertia**: intercept `wheel` (preventDefault) and feed deltas into VELOCITY, not
  position: `vel += delta·k` (impulse), each frame `tgt += vel; vel *= friction(.9)`.
  Choose k = 1−friction so total travel per notch equals the delta — clicky mouse
  wheels then accelerate and glide instead of kicking gear-by-gear (position-jump
  targets still jerk per notch even with output lerp). Then ease the real scroll
  (`cur += (tgt−cur)·.085`, `scrollTo(0,cur)`). Handle `deltaMode===1` (×16). Set
  `scroll-behavior:auto` (smooth-behavior fights the animator), resync on external
  scrolls (keys/hash) when `|scrollY−cur|` jumps, and rewire nav anchors to set the
  target. Skip entirely under `prefers-reduced-motion`.
- **Magnet**: when the wheel has rested ~500ms, find the nearest focal unit (image +
  its title/caption as ONE block — measure the wrapping figure). Reach ~8–9% of the
  viewport, and weight the pull by proximity so it's feather-light at the edge:
  `w = 1−d/reach; tgt += (anchor−tgt)·(.006+.016·w²)`. Tuning law learned the hard
  way: the magnet must read as a drift you notice late (~2–3s to center), never a
  grab — if scrolling slightly past a picture visibly yanks back, it's 3× too strong.

## 2. Continuous background picture (one image through the whole page)

The reveal layer above is `position:fixed` + `background-attachment:fixed`-equivalent, so
every section reveals *the same* image in place — scrolling moves the page over a still
picture. That continuity is the effect; never swap images per section. For non-reveal
sites: `background: url(...) center/cover fixed` on body, sections with transparent gaps.

**One-artwork trick**: when the page shows pictures (exhibition plates, project cards),
make them *detail crops of the same background image* (canvas `drawImage` source rects
framing a face, a bird, a branch). The plates and the reveal then belong to one artwork
— continuity you can feel, and one generation pays for everything.

**Generated backgrounds and page length** — decision tree:
- Fixed layer (default): ONE viewport-sized image (1536×1024 / 4K) covers any page
  length, continuous by construction. Always prefer this; never generate page-height art.
- Background must scroll 1:1: never mirror-tile figurative art (statues flip upside
  down — instantly wrong). Build a purpose-sized tall composite instead: measure the
  page (needed imgH ≈ (viewportH + scrollMax) / (displayW/imgW)), then generate N
  portrait panels (1024×1536) with the SAME style/palette prompt plus the key line
  "at the very top and bottom edges the carving fades smoothly into plain smooth
  uncarved stone" — panels then stack with a ~70px crossfade and the seams are
  invisible because plain stone meets plain stone. Batch-generate (estimate first),
  stitch, and clamp the scroll window instead of wrapping. Size the sampling window
  from the REAL page, not from a hardcoded zoom: `winH = viewportH/(viewportH+scrollMax)`
  then `winW = winH·(vpW/vpH)·(imgH/imgW)` capped at 1 — narrower viewports zoom in
  horizontally instead of running out of image and freezing mid-page (the freeze is
  viewport-dependent, so it hides from tests run at one window size). Slow parallax
  (~0.25–0.3× scroll) remains the cheap fallback when one 9:16 image must stretch.

## 3. Procedural stone/marble texture (self-contained imagery)

When no photo is supplied, generate stone with SVG turbulence — infinite, zero bytes of
image data, tintable via tokens:

```html
<svg width="0" height="0"><filter id="stone">
  <feTurbulence type="fractalNoise" baseFrequency="0.008 0.011" numOctaves="5" seed="7"/>
  <feColorMatrix values="0 0 0 0 0.82  0 0 0 0 0.79  0 0 0 0 0.74  0 0 0 0 1"/>
  <feComponentTransfer><feFuncA type="discrete" tableValues="1"/></feComponentTransfer>
  <feComposite operator="in" in2="SourceGraphic"/>
</filter></svg>
```

Apply to a div (`filter:url(#stone)`) or rasterize once to canvas → dataURL if filters
are heavy. Layer two turbulences (low-freq form + high-freq grain) + a soft vignette
gradient for realism. Vary `seed` per project so no two sites share a texture.

### 3b. Carved bas-relief (when the reference has sculpted/engraved surfaces)

Flat noise reads as "boring stone". Carving = **recessed grooves with directional
light**: stroke each motif path three times — lit lip offset (+2.2,+2.2) in warm light
(`rgba(255,226,186,.4)`), deep shadow offset (−2.2,−2.2) in near-black, then the groove
core at (0,0) in dark brown, widest. Build a small motif library as path functions
(spirals, suns, zigzags, animals, hands, rings — match the site's culture/topic) and
stamp ~20-30 across the base texture at varied scale/rotation/alpha. Add 2-3 giant
faint carved characters (numerals, letters) as section anchors. Same 3-pass trick
works for `ctx.fillText` to carve typography.

### 3d. White sculpted relief (shaded heightfield — for references with 3D bas-relief)

When the reference's background is *sculpted* (ZBrush-style organic relief, not line
engravings), stroke-based carving looks wrong. Build a real heightfield and light it:

1. **Height**: domain-warped fBm at VERY low frequency — a handful of large forms per
   image, not texture (`p → fbm(p + warp·fbm(p + warp·fbm(p)))`, base wavelength ≈ ⅕
   of the canvas). Optional ridge term `1−|2·fbm−1|` for dune crests. Compute at half
   resolution; box-blur the field 2× (carved stone is polished, not gravel).
2. **Sculpt text/symbols**: draw them white on a temp canvas, blur 3px, add the alpha
   into the heightfield as raised plateaus — they become part of the stone.
3. **Shade**: finite-difference normals (slope strength is the sculpt — tune until
   forms pop), one raking directional light from upper-left, `diff = max(0, n·L)`,
   `s = (.56 + .5·diff) · (.86 + .14·height) + pow(diff,14)·.14` clamped to [.5, 1.05],
   times a warm near-white (247,243,233). Upscale smoothly to full size.
4. Calibrate scale by eye via screenshot: crumpled-foil = frequency too high; flat
   gray = slope strength too low. Iterate those two numbers only.

## 3c. Entrance sequence (never open cold)

Award-site grammar: **loader → transition → hero rise**. Minimal version: fixed overlay
with wordmark tracking-in (letter-spacing 1.1em → normal) + a hairline growing + a small
serif detail; at ~1.2s fade the overlay while the reveal bloom (1b) breathes open; hero
lines are `paused` until `body.loaded` starts their staggered rise. Total < 2.5s, and
skip it entirely under `prefers-reduced-motion`.

## 4. Scroll reveal (the default polish pass)

```js
const io=new IntersectionObserver(es=>es.forEach(e=>e.target.classList.toggle('in',e.isIntersecting)),{threshold:.18});
document.querySelectorAll('[data-reveal]').forEach(el=>io.observe(el));
```
```css
[data-reveal]{opacity:0;transform:translateY(28px);transition:opacity .6s var(--ease),transform .6s var(--ease);}
[data-reveal].in{opacity:1;transform:none;}
[data-reveal]:nth-child(2){transition-delay:.08s}  /* stagger siblings */
```
Entrances only reveal once unless the reference clearly re-hides. < 700ms total.

## 5. Oversized hero type, line by line

Reference-studio look: hero words each on their own line, clipped and rising in.

```css
.hero h1{font-size:clamp(3rem,11vw,10rem);line-height:.95;letter-spacing:-.03em;}
.hero .line{display:block;overflow:hidden}
.hero .line>span{display:inline-block;transform:translateY(110%);animation:rise .8s var(--ease) forwards;}
.hero .line:nth-child(2)>span{animation-delay:.1s} /* etc. */
@keyframes rise{to{transform:none}}
```

## 6. Magnetic / trailing cursor accents

Small dot that lerps after the cursor (slower factor, ~.12) and scales up over links —
use only if the reference has it; two cursor effects at once (reveal + magnet) is fine,
three is noise.

## 7. Marquee strip

```css
.marquee{overflow:hidden;white-space:nowrap}
.marquee>div{display:inline-block;animation:mq 22s linear infinite}
@keyframes mq{to{transform:translateX(-50%)}}  /* content duplicated once inside */
```

## 8. Ambient daylight (scroll = time of day)

For day-narrative pages (health, hospitality, routines): a fixed backdrop div whose
color interpolates through keyed stops (dawn cream → morning gold → dusk → deep night
→ dawn) by scroll fraction, smoothstepped between keys. When interpolated luminance
crosses a threshold, toggle a body.night class that swaps text tokens (with a slow
color transition). The page itself passes through the day — one cohesive signature
that replaces repeating a widget per section.

## 9. Object metaphors beat charts

When a data section still "feels like a graph" after styling, stop styling and promote
the data into an object the brand owns: a moon that fills to the score (fraction →
phase terminator, halo grows with fullness), a tide whose waves reach as deep as each
sleep cycle (leaving wet marks as the record), a sprig that grows with recovery (stem
= deep, leaves = REM, bloom = the score). Build 3+ candidates as a live comparison lab
and let the user pick — a metaphor is a taste decision, not a correctness one. Watch
for the gift of coincidence (a score of 89 IS an 89%-full moon).

## Compose rule

One *signature* effect (usually #1 or a reference-specific centerpiece) + #4 everywhere +
at most one accent (#5/#6/#7). More than that and the page competes with itself.
Corollary from feedback: **a good widget used four times is a template** — when a page
has repeated sections (scenes, features), give each its OWN mechanic (card once, big
counting number once, scroll-eased value once, drawn chart once) under one visual
system, rather than cloning the best one.
