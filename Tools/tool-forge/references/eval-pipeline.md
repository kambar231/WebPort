# Eval pipeline — prove the tool works before shipping it

Two eval families: **task evals** (does the skill make Claude better at the job?) and
**trigger evals** (does the description fire at the right moments?). Run both for every
forged tool. Workspace layout:

```
<tool>/evals/
├── evals.json            # the task-eval prompts
├── triggers.json         # should / should-not trigger queries
└── iteration-N/          # one dir per improve-loop pass (gitignored)
    └── eval-<id>/{with-skill,baseline}/ + grading.json
```

## Task evals

**1. Write 2–3 realistic prompts** — real phrasings the user would type, substantive
enough that Claude actually needs the skill (trivial one-step asks won't exercise it).
Confirm them with the user. Save to `evals.json`:

```json
[{"id": "icons-batch", "prompt": "make me 6 matching pastel app icons for a habit tracker"}]
```

**2. Run pairs concurrently** — for each eval spawn TWO subagents in the same message:
one told to use the skill (give it the skill path), one baseline without it (or with a
snapshot of the old version when improving an existing tool). Each writes its outputs into
its own directory. Record tokens + duration from each completion — that data is only
available at completion time.

**3. Draft assertions while runs execute** — objective, descriptively named, and
*discriminating* (an assertion every output passes measures nothing). Good: "all 6 icons
share the same background hue family", "stdout parsed as JSON with ok=true", "HTML opens
with zero console errors". Prefer scripted checks over eyeballing. Purely subjective
qualities (taste, style) get a human look instead of fake assertions.

**4. Grade + compare** — fill `grading.json` per eval: each assertion `{"text", "passed",
"evidence"}`. Then compare pairs: pass-rate, tokens, duration, with-skill minus baseline.
If baseline ties with-skill, the skill isn't earning its context — cut or sharpen it.

**5. Human review** — put the artifacts in front of the user (screenshots, generated
files, side-by-side with/without) before self-iterating. Their feedback outranks the
grades.

## Improve loop

Apply feedback with these rules, then rerun into `iteration-N+1`:

- **Generalize, don't overfit** — fix the *class* of failure, not the eval's specifics;
  the skill must work on prompts you haven't written yet.
- **Cut before adding** — read the with-skill transcripts; delete instructions the agent
  ignored or that wasted its time. Leaner usually scores better.
- **Bundle repetition** — if every run wrote the same helper code, move it to `scripts/`.
- Stop when: assertions pass, the with-skill delta is clearly positive, and user feedback
  is empty. Don't polish past that.

## Trigger evals (on the description)

**1. Write ~20 queries** in `triggers.json`: 8–10 should-trigger (varied phrasing, casual
wording, typos, implicit asks) and 8–10 should-NOT-trigger **near-misses that share
keywords** with the skill (obviously-irrelevant queries measure nothing).

```json
{"should": ["mock up 5 versions of the rooms screen", "..."],
 "should_not": ["which of these two mockups do you like better", "..."]}
```

**2. Judge each query** against the installed skill inventory: given this description
(and the descriptions of neighboring skills), would the skill load? Run each 3× if using
live probes — triggering is stochastic. Score = should-rate minus false-positive-rate.

**3. Fix failures in the description only** (the body can't affect triggering): missed
triggers → add the exact phrasings; false positives → sharpen the "Do NOT use" boundary
naming the tool that should win. Keep a held-out few queries you didn't tune on as the
final check.

**4. Live confirmation after install** — fresh session, one should-phrase, one near-miss.

## Environment notes

- Claude Code: subagents via the Task tool; run all pairs in one message for concurrency.
- No-subagent environments: run serially yourself; skip baselines, keep assertions.
- Improving an installed skill: copy it out of `~/.claude/skills/` before editing (the
  installed path may be a symlink to the live repo — edit the repo, not the link).
