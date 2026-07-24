#!/usr/bin/env bash
#
# install.sh — register the webgen skill for Claude Code on THIS machine.
#
# Cloning the repo gives you the code; this makes the agent actually see the skill.
# It is idempotent — safe to re-run after a git pull. What it does:
#   1. installs Python deps from requirements.txt
#   2. ensures a Chromium is available for Playwright (skips if one is preinstalled)
#   3. registers the skill under ~/.claude/skills/, rewriting the CLI path in the
#      skill doc to point at THIS clone (so it works no matter where you cloned it).
#
# Usage:  ./install.sh
# Optional: CLAUDE_SKILLS_DIR=/custom/path ./install.sh
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILLS_DIR="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}"

echo "webgen installer"
echo "  repo:   $REPO"
echo "  skills: $SKILLS_DIR"
echo

# 1) Python deps (handle PEP 668 externally-managed envs gracefully).
echo "[1/3] installing Python deps …"
if ! python3 -m pip install --user -q -r "$REPO/requirements.txt" 2>/dev/null; then
  python3 -m pip install --user --break-system-packages -q -r "$REPO/requirements.txt"
fi
echo "      ok (playwright)"

# 2) browser — reuse a preinstalled Chromium if the env points at one.
echo "[2/3] checking Chromium …"
PW_DIR="${PLAYWRIGHT_BROWSERS_PATH:-/opt/pw-browsers}"
if [ -x "$PW_DIR/chromium" ] || [ -n "${WEBGEN_CHROMIUM:-}" ]; then
  echo "      using preinstalled Chromium ($PW_DIR/chromium)"
else
  python3 -m playwright install chromium
  echo "      installed Playwright Chromium"
fi

# 3) register the skill. Canonical clone symlinks (live edits, single source of
#    truth); any other clone copies with the CLI path rewritten to this clone.
CANONICAL="/home/claude/WebPort"
echo "[3/3] registering skill under $SKILLS_DIR …"
mkdir -p "$SKILLS_DIR/webgen"
DEST="$SKILLS_DIR/webgen/SKILL.md"
if [ "$REPO" = "$CANONICAL" ]; then
  ln -sfn "$REPO/SKILL.md" "$DEST"
  echo "      webgen -> $DEST (symlink)"
else
  sed "s|$CANONICAL|$REPO|g" "$REPO/SKILL.md" > "$DEST"
  echo "      webgen -> $DEST (copied, paths rewritten to this clone)"
fi

echo
echo "Done. Start a new Claude Code session to pick up the skill."
