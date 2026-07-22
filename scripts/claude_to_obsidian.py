#!/usr/bin/env python3
"""
Pipeline: Claude Code chats -> vault (auto-routed by project)

Adapted from https://github.com/lucasrosati/claude-code-memory-setup
Adds frontmatter, automatic tags, and wikilinks to existing notes.

Routing: each exported file's `cwd:` frontmatter (emitted by the forked
claude-conversation-extractor -- see README) is resolved to a target vault the same way
the vault-scope skill resolves it: walk up from `cwd` looking for `.claude/vault-scope.json`,
stopping after the first git repo root; default to a private vault at ~/vault if nothing
is found. Files without `cwd:` frontmatter (exports made with the un-forked extractor) are
skipped unless --vault-dir/--project are passed explicitly to force a single target.

After processing, each touched vault that is itself a git repo gets its chats/ changes
committed automatically (scoped to chats/ only, so unrelated in-progress edits elsewhere
in the vault are left alone). Vaults that aren't git repos are skipped silently. This
never pushes -- pushing to a shared vault stays a separate, explicit step.

Usage:
    python3 claude_to_obsidian.py --export-dir ~/claude-exports
    python3 claude_to_obsidian.py --export-dir ~/claude-exports --dry-run
    python3 claude_to_obsidian.py --export-dir ~/claude-exports --vault-dir /path/to/vault --project client  # force a single target

Options:
    --vault-dir     Force all files to one vault (skips auto-routing)
    --project       Force all files to one project folder (requires --vault-dir)
    --dry-run       Show what would happen without modifying anything
    --force         Reprocess even if the destination file already exists
    --origin        Force origin: code, web, or auto (default: auto)
    --no-wikilinks  Disable wikilink insertion
"""

import argparse
import json
import re
import subprocess
from datetime import datetime
from pathlib import Path

# ============================================================================
# CONFIGURATION — generic default tags, plus an example additive domain-specific layer
# ============================================================================

GENERIC_TAG_MAP = {
    "architecture": "architecture",
    "adr": "adr",
    "decision": "decision",
    "refactor": "refactoring",
    "migration": "migration",
    "upgrade": "upgrade",

    "database": "database",
    "sql": "database",

    "jwt": "auth",
    "authentication": "auth",
    "authorization": "auth",

    "api": "api",
    "rest": "api",
    "http": "api",
    "endpoint": "api",

    "test": "testing",
    "mock": "testing",

    "docker": "docker",
    "ci/cd": "cicd",
    "pipeline": "pipeline",
    "git": "git",
    "linux": "linux",

    "ui": "ui",
    "ux": "ui",

    "claude": "ai",
    "graphify": "graphify",
    "llm": "ai",
    "prompt": "prompt-engineering",

    "bug": "debugging",
    "debug": "debugging",
    "error": "debugging",
    "fix": "bugfix",
    "deploy": "deploy",
    "performance": "performance",
}

# Example domain-specific keywords (.NET/C# stack) — additive on top of the generic map
# above. Replace with your own stack's keywords, or delete entirely; a vault for an
# unrelated project can just ignore these — they won't match anything and are harmless.
DOTNET_TAG_MAP = {
    "c#": "csharp",
    "csharp": "csharp",
    ".net": "dotnet",
    "dotnet": "dotnet",
    "winforms": "winforms",
    "winfoms": "winforms",
    "asp.net": "aspnet",
    "aspnet": "aspnet",
    "blazor": "blazor",
    "wpf": "wpf",
    "xaml": "xaml",
    "nuget": "nuget",
    "visual studio": "visual-studio",
    "devexpress": "devexpress",
    "postgresql": "database",
    "postgres": "database",
    "mssql": "database",
    "sql server": "database",
    "entity framework": "entity-framework",
    "dapper": "dapper",
    "claims": "auth",
    "role": "auth",
    "swagger": "api",
    "openapi": "api",
    "xunit": "testing",
    "nunit": "testing",
    "pytest": "testing",
    "bat": "testing",
    "gitlab": "gitlab",
    "3d": "3d",
    "viewer": "viewer",
    "image": "imaging",
    "obsidian": "obsidian",
}

