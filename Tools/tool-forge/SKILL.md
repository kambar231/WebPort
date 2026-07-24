---
name: tool-forge
description: Create a new agent tool from a plain-language description — interview the user, scaffold it, implement it, eval it, and install it as a Claude Code skill. Use whenever the user wants to CREATE or IMPROVE a tool, skill, CLI, or generator — "make me a tool that…", "I want a skill for…", "build a CLI that…", "create a prototype generator", "turn this script into a skill", "add a batch mode to my tool" — even if they never say the word "skill". Handles three archetypes and hybrids: CLI tools wrapped in a skill (like imagegen), instruction-only skills (pure knowledge/workflow), and visual/HTML tools (UI mockups, dashboards, prototypes with a screenshot-iterate loop). Do NOT use when the user just wants to RUN an existing tool, or wants images/documents produced (use that tool's own skill).
---

# tool-forge

You are a toolsmith. The user describes a capability in plain language; you deliver an
installed, evaluated, agent-ready tool. Optimize for **fast, elegant, reliable** — a lean
SKILL.md that triggers correctly beats a long one that explains too much. Context is king:
every token the finished tool loads must earn its place.

## The pipeline

1. **Interview** — extract the spec from what the user already said; ask only what's missing.
2. **Route** — pick the archetype (or hybrid).
3. **Scaffold** — `python scripts/scaffold.py` creates the directory skeleton.
4. **Implement** — write the code and the SKILL.md, following the archetype reference.
5. **Validate + smoke test** — `python scripts/validate_skill.py`, then actually run the tool.
6. **Eval** — full pipeline in [references/eval-pipeline.md](references/eval-pipeline.md).
7. **Install** — symlink into `~/.claude/skills/` and confirm triggering.

Detect where the user already is in this loop and jump in there — don't restart from step 1
if they arrive with a half-built tool.

## Step 1 — Interview

First mine the conversation; most answers are already there. Then ask, at most, the gaps:

1. What should the tool let Claude (or the user) do? What does "done" look like?
2. When should it trigger — what exact phrases will the user say?
3. What does it output — files, JSON, HTML, edits? Where do outputs land?
4. What varies per call (the flags/params) vs. what is fixed policy?
5. Does it cost money or have side effects per run? (→ needs estimate/dry-run gating)
6. Are outputs objectively checkable? (→ shapes the eval step)

Keep the interview to one round of questions. Write the answers down as a short spec
(name, archetype, trigger phrases, inputs, outputs, contract, risks) and confirm it in one
message before building.

## Step 2 — Route to an archetype

| The tool mostly… | Archetype | Read |
|---|---|---|
| runs code against APIs/files, returns results (generation, conversion, scraping, batch jobs) | **cli-tool** | [references/cli-contract.md](references/cli-contract.md) |
| encodes knowledge, judgment, or a workflow — no runtime code needed | **instruction-skill** | [references/skill-authoring.md](references/skill-authoring.md) |
| produces things a human looks at — UI mockups, prototypes, dashboards, diagrams | **visual-tool** | [references/visual-tools.md](references/visual-tools.md) |

Hybrids are normal (a visual-tool with a CLI renderer; a cli-tool whose skill carries deep
prompt-writing guidance). Route by where the *hard part* lives. Every archetype ends the
same way: a skill directory with a SKILL.md — so read
[references/skill-authoring.md](references/skill-authoring.md) in all three cases before
writing any SKILL.md.

## Step 3 — Scaffold

```bash
python scripts/scaffold.py <tool-name> --archetype cli-tool|instruction-skill|visual-tool \
  --dest <parent-dir>
```

Creates the standard tree and copies the matching template from `templates/`:

```
<tool-name>/
├── SKILL.md          # agent contract — the only file that costs context
├── README.md         # human setup only; must point agents at SKILL.md
├── scripts/ | *.py   # cli-tool: the engine. Executed, never read into context.
├── references/       # only if SKILL.md would otherwise exceed ~300 lines
├── evals/            # evals.json + workspaces (gitignored)
└── assets/           # templates/fonts/tokens used in OUTPUT (visual-tool)
```

Name: kebab-case, ≤64 chars, verb-ish (`icon-batcher`, `flow-mocker`), never
`helper`/`utils`/`tools`, never containing `claude`/`anthropic`.

## Step 4 — Implement

Write the engine first, the SKILL.md last — you can't document a contract that doesn't
exist yet. Follow the archetype reference for the contract details. Non-negotiables that
apply to every archetype:

- **The SKILL.md body stays under 300 lines** (hard ceiling 500). Overflow goes to
  `references/` — one level deep, never chained. Assume Claude is smart: document the
  *contract and the decisions*, not what JSON or Python is.
- **Description is the trigger** — all "when to use" lives there, none in the body. Use the
  formula in skill-authoring.md: what it does + pushy "use whenever…" trigger phrases +
  explicit "Do NOT use for…" boundary against neighboring tools.
- **Scripts execute, references load.** Anything deterministic and repeatable becomes a
  script (its code never enters context). Anything requiring judgment stays as instructions.
- **Explain why, not MUST.** All-caps ALWAYS/NEVER is a yellow flag — replace it with the
  one-line reason the rule exists.
- **One default + an escape hatch**, not a menu. (imagegen: `auto` provider, override flags.)
- **Costly or destructive operations get a dry-run** (`--estimate` / `--dry-run`) and the
  generated SKILL.md must tell the agent to run it and surface the number before spending.

For cli-tools, the stdout/stderr/exit-code/batch contract is specified fully in
cli-contract.md — implement it exactly; it's what makes the tool drivable by an agent.
For visual-tools, the render→screenshot→compare→fix loop in visual-tools.md is what makes
output quality reliable — build the tool so the loop is cheap to run.

## Step 5 — Validate + smoke test

```bash
python scripts/validate_skill.py <tool-dir>     # frontmatter, name/description limits, tree
```

Then run the real thing once end-to-end: cli-tool → one cheap real invocation, parse the
JSON, check `ok` and exit code; visual-tool → generate one artifact and look at it;
instruction-skill → walk one example through the instructions yourself. Fix before evaling.

## Step 6 — Eval (full pipeline)

Read [references/eval-pipeline.md](references/eval-pipeline.md) and run it: 2–3 realistic
task evals as baseline-vs-with-skill subagent pairs, objective assertions, grading,
benchmark deltas, then ~20-query trigger evals (should / should-not, with near-misses) on
the description. Iterate the skill on what fails — generalize from failures, don't overfit
to the eval prompts. Stop when evals pass and another iteration wouldn't change the tool.

## Step 7 — Install

The repo is the single source of truth; the skill registration is a symlink (same pattern
as imagegen). On Windows, from an elevated or developer-mode shell:

```powershell
New-Item -ItemType SymbolicLink -Path "$env:USERPROFILE\.claude\skills\<tool-name>" -Target "C:\path\to\<tool-name>"
```

(macOS/Linux: `ln -s /path/to/<tool-name> ~/.claude/skills/<tool-name>`.)

Confirm registration in a fresh session with two probes: one phrase that should trigger it,
one near-miss that shouldn't.

## Operational notes

- Pin absolute interpreter paths in generated SKILL.md invocations when the tool targets
  one specific machine (imagegen pins its Windows python path); keep templates portable
  (`python3`) and substitute at install time.
- Secrets go in the tool's own `.env` (+ `.env.example`, gitignored), loaded by the engine
  so it runs from any cwd.
- When improving an existing tool rather than creating one: snapshot the current skill dir
  first, use it as the eval baseline, and preserve the tool's name.
- Windows tip: if symlinks are unavailable, a junction works for directories:
  `cmd /c mklink /J "%USERPROFILE%\.claude\skills\<name>" "C:\path\to\<name>"`.
