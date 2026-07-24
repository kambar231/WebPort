#!/usr/bin/env python3
"""
videogen - one CLI in front of fal.ai's video models, built for an AI to drive.

Companion to imagegen.py: imagegen makes the still frames, videogen turns a
prompt (and optional first/last frames) into an MP4. Same contract as imagegen -
you call it from the shell, read ONE JSON object from stdout, use the returned
absolute file paths. Live progress streams to stderr so stdout stays parseable.

Three generation modes, auto-detected from the inputs you give:
  text-to-video  (t2v)  videogen "a drone shot over pine forest at dawn"
  image-to-video (i2v)  videogen "the phone lights up" --image frames/first.png
  first-last     (flf)  videogen "hand flips the phone over" --first a.png --last b.png

Subcommands:
  single   videogen "<prompt>" [flags]            # default if no subcommand
  batch    videogen batch clips.jsonl [--workers] # many, concurrent + monitored
  models   videogen models                        # dump the curated model roster
  cost     videogen cost                          # spend so far from the ledger

Every clip is saved with provenance (a sidecar .json next to the .mp4). Batch
runs also write a run-manifest. Cost is estimated before (--estimate) and
tracked after (central video_cost_ledger.jsonl). Costs real money per second of
video - always --estimate a large or high-res batch first and show the user.

Single output:
  {"ok": true, "model": "...", "endpoint": "...", "mode": "i2v",
   "videos": ["/abs/.../clip_0.mp4"], "cost_usd": 0.35, "errors": []}
Batch output:
  {"ok": true, "count": N, "succeeded": n, "failed": m, "total_cost_usd": ...,
   "videos": [...all...], "results": [ {per-item} ... ], "manifest": ".../batch_*.json"}
"""

import argparse
import json
import os
import re
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).parent
load_dotenv(ROOT / ".env")

# Default output goes to the CURRENT WORKING DIRECTORY (the repo the agent is in),
# not the skill folder - so clips land next to the code that asked for them.
# Override with --out. The cost ledger below stays central on purpose.
OUTPUT_DIR = Path.cwd() / "videogen-outputs"

LEDGER_PATH = ROOT / "outputs" / "video_cost_ledger.jsonl"   # fixed, ignores --out

_print_lock = threading.Lock()
_ledger_lock = threading.Lock()


def log(msg: str) -> None:
    """Progress to stderr - keeps stdout a single clean JSON object."""
    with _print_lock:
        print(msg, file=sys.stderr, flush=True)


