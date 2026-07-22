#!/usr/bin/env python3
"""Plain-assert tests for the session-transcript-linking feature.
Run directly: python3 tests/test_linking.py
(No pytest dependency, matching this repo's existing zero-dependency scripts.)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from claude_to_obsidian import build_frontmatter, strip_existing_frontmatter


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


if __name__ == "__main__":
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"PASS: {t.__name__}")
    print(f"\n{len(tests)} passed")
