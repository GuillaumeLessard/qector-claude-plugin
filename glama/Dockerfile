# Glama runtime for QECTOR Claude Plugin
#
# Purpose
# -------
# The QECTOR MCP servers (`mcp_server_library.py` and friends) are
# stdio-only. Glama's automated check connects over HTTP and runs the
# MCP `initialize` and `tools/list` requests. This Dockerfile wraps the
# stdio server in `mcp-proxy` (streamable-HTTP transport) so Glama's
# HTTP probe can introspect the surface.
#
# Build
# -----
#   docker build -f glama/Dockerfile -t qector-claude-plugin:1.0.4 .
#
# Run
# ---
#   docker run --rm -p 8080:8080 qector-claude-plugin:1.0.4
#
# Then Glama can probe:
#   - initialize at POST http://<host>:8080/mcp
#   - tools/list at POST http://<host>:8080/mcp
# with the standard MCP JSON-RPC 2.0 envelope over the Streamable HTTP
# transport.
#
# Why a wrapper and not a real HTTP server
# ----------------------------------------
# QECTOR is intentionally a local, fail-closed stdio plugin. The
# `mcp_server_library.py` runs the same code that ships in the
# `qector-claude-plugin-1.0.4.zip` plugin archive. Wrapping it in
# `mcp-proxy` keeps the entire trust zone (8 stable tools, per-tool
# call budgets, fail-closed `H c = s (mod 2)` verification) intact
# while satisfying Glama's HTTP introspection requirement.
#
# What's in the image
# -------------------
#   - python:3.12-slim base
#   - qector-decoder-v3==1.0.0 (the QEC backend wheel; the strict-math
#     engine that every decode call runs against)
#   - mcp==1.26.0 (the MCP SDK the QECTOR servers are written against)
#   - mcp-proxy (streamable-HTTP wrapper from sparfenyuk/mcp-proxy)
#   - The two files Glama needs to start the server:
#       mcp/mcp_server_library.py
#       mcp/qector_mcp_contract.py

FROM python:3.12-slim AS base

# System deps. We need git to install mcp-proxy from GitHub (the PyPI
# version is older; we want the latest streamable-HTTP support).
# build-essential is left in just in case a wheel isn't available for
# the target arch; it's removed at the end of this stage.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        git \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Python deps. Pin mcp to the same version QECTOR ships against, and
# install qector-decoder-v3 at the exact version the plugin is tested
# against. mcp-proxy is installed from GitHub for the latest
# streamable-HTTP support; pin to a known-good tag.
ARG QECTOR_DECODER_VERSION=1.0.0
ARG MCP_VERSION=1.26.0
ARG MCP_PROXY_REF=v0.12.0

RUN pip install --no-cache-dir \
        "mcp==${MCP_VERSION}" \
        "qector-decoder-v3[stim]==${QECTOR_DECODER_VERSION}" \
        "numpy>=1.26,<2.3" \
        "cryptography>=48.0.1,<50" \
    && pip install --no-cache-dir \
        "git+https://github.com/sparfenyuk/mcp-proxy.git@${MCP_PROXY_REF}"

# Copy only the files Glama needs to start the server. We do NOT copy
# the whole repo — the rest of the source is dev-only and would just
# bloat the image and increase the attack surface.
WORKDIR /app
COPY mcp/mcp_server_library.py /app/mcp/mcp_server_library.py
COPY mcp/qector_mcp_contract.py /app/mcp/qector_mcp_contract.py

# Healthcheck. `mcp-proxy` exposes a Streamable HTTP endpoint at
# /mcp on the bound port. A TCP probe on 8080 is enough to confirm
# the wrapper started; the actual MCP introspection is done by
# Glama's checker, not by the healthcheck.
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=5 \
    CMD python -c "import socket,sys; s=socket.socket(); \
s.settimeout(2); \
sys.exit(0 if s.connect_ex(('127.0.0.1', 8080))==0 else 1)"

# Expose the Streamable HTTP port.
EXPOSE 8080

# Run mcp-proxy in streamable-http mode, wrapping the stdio QECTOR
# library server. mcp-proxy's default streamable-http path is /mcp.
# Environment:
#   - QECTOR_SILENT:  suppress the QECTOR decoder banner on stderr
#   - PYTHONUNBUFFERED: keep stdio line-buffered (mcp-proxy pipes the
#                       child's stdout back to its HTTP clients)
#   - QECTOR_ARTIFACT_DIR: artifacts (when any tool writes one) land
#                          in a path the image can write to
ENV QECTOR_SILENT=1 \
    PYTHONUNBUFFERED=1 \
    QECTOR_ARTIFACT_DIR=/tmp/qector-artifacts

RUN mkdir -p /tmp/qector-artifacts

# The library server is the canonical 8-tool stable surface, which is
# the surface Glama is most likely to probe. We pass `--transport
# streamablehttp` to mcp-proxy to be explicit about the protocol
# (default is sse; streamablehttp is what Glama's checker uses in 2026).
#
# `--host 0.0.0.0` binds all interfaces so the container is reachable
# from outside (Glama runs the container with port mapping).
CMD ["mcp-proxy", "--host", "0.0.0.0", "--port", "8080", \
     "--transport", "streamablehttp", \
     "--allow-origin", "*", \
     "--", "python", "/app/mcp/mcp_server_library.py"]
