#!/usr/bin/env python3
"""Scaffold a new tool directory from a template. stdout: one JSON object. Exit 0/1.

Usage: python scaffold.py <tool-name> --archetype cli-tool|instruction-skill|visual-tool [--dest DIR]
"""
import argparse
import json
import re
import shutil
import sys
from pathlib import Path

FORGE = Path(__file__).resolve().parent.parent
ARCHETYPES = ("cli-tool", "instruction-skill", "visual-tool")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("name")
    ap.add_argument("--archetype", required=True, choices=ARCHETYPES)
    ap.add_argument("--dest", default=".")
    args = ap.parse_args()

    if not re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", args.name) or len(args.name) > 64:
        print(json.dumps({"ok": False, "errors": [
            f"name {args.name!r} must be kebab-case [a-z0-9-], max 64 chars, no edge/double hyphens"]}))
        return 1
    if any(w in args.name for w in ("claude", "anthropic")):
        print(json.dumps({"ok": False, "errors": ["name must not contain 'claude' or 'anthropic'"]}))
        return 1

    dest = Path(args.dest).resolve() / args.name
    if dest.exists():
        print(json.dumps({"ok": False, "errors": [f"{dest} already exists — refusing to overwrite"]}))
        return 1

    template = FORGE / "templates" / args.archetype
    if not template.is_dir():
        print(json.dumps({"ok": False, "errors": [f"template missing: {template}"]}))
        return 1

    shutil.copytree(template, dest)
    (dest / "evals").mkdir(exist_ok=True)
    (dest / ".gitignore").write_text(".env\noutputs/\nevals/iteration-*/\n__pycache__/\n", encoding="utf-8")

    # Substitute the tool name into every text file.
    created = []
    for p in sorted(dest.rglob("*")):
        if p.is_file():
            try:
                t = p.read_text(encoding="utf-8")
                if "__TOOL_NAME__" in t:
                    p.write_text(t.replace("__TOOL_NAME__", args.name), encoding="utf-8")
            except (UnicodeDecodeError, PermissionError):
                pass
            created.append(str(p.relative_to(dest)))

    next_step = {
        "cli-tool": "implement do_item()/estimate_item() in engine.py, then fill SKILL.md "
                    "(references/cli-contract.md), then validate_skill.py",
        "instruction-skill": "fill every TODO in SKILL.md (references/skill-authoring.md), "
                             "then validate_skill.py",
        "visual-tool": "inline tokens.css into template.html, fill SKILL.md "
                       "(references/visual-tools.md), then validate_skill.py",
    }[args.archetype]
    print(json.dumps({"ok": True, "tool": args.name, "archetype": args.archetype,
                      "path": str(dest), "files": created, "next": next_step}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
