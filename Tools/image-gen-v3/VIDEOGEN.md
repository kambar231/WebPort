---
name: videogen
description: Generate video clips (MP4) by calling a local CLI that fronts fal.ai's video models — Kling 2.5 Turbo Pro (default), Veo 3.1 (with audio + first-last-frame), Seedance, Hailuo, Luma Ray 2. Use when you need to actually PRODUCE video files — text-to-video, image-to-video (animate a still), or first-last-frame (interpolate between two stills), for ads, product/onboarding footage, b-roll, social clips, or animated logos. Companion to `imagegen`: generate the first/last frames with imagegen, then hand them to videogen. This is the tool to call when the user wants video made from a prompt or from images.
---

# videogen

A single CLI that produces **MP4 files** from prompts (and optional frame images), fronting **fal.ai**'s video model catalog. You call it from the shell, read **one JSON object from stdout**, and use the returned absolute file paths. It saves a sidecar `.json` with full provenance next to every clip. Same contract, cost-tracking, and batch design as the `imagegen` skill — they're built to be used together.

**Engine:** `python3 /home/roman/Design_Mockup_Skill/videogen.py`
(It loads `FAL_KEY` from its own `.env`, so it works from any working directory.)

## When to invoke

- "Generate / make / render a video of …" (from a text prompt).
- "Animate this image / make this still move" (image-to-video).
- "Morph / transition from image A to image B" (first-last-frame).
- "Make an ad / product clip / onboarding footage / b-roll / animated logo."
- "Generate a batch of clips" / many prompts at once.

## When NOT to invoke

- You only need still images → use **`imagegen`**.
- You want a fully edited, multi-scene, timeline-based video with captions/motion-graphics/narration → that's the **HyperFrames** skills. videogen produces individual AI-generated **source clips**; HyperFrames composes finished videos. They pair well (videogen makes the footage, HyperFrames edits it).
- You only want prompt **text** authored → use `image-prompts` for the frame prompts.

## How to call it

```
python3 /home/roman/Design_Mockup_Skill/videogen.py "<prompt>" [flags]      # single
python3 /home/roman/Design_Mockup_Skill/videogen.py batch <file> [flags]    # many, concurrent
python3 /home/roman/Design_Mockup_Skill/videogen.py models                  # roster (see live options)
python3 /home/roman/Design_Mockup_Skill/videogen.py cost                     # spend so far
```

stdout is ALWAYS one JSON object — parse it. Live progress (uploads, fal queue logs, downloads) goes to **stderr**. Exit code is 0 on full success, 1 if anything failed.

Single result:
```json
{"ok": true, "model": "Kling 2.5 Turbo Pro", "endpoint": "fal-ai/kling-video/v2.5-turbo/pro/image-to-video",
 "mode": "i2v", "videos": ["/abs/path/videogen-outputs/clip_0.mp4"], "cost_usd": 0.35, "errors": []}
```

## The three modes (auto-detected from what you pass)

| Mode | Trigger | What it does |
|------|---------|--------------|
| **t2v** text-to-video | just a prompt | pure generation from the text |
| **i2v** image-to-video | `--image <frame>` | animates a still (your imagegen frame becomes the first frame / reference) |
| **flf** first-last-frame | `--first <a>` + `--last <b>` | interpolates a motion between two stills (Veo 3.1 only) |

Force a mode with `--mode t2v|i2v|flf` if needed. **The image-to-video and first-last-frame modes ARE the "use images as references" workflow** — the frame(s) you pass constrain the look, subject, and composition of the video.

## Where the videos go (read this first)

**`videos[*]` are absolute paths** — use them exactly as returned. By default clips save to **`./videogen-outputs/` in your current working directory**. To target a folder, pass **`--out <dir>`** (relative or absolute, created if missing):

```
python3 .../videogen.py "..." --out ./assets/clips
```

## Picking a model (`--model`, default `kling`)

Run `videogen.py models` for the live roster (modes, durations, resolutions, prices). Quick guide:

| Want | Use | Why |
|------|-----|-----|
| default workhorse, great motion, cheap, i2v + optional tail frame | **kling** (default) | Kling 2.5 Turbo Pro, ~$0.07/s |
| top fidelity, **native audio**, **first-last-frame**, dialogue/hero shots | **veo** | Veo 3.1 — only model here that does flf + audio (`--audio`), ~$0.40/s |
| cheap bulk b-roll, strong prompt-adherence + camera control | **seedance** | Seedance 1.0 Pro, ~$0.06/s |
| natural physics, expressive characters, cheap | **hailuo** | MiniMax Hailuo 02, ~$0.05/s |
| smooth cinematic camera moves, establishing shots | **luma** | Luma Ray 2, ~$0.12/s |

Any raw fal endpoint also works: `--model fal-ai/<something>/image-to-video` (treated as a generic passthrough with common params). fal renames/reprices endpoints over time — if a listed one 404s, check https://fal.ai/models and pass the current id via `--model`.

## Flags

| flag | values |
|------|--------|
| `--model` | `kling` (default) `veo` `seedance` `hailuo` `luma` \| any `fal-ai/...` endpoint |
| `--mode` | `t2v` `i2v` `flf` (default: auto from the frames you pass) |
| `--duration` | seconds; per-model allowed set (Kling 5/10, Veo 4/6/8, …) — see `models` |
| `--aspect` | `16:9` (default) `9:16` `1:1` … (model-dependent) |
| `--resolution` | `720p` `1080p` `4k` (model-dependent) |
| `--image` | i2v source / first frame (an image file, e.g. from imagegen) |
| `--first` / `--last` | flf frames; `--last` is also an optional **tail** frame for Kling i2v |
| `--audio` | Veo only: generate synced audio |
| `-n` | clips per prompt (default 1) |
| `--out` | output dir (default `./videogen-outputs`) |
| `--estimate` | dry run: print projected cost as JSON, generate nothing |
| `--workers` | (batch) concurrent requests, default 3 |

