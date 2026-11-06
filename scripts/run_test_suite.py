#!/usr/bin/env python3
"""Run the test suite one module at a time with wall-clock timings.

For reviewers whose sandbox imposes a per-command time limit: each module
runs as its own subprocess, prints its duration, and the summary states
exactly which modules ran, passed, were skipped for a missing runtime, or
failed. The combined result equals ``python -m unittest discover -s tests``.

    python scripts/run_test_suite.py                 # all modules
    python scripts/run_test_suite.py --module tests.test_signing
    PYTHONPATH=<extracted mcpb>/server/lib python scripts/run_test_suite.py   # bundled runtime
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULES = [
    "tests.test_signing",
    "tests.test_airgap",
    "tests.test_contract_v2",
    "tests.test_mcp_conformance",
    "tests.test_secure_server",
    "tests.test_production_readiness",
    "tests.test_reference_manual_math",
]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--module", action="append", default=None, help="Run only this module (repeatable).")
    parser.add_argument("--timeout", type=float, default=600.0, help="Per-module wall-clock limit in seconds.")
    args = parser.parse_args(argv)
    modules = args.module or MODULES
    env = {**os.environ, "QECTOR_SILENT": "1"}
    runtime = []
    for name in ("mcp.types", "qector_decoder_v3", "jsonschema", "numpy"):
        try:
            __import__(name)
        except Exception:
            runtime.append(name)
    print(f"interpreter: {sys.executable} ({sys.version.split()[0]})")
    print("runtime:", "complete" if not runtime else f"missing {runtime} -> runtime-dependent tests will be SKIPPED, not failed")
    totals = {"ran": 0, "failures": 0, "errors": 0, "skipped": 0}
    exit_code = 0
    for module in modules:
        started = time.perf_counter()
        try:
            proc = subprocess.run(
                [sys.executable, "-m", "unittest", module],
                cwd=str(ROOT),
                env=env,
                capture_output=True,
                text=True,
                timeout=args.timeout,
            )
        except subprocess.TimeoutExpired:
            print(f"{module:38s} TIMEOUT after {args.timeout:.0f}s")
            exit_code = 1
            continue
        elapsed = time.perf_counter() - started
        tail = proc.stderr.strip().splitlines()
        ran = re.search(r"Ran (\d+) tests?", proc.stderr)
        summary = tail[-1] if tail else "(no output)"
        counts = {k: int(v) for k, v in re.findall(r"(failures|errors|skipped)=(\d+)", summary)}
        totals["ran"] += int(ran.group(1)) if ran else 0
        for key in ("failures", "errors", "skipped"):
            totals[key] += counts.get(key, 0)
        status = "OK" if proc.returncode == 0 else "FAIL"
        if proc.returncode != 0:
            exit_code = 1
        print(f"{module:38s} {status:4s} {elapsed:6.1f}s  {summary}")
        if proc.returncode != 0:
            print(proc.stderr[-4000:])
    print(
        f"\nTOTAL ran={totals['ran']} failures={totals['failures']} errors={totals['errors']} skipped={totals['skipped']} -> "
        + ("OK" if exit_code == 0 else "FAILED")
    )
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
