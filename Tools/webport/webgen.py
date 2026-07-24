#!/usr/bin/env python3
"""
webgen — a website engine an AI agent can drive as a skill.

One CLI, four verbs. stdout is ALWAYS one JSON object; live progress goes to
stderr. Exit code 0 on full success, 1 if anything failed.

  webgen.py init <dir> [--name --desc --sections a,b,c]   scaffold a site + tokens + manifest
  webgen.py shot <dir|file|url> [--widths --out --wait]    screenshot at widths, catch console errors
  webgen.py check <dir> [--widths]                         static + runtime quality gate
  webgen.py capture <url> [--out]                          extract a reference site's design spec
  webgen.py serve <dir> [--port]                           dev server (foreground)

Screenshots use the preinstalled Chromium if PLAYWRIGHT_BROWSERS_PATH or
WEBGEN_CHROMIUM points at one; otherwise Playwright's own.
"""

import argparse
import http.server
import json
import os
import re
import socket
import socketserver
import sys
import threading
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse, unquote

# ---------------------------------------------------------------- utilities

def log(msg):
    print(msg, file=sys.stderr, flush=True)

def emit(obj, code=None):
    print(json.dumps(obj, indent=1))
    sys.exit(0 if code is None else code)

def fail(msg, **extra):
    emit({"ok": False, "errors": [msg], **extra}, code=1)

def chromium_path():
    p = os.environ.get("WEBGEN_CHROMIUM")
    if p and Path(p).exists():
        return p
    base = os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "/opt/pw-browsers")
    cand = Path(base) / "chromium"
    return str(cand) if cand.exists() else None

def launch_browser(p):
    exe = chromium_path()
    kw = {"executable_path": exe} if exe else {}
    return p.chromium.launch(**kw)

def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]

class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):  # keep stderr clean for our own progress lines
        pass

def serve_dir(directory, port=None):
    """Start a background HTTP server for `directory`; return (url, server)."""
    port = port or free_port()
    handler = lambda *a, **kw: _Quiet(*a, directory=str(directory), **kw)
    srv = socketserver.TCPServer(("127.0.0.1", port), handler)
    srv.allow_reuse_address = True
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{port}/", srv

def resolve_target(target):
    """Return (url, server_or_None) for a dir, an .html file, or a URL."""
    if re.match(r"^https?://", target):
        return target, None
    path = Path(target).resolve()
    if path.is_dir():
        if not (path / "index.html").exists():
            fail(f"no index.html in {path}")
        url, srv = serve_dir(path)
        return url + "index.html", srv
    if path.is_file():
        url, srv = serve_dir(path.parent)
        return url + path.name, srv
    fail(f"target not found: {target}")

def stamp():
    return datetime.now().strftime("%Y%m%d_%H%M%S")

# ---------------------------------------------------------------- init

TOKENS_CSS = """\
/* ------------------------------------------------------------------
   DESIGN TOKENS — single source of truth. Define these FIRST, before
   writing any section. Every section's CSS must reference tokens, not
   raw values, so the whole site stays coherent.
   ------------------------------------------------------------------ */
:root {
  /* color */
  --color-bg: #ffffff;
  --color-surface: #f6f7f9;
  --color-text: #101828;
  --color-text-muted: #475467;
  --color-accent: #2f6bff;
  --color-accent-ink: #ffffff;
  --color-border: #e4e7ec;

  /* type — one display face, one text face, a modular scale */
  --font-display: "Inter", system-ui, sans-serif;
  --font-text: "Inter", system-ui, sans-serif;
  --text-xs: 0.79rem;
  --text-sm: 0.89rem;
  --text-base: 1rem;
  --text-lg: 1.125rem;
  --text-xl: 1.35rem;
  --text-2xl: 1.8rem;
  --text-3xl: 2.5rem;
  --text-4xl: 3.4rem;

  /* space — 4px base grid */
  --space-1: 0.25rem;
  --space-2: 0.5rem;
  --space-3: 0.75rem;
  --space-4: 1rem;
  --space-6: 1.5rem;
  --space-8: 2rem;
  --space-12: 3rem;
  --space-16: 4rem;
  --space-24: 6rem;

  /* shape + depth */
  --radius-sm: 6px;
  --radius-md: 12px;
  --radius-lg: 20px;
  --shadow-sm: 0 1px 2px rgb(16 24 40 / 0.06);
  --shadow-md: 0 8px 24px rgb(16 24 40 / 0.08);

  /* layout */
  --container: 1140px;
}
"""

