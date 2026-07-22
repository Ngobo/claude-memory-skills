# claude-memory-skills

Claude Code skills that give Claude persistent memory across sessions, stored in a
plain-markdown, Obsidian-compatible vault — with automatic, per-project resolution
between a **shared team vault** and a **personal/private vault**. No config beyond one
small marker file per repo.

## Table of contents

- [The problem](#the-problem)
- [How it works](#how-it-works)
- [Quick start](#quick-start)
- [Skills reference](#skills-reference)
  - [`/setup`](#setup)
  - [`/vault-scope`](#vault-scope)
  - [`/project-init`](#project-init)
  - [`/resume`](#resume)
  - [`/save`](#save)
- [The `vault-scope.json` marker](#the-vault-scopejson-marker)
- [Vault layout](#vault-layout)
- [Multi-project / team setups](#multi-project--team-setups)
- [Optional: Graphify integration](#optional-graphify-integration)
- [Optional: automatic chat import](#optional-automatic-chat-import)
- [Repo layout](#repo-layout)
- [FAQ / troubleshooting](#faq--troubleshooting)
- [License](#license)

## The problem

Claude Code starts every session with a blank slate. Left alone, you re-explain the
same architecture, the same decisions, the same "why did we do it this way" every time
you open a new session. `CLAUDE.md` covers static facts; it doesn't cover *history* —
what was decided last Tuesday, what's still open, what you tried that didn't work.

These skills solve that with a vault: a folder of plain markdown notes, one per
session, that Claude reads at the start of a conversation (`/resume`) and writes to at
the end (`/save`). The twist is **scope**: some projects want that vault shared with a
team (so notes are visible to everyone via git), others want it private to you. This
repo makes both work with the same commands, resolved automatically per project.

## How it works

Every skill call resolves a single question first: *which vault, and is it shared or
private?* That resolution walks up from the current directory looking for
`.claude/vault-scope.json`, stopping after the first git repo root it finds (it never
walks past a repo boundary). If no marker is found anywhere, it defaults to a private
vault at `~/vault`, scaffolding it automatically the first time it's needed.

```
                    resolve_vault_scope()
                            │
              found .claude/vault-scope.json?
                 │                        │
                yes                       no
                 │                        │
        use its scope + vault      hit a .git root without
        (shared or private)        finding one?
                                          │
                                         yes
                                          │
                            default: private, ~/vault
                            (scaffolded on first use)
```

This means the exact same `/resume` and `/save` commands work identically whether
you're in a team repo that shares notes with colleagues over git, or a one-off personal
project where you just want a private journal of decisions and context.

## Quick start

```bash
git clone https://github.com/Ngobo/claude-memory-skills.git
cd claude-memory-skills
claude
```

Then, inside the Claude Code session:

```
/setup
```

That installs all five skills to `~/.claude/skills/` and wires up trigger instructions
in `~/.claude/CLAUDE.md`. From then on, `/resume`, `/save`, `/vault-scope`, and
`/project-init` work from **any** project directory on this machine — you don't need
this repo checked out anywhere else, and you don't need to re-run `/setup` unless you
want to pick up an update to the skills themselves.

To wire up a specific project:

```
cd ~/code/some-project
/vault-scope private          # or: /vault-scope shared ../path/to/vault
/project-init                 # scaffolds CLAUDE.md, offers Graphify
```

## Skills reference

### `/setup`

One-time (per machine) install step. Safe to re-run — it won't duplicate anything
already in place.

1. Copies all skill files + the shared `lib/` helpers into `~/.claude/skills/`.
2. Appends a `## Memory Skills` section to `~/.claude/CLAUDE.md` telling Claude to
   invoke each skill on its trigger command (only if not already present).
3. If run from inside a **self-referential shared vault** (see below) that sits next
   to sibling project repos, generates a local `CLAUDE.md` one directory up,
   documenting the setup for anyone working in those sibling repos. This step is a
   no-op for a normal install — most people won't hit it.
4. Installs the chat-import scripts to `~/.claude/skills/scripts/`, and checks whether
   the extractor fork (see [chat import](#optional-automatic-chat-import) below) is
   installed — reporting its presence/absence without installing it automatically.
5. Offers to schedule daily automatic chat import via cron. Asked once — if you
   decline, re-running `/setup` later asks again (the crontab itself is the record of
   whether you've already said yes, independent of whether the extractor is installed
   yet); if you accept, later re-runs just silently refresh the script path.

Re-run `/setup` any time you pull an update to this repo, to refresh the installed
copies in `~/.claude/skills/`.

### `/vault-scope`

Check or change whether the current repo uses a shared vault or a personal one.
Deliberately low-friction — no subcommand syntax to memorize for the common case.

| Command | Effect |
|---|---|
| `/vault-scope` | Shows current resolution, then asks what to do (keep / switch to shared / switch to private) |
| `/vault-scope shared [path]` | Sets this repo to shared scope. `path` optional — if omitted, looks for a `vault/` sibling one directory up; if none is found, offers to point at an existing shared vault or scaffold a new one |
| `/vault-scope private` | Sets this repo to private scope, defaulting to `~/vault` (scaffolded automatically if it doesn't exist yet) |
| `/vault-scope status` | Read-only — just prints the current resolution, no prompts |

Switching scope previews exactly what would move — only files from
`chats/<project>/` (including `imported/`) missing at the destination, so anything
already copied from an earlier switch isn't re-touched — and asks before copying,
every time, in both directions. private→shared can expose previously-private notes
to teammates, so this is never silent; declining still lets the scope switch itself
go through, and the source is never modified or deleted either way.

### `/project-init`

Scaffolds a repo's `CLAUDE.md` with vault wiring, and — the first time it's run for
that repo — asks whether to enable [Graphify](https://github.com/safishamsi/graphify)
code-map integration. Your answer is recorded in `vault-scope.json` so you're never
asked twice, and every subsequent run only fills in what's missing.

If the repo has no `vault-scope.json` yet, `/project-init` invokes `/vault-scope`
first to establish one.

### `/resume`

Run at the start of a session. Resolves scope, `git pull`s the vault if it's a shared
one, then reads the last 3–5 session notes for the current project (both hand-written
`/save` notes and anything auto-imported — see [chat import](#optional-automatic-chat-import)
below) and presents a brief: recent work, open items, and — if Graphify is enabled —
an architecture summary from the code graph.

### `/save`

Run at the end of a session. Writes a timestamped markdown note
(`chats/<project>/YYYY-MM-DD-HH-MM.md`) summarizing what was done, key decisions, and
open questions, then commits and pushes it if the vault is shared.

## The `vault-scope.json` marker

Committed to git at `.claude/vault-scope.json` in the root of each project repo:

```json
{
  "scope": "shared",
  "vault": "../vault",
  "graphify": true
}
```

| Field | Meaning |
|---|---|
| `scope` | `"shared"` or `"private"` |
| `vault` | Path to the vault. Relative paths resolve against the repo root (portable across machines/checkouts); `~/...` and absolute paths both work |
| `graphify` | `true`/`false` — whether `/project-init` has Graphify enabled for this repo. Absent until `/project-init` has asked once |

A vault can also be **self-referential** — a vault repo whose own `vault-scope.json`
points at itself (`"vault": "."`). This is what lets sessions run *inside* the vault
repo (e.g. while tweaking these skills) stay shared with the team instead of falling
back to a private vault by default.

## Vault layout

A vault (shared or private) is just a folder — created automatically by
`/vault-scope` or `/setup` if it doesn't exist yet:

```
vault/
├── CLAUDE.md          # instructions Claude reads when working in the vault itself
├── chats/
│   └── <project>/
│       ├── 2026-07-04-14-30.md      # hand-written /save notes
│       └── imported/                # auto-imported full transcripts (optional, see below)
├── permanent/         # your own consolidated notes, if you keep any
├── inbox/             # quick unsorted capture
├── fleeting/
├── logs/
└── references/
```

Nothing beyond `chats/` is required by the skills themselves — the rest are just
Zettelkasten-style conventions you're free to use, ignore, or rename.

## Multi-project / team setups

If several repos share one vault (a team layout, e.g. `team/{app,api,vault}` with
`vault/` as a sibling), give each repo a `shared` marker pointing at the vault:

```bash
cd team/app && /vault-scope shared ../vault
cd team/api && /vault-scope shared ../vault
```

And give the vault repo itself a self-referential marker so work done *on* the vault
stays visible to the team too:

```json
// team/vault/.claude/vault-scope.json
{ "scope": "shared", "vault": ".", "graphify": false }
```

Once that's in place, running `/setup` from inside the vault repo will also generate
`team/CLAUDE.md` (untracked, machine-local) documenting Memory Skills for anyone who
opens a session anywhere under `team/` — no shared repo needed at that parent level,
since Claude Code loads `CLAUDE.md` by walking the full filesystem ancestor chain
regardless of git boundaries.

## Optional: Graphify integration

[Graphify](https://github.com/safishamsi/graphify) builds a queryable knowledge graph
of a codebase so Claude doesn't have to re-read every file every session. It's
entirely opt-in per repo: `/project-init` asks once, and everything (the `pip install`,
`CLAUDE.md` sections, PreToolUse hook, git hooks) is skipped if you say no. Nothing in
the core memory skills depends on it.

## Optional: automatic chat import

Hand-written `/save` notes are a *summary*. If you also want full, searchable
transcripts of every session imported into the vault automatically, `/setup` handles
most of this for you (step 4/5 — see [`/setup`](#setup) above):

- It installs `scripts/claude_to_obsidian.py` and `scripts/sync_obsidian.sh` from this
  repo to `~/.claude/skills/scripts/` — general-purpose, not tied to any one vault.
- It checks whether the extractor fork is installed (see below) and tells you if not,
  without installing it automatically.
- It offers to schedule a daily cron job (asked once; silently refreshed on later
  `/setup` re-runs if you already said yes).

The one manual step `/setup` won't do for you — installing the extractor fork, since
that's a systemwide pip install rather than something scoped to `~/.claude/`:

```bash
pip install git+https://github.com/Ngobo/claude-conversation-extractor.git@add-cwd-project-metadata
```

This fork adds `cwd`/`project` metadata to exports, which `claude_to_obsidian.py` needs
for routing — the plain upstream extractor doesn't include it. Once installed,
`sync_obsidian.sh` reads each session's `cwd`, resolves it through the same
`vault-scope.json` logic as the skills above, tags it, and writes it to
`chats/<project>/imported/` in the correct vault — shared and private sessions get
split correctly in a single run. Idempotent: a session already imported is skipped,
not duplicated, on every re-run (cron or manual).

After processing, each touched vault that's a git repo gets its `chats/` changes
committed automatically (scoped to `chats/` only, so any unrelated in-progress edits
elsewhere in the vault are left alone). Vaults that aren't git repos are skipped
silently — nothing errors, files are still written, just not committed. This never
pushes; pushing a shared vault stays a separate, explicit step, since auto-pushing raw
imported transcripts to a team-visible repo unattended is a bigger call than committing
locally.

## Repo layout

```
claude-memory-skills/
├── .claude/skills/
│   ├── setup/SKILL.md
│   ├── vault-scope/SKILL.md
│   ├── project-init/SKILL.md
│   ├── resume/SKILL.md
│   ├── save/SKILL.md
│   └── lib/
│       ├── resolve-vault.sh     # scope-resolution algorithm, shared by every skill
│       └── scaffold-vault.sh    # creates a new vault's folder structure + git init
├── scripts/
│   ├── claude_to_obsidian.py    # tags + routes exported sessions into the right vault
│   └── sync_obsidian.sh         # driver: export via claude-extract, then process
├── README.md
└── LICENSE
```

## FAQ / troubleshooting

**Do I need to keep this repo checked out to use the skills?**
No. `/setup` copies everything into `~/.claude/skills/`, which is what actually runs.
Keep this repo around only so you can `git pull` updates and re-run `/setup`.

**I ran `/vault-scope shared` but there's no vault nearby.**
You'll be asked whether to point at an existing shared vault (enter its path) or
scaffold a brand new one at a location you choose. Nothing is created silently.

**What happens to notes if I switch a repo from shared to private (or back)?**
`/vault-scope` shows you exactly which notes would move (only ones missing at the
destination — nothing already-copied gets touched again) and asks before copying.
Declining still switches the scope; the notes just stay only in the old vault. The
old copy is never deleted or modified either way, so you can flip a project between
shared and private any number of times without losing or duplicating notes.

**Does this require Obsidian?**
No. Everything is plain markdown with YAML frontmatter. Obsidian (or any markdown
editor, or nothing at all) is an optional viewer, not a dependency.

## License

MIT — see [LICENSE](LICENSE).
