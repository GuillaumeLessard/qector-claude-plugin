# QECTOR Claude Plugin v1.0.5 is live

Version 1.0.5 makes QECTOR work everywhere Claude Code and Claude Desktop
run, on every machine shape, without a single manual PATH edit.

## Why this release matters

Stock macOS ships `python3` but no bare `python`. Debian, Ubuntu, and
Fedora do the same. Windows adds its own trap with the Store alias.
Version 1.0.4 assumed a bare `python` existed and broke on all of them.
This release fixes that class of failure permanently: every entry point
now boots through a shipped launcher that hunts down a real interpreter,
checks it against the supported window, and refuses loudly when nothing
qualifies. No silent misbehavior, no half working installs, no support
tickets that begin with "it works on my machine".

## Highlights

* **Universal launcher** in every archive and in the Desktop bundle.
  Resolution order is your pinned override, then `python3`, then
  `python`, with the Windows py launcher tried first. Unsupported interpreters are
  skipped, never fatal mid search.
* **Supported range enforcement.** Only Python 3.9 through 3.13 pass,
  matching the published wheel matrix exactly. A 3.14 only machine gets
  an immediate, actionable message instead of a deep import crash.
* **Interpreter pinning on every surface.** Claude Code asks once via
  user configuration and Desktop does the same; your answer reaches the
  launcher as an environment variable and wins over auto resolution.
* **Windows done properly inside the bundle.** Platform overrides select
  the command shim on win32 while macOS and Linux keep the shell shim,
  and bundled runtime builds bypass overrides entirely so the packed
  interpreter always takes precedence.
* **Executable permissions that survive packaging.** Launcher entries are
  stamped 0755 with deterministic timestamps, so hashes stay stable and
  extraction never strips the execute bit.
* **Stronger release gates.** The bundle validator now fails any skill
  archive whose declared version drifts from the release version, and
  confirms launcher presence in the current bundle. The metadata gate now
  resolves inherited versions by reading source, needing zero runtime
  dependencies to run.

## Surface status

* Claude Code on Windows, macOS, and Linux: fully supported today.
* Claude Desktop on Windows and macOS: one click install, fully supported.
* Air gapped and restricted environments: fully supported offline.
* Web, iOS, Android, and Cowork: arriving with the hosted remote
  connector on the 1.1.x roadmap, since local stdio cannot reach those
  surfaces by architecture.

## Integrity

Artifacts are built deterministically with fixed timestamps, so rebuilds
reproduce byte for byte. The registry descriptor matches the Desktop
bundle hash exactly, sidecars cover each artifact, a combined checksum
file and an SBOM ship alongside, and provenance records the release
commit and runtime pins. All of it lives in the repository under dist.

## Get it

Claude Code users: run the two marketplace commands from the Quick start
section of the repository README.

Claude Desktop users: open Settings, then Extensions, then Advanced
settings, then Install Extension, and pick the Desktop bundle from the
v1.0.5 release page. Restart when prompted.

Full notes, hashes, and validation gates live in the repository README
and CHANGELOG.

QECTOR: local quantum error correction for Claude, verified against
H c = s mod 2 before any correction leaves the server.
