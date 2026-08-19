#!/usr/bin/env python3
"""
Pro packager: builds BOTH an upload-safe single skill ZIP for claude.ai
AND a full multi-skill plugin ZIP for `claude --plugin-dir`, using
forward-slash ZIP entry names and clean exclusions.

Usage:
    python scripts/pro_pack.py                  # build both into dist/
    python scripts/pro_pack.py --skill qector-core
    python scripts/pro_pack.py --plugin
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
EXCLUDE_DIRS = {
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    "node_modules",
    "dist",
    "build",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "artifacts",
    ".cargo",
    "target",
    "site-packages",
    "skills-main",
    ".tmp_core",
    "bin",
}
EXCLUDE_FILES = {".DS_Store", "Thumbs.db", "err.txt", "out.txt", "output.txt"}
EXCLUDE_SUFFIXES = {
    ".pyc",
    ".pyo",
    ".pyd",
    ".so",
    ".exe",
    ".dll",
    ".pdb",
    ".log",
    ".sha256",
    ".deprecated",
    ".tmp",
    ".bak",
    ".orig",
}
FORBIDDEN_RE = re.compile(r'[<>:"|?*\x00-\x1f]')


def _is_stray_artifact(rel: Path) -> bool:
    """Catch accidental editor/shell artifacts that aren't part of the
    documented public package: default OS-generated filenames (e.g.
    Windows' "New Text Document.txt"), personal scratch notes left at
    repo root, and any stray .txt files other than requirements.txt.
    """
    name = rel.name
    lower = name.lower()
    if lower.startswith("new text document") or lower.startswith("new document"):
        return True
    if lower.startswith(("todo_", "notes_", "scratch", "test_", "temp_")) and lower.endswith(
        (".txt", ".md")
    ):
        return True
    if len(rel.parts) == 1 and lower.endswith(".txt") and lower != "requirements.txt":
        return True
    return False


def norm(rel: Path) -> str:
    return "/".join(p.replace("\\", "/") for p in rel.parts)


def skip(rel: Path) -> bool:
    if any(p in EXCLUDE_DIRS for p in rel.parts):
        return True
    if any(
        p.startswith(".") and p not in {".claude-plugin", ".mcp.json"}
        for p in rel.parts
    ):
        return True
    if rel.name in EXCLUDE_FILES:
        return True
    if _is_stray_artifact(rel):
        return True
    if rel.suffix in EXCLUDE_SUFFIXES:
        return True
    return any(FORBIDDEN_RE.search(p) for p in rel.parts)


def write_zip(out: Path, entries: list[tuple[Path, str]]) -> Path:
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        out.unlink()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for fp, arc in entries:
            if "\\" in arc:
                print(f"WARN: backslash in {arc}", file=sys.stderr)
            zf.write(fp, arc)
    sha = hashlib.sha256(out.read_bytes()).hexdigest()
    (out.with_suffix(out.suffix + ".sha256")).write_text(
        f"{sha}  {out.name}\n", encoding="ascii"
    )
    return out


def make_skill_zip(skill: str) -> Path:
    sp = ROOT / "skills" / skill
    md = sp / "SKILL.md"
    if not md.is_file():
        print(f"ERROR: {md} not found", file=sys.stderr)
        sys.exit(1)
    import os

    entries = []
    for root, dirs, files in os.walk(sp):
        dirs[:] = [
            d
            for d in dirs
            if d not in EXCLUDE_DIRS
            and not (d.startswith(".") and d not in {".claude-plugin"})
        ]
        for f in files:
            fp = Path(root) / f
            rel = fp.relative_to(sp)
            if not skip(rel):
                entries.append((fp, f"{skill}/{norm(rel)}"))
    return write_zip(DIST / f"qector-{skill}-skill.zip", entries)


def make_plugin_zip() -> Path:
    import os

    v = "1.0.0"
    manifest = ROOT / ".claude-plugin" / "plugin.json"
    if manifest.is_file():
        v = json.loads(manifest.read_text(encoding="utf-8")).get("version", v)

    entries = []
    for root, dirs, files in os.walk(ROOT):
        # Prune excluded directories in place
        dirs[:] = [
            d
            for d in dirs
            if d not in EXCLUDE_DIRS
            and not (d.startswith(".") and d not in {".claude-plugin"})
        ]
        for f in files:
            fp = Path(root) / f
            rel = fp.relative_to(ROOT)
            if not skip(rel):
                entries.append((fp, norm(rel)))

    return write_zip(DIST / f"qector-claude-plugin-v{v}.zip", entries)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--skill", action="append", help="build a single skill ZIP (repeatable)"
    )
    ap.add_argument("--plugin", action="store_true", help="build the full plugin ZIP")
    ap.add_argument(
        "--all", action="store_true", help="build qector-core skill + full plugin ZIP"
    )
    a = ap.parse_args()

    build_skill = a.skill is not None or a.all
    build_plugin = a.plugin or a.all

    if not build_skill and not build_plugin:
        ap.error("specify --skill X, --plugin, or --all")

    if build_skill:
        for s in a.skill if a.skill else ["qector-core"]:
            p = make_skill_zip(s)
            print(f"skill: {p} ({p.stat().st_size} bytes)")
    if build_plugin:
        p = make_plugin_zip()
        print(f"plugin: {p} ({p.stat().st_size} bytes)")
