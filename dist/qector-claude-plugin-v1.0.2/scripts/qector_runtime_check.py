"""Check the app-free QECTOR runtime in the current Python interpreter.

Run this command once with system Python and once with the selected virtual
environment when both launch modes are part of a deployment. It produces only
fresh local output; no result is stored in the public package.
"""

from __future__ import annotations

import importlib.metadata
import importlib.util
import json
import os
import platform
import sys
from pathlib import Path

os.environ["QECTOR_SILENT"] = "1"

EXPECTED_QECTOR = "1.0.0"
EXPECTED_MCP = "1.26.0"
EXPECTED_TOOLS = {
    "list_code_families",
    "list_decoders",
    "get_license_info",
    "decode_syndrome",
    "decode_single",
    "threshold_sweep",
    "build_code_from_matrix",
    "compat_report",
}
ROOT = Path(__file__).resolve().parents[1]


def _version(name: str) -> str | None:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def main() -> int:
    failures: list[str] = []
    qector_version = _version("qector-decoder-v3")
    mcp_version = _version("mcp")
    if qector_version != EXPECTED_QECTOR:
        failures.append(
            f"qector-decoder-v3=={EXPECTED_QECTOR} required; found {qector_version or 'missing'}"
        )
    if mcp_version != EXPECTED_MCP:
        failures.append(
            f"mcp=={EXPECTED_MCP} required; found {mcp_version or 'missing'}"
        )

    try:
        import numpy as np
        import qector_decoder_v3 as qector

        stable_symbols = (
            "UnionFindDecoder",
            "FastUnionFindDecoder",
            "BlossomDecoder",
            "SparseBlossomDecoder",
            "NativeAutoDecoder",
        )
        missing = [name for name in stable_symbols if not hasattr(qector, name)]
        if missing:
            failures.append(f"missing stable decoder symbols: {', '.join(missing)}")
        code = qector.codes.repetition_code(3)
        error = np.array([1, 0, 0], dtype=np.uint8)
        syndrome = code.syndrome(error)
        correction = qector.BlossomDecoder(
            code.check_to_qubits,
            n_qubits=code.n_qubits,
        ).decode(syndrome)
        matrix = np.asarray(code.parity_check_matrix(), dtype=np.uint8)
        if not np.array_equal((matrix @ correction.astype(int)) % 2, syndrome):
            failures.append("live app-free decode failed H c = s (mod 2)")
    except Exception as exc:
        failures.append(f"app-free QECTOR import/decode failed: {exc}")

    try:
        from mcp.server import Server  # noqa: F401
    except Exception as exc:
        failures.append(f"MCP SDK low-level Server import failed: {exc}")

    try:
        server_path = ROOT / "mcp" / "mcp_server_library.py"
        spec = importlib.util.spec_from_file_location(
            "qector_library_server", server_path
        )
        if spec is None or spec.loader is None:
            raise RuntimeError("could not load library server")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        actual_tools = {tool.name for tool in module.TOOLS}
        if actual_tools != EXPECTED_TOOLS:
            failures.append(
                f"library MCP tool spec mismatch: expected {sorted(EXPECTED_TOOLS)}, "
                f"found {sorted(actual_tools)}"
            )
    except Exception as exc:
        failures.append(f"library MCP specification check failed: {exc}")

    payload = {
        "status": "ok" if not failures else "fail",
        "app_required": False,
        "server": str(ROOT / "mcp" / "mcp_server_library.py"),
        "python": sys.executable,
        "python_version": platform.python_version(),
        "venv": sys.prefix != sys.base_prefix,
        "qector_decoder_v3": qector_version,
        "mcp": mcp_version,
        "failures": failures,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
