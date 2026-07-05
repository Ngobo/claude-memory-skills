#!/bin/bash
# resolve-vault.sh — shared vault-scope resolution for Memory Skills.
#
# Source this file, then call `resolve_vault_scope` to set:
#   VAULT_SCOPE          "shared" | "private"
#   VAULT_DIR            absolute path to the resolved vault
#   VAULT_PROJECT        basename of the directory the marker was found in (or $PWD)
#   VAULT_GRAPHIFY       "true" | "false" | "" (from the marker, if project-init recorded a choice)
#   VAULT_MARKER_FOUND   "1" if a .claude/vault-scope.json was found walking up, "" otherwise
#
# Resolution walks up from $PWD looking for .claude/vault-scope.json, stopping after
# checking the first directory that is itself a git repo root (never climbs past it).
# If nothing is found, defaults to a private vault at ~/vault.

resolve_vault_scope() {
  local dir="$PWD"
  VAULT_MARKER_FOUND=""
  VAULT_GRAPHIFY=""

  while true; do
    if [ -f "$dir/.claude/vault-scope.json" ]; then
      VAULT_MARKER_FOUND=1
      VAULT_PROJECT=$(basename "$dir")

      local parsed
      parsed=$(python3 -c "
import json
d = json.load(open('$dir/.claude/vault-scope.json'))
g = d.get('graphify', '')
print(d.get('scope',''))
print(d.get('vault',''))
print(str(g).lower() if isinstance(g, bool) else g)
" 2>/dev/null)
      VAULT_SCOPE=$(sed -n '1p' <<< "$parsed")
      local raw_vault
      raw_vault=$(sed -n '2p' <<< "$parsed")
      VAULT_GRAPHIFY=$(sed -n '3p' <<< "$parsed")

      case "$raw_vault" in
        "~"*) raw_vault="$HOME${raw_vault#\~}" ;;
      esac
      case "$raw_vault" in
        /*) VAULT_DIR="$raw_vault" ;;
        *) VAULT_DIR=$(cd "$dir/$raw_vault" 2>/dev/null && pwd) ;;
      esac
      return 0
    fi

    if [ -d "$dir/.git" ]; then
      break
    fi
    if [ "$dir" = "/" ]; then
      break
    fi
    dir=$(dirname "$dir")
  done

  VAULT_SCOPE="private"
  VAULT_DIR="$HOME/vault"
  VAULT_PROJECT=$(basename "$PWD")
}
