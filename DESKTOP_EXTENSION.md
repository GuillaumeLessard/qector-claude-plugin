# Desktop Extension

The canonical Claude Desktop artifact is
`dist/qector-claude-desktop-<version>.mcpb`. Install it through Claude Desktop:

1. Open **Settings**.
2. Open **Extensions** and then **Advanced settings**.
3. Choose **Install Extension** and select the `.mcpb` artifact.
4. Restart Claude Desktop.

The extension defaults to the 8-tool safe profile. It does not expose research
or administrative operations. The artifact includes the manifest, icon, safe
server source, dependency requirements, license, privacy notice, and release
provenance. A fully self-contained runtime is produced only with the release
builder's `--runtime-root` option; otherwise the extension explicitly requires
a compatible local Python environment.
