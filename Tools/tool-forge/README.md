# tool-forge — the tool that makes your tools

A Claude Code meta-skill: describe a capability in plain language and Claude interviews
you, scaffolds the tool, implements it, runs a full eval pipeline on it, and installs it
as a skill. Three archetypes: **cli-tool** (imagegen-style agent-native CLI), **instruction-
skill** (pure knowledge/workflow), **visual-tool** (self-contained HTML prototypes with a
screenshot-iterate loop) — plus hybrids.

> **Agents:** read [SKILL.md](SKILL.md) — the canonical guide.

## Install

Unzip anywhere (e.g. `C:\Users\kmangibayev\Code\GIOIA\tool-forge`), then register the
skill via symlink so the repo stays the single source of truth:

```powershell
New-Item -ItemType SymbolicLink -Path "$env:USERPROFILE\.claude\skills\tool-forge" -Target "C:\Users\kmangibayev\Code\GIOIA\tool-forge"
```

(If symlinks need elevation, a junction works too:
`cmd /c mklink /J "%USERPROFILE%\.claude\skills\tool-forge" "C:\Users\kmangibayev\Code\GIOIA\tool-forge"`)

Then in a fresh Claude Code session, say e.g. *"make me a tool that generates 5 HTML
variants of any app screen I describe"* and watch it forge.

## Layout

| path | purpose |
|---|---|
| `SKILL.md` | the pipeline: interview → route → scaffold → implement → validate → eval → install |
| `references/skill-authoring.md` | frontmatter rules, the description formula, context budgeting |
| `references/cli-contract.md` | the agent-native CLI contract (JSON stdout, batch, cost gating, provenance) |
| `references/visual-tools.md` | design tokens, screenshot-iterate loop, variant batches |
| `references/eval-pipeline.md` | task evals (baseline vs with-skill), trigger evals, improve loop |
| `scripts/scaffold.py` | creates a new tool directory from a template |
| `scripts/validate_skill.py` | frontmatter/structure validator (JSON out) |
| `templates/{cli-tool,instruction-skill,visual-tool}/` | the three archetype skeletons |

Built from the official Agent Skills spec + Anthropic's skill-creator methodology +
community agent-native-CLI patterns (researched July 2026).
