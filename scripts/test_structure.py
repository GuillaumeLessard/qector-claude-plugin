"""Validate all skills, agents, commands, and hooks structurally."""

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
passed = 0
failed = 0
warnings = 0


def check(condition, label, warn_only=False):
    global passed, failed, warnings
    if condition:
        print(f"  PASS - {label}")
        passed += 1
    elif warn_only:
        print(f"  WARN - {label}")
        warnings += 1
    else:
        print(f"  FAIL - {label}")
        failed += 1


# ---- Skills ----
print(f"\n{'='*70}")
print("  SKILLS VALIDATION")
print(f"{'='*70}")

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
        with open(skill_md, "r", encoding="utf-8") as f:
            content = f.read()
        check(len(content) > 100, f"skills/{sd}/SKILL.md has substantive content ({len(content)} bytes)")
        # Check for YAML frontmatter
        has_frontmatter = content.startswith("---")
        check(has_frontmatter, f"skills/{sd}/SKILL.md has YAML frontmatter", warn_only=True)

# ---- Agents ----
print(f"\n{'='*70}")
print("  AGENTS VALIDATION")
print(f"{'='*70}")

agents_dir = os.path.join(ROOT, "agents")
agent_files = sorted(os.listdir(agents_dir))
print(f"  Found {len(agent_files)} agent files")
check(len(agent_files) >= 5, f"At least 5 agents present (got {len(agent_files)})")

for af in agent_files:
    if not af.endswith(".md"):
        continue
    agent_path = os.path.join(agents_dir, af)
    with open(agent_path, "r", encoding="utf-8") as f:
        content = f.read()
    check(len(content) > 200, f"agents/{af} has substantive content ({len(content)} bytes)")
    # Agents should reference tools or skills
    has_tool_ref = "tool" in content.lower() or "skill" in content.lower() or "mcp" in content.lower()
    check(has_tool_ref, f"agents/{af} references tools/skills/MCP")

# ---- Commands ----
print(f"\n{'='*70}")
print("  COMMANDS VALIDATION")
print(f"{'='*70}")

commands_dir = os.path.join(ROOT, "commands")
cmd_files = sorted(os.listdir(commands_dir))
print(f"  Found {len(cmd_files)} command files")
check(len(cmd_files) >= 3, f"At least 3 commands present (got {len(cmd_files)})")

for cf in cmd_files:
    if not cf.endswith(".md"):
        continue
    cmd_path = os.path.join(commands_dir, cf)
    with open(cmd_path, "r", encoding="utf-8") as f:
        content = f.read()
    check(len(content) > 100, f"commands/{cf} has substantive content ({len(content)} bytes)")

# ---- Hooks ----
print(f"\n{'='*70}")
print("  HOOKS VALIDATION")
print(f"{'='*70}")

hooks_path = os.path.join(ROOT, "hooks", "hooks.json")
check(os.path.isfile(hooks_path), "hooks/hooks.json exists")
if os.path.isfile(hooks_path):
    with open(hooks_path, "r", encoding="utf-8") as f:
        hooks_data = json.load(f)
    check(isinstance(hooks_data, dict), "hooks.json is valid JSON dict")
    hooks_section = hooks_data.get("hooks", {})
    check("SessionStart" in hooks_section, "hooks.json has SessionStart event")
    check("PostToolUse" in hooks_section, "hooks.json has PostToolUse event")
    for event_name, event_list in hooks_section.items():
        for i, entry in enumerate(event_list):
            inner_hooks = entry.get("hooks", [])
            for j, h in enumerate(inner_hooks):
                check("type" in h, f"hooks.{event_name}[{i}].hooks[{j}] has 'type' ({h.get('type','?')})")
                check("command" in h, f"hooks.{event_name}[{i}].hooks[{j}] has 'command'")

# ---- Plugin manifests ----
print(f"\n{'='*70}")
print("  PLUGIN MANIFESTS VALIDATION")
print(f"{'='*70}")

plugin_json = os.path.join(ROOT, ".claude-plugin", "plugin.json")
marketplace_json = os.path.join(ROOT, ".claude-plugin", "marketplace.json")
mcp_json = os.path.join(ROOT, ".mcp.json")

check(os.path.isfile(plugin_json), ".claude-plugin/plugin.json exists")
check(os.path.isfile(marketplace_json), ".claude-plugin/marketplace.json exists")
check(os.path.isfile(mcp_json), ".mcp.json exists")

if os.path.isfile(plugin_json):
    with open(plugin_json, "r", encoding="utf-8") as f:
        pj = json.load(f)
    check("name" in pj, f"plugin.json has 'name' field: {pj.get('name','?')}")
    check("version" in pj, f"plugin.json has 'version' field: {pj.get('version','?')}")

if os.path.isfile(marketplace_json):
    with open(marketplace_json, "r", encoding="utf-8") as f:
        mj = json.load(f)
    check("name" in mj, f"marketplace.json has 'name' field: {mj.get('name','?')}")

if os.path.isfile(mcp_json):
    with open(mcp_json, "r", encoding="utf-8") as f:
        mc = json.load(f)
    servers = mc.get("mcpServers", {})
    check("qector-library" in servers, "mcp.json registers qector-library server")
    check("qector-bench" in servers, "mcp.json registers qector-bench server")

# ---- Dist archives ----
print(f"\n{'='*70}")
print("  DIST ARCHIVES VALIDATION")
print(f"{'='*70}")

dist_dir = os.path.join(ROOT, "dist")
if os.path.isdir(dist_dir):
    dist_files = os.listdir(dist_dir)
    has_skill_zip = any("qector-core-skill" in f and f.endswith(".zip") for f in dist_files)
    has_plugin_zip = any("claude-plugin" in f and f.endswith(".zip") for f in dist_files)
    has_sha = any(f.endswith(".sha256") for f in dist_files)
    check(has_skill_zip, "dist/ contains qector-core-skill.zip")
    check(has_plugin_zip, "dist/ contains claude-plugin.zip")
    check(has_sha, "dist/ contains .sha256 sidecar(s)")
else:
    check(False, "dist/ directory exists")

# ---- No leftover junk ----
print(f"\n{'='*70}")
print("  CLEANLINESS CHECKS")
print(f"{'='*70}")

check(not os.path.isfile(os.path.join(ROOT, "err.txt")) or os.path.getsize(os.path.join(ROOT, "err.txt")) == 0,
      "err.txt is empty or absent")
check(not os.path.isfile(os.path.join(ROOT, "plugin.json.deprecated")),
      "No plugin.json.deprecated in root")
check(not os.path.isfile(os.path.join(ROOT, "marketplace.json.deprecated")),
      "No marketplace.json.deprecated in root")

# ---- Summary ----
print(f"\n{'='*70}")
print(f"  STRUCTURAL VALIDATION SUMMARY")
print(f"{'='*70}")
print(f"  Passed:   {passed}")
print(f"  Failed:   {failed}")
print(f"  Warnings: {warnings}")
status = "ALL CLEAR" if failed == 0 else "FAILURES DETECTED"
print(f"  Status:   {status}")
print(f"{'='*70}")
sys.exit(0 if failed == 0 else 1)
