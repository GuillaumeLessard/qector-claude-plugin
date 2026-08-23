# QECTOR Claude Plugin v1.0.5

**General availability · August 23, 2026**

QECTOR v1.0.5 delivers a verified quantum error correction workspace that
installs cleanly on every machine Claude Code and Claude Desktop support.
This release removes the last portability barriers between our software
and your hardware: install once, and the runtime locates, validates, and
uses the correct interpreter wherever your work takes you.

## Engineered for every environment

Modern operating systems have diverged on how Python is presented, and
version 1.0.4 assumed more uniformity than the real world provides.
Version 1.0.5 replaces that assumption with engineered resolution.

Every entry point now starts through a launcher we ship and stand behind.
It honors an administrator supplied interpreter first, then discovers a
suitable system Python, verifies the version against the supported range,
and executes only a fully qualified candidate. When nothing qualifies,
the operator receives precise remediation guidance instead of a stack
trace. The supported window is Python 3.9 through 3.13, matching the
published native wheel matrix exactly.

## Key improvements

* **Universal launcher, shipped everywhere.** Present in the plugin
  archive, the source distribution, and the Desktop bundle, with platform
  appropriate selection handled by manifest overrides.
* **Interpreter governance on every surface.** Administrators pin a
  specific interpreter through configuration on Claude Code and Claude
  Desktop alike; the pinned choice travels to the runtime and always
  supersedes discovery.
* **First class Windows packaging.** The Desktop bundle resolves the
  command shim on win32 automatically, while bundled runtime builds take
  complete control of interpreter selection.
* **Integrity preserved end to end.** Launchers are packaged executable
  with deterministic timestamps across every archive, so rebuilds are bit
  identical and verification never degrades.
* **Stronger automated gates.** Bundle validation now rejects version
  drift in auxiliary archives, confirms launcher presence in the current
  bundle, and the metadata gate resolves inherited versions statically
  with zero runtime prerequisites.

## Verification and quality assurance

The release passed the complete gate suite before publication: eight
hundred thirty two structural assertions, seventy four mathematical and
protocol unit tests covering all sixteen reference theorems, source and
bundle validation, metadata cross checks, and deterministic rebuild
comparison. Artifact hashes are published with sidecars, a combined
checksum manifest, an SBOM, and provenance records binding each artifact
to its release commit and runtime pins.

## Availability

* **Claude Code:** install from the marketplace with two commands, or
  update an existing installation and restart your session.
* **Claude Desktop:** download the Desktop bundle from this release page
  and install it through Extensions with a single click.
* **Air gapped deployments:** fully supported offline; the default
  configuration performs no network operations.

Web, iOS, Android, and Cowork arrive with the hosted remote connector on
the 1.1.x roadmap.

## Licensing

QECTOR is proprietary software from iD01t Productions. The backend engine
remains free for personal, academic, educational, and non commercial
research. Commercial licensing, evaluation terms, and support are
available at qector.store.

Every correction QECTOR returns has been verified against the parity
relation H c = s mod 2 before it leaves the server. That guarantee is
the product, and version 1.0.5 delivers it everywhere you work.
