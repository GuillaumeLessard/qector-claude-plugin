r"""Run the public QECTOR reference-manual proof obligations.

Usage:
    python bin/run_manual_math_validation.py
    python bin/run_manual_math_validation.py --json-out ../qector-artifacts/manual_validation.json

The command does not claim a universal mathematical theorem from finite tests.
It records which concrete proof obligations were executed against the live
qector-decoder-v3 wheel and which hardware-dependent surfaces were not run.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import platform
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

# Ensure python/ is importable without relying on pytest's conftest.py hook,
# so this script (and `python -m unittest discover`) resolve
# `qector_math_ground_truth` the same way pytest does.
sys.path.insert(0, str(ROOT / "python"))


def _wheel_version() -> str:
    try:
        return importlib.metadata.version("qector-decoder-v3")
    except importlib.metadata.PackageNotFoundError:
        return "not installed"


def _summary(result: unittest.TestResult) -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "reference_manual": "10.5281/zenodo.21941046",
        "qector_decoder_v3": _wheel_version(),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "PASS" if result.wasSuccessful() else "FAIL",
        "tests_run": result.testsRun,
        "failures": len(result.failures),
        "errors": len(result.errors),
        "scope": {
            "theorems": "finite executable obligations for Theorems 1-16",
            "worked_examples": [
                "Appendix E.1",
                "Appendix E.2",
                "Appendix E.3",
                "Appendix E.4",
            ],
            "gpu": "not executed; no GPU evidence is inferred",
            "asymptotics": "not proved by runtime tests; manual proof remains authoritative",
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="QECTOR reference-manual math validation"
    )
    parser.add_argument(
        "--json-out", help="write a machine-readable validation summary"
    )
    args = parser.parse_args(argv)

    suite = unittest.defaultTestLoader.discover(
        str(ROOT / "tests"),
        pattern="test_reference_manual_math.py",
        top_level_dir=str(ROOT),
    )
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    summary = _summary(result)
    if args.json_out:
        output = Path(args.json_out).expanduser()
        if not output.is_absolute():
            output = ROOT / output
        output.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(summary, sort_keys=True, indent=2).encode("utf-8")
        output.write_bytes(payload)
        print(f"Validation summary: {output}")
        print(f"SHA-256: {hashlib.sha256(payload).hexdigest()}")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
