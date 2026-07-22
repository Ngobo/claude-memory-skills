# /save

Write end-of-session decisions to the vault. Resolves whether this project uses the
shared team vault or your personal vault automatically.

## Steps

1. Resolve scope and confirm the vault exists:
```bash
source ~/.claude/skills/lib/resolve-vault.sh
resolve_vault_scope
echo "Scope: $VAULT_SCOPE — Vault: $VAULT_DIR — Project: $VAULT_PROJECT"
[ -z "$VAULT_MARKER_FOUND" ] && echo "No .claude/vault-scope.json found in this repo — defaulting to private vault. Run /vault-scope to set this project's scope explicitly."
[ -d "$VAULT_DIR/.git" ] || echo "Vault not found at $VAULT_DIR — run /vault-scope to set it up."
```
Stop if the vault directory doesn't exist.

2. Summarize the session — include:
   - What was done (bullet list of changes/tasks)
   - Key decisions (architectural choices, tradeoffs)
   - Open questions / next steps

3. Check whether the current session's ID is available:
```bash
echo "${CLAUDE_CODE_SESSION_ID:-}"
```
If that printed a non-empty value, write to
`$VAULT_DIR/chats/$VAULT_PROJECT/YYYY-MM-DD-HH-MM.md` **with** a frontmatter block
(replace `<value>` with the exact value just printed):

```markdown
---
session_id: "<value>"
---

# Session YYYY-MM-DD

## What we did
- ...

## Key decisions
- ...

## Open questions / next steps
- ...
```

If it printed nothing (this is an internal, undocumented env var — it may not always
be set), write the note **without** the frontmatter block, exactly as before:

```markdown
# Session YYYY-MM-DD

## What we did
- ...

## Key decisions
- ...

## Open questions / next steps
- ...
```

4. Commit and push:
```bash
source ~/.claude/skills/lib/resolve-vault.sh
resolve_vault_scope
TIMESTAMP=$(date +"%Y-%m-%d-%H-%M")
mkdir -p "$VAULT_DIR/chats/$VAULT_PROJECT"
cd "$VAULT_DIR" \
  && git add "chats/$VAULT_PROJECT/$TIMESTAMP.md" \
  && git commit -m "save $VAULT_PROJECT session $(date +%Y-%m-%d)" \
  && git push
```
