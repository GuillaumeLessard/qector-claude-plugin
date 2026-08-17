"""
QECTOR hook helper - SessionStart banner (optional, see hooks/hooks.json).

Prints a compact runtime banner into the session context. Exits 0 always;
never blocks startup.
"""

import os
import importlib.metadata
import sys


def main():
    try:
        exe = os.environ.get("QECTOR_EXE")
        tool = bool(exe and os.path.isfile(exe))
        try:
            library_version = importlib.metadata.version("qector-decoder-v3")
        except importlib.metadata.PackageNotFoundError:
            library_version = "not installed"
        print(
            "QECTOR plugin active: skills=qector-core,qector-math-foundations,qector-researcher,"
            "qector-developer,qector-sysadmin,qector-hardware-engineer,qector-educator,run-qector; agents=qec-researcher,"
            "qec-developer,qec-validator,qec-hardware-engineer,qec-sysadmin"
        )
        print(f"Workbench MCP executable configured: {tool}; optional and device-local")
        print(f"Library wheel: qector-decoder-v3=={library_version}; target=1.0.0")
        print(
            "Device-local validation required: run the library math gate and "
            "negotiate any Workbench surface with initialize/tools/list."
        )
        print(
            "Zero-egress rule active: decode locally via MCP; never upload "
            ".stim/.npy/parity matrices to web APIs."
        )
    except Exception as exc:  # never break startup
        print(f"[qector session hook warn] {exc}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
