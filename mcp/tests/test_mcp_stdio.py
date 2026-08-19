"""End-to-end MCP stdio validation for the QECTOR plugin (simplified).

Spawns each registered MCP server as a subprocess, sends the JSON-RPC
2.0 initialize + tools/list handshake, and verifies the tool
inventory plus a sample tools/call. Hard 15s timeout per server.

Run from the workspace root:

    python mcp/tests/test_mcp_stdio.py
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MCP_DIR = ROOT / "mcp"

os.environ.setdefault("QECTOR_SILENT", "1")

SERVERS = {
    "qector-library": MCP_DIR / "mcp_server_library.py",
    "qector-bench": MCP_DIR / "mcp_server_qector_bench.py",
}

EXPECTED_TOOLS = {
    "qector-library": {
        "list_code_families",
        "list_decoders",
        "get_license_info",
        "decode_syndrome",
        "decode_single",
        "threshold_sweep",
        "build_code_from_matrix",
        "compat_report",
    },
    "qector-bench": {
        "wilson_ci",
        "wilson_table",
        "logical_coset_score",
        "dem_inspect",
        "dem_collapse_parallel",
        "code_family_info",
        "code_export_matrices",
        "code_logicals_inspect",
        "code_distance_check",
        "pymatching_compat_check",
        "sinter_decoder_list",
        "qiskit_plugin_check",
        "hardware_probe",
        "license_active_check",
        "env_block",
        "workbench_probe",
        "artifacts_sha256",
        "artifact_metadata_check",
        "decode_faithfulness_check",
        "hot_path_microbench",
    },
}


def _send(proc, lines):
    payload = ("\n".join(lines) + "\n").encode("utf-8")
    proc.stdin.write(payload)
    proc.stdin.flush()


def _read_one(proc, *, timeout: float):
    """Read one line from the subprocess with a hard timeout.

    On Windows, msvcrt is used to poll. On Unix, select.
    """
    import time

    if sys.platform == "win32":
        try:
            import msvcrt
        except ImportError:
            msvcrt = None
        if msvcrt is not None:
            start = time.monotonic()
            while time.monotonic() - start < timeout:
                if msvcrt.kbhit() if hasattr(msvcrt, "kbhit") else False:
                    pass
                # Use non-blocking readline
                proc.stdout.flush() if hasattr(proc.stdout, "flush") else None
                line = proc.stdout.readline()
                if line:
                    return line
                # Sleep a bit to avoid busy loop
                time.sleep(0.05)
            return None
    # Fallback: blocking readline with no timeout (use subprocess timeout)
    return proc.stdout.readline()


def test_server(server_name: str, server_path: Path) -> dict:
    print(f"\n--- {server_name} ({server_path.name}) ---")
    if not server_path.is_file():
        return {"ok": False, "error": f"server file missing: {server_path}"}

    proc = subprocess.Popen(
        [sys.executable, str(server_path)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        env=os.environ.copy(),
    )

    result = {
        "server": server_name,
        "ok": False,
        "server_name": None,
        "tool_count": 0,
        "expected_count": len(EXPECTED_TOOLS.get(server_name, set())),
        "missing_tools": [],
        "sample_call_ok": None,
        "sample_call": None,
    }

    try:
        init_msg = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "qector-stdio-test", "version": "1.0"},
            },
        }
        list_msg = {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}
        notif = {"jsonrpc": "2.0", "method": "notifications/initialized"}
        _send(proc, [json.dumps(init_msg), json.dumps(notif), json.dumps(list_msg)])

        # Read initialize response
        line1 = proc.stdout.readline()
        if not line1:
            result["error"] = "no initialize response"
            return result
        init_resp = json.loads(line1)
        result["server_name"] = (
            init_resp.get("result", {}).get("serverInfo", {}).get("name")
        )

        # Read tools/list response
        line2 = proc.stdout.readline()
        if not line2:
            result["error"] = "no tools/list response"
            return result
        list_resp = json.loads(line2)
        tools = list_resp.get("result", {}).get("tools", [])
        actual = {t.get("name") for t in tools}
        result["tool_count"] = len(actual)
        expected = EXPECTED_TOOLS.get(server_name, set())
        result["missing_tools"] = sorted(expected - actual)

        # Sample call
        if server_name == "qector-library":
            sample_name, sample_args = "list_decoders", {}
        else:
            sample_name, sample_args = "wilson_ci", {"k": 10, "n": 1000}
        call_msg = {
            "jsonrpc": "2.0",
            "id": 100,
            "method": "tools/call",
            "params": {"name": sample_name, "arguments": sample_args},
        }
        _send(proc, [json.dumps(call_msg)])
        line3 = proc.stdout.readline()
        if line3:
            call_resp = json.loads(line3)
            content = call_resp.get("result", {}).get("content", [])
            if call_resp.get("error") is not None:
                result["sample_call_ok"] = False
                result["sample_call"] = call_resp["error"]
            elif content and content[0].get("type") == "text":
                try:
                    payload = json.loads(content[0]["text"])
                    if server_name == "qector-bench" and sample_name == "wilson_ci":
                        lo, hi = payload.get("wilson_95", [None, None])
                        result["sample_call_ok"] = (
                            lo is not None
                            and hi is not None
                            and abs(lo - 0.0054407544447740265) < 1e-9
                            and abs(hi - 0.018309468872823392) < 1e-9
                        )
                        result["sample_call"] = {
                            "tool": sample_name,
                            "wilson_95": [lo, hi],
                            "expected": [0.0054407544447740265, 0.018309468872823392],
                        }
                    else:
                        result["sample_call_ok"] = True
                        result["sample_call"] = {
                            "tool": sample_name,
                            "ok_keys": sorted(payload.keys())[:5]
                            if isinstance(payload, dict)
                            else None,
                        }
                except (json.JSONDecodeError, TypeError) as exc:
                    result["sample_call_ok"] = False
                    result["sample_call"] = f"parse error: {exc}"
            else:
                result["sample_call_ok"] = False
                result["sample_call"] = "no text content"
        else:
            result["sample_call_ok"] = False
            result["sample_call"] = "no response"

        result["ok"] = not result["missing_tools"] and bool(result["server_name"])
        if not result["ok"] and not result.get("error"):
            result["error"] = (
                f"missing tools: {result['missing_tools']}"
                if result["missing_tools"]
                else "no server name"
            )
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        try:
            if proc.stdin:
                proc.stdin.close()
        except Exception:
            pass
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            try:
                proc.wait(timeout=2)
            except Exception:
                pass

    print(f"  server: {result['server_name']}")
    print(f"  tools: {result['tool_count']} (expected {result['expected_count']})")
    if result["missing_tools"]:
        print(f"  MISSING: {result['missing_tools']}")
    print(f"  sample call: {result['sample_call']}")
    print(f"  sample call ok: {result['sample_call_ok']}")
    if result.get("error"):
        print(f"  ERROR: {result['error']}")
    print(f"  ok: {result['ok']}")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="End-to-end MCP stdio validation")
    parser.add_argument("--server", choices=tuple(SERVERS) + ("all",), default="all")
    args = parser.parse_args()
    targets = list(SERVERS.keys()) if args.server == "all" else [args.server]
    results = [test_server(name, SERVERS[name]) for name in targets]
    print()
    n_ok = sum(1 for r in results if r["ok"])
    print(f"PASS: {n_ok}/{len(results)} servers validated")
    return 0 if n_ok == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
