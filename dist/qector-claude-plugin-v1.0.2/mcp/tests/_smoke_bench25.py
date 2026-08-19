"""Quick verify: bench server loads and 25 tools registered."""

import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "qector_bench", str(Path(__file__).parent.parent / "mcp_server_qector_bench.py")
)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
print(f"tools={len(m.TOOL_FUNCTIONS)} schemas={len(m.TOOLS)}")
for t in sorted(m.TOOL_FUNCTIONS.keys()):
    print(f"  {t}")