# ── model roster ──────────────────────────────────────────────────────────────
# Each entry maps an alias to the fal endpoints for each supported mode, plus the
# family (which decides how arguments are shaped), allowed durations/resolutions,
# and an ESTIMATED $/second. fal renames/reprices endpoints over time - these are
# best-effort as of the 2026 catalog; `--model <any-fal-endpoint>` always works
# as a passthrough (treated as the `generic` family) if a model isn't listed.
#
# modes: t2v = text-to-video, i2v = image-to-video (needs --image),
#        flf = first-last-frame (needs --first + --last).
MODELS = {
    "kling": {
        "family": "kling",
        "label": "Kling 2.5 Turbo Pro",
        "endpoints": {
            "t2v": "fal-ai/kling-video/v2.5-turbo/pro/text-to-video",
            "i2v": "fal-ai/kling-video/v2.5-turbo/pro/image-to-video",
        },
        "durations": [5, 10],         # seconds, sent as a string ("5"/"10")
        "default_duration": 5,
        "aspects": ["16:9", "9:16", "1:1"],
        "audio": False,
        "per_sec": 0.07,
        "notes": "Great motion + value. i2v accepts an optional --last tail frame. Default workhorse.",
    },
    "veo": {
        "family": "veo",
        "label": "Veo 3.1",
        "endpoints": {
            "t2v": "fal-ai/veo3.1",
            "i2v": "fal-ai/veo3.1/image-to-video",
            "flf": "fal-ai/veo3.1/first-last-frame-to-video",
        },
        "durations": [4, 6, 8],       # seconds, sent as "4s"/"6s"/"8s"
        "default_duration": 8,
        "resolutions": ["720p", "1080p", "4k"],
        "default_resolution": "1080p",
        "aspects": ["16:9", "9:16"],
        "audio": True,                # can generate synced audio; --audio to enable
        "per_sec": 0.40,              # with audio; higher than Kling
        "notes": "Top fidelity + native audio + only listed model with first-last-frame. Use for hero shots and dialogue.",
    },
    "seedance": {
        "family": "seedance",
        "label": "Seedance 1.0 Pro (ByteDance)",
        "endpoints": {
            "t2v": "fal-ai/bytedance/seedance/v1/pro/text-to-video",
            "i2v": "fal-ai/bytedance/seedance/v1/pro/image-to-video",
        },
        "durations": [5, 10],
        "default_duration": 5,
        "resolutions": ["480p", "720p", "1080p"],
        "default_resolution": "1080p",
        "aspects": ["16:9", "9:16", "1:1"],
        "audio": False,
        "per_sec": 0.06,
        "notes": "Cheap, strong prompt-adherence and camera control. Good for bulk b-roll.",
    },
    "hailuo": {
        "family": "hailuo",
        "label": "MiniMax Hailuo 02 Pro",
        "endpoints": {
            "t2v": "fal-ai/minimax/hailuo-02/pro/text-to-video",
            "i2v": "fal-ai/minimax/hailuo-02/pro/image-to-video",
        },
        "durations": [6, 10],
        "default_duration": 6,
        "resolutions": ["768p", "1080p"],
        "default_resolution": "1080p",
        "aspects": ["16:9", "9:16"],
        "audio": False,
        "per_sec": 0.05,
        "notes": "Very natural physics/motion, expressive characters. Cheap for character shots.",
    },
    "luma": {
        "family": "luma",
        "label": "Luma Ray 2",
        "endpoints": {
            "t2v": "fal-ai/luma-dream-machine/ray-2",
            "i2v": "fal-ai/luma-dream-machine/ray-2/image-to-video",
        },
        "durations": [5, 9],
        "default_duration": 5,
        "resolutions": ["540p", "720p", "1080p"],
        "default_resolution": "1080p",
        "aspects": ["16:9", "9:16", "1:1", "4:3", "3:4", "21:9", "9:21"],
        "audio": False,
        "per_sec": 0.12,
        "notes": "Smooth, cinematic camera moves and coherent worlds. Nice for sweeping establishing shots.",
    },
}

DEFAULT_MODEL = "kling"

# alias table (lowercased) -> canonical roster key
MODEL_ALIASES = {
    "kling": "kling", "kling2.5": "kling", "kling-2.5": "kling", "k": "kling",
    "veo": "veo", "veo3": "veo", "veo3.1": "veo", "veo-3.1": "veo",
    "seedance": "seedance", "bytedance": "seedance", "seed": "seedance",
    "hailuo": "hailuo", "minimax": "hailuo",
    "luma": "luma", "ray2": "luma", "ray-2": "luma", "dream-machine": "luma",
}


# ── spec: one normalized generation request ──────────────────────────────────

DEFAULTS = dict(model=None, mode=None, duration=None, aspect=None, resolution=None,
                image=None, first=None, last=None, audio=False, n=1, name=None)


def make_spec(prompt, **over):
    spec = {**DEFAULTS, "prompt": prompt}
    spec.update({k: v for k, v in over.items() if v is not None})
    return spec


def resolve_model(spec) -> tuple:
    """Return (roster_key_or_None, model_entry). Unknown ids -> generic passthrough."""
    m = (spec.get("model") or DEFAULT_MODEL).strip()
    key = MODEL_ALIASES.get(m.lower())
    if key:
        return key, MODELS[key]
    if m.startswith("fal-ai/"):        # raw endpoint passthrough
        return None, {"family": "generic", "label": m, "endpoints": {},
                      "per_sec": 0.10, "durations": [], "default_duration": 5,
                      "audio": False, "notes": "raw fal endpoint (generic handling)"}
    # not an alias, not an endpoint -> fall back to default with a warning later
    return DEFAULT_MODEL, MODELS[DEFAULT_MODEL]


def resolve_mode(spec) -> str:
    """t2v / i2v / flf, from --mode override or the frames provided."""
    if spec.get("mode"):
        return spec["mode"]
    if spec.get("first") and spec.get("last"):
        return "flf"
    if spec.get("image") or spec.get("first"):
        return "i2v"
    return "t2v"


def resolve_duration(spec, entry) -> int:
    if spec.get("duration") is not None:
        return int(str(spec["duration"]).rstrip("s"))
    return entry.get("default_duration", 5)


# ── cost estimation + tracking ───────────────────────────────────────────────

