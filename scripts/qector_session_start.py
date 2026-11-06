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
            "QECTOR plugin 2.0.1 active: 28 skills (start with qector-core and "
            "qector-math-foundations); agents=qec-researcher,qec-developer,"
            "qec-validator,qec-hardware-engineer,qec-sysadmin"
        )
        print(f"Workbench MCP executable configured: {tool}; optional and device-local")
        print(f"Library wheel: qector-decoder-v3=={library_version}; target=1.0.1")
        print(
            "Default MCP server: qector-secure (air-gapped, JSON Schema 2020-12 "
            "validated in and out, INTEGRITY.json verified, optional hash-chained audit)."
        )
        print(
            "Device-local validation required: run the library math gate and "
            "negotiate any Workbench surface with initialize/tools/list."
        )
        print(
            "Air-gapped by default: decode locally via qector-secure; never upload "
            ".stim/.npy/parity matrices to web APIs."
        )
    except Exception as exc:  # never break startup
        print(f"[qector session hook warn] {exc}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
