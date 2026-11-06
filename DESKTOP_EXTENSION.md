# Desktop Extension

The canonical Claude Desktop artifact is
`dist/qector-claude-desktop-<version>.mcpb`. Install it through Claude Desktop:

1. Open **Settings**.
2. Open **Extensions** and then **Advanced settings**.
3. Choose **Install Extension** and select the `.mcpb` artifact.
4. Restart Claude Desktop.

The extension runs `mcp/mcp_server_secure.py --profile safe` with
`QECTOR_AIR_GAPPED=1` and `QECTOR_INTEGRITY_STRICT=1`: twelve tools, no
network, files verified against the bundled `INTEGRITY.json` at every start.
Two optional settings are offered at install time: the Python interpreter to
use (`QECTOR_PYTHON`) and an audit-log directory (`QECTOR_AUDIT_DIR`).

The portable bundle requires a local Python 3.10–3.13 environment with
`requirements.lock` installed. A self-contained, platform-specific bundle
that vendors the runtime into `server/lib` (as the MCPB `python` server type
expects) is produced with:

```bash
python scripts/build_wheelhouse.py --out wheelhouse
python scripts/build_release.py --desktop --bundle-lib wheelhouse
```

The extension does not expose research or administrative operations.

## How the interpreter is found

- **macOS / Linux**: the manifest runs `sh scripts/qector-python …`
  (no dependency on an executable bit surviving extraction). The
  launcher tries `QECTOR_PYTHON`, then `python3.13` … `python3.10`,
  `python3`, `python`, and finally the usual Homebrew, python.org,
  pyenv and `~/.local/bin` locations. That last step matters on macOS:
  a GUI application such as Claude Desktop receives the launchd `PATH`
  (`/usr/bin:/bin:…`), not your shell's, and Apple's `/usr/bin/python3`
  is 3.9 (or a stub that opens the developer-tools dialog). If the
  extension reports "no Python 3.10-3.13 interpreter found", set the
  *Python interpreter* setting to the absolute path of a supported
  interpreter.
- **Windows**: the manifest's `win32` override runs
  `powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File scripts\qector-python.ps1 …`
  (a real executable: Node refuses to spawn `.cmd` files without a
  shell). The script tries `QECTOR_PYTHON`, then `py -3.13` … `py -3.10`,
  `py -3`, `python3`, `python`, rejecting the Microsoft Store stub and
  any 3.14+ interpreter. `scripts\qector-python.cmd` is the equivalent
  for manual `cmd.exe` use.

Both launchers run two passes: first an interpreter that already has the
runtime (`qector_decoder_v3`, `mcp`, `jsonschema`) installed, then any
supported version (the server then reports the missing dependency itself).
An explicit *Python interpreter* setting always wins when it is a supported
version. `scripts/boot_from_manifest.py <bundle>` reproduces exactly what
the host does on the current platform (exec-form spawn of the manifest's
command) and is run by CI on Windows and macOS (RELEASE_VALIDATION.md).

## Line endings

`INTEGRITY.json` hashes the exact bytes of every runtime file and strict
mode refuses to start on any mismatch. The repository therefore ships a
`.gitattributes` with `* -text` so that a Git checkout on Windows
(`core.autocrlf=true` by default) does not rewrite line endings; the
archives are byte-exact by construction. If a modified checkout reports
every runtime file as mismatched, line-ending conversion is the first
thing to check.
