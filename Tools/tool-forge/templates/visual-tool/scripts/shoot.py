#!/usr/bin/env python3
"""Screenshot an HTML file at target viewports. stdout: one JSON object. Exit 0/1.

Usage: python shoot.py <file.html> [--width 390 1440] [--out DIR]
Requires: pip install playwright && playwright install chromium
"""
import argparse
import json
import sys
from pathlib import Path

VIEWPORTS = {390: 844, 1440: 900}  # width -> height defaults


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("html")
    ap.add_argument("--width", type=int, nargs="+", default=[390, 1440])
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    src = Path(args.html).resolve()
    if not src.is_file():
        print(json.dumps({"ok": False, "errors": [f"no such file: {src}"]}))
        return 1
    out_dir = Path(args.out) if args.out else src.parent / "shots"
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print(json.dumps({"ok": False, "errors": [
            "playwright not installed: pip install playwright && playwright install chromium"]}))
        return 1

    shots, errors = [], []
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for w in args.width:
            h = VIEWPORTS.get(w, 900)
            page = browser.new_page(viewport={"width": w, "height": h})
            console_errors = []
            page.on("console", lambda m, ce=console_errors: ce.append(m.text) if m.type == "error" else None)
            page.goto(src.as_uri())
            page.wait_for_timeout(400)  # let entrance animations settle
            dest = out_dir / f"{src.stem}_{w}w.png"
            page.screenshot(path=str(dest), full_page=True)
            shots.append(str(dest))
            if console_errors:
                errors.append({"viewport": w, "console_errors": console_errors})
            page.close()
        browser.close()

    print(json.dumps({"ok": not errors, "shots": shots, "errors": errors}, indent=1))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
