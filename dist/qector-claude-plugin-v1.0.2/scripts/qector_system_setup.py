#!/usr/bin/env python3
"""
QECTOR First-Time System Setup & Verification Tool (28th Tool CLI).

Audits python interpreter, dependencies, installs required packages from
requirements.txt upon explicit user approbation, configures artifacts
directory, and verifies decoding faithfulness against Theorem 1.

Usage:
    python scripts/qector_system_setup.py --check-only    # Read-only audit
    python scripts/qector_system_setup.py --confirm       # Install and configure
"""

from __future__ import annotations

import argparse
import importlib.metadata
import importlib.util
import json
import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any

REF_DOI = "10.5281/zenodo.21941046"
ROOT = Path(__file__).resolve().parents[1]
REQUIREMENTS_FILE = ROOT / "requirements.txt"


def _installed_version(distribution: str) -> str:
    try:
        return importlib.metadata.version(distribution)
    except importlib.metadata.PackageNotFoundError:
        return "not installed"


def audit_environment() -> dict[str, Any]:
    """Perform a read-only probe of the host environment."""
    py_exe = sys.executable
    py_ver = platform.python_version()
    is_venv = sys.prefix != sys.base_prefix
    has_pip = importlib.util.find_spec("pip") is not None

    versions = {
        "numpy": _installed_version("numpy"),
        "qector_decoder_v3": _installed_version("qector-decoder-v3"),
        "mcp": _installed_version("mcp"),
        "cryptography": _installed_version("cryptography"),
    }

    artifact_dir = Path(os.environ.get("QECTOR_ARTIFACT_DIR", ROOT / "artifacts"))

    return {
        "python_executable": py_exe,
        "python_version": py_ver,
        "virtual_environment": is_venv,
        "pip_available": has_pip,
        "installed_versions": versions,
        "requirements_file": str(REQUIREMENTS_FILE),
        "requirements_file_exists": REQUIREMENTS_FILE.is_file(),
        "artifact_directory": str(artifact_dir),
        "artifact_dir_exists": artifact_dir.is_dir(),
        "license_environment": {
            "QECTOR_LICENSE_KEY": bool(os.environ.get("QECTOR_LICENSE_KEY")),
            "QECTOR_LICENSE_FILE": os.environ.get("QECTOR_LICENSE_FILE", "unset"),
            "QECTOR_SILENT": os.environ.get("QECTOR_SILENT", "1"),
        },
    }


def run_setup(confirm: bool = False, install_deps: bool = True) -> dict[str, Any]:
    """Execute setup with safety gate."""
    audit = audit_environment()

    actions_planned = [
        "Install / verify production requirements: numpy>=1.26,<2.3, qector-decoder-v3==1.0.0, mcp==1.26.0, cryptography>=48.0.1,<50",
        "Create artifacts/ evidence directory",
        "Run live decoder syndrome faithfulness test (H c = s mod 2)",
    ]

    if not confirm:
        return {
            "status": "dry_run_pending_approval",
            "user_approbation_required": True,
            "user_approbation_granted": False,
            "actions_planned": actions_planned,
            "diagnostics": audit,
            "message": (
                "SAFETY GATE: Read-only inspection complete. No changes were made. "
                "Re-run with --confirm (or set confirm=True in MCP) to grant user approbation."
            ),
        }

    # User approbation granted
    actions_executed = []

    # 1. Install dependencies
    if install_deps and audit["pip_available"]:
        cmd = [sys.executable, "-m", "pip", "install", "-r", str(REQUIREMENTS_FILE)]
        try:
            p = subprocess.run(
                cmd, capture_output=True, text=True, timeout=180, cwd=str(ROOT)
            )
            actions_executed.append({
                "action": "pip_install",
                "command": " ".join(cmd),
                "success": p.returncode == 0,
                "stdout": p.stdout[-300:] if p.stdout else "",
                "stderr": p.stderr[-300:] if p.stderr else "",
            })
        except Exception as exc:
            actions_executed.append({
                "action": "pip_install",
                "success": False,
                "error": str(exc),
            })

    # 2. Prepare artifacts directory
    artifact_dir = Path(audit["artifact_directory"])
    try:
        artifact_dir.mkdir(parents=True, exist_ok=True)
        test_file = artifact_dir / ".write_test.tmp"
        test_file.write_text("ok", encoding="utf-8")
        test_file.unlink()
        actions_executed.append({
            "action": "create_artifact_directory",
            "path": str(artifact_dir),
            "success": True,
        })
    except Exception as exc:
        actions_executed.append({
            "action": "create_artifact_directory",
            "path": str(artifact_dir),
            "success": False,
            "error": str(exc),
        })

    # 3. Live math validation
    validation_result = {"passed": False}
    try:
        import numpy as np
        import qector_decoder_v3 as qd
        from qector_decoder_v3 import BlossomDecoder, codes

        code = codes.repetition_code(5)
        matrix = np.asarray(code.parity_check_matrix(), dtype=np.uint8)
        syndrome = np.array([1, 0, 0, 1], dtype=np.uint8)
        decoder = BlossomDecoder(code.check_to_qubits, n_qubits=code.n_qubits)
        correction = np.asarray(decoder.decode(syndrome), dtype=np.uint8)
        calculated = (matrix.astype(np.int64) @ correction.astype(np.int64)) % 2
        is_faithful = np.array_equal(calculated.astype(np.uint8), syndrome)

        validation_result = {
            "passed": is_faithful,
            "decoder": "BlossomDecoder",
            "family": "repetition",
            "distance": 5,
            "theorem_1_faithful": is_faithful,
            "qector_version": getattr(qd, "__version__", "unknown"),
        }
        actions_executed.append({
            "action": "math_validation",
            "success": is_faithful,
            "details": validation_result,
        })
    except Exception as exc:
        validation_result = {"passed": False, "error": str(exc)}
        actions_executed.append({
            "action": "math_validation",
            "success": False,
            "error": str(exc),
        })

    return {
        "status": "ready" if validation_result.get("passed", False) else "configured",
        "user_approbation_required": True,
        "user_approbation_granted": True,
        "actions_executed": actions_executed,
        "diagnostics": audit_environment(),
        "validation_result": validation_result,
        "reference_manual": REF_DOI,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="QECTOR System Setup & Verification Tool (28th Tool)"
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Grant user approbation and execute installations/configurations.",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Run read-only inspection without making changes.",
    )
    args = parser.parse_args()

    confirm = args.confirm and not args.check_only
    result = run_setup(confirm=confirm)
    print(json.dumps(result, indent=2))
    return 0 if result["status"] in ("ready", "dry_run_pending_approval") else 1


if __name__ == "__main__":
    sys.exit(main())