def per_clip_cost(entry, duration) -> float:
    return round(entry.get("per_sec", 0.10) * int(duration), 4)


def estimate_spec(spec) -> dict:
    key, entry = resolve_model(spec)
    mode = resolve_mode(spec)
    dur = resolve_duration(spec, entry)
    per = per_clip_cost(entry, dur)
    return {"model": entry["label"], "mode": mode, "duration_s": dur, "n": spec["n"],
            "per_clip_usd": per, "cost_usd": round(per * spec["n"], 4)}


def append_ledger(entry: dict) -> None:
    with _ledger_lock:
        LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(LEDGER_PATH, "a") as f:
            f.write(json.dumps(entry) + "\n")


# ── provenance ───────────────────────────────────────────────────────────────

def slugify(text: str, max_len: int = 60) -> str:
    text = re.sub(r"[^a-z0-9\s-]", "", text.lower())
    text = re.sub(r"\s+", "_", text).strip("_")
    return text[:max_len] or "clip"


def save_video(data: bytes, slug: str, idx: int, meta: dict) -> str:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{slug}_{idx}.mp4"
    filepath = OUTPUT_DIR / filename
    filepath.write_bytes(data)
    sidecar = {**meta, "filename": filename,
               "generated_at": datetime.now().isoformat(timespec="seconds")}
    filepath.with_suffix(".json").write_text(json.dumps(sidecar, indent=2))
    return str(filepath.resolve())   # absolute - unambiguous no matter the cwd


# ── argument shaping per model family ─────────────────────────────────────────

def _need(path_key, spec, mode):
    p = spec.get(path_key) or (spec.get("image") if path_key == "first" else None)
    if not p:
        raise RuntimeError(f"mode {mode} needs --{path_key} (a frame image)")
    if not Path(p).exists():
        raise RuntimeError(f"frame not found: {p}")
    return p


def build_arguments(fal_client, entry, spec, mode, endpoint) -> dict:
    """Upload any local frames and shape the per-family fal payload."""
    family = entry["family"]
    prompt = spec["prompt"]
    dur = resolve_duration(spec, entry)
    aspect = spec.get("aspect") or (entry.get("aspects", ["16:9"])[0])
    resolution = spec.get("resolution") or entry.get("default_resolution", "1080p")

    def up(path):
        log(f"       uploading {Path(path).name} …")
        return fal_client.upload_file(str(path))

    # frames
    first_url = last_url = None
    if mode in ("i2v", "flf"):
        first_url = up(_need("first", spec, mode))
    if mode == "flf":
        last_url = up(_need("last", spec, mode))
    elif mode == "i2v" and spec.get("last"):        # optional tail frame for i2v
        if Path(spec["last"]).exists():
            last_url = up(spec["last"])
        else:
            log(f"[warn] tail frame missing: {spec['last']} - generating without it")

    if family == "veo":
        dur_s = f"{dur}s"
        if mode == "flf":
            return {"prompt": prompt, "first_frame_url": first_url,
                    "last_frame_url": last_url, "duration": dur_s,
                    "resolution": resolution, "aspect_ratio": aspect,
                    "generate_audio": bool(spec.get("audio"))}
        if mode == "i2v":
            return {"prompt": prompt, "image_url": first_url, "duration": dur_s,
                    "resolution": resolution, "generate_audio": bool(spec.get("audio"))}
        return {"prompt": prompt, "duration": dur_s, "resolution": resolution,
                "aspect_ratio": aspect, "generate_audio": bool(spec.get("audio"))}

    if family == "kling":
        args = {"prompt": prompt, "duration": str(dur)}
        if mode == "i2v":
            args["image_url"] = first_url
            if last_url:
                args["tail_image_url"] = last_url
        else:
            args["aspect_ratio"] = aspect
        return args

    if family in ("seedance", "hailuo"):
        args = {"prompt": prompt, "duration": str(dur), "resolution": resolution}
        if mode == "i2v":
            args["image_url"] = first_url
        else:
            args["aspect_ratio"] = aspect
        return args

    if family == "luma":
        args = {"prompt": prompt, "duration": f"{dur}s", "resolution": resolution,
                "aspect_ratio": aspect}
        if mode == "i2v":
            args["image_url"] = first_url
        return args

    # generic passthrough - best-effort common params
    args = {"prompt": prompt, "duration": str(dur)}
    if first_url:
        args["image_url"] = first_url
    if last_url:
        args["tail_image_url"] = last_url
    return args