BASE_CSS = """\
/* base reset + primitives; section styles go below, tokens in tokens.css */
*, *::before, *::after { box-sizing: border-box; }
body {
  margin: 0;
  font-family: var(--font-text);
  font-size: var(--text-base);
  line-height: 1.6;
  color: var(--color-text);
  background: var(--color-bg);
  -webkit-font-smoothing: antialiased;
}
img, svg, video { max-width: 100%; display: block; }
h1, h2, h3, h4 { font-family: var(--font-display); line-height: 1.15; margin: 0 0 var(--space-4); }
h1 { font-size: var(--text-4xl); letter-spacing: -0.02em; }
h2 { font-size: var(--text-3xl); letter-spacing: -0.015em; }
h3 { font-size: var(--text-xl); }
p  { margin: 0 0 var(--space-4); color: var(--color-text-muted); }
a  { color: inherit; }
.container { max-width: var(--container); margin-inline: auto; padding-inline: var(--space-6); }
.btn {
  display: inline-flex; align-items: center; gap: var(--space-2);
  padding: var(--space-3) var(--space-6); border-radius: var(--radius-sm);
  font-weight: 600; font-size: var(--text-sm); text-decoration: none;
  border: 1px solid transparent; cursor: pointer; transition: 150ms ease;
}
.btn-primary { background: var(--color-accent); color: var(--color-accent-ink); }
.btn-primary:hover { filter: brightness(1.08); }
.btn-ghost { border-color: var(--color-border); }
.btn-ghost:hover { background: var(--color-surface); }
section { padding-block: var(--space-24); }
@media (max-width: 720px) {
  h1 { font-size: var(--text-3xl); }
  h2 { font-size: var(--text-2xl); }
  section { padding-block: var(--space-16); }
}
"""

INDEX_HTML = """\
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{name}</title>
  <meta name="description" content="{desc}">
  <link rel="icon" href="data:,">
  <link rel="stylesheet" href="css/tokens.css">
  <link rel="stylesheet" href="css/styles.css">
</head>
<body>
{sections}
  <script src="js/main.js"></script>
</body>
</html>
"""

MAIN_JS = """\
// progressive enhancement only — the site must fully work without JS
document.addEventListener('DOMContentLoaded', () => {
  // reveal-on-scroll for [data-reveal] elements
  const io = new IntersectionObserver((entries) => {
    entries.forEach(e => { if (e.isIntersecting) { e.target.classList.add('is-visible'); io.unobserve(e.target); } });
  }, { threshold: 0.12 });
  document.querySelectorAll('[data-reveal]').forEach(el => io.observe(el));
});
"""

DEFAULT_SECTIONS = ["nav", "hero", "logos", "features", "metrics", "how-it-works", "cta", "footer"]

def cmd_init(args):
    root = Path(args.dir).resolve()
    if (root / "webgen.json").exists() and not args.force:
        fail(f"{root} already initialized (webgen.json exists); pass --force to overwrite")
    sections = [s.strip() for s in (args.sections or ",".join(DEFAULT_SECTIONS)).split(",") if s.strip()]
    log(f"init: {root}")
    for d in ["css", "js", "assets", "shots"]:
        (root / d).mkdir(parents=True, exist_ok=True)
    body = "\n".join(
        f'  <{"header" if s == "nav" else "footer" if s == "footer" else "section"} id="{s}" class="section-{s}">\n'
        f"    <!-- TODO section: {s} -->\n"
        f'  </{"header" if s == "nav" else "footer" if s == "footer" else "section"}>'
        for s in sections
    )
    (root / "index.html").write_text(INDEX_HTML.format(name=args.name, desc=args.desc, sections=body))
    (root / "css" / "tokens.css").write_text(TOKENS_CSS)
    (root / "css" / "styles.css").write_text(BASE_CSS)
    (root / "js" / "main.js").write_text(MAIN_JS)
    manifest = {
        "name": args.name,
        "created": stamp(),
        "sections": [{"id": s, "status": "todo"} for s in sections],
    }
    (root / "webgen.json").write_text(json.dumps(manifest, indent=2))
    log(f"  scaffolded {len(sections)} section placeholders")
    emit({
        "ok": True,
        "root": str(root),
        "files": [str(root / f) for f in ["index.html", "css/tokens.css", "css/styles.css", "js/main.js", "webgen.json"]],
        "sections": sections,
        "next": "define tokens in css/tokens.css, then build sections top-to-bottom; run `shot` after each",
        "errors": [],
    })