## The imagegen → videogen workflow (frames as references)

This is the main pattern. Generate stills with `imagegen`, then animate them.

**1. Animate one still (i2v):**
```bash
# make the frame
python3 /home/roman/Design_Mockup_Skill/imagegen.py "belo home screen on a phone on a wooden desk, warm light" --out frames
# animate it -> reads {"images":["/abs/frames/..._0.webp"]}, feed that path to --image
python3 /home/roman/Design_Mockup_Skill/videogen.py "the screen lights up, subtle parallax, gentle push-in" \
  --image frames/belo_home_screen_0.webp --duration 5
```

**2. Morph between two stills (flf, Veo):**
```bash
# first + last frame (keep them consistent — same subject, use imagegen --refs)
python3 .../imagegen.py "phone face-down on a desk"        --out frames        # -> intro_start_0.webp
python3 .../imagegen.py "phone facing camera, belo home screen, pearl-blush studio bg" \
  --refs frames/intro_start_0.webp --out frames                                # -> intro_end_0.webp
# interpolate the flip
python3 .../videogen.py "a hand picks up the face-down phone and flips it to face the camera as the screen lights up" \
  --model veo --mode flf --first frames/intro_start_0.webp --last frames/intro_end_0.webp \
  --duration 6 --resolution 1080p --aspect 16:9
```

**Consistency tip:** to keep a set of clips on-brand, generate ONE anchor still, reuse it via imagegen `--refs` for every other frame (see the `imagegen` anchor workflow), then animate. The frames carry the palette/lighting; the video inherits it.

## Batch mode (use whenever there is more than one clip)

Input file format is chosen by extension:
- **`.txt`** — one prompt per line; all share the CLI flags.
- **`.jsonl`** — one JSON object per line; each key overrides the CLI defaults per item.
- **`.json`** — a JSON array of those objects (also tolerates `{"clips": [...]}`).

Per-item keys: `prompt` (required), `model`, `mode`, `duration`, `aspect`, `resolution`, `image`, `first`, `last`, `audio`, `n`, `name`.

`clips.jsonl`:
```json
{"prompt": "the phone screen lights up, gentle push-in", "model": "kling", "image": "frames/home_0.webp", "duration": 5, "name": "home"}
{"prompt": "drone sweep over an autumn campus quad at golden hour", "model": "seedance", "duration": 10, "aspect": "16:9", "name": "quad"}
```
```
python3 /home/roman/Design_Mockup_Skill/videogen.py batch clips.jsonl --workers 3
```
A failed item never aborts the run — it lands in `results` with `ok:false` + its `error`; run-level `ok` is true only if every item succeeded. Rebuild a file from the failed `results` to retry.

## Cost: estimate before, track after

Video costs **real money per second** — much more than images. Always `--estimate` a large or high-res/long batch first and surface the number to the user.

```bash
python3 .../videogen.py "..." --model veo --duration 8 --audio --estimate
# -> {"ok":true,"estimate":true,"model":"Veo 3.1","mode":"t2v","duration_s":8,"cost_usd":3.2, ...}
python3 .../videogen.py batch clips.jsonl --estimate
# -> {"ok":true,"estimate":true,"count":12,"cost_usd":6.30,"items":[...]}
```

Every real run appends to `outputs/video_cost_ledger.jsonl`. Check totals any time:
```bash
python3 .../videogen.py cost   # -> {"total_usd":..., "today_usd":..., "clips":..., "by_model":{...}}
```

Rough per-second estimates (see `MODELS[*]['per_sec']` in videogen.py): kling ~$0.07 · veo ~$0.40 (with audio) · seedance ~$0.06 · hailuo ~$0.05 · luma ~$0.12. A 5s Kling clip ≈ $0.35; an 8s Veo clip ≈ $3.20. These are estimates (fal bills per generation); confirm against your fal dashboard.

## Provenance

Every clip writes a sidecar `<name>.json` (prompt, model, endpoint, mode, duration, frame inputs, source video url, timestamp). Batches also write `videogen-outputs/batch_<timestamp>.json` with every item's full spec + result.

## Operational notes for the agent

- **Always parse stdout as JSON**; use `videos[*]` **absolute** paths verbatim. Don't scrape stderr.
- **Check `ok`.** On failure the reason is in `errors[*]` / per-item `error` (missing `FAL_KEY`, missing deps, a frame path that doesn't exist, an unsupported mode for the chosen model, a fal endpoint error).
- **Set `--out`** to control where clips land.
- **More than one clip → use `batch`** (concurrent + monitored), not a loop of single calls. Keep `--workers` modest (default 3) — fal queues and bills each.
- **Costs real money.** Don't silently run large `-n`/long/4k batches — `--estimate` first, show the projected `cost_usd`, prefer short durations / cheaper models (seedance, hailuo, kling) while iterating; save Veo for the final hero clip.
- Setup: `pip install -r requirements.txt` (adds `fal-client`, `requests`) and set `FAL_KEY` in `/home/roman/Design_Mockup_Skill/.env` (get one at https://fal.ai/dashboard/keys).
```