def endpoint_for(entry, spec, mode) -> str:
    """Resolve the fal endpoint. Raw-endpoint models are used verbatim."""
    if entry["family"] == "generic":
        return spec["model"]
    eps = entry.get("endpoints", {})
    if mode not in eps:
        supported = ", ".join(eps.keys())
        raise RuntimeError(f"{entry['label']} has no {mode} endpoint (supports: {supported})")
    return eps[mode]


# ── backend ──────────────────────────────────────────────────────────────────

def run_one(spec) -> dict:
    """Generate one clip. Never raises - returns a result dict."""
    key, entry = resolve_model(spec)
    mode = resolve_mode(spec)
    try:
        import fal_client
        import requests
    except ImportError:
        return {"ok": False, "model": entry["label"], "endpoint": None, "mode": mode,
                "prompt": spec["prompt"], "videos": [], "cost_usd": 0.0,
                "error": "deps missing - pip install -r requirements.txt (fal-client, requests)"}
    if not os.getenv("FAL_KEY"):
        return {"ok": False, "model": entry["label"], "endpoint": None, "mode": mode,
                "prompt": spec["prompt"], "videos": [], "cost_usd": 0.0,
                "error": "FAL_KEY not set (get one at https://fal.ai/dashboard/keys)"}

    try:
        endpoint = endpoint_for(entry, spec, mode)
        dur = resolve_duration(spec, entry)
        slug = slugify(spec.get("name") or spec["prompt"])
        meta = {"prompt": spec["prompt"], "model": entry["label"], "endpoint": endpoint,
                "mode": mode, "duration_s": dur, "aspect": spec.get("aspect"),
                "resolution": spec.get("resolution"), "audio": bool(spec.get("audio")),
                "image": spec.get("image"), "first": spec.get("first"), "last": spec.get("last")}

        def on_update(update):
            if isinstance(update, fal_client.InProgress):
                for lg in (update.logs or []):
                    log(f"       {lg.get('message', '')}")

        videos = []
        for i in range(spec["n"]):
            arguments = build_arguments(fal_client, entry, spec, mode, endpoint)
            log(f"       generating [{i + 1}/{spec['n']}] {endpoint} ({dur}s, {mode}) …")
            result = fal_client.subscribe(endpoint, arguments=arguments,
                                          with_logs=True, on_queue_update=on_update)
            url = _extract_video_url(result)
            if not url:
                raise RuntimeError(f"no video url in fal response: {str(result)[:200]}")
            log(f"       downloading → {slug}_{len(videos)}.mp4")
            resp = requests.get(url, timeout=600)
            resp.raise_for_status()
            videos.append(save_video(resp.content, slug, len(videos), {**meta, "video_url": url}))

        cost = per_clip_cost(entry, dur) * len(videos)
        append_ledger({"ts": datetime.now().isoformat(timespec="seconds"),
                       "model": entry["label"], "endpoint": endpoint, "mode": mode,
                       "duration_s": dur, "clips": len(videos), "cost_usd": round(cost, 4),
                       "prompt": spec["prompt"][:80]})
        return {"ok": True, "model": entry["label"], "endpoint": endpoint, "mode": mode,
                "prompt": spec["prompt"], "videos": videos, "cost_usd": round(cost, 4),
                "error": None}
    except Exception as e:  # noqa: BLE001 - one bad clip shouldn't kill a batch
        return {"ok": False, "model": entry["label"], "endpoint": None, "mode": mode,
                "prompt": spec["prompt"], "videos": [], "cost_usd": 0.0, "error": str(e)}


def _extract_video_url(result) -> str:
    """fal video endpoints return {'video': {'url': ...}} or {'videos':[{'url':..}]}."""
    if not isinstance(result, dict):
        return ""
    v = result.get("video")
    if isinstance(v, dict) and v.get("url"):
        return v["url"]
    if isinstance(v, str):
        return v
    vs = result.get("videos")
    if isinstance(vs, list) and vs and isinstance(vs[0], dict):
        return vs[0].get("url", "")
    return ""


# ── batch ────────────────────────────────────────────────────────────────────

