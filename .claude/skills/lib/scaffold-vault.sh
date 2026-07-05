#!/bin/bash
# scaffold-vault.sh — create a new empty vault at a given path if one doesn't already exist.
# Usage: source this file, then call `scaffold_vault_if_missing <path>`.
# Shared by the private-vault bootstrap and the "create a new shared vault" flow in
# /vault-scope, so both scopes create vaults the same way.

scaffold_vault_if_missing() {
  local path="$1"
  path="${path/#\~/$HOME}"

  if [ -d "$path/.git" ]; then
    return 0
  fi

  mkdir -p "$path"/chats "$path"/permanent "$path"/inbox "$path"/templates "$path"/fleeting "$path"/logs "$path"/references

  if [ ! -f "$path/CLAUDE.md" ]; then
    cat > "$path/CLAUDE.md" << 'EOF'
# Vault

Knowledge vault for Claude Code sessions.

## Session Commands
- `/resume` — read recent notes in `chats/<project>/` and summarize context for the current project
- `/save` — write a timestamped session note to `chats/<project>/YYYY-MM-DD-HH-MM.md` capturing decisions made this session
- `/vault-scope` — check or change whether a project uses this vault (or another one)
EOF
  fi

  (cd "$path" && git init -q 2>/dev/null; git add -A && git commit -q -m "initial vault scaffold" 2>/dev/null)
  echo "Scaffolded vault at $path"
}
