#!/usr/bin/env python3
"""MCP server for AOS-CX switch troubleshooting — VSX checks (PoC).

This is a proof-of-concept. It reuses the project's Robot Framework
domain libraries directly rather than re-implementing anything:
``_aoscx`` provides the authenticated REST session and ``CXLibraryVSX``
provides the VSX assertions. Each VSX keyword is invoked outside Robot;
its pass/fail outcome and the per-field detail it logs are collected
into a structured response.

Scope today is VSX only. The intent is to grow into a full AOS-CX
troubleshooting server by exposing the other CXLibrary* modules the
same way.

Setup (the server is launched by Claude Code via .mcp.json):
  * CX_USERNAME / CX_PASSWORD  switch credentials (required)
  * CX_API_VERSION             AOS-CX REST API version (default v10.16)
  * CX_SITE_FILE               path to site.yaml (default: next to this file)

site.yaml is read only for the device hostname/IP inventory; no other
keys in it are used.
"""

import logging
import os
import sys
from pathlib import Path

import yaml
from mcp.server.fastmcp import FastMCP

# The domain libraries use bare imports (``import _aoscx``); their
# import root is the libraries/ directory, mirroring how the .robot
# suites load them via ``Library  ../libraries/...``.
_REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(_REPO_ROOT / "libraries"))

import _aoscx  # noqa: E402
from CXLibraryVSX import CXLibraryVSX  # noqa: E402


SITE_FILE = Path(os.environ.get("CX_SITE_FILE") or _REPO_ROOT / "site.yaml")
API_VERSION = os.environ.get("CX_API_VERSION") or "v10.16"

mcp = FastMCP("aoscx-vsx")


# =========================================================================
# Log capture
# =========================================================================
# Outside a Robot run, robot.api.logger routes messages to the stdlib
# logger "RobotFramework" (never to stdout, so MCP stdio stays clean).
# A buffering handler lets us surface the per-field values the VSX
# checks log alongside their pass/fail result.


class _LogCapture(logging.Handler):
    def __init__(self):
        super().__init__(level=logging.INFO)
        self.records = []

    def emit(self, record):
        self.records.append(record.getMessage())

    def reset(self):
        self.records.clear()


_capture = _LogCapture()
_robot_logger = logging.getLogger("RobotFramework")
_robot_logger.setLevel(logging.INFO)
_robot_logger.addHandler(_capture)


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
# Tools
# =========================================================================

# (result key, CXLibraryVSX method name)
_VSX_CHECKS = [
    ("vsx_peers_in_sync", "vsx_peers_should_be_in_sync"),
    ("vsx_keepalive_established", "vsx_keepalive_should_be_established"),
    ("vsx_firmware_match", "vsx_firmware_should_match"),
]


@mcp.tool()
def list_devices() -> list[dict]:
    """List the switches defined in site.yaml.

    Returns each device's hostname and management IP only. Use the
    hostname or IP as the ``device`` argument to ``check_vsx``.
    """
    return [
        {"hostname": d.get("hostname"), "ip": d.get("ip")}
        for d in _devices()
    ]


@mcp.tool()
def check_vsx(device: str) -> dict:
    """Run the VSX health checks against one switch.

    Args:
        device: Hostname or management IP of a switch in site.yaml.

    Runs three checks, reused verbatim from the CXLibraryVSX Robot
    library:
      * vsx_peers_in_sync        ISL operational, peer established and
                                 ready, config sync in-sync
      * vsx_keepalive_established keepalive state is in_sync_established
      * vsx_firmware_match       both VSX peers run identical software

    Each check reports status (pass | fail | error), a message, and
    ``detail`` — the per-field values the check logged, useful for
    pinpointing which part of VSX is unhealthy.
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

    vsx = CXLibraryVSX()
    checks = []
    try:
        for name, method_name in _VSX_CHECKS:
            _capture.reset()
            try:
                getattr(vsx, method_name)(ip)
                status, message = "pass", "ok"
            except AssertionError as e:
                status, message = "fail", str(e)
            except Exception as e:
                status, message = "error", f"{type(e).__name__}: {e}"
            checks.append(
                {
                    "name": name,
                    "status": status,
                    "message": message,
                    "detail": list(_capture.records),
                }
            )
    finally:
        _aoscx.disconnect(ip)

    if any(c["status"] == "error" for c in checks):
        overall = "error"
    elif any(c["status"] == "fail" for c in checks):
        overall = "fail"
    else:
        overall = "pass"

    return {"device": hostname, "ip": ip, "overall": overall, "checks": checks}


if __name__ == "__main__":
    mcp.run()
