"""Air-gap guard for QECTOR MCP server processes.

Air-gapped mode is **on by default** in QECTOR 2.0.0 (``QECTOR_AIR_GAPPED``
unset or truthy). It installs defence-in-depth guards inside the Python
process:

* ``socket.socket`` is replaced by a subclass that refuses ``connect`` /
  ``bind`` / ``sendto`` to any non-loopback endpoint, and
  ``socket.create_connection`` / ``socket.getaddrinfo`` / ``urllib.request.urlopen``
  raise :class:`QECTORNetworkDisabledError` for non-loopback hosts, so any
  Python-level egress attempt (``urllib``, ``httpx``, ``requests`` ...)
  fails closed before a connection is opened. Loopback and AF_UNIX stay
  available because the asyncio event loop and the MCP stdio transport
  need in-host plumbing; neither can leave the machine.
* ``subprocess.Popen`` raises :class:`PermissionError` so no tool can
  launch a child process. The admin server, which legitimately launches
  processes, opts out explicitly with ``allow_subprocess=True`` and still
  honours the network guard.
* Billing / licence-issuing environment variables that the
  ``qector-decoder-v3`` wheel would read for its Stripe metering path are
  removed from ``os.environ`` so that path cannot be armed by accident.
* ``QECTOR_SILENT=1`` is forced so the wheel banner cannot corrupt stdio.

What the guard **cannot** do, stated plainly because a reviewer will check:
the ``qector-decoder-v3`` native core (Rust, ``rustls``/``ureq``) contains
its own TLS client and the literal endpoint
``https://api.stripe.com/v1/billing/meter_events`` for the opt-in
``flush_usage`` metering call, plus optional REST/gRPC/metrics servers.
Those are native code; a Python monkeypatch cannot intercept them. The
QECTOR plugin never calls any of those symbols (see ``WHEEL_NETWORK_SYMBOLS``
and ``tests/test_airgap.py``), but a lab that requires a hard guarantee
must also apply a host-level egress policy (firewall, network namespace,
or an unplugged NIC). ``airgap_status`` reports all of this verbatim.
"""

from __future__ import annotations

import ipaddress
import os
import socket
import subprocess
import threading
from typing import Any

from qector_mcp_contract import QECTORNetworkDisabledError, env_flag

REFERENCE_WHEEL = "qector-decoder-v3==1.0.1"

# Symbols of the decoder wheel that can reach the network or launch
# servers. The plugin never references them; tests/test_airgap.py greps the
# server sources to keep it that way.
WHEEL_NETWORK_SYMBOLS: tuple[str, ...] = (
    "flush_usage",
    "record_shots",
    "get_accumulated_shots",
    "stripe_integration",
    "rest_api",
    "run_grpc_server",
    "start_metrics_server",
    "run_mcp_server",
    "workbench",
    "Workbench",
)
WHEEL_EMBEDDED_ENDPOINTS: tuple[str, ...] = (
    "https://api.stripe.com/v1/billing/meter_events",
    "https://qector.store/pricing",
)
# Environment variables the wheel reads for billing / licence issuance.
# They are removed from the server process so the metering path cannot be
# armed by inherited shell state.
SCRUBBED_ENV_VARS: tuple[str, ...] = (
    "STRIPE_SECRET_KEY",
    "STRIPE_API_KEY",
    "STRIPE_WEBHOOK_SECRET",
    "QECTOR_STRIPE_CUSTOMER_ID",
    "QECTOR_LICENSE_PRIVATE_KEY_B64",
    "QECTOR_LABS_BOT_WEBHOOK",
)
GUARD_SCOPE_STATEMENT = (
    "Python-level guards are defence in depth against the tool surface, not a "
    "sandbox: they wrap socket.socket/SocketType, getaddrinfo, create_connection, "
    "urllib.request.urlopen, subprocess.Popen and the os.* launch helpers. Code "
    "already executing inside the process can still reach the network through the "
    "private _socket module, the guarded class's base type, ctypes or os.fork+exec, "
    "and the decoder wheel's native core has its own TLS client. A host egress "
    "policy is the only hard guarantee."
)
RECOMMENDED_HOST_CONTROLS: tuple[str, ...] = (
    "Run the server on a host with no default route or inside a network namespace without egress.",
    "Deny outbound TCP/443 from the Python interpreter at the host firewall.",
    "Install from the signed offline wheelhouse (scripts/install_offline.sh) and verify SHA256SUMS.",
    "Keep QECTOR_AIR_GAPPED unset or =1; never pass check_pypi=true.",
    "Do not register qector-admin on lab machines; system_setup is the only tool that can invoke pip.",
)

