#!/usr/bin/env python3
"""
Claude Desktop Windows App Connector & Extension Installer for QECTOR Plugin.

Provides complete, zero-friction integration for Claude Desktop on Windows (and macOS/Linux):
1. Registers the stable `qector-library` server in `claude_desktop_config.json`.
   The research and administrative surfaces are opt-in flags.
2. Installs QECTOR as a first-class Extension in Claude Desktop Settings with
   a single combined `qector-desktop` MCP entry point
   (`Claude Extensions/ant.dir.gh.guillaumelessard.qector` & `extensions-installations.json`).
3. Non-destructively preserves existing servers and preferences with automatic timestamped backups.
4. Normalizes all Windows paths to forward slashes to prevent JSON escape sequence crashes.
5. Injects `QECTOR_SILENT=1` and `PYTHONUNBUFFERED=1` to guarantee pure stdio JSON-RPC.
6. Stages the extension copy in a sibling temp directory and swaps it in with a single
   rename, so a Claude Desktop process that still has the previous extension's files open
   (e.g. an active `qector-library` MCP server) cannot turn a re-install into a half-deleted,
   half-copied extension directory. Detects a running Claude Desktop process up front and
   warns (never blocks) so the person knows why a locked-file retry might be needed.

Note: QECTOR is a local, offline MCP server. It is installed as a Claude Desktop Extension
(this script), never as a remote "Custom Connector" (that flow expects a hosted URL and
performs OAuth, which QECTOR does not have and will always fail).
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
import stat
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
LIBRARY_SCRIPT = ROOT / "mcp" / "mcp_server_library.py"
RESEARCH_SCRIPT = ROOT / "mcp" / "mcp_server_qector_bench.py"
ADMIN_SCRIPT = ROOT / "mcp" / "mcp_server_admin.py"
DESKTOP_SCRIPT = ROOT / "mcp" / "mcp_server_desktop.py"
EXTENSION_DIR_SRC = ROOT / ".claude-desktop-extension"
EXTENSION_ID = "ant.dir.gh.guillaumelessard.qector"

# Files/dirs that never belong in the installed, end-user Claude Desktop
# Extension: bytecode caches (frequently locked by a running interpreter,
# and regenerated on first run anyway), plus developer/internal-only
# artifacts -- underscore-prefixed smoke-test and validation scripts, the
# device-local VALIDATION_REPORT.md, the test suite, and the pre-desktop
# generic mcp_config.json / workbench_config.example.json that are
# superseded by claude_desktop_config.json for this install path. None of
# these are referenced by manifest.json or CLAUDE_DESKTOP.md as required for
# qector-library to run, so a public release install directory
# should not carry them.
_COPY_IGNORE = shutil.ignore_patterns(
    "__pycache__",
    "*.pyc",
    "*.pyo",
    "_smoke_*.py",
    "_validate_all.py",
    "VALIDATION_REPORT.md",
    "tests",
    "mcp_config.json",
    "workbench_config.example.json",
)


def is_claude_desktop_running() -> list[str]:
    """Best-effort detection of running Claude Desktop processes.

    Returns a list of matched process descriptions (empty if none found or
    detection isn't supported on this platform). Used only to produce a
    clearer error message -- never to block the caller.
    """
    system = platform.system()
    try:
        if system == "Windows":
            out = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq Claude.exe", "/FO", "CSV", "/NH"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            lines = [ln for ln in out.stdout.splitlines() if ln.strip() and "claude.exe" in ln.lower()]
            return lines
        else:
            out = subprocess.run(["pgrep", "-fli", "claude"], capture_output=True, text=True, timeout=10)
            lines = [ln for ln in out.stdout.splitlines() if ln.strip()]
            return lines
    except Exception:
        return []


def _rmtree_retry(path: Path, attempts: int = 6, delay_s: float = 0.5) -> None:
    """Remove a directory tree, tolerating transient Windows file locks and
    read-only files (both common when Claude Desktop is running and has the
    extension folder or its own copy of the MCP scripts open)."""

    def _on_error_legacy(func, target_path, exc_info):
        # Python < 3.12 callback shape: exc_info is (type, value, traceback).
        try:
            os.chmod(target_path, stat.S_IWRITE)
            func(target_path)
        except Exception:
            pass

    def _on_exc(func, target_path, exc):
        # Python >= 3.12 callback shape: exc is the exception instance.
        try:
            os.chmod(target_path, stat.S_IWRITE)
            func(target_path)
        except Exception:
            pass

    # shutil.rmtree's onexc= replaces the deprecated onerror= as of Python
    # 3.12 (onerror still works there but emits a DeprecationWarning on every
    # call, which would otherwise print on every install this project's
    # supported 3.12/3.13 users run). Requirements.txt supports 3.9-3.13, so
    # both call shapes must stay available; pick whichever this interpreter
    # accepts rather than hardcoding one.
    _use_onexc = sys.version_info >= (3, 12)

    last_exc: Exception | None = None
    for i in range(attempts):
        if not path.exists():
            return
        try:
            if _use_onexc:
                shutil.rmtree(path, onexc=_on_exc)
            else:
                shutil.rmtree(path, onerror=_on_error_legacy)
            if not path.exists():
                return
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
        time.sleep(delay_s * (i + 1))
    if path.exists():
        raise PermissionError(
            f"Could not remove '{path}' after {attempts} attempts (still in use). "
            "Close Claude Desktop completely (check the system tray) and re-run the installer. "
            f"Last error: {last_exc}"
        )


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
        "research_script_exists": RESEARCH_SCRIPT.is_file(),
        "admin_script_exists": ADMIN_SCRIPT.is_file(),
        "desktop_script_exists": DESKTOP_SCRIPT.is_file(),
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
    if not diag["research_script_exists"]:
        diag["errors"].append(f"Missing research server script: {RESEARCH_SCRIPT}")
    if not diag["admin_script_exists"]:
        diag["errors"].append(f"Missing admin server script: {ADMIN_SCRIPT}")
    if not diag["desktop_script_exists"]:
        diag["errors"].append(f"Missing desktop server script: {DESKTOP_SCRIPT}")

    diag["ready"] = len(diag["errors"]) == 0
    return diag


def build_qector_mcp_entries(
    python_exe: str,
    *,
    include_research: bool = False,
    include_admin: bool = False,
) -> dict[str, Any]:
    """Generate explicit-profile QECTOR MCP server entries."""
    py_path = str(Path(python_exe).resolve()).replace("\\", "/")
    lib_path = str(LIBRARY_SCRIPT.resolve()).replace("\\", "/")
    entries = {
        "qector-library": {
            "command": py_path,
            "args": [lib_path],
            "env": {
                "QECTOR_SILENT": "1",
                "PYTHONUNBUFFERED": "1",
            },
        }
    }
    if include_research:
        research_path = str(RESEARCH_SCRIPT.resolve()).replace("\\", "/")
        entries["qector-research"] = {
            "command": py_path,
            "args": [research_path],
            "env": {
                "QECTOR_SILENT": "1",
                "PYTHONUNBUFFERED": "1",
            },
        }
    if include_admin:
        admin_path = str(ADMIN_SCRIPT.resolve()).replace("\\", "/")
        entries["qector-admin"] = {
            "command": py_path,
            "args": [admin_path],
            "env": {
                "QECTOR_SILENT": "1",
                "PYTHONUNBUFFERED": "1",
                "QECTOR_ADMIN_ENABLED": "1",
            },
        }
    return entries


def configure_developer_mcp(
    claude_dir: Path,
    python_exe: str,
    dry_run: bool = False,
    remove: bool = False,
    include_research: bool = False,
    include_admin: bool = False,
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
        mcp_servers.pop("qector-research", None)
        mcp_servers.pop("qector-admin", None)
        mcp_servers.pop("qector-bench", None)
    else:
        mcp_servers.update(
            build_qector_mcp_entries(
                python_exe,
                include_research=include_research,
                include_admin=include_admin,
            )
        )

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
    """Install/Register QECTOR as a local Claude Desktop Extension.

    Never registers QECTOR as a remote "Custom Connector": that flow expects a
    hosted URL and performs OAuth, which this offline, stdio-only server does
    not support and would always fail to authenticate.
    """
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

    # The extension has one MCP entry point and therefore uses the Desktop
    # adapter's safe profile. Developer MCP configuration may opt into the
    # separately registered research/admin trust zones.
    manifest_data["server"]["entry_point"] = "mcp/mcp_server_desktop.py"
    manifest_data["server"]["mcp_config"]["command"] = py_path
    manifest_data["server"]["mcp_config"]["args"] = [
        "${__dirname}/mcp/mcp_server_desktop.py",
        "--profile",
        "safe",
    ]

    manifest_bytes = json.dumps(manifest_data, indent=2, sort_keys=True).encode("utf-8")
    manifest_hash = hashlib.sha256(manifest_bytes).hexdigest()

    extensions_dict = registry.get("extensions", {})

    if remove:
        extensions_dict.pop(EXTENSION_ID, None)
    else:
        extensions_dict[EXTENSION_ID] = {
            "id": EXTENSION_ID,
            "version": manifest_data["version"],
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

    running = is_claude_desktop_running()
    if running:
        result["warning"] = (
            "Claude Desktop appears to be running. The installer will still proceed "
            "(files are staged and swapped in atomically, so a live MCP server holding "
            "the previous copy open cannot corrupt the install), but Claude Desktop must "
            "be fully restarted afterwards to pick up the change."
        )

    try:
        ext_parent_dir.mkdir(parents=True, exist_ok=True)

        if remove:
            # A plain rmtree here can still fail if a running Claude Desktop process
            # has a file in this directory open; retry with backoff instead of the
            # previous ignore_errors=True, which silently reported success on a
            # partially-removed directory.
            if ext_target_dir.is_dir():
                _rmtree_retry(ext_target_dir)
        else:
            # Build the full new extension contents in a sibling staging directory
            # first, then swap it into place with a single rename. This is the
            # part that used to be `rmtree(existing) -> mkdir -> copytree(new)`
            # directly on ext_target_dir: if anything (most commonly a running
            # Claude Desktop / qector-library MCP server process) had a file in
            # that directory open, the rmtree would only partially succeed
            # (ignore_errors=True hid this), the following mkdir would silently
            # "succeed" on the leftover directory, and the copytree would then
            # throw on the first still-locked file -- reported as a bare
            # "error" status with no indication of what actually happened.
            staging_dir = ext_parent_dir / f".{EXTENSION_ID}.staging-{os.getpid()}-{time.time_ns()}"
            if staging_dir.exists():
                _rmtree_retry(staging_dir)
            staging_dir.mkdir(parents=True, exist_ok=False)
            try:
                (staging_dir / "manifest.json").write_bytes(manifest_bytes)
                if (EXTENSION_DIR_SRC / "icon.png").is_file():
                    shutil.copy2(EXTENSION_DIR_SRC / "icon.png", staging_dir / "icon.png")
                if (EXTENSION_DIR_SRC / "README.md").is_file():
                    shutil.copy2(EXTENSION_DIR_SRC / "README.md", staging_dir / "README.md")
                # Deep copy mcp/ directory to make the connector fully self-contained.
                # Dev/internal-only files never belong in the installed extension:
                # bytecode caches, smoke-test scripts, and the internal validation
                # report are excluded so a "public release" install directory only
                # contains what an end user's Claude Desktop actually needs to run
                # the two MCP servers.
                mcp_src = ROOT / "mcp"
                if mcp_src.is_dir():
                    shutil.copytree(mcp_src, staging_dir / "mcp", ignore=_COPY_IGNORE)

                # Old copy is removed only after the new one is fully staged, and the
                # staged copy is renamed into place immediately after -- the window in
                # which ext_target_dir does not exist is a single filesystem rename,
                # not the multi-second copytree that used to run against a live path.
                if ext_target_dir.is_dir():
                    _rmtree_retry(ext_target_dir)
                os.replace(staging_dir, ext_target_dir)
            except Exception:
                # Never leave an orphaned staging directory behind on failure.
                if staging_dir.exists():
                    _rmtree_retry(staging_dir, attempts=2, delay_s=0.2)
                raise

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
        result["error"] = f"{exc.__class__.__name__}: {exc}"
        if running:
            result["error"] += (
                " (Claude Desktop was detected running during this install -- fully quit it "
                "from the system tray, not just close the window, and re-run this installer.)"
            )

    return result


def _resolve_python_executable(custom_python: str | None) -> str:
    """Return a verified Python 3 interpreter path.

    ``custom_python`` is written into Claude Desktop config, so it must be an
    existing file that actually identifies as Python 3. The Windows ``py.exe``
    launcher is accepted; arbitrary binaries are not.
    """
    if custom_python is None:
        return sys.executable
    candidate = Path(custom_python).expanduser()
    if not candidate.is_file():
        raise ValueError(f"python_path is not an existing file: {custom_python}")
    resolved = str(candidate.resolve())
    try:
        completed = subprocess.run(
            [resolved, "-c", "import sys; print(sys.version_info[0])"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except Exception as exc:
        raise ValueError(
            f"python_path is not an executable Python interpreter: {exc}"
        ) from exc
    if completed.returncode != 0 or completed.stdout.strip() != "3":
        raise ValueError("python_path must be a Python 3 interpreter")
    return resolved


def configure_desktop(
    dry_run: bool = False,
    remove: bool = False,
    custom_python: str | None = None,
    include_research: bool = False,
    include_admin: bool = False,
) -> dict[str, Any]:
    """Execute complete Claude Desktop integration (Developer MCP + Settings/Connectors)."""
    claude_dir = get_claude_base_dir()
    try:
        python_exe = _resolve_python_executable(custom_python)
    except ValueError as exc:
        return {
            "action": "remove" if remove else "configure",
            "dry_run": dry_run,
            "profiles": {
                "library": True,
                "research": include_research,
                "admin": include_admin,
            },
            "claude_dir": str(claude_dir),
            "runtime": {"python_executable": custom_python, "errors": [str(exc)]},
            "developer_mcp": {"status": "error", "error": str(exc)},
            "settings_connector_extension": {"status": "error", "error": str(exc)},
            "status": "error",
            "message": str(exc),
        }
    runtime_diag = check_runtime(python_exe)

    mcp_res = configure_developer_mcp(
        claude_dir=claude_dir,
        python_exe=python_exe,
        dry_run=dry_run,
        remove=remove,
        include_research=include_research,
        include_admin=include_admin,
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
        "profiles": {
            "library": True,
            "research": include_research,
            "admin": include_admin,
        },
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
        "--with-research",
        action="store_true",
        help="Also register the opt-in qector-research MCP server.",
    )
    parser.add_argument(
        "--with-admin",
        action="store_true",
        help=(
            "Also register qector-admin with QECTOR_ADMIN_ENABLED=1. "
            "Use only after reviewing the admin configuration example."
        ),
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
        include_research=args.with_research,
        include_admin=args.with_admin,
    )

    if args.json:
        print(json.dumps(res, indent=2, sort_keys=True))
    else:
        print("=" * 70)
        print("  QECTOR CLAUDE DESKTOP CONNECTOR & EXTENSION INSTALLER")
        print("=" * 70)
        print(f"Claude AppData: {res['claude_dir']}")
        print(f"Python Binary:  {res['runtime']['python_executable']}")
        print(
            "Profiles:       "
            f"library, research={'enabled' if res['profiles']['research'] else 'disabled'}, "
            f"admin={'enabled' if res['profiles']['admin'] else 'disabled'}"
        )
        print(f"Status:         {res['status'].upper()}")
        print(f"Message:        {res['message']}")
        print("\n1. Developer MCP Config:")
        print(f"   Status: {res['developer_mcp']['status']}")
        if res['developer_mcp'].get('backup_path'):
            print(f"   Backup: {res['developer_mcp']['backup_path']}")
        if res['developer_mcp'].get('error'):
            print(f"   Error:  {res['developer_mcp']['error']}")
        print("\n2. Claude Desktop Settings / Extension:")
        print(f"   Extension ID: {res['settings_connector_extension']['extension_id']}")
        print(f"   Status:       {res['settings_connector_extension']['status']}")
        if res['settings_connector_extension'].get('backup_path'):
            print(f"   Backup:       {res['settings_connector_extension']['backup_path']}")
        if res['settings_connector_extension'].get('warning'):
            print(f"   Warning:      {res['settings_connector_extension']['warning']}")
        if res['settings_connector_extension'].get('error'):
            print(f"   Error:        {res['settings_connector_extension']['error']}")
        if res["runtime"].get("errors"):
            print("\n3. Runtime diagnostics:")
            for err in res["runtime"]["errors"]:
                print(f"   - {err}")
        if res["status"] == "error":
            print(
                "\nRe-run with --json for the full machine-readable diagnostic, "
                "including the exact exception raised."
            )
        print("=" * 70)

    return 0 if res["status"] in ("success", "dry_run_success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