def load_specs(path: Path, defaults: dict) -> list:
    """Read .txt (one prompt/line), .jsonl (one spec/line), or .json (array of specs)."""
    text = path.read_text()
    if path.suffix == ".jsonl":
        rows = [json.loads(l) for l in text.splitlines() if l.strip()]
    elif path.suffix == ".json":
        rows = json.loads(text)
        if isinstance(rows, dict):          # tolerate {"clips": [...]} manifests
            rows = rows.get("clips", rows.get("items", []))
    else:
        rows = [{"prompt": l.strip()} for l in text.splitlines() if l.strip()]
    specs = []
    for row in rows:
        if "prompt" not in row:
            raise ValueError(f"each item needs a 'prompt' key: {row}")
        merged = {**defaults, **row}         # per-item keys override CLI defaults
        specs.append(make_spec(**{k: v for k, v in merged.items() if k in DEFAULTS or k == "prompt"}))
    return specs


def run_batch(specs: list, workers: int) -> dict:
    total = len(specs)
    log(f"batch: {total} clips, {workers} workers -> {OUTPUT_DIR}")
    results = [None] * total
    done = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = {pool.submit(run_one, s): i for i, s in enumerate(specs)}
        for fut in as_completed(futs):
            i = futs[fut]
            res = fut.result()
            results[i] = res
            done += 1
            mark = "ok " if res["ok"] else "ERR"
            tail = res["videos"][0] if res["videos"] else (res["error"] or "")[:80]
            log(f"  [{done}/{total}] {mark} {res['mode']:<4} ${res['cost_usd']:.3f} "
                f"{res['prompt'][:38]!r} -> {tail}")

    videos = [p for r in results for p in r["videos"]]
    succeeded = sum(1 for r in results if r["ok"])
    total_cost = round(sum(r["cost_usd"] for r in results), 4)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest_path = OUTPUT_DIR / f"batch_{stamp}.json"
    manifest_path.write_text(json.dumps(
        {"generated_at": datetime.now().isoformat(timespec="seconds"),
         "count": total, "succeeded": succeeded, "failed": total - succeeded,
         "total_cost_usd": total_cost, "results": results}, indent=2))
    log(f"batch done: {succeeded}/{total} ok, est ${total_cost:.3f}, "
        f"manifest -> {manifest_path.resolve()}")
    return {"ok": succeeded == total, "count": total, "succeeded": succeeded,
            "failed": total - succeeded, "total_cost_usd": total_cost,
            "videos": videos, "results": results,
            "manifest": str(manifest_path.resolve()),
            "errors": [r["error"] for r in results if r["error"]]}


# ── reports ──────────────────────────────────────────────────────────────────

def models_report() -> dict:
    roster = {}
    for k, e in MODELS.items():
        roster[k] = {"label": e["label"], "family": e["family"],
                     "modes": list(e.get("endpoints", {}).keys()),
                     "durations_s": e.get("durations"),
                     "default_duration_s": e.get("default_duration"),
                     "resolutions": e.get("resolutions"),
                     "aspects": e.get("aspects"),
                     "audio": e.get("audio", False),
                     "est_usd_per_sec": e.get("per_sec"),
                     "endpoints": e.get("endpoints"),
                     "notes": e.get("notes")}
    return {"ok": True, "default": DEFAULT_MODEL, "aliases": MODEL_ALIASES,
            "models": roster,
            "note": "modes: t2v=text-to-video, i2v=image-to-video (--image), flf=first-last-frame (--first/--last). "
                    "Any fal-ai/... endpoint also works via --model as a generic passthrough. Prices are estimates."}


def cost_report() -> dict:
    if not LEDGER_PATH.exists():
        return {"ok": True, "note": "no ledger yet", "total_usd": 0.0,
                "today_usd": 0.0, "clips": 0, "by_model": {}}
    rows = [json.loads(l) for l in LEDGER_PATH.read_text().splitlines() if l.strip()]
    today = datetime.now().date().isoformat()
    by_model = {}
    for r in rows:
        m = by_model.setdefault(r["model"], {"clips": 0, "cost_usd": 0.0})
        m["clips"] += r.get("clips", 1)
        m["cost_usd"] = round(m["cost_usd"] + r["cost_usd"], 4)
    return {"ok": True,
            "total_usd": round(sum(r["cost_usd"] for r in rows), 4),
            "today_usd": round(sum(r["cost_usd"] for r in rows if r["ts"][:10] == today), 4),
            "clips": sum(r.get("clips", 1) for r in rows),
            "runs": len(rows), "by_model": by_model,
            "ledger": str(LEDGER_PATH.relative_to(ROOT)),
            "note": "estimates; see MODELS[*]['per_sec'] in videogen.py"}


