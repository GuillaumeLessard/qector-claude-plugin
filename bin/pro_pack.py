#!/usr/bin/env python3
"""
Pro packager: builds BOTH an upload-safe single skill ZIP for claude.ai
AND a full multi-skill plugin ZIP for `claude --plugin-dir`, using
forward-slash ZIP entry names and clean exclusions.

Usage:
    python bin/pro_pack.py                  # build both into dist/
    python bin/pro_pack.py --skill qector-core
    python bin/pro_pack.py --plugin
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
    ".git", "__pycache__", ".venv", "venv", "node_modules", "dist", "build",
    ".mypy_cache", ".pytest_cache", ".ruff_cache", "artifacts", ".cargo",
    "target", "site-packages", "skills-main",
}
EXCLUDE_FILES = {".DS_Store", "Thumbs.db"}
EXCLUDE_SUFFIXES = {".pyc", ".pyo", ".pyd", ".so", ".exe", ".dll", ".pdb", ".log", ".sha256"}
FORBIDDEN_RE = re.compile(r'[<>:"|?*\x00-\x1f]')


def norm(rel: Path) -> str:
    return "/".join(p.replace("\\", "/") for p in rel.parts)


def skip(rel: Path) -> bool:
    if any(p in EXCLUDE_DIRS for p in rel.parts):
        return True
    if rel.name.startswith(".") and rel.name not in {".claude-plugin", ".mcp.json"}:
        return True
    if rel.name in EXCLUDE_FILES:
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
    (out.with_suffix(out.suffix + ".sha256")).write_text(f"{sha}  {out.name}\n")
    return out


def make_skill_zip(skill: str) -> Path:
    sp = ROOT / "skills" / skill
    md = sp / "SKILL.md"
    if not md.is_file():
        print(f"ERROR: {md} not found", file=sys.stderr)
        sys.exit(1)
    rel_iter = (fp for fp in sorted(sp.rglob("*")) if fp.is_file())
    entries = [
        (fp, f"{skill}/{norm(fp.relative_to(sp))}")
        for fp in rel_iter
        if not skip(fp.relative_to(sp))
    ]
    return write_zip(DIST / f"qector-{skill}-skill.zip", entries)


def make_plugin_zip() -> Path:
    v = "1.0.0"
    manifest = ROOT / ".claude-plugin" / "plugin.json"
    if manifest.is_file():
        v = json.loads(manifest.read_text()).get("version", v)
    rel_iter = (fp for fp in sorted(ROOT.rglob("*")) if fp.is_file())
    entries = [
        (fp, norm(fp.relative_to(ROOT)))
        for fp in rel_iter
        if not skip(fp.relative_to(ROOT))
    ]
    return write_zip(DIST / f"qector-claude-plugin-v{v}.zip", entries)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--skill", action="append", help="build a single skill ZIP (repeatable)")
    ap.add_argument("--plugin", action="store_true", help="build the full plugin ZIP")
    ap.add_argument("--all", action="store_true", help="build qector-core skill + full plugin ZIP")
    a = ap.parse_args()

    build_skill = a.skill is not None or a.all
    build_plugin = a.plugin or a.all

    if not build_skill and not build_plugin:
        ap.error("specify --skill X, --plugin, or --all")

    if build_skill:
        for s in (a.skill if a.skill else ["qector-core"]):
            p = make_skill_zip(s)
            print(f"skill: {p} ({p.stat().st_size} bytes)")
    if build_plugin:
        p = make_plugin_zip()
        print(f"plugin: {p} ({p.stat().st_size} bytes)")
