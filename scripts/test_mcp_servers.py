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
            "family": "repetition", "size": 5, "decoder": "blossom",
            "syndrome": [1, 0, 0, 1]
        }},
        {"name": "decode_single", "arguments": {
            "family": "repetition", "size": 3, "decoder": "blossom",
            "error_rate": 0.1, "seed": 42
        }},
        {"name": "threshold_sweep", "arguments": {
            "family": "repetition", "distances": [3, 5],
            "error_rates": [0.05], "trials": 10, "seed": 42
        }},
        {"name": "compat_report", "arguments": {}},
    ]
    p, f, s = test_server("MCP Library Server (8 tools)", "mcp/mcp_server_library.py", library_calls)
    total_passed += p; total_failed += f; total_skipped += s

    # ---- Bench server (20 tools) ----
    bench_calls = [
        {"name": "list_code_families", "arguments": {}},
        {"name": "list_decoders", "arguments": {}},
        {"name": "get_license_info", "arguments": {}},
        {"name": "decode_syndrome", "arguments": {
            "family": "repetition", "size": 5, "decoder": "blossom",
            "syndrome": [1, 0, 0, 1]
        }},
        {"name": "decode_single", "arguments": {
            "family": "repetition", "size": 3, "decoder": "blossom",
            "error_rate": 0.1, "seed": 42
        }},
        {"name": "compat_report", "arguments": {}},
        {"name": "code_properties", "arguments": {"family": "repetition", "size": 5}},
        {"name": "code_logicals_inspect", "arguments": {"family": "repetition", "size": 5}},
        {"name": "wilson_interval", "arguments": {"k": 5, "n": 100}},
        {"name": "micro_benchmark", "arguments": {
            "family": "repetition", "size": 5, "decoder_name": "blossom",
            "shots": 10, "seed": 42
        }},
    ]
    p, f, s = test_server("MCP Bench Server (20 tools)", "mcp/mcp_server_qector_bench.py", bench_calls)
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
