# claude-memory-skills

Claude Code skills that give Claude persistent memory across sessions via an
[Obsidian](https://obsidian.md)-style vault — with automatic support for both a
**shared team vault** and a **personal/private vault**, resolved per-project.

## What's in here

- `/resume` — load recent session context at the start of a conversation
- `/save` — write end-of-session decisions to the vault
- `/project-init` — scaffold a repo's `CLAUDE.md` with vault wiring, and (optionally)
  [Graphify](https://github.com/safishamsi/graphify) code-map integration
- `/vault-scope` — check or change whether a project uses a shared vault or a
  personal one, and copy notes over when switching
- `/setup` — one-time install of all of the above

## How scope resolution works

Each project repo gets a `.claude/vault-scope.json`, committed to git:

```json
{ "scope": "shared", "vault": "../vault", "graphify": true }
```

`/resume`, `/save`, and `/project-init` all resolve which vault to use by walking up
from the current directory looking for this marker, stopping after the first git repo
root. If nothing is found, they default to a private vault at `~/vault` (created
automatically on first use).

This means the same skills work identically whether you're in a team repo that shares
notes with colleagues, or a personal project where you want a private journal of
decisions and context — no per-project configuration beyond the one marker file.

## Companion: automatic chat import

A separate tool, [claude-conversation-extractor (fork)](https://github.com/Ngobo/claude-conversation-extractor),
adds `cwd`/`project` metadata to exported Claude Code conversations, which lets a
cron job route each session's full transcript into the right vault automatically. See
that repo, plus `scripts/claude_to_obsidian.py` in your vault, for the import pipeline.

## Install

```bash
git clone https://github.com/Ngobo/claude-memory-skills.git
cd claude-memory-skills
claude
```

Then run `/setup`. That's it — `/resume`, `/save`, `/vault-scope`, and `/project-init`
now work from any project directory on this machine.

To wire up a specific repo (set its scope and, optionally, Graphify):

```
/vault-scope shared ../vault      # or: /vault-scope private
/project-init
```