KEYWORD_TAG_MAP = {**GENERIC_TAG_MAP, **DOTNET_TAG_MAP}
SHORT_KEYWORDS = {"api", "git", "llm", "sql", "rest", "ui", "ux", "3d", "wpf", "bat", "adr"}

# ============================================================================
# VAULT ROUTING — mirrors resolve-vault.sh's algorithm
# ============================================================================


def resolve_vault_for_cwd(cwd: str) -> tuple[str, Path, str]:
    """Walk up from `cwd` looking for .claude/vault-scope.json, stopping after the
    first git repo root. Falls back to a private vault at ~/vault if nothing is found.
    Returns (scope, vault_dir, project)."""
    d = Path(cwd)
    while True:
        marker = d / ".claude" / "vault-scope.json"
        if marker.exists():
            data = json.loads(marker.read_text())
            scope = data.get("scope", "private")
            vault_dir = _expand_vault_path(data.get("vault", "~/vault"), d)
            return scope, vault_dir, d.name
        if (d / ".git").exists():
            break
        if d.parent == d:
            break
        d = d.parent
    return "private", Path.home() / "vault", Path(cwd).name


def _expand_vault_path(raw: str, base: Path) -> Path:
    if raw.startswith("~"):
        return Path(raw.replace("~", str(Path.home()), 1))
    p = Path(raw)
    return p if p.is_absolute() else (base / p).resolve()


# ============================================================================
# CORE LOGIC
# ============================================================================


def detect_origin(filepath: Path, content: str) -> str:
    path_str = str(filepath).lower()
    if any(k in path_str for k in ("code", "claude-code", ".claude/projects")):
        return "code"
    code_indicators = ["```bash", "$ claude", "terminal", "command line"]
    hits = sum(1 for ind in code_indicators if ind.lower() in content.lower())
    if hits >= 2:
        return "code"
    return "web"


def extract_tags(content: str) -> list[str]:
    content_lower = content.lower()
    found: set[str] = set()
    for keyword, tag in KEYWORD_TAG_MAP.items():
        if keyword in SHORT_KEYWORDS:
            if re.search(rf"\b{re.escape(keyword)}\b", content_lower):
                found.add(tag)
        else:
            if keyword in content_lower:
                found.add(tag)
    return sorted(found)


def strip_existing_frontmatter(content: str) -> tuple[dict[str, str], str]:
    existing: dict[str, str] = {}
    body = content
    if content.startswith("---\n"):
        end = content.find("\n---\n", 4)
        if end != -1:
            fm_block = content[4:end]
            body = content[end + 5:]
            for line in fm_block.split("\n"):
                if ":" in line and not line.startswith("  ") and not line.startswith("-"):
                    key, _, val = line.partition(":")
                    existing[key.strip()] = val.strip().strip('"')
    return existing, body


def build_frontmatter(title: str, tags: list[str], origin: str, created: str, project: str, cwd: str, session_id: str = "") -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    all_tags = ["chat-import", f"project-{project}"] + [t for t in tags if t != "chat-import"]
    tags_yaml = "\n".join(f"  - {t}" for t in all_tags)
    session_line = f'session_id: "{session_id}"\n' if session_id else ""
    return f"""---
title: "{title}"
tags:
{tags_yaml}
source: claude
origin: {origin}
project: {project}
cwd: "{cwd}"
{session_line}created: {created}
processed: {now}
status: imported
type: chat
---

"""


def collect_vault_notes(vault_dir: Path) -> list[str]:
    notes: list[str] = []
    if not vault_dir.exists():
        return notes
    for md in vault_dir.rglob("*.md"):
        rel = md.relative_to(vault_dir)
        if any(p.startswith(".") for p in rel.parts):
            continue
        name = md.stem
        if len(name) >= 4:
            notes.append(name)
    notes.sort(key=lambda n: -len(n))
    return notes


