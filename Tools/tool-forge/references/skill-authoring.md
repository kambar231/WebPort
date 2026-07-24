# Writing the SKILL.md — authoring rules

The SKILL.md is the agent contract. Its description is always in context (~100 tokens per
installed skill); its body loads only when triggered; its references load only when read.
Budget accordingly: description ≤1024 chars, body <300 lines (hard ceiling 500), reference
files one level deep with a table of contents past ~300 lines.

## Frontmatter

Allowed keys: `name`, `description`, `license`, `allowed-tools`, `metadata`,
`compatibility`. Required: `name`, `description`.

- `name`: kebab-case, `^[a-z0-9-]+$`, ≤64 chars, must equal the directory name, no
  `claude`/`anthropic`, no leading/trailing/double hyphens.
- `description`: ≤1024 chars, no `<` or `>`, quoted if it contains `:` or `"`. Third
  person.
- `metadata`: string→string map for `author`/`version` (version is NOT a top-level key).

## The description formula (highest-leverage text in the whole tool)

Claude undertriggers by default, so descriptions must be deliberately pushy. Build it in
four parts, in order:

1. **What it does** — imperative, outcome-focused, one clause.
   `Generate or edit images by calling a local CLI…`
2. **When to use** — "Use when / whenever the user…" followed by the *actual phrases users
   say*: verbs, synonyms, file extensions, casual phrasings ("the xlsx in my downloads").
   Add "even if they don't explicitly say X" for implicit triggers.
3. **Concrete trigger list** — enumerate the task nouns: "mockups, UI screens, icons,
   product shots, hero images…"
4. **Negative boundary** — "Do NOT use for/when…" naming the neighboring skill or tool that
   should win instead. This is what disambiguates against competing skills.

All "when to use" information lives in the description, none in the body. Aim for 100–200
words. Test it with trigger evals (see eval-pipeline.md).

## Body structure (proven ordering)

1. **Title + one-line premise** — the single mental model ("One CLI, JSON on stdout").
2. **Routing** — if the tool has modes/engines, a compact task→choice table first.
3. **How to call it** — exact command lines, exact output shape with a real example.
4. **Flags/options table** — terse, one row per flag.
5. **Recipes** — 3–6 copy-paste examples covering the common cases, including one batch
   and one edge case.
6. **Operational notes for the agent** — parse rules, failure handling, cost gating,
   "more than one X → use batch".

## Style rules

- Imperative voice to the agent: "Parse stdout as JSON", not "You should parse…".
- Explain *why* instead of shouting: "run `--estimate` first — generation costs real money
  per image" beats "ALWAYS ESTIMATE". Caps-lock MUST/NEVER is a yellow flag: find the
  reason and state it.
- One consistent term per concept (pick "prompt", don't alternate with "query"/"request").
- Assume Claude knows the domain — cut any sentence that teaches general programming.
  Target ~50 tokens where 150 would also work.
- One default + escape hatch, not a menu of equivalent options.
- No time-sensitive facts in the body (model names/prices change: point at where the code
  defines them, e.g. "the exact table lives in `PRICING` in engine.py").
- Concrete examples over abstractions — a real command with real output beats a schema.
- If every test run makes the agent write the same helper script, that script belongs in
  `scripts/` — bundle it and change the instruction from "write code that…" to "run …".

## Degrees of freedom

Match specificity to fragility:

| Freedom | When | Mechanism |
|---|---|---|
| High | many valid approaches, judgment matters | prose heuristics |
| Medium | preferred pattern, some variance OK | template/pseudocode + params |
| Low | fragile exact sequence (migrations, billing) | a script with no choices |

## Skill vs. the other primitives

Skill = "how we do X", loaded on demand. CLAUDE.md = always-on style (costs tokens every
turn — keep tiny). Slash command = user manually fires it. Subagent = delegate work into a
fresh context. Hook = must happen regardless of the model. MCP = expose tools over a
protocol. When a forge request is really "make Claude always do X", it's a CLAUDE.md line,
not a skill — say so and save the user a tool.
