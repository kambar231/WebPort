#!/usr/bin/env python3
"""Validate a skill directory. stdout: one JSON object. Exit 0 = valid, 1 = problems.

Usage: python validate_skill.py <skill-dir>
"""
import json
import re
import sys
from pathlib import Path

ALLOWED_KEYS = {"name", "description", "license", "allowed-tools", "metadata", "compatibility"}
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def parse_frontmatter(text):
    if not text.startswith("---"):
        return None, "SKILL.md must start with '---' YAML frontmatter"
    end = text.find("\n---", 3)
    if end == -1:
        return None, "frontmatter not closed with '---'"
    block = text[3:end].strip("\n")
    # Minimal YAML: top-level "key: value" lines; nested lines (indented) attach to metadata.
    fm, current_key = {}, None
    for line in block.splitlines():
        if not line.strip():
            continue
        if line[0] in " \t":
            if current_key:
                joined = (str(fm.get(current_key, "")) + " " + line.strip()).strip()
                fm[current_key] = joined
            continue
        if ":" not in line:
            return None, f"unparseable frontmatter line: {line!r}"
        key, _, val = line.partition(":")
        current_key = key.strip()
        val = val.strip()
        if val in (">", "|", ">-", "|-"):  # YAML block scalar: value is the indented lines
            val = ""
        fm[current_key] = val.strip('"').strip("'")
    return fm, None


def main():
    problems, warnings = [], []
    if len(sys.argv) != 2:
        print(json.dumps({"ok": False, "problems": ["usage: validate_skill.py <skill-dir>"]}))
        return 1
    root = Path(sys.argv[1]).resolve()
    skill_md = root / "SKILL.md"
    if not skill_md.is_file():
        print(json.dumps({"ok": False, "problems": [f"no SKILL.md in {root}"]}))
        return 1

    text = skill_md.read_text(encoding="utf-8")
    fm, err = parse_frontmatter(text)
    if err:
        problems.append(err)
    else:
        for k in fm:
            if k not in ALLOWED_KEYS:
                problems.append(f"frontmatter key not allowed: {k!r} (allowed: {sorted(ALLOWED_KEYS)})")
        name = fm.get("name", "")
        desc = fm.get("description", "")
        if not name:
            problems.append("frontmatter missing required key: name")
        else:
            if not NAME_RE.match(name):
                problems.append(f"name {name!r} must be kebab-case [a-z0-9-], no edge/double hyphens")
            if len(name) > 64:
                problems.append(f"name is {len(name)} chars (max 64)")
            if any(w in name for w in ("claude", "anthropic")):
                problems.append("name must not contain 'claude' or 'anthropic'")
            if name != root.name:
                problems.append(f"name {name!r} != directory name {root.name!r}")
        if not desc:
            problems.append("frontmatter missing required key: description")
        else:
            if len(desc) > 1024:
                problems.append(f"description is {len(desc)} chars (max 1024)")
            if "<" in desc or ">" in desc:
                problems.append("description must not contain '<' or '>'")
            if len(desc) < 60:
                warnings.append("description under 60 chars — almost certainly not pushy enough to trigger")
            if "do not" not in desc.lower() and "don't" not in desc.lower():
                # presence check only — it can't judge whether the boundary names the right neighbor
                warnings.append("description has no negative boundary ('Do NOT use for…')")
            if "TODO" in desc:
                problems.append("description still contains TODO — the skill is not implemented")
        if "__TOOL_NAME__" in text:
            problems.append("file still contains __TOOL_NAME__ placeholder")
        if "TODO" in text[text.find("\n---", 3) + 4:]:
            warnings.append("body contains TODO markers — implement before evaling")

    body_lines = text[text.find("\n---", 3) + 4:].count("\n") if text.startswith("---") else text.count("\n")
    if body_lines > 500:
        problems.append(f"SKILL.md body is {body_lines} lines (hard ceiling 500) — push detail to references/")
    elif body_lines > 300:
        warnings.append(f"SKILL.md body is {body_lines} lines (target <300) — consider trimming")

    # Reference hygiene: files referenced must exist; refs must be one level deep.
    for m in re.finditer(r"\]\((references/[^)#\s]+|scripts/[^)#\s]+|assets/[^)#\s]+)\)", text):
        if not (root / m.group(1)).exists():
            problems.append(f"SKILL.md links to missing file: {m.group(1)}")
    for ref in (root / "references").glob("*.md") if (root / "references").is_dir() else []:
        rtext = ref.read_text(encoding="utf-8")
        if re.search(r"\]\(references/", rtext):
            warnings.append(f"{ref.name} links to another reference — keep references one level deep")
        if rtext.count("\n") > 300 and "## " not in rtext[:2000]:
            warnings.append(f"{ref.name} exceeds 300 lines with no early headings/TOC")

    for junk in ("__pycache__", ".DS_Store", "node_modules"):
        if list(root.rglob(junk)):
            warnings.append(f"contains {junk} — exclude from packaging")

    ok = not problems
    print(json.dumps({"ok": ok, "skill": root.name, "body_lines": body_lines,
                      "problems": problems, "warnings": warnings}, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