# ---------------------------------------------------------------- shot

def cmd_shot(args):
    from playwright.sync_api import sync_playwright
    url, srv = resolve_target(args.target)
    widths = [int(w) for w in args.widths.split(",")]
    out = Path(args.out or (Path(args.target).resolve() / "shots" if Path(args.target).is_dir() else Path.cwd() / "webgen-shots"))
    out.mkdir(parents=True, exist_ok=True)
    shots, console_errors, failed_requests = [], [], []
    ts = stamp()
    log(f"shot: {url} @ {widths}")
    with sync_playwright() as p:
        browser = launch_browser(p)
        page = browser.new_page()
        page.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)
        page.on("requestfailed", lambda r: failed_requests.append(r.url))
        page.goto(url, wait_until="networkidle")
        # scroll pass: fire lazy-load + scroll-reveal animations before shooting
        page.evaluate("async () => { for (let y = 0; y <= document.body.scrollHeight; y += 600) { scrollTo({top: y, behavior: 'instant'}); await new Promise(r => setTimeout(r, 100)); } scrollTo({top: 0, behavior: 'instant'}); }")
        page.wait_for_timeout(700)
        if args.wait:
            page.wait_for_timeout(args.wait)
        title = page.title()
        for w in widths:
            page.set_viewport_size({"width": w, "height": 900})
            page.wait_for_timeout(250)
            path = out / f"shot_{ts}_{w}w{'_full' if not args.viewport_only else ''}.png"
            page.screenshot(path=str(path), full_page=not args.viewport_only)
            shots.append({"width": w, "path": str(path.resolve())})
            log(f"  [{w}w] -> {path}")
        overflow = {}
        for w in widths:
            page.set_viewport_size({"width": w, "height": 900})
            page.wait_for_timeout(150)
            over = page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
            if over > 1:
                overflow[str(w)] = over
        browser.close()
    if srv:
        srv.shutdown()
    emit({
        "ok": not console_errors and not failed_requests,
        "title": title,
        "shots": shots,
        "console_errors": console_errors,
        "failed_requests": failed_requests,
        "horizontal_overflow_px": overflow,
        "errors": console_errors + [f"request failed: {u}" for u in failed_requests],
    }, code=1 if (console_errors or failed_requests) else 0)

# ---------------------------------------------------------------- check

def _static_checks(root):
    issues = []
    html_files = list(root.glob("*.html")) + list(root.glob("**/*.html"))
    html_files = sorted(set(html_files))
    for hf in html_files:
        rel = hf.relative_to(root)
        text = hf.read_text(errors="ignore")
        if "<!-- TODO" in text:
            for m in re.finditer(r"<!-- TODO[^>]*-->", text):
                issues.append({"level": "error", "file": str(rel), "issue": f"unfinished placeholder: {m.group(0)[:60]}"})
        if not re.search(r'<meta[^>]+viewport', text, re.I):
            issues.append({"level": "error", "file": str(rel), "issue": "missing <meta name=viewport>"})
        if not re.search(r'<title>[^<]+</title>', text, re.I):
            issues.append({"level": "error", "file": str(rel), "issue": "missing or empty <title>"})
        if not re.search(r'<meta[^>]+name=["\']description', text, re.I):
            issues.append({"level": "warn", "file": str(rel), "issue": "missing meta description"})
        for m in re.finditer(r'<img\b(?![^>]*\balt=)[^>]*>', text, re.I):
            issues.append({"level": "error", "file": str(rel), "issue": f"img missing alt: {m.group(0)[:70]}"})
        for m in re.finditer(r'(?:href|src)=["\']([^"\'#>]+)["\']', text, re.I):
            ref = m.group(1)
            if re.match(r"^(https?:|mailto:|tel:|data:|javascript:)", ref):
                continue
            target = (hf.parent / unquote(ref.split("?")[0])).resolve()
            if not target.exists():
                issues.append({"level": "error", "file": str(rel), "issue": f"broken local ref: {ref}"})
        for m in re.finditer(r'<a\b[^>]*href=["\'](#|)["\']', text, re.I):
            issues.append({"level": "warn", "file": str(rel), "issue": 'placeholder link href="#" or empty'})
    for cf in root.glob("**/*.css"):
        css = cf.read_text(errors="ignore")
        body = re.sub(r":root\s*{[^}]*}", "", css)
        hardcoded = re.findall(r"(?<!-)#[0-9a-fA-F]{3,8}\b", body)
        if str(cf.name) != "tokens.css" and len(hardcoded) > 4:
            issues.append({"level": "warn", "file": str(cf.relative_to(root)),
                           "issue": f"{len(hardcoded)} hardcoded hex colors outside tokens.css — use var(--color-*)"})
    return issues

