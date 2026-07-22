#!/usr/bin/env python3
"""Plain-assert tests for the session-transcript-linking feature.
Run directly: python3 tests/test_linking.py
(No pytest dependency, matching this repo's existing zero-dependency scripts.)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from claude_to_obsidian import build_frontmatter, strip_existing_frontmatter

import tempfile
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from claude_to_obsidian import find_matching_summary_note, add_link_field


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_build_frontmatter_includes_session_id_when_present():
    fm = build_frontmatter(
        title="t", tags=[], origin="code", created="2026-07-22",
        project="myproj", cwd="/tmp/myproj", session_id="abc-123-uuid",
    )
    assert 'session_id: "abc-123-uuid"' in fm, fm


def test_build_frontmatter_omits_session_id_when_empty():
    fm = build_frontmatter(
        title="t", tags=[], origin="code", created="2026-07-22",
        project="myproj", cwd="/tmp/myproj", session_id="",
    )
    assert "session_id" not in fm, fm


def test_strip_existing_frontmatter_reads_session_id_back():
    fm = build_frontmatter(
        title="t", tags=[], origin="code", created="2026-07-22",
        project="myproj", cwd="/tmp/myproj", session_id="abc-123-uuid",
    )
    existing, _ = strip_existing_frontmatter(fm + "body text")
    assert existing.get("session_id") == "abc-123-uuid", existing


def test_find_matching_summary_note_matches_by_session_id():
    with tempfile.TemporaryDirectory() as tmp:
        vault = Path(tmp)
        _write(vault / "chats" / "proj" / "2026-07-22-10-00.md",
               '---\nsession_id: "abc-123"\n---\n\n# Session\n')
        _write(vault / "chats" / "proj" / "imported" / "claude-conversation-2026-07-22-abc12345.md",
               '---\nsession_id: "abc-123"\n---\n\n# transcript\n')
        found = find_matching_summary_note(vault, "proj", "abc-123")
        assert found is not None
        assert found.name == "2026-07-22-10-00.md", found


def test_find_matching_summary_note_ignores_imported_subfolder():
    with tempfile.TemporaryDirectory() as tmp:
        vault = Path(tmp)
        # Only a transcript with this session_id exists, in imported/ -- must not match.
        _write(vault / "chats" / "proj" / "imported" / "claude-conversation-2026-07-22-abc12345.md",
               '---\nsession_id: "abc-123"\n---\n\n# transcript\n')
        found = find_matching_summary_note(vault, "proj", "abc-123")
        assert found is None, found


def test_find_matching_summary_note_returns_none_when_no_match():
    with tempfile.TemporaryDirectory() as tmp:
        vault = Path(tmp)
        _write(vault / "chats" / "proj" / "2026-07-22-10-00.md",
               '---\nsession_id: "other-id"\n---\n\n# Session\n')
        found = find_matching_summary_note(vault, "proj", "abc-123")
        assert found is None, found


def test_add_link_field_adds_frontmatter_and_body_line():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "note.md"
        _write(path, '---\nsession_id: "abc-123"\n---\n\n# Session\n\nsome text\n')
        add_link_field(path, "full_transcript", "claude-conversation-2026-07-22-abc12345", "Full transcript")
        text = path.read_text()
        assert 'full_transcript: "[[claude-conversation-2026-07-22-abc12345]]"' in text, text
        assert "**Full transcript:** [[claude-conversation-2026-07-22-abc12345]]" in text, text
        assert "# Session" in text  # original body preserved


def test_add_link_field_is_idempotent():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "note.md"
        _write(path, '---\nsession_id: "abc-123"\n---\n\n# Session\n')
        add_link_field(path, "full_transcript", "claude-conversation-2026-07-22-abc12345", "Full transcript")
        first = path.read_text()
        add_link_field(path, "full_transcript", "claude-conversation-2026-07-22-abc12345", "Full transcript")
        second = path.read_text()
        assert first == second, "second call must not change the file"
        assert second.count("full_transcript:") == 1, second
        assert second.count("**Full transcript:**") == 1, second


if __name__ == "__main__":
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"PASS: {t.__name__}")
    print(f"\n{len(tests)} passed")
