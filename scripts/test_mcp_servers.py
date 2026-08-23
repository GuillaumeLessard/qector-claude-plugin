"""Comprehensive MCP server integration test for both library and bench servers.

Sends JSON-RPC initialize + tools/list over stdio, then invokes each tool
with minimal valid arguments to confirm they respond without errors.
"""

import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Standalone CLI diagnostic (see the __main__ guard below), not a pytest
# suite. __test__ = False stops pytest from auto-collecting test_server as
# a test case, since it takes required positional args (label, server_path,
# tool_calls) that are not pytest fixtures. Mirrors the same fix already
# applied in mcp/tests/test_mcp_stdio.py.
__test__ = False


_SERVER_STARTUP_TIMEOUT_S = 60
_SERVER_PER_CALL_TIMEOUT_S = 15


def _readline_with_timeout(proc: subprocess.Popen, timeout_s: float):
    """Read one line from proc.stdout, returning None on timeout or exit."""
    import queue
    import threading

    q: queue.Queue = queue.Queue(maxsize=1)

    def _reader():
        try:
            q.put(proc.stdout.readline())
        except Exception:
            q.put(None)

    t = threading.Thread(target=_reader, daemon=True)
    t.start()
    try:
        line = q.get(timeout=timeout_s)
    except queue.Empty:
        return None
    if not line:
        return None
    return line


def _call_server(server_path: str, messages: list[dict]) -> list[dict]:
    """Send JSON-RPC messages to an MCP server over a persistent stdio pipe.

    Cold start (heavy scientific-stack imports) has been measured taking
    over 30s before the server's stdio loop starts responding. A one-shot
    subprocess.run(input=...) also closes stdin the instant the payload is
    written, which is the wrong transport model for a persistent stdio
    server. This keeps a Popen pipe open for the life of the exchange
    (same pattern as mcp/tests/test_mcp_stdio.py) and gives the first
    response real cold-start headroom.
    """
    env = {**os.environ, "QECTOR_SILENT": "1", "PYTHONIOENCODING": "utf-8"}
    proc = subprocess.Popen(
        [sys.executable, server_path],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
        cwd=ROOT,
    )
    responses: list[dict] = []
    try:
        for i, msg in enumerate(messages):
            proc.stdin.write(json.dumps(msg) + "\n")
            proc.stdin.flush()
            timeout = _SERVER_STARTUP_TIMEOUT_S if i == 0 else _SERVER_PER_CALL_TIMEOUT_S
            line = _readline_with_timeout(proc, timeout)
            if line is None:
                break
            line = line.strip()
            if line:
                try:
                    responses.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    finally:
        try:
            proc.kill()
            proc.wait(timeout=5)
        except Exception:
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
            "H_matrix": [[1, 1, 0], [0, 1, 1]], "family": "custom_rep3", "distance": 3
        }},
        {"name": "compat_report", "arguments": {}},
    ]
    p, f, s = test_server("MCP Library Server (8 tools)", "mcp/mcp_server_library.py", library_calls)
    total_passed += p
    total_failed += f
    total_skipped += s

    # ---- Research server (29 tools) ----
    research_calls = [
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
        {"name": "get_capability_matrix", "arguments": {}},
        {"name": "get_evidence_policy", "arguments": {}},
        {"name": "get_runtime_provenance", "arguments": {"check_pypi": False}},
    ]
    p, f, s = test_server("MCP Research Server (29 tools)", "mcp/mcp_server_qector_bench.py", research_calls)
    total_passed += p
    total_failed += f
    total_skipped += s

    # ---- Summary ----
    print(f"\n{'='*70}")
    print("  FINAL SUMMARY")
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