def cmd_check(args):
    root = Path(args.dir).resolve()
    if not root.is_dir():
        fail(f"not a directory: {root}")
    log(f"check: {root}")
    issues = _static_checks(root)
    log(f"  static: {len(issues)} issue(s)")
    runtime = {"console_errors": [], "failed_requests": [], "horizontal_overflow_px": {}}
    if not args.static_only and (root / "index.html").exists():
        from playwright.sync_api import sync_playwright
        url, srv = serve_dir(root)
        widths = [int(w) for w in args.widths.split(",")]
        with sync_playwright() as p:
            browser = launch_browser(p)
            page = browser.new_page()
            page.on("console", lambda m: runtime["console_errors"].append(m.text) if m.type == "error" else None)
            page.on("requestfailed", lambda r: runtime["failed_requests"].append(r.url))
            page.goto(url + "index.html", wait_until="networkidle")
            for w in widths:
                page.set_viewport_size({"width": w, "height": 900})
                page.wait_for_timeout(150)
                over = page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
                if over > 1:
                    runtime["horizontal_overflow_px"][str(w)] = over
            browser.close()
        srv.shutdown()
        log(f"  runtime: {len(runtime['console_errors'])} console error(s), "
            f"{len(runtime['failed_requests'])} failed request(s), "
            f"overflow at {list(runtime['horizontal_overflow_px']) or 'none'}")
    errors = [i for i in issues if i["level"] == "error"]
    for w, px in runtime["horizontal_overflow_px"].items():
        errors.append({"level": "error", "file": "index.html", "issue": f"horizontal overflow {px}px at {w}w"})
    ok = not errors and not runtime["console_errors"] and not runtime["failed_requests"]
    emit({"ok": ok, "issues": issues, **runtime,
          "summary": {"errors": len(errors) + len(runtime["console_errors"]) + len(runtime["failed_requests"]),
                      "warnings": len([i for i in issues if i["level"] == "warn"])},
          "errors": [i["issue"] for i in errors] + runtime["console_errors"]},
         code=0 if ok else 1)

# ---------------------------------------------------------------- capture

CAPTURE_JS = """
() => {
  const uniq = a => [...new Set(a)];
  const secs = [...document.querySelectorAll('body header, body section, body main > div, body footer, body nav')]
    .filter(el => el.offsetHeight > 40)
    .slice(0, 40)
    .map(el => ({
      tag: el.tagName.toLowerCase(),
      id: el.id || null,
      class: (el.className && String(el.className).slice(0, 80)) || null,
      heading: (el.querySelector('h1,h2,h3')?.innerText || '').slice(0, 120) || null,
      height: el.offsetHeight,
    }));
  const els = [...document.querySelectorAll('body *')].slice(0, 1500);
  const colors = {}, fonts = {}, sizes = {};
  for (const el of els) {
    const cs = getComputedStyle(el);
    for (const c of [cs.color, cs.backgroundColor]) {
      if (c && c !== 'rgba(0, 0, 0, 0)') colors[c] = (colors[c] || 0) + 1;
    }
    const f = cs.fontFamily.split(',')[0].replace(/"/g, '').trim();
    fonts[f] = (fonts[f] || 0) + 1;
    if (/^H[1-4]$/.test(el.tagName)) sizes[el.tagName] = cs.fontSize;
  }
  const top = o => Object.entries(o).sort((a, b) => b[1] - a[1]).slice(0, 12).map(([k, v]) => ({value: k, count: v}));
  // --- motion: every element with a real transition or animation ---
  const motion = [];
  for (const el of els) {
    const cs = getComputedStyle(el);
    const hasTrans = cs.transitionDuration.split(',').some(d => parseFloat(d) > 0);
    const hasAnim = cs.animationName !== 'none';
    if ((hasTrans || hasAnim) && motion.length < 60) {
      motion.push({
        selector: el.tagName.toLowerCase() + (el.id ? '#' + el.id : '') +
                  (el.classList.length ? '.' + [...el.classList].slice(0, 3).join('.') : ''),
        transition_property: hasTrans ? cs.transitionProperty : null,
        transition_duration: hasTrans ? cs.transitionDuration : null,
        transition_easing: hasTrans ? cs.transitionTimingFunction : null,
        animation_name: hasAnim ? cs.animationName : null,
        animation_duration: hasAnim ? cs.animationDuration : null,
        animation_easing: hasAnim ? cs.animationTimingFunction : null,
        animation_iterations: hasAnim ? cs.animationIterationCount : null,
      });
    }
  }
  // --- @keyframes + @font-face pulled from same-origin stylesheets ---
  const keyframes = [], fontFaces = [];
  for (const sheet of document.styleSheets) {
    try {
      for (const rule of sheet.cssRules) {
        if (rule.type === CSSRule.KEYFRAMES_RULE && keyframes.length < 30) keyframes.push(rule.cssText.slice(0, 1200));
        if (rule.type === CSSRule.FONT_FACE_RULE && fontFaces.length < 20) fontFaces.push(rule.cssText.slice(0, 500));
      }
    } catch (e) { /* cross-origin sheet — note it */ keyframes.push('/* unreadable cross-origin sheet: ' + (sheet.href || '?') + ' */'); }
  }
  const fontLinks = [...document.querySelectorAll('link[href*="font"]')].map(l => l.href).slice(0, 10);
  return {
    title: document.title,
    description: document.querySelector('meta[name=description]')?.content || null,
    sections: secs,
    palette: top(colors),
    fonts: top(fonts),
    heading_sizes: sizes,
    body_font_size: getComputedStyle(document.body).fontSize,
    motion: motion,
    keyframes: keyframes,
    font_faces: fontFaces,
    font_links: fontLinks,
    max_content_width: (() => {
      const c = [...document.querySelectorAll('div')].map(d => d.offsetWidth).filter(w => w > 600 && w < innerWidth);
      return c.length ? Math.max(...uniq(c).filter(w => w < innerWidth - 40)) : null;
    })(),
  };
}
"""

