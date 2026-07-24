# The agent-native CLI contract

A CLI an agent can drive blind. imagegen is the house reference implementation; the
template in `templates/cli-tool/engine.py` implements this skeleton. Every generated
cli-tool follows all of it — the contract is what makes the tool reliable, and it's cheap
to implement once scaffolded.

## I/O contract (non-negotiable)

- **stdout: exactly one JSON object per invocation.** Nothing else, ever — no banners, no
  logs. The agent parses stdout blind.
- **stderr: human/monitor stream.** Live progress, per-item lines, warnings. Safe to show
  or ignore; never needed for correctness.
- **Exit code:** 0 = full success, 1 = anything failed. The agent checks it before parsing.
- **Non-interactive always.** No prompts, no confirmations that block; destructive or
  costly paths get flags instead (`--dry-run`, `--yes`).
- **Even a crash emits the JSON failure shape** — wrap main in a top-level handler; a raw
  traceback with empty stdout breaks the agent that's parsing blind.
- **Subcommands, not overloaded positionals** (`run` / `batch` / `cost`), so an input
  string can never collide with a command name.

Result shape — success and failure are the same shape:

```json
{"ok": true,  "outputs": ["outputs/foo_0.png"], "cost_usd": 0.05, "errors": []}
{"ok": false, "outputs": [], "cost_usd": 0.0,
 "errors": [{"code": "BAD_SIZE", "message": "--size must be one of: 1K, 2K, 4K (got '3K')"}]}
```

- `ok` first; the agent branches on it.
- Errors **teach**: name the flag, enumerate the valid values, show what was received.
- Include machine `code` + human `message`.

## Flags

- One default that covers the common case + explicit overrides (`auto` routing beats making
  the agent choose an engine every call).
- Enumerable values validated up front with teaching errors.
- `--out <dir>` for output location, defaulting inside the tool's own folder.
- Bounded output: if a command can return many items, paginate or `--limit` with a
  truncation hint in the JSON.

## Cost / side-effect gating

If a run spends money, calls a metered API, or mutates anything:

- `--estimate` / `--dry-run`: full parse + validation + projected cost as JSON, zero side
  effects — run it before creating any output dirs or touching the ledger. The generated
  SKILL.md must tell the agent: estimate first, surface the number, prefer cheap settings
  while iterating, finalize expensive.
- Report actuals on every real run (`cost_usd` per item + total).
- Append every run to a ledger (`outputs/cost_ledger.jsonl`) and provide a `cost`
  subcommand summarizing today / all-time / by model.

## Batch mode

Any tool that will ever be called with >1 input gets a batch subcommand — concurrent
worker pool, not a loop of single calls:

- Input by extension: `.txt` one item per line (shared flags) · `.jsonl` one object per
  line (per-item overrides) · `.json` array of objects.
- Per-item progress lines to stderr as items finish.
- **One failed item never aborts the run.** Per-item `ok` + `error` in `results[]`;
  run-level `ok` true only if all succeeded — so retrying is "rebuild the file from
  failed results".
- Write a run manifest (`batch_<timestamp>.json`) with every item's full spec + result.
- **Output names must be collision-free** — dedupe/index item names before writing, or a
  duplicate `name` silently overwrites an earlier output while reporting full success.

## Provenance

Outputs must be self-explaining: sidecar `<name>.json` per output (inputs, params, model,
timestamp) and embedded metadata where the format allows (EXIF for images). Nothing about
how an output was made is ever lost.

## Setup conventions

- Keys in the tool's own `.env` (+ committed `.env.example`), loaded by the engine so it
  works from any cwd. `.env` and `outputs/` gitignored.
- `requirements.txt` minimal and pinned loosely.
- The generated SKILL.md pins the exact interpreter + script path for the target machine
  (Windows: `"C:/…/python.exe" C:/…/engine.py`), because the agent may call it from any
  working directory.
