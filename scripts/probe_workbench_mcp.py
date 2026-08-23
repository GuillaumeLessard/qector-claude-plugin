"""
QECTOR Workbench MCP - live probe script.

Performs a fresh MCP stdio handshake against a target Workbench executable and
prints the device-local transcript: initialize, mcp_status, tools/list count,
and representative tool calls. Output is never bundled by this repository.

Usage:
    python bin/probe_workbench_mcp.py --executable "C:\\path\\to\\QectorWorkbench-Portable.exe"
    python bin/probe_workbench_mcp.py --tools --limit 5   # list N tool names

Requires only the Python standard library. The target executable path is
required so the probe cannot accidentally validate a different machine.
"""

import argparse
import json
import os
import subprocess
import sys

ENV = os.environ.copy()
ENV["QECTOR_SILENT"] = "1"
WORKBENCH_PROTOCOL_VERSION = "2025-03-26"


def send(proc, lines):
    payload = ("\n".join(lines) + "\n").encode("utf-8")
    proc.stdin.write(payload)
    proc.stdin.flush()


def main():
    parser = argparse.ArgumentParser(description="QECTOR Workbench MCP live probe")
    parser.add_argument("--executable", required=True)
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--tools", action="store_true", help="list tool names and exit")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    if not os.path.isfile(args.executable):
        sys.exit(f"Executable not found: {args.executable}")

    try:
        proc = subprocess.Popen(
            [args.executable, "--mcp"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            env=ENV,
        )
    except OSError as exc:
        sys.exit(f"Failed to start executable: {exc}")

    try:
        init = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": WORKBENCH_PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "qector-probe", "version": "1.0"},
            },
        }
        notif = {"jsonrpc": "2.0", "method": "notifications/initialized"}
        status = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": "mcp_status", "arguments": {}},
        }
        tlist = {"jsonrpc": "2.0", "id": 3, "method": "tools/list"}
        send(proc, [json.dumps(init), json.dumps(notif)])

        if args.tools:
            send(proc, [json.dumps(tlist)])
        else:
            send(proc, [json.dumps(status), json.dumps(tlist)])

        responses = 2 if args.tools else 3
        for _ in range(responses):
            line = proc.stdout.readline()
            if not line:
                break
            try:
                resp = json.loads(line)
            except json.JSONDecodeError:
                print(
                    f"[raw output]: {line.decode('utf-8', errors='replace').rstrip()}"
                )
                continue
            if args.tools and resp.get("id") == 3:
                tools = resp.get("result", {}).get("tools", [])
                names = [t["name"] for t in tools]
                shown = names if args.limit is None else names[: args.limit]
                print(f"tools={len(tools)}")
                for n in shown:
                    print(n)
            else:
                print(json.dumps(resp, indent=2))
    finally:
        if proc.stdin:
            try:
                proc.stdin.close()
            except Exception:
                pass
        try:
            proc.wait(timeout=args.timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()


if __name__ == "__main__":
    main()
