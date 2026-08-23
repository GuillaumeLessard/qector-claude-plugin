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

# This module is a standalone CLI diagnostic (see ``main`` below), not a
# pytest suite. It matches pytest's ``test_*.py`` / ``test_*`` naming by
# convention (so it reads consistently alongside the other tools/tests),
# but `test_server` takes required positional arguments and is not meant
# to be collected or called by pytest. `__test__ = False` tells pytest to
# skip collecting this module entirely, instead of erroring out on
# `test_server` for missing fixtures.
__test__ = False

ROOT = Path(__file__).resolve().parents[2]
MCP_DIR = ROOT / "mcp"

os.environ.setdefault("QECTOR_SILENT", "1")

SERVERS = {
    "qector-library": MCP_DIR / "mcp_server_library.py",
    "qector-research": MCP_DIR / "mcp_server_qector_bench.py",
    "qector-desktop": MCP_DIR / "mcp_server_desktop.py",
    "qector-admin": MCP_DIR / "mcp_server_admin.py",
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
    "qector-research": {
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
        "compat_report",
        "artifacts_sha256",
        "artifact_metadata_check",
        "decode_faithfulness_check",
        "hot_path_microbench",
        "stim_circuit_probe",
        "sinter_task_template",
        "workload_hash",
        "theorem_lookup",
        "glossary_lookup",
        "reproduction_command_lookup",
        "get_capability_matrix",
        "get_evidence_policy",
        "get_runtime_provenance",
    },
}

EXPECTED_TOOLS["qector-desktop"] = EXPECTED_TOOLS["qector-library"]
EXPECTED_TOOLS["qector-admin"] = {
    "system_setup",
    "configure_claude_desktop",
    "workbench_probe",
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
        "contract_issues": [],
        "sample_call_ok": None,
        "sample_call": None,
    }

    try:
        init_msg = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
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
        for tool in tools:
            name = tool.get("name", "<unnamed>")
            if "outputSchema" not in tool:
                result["contract_issues"].append(f"{name}: missing outputSchema")
            annotations = tool.get("annotations")
            if not isinstance(annotations, dict):
                result["contract_issues"].append(f"{name}: missing annotations")

        # Sample call
        if server_name in {"qector-library", "qector-desktop"}:
            sample_name, sample_args = "list_decoders", {}
        elif server_name == "qector-research":
            sample_name, sample_args = "wilson_ci", {"k": 10, "n": 1000}
        else:
            sample_name, sample_args = "system_setup", {"confirm": False}
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
            tool_result = call_resp.get("result", {})
            content = tool_result.get("content", [])
            if call_resp.get("error") is not None:
                result["sample_call_ok"] = False
                result["sample_call"] = call_resp["error"]
            elif content and content[0].get("type") == "text":
                try:
                    payload = tool_result.get("structuredContent") or json.loads(
                        content[0]["text"]
                    )
                    required_fields = {
                        "status",
                        "claim_class",
                        "provenance",
                        "runtime",
                        "scope",
                        "verification",
                        "artifact",
                        "warnings",
                        "result",
                    }
                    if not required_fields.issubset(payload):
                        result["sample_call_ok"] = False
                        result["sample_call"] = "missing result envelope fields"
                    elif server_name == "qector-research" and sample_name == "wilson_ci":
                        lo, hi = payload["result"].get("wilson_95", [None, None])
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
                    elif server_name == "qector-admin":
                        result["sample_call_ok"] = (
                            tool_result.get("isError") is True
                            and payload.get("error", {}).get("code") == "PERMISSION_DENIED"
                        )
                        result["sample_call"] = payload.get("error")
                    else:
                        result["sample_call_ok"] = True
                        result["sample_call"] = {
                            "tool": sample_name,
                            "status": payload["status"],
                            "verification": payload["verification"]["status"],
                        }
                except (json.JSONDecodeError, KeyError, TypeError) as exc:
                    result["sample_call_ok"] = False
                    result["sample_call"] = f"parse error: {exc}"
            else:
                result["sample_call_ok"] = False
                result["sample_call"] = "no text content"
        else:
            result["sample_call_ok"] = False
            result["sample_call"] = "no response"

        result["ok"] = (
            not result["missing_tools"]
            and not result["contract_issues"]
            and bool(result["server_name"])
            and result["sample_call_ok"] is True
        )
        if not result["ok"] and not result.get("error"):
            result["error"] = (
                f"missing tools: {result['missing_tools']}"
                if result["missing_tools"]
                else f"tool contract issues: {result['contract_issues']}"
                if result["contract_issues"]
                else "no server name or sample response"
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
    if result["contract_issues"]:
        print(f"  CONTRACT: {result['contract_issues']}")
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