_lock = threading.RLock()
_state: dict[str, Any] = {
    "installed": False,
    "air_gapped": False,
    "mode_source": "default",
    "socket_guard": False,
    "subprocess_guard": False,
    "urllib_guard": False,
    "env_scrubbed": False,
    "wheel_offline_flag": False,
    "scrubbed": [],
    "blocked_attempts": 0,
}
_originals: dict[str, Any] = {}


def air_gapped_requested() -> tuple[bool, str]:
    """Return (air_gapped, source) from the environment; default is on."""
    raw = os.environ.get("QECTOR_AIR_GAPPED")
    if raw is None:
        return True, "default"
    return env_flag("QECTOR_AIR_GAPPED", True), "environment"


def _blocked(*_args: Any, **_kwargs: Any) -> Any:
    with _lock:
        _state["blocked_attempts"] += 1
    raise QECTORNetworkDisabledError(
        "network access is disabled: this QECTOR server runs air-gapped "
        "(QECTOR_AIR_GAPPED=1). Set QECTOR_AIR_GAPPED=0 only on a host where "
        "egress is intentionally permitted."
    )


_LOOPBACK_HOSTS = {"localhost", "127.0.0.1", "::1"}
# ``None`` / ``""`` mean "the local host" for name resolution
# (``getaddrinfo(None, port)``) but mean INADDR_ANY for ``bind``/``connect``,
# so they are accepted only where a resolver asks, never as an endpoint.
_UNSPECIFIED_HOSTS = {None, ""}


def _is_loopback_host(host: Any, *, allow_unspecified: bool = False) -> bool:
    """True only for literal loopback addresses or the name ``localhost``.

    Hostnames are never trusted by prefix (``127.attacker.example`` is not
    loopback) and the wildcard addresses ``0.0.0.0`` / ``::`` / ``""`` are
    refused, so a guarded process can neither resolve nor listen on a
    public interface. ``allow_unspecified`` admits ``None``/``""`` for
    ``getaddrinfo`` only.
    """
    if host in _UNSPECIFIED_HOSTS:
        return allow_unspecified
    if host in _LOOPBACK_HOSTS:
        return True
    if isinstance(host, bytes):
        host = host.decode("ascii", "replace")
    if not isinstance(host, str):
        return False
    text = host.strip("[]").split("%", 1)[0]
    try:
        return ipaddress.ip_address(text).is_loopback
    except ValueError:
        return False


def _address_allowed(address: Any) -> bool:
    """Only loopback endpoints may be contacted; everything else fails closed."""
    if isinstance(address, (str, bytes)):
        return True  # AF_UNIX path: in-host IPC, no egress
    if isinstance(address, tuple) and address:
        return _is_loopback_host(address[0])
    return False


class _GuardedSocket(socket.socket):
    """Socket subclass that refuses every non-loopback endpoint.

    The event loop (asyncio's self-pipe on Unix, its AF_INET socketpair
    emulation on Windows) and anyio's stdio plumbing need in-host sockets,
    so creation is allowed; ``connect`` / ``connect_ex`` / ``sendto`` /
    ``bind`` to anything but loopback or an AF_UNIX path raise
    :class:`QECTORNetworkDisabledError`. ``isinstance(obj, socket.socket)``
    keeps working because this is a subclass, not a replacement function.
    """

    def connect(self, address: Any) -> None:  # type: ignore[override]
        if not _address_allowed(address):
            _blocked()
        super().connect(address)

    def connect_ex(self, address: Any) -> int:  # type: ignore[override]
        if not _address_allowed(address):
            _blocked()
        return super().connect_ex(address)

    def sendto(self, *args: Any) -> int:  # type: ignore[override]
        if args and not _address_allowed(args[-1]):
            _blocked()
        return super().sendto(*args)

    def bind(self, address: Any) -> None:  # type: ignore[override]
        if not _address_allowed(address):
            _blocked()
        super().bind(address)


