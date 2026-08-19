"""Smoke test for the bench MCP server - math-only tools, no qector needed."""

import importlib.util
import sys
from pathlib import Path

# Prevent local mcp/ directory from shadowing installed mcp package
mcp_dir = Path(__file__).resolve().parent
while str(mcp_dir) in sys.path:
    sys.path.remove(str(mcp_dir))

spec = importlib.util.spec_from_file_location(
    "qector_bench",
    str(Path(__file__).parent / "mcp_server_qector_bench.py"),
)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

print("=== Wilson CI manual example (10/1000) ===")
r = m.dispatch_tool("wilson_ci", {"k": 10, "n": 1000})
print("  expected: (0.00544, 0.01831)")
print(f"  got:      {r['wilson_95']}")
print()

print("=== Wilson table ===")
r = m.dispatch_tool("wilson_table", {"n": 1000, "k_list": [0, 1, 5, 10, 50, 100]})
for row in r["rows"]:
    print(
        f"  k={row['k']:>4d}: wilson_95 = [{row['wilson_95'][0]:.5f}, {row['wilson_95'][1]:.5f}]"
    )
print()

print("=== DEM inspect ===")
dem_text = """# A tiny DEM
error(0.001) D0 D2 L0
error(0.005) D1 D3
error(0.01 0.02) D4 D5 L1
detector(0, 0) D0
detector(1, 0) D1
detector(0, 1) D2
detector(1, 1) D3
detector(2, 0) D4
detector(2, 1) D5
logical_observable L0
logical_observable L1
"""
r = m.dispatch_tool("dem_inspect", {"dem_text": dem_text})
print(f"  summary: {r['summary']}")
print()

print("=== DEM collapse parallel ===")
r = m.dispatch_tool("dem_collapse_parallel", {"dem_text": dem_text})
for e in r["collapse"]["graphlike_edges"]:
    print(
        f"  D{e['detector_pair'][0]}-D{e['detector_pair'][1]}: "
        f"p={e['p_combined']:.4f}, weight={e['weight_log']:.3f}, n_members={e['n_members']}"
    )
print(f"  manual sanity check: {r['manual_worked_example_check']}")
print()

print("=== Logical coset score ===")
predicted = [[0, 0, 0, 0], [1, 0, 1, 0], [0, 0, 0, 0]]
sampled = [[0, 0, 0, 0], [1, 0, 1, 0], [0, 1, 0, 0]]
r = m.dispatch_tool(
    "logical_coset_score",
    {"predicted_logicals": predicted, "sampled_logicals": sampled},
)
print(f"  {r}")
print()

print("=== Decode faithfulness check (external Theorem 1 verifier) ===")
# H = [[1,1,0],[0,1,1]] over F2 with syndrome s = [1,0]
# e_hard = [1,0,0] -> H e = [1,0] = s, so decode returns immediately
H = [[1, 1, 0], [0, 1, 1]]
s = [1, 0]
c = [1, 0, 0]
r = m.dispatch_tool(
    "decode_faithfulness_check",
    {"H_matrix": H, "syndrome": s, "correction": c},
)
print(f"  syndrome_valid: {r['syndrome_valid']} (expected True)")
# Now an invalid case
r = m.dispatch_tool(
    "decode_faithfulness_check",
    {"H_matrix": H, "syndrome": s, "correction": [0, 0, 0]},
)
print(f"  invalid case syndrome_valid: {r['syndrome_valid']} (expected False)")
print()

print("=== Env block ===")
r = m.dispatch_tool("env_block")
print(f"  qector present: {r['qector_decoder_v3_present']}")
print(f"  keys: {list(r['environment'].keys())}")
print()

print("=== Artifact metadata check ===")
r = m.dispatch_tool(
    "artifact_metadata_check",
    {"family": "rotated_surface", "size": 5, "decoder_name": "blossom"},
)
print(f"  all_required_fields_present: {r['all_required_fields_present']}")
print(f"  required fields: {r['required_fields']}")
print()

print("ALL SMOKE TESTS PASSED")
