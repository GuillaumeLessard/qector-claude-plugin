# Release Validation

Run every gate below before publishing. All of them are also run by CI on
Python 3.10–3.13 against both the `mcp` 1.x and 2.x SDK lines.

```bash
python scripts/release_validate.py                 # versions, pins, defaults, disclosures
python scripts/validate_source.py                  # tree shape
python scripts/export_schemas.py --check           # schemas/ matches the live servers
python scripts/generate_integrity_manifest.py --check
QECTOR_SILENT=1 python -m unittest discover -s tests -v
python mcp/tests/test_mcp_stdio.py                 # 5 servers over real stdio
ruff check .
python scripts/build_release.py --all --signing-key ~/.qector/release-signing.pem
python scripts/validate_plugin_bundle.py           # archive contents, INTEGRITY.json and signatures inside each, then a live strict stdio boot of every shipped archive
python scripts/sign_release.py --verify dist       # Ed25519 signatures (add --pubkey <key> for origin)
sha256sum -c dist/SHA256SUMS
```

Offline-path smoke (connected host):

```bash
python scripts/build_wheelhouse.py --out /tmp/wh
sh scripts/install_offline.sh /tmp/wh /tmp/venv-qector
```

Desktop bundle with vendored runtime (platform specific):

```bash
python scripts/build_release.py --desktop --bundle-lib /tmp/wh
```

Then install the produced `.mcpb` through Claude Desktop and call
`airgap_status`, `integrity_check` and `decode_syndrome` from the client.
Never mark a release as validated solely because source-tree tests pass.

## Native-platform checks (release-blocking)

The gates above run on Linux. The `native` job in `.github/workflows/ci.yml`
runs the rows below on `windows-latest` and `macos-latest` on every push:
a checkout under Git for Windows' default `core.autocrlf=true`, the
launchers (`.cmd`, `.ps1`, POSIX) with and without a qualifying interpreter,
the full suite, the archive build, `validate_plugin_bundle.py`, and
`scripts/boot_from_manifest.py`, which extracts the Desktop bundle and
spawns the exact `command`/`args`/`env` its manifest names for that
platform in exec form (as Claude Desktop does), then checks 12 tools,
`integrity_check.passed` with a pinned signature, `air_gapped: true` and a
verified decode. A release is validated only when that job is green on the
commit being released; record the run URL in the release notes.

| Platform | Check | Expected |
|:---------|:------|:---------|
| Windows 10/11, python.org 3.11–3.13 installed | install `qector-claude-desktop-<v>.mcpb`, call `airgap_status` | `powershell.exe -File scripts\qector-python.ps1` starts the server; `air_gapped: true`; `integrity_check.signature.source == "pinned"` |
| Windows, Claude Code | `claude plugin install qector@qector-tools` | either the server starts (Git for Windows `sh` on PATH) or the README's `claude mcp add … cmd /c …\qector-python.cmd` fallback starts it; hooks report Git Bash or the documented PowerShell notice |
| Windows, git checkout | `git clone` then `python scripts/generate_integrity_manifest.py --check` | `passed: true` (no CRLF conversion thanks to `.gitattributes`) |
| macOS, Claude Desktop (no Homebrew Python on the launchd PATH) | install the `.mcpb` without setting *Python interpreter* | launcher finds `/Library/Frameworks/Python.framework/...` or Homebrew, or reports the documented "set the Python interpreter setting" message on stderr |
| macOS | `sh scripts/install_offline.sh <wheelhouse> <venv>` | `shasum -a 256 -c` path verifies, runtime check `ok` |

Until the `native` job has run green for the release commit, release notes
must say that Windows and macOS installs are automated but not yet
executed.
