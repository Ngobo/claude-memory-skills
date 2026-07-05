#!/bin/bash
# Sync Claude Code chats -> vault(s), auto-routed per session by its cwd.
#
# Usage:
#   ./scripts/sync_obsidian.sh              # import all local sessions, auto-routed
#   ./scripts/sync_obsidian.sh --dry-run
#   ./scripts/sync_obsidian.sh --force      # reprocess even already-imported sessions
#
# Setup (requires the extractor fork that emits cwd/project frontmatter):
#   pip install git+https://github.com/Ngobo/claude-conversation-extractor.git@add-cwd-project-metadata
#   chmod +x scripts/sync_obsidian.sh
#
# Cron (daily at 10pm):
#   (crontab -l 2>/dev/null; echo "0 22 * * * $(pwd)/scripts/sync_obsidian.sh") | crontab -

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXPORT_DIR="$HOME/claude-exports"
LOG="$SCRIPT_DIR/sync.log"

mkdir -p "$EXPORT_DIR"
echo "[$(date)] Sync started" >> "$LOG"

if command -v claude-extract &> /dev/null; then
    claude-extract --all --output "$EXPORT_DIR" 2>> "$LOG"
    echo "[$(date)] Claude Code chats exported" >> "$LOG"
else
    echo "[$(date)] claude-extract not found — install the fork first:" >> "$LOG"
    echo "[$(date)]   pip install git+https://github.com/Ngobo/claude-conversation-extractor.git@add-cwd-project-metadata" >> "$LOG"
    echo "claude-extract not found. Install the fork:"
    echo "  pip install git+https://github.com/Ngobo/claude-conversation-extractor.git@add-cwd-project-metadata"
    exit 1
fi

python3 "$SCRIPT_DIR/claude_to_obsidian.py" --export-dir "$EXPORT_DIR" "$@" 2>> "$LOG"

EXIT_CODE=$?
echo "[$(date)] Sync completed (exit $EXIT_CODE)" >> "$LOG"
echo "" >> "$LOG"
exit $EXIT_CODE
