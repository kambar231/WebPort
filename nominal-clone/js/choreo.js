/* ------------------------------------------------------------------
   choreo.js — a tiny scroll-choreography engine.

   An animation is a SCORE: a plain data object you edit, not code.

     Choreo.scene(wrapperEl, {
       tracks: [
         { el, keys: [ {at:0, left:76, top:18, opacity:0},
                       {at:0.6, left:62, top:32, opacity:1} ],
           ease: 'easeInOut' },
         ...
       ],
       onProgress(p, api) { ... }    // optional: lines, CSS vars, anything
     })

   - wrapper's height minus one viewport = the scroll distance of the scene;
     progress p runs 0→1 across it (works with position:sticky pinning).
   - keys: keyframes at progress points; properties between keys interpolate
     with the track's easing. Supported: left/top (%), x/y (px), opacity,
     scale, rotate (deg). Unknown numeric props are set as CSS vars (--prop).
   - Everything is driven by real scroll position: scrub up, it reverses.
   ------------------------------------------------------------------ */
(function () {
  const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;

  const EASE = {
    linear: t => t,
    easeIn: t => t * t,
    easeOut: t => 1 - (1 - t) * (1 - t),
    easeInOut: t => (t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2),
  };

  const lerp = (a, b, t) => a + (b - a) * t;

  // value of `prop` at progress p, interpolated across a track's keyframes
  function sample(keys, p, prop, ease) {
    let prev = null, next = null;
    for (const k of keys) {
      if (k[prop] === undefined) continue;
      if (k.at <= p) prev = k;
      if (k.at >= p && !next) next = k;
    }
    if (!prev && !next) return undefined;
    if (!prev) return next[prop];
    if (!next || prev === next) return prev[prop];
    const span = next.at - prev.at || 1;
    return lerp(prev[prop], next[prop], ease((p - prev.at) / span));
  }

  const XFORM_PROPS = ['x', 'y', 'z', 'scale', 'rotate', 'rotateX', 'rotateY'];

  // build a transform string from sampled 3D properties — shared by tracks
  // and by imperative callers (Choreo.xform)
  function xform(v) {
    const tf = [];
    if (v.x !== undefined || v.y !== undefined || v.z !== undefined)
      tf.push(`translate3d(${v.x || 0}px, ${v.y || 0}px, ${v.z || 0}px)`);
    if (v.rotateX !== undefined) tf.push(`rotateX(${v.rotateX}deg)`);
    if (v.rotateY !== undefined) tf.push(`rotateY(${v.rotateY}deg)`);
    if (v.rotate !== undefined) tf.push(`rotate(${v.rotate}deg)`);
    if (v.scale !== undefined) tf.push(`scale(${v.scale})`);
    return tf.join(' ');
  }

  function applyTrack(t, p) {
    const ease = EASE[t.ease || 'easeInOut'] || EASE.easeInOut;
    const els = t.el.length !== undefined ? t.el : [t.el];
    const get = prop => sample(t.keys, p, prop, ease);
    const left = get('left'), top = get('top'), opacity = get('opacity');
    const v = {};
    XFORM_PROPS.forEach(prop => { const s = get(prop); if (s !== undefined) v[prop] = s; });
    const tf = xform(v);
    for (const el of els) {
      if (left !== undefined) el.style.left = left + '%';
      if (top !== undefined) el.style.top = top + '%';
      if (opacity !== undefined) el.style.opacity = opacity;
      if (tf) el.style.transform = tf;
      // any other numeric keyframe property becomes a CSS variable
      for (const k of t.keys) {
        for (const prop of Object.keys(k)) {
          if (['at', 'left', 'top', 'opacity'].includes(prop) || XFORM_PROPS.includes(prop)) continue;
          const val = get(prop);
          if (val !== undefined) el.style.setProperty('--' + prop, val);
        }
      }
    }
  }

  // ---- extrude: turn a flat element into a REAL 3D slab -------------------
  // Injects four side faces (preserve-3d) so the element has actual depth.
  // The faces extend backward from the front face; tilt the element with
  // rotateX/rotateY (via xform or a track) and the volume becomes visible,
  // with true parallax as it moves in Z. Requires `perspective` on an
  // ancestor and `transform-style: preserve-3d` up the chain.
  // A watertight cuboid: front face = the element itself (opaque), four side
  // faces extruding BACKWARD (-z, consistently — mixed directions cause the
  // see-through / split-plane artifacts), plus a solid back face. Each side
  // face is nudged 1px inward off the z=0 plane so it never z-fights the
  // front border.
  function extrude(el, depth = 24, faceStyle = {}) {
    const w = el.offsetWidth, h = el.offsetHeight;
    el.style.transformStyle = 'preserve-3d';
    const base = {
      position: 'absolute', background: faceStyle.background || '#101312',
      border: faceStyle.border || '1px solid rgba(255,255,255,0.18)',
      pointerEvents: 'none', boxSizing: 'border-box',
    };
    const faces = [
      // top: strip hinged at the top edge, swung backward
      { top: '0', left: '0', width: w + 'px', height: depth + 'px',
        transformOrigin: '50% 0', transform: 'translateZ(-1px) rotateX(-90deg)' },
      // bottom: hinged at the bottom edge, swung backward
      { bottom: '0', left: '0', width: w + 'px', height: depth + 'px',
        transformOrigin: '50% 100%', transform: 'translateZ(-1px) rotateX(90deg)' },
      // left: hinged at the left edge, swung backward
      { top: '0', left: '0', width: depth + 'px', height: h + 'px',
        transformOrigin: '0 50%', transform: 'translateZ(-1px) rotateY(90deg)' },
      // right: hinged at the right edge, swung backward
      { top: '0', right: '0', width: depth + 'px', height: h + 'px',
        transformOrigin: '100% 50%', transform: 'translateZ(-1px) rotateY(-90deg)' },
      // back: sealed rear plate
      { top: '0', left: '0', width: w + 'px', height: h + 'px',
        transform: `translateZ(${-depth}px)` },
    ];
    faces.forEach(f => {
      const d = document.createElement('div');
      Object.assign(d.style, base, f);
      d.setAttribute('aria-hidden', 'true');
      el.appendChild(d);
    });
    return el;
  }

  // opts.tick: run a continuous rAF loop instead of scroll-only updates.
  // onProgress then receives (p, api, dt) EVERY frame — dt in ms — which
  // enables time-based behaviors blended with scroll: springs, magnetic
  // settling ("finish the landing when the user stops scrolling"), decay.
  // api.idleMs() reports time since the last scroll input for exactly that.
  // NOTE: scenes intentionally do NOT bail out under prefers-reduced-motion.
  // Scroll-scrubbed choreography is user-driven (it only moves as much as
  // the user scrolls) — and OS conditions like Windows battery saver flip
  // the reduced flag silently, which would make the sequence vanish.
  // Callers that want a static fallback should decide that themselves.
  function scene(wrap, score, opts = {}) {
    if (!wrap) return { progress: () => 1, disabled: true };
    let lastScrollTs = -1e9;
    const api = {
      // position (in %) of a tracked element right now — for connectors
      pos(el) { return { x: parseFloat(el.style.left) || 0, y: parseFloat(el.style.top) || 0 }; },
      progress: 0,
      idleMs: () => performance.now() - lastScrollTs,
    };
    const compute = (dt) => {
      const r = wrap.getBoundingClientRect();
      const total = r.height - innerHeight;
      const p = total > 0 ? Math.min(1, Math.max(0, -r.top / total)) : 1;
      api.progress = p;
      (score.tracks || []).forEach(t => applyTrack(t, p));
      if (score.onProgress) score.onProgress(p, api, dt);
    };
    addEventListener('scroll', () => { lastScrollTs = performance.now(); }, { passive: true });
    if (opts.tick) {
      let last = performance.now();
      let lastStep = 0;
      const step = (t) => {
        const dt = Math.min(64, Math.max(1, t - last)); last = t; lastStep = t;
        try {
          compute(dt);
          if (window.__frames !== undefined) window.__frames++;
        } catch (err) {
          // surface the error loudly but KEEP the loop alive
          window.__choreoError = String(err && err.stack || err);
          if (window.__hud) window.__hud('ENGINE ERROR: ' + String(err));
          console.error('choreo frame error:', err);
        }
      };
      const loop = (t) => { step(t); requestAnimationFrame(loop); };
      requestAnimationFrame(loop);
      // FALLBACK DRIVE: some environments stop delivering rAF callbacks to
      // visible windows (occlusion detection, aggressive throttling). If no
      // rAF step has run in the last 200ms, drive the scene from a timer —
      // slightly less silky, but the animation ALWAYS runs.
      setInterval(() => {
        const now = performance.now();
        if (now - lastStep > 200) step(now);
      }, 50);
    } else {
      let ticking = false;
      const onScroll = () => {
        if (!ticking) { ticking = true; requestAnimationFrame(() => { compute(16); ticking = false; }); }
      };
      addEventListener('scroll', onScroll, { passive: true });
      addEventListener('resize', () => compute(16));
      compute(16);
    }
    return api;
  }

  // helper: fade `lines` in over per-line progress windows and pin their
  // endpoints to tracked elements' positions. pairs: [[i,j], ...]
  function connect(lines, nodes, pairs, api, p, windowSize = 0.5, stagger = 0.12) {
    lines.forEach((ln, i) => {
      const [ai, bi] = pairs[i] || [i, (i + 1) % nodes.length];
      const a = api.pos(nodes[ai]), b = api.pos(nodes[bi]);
      ln.setAttribute('x1', a.x); ln.setAttribute('y1', a.y);
      ln.setAttribute('x2', b.x); ln.setAttribute('y2', b.y);
      ln.style.opacity = Math.min(1, Math.max(0, (p - i * stagger) / windowSize));
    });
  }

  window.Choreo = { scene, connect, extrude, xform, EASE };
})();
