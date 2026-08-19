#!/usr/bin/env python3
"""
Claude Desktop Windows App Connector & Extension Installer for QECTOR Plugin.

Provides complete, zero-friction integration for Claude Desktop on Windows (and macOS/Linux):
1. Registers MCP servers (`qector-library` and `qector-bench`) in `claude_desktop_config.json`.
2. Installs QECTOR as a first-class Custom Connector / Extension in Claude Desktop Settings
   (`Claude Extensions/ant.dir.gh.guillaumelessard.qector` & `extensions-installations.json`).
3. Non-destructively preserves existing servers and preferences with automatic timestamped backups.
4. Normalizes all Windows paths to forward slashes to prevent JSON escape sequence crashes.
5. Injects `QECTOR_SILENT=1` and `PYTHONUNBUFFERED=1` to guarantee pure stdio JSON-RPC.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import importlib.metadata
import json
import os
import platform
import shutil
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
LIBRARY_SCRIPT = ROOT / "mcp" / "mcp_server_library.py"
BENCH_SCRIPT = ROOT / "mcp" / "mcp_server_qector_bench.py"
EXTENSION_DIR_SRC = ROOT / "extension"
EXTENSION_ID = "ant.dir.gh.guillaumelessard.qector"


def get_claude_base_dir() -> Path:
    """Resolve the OS-specific Claude Desktop roaming AppData directory."""
    system = platform.system()
    if system == "Windows":
        app_data = os.environ.get("APPDATA")
        if app_data:
            return Path(app_data) / "Claude"
        return Path.home() / "AppData" / "Roaming" / "Claude"
    elif system == "Darwin":  # macOS
        return Path.home() / "Library" / "Application Support" / "Claude"
    else:  # Linux / generic
        config_home = os.environ.get("XDG_CONFIG_HOME")
        if config_home:
            return Path(config_home) / "Claude"
        return Path.home() / ".config" / "Claude"


def check_runtime(python_exe: str) -> dict[str, Any]:
    """Audit the runtime environment and packages."""
    diag: dict[str, Any] = {
        "python_executable": python_exe,
        "python_version": platform.python_version(),
        "is_venv": sys.prefix != sys.base_prefix,
        "qector_wheel": None,
        "mcp_sdk": None,
        "numpy": None,
        "library_script_exists": LIBRARY_SCRIPT.is_file(),
        "bench_script_exists": BENCH_SCRIPT.is_file(),
        "ready": False,
        "errors": [],
    }

    try:
        diag["qector_wheel"] = importlib.metadata.version("qector-decoder-v3")
    except Exception:
        diag["errors"].append("qector-decoder-v3 package not found in active Python environment")

    try:
        diag["mcp_sdk"] = importlib.metadata.version("mcp")
    except Exception:
        diag["errors"].append("mcp package not found in active Python environment")

    try:
        diag["numpy"] = importlib.metadata.version("numpy")
    except Exception:
        diag["errors"].append("numpy package not found in active Python environment")

    if not diag["library_script_exists"]:
        diag["errors"].append(f"Missing library server script: {LIBRARY_SCRIPT}")
    if not diag["bench_script_exists"]:
        diag["errors"].append(f"Missing bench server script: {BENCH_SCRIPT}")

    diag["ready"] = len(diag["errors"]) == 0
    return diag


def build_qector_mcp_entries(python_exe: str) -> dict[str, Any]:
    """Generate the exact JSON config entries for both QECTOR MCP servers."""
    py_path = str(Path(python_exe).resolve()).replace("\\", "/")
    lib_path = str(LIBRARY_SCRIPT.resolve()).replace("\\", "/")
    bench_path = str(BENCH_SCRIPT.resolve()).replace("\\", "/")

    return {
        "qector-library": {
            "command": py_path,
            "args": [lib_path],
            "env": {
                "QECTOR_SILENT": "1",
                "PYTHONUNBUFFERED": "1",
            },
        },
        "qector-bench": {
            "command": py_path,
            "args": [bench_path],
            "env": {
                "QECTOR_SILENT": "1",
                "PYTHONUNBUFFERED": "1",
            },
        },
    }


def configure_developer_mcp(
    claude_dir: Path,
    python_exe: str,
    dry_run: bool = False,
    remove: bool = False,
) -> dict[str, Any]:
    """Manage Developer mcpServers in claude_desktop_config.json."""
    config_path = claude_dir / "claude_desktop_config.json"
    result: dict[str, Any] = {
        "component": "claude_desktop_config.json",
        "path": str(config_path),
        "backup_path": None,
        "status": "pending",
    }

    existing_config: dict[str, Any] = {"mcpServers": {}}
    if config_path.is_file():
        try:
            raw_text = config_path.read_text(encoding="utf-8")
            if raw_text.strip():
                existing_config = json.loads(raw_text)
                if not isinstance(existing_config, dict):
                    existing_config = {"mcpServers": {}}
                elif "mcpServers" not in existing_config or not isinstance(existing_config.get("mcpServers"), dict):
                    existing_config["mcpServers"] = {}
        except Exception as exc:
            result["status"] = "error"
            result["error"] = f"Failed to parse {config_path}: {exc}"
            return result

    mcp_servers = dict(existing_config.get("mcpServers", {}))
    if remove:
        mcp_servers.pop("qector-library", None)
        mcp_servers.pop("qector-bench", None)
    else:
        mcp_servers.update(build_qector_mcp_entries(python_exe))

    existing_config["mcpServers"] = mcp_servers

    if dry_run:
        result["status"] = "dry_run_success"
        result["proposed_config"] = existing_config
        return result

    try:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        if config_path.is_file():
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = config_path.with_name(f"claude_desktop_config.json.bak.{timestamp}")
            shutil.copy2(config_path, backup_path)
            result["backup_path"] = str(backup_path)

        formatted_json = json.dumps(existing_config, indent=2, sort_keys=True) + "\n"
        config_path.write_text(formatted_json, encoding="utf-8")
        result["status"] = "success"
    except Exception as exc:
        result["status"] = "error"
        result["error"] = str(exc)

    return result


def configure_settings_connector_extension(
    claude_dir: Path,
    python_exe: str,
    dry_run: bool = False,
    remove: bool = False,
) -> dict[str, Any]:
    """Install/Register QECTOR as a Claude Desktop Extension / Custom Connector."""
    ext_parent_dir = claude_dir / "Claude Extensions"
    ext_target_dir = ext_parent_dir / EXTENSION_ID
    registry_file = claude_dir / "extensions-installations.json"

    result: dict[str, Any] = {
        "component": "Claude Extensions Settings/Connectors",
        "extension_id": EXTENSION_ID,
        "extension_dir": str(ext_target_dir),
        "registry_file": str(registry_file),
        "backup_path": None,
        "status": "pending",
    }

    # Load registry
    registry: dict[str, Any] = {"extensions": {}}
    if registry_file.is_file():
        try:
            raw_text = registry_file.read_text(encoding="utf-8")
            if raw_text.strip():
                registry = json.loads(raw_text)
                if not isinstance(registry, dict) or "extensions" not in registry:
                    registry = {"extensions": {}}
        except Exception as exc:
            result["status"] = "error"
            result["error"] = f"Failed to parse {registry_file}: {exc}"
            return result

    # Read extension manifest template
    manifest_src = EXTENSION_DIR_SRC / "manifest.json"
    if not manifest_src.is_file():
        result["status"] = "error"
        result["error"] = f"Missing source manifest template at {manifest_src}"
        return result

    manifest_data = json.loads(manifest_src.read_text(encoding="utf-8"))
    py_path = str(Path(python_exe).resolve()).replace("\\", "/")
    lib_path = str(LIBRARY_SCRIPT.resolve()).replace("\\", "/")
    manifest_data["server"]["mcp_config"]["command"] = py_path
    manifest_data["server"]["mcp_config"]["args"] = [lib_path]

    manifest_bytes = json.dumps(manifest_data, indent=2, sort_keys=True).encode("utf-8")
    manifest_hash = hashlib.sha256(manifest_bytes).hexdigest()

    extensions_dict = registry.get("extensions", {})

    if remove:
        extensions_dict.pop(EXTENSION_ID, None)
    else:
        extensions_dict[EXTENSION_ID] = {
            "id": EXTENSION_ID,
            "version": manifest_data.get("version", "1.0.2"),
            "hash": manifest_hash,
            "installedAt": datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
            "manifest": manifest_data,
            "signatureInfo": {"status": "unsigned"},
            "source": "local",
        }

    registry["extensions"] = extensions_dict

    if dry_run:
        result["status"] = "dry_run_success"
        result["manifest_hash"] = manifest_hash
        return result

    try:
        ext_parent_dir.mkdir(parents=True, exist_ok=True)

        if remove:
            if ext_target_dir.is_dir():
                shutil.rmtree(ext_target_dir, ignore_errors=True)
        else:
            ext_target_dir.mkdir(parents=True, exist_ok=True)
            # Write updated manifest into extension folder
            (ext_target_dir / "manifest.json").write_bytes(manifest_bytes)
            # Copy icon and docs if present
            if (EXTENSION_DIR_SRC / "icon.png").is_file():
                shutil.copy2(EXTENSION_DIR_SRC / "icon.png", ext_target_dir / "icon.png")
            if (EXTENSION_DIR_SRC / "README.md").is_file():
                shutil.copy2(EXTENSION_DIR_SRC / "README.md", ext_target_dir / "README.md")

        # Backup & write registry file
        if registry_file.is_file():
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = registry_file.with_name(f"extensions-installations.json.bak.{timestamp}")
            shutil.copy2(registry_file, backup_path)
            result["backup_path"] = str(backup_path)

        formatted_registry = json.dumps(registry, indent=2, sort_keys=True) + "\n"
        registry_file.write_text(formatted_registry, encoding="utf-8")

        result["status"] = "success"
    except Exception as exc:
        result["status"] = "error"
        result["error"] = str(exc)

    return result


def configure_desktop(
    dry_run: bool = False,
    remove: bool = False,
    custom_python: str | None = None,
) -> dict[str, Any]:
    """Execute complete Claude Desktop integration (Developer MCP + Settings/Connectors)."""
    claude_dir = get_claude_base_dir()
    python_exe = custom_python or sys.executable
    runtime_diag = check_runtime(python_exe)

    mcp_res = configure_developer_mcp(
        claude_dir=claude_dir,
        python_exe=python_exe,
        dry_run=dry_run,
        remove=remove,
    )

    ext_res = configure_settings_connector_extension(
        claude_dir=claude_dir,
        python_exe=python_exe,
        dry_run=dry_run,
        remove=remove,
    )

    is_ok = (mcp_res["status"] in ("success", "dry_run_success")) and (
        ext_res["status"] in ("success", "dry_run_success")
    )

    return {
        "action": "remove" if remove else "configure",
        "dry_run": dry_run,
        "claude_dir": str(claude_dir),
        "runtime": runtime_diag,
        "developer_mcp": mcp_res,
        "settings_connector_extension": ext_res,
        "status": "success" if (is_ok and not dry_run) else ("dry_run_success" if dry_run else "error"),
        "message": (
            "Successfully configured QECTOR in Claude Desktop (both Developer MCP and Settings Connectors). "
            "Please fully restart Claude Desktop."
            if is_ok
            else "Errors encountered during configuration."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Configure QECTOR in Claude Desktop (Developer MCP & Settings Connectors)"
    )
    parser.add_argument(
        "--check-only",
        "--dry-run",
        action="store_true",
        dest="dry_run",
        help="Inspect configuration without modifying files",
    )
    parser.add_argument(
        "--confirm",
        "--apply",
        action="store_true",
        dest="confirm",
        help="Apply changes to Claude Desktop configuration and extensions",
    )
    parser.add_argument(
        "--remove",
        action="store_true",
        help="Remove QECTOR server and extension entries from Claude Desktop",
    )
    parser.add_argument(
        "--python-path",
        type=str,
        default=None,
        help="Explicit Python interpreter executable path to pin in config",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output diagnostics in JSON format",
    )

    args = parser.parse_args(argv)

    if not args.confirm and not args.dry_run and not args.remove:
        args.dry_run = True

    res = configure_desktop(
        dry_run=args.dry_run,
        remove=args.remove,
        custom_python=args.python_path,
    )

    if args.json:
        print(json.dumps(res, indent=2, sort_keys=True))
    else:
        print("=" * 70)
        print("  QECTOR CLAUDE DESKTOP CONNECTOR & EXTENSION INSTALLER")
        print("=" * 70)
        print(f"Claude AppData: {res['claude_dir']}")
        print(f"Python Binary:  {res['runtime']['python_executable']}")
        print(f"Status:         {res['status'].upper()}")
        print(f"Message:        {res['message']}")
        print("\n1. Developer MCP Config:")
        print(f"   Status: {res['developer_mcp']['status']}")
        if res['developer_mcp'].get('backup_path'):
            print(f"   Backup: {res['developer_mcp']['backup_path']}")
        print("\n2. Claude Desktop Settings / Connectors Extension:")
        print(f"   Extension ID: {res['settings_connector_extension']['extension_id']}")
        print(f"   Status:       {res['settings_connector_extension']['status']}")
        if res['settings_connector_extension'].get('backup_path'):
            print(f"   Backup:       {res['settings_connector_extension']['backup_path']}")
        print("=" * 70)

    return 0 if res["status"] in ("success", "dry_run_success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
