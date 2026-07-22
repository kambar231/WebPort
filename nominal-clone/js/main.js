const NUMERA_BUILD = 'v25';
console.log('numera build', NUMERA_BUILD, '| reduced-motion:', matchMedia('(prefers-reduced-motion: reduce)').matches);
document.documentElement.classList.add('js');

window.__frames = 0;
// isolate init blocks: one failing feature must not kill the others
window.__safe = (name, fn) => {
  try { fn(); } catch (err) {
    console.error('init failed:', name, err);
    if (window.__hud) window.__hud('INIT ERROR in ' + name + ': ' + String(err));
    window.__choreoError = name + ': ' + String(err && err.stack || err);
  }
};

// DEMO MODE (?demo=1): auto-plays the dark sequence on a loop — used when
// the page is embedded as a live "screen" inside a portfolio card iframe.
const DEMO = new URLSearchParams(location.search).has('demo');
// SCRUB MODE (?scrub=1): like demo, but the parent page DRIVES the sequence
// via postMessage({type:'pf-scrub', p:0..1}) — used for the scroll-gated
// portfolio card. No autoplay: the sequence only moves when the user does.
const SCRUB = new URLSearchParams(location.search).has('scrub');
if (DEMO || SCRUB) document.documentElement.classList.add('demo');