# ── CLI ──────────────────────────────────────────────────────────────────────

def add_common(ap):
    ap.add_argument("--model", help="kling (default) | veo | seedance | hailuo | luma | any fal-ai/... endpoint")
    ap.add_argument("--mode", choices=["t2v", "i2v", "flf"],
                    help="force mode (default: auto from the frames you pass)")
    ap.add_argument("--duration", help="clip length in seconds (per-model allowed set; see `videogen models`)")
    ap.add_argument("--aspect", help="16:9 (default) | 9:16 | 1:1 | ... (model-dependent)")
    ap.add_argument("--resolution", help="720p | 1080p | 4k (model-dependent)")
    ap.add_argument("--image", help="i2v: the source / first frame (an image file, e.g. from imagegen)")
    ap.add_argument("--first", help="flf: first frame (alias of --image for i2v)")
    ap.add_argument("--last", help="flf: last frame; also an optional tail frame for Kling i2v")
    ap.add_argument("--audio", action="store_true", help="veo only: generate synced audio")
    ap.add_argument("-n", type=int, default=1, help="clips per prompt (default 1)")
    ap.add_argument("--out", help="output dir (default ./videogen-outputs in the current working dir)")
    ap.add_argument("--estimate", action="store_true",
                    help="dry run: print projected cost as JSON, generate nothing")


def cli_defaults(args) -> dict:
    return dict(model=args.model, mode=args.mode, duration=args.duration, aspect=args.aspect,
                resolution=args.resolution, image=args.image, first=args.first, last=args.last,
                audio=args.audio, n=args.n)


def main():
    ap = argparse.ArgumentParser(description="Unified video generation CLI (fal.ai).")
    sub = ap.add_subparsers(dest="cmd")

    ps = sub.add_parser("single", help="generate from one prompt (default if no subcommand)")
    ps.add_argument("prompt")
    add_common(ps)

    pb = sub.add_parser("batch", help="generate from a .txt / .jsonl / .json file of clips")
    pb.add_argument("file")
    pb.add_argument("--workers", type=int, default=3, help="concurrent requests (default 3)")
    add_common(pb)

    sub.add_parser("models", help="print the curated model roster (modes, durations, prices)")
    sub.add_parser("cost", help="show spend totals from the ledger (today / all-time / by model)")

    # Allow bare `videogen "prompt" ...` (no subcommand) -> single.
    argv = sys.argv[1:]
    if argv and argv[0] not in ("single", "batch", "models", "cost", "-h", "--help"):
        argv = ["single"] + argv
    args = ap.parse_args(argv)

    global OUTPUT_DIR
    if getattr(args, "out", None):
        OUTPUT_DIR = Path(args.out).expanduser().resolve()

    if args.cmd == "models":
        print(json.dumps(models_report(), indent=2))
        return

    if args.cmd == "cost":
        print(json.dumps(cost_report(), indent=2))
        return

    if args.cmd == "batch":
        defaults = cli_defaults(args)
        specs = load_specs(Path(args.file), {k: v for k, v in defaults.items()
                                             if v not in (None, False)})
        if args.estimate:
            items = [estimate_spec(s) for s in specs]
            print(json.dumps({"ok": True, "estimate": True, "count": len(items),
                              "cost_usd": round(sum(i["cost_usd"] for i in items), 4),
                              "items": items, "note": "estimate, nothing generated"}, indent=2))
            return
        out = run_batch(specs, args.workers)
        print(json.dumps(out))
        sys.exit(0 if out["ok"] else 1)

    if args.cmd == "single":
        spec = make_spec(args.prompt, **cli_defaults(args))
        if args.estimate:
            print(json.dumps({"ok": True, "estimate": True, **estimate_spec(spec),
                              "note": "estimate, nothing generated"}, indent=2))
            return
        res = run_one(spec)
        log(f"{'ok ' if res['ok'] else 'ERR'} {res['mode']} ${res['cost_usd']:.3f} -> "
            f"{res['videos'][0] if res['videos'] else res['error']}")
        print(json.dumps({"ok": res["ok"], "model": res["model"], "endpoint": res["endpoint"],
                          "mode": res["mode"], "videos": res["videos"],
                          "cost_usd": res["cost_usd"],
                          "errors": [res["error"]] if res["error"] else []}))
        sys.exit(0 if res["ok"] else 1)

    ap.print_help()


if __name__ == "__main__":
    main()
