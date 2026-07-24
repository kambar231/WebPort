#!/usr/bin/env bash
#
# install.sh — register the imagegen + videogen skills for Claude Code on THIS machine.
#
# Cloning the repo gives you the code; this makes the agent actually see the skills.
# It is idempotent — safe to re-run after a git pull. What it does:
#   1. installs Python deps from requirements.txt
#   2. creates .env from .env.example if you don't have one yet (add your keys after)
#   3. registers both skills under ~/.claude/skills/, rewriting the CLI paths in the
#      skill docs to point at THIS clone (so it works no matter where you cloned it).
#
# Usage:  ./install.sh
# Optional: CLAUDE_SKILLS_DIR=/custom/path ./install.sh
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILLS_DIR="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}"

echo "imagegen + videogen installer"
echo "  repo:   $REPO"
echo "  skills: $SKILLS_DIR"
echo

# 1) Python deps (handle PEP 668 externally-managed envs gracefully).
echo "[1/3] installing Python deps …"
if ! python3 -m pip install --user -q -r "$REPO/requirements.txt" 2>/dev/null; then
  python3 -m pip install --user --break-system-packages -q -r "$REPO/requirements.txt"
fi
echo "      ok (fal-client, requests, openai, google-genai, Pillow, python-dotenv)"

# 2) .env — never overwrite an existing one (it may hold real keys).
echo "[2/3] checking .env …"
if [ -f "$REPO/.env" ]; then
  echo "      .env already exists — leaving it untouched"
else
  cp "$REPO/.env.example" "$REPO/.env"
  echo "      created .env from .env.example — add OPENAI_API_KEY / GOOGLE_API_KEY / FAL_KEY"
fi

# 3) register skills. If this is the canonical clone, symlink (edits to the doc
#    reflect live — single source of truth). If it was cloned elsewhere, copy the
#    doc and rewrite the hardcoded CLI paths to this clone so they resolve here.
CANONICAL="/home/roman/Design_Mockup_Skill"
echo "[3/3] registering skills under $SKILLS_DIR …"
install_skill() {
  local name="$1" src="$2" dest="$SKILLS_DIR/$1/SKILL.md"
  mkdir -p "$SKILLS_DIR/$name"
  if [ "$REPO" = "$CANONICAL" ]; then
    ln -sfn "$REPO/$src" "$dest"
    echo "      $name -> $dest (symlink)"
  else
    sed "s|$CANONICAL|$REPO|g" "$REPO/$src" > "$dest"
    echo "      $name -> $dest (copied, paths rewritten to this clone)"
  fi
}
install_skill imagegen SKILL.md
install_skill videogen VIDEOGEN.md

echo
echo "Done. Start a new Claude Code session to pick up the skills."
echo "Then add your API keys to: $REPO/.env"
echo "  OPENAI_API_KEY  (images)   https://platform.openai.com/api-keys"
echo "  GOOGLE_API_KEY  (images)   https://aistudio.google.com/apikey"
echo "  FAL_KEY         (video)    https://fal.ai/dashboard/keys"
