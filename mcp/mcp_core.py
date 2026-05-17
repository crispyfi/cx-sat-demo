"""Shared infrastructure for the AOS-CX troubleshooting MCP server.

A standalone MCP server that exposes AOS-CX troubleshooting checks as
tools for Claude Code.

It builds on the project's domain modules: ``_aoscx`` provides the
authenticated REST session and the ``CXLibrary*`` modules provide the
checks. Each check's pass/fail outcome and the per-field detail it
records are collected into a structured response.

Setup:
  * Switch credentials are read from the repo's ``.env`` file
    (``CX_USERNAME`` / ``CX_PASSWORD``).
  * The AOS-CX REST API version is fixed at v10.16.
  * ``CX_SITE_FILE`` optionally overrides the path to site.yaml
    (default: at the repo root).

site.yaml is read only for the device hostname/IP inventory; no other
keys in it are used.

Per-domain check modules (e.g. ``vsx_checks.py``) import ``mcp`` and
``run_checks`` from here to register their tools.
"""

import logging
import os
import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

# The domain modules use bare imports (``import _aoscx``); their import
# root is the libraries/ directory. This module lives in mcp/, one
# directory below the repo root.
_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "libraries"))

# Switch credentials (CX_USERNAME / CX_PASSWORD) come from the repo's
# .env file. Load it explicitly so the server works regardless of the
# directory Claude Code launches it from.
load_dotenv(_REPO_ROOT / ".env")

import _aoscx  # noqa: E402


# AOS-CX REST API version, fixed for now.
API_VERSION = "v10.16"

SITE_FILE = Path(os.environ.get("CX_SITE_FILE") or _REPO_ROOT / "site.yaml")

mcp = FastMCP("aoscx")


# =========================================================================
# Log capture
# =========================================================================
# The domain modules emit per-field diagnostics to the stdlib logger
# named "RobotFramework" — and only to its handlers, never to stdout,
# so MCP stdio stays clean. A buffering handler lets us surface those
# values alongside each check's pass/fail result.


class _LogCapture(logging.Handler):
    def __init__(self):
        super().__init__(level=logging.INFO)
        self.records = []

    def emit(self, record):
        self.records.append(record.getMessage())

    def reset(self):
        self.records.clear()


_capture = _LogCapture()
_diag_logger = logging.getLogger("RobotFramework")
_diag_logger.setLevel(logging.INFO)
_diag_logger.addHandler(_capture)


# =========================================================================
# site.yaml inventory
# =========================================================================


def _devices():
    """Device list from site.yaml ([] if the file is missing/empty)."""
    if not SITE_FILE.is_file():
        return []
    data = yaml.safe_load(SITE_FILE.read_text()) or {}
    return data.get("devices") or []


def _resolve(device):
    """Find a device by exact hostname/IP, then by case-insensitive hostname."""
    devices = _devices()
    for d in devices:
        if d.get("hostname") == device or d.get("ip") == device:
            return d
    for d in devices:
        if str(d.get("hostname", "")).lower() == str(device).lower():
            return d
    return None


# =========================================================================
# Check runner
# =========================================================================


def run_checks(device, library_class, checks):
    """Connect to one switch, run a sequence of checks, return a structured report.

    Args:
        device: Hostname or management IP of a switch in site.yaml.
        library_class: A ``CXLibrary*`` class whose methods are the checks.
        checks: List of ``(result_name, method_name)`` pairs, run in order.

    Each check method is called with the device IP and is expected to
    raise ``AssertionError`` on a failed check. Any other exception is
    reported as an ``error``. Returns ``{device, ip, overall, checks}``
    where each entry carries status (pass | fail | error), a message,
    and ``detail`` — the per-field values the check recorded.
    """
    dev = _resolve(device)
    if dev is None:
        known = ", ".join(
            str(d.get("hostname") or d.get("ip")) for d in _devices()
        )
        return {"error": f"device {device!r} not found in site.yaml (known: {known})"}

    ip = dev.get("ip")
    hostname = dev.get("hostname")

    # Each call is a fresh troubleshooting snapshot — drop any responses
    # _aoscx cached for this device on a previous call.
    for key in [k for k in _aoscx._cache if k[0] == ip]:
        del _aoscx._cache[key]

    try:
        _aoscx.connect(ip, API_VERSION)
    except Exception as e:
        return {
            "device": hostname,
            "ip": ip,
            "overall": "error",
            "error": f"connection failed: {e}",
        }

    lib = library_class()
    results = []
    try:
        for name, method_name in checks:
            _capture.reset()
            try:
                getattr(lib, method_name)(ip)
                status, message = "pass", "ok"
            except AssertionError as e:
                status, message = "fail", str(e)
            except Exception as e:
                status, message = "error", f"{type(e).__name__}: {e}"
            results.append(
                {
                    "name": name,
                    "status": status,
                    "message": message,
                    "detail": list(_capture.records),
                }
            )
    finally:
        _aoscx.disconnect(ip)

    if any(c["status"] == "error" for c in results):
        overall = "error"
    elif any(c["status"] == "fail" for c in results):
        overall = "fail"
    else:
        overall = "pass"

    return {"device": hostname, "ip": ip, "overall": overall, "checks": results}


# =========================================================================
# Generic tools
# =========================================================================


@mcp.tool()
def list_devices() -> list[dict]:
    """List the switches defined in site.yaml.

    Returns each device's hostname and management IP only. Use the
    hostname or IP as the ``device`` argument to the check tools.
    """
    return [
        {"hostname": d.get("hostname"), "ip": d.get("ip")}
        for d in _devices()
    ]