def find_matching_summary_note(vault_dir: Path, project: str, session_id: str) -> Path | None:
    """Find a hand-written /save note (chats/<project>/*.md, NOT imported/) whose
    session_id frontmatter matches. Returns the most recently modified match, or None."""
    if not session_id:
        return None
    summary_dir = vault_dir / "chats" / project
    if not summary_dir.exists():
        return None
    candidates = []
    for md in summary_dir.glob("*.md"):  # non-recursive: excludes imported/ subfolder
        content = md.read_text(encoding="utf-8", errors="replace")
        existing, _ = strip_existing_frontmatter(content)
        if existing.get("session_id") == session_id:
            candidates.append(md)
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def add_link_field(filepath: Path, field_name: str, target_stem: str, body_label: str) -> None:
    """Idempotently add a frontmatter field + a visible body line linking to another
    note by its bare name (Obsidian resolves [[name]] vault-wide regardless of folder).
    No-ops if the link is already present, or if filepath has no frontmatter to anchor to."""
    content = filepath.read_text(encoding="utf-8")
    link = f"[[{target_stem}]]"
    if f'{field_name}: "{link}"' in content:
        return  # already linked

    if not content.startswith("---\n"):
        return
    end = content.find("\n---\n", 4)
    if end == -1:
        return

    fm_block = content[4:end]
    body = content[end + 5:]

    fm_lines = [l for l in fm_block.split("\n") if not l.startswith(f"{field_name}:")]
    fm_lines.append(f'{field_name}: "{link}"')
    new_fm = "\n".join(fm_lines)

    body_line = f"**{body_label}:** {link}"
    new_content = f"---\n{new_fm}\n---\n\n{body_line}\n\n{body.lstrip()}"
    filepath.write_text(new_content, encoding="utf-8")


def insert_wikilinks(body: str, vault_notes: list[str]) -> str:
    parts = re.split(r"(```[\s\S]*?```|`[^`\n]+`)", body)
    linked: set[str] = set()
    for i, part in enumerate(parts):
        if part.startswith("`"):
            continue
        for note in vault_notes:
            if note in linked:
                continue
            pattern = rf"(?<!\[\[)\b({re.escape(note)})\b(?!\]\])"
            match = re.search(pattern, part, re.IGNORECASE)
            if match:
                parts[i] = part[: match.start()] + f"[[{note}]]" + part[match.end():]
                part = parts[i]
                linked.add(note)
    return "".join(parts)


def process_file(
    filepath: Path,
    vault_dir: Path,
    vault_notes: list[str],
    project: str,
    cwd: str,
    session_id: str,
    origin_override: str | None,
    no_wikilinks: bool,
    dry_run: bool,
    force: bool,
) -> dict | None:
    content = filepath.read_text(encoding="utf-8", errors="replace")
    existing, body = strip_existing_frontmatter(content)

    dest_dir = vault_dir / "chats" / project / "imported"
    dest = dest_dir / filepath.name

    if dest.exists() and not force:
        return None  # already imported — idempotent skip

    origin = origin_override or existing.get("origin") or detect_origin(filepath, content)
    tags = extract_tags(content)
    title = existing.get("title") or filepath.stem

    mtime = datetime.fromtimestamp(filepath.stat().st_mtime)
    created = existing.get("created") or mtime.strftime("%Y-%m-%d")

    if not no_wikilinks:
        body = insert_wikilinks(body, vault_notes)

    frontmatter = build_frontmatter(title, tags, origin, created, project, cwd, session_id)
    output = frontmatter + body

    result = {
        "source": str(filepath),
        "dest": str(dest),
        "origin": origin,
        "tags": tags,
        "title": title,
        "project": project,
        "session_id": session_id,
        "vault": str(vault_dir),
    }

    if dry_run:
        return result

    dest_dir.mkdir(parents=True, exist_ok=True)
    dest.write_text(output, encoding="utf-8")

    return result


