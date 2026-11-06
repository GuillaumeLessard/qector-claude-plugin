#!/usr/bin/env python3
"""Export every tool's input/output JSON Schema to ``schemas/``.

The exported files are the review artefact for non-Python clients and
for Anthropic's static tooling: one ``<tool>.input.schema.json`` and one
``<tool>.output.schema.json`` per tool, plus the shared envelope, the
audit-record schema and an ``index.json`` with SHA-256 digests. ``--check``
fails when the committed files differ from what the servers advertise,
which keeps the catalog and the code from drifting apart.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "mcp"))
os.environ.setdefault("QECTOR_SILENT", "1")

from qector_audit import RECORD_SCHEMA  # noqa: E402
from qector_mcp_compat import tool_annotations_dict, tool_input_schema, tool_output_schema  # noqa: E402
from qector_mcp_contract import CONTRACT_VERSION, RESULT_OUTPUT_SCHEMA, schema_sha256  # noqa: E402

SCHEMAS_DIR = ROOT / "schemas"


def _dump(value) -> str:
    return json.dumps(value, indent=2, sort_keys=True) + "\n"


def collect() -> dict[str, str]:
    import mcp_server_admin as admin
    import mcp_server_qector_bench as research
    import mcp_server_secure as secure

    files: dict[str, str] = {"envelope.schema.json": _dump(RESULT_OUTPUT_SCHEMA), "audit-record.schema.json": _dump(RECORD_SCHEMA)}
    index: dict[str, dict] = {}
    tools, stability, _ = secure.assemble_tools("research")
    surfaces = [(tool, stability[tool.name], "qector-secure") for tool in tools]
    surfaces += [(tool, "provisional", "qector-research") for tool in research.TOOLS if tool.name == "compat_report"]
    surfaces += [(tool, "admin", "qector-admin") for tool in admin.TOOLS]
    for tool, stab, server in surfaces:
        prefix = tool.name if server != "qector-research" else "research_compat_report"
        if prefix in index and server == "qector-research":
            continue
        input_schema = tool_input_schema(tool)
        output_schema = tool_output_schema(tool) or {}
        files[f"{prefix}.input.schema.json"] = _dump(input_schema)
        files[f"{prefix}.output.schema.json"] = _dump(output_schema)
        index[prefix] = {
            "server": server,
            "stability": stab,
            "annotations": tool_annotations_dict(tool),
            "input_sha256": schema_sha256(input_schema),
            "output_sha256": schema_sha256(output_schema),
        }
    files["index.json"] = _dump(
        {
            "contract_version": CONTRACT_VERSION,
            "dialect": "https://json-schema.org/draft/2020-12/schema",
            "envelope_sha256": schema_sha256(RESULT_OUTPUT_SCHEMA),
            "audit_record_sha256": schema_sha256(RECORD_SCHEMA),
            "tools": dict(sorted(index.items())),
        }
    )
    return files


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Fail when schemas/ differs from the live servers.")
    args = parser.parse_args(argv)
    files = collect()
    if args.check:
        drift = []
        for name, content in files.items():
            path = SCHEMAS_DIR / name
            if not path.is_file() or path.read_text(encoding="utf-8") != content:
                drift.append(name)
        extra = sorted(p.name for p in SCHEMAS_DIR.glob("*.json")) if SCHEMAS_DIR.is_dir() else []
        extra = [name for name in extra if name not in files]
        if drift or extra:
            print("schema drift:", drift, "unexpected:", extra)
            return 1
        print(f"schemas/ is in sync ({len(files)} files)")
        return 0
    SCHEMAS_DIR.mkdir(exist_ok=True)
    for stale in SCHEMAS_DIR.glob("*.json"):
        if stale.name not in files:
            stale.unlink()
    for name, content in files.items():
        (SCHEMAS_DIR / name).write_text(content, encoding="utf-8")
    print(f"exported {len(files)} schema files to {SCHEMAS_DIR.relative_to(ROOT)}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
