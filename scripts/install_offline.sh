#!/bin/sh
# QECTOR offline installer (POSIX sh). Installs the pinned runtime from a
# wheelhouse produced by scripts/build_wheelhouse.py without touching any
# package index. Fails closed if a checksum does not match.
#
#   sh scripts/install_offline.sh /media/usb/wheelhouse [/path/to/venv]
#
# The second argument names a virtual environment to create (default
# ./.venv-qector). The interpreter is resolved by scripts/qector-python.
set -eu

WHEELHOUSE="${1:?usage: install_offline.sh WHEELHOUSE_DIR [VENV_DIR]}"
VENV="${2:-./.venv-qector}"
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
PY="$HERE/qector-python"

[ -d "$WHEELHOUSE" ] || { echo "wheelhouse not found: $WHEELHOUSE" >&2; exit 2; }
[ -f "$WHEELHOUSE/SHA256SUMS" ] || { echo "SHA256SUMS missing in $WHEELHOUSE" >&2; exit 2; }

echo "== verifying wheelhouse checksums"
if command -v sha256sum >/dev/null 2>&1; then
  (cd "$WHEELHOUSE" && sha256sum -c SHA256SUMS --quiet)
elif command -v shasum >/dev/null 2>&1; then
  (cd "$WHEELHOUSE" && shasum -a 256 -c SHA256SUMS --quiet)
else
  "$PY" "$HERE/build_wheelhouse.py" --verify "$WHEELHOUSE"
fi

echo "== creating virtual environment $VENV"
"$PY" -m venv "$VENV"
if [ -x "$VENV/bin/python" ]; then VPY="$VENV/bin/python"; else VPY="$VENV/Scripts/python.exe"; fi

echo "== installing pinned runtime with --no-index"
"$VPY" -m pip install --no-index --find-links "$WHEELHOUSE" --require-virtualenv \
  --disable-pip-version-check -r "$ROOT/requirements.lock"

echo "== verifying runtime"
QECTOR_SILENT=1 "$VPY" "$ROOT/scripts/qector_runtime_check.py"
echo "== verifying integrity manifest"
"$VPY" "$ROOT/scripts/generate_integrity_manifest.py" --check >/dev/null && echo "INTEGRITY.json OK" || echo "WARNING: INTEGRITY.json drift (see scripts/generate_integrity_manifest.py --check)"
echo
echo "Done. Point QECTOR_PYTHON at $VPY (or activate $VENV) before starting Claude Code / Claude Desktop."
