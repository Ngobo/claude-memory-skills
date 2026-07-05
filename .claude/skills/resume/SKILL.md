# /resume

Load recent session context at the start of a conversation. Works from any project —
resolves whether this project uses the shared team vault or your personal vault
automatically.

## Steps

1. Resolve scope, confirm the vault exists, and pull latest:
```bash
source ~/.claude/skills/lib/resolve-vault.sh
resolve_vault_scope
echo "Scope: $VAULT_SCOPE — Vault: $VAULT_DIR — Project: $VAULT_PROJECT"
[ -z "$VAULT_MARKER_FOUND" ] && echo "No .claude/vault-scope.json found in this repo — defaulting to private vault. Run /vault-scope to set this project's scope explicitly."
if [ -d "$VAULT_DIR/.git" ]; then
  (cd "$VAULT_DIR" && git pull)
else
  echo "Vault not found at $VAULT_DIR — run /vault-scope to set it up."
fi
```
Stop if the vault directory doesn't exist.

2. Find and read last 3-5 session notes for this project (both hand-written `/save` notes
   and any auto-imported chat notes):
```bash
source ~/.claude/skills/lib/resolve-vault.sh
resolve_vault_scope
ls -t "$VAULT_DIR/chats/$VAULT_PROJECT"/*.md "$VAULT_DIR/chats/$VAULT_PROJECT/imported"/*.md 2>/dev/null | head -5
```
Read each file, most recent first.

3. If Graphify is enabled for this project (`$VAULT_GRAPHIFY` = `true`), read the
   architecture snapshot (summary only — not the full report):
```bash
source ~/.claude/skills/lib/resolve-vault.sh
resolve_vault_scope
if [ "$VAULT_GRAPHIFY" = "true" ]; then
  head -80 graphify-out/GRAPH_REPORT.md 2>/dev/null || echo "No graph yet — run /graphify . to build it."
fi
```

4. Present a context brief to the user:
   - **Recent work** — what was done in the last sessions
   - **Open items** — anything unresolved from last session
   - **Architecture** — god nodes and top communities from GRAPH_REPORT.md header (only if Graphify is enabled for this project)
