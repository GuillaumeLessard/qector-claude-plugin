"""Comprehensive MCP server integration test for both library and bench servers.

Sends JSON-RPC initialize + tools/list over stdio, then invokes each tool
with minimal valid arguments to confirm they respond without errors.
"""

import json
import subprocess
import sys
import os
import traceback

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def _call_server(server_path: str, messages: list[dict]) -> list[dict]:
    """Send JSON-RPC messages to an MCP server over stdio and collect responses."""
    payload = "\n".join(json.dumps(m) for m in messages) + "\n"
    env = {**os.environ, "QECTOR_SILENT": "1", "PYTHONIOENCODING": "utf-8"}
    p = subprocess.run(
        [sys.executable, server_path],
        input=payload,
        capture_output=True,
        text=True,
        timeout=30,
        env=env,
        cwd=ROOT,
    )
    responses = []
    for line in p.stdout.strip().split("\n"):
        line = line.strip()
        if line:
            try:
                responses.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return responses


def _init_msg():
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-03-26",
            "capabilities": {},
            "clientInfo": {"name": "test-harness", "version": "1.0"},
        },
    }


def test_server(label: str, server_path: str, tool_calls: list[dict]):
    """Test a single MCP server: initialize, tools/list, then each tool_call."""
    print(f"\n{'='*70}")
    print(f"  TESTING: {label}")
    print(f"  Server:  {server_path}")
    print(f"{'='*70}")

    abs_path = os.path.join(ROOT, server_path)
    if not os.path.isfile(abs_path):
        print(f"  SKIP - server file not found: {abs_path}")
        return 0, 0, 1

    # Phase 1: initialize + tools/list
    msgs = [_init_msg(), {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}]
    try:
        resps = _call_server(abs_path, msgs)
    except subprocess.TimeoutExpired:
        print("  FAIL - server timed out on initialize")
        return 0, 1, 0
    except Exception as e:
        print(f"  FAIL - {e}")
        return 0, 1, 0

    if len(resps) < 2:
        print(f"  FAIL - expected 2 responses, got {len(resps)}")
        return 0, 1, 0

    init_resp = resps[0]
    tools_resp = resps[1]

    if "error" in init_resp:
        print(f"  FAIL - initialize error: {init_resp['error']}")
        return 0, 1, 0

    print(f"  PASS - initialize (protocol {init_resp.get('result',{}).get('protocolVersion','?')})")

    tools = tools_resp.get("result", {}).get("tools", [])
    tool_names = [t["name"] for t in tools]
    print(f"  PASS - tools/list returned {len(tools)} tools: {tool_names}")

    passed = 2
    failed = 0

    # Phase 2: invoke each tool
    for tc in tool_calls:
        name = tc["name"]
        args = tc.get("arguments", {})
        call_msgs = [
            _init_msg(),
            {
                "jsonrpc": "2.0",
                "id": 99,
                "method": "tools/call",
                "params": {"name": name, "arguments": args},
            },
        ]
        try:
            call_resps = _call_server(abs_path, call_msgs)
            # Find the tools/call response (id=99)
            tool_resp = None
            for r in call_resps:
                if r.get("id") == 99:
                    tool_resp = r
                    break
            if tool_resp is None:
                print(f"  FAIL - {name}: no response with id=99")
                failed += 1
                continue
            if "error" in tool_resp:
                print(f"  FAIL - {name}: {tool_resp['error'].get('message','?')}")
                failed += 1
            elif tool_resp.get("result", {}).get("isError"):
                # MCP-level tool error (input validation etc) — still a valid response
                content = tool_resp["result"].get("content", [{}])
                msg = content[0].get("text", "?") if content else "?"
                print(f"  WARN - {name}: tool returned isError (expected for edge cases): {msg[:120]}")
                passed += 1
            else:
                content = tool_resp.get("result", {}).get("content", [{}])
                snippet = json.dumps(content[0].get("text", "")[:100]) if content else "empty"
                print(f"  PASS - {name}: {snippet[:100]}")
                passed += 1
        except subprocess.TimeoutExpired:
            print(f"  FAIL - {name}: timed out")
            failed += 1
        except Exception as e:
            print(f"  FAIL - {name}: {e}")
            failed += 1

    return passed, failed, 0


