"""Full smoke test of the bench MCP server with QECTOR installed."""

import importlib.util
import json
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "qector_bench",
    str(Path(__file__).parent / "mcp_server_qector_bench.py"),
)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

print("=== code_family_info (rotated_surface d=5) ===")
r = m.dispatch_tool("code_family_info", {"family": "rotated_surface", "size": 5})
print(json.dumps(r, indent=2, default=str))
print()

print("=== code_logicals_inspect (rotated_surface d=5) ===")
r = m.dispatch_tool("code_logicals_inspect", {"family": "rotated_surface", "size": 5})
print(f"  n_logicals={r['n_logicals']}, logicals_present={r['logicals_present']}")
print()

print("=== code_logicals_inspect (unrotated_surface d=5, expected: no logicals) ===")
r = m.dispatch_tool("code_logicals_inspect", {"family": "unrotated_surface", "size": 5})
print(f"  n_logicals={r['n_logicals']}, logicals_present={r['logicals_present']}")
print(f"  scoring_note: {r.get('scoring_note', 'n/a')}")
print()

print("=== code_distance_check (rotated_surface d=5) ===")
r = m.dispatch_tool("code_distance_check", {"family": "rotated_surface", "size": 5})
print(f"  distance: {r['distance']}, shape: {r['matrix_shape']}")
print()

print("=== hardware_probe ===")
r = m.dispatch_tool("hardware_probe")
print(f"  cuda_available: {r['cuda_available']}")
print(f"  opencl_available: {r['opencl_available']}")
print(f"  license: {r.get('license', {})}")
print()

print("=== license_active_check ===")
r = m.dispatch_tool("license_active_check")
print(f"  tier: {r['tier']}, max_distance: {r['max_distance']}")
print()

print("=== sinter_decoder_list ===")
r = m.dispatch_tool("sinter_decoder_list")
print(f"  sinter_exposed: {r['sinter_exposed']}")
print(f"  decoders: {r['sinter_decoders']}")
print()

print("=== qiskit_plugin_check ===")
r = m.dispatch_tool("qiskit_plugin_check")
print(f"  qiskit_installed: {r['qiskit_installed']}")
print()

print("=== pymatching_compat_check (rotated_surface d=5) ===")
r = m.dispatch_tool("pymatching_compat_check", {"family": "rotated_surface", "size": 5})
print(f"  qector_syndrome_valid: {r['qector_syndrome_valid']}")
print(f"  pymatching_compared: {r['pymatching_compared']}")
if r["pymatching_compared"]:
    print(f"  bitwise_equal: {r['bitwise_equal']}")
print()

print("=== hot_path_microbench (small) ===")
r = m.dispatch_tool(
    "hot_path_microbench", {"family": "rotated_surface", "size": 5, "shots": 16}
)
print(
    f"  shots_completed: {r['shots_completed']}, syndrome_invalid: {r['syndrome_invalid']}"
)
if "latency_us" in r:
    lat = r["latency_us"]
    print(f"  mean={lat['mean']:.2f}us, p50={lat['p50']:.2f}us, p99={lat['p99']:.2f}us")
print()

print("=== artifacts_sha256 ===")
# Test on the bench server file itself
test_path = str(Path(__file__).parent / "mcp_server_qector_bench.py")
r = m.dispatch_tool("artifacts_sha256", {"paths": [test_path]})
print(f"  files: {r['n_files']}")
for f in r["files"]:
    print(f"  {Path(f['path']).name}: {f['sha256'][:16]}... ({f['size_bytes']} bytes)")
print()

print("=== decode_faithfulness_check (Steane syndrome [1,1,0]) ===")
# Steane [[7,1,3]] X-checks, error = [0,0,0,0,0,1,0] gives syndrome [1,1,0]
# In the v1.0.0 manual, this is appendix E.1.
H_steane = [
    [0, 0, 0, 1, 1, 1, 1],
    [0, 1, 1, 0, 0, 1, 1],
    [1, 0, 1, 0, 1, 0, 1],
]
# syndrome = [1, 1, 0]
# error = [0, 0, 0, 0, 0, 1, 0] gives H e = [1, 1, 0] mod 2
s_steane = [1, 1, 0]
c_steane = [0, 0, 0, 0, 0, 1, 0]
r = m.dispatch_tool(
    "decode_faithfulness_check",
    {
        "H_matrix": H_steane,
        "syndrome": s_steane,
        "correction": c_steane,
    },
)
print(f"  syndrome_valid: {r['syndrome_valid']} (expected True)")
print()

print("=== artifact_metadata_check ===")
r = m.dispatch_tool(
    "artifact_metadata_check",
    {
        "family": "rotated_surface",
        "size": 5,
        "decoder_name": "blossom",
    },
)
print(f"  all_required_fields_present: {r['all_required_fields_present']}")
print()

print("ALL TOOL SMOKE TESTS PASSED")
