#!/usr/bin/env python3
"""Boot a Desktop extension exactly as Claude Desktop would, on this platform.

Extracts a ``.mcpb``, reads ``manifest.json``, selects ``server.mcp_config``
plus the ``platform_overrides`` entry for the running platform, expands
``${__dirname}`` and ``${user_config.*}`` the way the host does, and spawns
the resulting ``command`` / ``args`` / ``env`` **in exec form** (no shell),
which is how Electron's ``child_process.spawn`` launches it. It then speaks
MCP over stdio: ``initialize``, ``tools/list`` (expects 12 tools) and
``tools/call integrity_check`` (expects ``passed`` and, when the manifest
pins a key, ``signature.source == "pinned"``).

This is the check that only a native Windows / macOS / Linux run can give:
that the launcher the manifest names (``sh`` + POSIX script, or
``powershell.exe -File`` + ``.ps1``) really starts the server on that OS.

    python scripts/boot_from_manifest.py dist/qector-claude-desktop-2.0.1.mcpb
    python scripts/boot_from_manifest.py <bundle> --python-path "C:\\Python312\\python.exe"
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import threading
import zipfile
from pathlib import Path


def _platform_key() -> str:
    if sys.platform.startswith("win"):
        return "win32"
    if sys.platform == "darwin":
        return "darwin"
    return "linux"


def _expand(value: str, *, dirname: Path, user_config: dict[str, str]) -> str:
    out = value.replace("${__dirname}", str(dirname))
    for key, setting in user_config.items():
        out = out.replace("${user_config." + key + "}", setting)
    return out


def _read_until(proc: subprocess.Popen, wanted: int, timeout: float) -> dict[int, dict]:
    responses: dict[int, dict] = {}
    stdout = proc.stdout
    assert stdout is not None

    def _pump() -> None:
        while len(responses) < wanted:
            line = stdout.readline()
            if not line:
                return
            text = line.decode("utf-8", "replace").strip()
            if not text.startswith("{"):
                print(f"[non-JSON stdout line] {text[:200]}", file=sys.stderr)
                continue
            message = json.loads(text)
            if "id" in message:
                responses[message["id"]] = message

    worker = threading.Thread(target=_pump, daemon=True)
    worker.start()
    worker.join(timeout)
    return responses


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--python-path", default=None, help="Value for ${user_config.python_path}; default: leave unset (launcher searches).")
    parser.add_argument("--audit-dir", default=None, help="Value for ${user_config.audit_dir}; default: unset.")
    parser.add_argument("--timeout", type=float, default=180.0)
    args = parser.parse_args(argv)

    with tempfile.TemporaryDirectory(prefix="qector-mcpb-") as tmp:
        root = Path(tmp)
        with zipfile.ZipFile(args.bundle) as archive:
            archive.extractall(root)
        manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
        config = dict(manifest["server"]["mcp_config"])
        override = config.get("platform_overrides", {}).get(_platform_key())
        if override:
            config = {**config, **override}
        user_config = {
            "python_path": args.python_path or "",
            "audit_dir": args.audit_dir or "",
        }
        # The host leaves an unset optional setting literally unexpanded or
        # empty; the launcher and the server tolerate both. Here we mimic
        # "empty" for unset values.
        command = _expand(config["command"], dirname=root, user_config=user_config)
        argv_list = [_expand(a, dirname=root, user_config=user_config) for a in config.get("args", [])]
        env = {k: v for k, v in os.environ.items() if not k.startswith("QECTOR_")}
        for key, value in config.get("env", {}).items():
            env[key] = _expand(value, dirname=root, user_config=user_config)
        pinned = env.get("QECTOR_INTEGRITY_PUBKEY") not in (None, "")
        print(f"platform={_platform_key()} command={command!r} args={argv_list}")
        print("env:", {k: v for k, v in env.items() if k.startswith("QECTOR_") or k == "PYTHONPATH"})
        try:
            proc = subprocess.Popen(
                [command, *argv_list],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                cwd=str(root),
            )
        except OSError as exc:
            print(f"SPAWN FAILED: {exc.__class__.__name__}: {exc}", file=sys.stderr)
            return 2
        frames = [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "boot_from_manifest", "version": "1"}}},
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
            {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "integrity_check", "arguments": {}}},
            {"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "airgap_status", "arguments": {}}},
            {"jsonrpc": "2.0", "id": 5, "method": "tools/call", "params": {"name": "decode_syndrome", "arguments": {"family": "repetition", "size": 3, "syndrome": [1, 0]}}},
        ]
        assert proc.stdin is not None
        proc.stdin.write(("\n".join(json.dumps(f) for f in frames) + "\n").encode("utf-8"))
        proc.stdin.flush()
        responses = _read_until(proc, 5, args.timeout)
        proc.stdin.close()
        try:
            proc.wait(timeout=30)
        except subprocess.TimeoutExpired:
            proc.kill()
        stderr_text = proc.stderr.read().decode("utf-8", "replace") if proc.stderr else ""
        for stream in (proc.stdout, proc.stderr):
            if stream:
                stream.close()
        if stderr_text.strip():
            print("--- server stderr ---", file=sys.stderr)
            print(stderr_text[-3000:], file=sys.stderr)
        failures: list[str] = []
        if 1 not in responses:
            failures.append("no initialize response")
        else:
            info = responses[1].get("result", {}).get("serverInfo", {})
            print("serverInfo:", info)
            if info.get("name") != "qector-secure-mcp":
                failures.append(f"unexpected server name {info.get('name')!r}")
        tools = responses.get(2, {}).get("result", {}).get("tools", [])
        print("tools:", len(tools))
        if len(tools) != 12:
            failures.append(f"expected 12 tools, got {len(tools)}")
        for rid, label in ((3, "integrity_check"), (4, "airgap_status"), (5, "decode_syndrome")):
            content = responses.get(rid, {}).get("result", {}).get("content", [])
            envelope = json.loads(content[0]["text"]) if content else {}
            status = envelope.get("status")
            print(f"{label}: status={status}")
            if label == "integrity_check":
                result = envelope.get("result", {})
                print("  passed:", result.get("passed"), "signature:", result.get("signature", {}).get("source"))
                if not result.get("passed"):
                    failures.append("integrity_check did not pass inside the extracted bundle")
                if pinned and result.get("signature", {}).get("source") != "pinned":
                    failures.append("manifest pins a key but the signature was not verified as pinned")
            elif label == "airgap_status":
                if not envelope.get("result", {}).get("air_gapped"):
                    failures.append("air_gapped is not true")
            elif label == "decode_syndrome":
                if status != "verified":
                    failures.append(f"decode_syndrome status {status!r}, expected verified")
        if proc.returncode not in (0, None):
            failures.append(f"server exit code {proc.returncode}")
        if failures:
            print("BOOT FAILED:", "; ".join(failures), file=sys.stderr)
            return 1
        print("BOOT OK")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
