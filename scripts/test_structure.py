#!/usr/bin/env python3
"""Run the QECTOR source and bundle structural validators in sequence.

This is the historical entry point. It now delegates to two focused scripts
so the *source-only* and *built-bundle* contracts are validated independently:

* ``scripts/validate_source.py``        — skills, agents, commands, hooks,
  manifests, Desktop extension source, MCP config templates, cleanliness.
  Always runnable from a source checkout; never requires ``dist/``.
* ``scripts/validate_plugin_bundle.py`` — built artifacts in ``dist/``.
  Reports informational when ``dist/`` is absent.

Exit code is 0 when both pass, 1 when either reports a failure.
"""

from __future__ import annotations

import argparse
import runpy
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skip-bundle",
        action="store_true",
        help="Run only the source validator (no dist/ checks).",
    )
    parser.add_argument(
        "--warn-only",
        action="store_true",
        help="Forwarded to both validators; never exits non-zero on failure.",
    )
    parser.add_argument(
        "--bundle-only",
        action="store_true",
        help="Run only the bundle validator (skip source).",
    )
    args = parser.parse_args()

    failures = 0
    extra = ["--warn-only"] if args.warn_only else []
    saved_argv = sys.argv

    if not args.bundle_only:
        print("=" * 70)
        print("  PHASE 1/2: SOURCE VALIDATION")
        print("=" * 70)
        source_path = HERE / "validate_source.py"
        sys.argv = [str(source_path), *extra]
        try:
            runpy.run_path(str(source_path), run_name="__main__")
        except SystemExit as exit_event:
            if exit_event.code not in (None, 0):
                failures += 1
        finally:
            sys.argv = saved_argv

    if not args.skip_bundle:
        print()
        print("=" * 70)
        print("  PHASE 2/2: PLUGIN BUNDLE VALIDATION")
        print("=" * 70)
        bundle_path = HERE / "validate_plugin_bundle.py"
        sys.argv = [str(bundle_path), *extra]
        try:
            runpy.run_path(str(bundle_path), run_name="__main__")
        except SystemExit as exit_event:
            if exit_event.code not in (None, 0):
                failures += 1
        finally:
            sys.argv = saved_argv

    print()
    print("=" * 70)
    print("  COMBINED STRUCTURAL VALIDATION")
    print("=" * 70)
    if failures == 0:
        print("  Status:   ALL CLEAR")
        return 0
    print(f"  Status:   {failures} phase(s) reported failures")
    return 1


if __name__ == "__main__":
    sys.exit(main())