def git_commit_if_repo(vault_dir: Path) -> None:
    """Commit newly imported chats if this vault is a git repo; skip silently if not.
    Scoped to the chats/ subdir so it never touches unrelated in-progress edits
    elsewhere in the vault. Does not push -- that stays a separate, explicit step."""
    if not (vault_dir / ".git").is_dir():
        return

    status = subprocess.run(
        ["git", "-C", str(vault_dir), "status", "--porcelain", "chats"],
        capture_output=True, text=True,
    )
    if not status.stdout.strip():
        return

    subprocess.run(["git", "-C", str(vault_dir), "add", "chats"], check=False)
    msg = f"import chats ({datetime.now().strftime('%Y-%m-%d %H:%M')})"
    commit = subprocess.run(
        ["git", "-C", str(vault_dir), "commit", "-q", "-m", msg],
        capture_output=True, text=True,
    )
    if commit.returncode == 0:
        print(f"Committed imported chats in {vault_dir}")
    else:
        print(f"git commit failed in {vault_dir}: {commit.stderr.strip()}")


def main():
    parser = argparse.ArgumentParser(description="Import Claude Code chats into the correct vault, auto-routed by project")
    parser.add_argument("--export-dir", required=True, type=Path, help="Directory with exported .md files")
    parser.add_argument("--vault-dir", type=Path, help="Force all files into this vault (skips auto-routing)")
    parser.add_argument("--project", help="Force all files into this project folder (requires --vault-dir)")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true", help="Reprocess even if the destination file already exists")
    parser.add_argument("--origin", choices=["code", "web", "auto"], default="auto")
    parser.add_argument("--no-wikilinks", action="store_true")
    args = parser.parse_args()

    if args.project and not args.vault_dir:
        print("ERROR: --project requires --vault-dir")
        return
    if not args.export_dir.exists():
        print(f"ERROR: Export directory not found: {args.export_dir}")
        return

    md_files = sorted(args.export_dir.rglob("*.md"))
    if not md_files:
        print("No .md files found in export directory.")
        return

    print(f"Files to consider: {len(md_files)}")
    if args.dry_run:
        print("=== DRY RUN — nothing will be modified ===\n")

    origin_override = args.origin if args.origin != "auto" else None
    vault_notes_cache: dict[Path, list[str]] = {}
    results = []
    skipped_no_cwd = 0
    skipped_already_imported = 0

    for f in md_files:
        content = f.read_text(encoding="utf-8", errors="replace")
        existing, _ = strip_existing_frontmatter(content)
        cwd = existing.get("cwd", "")
        session_id = existing.get("session_id", "")

        if args.vault_dir:
            vault_dir = args.vault_dir
            project = args.project or "misc"
        elif cwd:
            _, vault_dir, project = resolve_vault_for_cwd(cwd)
        else:
            skipped_no_cwd += 1
            continue

        if vault_dir not in vault_notes_cache:
            vault_notes_cache[vault_dir] = collect_vault_notes(vault_dir)

        result = process_file(
            f, vault_dir, vault_notes_cache[vault_dir],
            project, cwd, session_id, origin_override,
            args.no_wikilinks, args.dry_run, args.force,
        )
        if result is None:
            skipped_already_imported += 1
            continue

        results.append(result)
        tags_str = ", ".join(result["tags"]) if result["tags"] else "(no tags)"
        prefix = "[DRY] " if args.dry_run else ""
        print(f'{prefix}+ {result["title"]} -> {result["vault"]}/chats/{result["project"]}/imported/')
        print(f'  Origin: {result["origin"]} | Tags: {tags_str}')

        if not args.dry_run and session_id:
            transcript_path = Path(result["dest"])
            summary_path = find_matching_summary_note(vault_dir, project, session_id)
            if summary_path:
                add_link_field(summary_path, "full_transcript", transcript_path.stem, "Full transcript")
                add_link_field(transcript_path, "summary_note", summary_path.stem, "Session summary")
                print(f"  Linked -> {summary_path.name}")

    if not args.dry_run:
        for touched_vault in sorted({Path(r["vault"]) for r in results}):
            git_commit_if_repo(touched_vault)

    print(f"\n{'=' * 50}")
    print("SUMMARY")
    print(f"{'=' * 50}")
    print(f"Imported: {len(results)}")
    print(f"Skipped (already imported): {skipped_already_imported}")
    if skipped_no_cwd:
        print(f"Skipped (no cwd frontmatter — export made without the extractor fork): {skipped_no_cwd}")
    if args.dry_run:
        print("\nDry run — no files were modified.")


if __name__ == "__main__":
    main()