def cmd_capture(args):
    from playwright.sync_api import sync_playwright
    out = Path(args.out or f"capture_{stamp()}.json")
    log(f"capture: {args.url}")
    with sync_playwright() as p:
        browser = launch_browser(p)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(args.url, wait_until="networkidle")
        page.wait_for_timeout(1500)
        # scroll pass first: triggers lazy content + scroll-reveal animations
        page.evaluate("async () => { for (let y = 0; y <= document.body.scrollHeight; y += 600) { scrollTo({top: y, behavior: 'instant'}); await new Promise(r => setTimeout(r, 120)); } scrollTo({top: 0, behavior: 'instant'}); }")
        page.wait_for_timeout(800)
        spec = page.evaluate(CAPTURE_JS)
        # probe hover states on interactive elements: style diff before/after hover
        hover_states = []
        style_js = "el => { const c = getComputedStyle(el); return {bg: c.backgroundColor, color: c.color, transform: c.transform, shadow: c.boxShadow, border: c.borderColor, underline: c.textDecorationLine}; }"
        for handle in page.query_selector_all("a[class*='btn'], button, .btn, nav a, header a")[:10]:
            try:
                if not handle.is_visible():
                    continue
                before = handle.evaluate(style_js)
                handle.hover()
                page.wait_for_timeout(350)
                after = handle.evaluate(style_js)
                diff = {k: {"from": before[k], "to": after[k]} for k in before if before[k] != after[k]}
                label = handle.evaluate("el => (el.innerText || '').slice(0, 40) || el.className.toString().slice(0, 40)")
                if diff:
                    hover_states.append({"element": label, "changes": diff})
            except Exception:
                continue
        spec["hover_states"] = hover_states
        page.mouse.move(0, 0)
        shot = str(Path(out).with_suffix("")) + "_reference.png"
        page.screenshot(path=shot, full_page=True)
        browser.close()
    spec["source_url"] = args.url
    spec["reference_screenshot"] = str(Path(shot).resolve())
    out.write_text(json.dumps(spec, indent=2))
    log(f"  spec -> {out}\n  reference shot -> {shot}")
    emit({"ok": True, "spec": str(out.resolve()), "reference_screenshot": str(Path(shot).resolve()),
          "sections_found": len(spec["sections"]), "errors": []})

# ---------------------------------------------------------------- film

