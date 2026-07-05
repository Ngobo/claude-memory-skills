# /vault-scope

Check or change whether this project uses the shared team vault or a personal/private
vault. Writes `.claude/vault-scope.json` in the current repo (commit it to git so
teammates see the same resolution).

## Usage
- `/vault-scope` — show current resolution, offer to change it
- `/vault-scope shared [path]` — set this repo to shared scope (path optional)
- `/vault-scope private` — set this repo to private scope (defaults to `~/vault`)
- `/vault-scope status` — read-only, just print the resolution, no prompts, no writes

## Steps

### 1. Always resolve current state first

```bash
source ~/.claude/skills/lib/resolve-vault.sh
resolve_vault_scope
echo "Current scope: $VAULT_SCOPE"
echo "Current vault: $VAULT_DIR"
echo "Marker found in this repo: ${VAULT_MARKER_FOUND:-no (using default)}"
```

### 2. `status` — stop here

If the user ran `/vault-scope status`, just report the values from step 1 and stop.
No prompts, no writes.

### 3. No arguments — ask what to do

If the user ran plain `/vault-scope` with no arguments, ask via AskUserQuestion:

> "This project currently resolves to **$VAULT_SCOPE** scope (vault: $VAULT_DIR). What
> would you like to do?"
> Options: "Keep as is" / "Switch to shared" / "Switch to private"

"Keep as is" → stop, nothing to change. Otherwise continue to step 4 with the target
scope the user picked. If the user instead ran `/vault-scope shared [path]` or
`/vault-scope private` directly, skip this prompt and go straight to step 4 with that
target scope.

### 4. Determine the target vault path

**Target = private:** default path is `~/vault`. If it doesn't exist yet:
```bash
source ~/.claude/skills/lib/scaffold-vault.sh
scaffold_vault_if_missing ~/vault
```

**Target = shared:** if the user gave an explicit path argument, use it directly (skip
the search below). Otherwise look for the nearest ancestor directory (above the current
repo) that itself contains a `vault/` subdirectory which is a git repo:
```bash
dir=$(dirname "$PWD")
found=""
while [ "$dir" != "/" ]; do
  if [ -d "$dir/vault/.git" ]; then
    found="$dir/vault"
    break
  fi
  dir=$(dirname "$dir")
done
echo "${found:-not found}"
```

- If found, use it.
- If **not found**, ask via AskUserQuestion:
  > "No shared vault found near this project. What would you like to do?"
  > Options: "Enter the path to an existing shared vault" / "Create a new shared vault here" / "Cancel"
  - *Enter existing path* → user picks Other and types a path. Verify it's a real
    directory with a `.git` inside; if not, say so and stop without writing anything.
  - *Create new* → user picks Other and types where. Run the same scaffolding helper
    used for private vaults:
    ```bash
    source ~/.claude/skills/lib/scaffold-vault.sh
    scaffold_vault_if_missing "<path the user gave>"
    ```
  - *Cancel* → stop, no changes made.

### 5. Always copy notes between vaults when the vault is actually changing

This always runs, unconditionally — no prompt, no yes/no question — on first-time
setup **and** on every subsequent switch of an already-scoped repo. A project that
flips private → shared → private → shared over its lifetime must not lose or
duplicate notes at any point in that history, so this is not optional and not
gated on asking the user.

```bash
source ~/.claude/skills/lib/resolve-vault.sh
resolve_vault_scope
OLD_VAULT="$VAULT_DIR"
OLD_PROJECT="$VAULT_PROJECT"
```

(`$OLD_VAULT`/`$OLD_PROJECT` are the state resolved in step 1, i.e. *before* any
change — capture them again here since step 4 may have run other commands since.)

Compare `$OLD_VAULT` against the target vault path determined in step 4. If they
resolve to the same directory, skip this step — nothing to copy. Otherwise, merge
`chats/<project>/` (including any `imported/` subfolder) from the old vault into the
new one:

```bash
if [ -d "$OLD_VAULT/chats/$OLD_PROJECT" ]; then
  mkdir -p "<new vault>/chats/<project>"
  cp -r --update=none "$OLD_VAULT/chats/$OLD_PROJECT/." "<new vault>/chats/<project>/"
  echo "Copied chats/$OLD_PROJECT/ from $OLD_VAULT to <new vault>."
else
  echo "No existing notes at $OLD_VAULT/chats/$OLD_PROJECT/ — nothing to copy."
fi
```

`--update=none` (no-clobber) means files already present at the destination from an
earlier switch are left untouched; only files missing there get copied. The source is
never modified or deleted. Because this always runs on every switch, a project's notes
accumulate correctly no matter how many times it flips scope over time — each switch
picks up exactly what's new since the last one.

### 6. Write the marker

Preserve the existing `graphify` key if one is already set (from `/project-init`).
Write the vault path in portable form: `../vault` style relative path when the target
vault is a direct sibling of the current repo, otherwise the `~/...` form when it's
under `$HOME`, otherwise an absolute path.

```bash
mkdir -p .claude
python3 - << 'PYEOF'
import json, pathlib, os

marker = pathlib.Path(".claude/vault-scope.json")
existing = json.load(open(marker)) if marker.exists() else {}

target_scope = "SHARED_OR_PRIVATE"          # fill in from step 3/4
target_vault_abs = "/absolute/path/to/vault"  # fill in from step 4

home = os.path.expanduser("~")
cwd_parent = os.path.dirname(os.getcwd())
if os.path.normpath(target_vault_abs) == os.path.normpath(os.path.join(cwd_parent, "vault")):
    portable = "../vault"
elif target_vault_abs.startswith(home):
    portable = "~" + target_vault_abs[len(home):]
else:
    portable = target_vault_abs

existing["scope"] = target_scope
existing["vault"] = portable
json.dump(existing, open(marker, "w"), indent=2)
existing.setdefault("graphify", existing.get("graphify", False))
print(json.dumps(existing, indent=2))
PYEOF
```

(Fill in `target_scope` / `target_vault_abs` with the actual resolved values from the
steps above before running — don't leave the placeholders literal.)

### 7. Report

Confirm the new scope + vault path, what was copied (or that there was nothing to
copy), and remind the user to `git add .claude/vault-scope.json && git commit` so
teammates see the same scope (for shared repos).
