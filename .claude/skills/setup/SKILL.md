# /setup

One-time setup for Memory Skills. Run from this repo's root. Safe to re-run.

## Steps (execute in order)

### 1. Install global skills + shared lib

```bash
mkdir -p ~/.claude/skills/resume ~/.claude/skills/save ~/.claude/skills/project-init ~/.claude/skills/vault-scope ~/.claude/skills/lib
cp .claude/skills/resume/SKILL.md ~/.claude/skills/resume/SKILL.md
cp .claude/skills/save/SKILL.md ~/.claude/skills/save/SKILL.md
cp .claude/skills/project-init/SKILL.md ~/.claude/skills/project-init/SKILL.md
cp .claude/skills/vault-scope/SKILL.md ~/.claude/skills/vault-scope/SKILL.md
cp .claude/skills/lib/resolve-vault.sh ~/.claude/skills/lib/resolve-vault.sh
cp .claude/skills/lib/scaffold-vault.sh ~/.claude/skills/lib/scaffold-vault.sh
echo "Global skills installed: resume, save, project-init, vault-scope."
```

Graphify is not installed here — it's opt-in per repo via `/project-init`, which asks
once and installs only if you say yes.

### 2. Register skill triggers in ~/.claude/CLAUDE.md

```bash
grep -q 'skill: "vault-scope"' ~/.claude/CLAUDE.md 2>/dev/null || cat >> ~/.claude/CLAUDE.md << 'EOF'

## Memory Skills

- **resume** (`~/.claude/skills/resume/SKILL.md`) — load recent vault context at session start. Trigger: `/resume`
  When the user types `/resume`, invoke the Skill tool with `skill: "resume"` before doing anything else.

- **save** (`~/.claude/skills/save/SKILL.md`) — write end-of-session notes to the vault. Trigger: `/save`
  When the user types `/save`, invoke the Skill tool with `skill: "save"` before doing anything else.

- **project-init** (`~/.claude/skills/project-init/SKILL.md`) — scaffold vault + (optional) Graphify wiring into a new repo's CLAUDE.md. Trigger: `/project-init`
  When the user types `/project-init`, invoke the Skill tool with `skill: "project-init"` before doing anything else.

- **vault-scope** (`~/.claude/skills/vault-scope/SKILL.md`) — check or change whether a project uses a shared vault or a personal one. Trigger: `/vault-scope`
  When the user types `/vault-scope`, invoke the Skill tool with `skill: "vault-scope"` before doing anything else.
EOF
echo "~/.claude/CLAUDE.md updated."
```

### 3. Generate a parent CLAUDE.md for shared multi-project layouts (optional)

If this machine hosts a shared vault that lives inside a parent folder alongside sibling
project repos (e.g. a team layout like `team/{app,api,vault}`), this step generates a
local, untracked CLAUDE.md one level up documenting Memory Skills — so it auto-loads for
any session started under those siblings. No repo is needed at that parent level: Claude
Code loads CLAUDE.md by walking the full filesystem ancestor chain, regardless of git
boundaries.

