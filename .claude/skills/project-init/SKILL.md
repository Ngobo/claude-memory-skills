# /project-init

Scaffold Memory Skills boilerplate into this repo's CLAUDE.md: vault wiring, and
(optionally) Graphify code-map integration. Run from the project repo root. Safe to
re-run — guards against duplication and won't re-ask questions already answered.

## Steps

### 1. Ensure vault scope is established

```bash
source ~/.claude/skills/lib/resolve-vault.sh
resolve_vault_scope
echo "Scope: $VAULT_SCOPE — Vault: $VAULT_DIR — Project: $VAULT_PROJECT"
```

If `$VAULT_MARKER_FOUND` is empty (no `.claude/vault-scope.json` in this repo yet),
invoke the `vault-scope` skill now (Skill tool, `skill: "vault-scope"`) to establish it,
then re-run the resolution above before continuing.

### 2. Ensure this project's chats folder exists in the vault

```bash
source ~/.claude/skills/lib/resolve-vault.sh
resolve_vault_scope
mkdir -p "$VAULT_DIR/chats/$VAULT_PROJECT"
echo "$VAULT_DIR/chats/$VAULT_PROJECT/ ready."
```

### 3. Decide Graphify — ask once, remember the answer

```bash
source ~/.claude/skills/lib/resolve-vault.sh
resolve_vault_scope
python3 -c "
import json
d = json.load(open('.claude/vault-scope.json'))
print('set' if 'graphify' in d else 'unset')
"
```

If the result is `unset`, ask via AskUserQuestion:

> "Enable Graphify code-map integration for this repo? It gives Claude a queryable
> knowledge graph of the codebase instead of re-reading files every session, but adds a
> pip install, an LLM API key requirement for semantic extraction, and a few git/hook
> integrations."
> Options: "Yes, enable Graphify" / "No, skip Graphify"

Record the answer immediately, regardless of which branch runs next:
```bash
python3 -c "
import json
p = '.claude/vault-scope.json'
d = json.load(open(p))
d['graphify'] = ANSWER_TRUE_OR_FALSE
json.dump(d, open(p, 'w'), indent=2)
"
```
(Replace `ANSWER_TRUE_OR_FALSE` with Python `True`/`False` matching the user's choice.)

If the result was already `set` (marker already has a `graphify` key from a previous
run), don't ask again — just use the recorded value for the steps below.

### 4. If Graphify is enabled, wire it up

Only run this section when the resolved `graphify` value is `true`. Skip entirely
(no pip install, no CLAUDE.md sections, no hooks) when `false`.

**4a. Install Graphify:**
```bash
python3 -c "import graphify" 2>/dev/null \
  && echo "graphify already installed." \
  || pip install graphifyy -q --break-system-packages
```
(The PyPI package is genuinely named `graphifyy` — double y — not a typo.)

**4b. Add graphify section to CLAUDE.md if missing:**
```bash
grep -q 'graphify-out' CLAUDE.md 2>/dev/null || cat >> CLAUDE.md << 'EOF'

## graphify

This project has a graphify knowledge graph at graphify-out/.

Rules:
- Before answering architecture or codebase questions, read graphify-out/GRAPH_REPORT.md for god nodes and community structure
- If graphify-out/wiki/index.md exists, navigate it instead of reading raw files
- After modifying code files in this session, run `graphify update .` to keep the graph current (AST-only, no API cost)
EOF
echo "graphify section added."
```

**4c. Add Context Navigation section to CLAUDE.md if missing:**
```bash
grep -q 'Context Navigation' CLAUDE.md 2>/dev/null || cat >> CLAUDE.md << 'EOF'

## Context Navigation (Graphify)

### 3-Layer Query Rule
1. **First:** query `graphify-out/graph.json` or `graphify-out/wiki/index.md`
   to understand code structure and connections
2. **Second:** query the vault for decisions, progress, and project context
3. **Third:** only read raw code files when editing
   or when the first two layers don't have the answer

### When to rebuild the graph
- After structural changes (new modules, major refactors)
- Command: `graphify . --update` (only processes modified files)
- The graph is persistent — NO need to rebuild every session

### Do NOT
- Don't manually modify files inside `graphify-out/`
- Don't re-read the entire codebase if the graph already has the information
EOF
echo "Context Navigation section added."
```

**4d. Verify graph exists:**
```bash
[ -f "graphify-out/graph.json" ] \
  && echo "graph.json OK." \
  || echo "WARNING: graphify-out/graph.json missing — run /graphify . to build it."
```

**4e. Register graphify PreToolUse hook if graphify is installed:**
```bash
python3 -c "import graphify" 2>/dev/null && {
  python3 -c "
from graphify.__main__ import _install_claude_hook
from pathlib import Path
_install_claude_hook(Path('.'))
"
  echo "graphify PreToolUse hook registered in .claude/settings.json"
} || echo "graphify not installed — skipping hook registration (run /graphify . first)"
```
This registers a hook that fires before grep/find/rg Bash calls and nudges toward
querying the graph instead. Note: `graphify claude install` skips this if CLAUDE.md
already has a graphify section, so `_install_claude_hook` is called directly.

**4f. Register graphify git hooks if graph exists:**
```bash
if [ -d "graphify-out" ]; then
  graphify hook install
  echo "graphify git hooks registered (post-commit, post-checkout)"
else
  echo "skipping git hooks — no graph yet (run /graphify . first)"
fi
```
Post-commit auto-rebuilds the graph (AST only, no LLM) after each commit; post-checkout
rebuilds on branch switches. Safe to re-run.

### 5. Add vault-wiring section to CLAUDE.md if missing

```bash
source ~/.claude/skills/lib/resolve-vault.sh
resolve_vault_scope
grep -q 'Memory Skills' CLAUDE.md 2>/dev/null || cat >> CLAUDE.md << EOF

## Memory Skills

This repo's vault scope: **$VAULT_SCOPE** (\`$VAULT_DIR\`) — see \`.claude/vault-scope.json\`.

**On session start:** \`/resume\` — loads recent context from \`$VAULT_DIR/chats/$VAULT_PROJECT/\`

**On session end:** \`/save\` — writes decisions to \`$VAULT_DIR/chats/$VAULT_PROJECT/YYYY-MM-DD-HH-MM.md\`

**To change scope:** \`/vault-scope\`
EOF
echo "Memory Skills section added."
```

### 6. Done

Report what was added vs. already present, and the resolved Graphify decision.
