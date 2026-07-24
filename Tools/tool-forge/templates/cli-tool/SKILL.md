---
name: __TOOL_NAME__
description: "TODO — what it does (imperative, one clause) + 'Use whenever the user…' with the exact phrases they say + concrete task nouns + 'Do NOT use for…' naming the neighboring tool that should win instead. 100–200 words, third person, no angle brackets."
---

# __TOOL_NAME__

TODO: one-line premise — the single mental model for this tool.

**Engine:** `python3 <ABSOLUTE-PATH>/engine.py` — pin the interpreter + path for the
target machine so calls work from any cwd. Reads keys from its own `.env`.

## How to call it

```
python3 engine.py run "<input>" [flags]      # single
python3 engine.py batch <file> [flags]       # many, concurrent
python3 engine.py cost                       # spend so far, incl. by_model
```

stdout is always ONE JSON object — parse it, branch on `ok`, use `outputs[*]`. Progress
streams to stderr (safe to ignore). Exit 0 = full success.

```json
{"ok": true, "outputs": ["outputs/…"], "total_cost_usd": 0.0, "results": [...], "errors": []}
```

## Flags

| flag | values | notes |
|------|--------|-------|
| `--out` | dir | default `outputs/` |
| `--estimate` | — | dry run: projected cost as JSON, does nothing |
| `--workers` | int | batch concurrency (default 4) |
| TODO | | tool-specific flags |

## Recipes

TODO: 3–6 copy-paste commands with real inputs — the common case, one batch, one edge
case.

## Batch mode

More than one input → use `batch`, not a loop of single calls. File by extension: `.txt`
one item per line · `.jsonl` one object per line (per-item overrides) · `.json` array.
A failed item never aborts the run — it lands in `results[]` with `ok:false` + `error`;
rebuild a retry file from those.

## Operational notes for the agent

- Parse stdout as JSON; check `ok`; failures explain themselves in `errors[*]`.
- If runs cost money: `--estimate` first, surface the projected cost to the user, iterate
  cheap and finalize expensive. `cost` reports spend so far.
- Every output gets a sidecar `.json` (and a batch manifest) — provenance is never lost.