// progressive enhancement only — the site must fully work without JS
document.addEventListener('DOMContentLoaded', () => {
  if (DEMO) {
    const wrap = document.querySelector('.how-scroll');
    const CYCLE = 26000;         // ms for one full pass of the sequence
    const HOLD = 1200;           // pause at the end before looping
    let t0 = performance.now();
    const drive = (t) => {
      const top = wrap.offsetTop, span = wrap.offsetHeight - innerHeight;
      const el = (t - t0) % (CYCLE + HOLD);
      const p = Math.min(1, el / CYCLE);
      scrollTo(0, top + span * p);
      requestAnimationFrame(drive);
    };
    requestAnimationFrame(drive);
    // block user scrolling — the demo owns the scroll position
    addEventListener('wheel', e => e.preventDefault(), { passive: false });
    addEventListener('touchmove', e => e.preventDefault(), { passive: false });
    // timer fallback (embedded iframes are often rAF-throttled)
    setInterval(() => {
      const top = wrap.offsetTop, span = wrap.offsetHeight - innerHeight;
      const el = (performance.now() - t0) % (CYCLE + HOLD);
      scrollTo(0, top + span * Math.min(1, el / CYCLE));
    }, 66);
  }
  if (SCRUB) {
    const wrap = document.querySelector('.how-scroll');
    const place = (p) => {
      const span = wrap.offsetHeight - innerHeight;
      scrollTo(0, wrap.offsetTop + span * Math.min(1, Math.max(0, p)));
    };
    place(0);                                   // park at the sequence start
    addEventListener('load', () => place(0));   // re-park once layout settles
    addEventListener('message', e => {
      if (e.data && e.data.type === 'pf-scrub') place(e.data.p);
    });
    addEventListener('wheel', e => e.preventDefault(), { passive: false });
    addEventListener('touchmove', e => e.preventDefault(), { passive: false });
  }
  const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;

  // ---- inertial wheel smoothing (desktop, normal mode only) -----------
  // Mouse wheels are notched; raw detents make the scroll-driven
  // choreography step like a button press. Wheel input feeds a velocity,
  // velocity feeds a lerped scroll position — every notch becomes a glide.
  // Touch keeps native momentum scrolling; demo/scrub are driven remotely.
  window.__safe('smoothscroll', () => {
  if (!DEMO && !SCRUB && !reduced && matchMedia('(hover: hover)').matches) {
    document.documentElement.classList.add('glide');  // CSS smooth-scroll would fight the lerp
    let cur = scrollY, tgt = scrollY, vel = 0;
    addEventListener('wheel', e => {
      if (e.ctrlKey) return;                       // keep pinch-zoom native
      e.preventDefault();
      const d = e.deltaY * (e.deltaMode === 1 ? 16 : 1);
      vel = Math.max(-140, Math.min(140, vel + d * .1));
    }, { passive: false });
    // external jumps (keyboard, scrollbar) resync the loop
    addEventListener('scroll', () => { if (Math.abs(scrollY - cur) > 60) { cur = tgt = scrollY; vel = 0; } }, { passive: true });
    // anchor links ride the same glide instead of jumping
    document.querySelectorAll('a[href^="#"]').forEach(a => a.addEventListener('click', e => {
      const el = document.querySelector(a.getAttribute('href'));
      if (!el) return;
      e.preventDefault();
      tgt = Math.max(0, Math.min(document.documentElement.scrollHeight - innerHeight,
        el.getBoundingClientRect().top + scrollY)); vel = 0;
    }));
    (function glide() {
      const maxY = document.documentElement.scrollHeight - innerHeight;
      if (Math.abs(vel) > .04) { tgt = Math.max(0, Math.min(maxY, tgt + vel)); vel *= .9; } else vel = 0;
      cur += (tgt - cur) * .085;
      if (Math.abs(cur - scrollY) > .4) scrollTo(0, cur);
      requestAnimationFrame(glide);
    })();
  }
  });

  // reveal-on-scroll with per-sibling stagger
  const io = new IntersectionObserver((entries) => {
    entries.forEach(e => {
      if (!e.isIntersecting) return;
      const el = e.target;
      const siblings = [...el.parentElement.children].filter(c => c.hasAttribute('data-reveal'));
      const idx = Math.max(0, siblings.indexOf(el));
      el.style.transitionDelay = reduced ? '0ms' : `${Math.min(idx, 5) * 90}ms`;
      el.classList.add('is-visible');
      io.unobserve(el);
    });
  }, { threshold: 0.12 });
  document.querySelectorAll('[data-reveal]').forEach(el => io.observe(el));

  // auto-hide nav: slides away when scrolling down (full-screen immersion
  // for the dark sequence), returns the moment you scroll up
  const nav = document.querySelector('.section-nav');
  if (nav) {
    let lastY = scrollY;
    addEventListener('scroll', () => {
      const dy = scrollY - lastY;
      lastY = scrollY;
      if (scrollY < 80) nav.classList.remove('nav-hidden');
      else if (dy > 2) nav.classList.add('nav-hidden');
      else if (dy < -2) nav.classList.remove('nav-hidden');
    }, { passive: true });
  }

  // logo marquee: duplicate the strip once and let CSS animate the loop
  window.__safe('marquee', () => {
  const strip = document.querySelector('.logo-strip');
  if (strip && !reduced) {
    const track = document.createElement('div');
    track.className = 'logo-track';
    track.append(...strip.childNodes);
    strip.append(track, track.cloneNode(true));
    strip.classList.add('is-marquee');
    strip.lastChild.setAttribute('aria-hidden', 'true');
  }
  });


  // typewriter: type "works" once when the stage first enters view,
  // then the caret stops and the underline remains
  window.__safe('typewriter', () => {
  const word = document.getElementById('type-word');
  if (word && !reduced) {
    const holder = word.parentElement;
    const w = word.textContent;
    word.textContent = '';
    const typeIo = new IntersectionObserver(async (entries) => {
      if (!entries.some(e => e.isIntersecting)) return;
      typeIo.disconnect();
      for (let i = 0; i <= w.length; i++) {
        word.textContent = w.slice(0, i);
        await new Promise(r => setTimeout(r, 110));
      }
      await new Promise(r => setTimeout(r, 900));
      holder.classList.add('done');
    }, { threshold: 0.4 });
    typeIo.observe(word.closest('.how-stage'));
  }
  });

  // ---- "How it works" choreography ------------------------------------
  // Phases across the pinned scroll (progress 0..1):
  //   0.00–0.14  intro: rectangle edges draw in, "How it works" centered
  //   0.14–0.86  four step scenes; per step the rig (camera) zooms toward
  //              that node's corner, art boxes + side panel fade in/out
  //   0.86–1.00  zoom back out, title swaps to "The Numera Platform"
  window.__safe('choreography', () => {
  const howScroll = document.querySelector('.how-scroll');
  if (howScroll) {
    // The full sequence runs on EVERY device — phones included. Geometry
    // adapts via CSS (scaled boxes, bottom-sheet panel); scroll-scrubbed
    // motion is user-driven so it also stays active under reduced-motion.
    {
      const rig = howScroll.querySelector('.rig');
      const stage = howScroll.querySelector('.how-stage');
      const lines = [...howScroll.querySelectorAll('.constellation-lines line')];
      const introTitle = howScroll.querySelector('.how-title');
      const finalTitle = howScroll.querySelector('.final-title');
      const scenes = [...howScroll.querySelectorAll('.step-scene')];
      // blocks per scene: they fly along the Z axis — from deep inside the
      // screen (negative Z, small and central via perspective) to their
      // resting plane (Z=0), then exit PAST the camera (positive Z)
      const sceneBlocks = scenes.map(sc =>
        [...sc.querySelectorAll('.art-box'), sc.querySelector('.step-panel')].map(el => ({
          el, isPanel: el.classList.contains('step-panel'),
          e: 0,   // persistent approach state — chases the scroll target
          x: 0,   // persistent exit state — same, for the departure leg
        })));
      // give every art box REAL depth (injected side faces) — the resting
      // tilt makes the volume visible; flight adds motion to it
      scenes.forEach(sc => sc.querySelectorAll('.art-box').forEach(b =>
        Choreo.extrude(b, +b.dataset.depth || 120, {background:'#181c1a', border:'1px solid rgba(255,255,255,0.28)'})));
      const easeOut = t => 1 - Math.pow(1 - t, 3);
      const easeIO = t => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);
      const easeIn = t => t * t * t;
      const Z_FROM = -2300, Z_EXIT = 2600; // exit BIG — blocks blow past the camera
      // HALLWAY TRAJECTORY: flight is linear along the perspective ray toward
      // the screen-center vanishing region — perspective itself provides the
      // "corridor" geometry. Only a GENTLE, near-constant yaw keeps the side
      // faces readable; it unwinds to front-faced over the last stretch.
      const FLY_X = 6, FLY_Y = -14;
      const MAGNET_AFTER = 500;           // ms of TRUE pause before settling — wheel-tick gaps must not trigger it
      // corner (as transform-origin %) per step, in scene order:
      // Data=top-right, Shadow Ledger=top-left, Always-On=bottom-left, Close=bottom-right
      const ORIGINS = [[75, 20], [25, 20], [25, 80], [75, 80]];
      const seg = (p, a, b) => Math.min(1, Math.max(0, (p - a) / (b - a)));
      const STEP_START = 0.14, STEP_END = 0.86;
      const W = (STEP_END - STEP_START) / scenes.length;

      // persistent fade states for the two stage titles — bistable like the
      // blocks: a pause mid-fade always resolves to fully shown or fully gone
      const fade = { intro: 1, final: 0 };
      let idleW = 0;   // 0 = following scroll, 1 = fully settled; blends smoothly

      Choreo.scene(howScroll, {
        tracks: [],
        onProgress(p, api, dt) {
          // intro: draw rectangle edges (staggered), hold title, fade out
          lines.forEach((ln, i) => {
            ln.style.opacity = Math.max(seg(p, 0.02 + i * 0.02, 0.1 + i * 0.02), 0);
          });
          const idleNow = api.idleMs() > MAGNET_AFTER;
          idleW += ((idleNow ? 1 : 0) - idleW) * (1 - Math.exp(-dt * 0.008));
          
          const kF = 1 - Math.exp(-dt * (0.014 - 0.008 * idleW));
          let introT = 1 - seg(p, STEP_START - 0.03, STEP_START + 0.03);
          introT += ((introT >= 0.5 ? 1 : 0) - introT) * idleW;   // continuous pole blend
          fade.intro += (introT - fade.intro) * kF;
          introTitle.style.opacity = fade.intro;

          // step scenes on a CONVEYOR: flight windows OVERLAP the step
          // boundaries, so while one set of blocks blows past the camera
          // the next set is already emerging small in the background.
          // The panel is a different actor: it slides UP from below, lands
          // in sync with the boxes' front-faced touchdown, and exits UP.
          let zoom = 1, origin = null;
          scenes.forEach((sc, i) => {
            const s = STEP_START + i * W;
            const lp = seg(p, s, s + W);                   // core (zoom) progress
            const anyVisible = p > s - 0.36 * W && p < s + 1.52 * W;
            sc.style.opacity = anyVisible ? 1 : 0;
            sc.style.pointerEvents = lp > 0.2 && lp < 0.8 ? 'auto' : 'none';
            let sceneMaxZ = -Infinity;   // stacked below: layering fix
            // OWNERSHIP POLES: at rest, the scene whose step interval
            // contains p is fully landed; scenes before it have fully left,
            // scenes after it haven't arrived. Complementary by construction
            // — a pause can never leave the stage empty.
            let poleE, poleX;
            if (p < s) { poleE = 0; poleX = 0; }
            else if (p < s + W) { poleE = 1; poleX = 0; }
            else { poleE = 1; poleX = 1; }
            (sceneBlocks[i] || []).forEach((f, j) => {
              const st = j * 0.08 * W;                     // per-block stagger
              let enterRaw, exitRaw;
              if (f.isPanel) {
                // panel lands WITH the boxes' touchdown, exits upward early
                enterRaw = seg(p, s + 0.06 * W, s + 0.50 * W);
                exitRaw = seg(p, s + 0.64 * W, s + 0.94 * W);
              } else {
                // boxes: enter BEFORE the step officially starts (behind the
                // previous set's exit), leave well into the next step
                enterRaw = seg(p, s - 0.30 * W + st, s + 0.34 * W + st);
                exitRaw = seg(p, s + 0.58 * W + st, s + 1.22 * W + st);
              }
              // while scrolling: track the (staggered) scroll targets.
              // while idle: follow the GROUP decision computed above.
              const eScroll = easeIO(enterRaw);
              // targets BLEND between scroll-following and the ownership
              // pole via idleW — continuous, so resuming a scrub never jumps
              const eT = eScroll + (poleE - eScroll) * idleW;
              const xT = exitRaw + (poleX - exitRaw) * idleW;
              const k = 1 - Math.exp(-dt * (0.014 - 0.008 * idleW));
              f.e += (eT - f.e) * k;
              f.x += (xT - f.x) * k;
              // BOUNDED LAG: smoothing may trail the scroll target, but never
              // so far that fast scrolling outruns the animation entirely
              const LAG = 0.28;
              f.e = Math.max(eT - LAG, Math.min(eT + LAG, f.e));
              f.x = Math.max(xT - LAG, Math.min(xT + LAG, f.x));
              const e = f.e;
              const exitT = easeIn(f.x);
              if (f.isPanel) {
                // vertical path: up from below → centered → up and away
                const yIn = (1 - e) * innerHeight * 0.75;
                const yOut = -exitT * innerHeight * 1.0;
                f.el.style.transform = `translateY(${yIn + yOut}px)`;
                f.el.style.opacity = seg(e, 0.02, 0.25);
              } else {
                // Z LANE: extra per-block depth separation, proportional
                // to flight amount — prevents cuboids of the same group from
                // intersecting mid-flight; exactly 0 when landed
                const lane = j * 240;
                const z = Z_FROM * (1 - e) + Z_EXIT * exitT - lane * (1 - e) + lane * exitT;
                sceneMaxZ = Math.max(sceneMaxZ, z);
                // gentle constant yaw for most of the flight, unwinding to
                // front-faced over the last 25% of the approach; a touch of
                // yaw returns as it blows past the camera
                const tilt = 1 - seg(e, 0.75, 1);
                const rx = FLY_X * tilt - 4 * exitT;
                const ry = FLY_Y * tilt + 10 * exitT;
                f.el.style.transform = Choreo.xform({ z, rotateX: rx, rotateY: ry });
                // no fade-out — it flies out of frame; only the last pixels fade
                f.el.style.opacity = Math.min(seg(e, 0.01, 0.12), 1 - seg(exitT, 0.88, 1));
              }
            });
            // LAYERING: scenes are separate stacking contexts, so browser
            // z-index — not 3D depth — decides who paints on top. Derive
            // z-index from the scene's closest block, so a set blowing past
            // the camera always covers the next set emerging in the deep.
            sc.style.zIndex = anyVisible ? String(100 + Math.round(sceneMaxZ / 40)) : '';
            if (lp > 0 && lp < 1) {
              origin = ORIGINS[i];
              const bell = Math.min(seg(lp, 0, 0.25), 1 - seg(lp, 0.75, 1));
              zoom = 1 + 0.55 * bell;
            }
          });
          if (origin) rig.style.transformOrigin = `${origin[0]}% ${origin[1]}%`;
          rig.style.transform = `scale(${zoom})`;
          // node labels fade back while zoomed so the frame reads as lines
          rig.style.opacity = 1 - 0.25 * (zoom - 1) / 0.55;

          // finale: platform title in, slight settle — bistable like the intro
          let finalT = seg(p, STEP_END + 0.02, 0.97);
          finalT += ((finalT >= 0.5 ? 1 : 0) - finalT) * idleW;
          fade.final += (finalT - fade.final) * kF;
          finalTitle.style.opacity = fade.final;
          finalTitle.style.transform = `scale(${0.94 + 0.06 * fade.final})`;
        },
      }, { tick: true });   // continuous rAF: enables the magnetic landing
    }
  }
  });

  // stat count-up when scrolled into view (e.g. "3x", "0", "65%")
  const statIo = new IntersectionObserver((entries) => {
    entries.forEach(e => {
      if (!e.isIntersecting) return;
      const el = e.target;
      statIo.unobserve(el);
      const m = el.textContent.trim().match(/^(\d+)(.*)$/);
      if (!m || reduced) return;
      const target = parseInt(m[1], 10), suffix = m[2], dur = 900, t0 = performance.now();
      const tick = (t) => {
        const p = Math.min(1, (t - t0) / dur);
        const eased = 1 - Math.pow(1 - p, 3); // ease-out cubic
        el.textContent = Math.round(target * eased) + suffix;
        if (p < 1) requestAnimationFrame(tick);
      };
      requestAnimationFrame(tick);
    });
  }, { threshold: 0.6 });
  document.querySelectorAll('.stat-number').forEach(el => statIo.observe(el));
});
