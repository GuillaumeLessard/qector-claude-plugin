import os
os.environ["QECTOR_SILENT"] = "1"

import importlib.util
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "skills"
MCP = ROOT / "mcp"

# Prevent local mcp/ directory from shadowing the installed mcp SDK package
while str(MCP) in sys.path:
    sys.path.remove(str(MCP))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

print("=" * 60)
print("SKILLS VALIDATION")
print("=" * 60)

skill_dirs = sorted(
    d for d in SKILLS.iterdir() if d.is_dir() and d.name.startswith("qector-")
)
print(f"Total qector-* skills: {len(skill_dirs)}")
print()

errors = []
for sd in skill_dirs:
    skill_file = sd / "SKILL.md"
    if not skill_file.is_file():
        errors.append(f"{sd.name}: missing SKILL.md")
        continue
    text = skill_file.read_text(encoding="utf-8")
    # Frontmatter check
    if not text.startswith("---"):
        errors.append(f"{sd.name}: no frontmatter")
        continue
    end = text.find("\n---\n", 4)
    if end < 0:
        errors.append(f"{sd.name}: frontmatter not closed")
        continue
    fm = text[4:end]
    m_name = re.search(r"^name:\s*(\S+)", fm, re.MULTILINE)
    m_desc = re.search(r"^description:\s*>", fm, re.MULTILINE)
    if not m_name:
        errors.append(f"{sd.name}: frontmatter missing name")
        continue
    name = m_name.group(1)
    has_desc = bool(m_desc) or bool(re.search(r"^description:\s*\S", fm, re.MULTILINE))
    if not has_desc:
        errors.append(f"{sd.name}: frontmatter missing description")
        continue
    # Content size
    body_len = len(text) - end - 5
    status = "OK"
    if body_len < 1500:
        status = "SHORT"
    print(f"  {sd.name:<40s}  {body_len:>6d} bytes  [{status}]")

print()
if errors:
    print("ERRORS:")
    for e in errors:
        print(f"  - {e}")
else:
    print("All skills have valid frontmatter.")
print()

print("=" * 60)
print("MCP SERVERS VALIDATION")
print("=" * 60)

for srv_name in ("mcp_server_library.py", "mcp_server_qector_bench.py"):
    srv_path = MCP / srv_name
    if not srv_path.is_file():
        print(f"  {srv_name}: MISSING")
        continue
    spec = importlib.util.spec_from_file_location(
        srv_name.replace(".py", ""), str(srv_path)
    )
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    n_tools = len(m.TOOL_FUNCTIONS)
    n_schema = len(m.TOOLS)
    print(f"  {srv_name}: {n_tools} tools, {n_schema} schemas, server={m.SERVER_NAME}")
    # Show tool names
    for t in sorted(m.TOOL_FUNCTIONS.keys()):
        print(f"    - {t}")

print()
print("=" * 60)
print("MCP JSON CONFIG")
print("=" * 60)
mcp_json = ROOT / ".mcp.json"
if mcp_json.is_file():
    config = json.loads(mcp_json.read_text(encoding="utf-8"))
    servers = config.get("mcpServers", {})
    print(f"  {len(servers)} servers registered in .mcp.json:")
    for name, cfg in servers.items():
        print(f"    - {name}: {cfg.get('command')} {cfg.get('args', [])}")
else:
    print("  .mcp.json MISSING")

print()
print("=" * 60)
print("DONE")
print("=" * 60)
