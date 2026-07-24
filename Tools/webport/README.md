# webgen — website engine skill

A dead-simple website engine an AI agent can drive as a **skill**. One CLI that
scaffolds token-driven static sites, screenshots them at multiple viewport widths
(headless Chromium), extracts design specs from reference sites, and gates the
result through a static + runtime quality check.

> **Agents:** read **[SKILL.md](SKILL.md)** — that's the canonical usage guide
> (registered as the `webgen` skill). This README is the human setup + overview.

Companion to [image-gen-v3](https://github.com/RomanSlack/image-gen-v3) (`imagegen`
skill): webgen builds the page, imagegen fills its `assets/`.

## Setup

```bash
git clone https://github.com/kambar231/WebPort.git
cd WebPort
./install.sh                # installs deps, registers the webgen skill
```

`install.sh` is idempotent — re-run it after a `git pull`. It links the skill into
`~/.claude/skills/` (rewriting the CLI path to wherever you cloned), and installs
the Python deps. No API keys needed.

**Manual setup**, if you'd rather:

```bash
pip install -r requirements.txt      # playwright
# uses the Chromium at $PLAYWRIGHT_BROWSERS_PATH/chromium if present,
# otherwise: python3 -m playwright install chromium
```

## Use

```bash
# scaffold a site (tokens.css + placeholder sections + manifest)
python3 webgen.py init ./site --name "Acme" --desc "Acme landing page"

# extract a reference site's design spec + full-page reference screenshot
python3 webgen.py capture https://example.com --out spec.json

# screenshot at widths; catches console errors, failed requests, mobile overflow
python3 webgen.py shot ./site --widths 1440,390

# quality gate: TODO placeholders, missing alts, broken refs, overflow… exit 0 = shippable
python3 webgen.py check ./site

# plain dev server for a human
python3 webgen.py serve ./site --port 8000
```

`stdout` is always one JSON object; live progress goes to `stderr`. The build
method (tokens first → section by section → shot → check) is in **[SKILL.md](SKILL.md)**.

## What it gives you

- **One command, JSON out** — trivial for an agent to call and parse.
- **A workflow, not just a scaffold** — design tokens as the single source of
  truth, section placeholders tracked as errors until finished, screenshots the
  agent must read, and a `check` verb that defines "done".
- **Self-serving screenshots** — `shot`/`check` spin up an ephemeral local server
  so relative paths and JS behave exactly as deployed.
- **Reference capture** — section outline, palette, fonts, and content width of
  any URL as JSON, plus a reference screenshot to compare against.
- **Runtime truth** — console errors, failed asset requests, and horizontal
  overflow per width, straight from headless Chromium.

## Files

| file | purpose |
|------|---------|
| `webgen.py` | the engine (CLI: `init` / `capture` / `shot` / `check` / `serve`) |
| `SKILL.md` | canonical agent-facing guide for `webgen` |
| `AGENTS.md` | pointer to SKILL.md |
| `install.sh` | registers the skill + installs deps (idempotent) |
| `requirements.txt` | `playwright` |
| `sites/` | sites built with the tool |
