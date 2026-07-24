#!/usr/bin/env python3
"""__TOOL_NAME__ engine — agent-native CLI skeleton (tool-forge cli-contract).

Contract: stdout = exactly one JSON object, success and failure alike; progress -> stderr;
exit 0 only on full success. Subcommands: run "<input>" | batch <file> | cost.
Dry run: --estimate (parses + validates, spends nothing).

Replace do_item() with the real work; adjust flags, MODEL, and estimate_item().
"""
import argparse
import concurrent.futures as cf
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
try:  # keys from the tool's own .env so it runs from any cwd
    from dotenv import load_dotenv
    load_dotenv(HERE / ".env")
except ImportError:
    pass

OUT_DEFAULT = HERE / "outputs"
LEDGER = OUT_DEFAULT / "cost_ledger.jsonl"
MODEL = "none"  # TODO: the model/backend this tool bills against, for the cost ledger


def log(msg):
    print(msg, file=sys.stderr, flush=True)


def emit(obj, code):
    print(json.dumps(obj))
    return code


def fail(code_str, message):
    return emit({"ok": False, "outputs": [],
                 "errors": [{"code": code_str, "message": message}]}, 1)


def estimate_item(item):
    """Projected cost in USD for one item. Return 0.0 for free tools."""
    return 0.0  # TODO


def do_item(item, out_dir):
    """Do the real work for one item spec (dict; 'name' is always set by main()).

    Return {"ok": bool, "outputs": [paths], "cost_usd": float, "model": MODEL,
            "error": str|None}. Catch failures and return ok=False with a teaching
    message ("--size must be one of: 1K, 2K, 4K (got '3K')") — never raise.
    """
    # TODO: implement. Demo stub writes a text file so the skeleton smoke-tests.
    out = out_dir / f"{item['name']}.txt"
    out.write_text(json.dumps(item), encoding="utf-8")
    # provenance sidecar: how this output was made
    out.with_suffix(".json").write_text(
        json.dumps({"spec": item, "model": MODEL, "ts": time.strftime("%Y-%m-%dT%H:%M:%S")}),
        encoding="utf-8")
    return {"ok": True, "outputs": [str(out)], "cost_usd": 0.0, "model": MODEL, "error": None}


def load_batch(path):
    p = Path(path)
    if not p.is_file():
        raise ValueError(f"batch file not found: {p}")
    if p.suffix == ".txt":
        items = [{"prompt": ln.strip()} for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()]
    elif p.suffix == ".jsonl":
        items = [json.loads(ln) for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()]
    elif p.suffix == ".json":
        items = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(items, list) or not all(isinstance(i, dict) for i in items):
            raise ValueError(".json batch file must be a JSON array of item objects")
    else:
        raise ValueError(f"batch file must be .txt, .jsonl, or .json (got {p.suffix!r})")
    if not items:
        raise ValueError(f"batch file {p} contains no items")
    return items


def name_items(items):
    """Give every item a distinct output name — collisions silently overwrite files."""
    seen = {}
    for i, item in enumerate(items):
        base = str(item.get("name") or f"item_{i:03d}").strip()
        n = seen.get(base, 0)
        seen[base] = n + 1
        item["name"] = base if n == 0 else f"{base}_{n}"
    return items


def cmd_cost():
    total = today = 0.0
    by_model, runs = {}, 0
    day = time.strftime("%Y-%m-%d")
    if LEDGER.exists():
        for ln in LEDGER.read_text(encoding="utf-8").splitlines():
            e = json.loads(ln)
            c = e.get("cost_usd", 0)
            total += c
            runs += 1
            by_model[e.get("model", "unknown")] = round(by_model.get(e.get("model", "unknown"), 0) + c, 4)
            if e.get("ts", "").startswith(day):
                today += c
    return emit({"ok": True, "total_usd": round(total, 4), "today_usd": round(today, 4),
                 "runs": runs, "by_model": by_model}, 0)


def run(items, args):
    if args.estimate:  # zero side effects: parse + validate + project only
        per = [estimate_item(i) for i in items]
        return emit({"ok": True, "estimate": True, "count": len(items),
                     "cost_usd": round(sum(per), 4), "items": per}, 0)

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    results = [None] * len(items)
    log(f"__TOOL_NAME__: {len(items)} item(s), {args.workers} workers -> {out_dir}")
    with cf.ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(do_item, item, out_dir): idx for idx, item in enumerate(items)}
        done = 0
        for fut in cf.as_completed(futs):
            idx = futs[fut]
            try:
                r = fut.result()
            except Exception as e:  # a failed item never aborts the run
                r = {"ok": False, "outputs": [], "cost_usd": 0.0, "model": MODEL, "error": str(e)}
            results[idx] = r
            done += 1
            mark = "ok " if r["ok"] else "FAIL"
            log(f"  [{done}/{len(items)}] {mark} ${r['cost_usd']:.3f} {r['outputs'] or r['error']}")

    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a", encoding="utf-8") as f:
        for item, r in zip(items, results):
            f.write(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
                                "cost_usd": r["cost_usd"], "model": r.get("model", MODEL),
                                "ok": r["ok"], "spec": item}) + "\n")

    failed = [r for r in results if not r["ok"]]
    payload = {"ok": not failed, "count": len(items), "succeeded": len(items) - len(failed),
               "failed": len(failed),
               "total_cost_usd": round(sum(r["cost_usd"] for r in results), 4),
               "outputs": [o for r in results for o in r["outputs"]],
               "results": results, "errors": [r["error"] for r in failed]}
    if len(items) > 1:  # run manifest for provenance
        manifest = out_dir / f"batch_{time.strftime('%Y%m%d_%H%M%S')}.json"
        manifest.write_text(json.dumps({"items": items, "results": results}, indent=1),
                            encoding="utf-8")
        payload["manifest"] = str(manifest)
    return emit(payload, 0 if not failed else 1)


def main():
    ap = argparse.ArgumentParser(prog="__TOOL_NAME__")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(p):
        p.add_argument("--out", default=str(OUT_DEFAULT))
        p.add_argument("--estimate", action="store_true", help="dry run: project cost, do nothing")
        p.add_argument("--workers", type=int, default=4)
        # TODO: add tool-specific flags here; validate enums with teaching errors.

    p_run = sub.add_parser("run", help="single input")
    p_run.add_argument("input")
    p_run.add_argument("-n", type=int, default=1, help="outputs per input")
    common(p_run)
    p_batch = sub.add_parser("batch", help="many inputs, concurrent")
    p_batch.add_argument("file")
    common(p_batch)
    sub.add_parser("cost", help="spend summary from the ledger")

    args = ap.parse_args()
    if args.cmd == "cost":
        return cmd_cost()
    if args.cmd == "batch":
        items = load_batch(args.file)
    else:
        items = [{"prompt": args.input} for _ in range(max(1, args.n))]
    return run(name_items(items), args)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit as e:  # argparse errors: usage went to stderr; stdout still gets JSON
        if e.code not in (0, 1, None):
            fail("USAGE", "bad arguments — see usage on stderr")
        raise
    except Exception as e:  # contract: even a crash yields one JSON object on stdout
        sys.exit(fail(type(e).__name__.upper(), str(e)))