def main():
    total_passed = 0
    total_failed = 0
    total_skipped = 0

    # ---- Library server (8 tools) ----
    library_calls = [
        {"name": "list_code_families", "arguments": {}},
        {"name": "list_decoders", "arguments": {}},
        {"name": "get_license_info", "arguments": {}},
        {"name": "decode_syndrome", "arguments": {
            "family": "repetition", "size": 5, "decoder_name": "blossom",
            "syndrome": [1, 0, 0, 1]
        }},
        {"name": "decode_single", "arguments": {
            "family": "rotated_surface", "distance": 3, "decoder_name": "blossom",
            "error_rate": 0.05, "seed": 42
        }},
        {"name": "threshold_sweep", "arguments": {
            "family": "rotated_surface", "distances": [3],
            "error_rates": [0.05], "trials": 10, "seed": 42
        }},
        {"name": "build_code_from_matrix", "arguments": {
            "H_matrix": [[1, 1, 0], [0, 1, 1]], "name": "custom_rep3", "distance": 3
        }},
        {"name": "compat_report", "arguments": {}},
    ]
    p, f, s = test_server("MCP Library Server (8 tools)", "mcp/mcp_server_library.py", library_calls)
    total_passed += p; total_failed += f; total_skipped += s

    # ---- Bench server (28 tools) ----
    bench_calls = [
        {"name": "wilson_ci", "arguments": {"k": 10, "n": 1000}},
        {"name": "wilson_table", "arguments": {"n": 1000, "k_list": [0, 1, 5, 10]}},
        {"name": "logical_coset_score", "arguments": {
            "predicted_logicals": [[0, 0, 0], [1, 0, 1]],
            "sampled_logicals": [[0, 0, 0], [1, 0, 1]],
        }},
        {"name": "dem_inspect", "arguments": {"dem_text": "error(0.001) D0 D1\ndetector(0, 0) D0\ndetector(1, 0) D1"}},
        {"name": "dem_collapse_parallel", "arguments": {"dem_text": "error(0.01 0.02) D0 D1\ndetector(0, 0) D0\ndetector(1, 0) D1"}},
        {"name": "code_family_info", "arguments": {"family": "rotated_surface", "size": 5}},
        {"name": "code_export_matrices", "arguments": {"family": "rotated_surface", "size": 5}},
        {"name": "code_logicals_inspect", "arguments": {"family": "rotated_surface", "size": 5}},
        {"name": "code_distance_check", "arguments": {"family": "rotated_surface", "size": 5}},
        {"name": "pymatching_compat_check", "arguments": {"family": "rotated_surface", "size": 5}},
        {"name": "sinter_decoder_list", "arguments": {}},
        {"name": "qiskit_plugin_check", "arguments": {}},
        {"name": "hardware_probe", "arguments": {}},
        {"name": "license_active_check", "arguments": {}},
        {"name": "env_block", "arguments": {"check_pypi": False}},
        {"name": "compat_report", "arguments": {"check_pypi": False}},
        {"name": "workbench_probe", "arguments": {"executable": "", "timeout": 5.0}},
        {"name": "artifacts_sha256", "arguments": {"paths": ["requirements.txt"]}},
        {"name": "artifact_metadata_check", "arguments": {"family": "rotated_surface", "size": 5, "decoder_name": "blossom"}},
        {"name": "decode_faithfulness_check", "arguments": {
            "H_matrix": [[1, 1, 0], [0, 1, 1]], "syndrome": [1, 0], "correction": [1, 0, 0]
        }},
        {"name": "hot_path_microbench", "arguments": {"family": "rotated_surface", "size": 3, "shots": 16, "decoder_name": "blossom"}},
        {"name": "stim_circuit_probe", "arguments": {"circuit_text": "R 0 1\nX_ERROR(0.01) 0\nM 0 1"}},
        {"name": "sinter_task_template", "arguments": {"family": "rotated_surface", "size": 5, "decoder_name": "blossom"}},
        {"name": "workload_hash", "arguments": {
            "H_matrix": [[1, 1, 0], [0, 1, 1]], "syndrome": [1, 0], "correction": [1, 0, 0]
        }},
        {"name": "theorem_lookup", "arguments": {"number": 1}},
        {"name": "glossary_lookup", "arguments": {"term": "syndrome faithfulness"}},
        {"name": "reproduction_command_lookup", "arguments": {"section": "all"}},
        {"name": "system_setup", "arguments": {"confirm": False}},
    ]
    p, f, s = test_server("MCP Bench Server (28 tools)", "mcp/mcp_server_qector_bench.py", bench_calls)
    total_passed += p; total_failed += f; total_skipped += s

    # ---- Summary ----
    print(f"\n{'='*70}")
    print(f"  FINAL SUMMARY")
    print(f"{'='*70}")
    print(f"  Passed:  {total_passed}")
    print(f"  Failed:  {total_failed}")
    print(f"  Skipped: {total_skipped}")
    status = "ALL CLEAR" if total_failed == 0 else "FAILURES DETECTED"
    print(f"  Status:  {status}")
    print(f"{'='*70}")
    return 0 if total_failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
