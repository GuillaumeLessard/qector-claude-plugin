#!/usr/bin/env python3
"""Validate the QECTOR source repository structure.

Run from anywhere; resolves the repo root from this file's location.

The script enforces the *source-tree* shape: skills, agents, commands, hooks,
plugin and Desktop extension manifests, MCP config templates, and cleanliness
of the working tree. It never requires ``dist/`` to be present and never
inspects built artifacts. The companion script
``scripts/validate_plugin_bundle.py`` covers the built-bundle contract.

Exit code is 0 when every check passes, 1 otherwise. ``--warn-only`` keeps the
exit code at 0 and only prints warnings; useful for local edits where a single
known regression is acceptable.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Counters are module-level so the helper can mutate them.
_passed = 0
_failed = 0
_warnings = 0
_warn_only = False


def check(condition: bool, label: str, warn_only: bool = False) -> None:
    global _passed, _failed, _warnings
    if condition:
        print(f"  PASS - {label}")
        _passed += 1
    elif warn_only or _warn_only:
        print(f"  WARN - {label}")
        _warnings += 1
    else:
        print(f"  FAIL - {label}")
        _failed += 1


def _section(title: str) -> None:
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}")


def validate_skills() -> None:
    _section("SKILLS VALIDATION")
    skills_dir = os.path.join(ROOT, "skills")
    skill_dirs = sorted(os.listdir(skills_dir))
    print(f"  Found {len(skill_dirs)} skill directories")
    check(len(skill_dirs) >= 7, f"At least 7 skills present (got {len(skill_dirs)})")
    for sd in skill_dirs:
        skill_path = os.path.join(skills_dir, sd)
        if not os.path.isdir(skill_path):
            continue
        skill_md = os.path.join(skill_path, "SKILL.md")
        has_skill_md = os.path.isfile(skill_md)
        check(has_skill_md, f"skills/{sd}/SKILL.md exists")
        if has_skill_md:
            with open(skill_md, "r", encoding="utf-8") as handle:
                content = handle.read()
            check(
                len(content) > 100,
                f"skills/{sd}/SKILL.md has substantive content ({len(content)} bytes)",
            )
            has_frontmatter = content.startswith("---")
            check(
                has_frontmatter,
                f"skills/{sd}/SKILL.md has YAML frontmatter",
                warn_only=True,
            )


def validate_agents() -> None:
    _section("AGENTS VALIDATION")
    agents_dir = os.path.join(ROOT, "agents")
    agent_files = sorted(os.listdir(agents_dir))
    print(f"  Found {len(agent_files)} agent files")
    check(len(agent_files) >= 5, f"At least 5 agents present (got {len(agent_files)})")
    for af in agent_files:
        if not af.endswith(".md"):
            continue
        agent_path = os.path.join(agents_dir, af)
        with open(agent_path, "r", encoding="utf-8") as handle:
            content = handle.read()
        check(len(content) > 200, f"agents/{af} has substantive content ({len(content)} bytes)")
        has_tool_ref = (
            "tool" in content.lower()
            or "skill" in content.lower()
            or "mcp" in content.lower()
        )
        check(has_tool_ref, f"agents/{af} references tools/skills/MCP")


def validate_commands() -> None:
    _section("COMMANDS VALIDATION")
    commands_dir = os.path.join(ROOT, "commands")
    cmd_files = sorted(os.listdir(commands_dir))
    print(f"  Found {len(cmd_files)} command files")
    check(len(cmd_files) >= 3, f"At least 3 commands present (got {len(cmd_files)})")
    for cf in cmd_files:
        if not cf.endswith(".md"):
            continue
        cmd_path = os.path.join(commands_dir, cf)
        with open(cmd_path, "r", encoding="utf-8") as handle:
            content = handle.read()
        check(len(content) > 100, f"commands/{cf} has substantive content ({len(content)} bytes)")


def validate_hooks() -> None:
    _section("HOOKS VALIDATION")
    hooks_path = os.path.join(ROOT, "hooks", "hooks.json")
    check(os.path.isfile(hooks_path), "hooks/hooks.json exists")
    if os.path.isfile(hooks_path):
        with open(hooks_path, "r", encoding="utf-8") as handle:
            hooks_data = json.load(handle)
        check(isinstance(hooks_data, dict), "hooks.json is valid JSON dict")
        hooks_section = hooks_data.get("hooks", {})
        check("SessionStart" in hooks_section, "hooks.json has SessionStart event")
        check("PostToolUse" in hooks_section, "hooks.json has PostToolUse event")
        for event_name, event_list in hooks_section.items():
            for i, entry in enumerate(event_list):
                inner_hooks = entry.get("hooks", [])
                for j, hook in enumerate(inner_hooks):
                    check(
                        "type" in hook,
                        f"hooks.{event_name}[{i}].hooks[{j}] has 'type' "
                        f"({hook.get('type', '?')})",
                    )
                    check(
                        "command" in hook,
                        f"hooks.{event_name}[{i}].hooks[{j}] has 'command'",
                    )
                    command = hook.get("command", "")
                    if "qector_session_start.py" in command:
                        check(
                            os.path.isfile(
                                os.path.join(
                                    ROOT, "scripts", "qector_session_start.py"
                                )
                            ),
                            "hooks SessionStart script scripts/qector_session_start.py exists",
                        )
                    if "qector_tool_log.py" in command:
                        check(
                            os.path.isfile(
                                os.path.join(ROOT, "scripts", "qector_tool_log.py")
                            ),
                            "hooks PostToolUse script scripts/qector_tool_log.py exists",
                        )


def validate_manifests() -> None:
    _section("PLUGIN MANIFESTS VALIDATION")
    plugin_json = os.path.join(ROOT, ".claude-plugin", "plugin.json")
    marketplace_json = os.path.join(ROOT, ".claude-plugin", "marketplace.json")
    mcp_json = os.path.join(ROOT, ".mcp.json")

    check(os.path.isfile(plugin_json), ".claude-plugin/plugin.json exists")
    check(os.path.isfile(marketplace_json), ".claude-plugin/marketplace.json exists")
    check(os.path.isfile(mcp_json), ".mcp.json exists")

    pj = None
    if os.path.isfile(plugin_json):
        with open(plugin_json, "r", encoding="utf-8") as handle:
            pj = json.load(handle)
        check("name" in pj, f"plugin.json has 'name' field: {pj.get('name', '?')}")
        check("version" in pj, f"plugin.json has 'version' field: {pj.get('version', '?')}")

    if os.path.isfile(marketplace_json):
        with open(marketplace_json, "r", encoding="utf-8") as handle:
            mj = json.load(handle)
        check("name" in mj, f"marketplace.json has 'name' field: {mj.get('name', '?')}")

    if os.path.isfile(mcp_json):
        with open(mcp_json, "r", encoding="utf-8") as handle:
            mc = json.load(handle)
        servers = mc.get("mcpServers", {})
        check(
            set(servers) == {"qector-library"},
            "mcp.json defaults to qector-library only",
        )
        for server_name in ("qector-library",):
            server_env = servers.get(server_name, {}).get("env", {})
            check(
                server_env.get("PYTHONUNBUFFERED") == "1",
                f"mcp.json enables unbuffered stdio for {server_name}",
            )

    # Cross-manifest version consistency: plugin.json, marketplace.json, and
    # the Desktop extension manifest must all carry the same version string.
    desktop_manifest = os.path.join(
        ROOT, ".claude-desktop-extension", "manifest.json"
    )
    if pj is not None and os.path.isfile(desktop_manifest):
        with open(desktop_manifest, "r", encoding="utf-8") as handle:
            dm = json.load(handle)
        plugin_version = pj.get("version")
        desktop_version = dm.get("version")
        check(
            plugin_version == desktop_version,
            f"plugin.json version ({plugin_version}) matches Desktop manifest "
            f"version ({desktop_version})",
        )


def validate_desktop_source() -> None:
    _section("CLAUDE DESKTOP EXTENSION VALIDATION")
    desktop_manifest_path = os.path.join(
        ROOT, ".claude-desktop-extension", "manifest.json"
    )
    desktop_server_path = os.path.join(ROOT, "mcp", "mcp_server_desktop.py")
    check(os.path.isfile(desktop_manifest_path), "Desktop extension manifest exists")
    check(os.path.isfile(desktop_server_path), "combined Desktop MCP server exists")
    if os.path.isfile(desktop_manifest_path):
        with open(desktop_manifest_path, "r", encoding="utf-8") as handle:
            desktop_manifest = json.load(handle)
        desktop_server = desktop_manifest.get("server", {})
        check(
            desktop_server.get("entry_point") == "mcp/mcp_server_desktop.py",
            "Desktop extension uses the profiled MCP entry point",
        )
        desktop_args = desktop_server.get("mcp_config", {}).get("args", [])
        check(
            desktop_args == [
                "${__dirname}/mcp/mcp_server_desktop.py",
                "--profile",
                "safe",
            ],
            "Desktop extension config selects the safe profile",
        )
        check(
            len(desktop_manifest.get("tools", [])) == 8,
            "Desktop extension advertises 8 stable tools",
        )
        # License metadata must be proprietary to match LICENSE.md.
        check(
            desktop_manifest.get("license", "").lower() == "proprietary",
            "Desktop extension license is Proprietary (matches LICENSE.md)",
        )


def validate_mcp_config_templates() -> None:
    _section("MCP CONFIG TEMPLATES VALIDATION")
    for cfg_rel in ("mcp/claude_desktop_config.json", "mcp/mcp_config.json"):
        cfg_path = os.path.join(ROOT, cfg_rel)
        check(os.path.isfile(cfg_path), f"{cfg_rel} exists")
        if os.path.isfile(cfg_path):
            with open(cfg_path, "r", encoding="utf-8") as handle:
                cfg_data = json.load(handle)
            cfg_servers = cfg_data.get("mcpServers", {})
            check(
                set(cfg_servers) == {"qector-library"},
                f"{cfg_rel} defaults to qector-library only",
            )


def validate_public_claims() -> None:
    _section("PUBLIC CLAIM CONSISTENCY")
    commands_dir = os.path.join(ROOT, "commands")
    agents_dir = os.path.join(ROOT, "agents")
    skills_dir = os.path.join(ROOT, "skills")
    command_files = [
        name for name in sorted(os.listdir(commands_dir)) if name.endswith(".md")
    ]
    agent_files = [
        name for name in sorted(os.listdir(agents_dir)) if name.endswith(".md")
    ]
    skill_dirs = [
        name
        for name in sorted(os.listdir(skills_dir))
        if os.path.isdir(os.path.join(skills_dir, name))
    ]
    check(len(command_files) == 11, f"exactly 11 slash commands (got {len(command_files)})")
    check(len(agent_files) == 5, f"exactly 5 agents (got {len(agent_files)})")
    check(len(skill_dirs) == 28, f"exactly 28 skills (got {len(skill_dirs)})")
    check(
        "qec-decode.md" not in command_files,
        "retired /qec-decode is not a current command",
    )
    check(
        "qec-desktop-connector.md" not in command_files,
        "retired /qec-desktop-connector is not a current command",
    )

    forbidden = (
        ("/qec-desktop-connector", "retired desktop-connector command"),
        ("/qec-decode", "retired decode command"),
        ("13 commands", "stale 13-command count"),
        ("12 reproducible", "stale 12-command count"),
        ("28 tools including", "stale 28-tool bench count"),
        ("exposes 28 tools", "stale 28-tool bench count"),
        ("(28 tools", "stale 28-tool bench count"),
        ("26 opt-in provisional", "stale 26-tool research count"),
        ("26 provisional", "stale 26-tool research count"),
        ("26-tool", "stale 26-tool research count"),
        ("qector-bench.", "retired qector-bench server prefix"),
        ("license\": \"Apache-2.0\"", "Apache-2.0 plugin license"),
    )
    scan_roots = (
        os.path.join(ROOT, "skills"),
        os.path.join(ROOT, "agents"),
        os.path.join(ROOT, "commands"),
        os.path.join(ROOT, "CLAUDE.md"),
        os.path.join(ROOT, "CLAUDE_DESKTOP.md"),
        os.path.join(ROOT, "README.md"),
        os.path.join(ROOT, "docs", "User_Manual.md"),
        os.path.join(ROOT, "cheat_sheets", "master_cheat_sheet.md"),
        os.path.join(ROOT, "mcp", "CLAUDE_DESKTOP.md"),
        os.path.join(ROOT, ".claude-desktop-extension", "README.md"),
        os.path.join(ROOT, "TOOL_STABILITY.md"),
        os.path.join(ROOT, "ARCHITECTURE.md"),
        os.path.join(ROOT, "FIRST_BOOT.md"),
        os.path.join(ROOT, "SECURITY.md"),
        os.path.join(ROOT, "MCP_API.md"),
    )
    for root in scan_roots:
        paths = []
        if os.path.isfile(root):
            paths.append(root)
        elif os.path.isdir(root):
            for dirpath, _dirnames, filenames in os.walk(root):
                for filename in filenames:
                    if filename.endswith(".md"):
                        paths.append(os.path.join(dirpath, filename))
        for path in paths:
            with open(path, "r", encoding="utf-8") as handle:
                text = handle.read()
            rel = os.path.relpath(path, ROOT).replace("\\", "/")
            for needle, label in forbidden:
                check(
                    needle not in text,
                    f"{rel} does not contain {label}",
                )


def validate_cleanliness() -> None:
    _section("CLEANLINESS CHECKS")
    check(
        not os.path.isfile(os.path.join(ROOT, "err.txt"))
        or os.path.getsize(os.path.join(ROOT, "err.txt")) == 0,
        "err.txt is empty or absent",
    )
    check(
        not os.path.isfile(os.path.join(ROOT, "plugin.json.deprecated")),
        "No plugin.json.deprecated in root",
    )
    check(
        not os.path.isfile(os.path.join(ROOT, "marketplace.json.deprecated")),
        "No marketplace.json.deprecated in root",
    )
    check(
        not os.path.isdir(os.path.join(ROOT, ".tmp_core")),
        "No .tmp_core directory in root",
    )
    check(
        not os.path.isdir(os.path.join(ROOT, "skills-main")),
        "No skills-main directory in root",
    )
    root_txt_files = [
        name
        for name in os.listdir(ROOT)
        if name.endswith(".txt") and os.path.isfile(os.path.join(ROOT, name))
    ]
    allowed_root_txt = {"requirements.txt"}
    stray_txt = set(root_txt_files) - allowed_root_txt
    check(
        len(stray_txt) == 0,
        f"No stray .txt files in root (found: {sorted(stray_txt)})",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--warn-only",
        action="store_true",
        help="Do not exit with a non-zero status on failures.",
    )
    args = parser.parse_args()

    global _warn_only
    _warn_only = args.warn_only

    validate_skills()
    validate_agents()
    validate_commands()
    validate_hooks()
    validate_manifests()
    validate_desktop_source()
    validate_mcp_config_templates()
    validate_public_claims()
    validate_cleanliness()

    _section("SOURCE VALIDATION SUMMARY")
    print(f"  Passed:   {_passed}")
    print(f"  Failed:   {_failed}")
    print(f"  Warnings: {_warnings}")
    status = "ALL CLEAR" if _failed == 0 else "FAILURES DETECTED"
    print(f"  Status:   {status}")
    print(f"{'=' * 70}")
    if _warn_only:
        return 0
    return 0 if _failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