This only applies if the *current directory* (where you're running `/setup` from) is
itself a shared vault — i.e. it has its own self-referential `.claude/vault-scope.json`
with `"scope": "shared"` pointing at itself. If that's not your situation, this step is a
no-op.

```bash
if [ -f .claude/vault-scope.json ]; then
  SCOPE=$(python3 -c "import json;print(json.load(open('.claude/vault-scope.json')).get('scope',''))" 2>/dev/null)
  VAULT_RAW=$(python3 -c "import json;print(json.load(open('.claude/vault-scope.json')).get('vault',''))" 2>/dev/null)
else
  SCOPE=""
fi

if [ "$SCOPE" = "shared" ] && [ "$VAULT_RAW" = "." ]; then
  PARENT=$(dirname "$PWD")
  SIBLINGS=""
  for d in "$PARENT"/*/; do
    d="${d%/}"
    [ "$d" = "$PWD" ] && continue
    [ -d "$d/.git" ] && SIBLINGS="$SIBLINGS $(basename "$d")"
  done

  if [ -n "$SIBLINGS" ]; then
    cat > "$PARENT/CLAUDE.md" << EOF
# Memory Skills

This file is generated locally by \`/setup\` and lives at the parent folder of the shared
vault at \`$PWD\` (not tracked in any repo — Claude Code loads CLAUDE.md by walking up the
directory tree, so this auto-loads for any session started in:$SIBLINGS).

## Memory Skills

- \`/resume\` — load recent session context at the start of a conversation
- \`/save\` — write end-of-session decisions to the vault
- \`/project-init\` — scaffold a repo's CLAUDE.md with vault wiring and (optionally) Graphify
- \`/vault-scope\` — check or change whether a project uses this shared vault or a personal one

Skill source: https://github.com/Ngobo/claude-memory-skills

Each sibling repo should have a \`.claude/vault-scope.json\` committed to it (run
\`/vault-scope shared\` from inside it) pointing back at \`$PWD\`, so \`/resume\` and
\`/save\` share notes with the team instead of falling back to a personal vault. Run
\`/vault-scope status\` in any repo to check its current resolution.
EOF
    echo "$PARENT/CLAUDE.md generated (siblings:$SIBLINGS)."
  else
    echo "No sibling repos found next to this vault — skipping parent CLAUDE.md."
  fi
else
  echo "This directory isn't a self-referential shared vault — skipping parent CLAUDE.md step."
fi
```

### 4. Install chat-import scripts

These are general-purpose too — not tied to any particular vault — so they install
globally alongside the skills themselves:

```bash
mkdir -p ~/.claude/skills/scripts
cp scripts/claude_to_obsidian.py ~/.claude/skills/scripts/claude_to_obsidian.py
cp scripts/sync_obsidian.sh ~/.claude/skills/scripts/sync_obsidian.sh
chmod +x ~/.claude/skills/scripts/sync_obsidian.sh
echo "Chat-import scripts installed to ~/.claude/skills/scripts/."
```

Check whether the extractor fork is installed (it adds the `cwd`/`project` metadata
the import script needs for routing — the plain upstream extractor doesn't have it):

```bash
python3 -c "import extract_claude_logs" 2>/dev/null \
  && echo "claude-conversation-extractor already installed." \
  || echo "Not installed. Chat import won't work until you run: pip install git+https://github.com/Ngobo/claude-conversation-extractor.git@add-cwd-project-metadata"
```

Don't install it automatically — just report its presence/absence, same as Graphify.

### 5. Offer to schedule automatic chat import (optional, asked once)

Check whether a cron entry for this already exists:

```bash
crontab -l 2>/dev/null | grep -q "sync_obsidian.sh" && echo "already scheduled" || echo "not scheduled"
```

- If **already scheduled**, just refresh the path in case it changed (e.g. an earlier
  install pointed at a repo checkout instead of the global location), without asking
  again:
  ```bash
  (crontab -l 2>/dev/null | grep -v "sync_obsidian.sh"; echo "0 22 * * * $HOME/.claude/skills/scripts/sync_obsidian.sh") | crontab -
  echo "Cron entry refreshed (daily 22:00)."
  ```
- If **not scheduled**, ask via AskUserQuestion:
  > "Schedule automatic daily chat import via cron (22:00)? Requires the extractor fork
  > from step 4 — sessions won't import until that's installed, but scheduling it now
  > is harmless either way." Options: "Yes, schedule it" / "No, skip for now"
  - *Yes* → run the same crontab command as above.
  - *No* → skip. Mention `/setup` can be re-run later to add it.

### 6. Done

Report what was done vs. already in place. Tell the user:
- `/resume`, `/save`, `/vault-scope` work from any project directory (shared or private,
  resolved automatically).
- Run `/vault-scope shared [path]` or `/vault-scope private` to explicitly set a repo's
  scope, then `/project-init` to scaffold its CLAUDE.md.
- Whether chat import is fully wired up (extractor fork installed + cron scheduled),
  partially (one but not the other), or not at all — and what to run to finish it.
