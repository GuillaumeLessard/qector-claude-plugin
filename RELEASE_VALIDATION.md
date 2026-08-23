# Release Validation

Run the following gates before publishing a release:

```bash
python scripts/release_validate.py
python scripts/test_structure.py
python -m unittest discover -s tests -v
python mcp/tests/test_mcp_stdio.py
ruff check .
python scripts/build_release.py --all
```

For an actual self-contained Desktop release, provide a tested virtual
environment to the builder:

```bash
python scripts/build_release.py --desktop --runtime-root /path/to/venv
```

Then install the produced `.mcpb` through Claude Desktop and repeat the MCP
stdio validation from the installed artifact directory. Never mark a release
as validated solely because source-tree tests pass.
