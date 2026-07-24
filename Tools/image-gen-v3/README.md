<p align="center">
  <img src="assets/banner.webp" alt="imagegen — a friendly crab painting in a field of poppies" width="100%">
</p>

# imagegen — image engine skill

A dead-simple image engine an AI agent can drive as a **skill**. One CLI in front of two
backends — OpenAI **gpt-image-2** / **gpt-image-1.5** and Google **gemini-3.1-flash-image**
("Nano Banana 2", default) with **gemini-3-pro-image** ("Nano Banana Pro") a flag away.
Model IDs and params verified against 2026 docs.

> **Agents:** read **[SKILL.md](SKILL.md)** — that's the canonical usage guide (registered as
> the `imagegen` skill). This README is the human setup + overview.

## Setup

**Quick install (registers both the `imagegen` and `videogen` skills):**

```bash
git clone git@github.com:RomanSlack/image-gen-v3.git
cd image-gen-v3
./install.sh                # installs deps, creates .env, registers both skills
# then add your keys to .env, and start a new Claude Code session
```

`install.sh` is idempotent — re-run it after a `git pull`. It links the skills into
`~/.claude/skills/` (rewriting the CLI paths to wherever you cloned), installs the Python
deps, and creates `.env` from the example if you don't have one.

**Manual setup**, if you'd rather:

```bash
pip install -r requirements.txt
cp .env.example .env        # add OPENAI_API_KEY + GOOGLE_API_KEY + FAL_KEY
```

The CLIs load keys from their own `.env`, so they run correctly from any directory.

## Use

```bash
# single  (auto-routes: gemini for scenes, openai for icons/edits/transparent)
python3 imagegen.py "a ceramic coffee cup by a window, soft morning light, photoreal"
# -> {"ok": true, "provider": "gemini", "model": "gemini-3.1-flash-image", "images": ["outputs/..._0.webp"], ...}

# batch  (concurrent, monitored, manifest-logged)
python3 imagegen.py batch prompts.jsonl --workers 4

# cost: estimate before spending, then track running total
python3 imagegen.py batch prompts.jsonl --estimate     # -> projected cost, generates nothing
python3 imagegen.py cost                                # -> today / all-time / by model
```

`stdout` is always one JSON object; live progress goes to `stderr`. Full flag table, batch
file formats, engine-selection rules, and the anchor/consistency workflow are in
**[SKILL.md](SKILL.md)**.

## What it gives you

- **One command, JSON out** — trivial for an agent to call and parse.
- **Two engines, one signature** — `--provider auto|openai|gemini`; `auto` routes by intent. Gemini defaults to **Nano Banana 2** (`gemini-3.1-flash-image`); `--model pro` switches to Nano Banana Pro.
- **Batch + monitoring** — concurrent worker pool, live per-item progress, a `batch_*.json` run-manifest; one failed item never aborts the run.
- **Cost estimator + tracker** — `--estimate` projects spend before generating; every run reports `cost_usd`; spend is logged to `cost_ledger.jsonl` and summarized by `imagegen.py cost`.
- **Transparent backgrounds** — `--transparent` auto-routes to gpt-image-1.5 (gpt-image-2 can't do it).
- **Provenance, always** — every image embeds its prompt in EXIF + writes a sidecar `.json`. Nothing about how an image was made is ever lost.

## Registering as a skill

`./install.sh` registers **both** skills under `~/.claude/skills/`:

```
~/.claude/skills/imagegen/SKILL.md   (image generation — OpenAI + Gemini)
~/.claude/skills/videogen/SKILL.md   (video generation — fal.ai; see VIDEOGEN.md)
```

On the canonical clone it symlinks them (editing `SKILL.md` / `VIDEOGEN.md` here updates the
skill live — single source of truth). On any other clone it copies them and rewrites the CLI
paths to that clone, so a fresh `git clone` + `./install.sh` gives anyone both skills, wired
correctly for their machine.

## Files

| file | purpose |
|------|---------|
| `imagegen.py` | image engine (CLI: `single` + `batch`, OpenAI + Gemini) |
| `videogen.py` | video engine (CLI: `single` + `batch` + `models`, fal.ai) |
| `SKILL.md` | canonical agent-facing guide for `imagegen` |
| `VIDEOGEN.md` | canonical agent-facing guide for `videogen` |
| `install.sh` | registers both skills + installs deps (idempotent) |
| `AGENTS.md` | pointer to SKILL.md + notes on the optional async Batch API |
| `requirements.txt` | `openai`, `google-genai`, `Pillow`, `python-dotenv`, `fal-client`, `requests` |
| `.env` / `.env.example` | API keys — `OPENAI_API_KEY`, `GOOGLE_API_KEY`, `FAL_KEY` (gitignored) |
| `outputs/` | cost ledgers (gitignored); clips/images land in `./videogen-outputs` / `./imagegen-outputs` in your cwd |