def cmd_film(args):
    """Viewport screenshots at successive scroll positions — for observing
    scroll-driven animations frame by frame."""
    from playwright.sync_api import sync_playwright
    url, srv = resolve_target(args.target)
    ts = stamp()
    # each run gets its own subfolder under the output dir, so runs never mix
    out = Path(args.out or "webgen-film") / f"run_{ts}"
    out.mkdir(parents=True, exist_ok=True)
    frames = []
    with sync_playwright() as p:
        browser = launch_browser(p)
        page = browser.new_page(viewport={"width": args.width, "height": args.height})
        page.goto(url, wait_until="networkidle")
        page.wait_for_timeout(1200)
        total = page.evaluate("document.body.scrollHeight - innerHeight")
        y_from = max(0, args.y_from or 0)
        y_to = min(total, args.y_to) if args.y_to is not None else total
        if y_to <= y_from:
            fail(f"--to ({y_to}) must be greater than --from ({y_from}); page scrollable range is 0..{total}")
        n = args.frames
        span = y_to - y_from
        log(f"film: {url} — {n} frames over y={y_from}..{y_to} ({span}px, step ~{span // max(1, n - 1)}px) @ {args.width}x{args.height}")
        for i in range(n):
            y = y_from + (round(span * i / (n - 1)) if n > 1 else 0)
            page.evaluate(f"scrollTo({{top: {y}, behavior: 'instant'}})")
            page.wait_for_timeout(args.wait)
            path = out / f"film_{ts}_{i:03d}_y{y}.png"
            page.screenshot(path=str(path))
            frames.append({"index": i, "scroll_y": y, "path": str(path.resolve())})
            log(f"  [{i + 1}/{n}] y={y} -> {path.name}")
        browser.close()
    if srv:
        srv.shutdown()
    emit({"ok": True, "total_scroll_px": total, "frames": frames, "errors": []})

# ---------------------------------------------------------------- serve

def cmd_serve(args):
    root = Path(args.dir).resolve()
    if not root.is_dir():
        fail(f"not a directory: {root}")
    port = args.port or free_port()
    url = f"http://127.0.0.1:{port}/"
    print(json.dumps({"ok": True, "url": url, "root": str(root), "errors": []}), flush=True)
    log(f"serving {root} at {url} (Ctrl-C to stop)")
    handler = lambda *a, **kw: _Quiet(*a, directory=str(root), **kw)
    with socketserver.TCPServer(("127.0.0.1", port), handler) as srv:
        srv.allow_reuse_address = True
        try:
            srv.serve_forever()
        except KeyboardInterrupt:
            pass

# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(prog="webgen.py", description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("init", help="scaffold a new site")
    a.add_argument("dir")
    a.add_argument("--name", default="New Site")
    a.add_argument("--desc", default="")
    a.add_argument("--sections", default=None, help="comma list; default nav,hero,logos,features,metrics,how-it-works,cta,footer")
    a.add_argument("--force", action="store_true")
    a.set_defaults(fn=cmd_init)

    a = sub.add_parser("shot", help="screenshot a dir/file/url at widths")
    a.add_argument("target")
    a.add_argument("--widths", default="1440,390")
    a.add_argument("--out", default=None)
    a.add_argument("--wait", type=int, default=0, help="extra ms to wait before shooting")
    a.add_argument("--viewport-only", action="store_true", help="viewport crop instead of full page")
    a.set_defaults(fn=cmd_shot)

    a = sub.add_parser("check", help="static + runtime quality gate")
    a.add_argument("dir")
    a.add_argument("--widths", default="1440,390")
    a.add_argument("--static-only", action="store_true")
    a.set_defaults(fn=cmd_check)

    a = sub.add_parser("capture", help="extract a reference site's design spec")
    a.add_argument("url")
    a.add_argument("--out", default=None)
    a.set_defaults(fn=cmd_capture)

    a = sub.add_parser("film", help="viewport shots at successive scroll positions")
    a.add_argument("target")
    a.add_argument("--from", dest="y_from", type=int, default=None,
                   help="start scroll position in px (default: top)")
    a.add_argument("--to", dest="y_to", type=int, default=None,
                   help="end scroll position in px (default: bottom)")
    a.add_argument("--frames", type=int, default=24)
    a.add_argument("--width", type=int, default=1440)
    a.add_argument("--height", type=int, default=900)
    a.add_argument("--wait", type=int, default=350, help="ms to settle at each position")
    a.add_argument("--out", default=None)
    a.set_defaults(fn=cmd_film)

    a = sub.add_parser("serve", help="dev server (foreground)")
    a.add_argument("dir")
    a.add_argument("--port", type=int, default=None)
    a.set_defaults(fn=cmd_serve)

    args = ap.parse_args()
    try:
        args.fn(args)
    except SystemExit:
        raise
    except Exception as e:
        fail(f"{type(e).__name__}: {e}")

if __name__ == "__main__":
    main()