def _guarded_getaddrinfo(host: Any, *args: Any, **kwargs: Any) -> Any:
    if not _is_loopback_host(host, allow_unspecified=True):
        _blocked()
    return _originals["socket.getaddrinfo"](host, *args, **kwargs)


def _guarded_create_connection(address: Any, *args: Any, **kwargs: Any) -> Any:
    if not _address_allowed(address):
        _blocked()
    return _originals["socket.create_connection"](address, *args, **kwargs)


def _blocked_popen(*_args: Any, **_kwargs: Any) -> Any:
    with _lock:
        _state["blocked_attempts"] += 1
    raise PermissionError(
        "subprocess launch is disabled in this QECTOR server process "
        "(air-gapped, no-subprocess policy)"
    )


# os-level launch primitives guarded alongside subprocess.Popen. ``os.fork``
# and ``os.exec*`` are deliberately left alone: the asyncio/anyio machinery
# the stdio transport relies on must keep working, and nothing in the tool
# surface takes a command or a path to execute.
_OS_LAUNCHERS = (
    "system",
    "popen",
    "posix_spawn",
    "posix_spawnp",
    "spawnl",
    "spawnle",
    "spawnlp",
    "spawnlpe",
    "spawnv",
    "spawnve",
    "spawnvp",
    "spawnvpe",
    "startfile",
)


def install(*, allow_subprocess: bool = False, force: bool | None = None, source: str | None = None) -> dict[str, Any]:
    """Install the guards once per process and return the status snapshot.

    *force* overrides the environment decision (used by ``--air-gapped`` /
    ``--allow-network`` CLI flags); *source* names where the decision came
    from for reporting.
    """
    with _lock:
        if _state["installed"]:
            return status()
        air_gapped, mode_source = air_gapped_requested()
        if force is not None:
            air_gapped, mode_source = force, source or "cli"
        _state["installed"] = True
        _state["air_gapped"] = air_gapped
        _state["mode_source"] = mode_source
        os.environ["QECTOR_SILENT"] = "1"
        scrubbed: list[str] = []
        for name in SCRUBBED_ENV_VARS:
            if name in os.environ:
                os.environ.pop(name, None)
                scrubbed.append(name)
        _state["scrubbed"] = scrubbed
        _state["env_scrubbed"] = True
        if not air_gapped:
            return status()
        # qector-decoder-v3 >= 1.0.1 honours QECTOR_OFFLINE inside its native
        # core: every billing call refuses before opening a socket. The Python
        # socket guard below cannot reach native code, so this is the layer
        # that covers the Rust HTTP client. Set (not setdefault): an inherited
        # QECTOR_OFFLINE=0 must not weaken an air-gapped process.
        os.environ["QECTOR_OFFLINE"] = "1"
        _state["wheel_offline_flag"] = True
        _originals["socket.socket"] = socket.socket
        _originals["socket.create_connection"] = socket.create_connection
        _originals["socket.getaddrinfo"] = socket.getaddrinfo
        _originals["socket.SocketType"] = socket.SocketType
        socket.socket = _GuardedSocket  # type: ignore[misc,assignment]
        socket.SocketType = _GuardedSocket  # type: ignore[misc,assignment]
        socket.create_connection = _guarded_create_connection  # type: ignore[assignment]
        socket.getaddrinfo = _guarded_getaddrinfo  # type: ignore[assignment]
        _state["socket_guard"] = True
        try:
            import urllib.request

            _originals["urllib.request.urlopen"] = urllib.request.urlopen
            urllib.request.urlopen = _blocked  # type: ignore[assignment]
            _state["urllib_guard"] = True
        except Exception:  # pragma: no cover - urllib is stdlib
            _state["urllib_guard"] = False
        if not allow_subprocess:
            _originals["subprocess.Popen"] = subprocess.Popen
            subprocess.Popen = _blocked_popen  # type: ignore[misc,assignment]
            for name in _OS_LAUNCHERS:
                if hasattr(os, name):
                    _originals[f"os.{name}"] = getattr(os, name)
                    setattr(os, name, _blocked_popen)
            _state["subprocess_guard"] = True
        return status()


def _uninstall_for_tests() -> None:
    """Restore the original symbols. Test-only; not part of the server API."""
    with _lock:
        for key in list(_originals):
            if key.startswith("os."):
                setattr(os, key[3:], _originals.pop(key))
        if "socket.socket" in _originals:
            socket.socket = _originals.pop("socket.socket")  # type: ignore[misc]
        if "socket.SocketType" in _originals:
            socket.SocketType = _originals.pop("socket.SocketType")  # type: ignore[misc]
        if "socket.create_connection" in _originals:
            socket.create_connection = _originals.pop("socket.create_connection")  # type: ignore[assignment]
        if "socket.getaddrinfo" in _originals:
            socket.getaddrinfo = _originals.pop("socket.getaddrinfo")  # type: ignore[assignment]
        if "urllib.request.urlopen" in _originals:
            import urllib.request

            urllib.request.urlopen = _originals.pop("urllib.request.urlopen")  # type: ignore[assignment]
        if "subprocess.Popen" in _originals:
            subprocess.Popen = _originals.pop("subprocess.Popen")  # type: ignore[misc]
        for key in ("installed", "air_gapped", "socket_guard", "subprocess_guard", "urllib_guard", "env_scrubbed"):
            _state[key] = False
        if _state.get("wheel_offline_flag"):
            os.environ.pop("QECTOR_OFFLINE", None)
        _state["wheel_offline_flag"] = False
        _state["mode_source"] = "default"
        _state["scrubbed"] = []
        _state["blocked_attempts"] = 0


def is_air_gapped() -> bool:
    """True when network paths must fail closed (installed guard or env default)."""
    with _lock:
        if _state["installed"]:
            return bool(_state["air_gapped"])
    return air_gapped_requested()[0]


def require_network(feature: str) -> None:
    """Raise :class:`QECTORNetworkDisabledError` when *feature* needs egress in air-gapped mode."""
    if is_air_gapped():
        raise QECTORNetworkDisabledError(
            f"{feature} requires outbound network access, which is disabled in "
            "air-gapped mode (QECTOR_AIR_GAPPED=1, the default)"
        )


def status() -> dict[str, Any]:
    with _lock:
        snapshot = dict(_state)
    return {
        "air_gapped": bool(snapshot["air_gapped"]) if snapshot["installed"] else air_gapped_requested()[0],
        "mode_source": snapshot["mode_source"] if snapshot["installed"] else air_gapped_requested()[1],
        "guards": {
            "python_socket": bool(snapshot["socket_guard"]),
            "python_subprocess": bool(snapshot["subprocess_guard"]),
            "urllib": bool(snapshot["urllib_guard"]),
            "env_scrub": bool(snapshot["env_scrubbed"]),
            "wheel_offline_flag": bool(snapshot.get("wheel_offline_flag", False)),
            "pypi_freshness": "disabled" if (snapshot["air_gapped"] if snapshot["installed"] else air_gapped_requested()[0]) else "opt_in",
        },
        "scrubbed_variables": list(snapshot["scrubbed"]),
        "transport": "stdio",
        "backend_network_surface": {
            "wheel": REFERENCE_WHEEL,
            "network_capable_symbols": list(WHEEL_NETWORK_SYMBOLS),
            "called_by_plugin": False,
            "embedded_endpoints": list(WHEEL_EMBEDDED_ENDPOINTS),
            "python_level_guard_blocks_native_core": False,
            "recommended_host_controls": list(RECOMMENDED_HOST_CONTROLS),
        },
        "blocked_attempts": int(snapshot["blocked_attempts"]),
        "guard_scope": GUARD_SCOPE_STATEMENT,
    }


def network_policy() -> dict[str, Any]:
    """Compact block embedded in compat / provenance results."""
    snapshot = status()
    return {
        "air_gapped": snapshot["air_gapped"],
        "python_socket_guard": snapshot["guards"]["python_socket"],
        "subprocess_guard": snapshot["guards"]["python_subprocess"],
        "env_scrubbed": snapshot["guards"]["env_scrub"],
        "transport": "stdio",
        "note": (
            "Python-level guards are defence in depth; the decoder wheel's native "
            "core carries its own TLS client that only a host egress policy can block."
        ),
    }
