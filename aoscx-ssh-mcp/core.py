"""Shared infrastructure for the aoscx-ssh-mcp server.

Provides the FastMCP instance, site.yaml inventory helpers, and SSH session
management for AOS-CX switches via netmiko.

Credentials (CX_USERNAME / CX_PASSWORD) are read from the repo's .env file.
CX_SITE_FILE optionally overrides the path to site.yaml.
"""

import os
from pathlib import Path

import yaml
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from netmiko import ConnectHandler

_REPO_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_REPO_ROOT / ".env")

SITE_FILE = Path(os.environ.get("CX_SITE_FILE") or _REPO_ROOT / "site.yaml")

mcp = FastMCP("aoscx-ssh-mcp")

# device_ip -> netmiko BaseConnection
_connections: dict = {}


# =========================================================================
# SSH session helpers
# =========================================================================


def _connect(ip: str):
    """Open an SSH session to an AOS-CX switch via netmiko."""
    username = os.environ.get("CX_USERNAME")
    password = os.environ.get("CX_PASSWORD")
    if not username or not password:
        raise RuntimeError("CX_USERNAME and CX_PASSWORD environment variables must be set")

    conn = ConnectHandler(
        device_type="aruba_aoscx",
        host=ip,
        username=username,
        password=password,
    )
    _connections[ip] = conn
    return conn


def _disconnect(ip: str) -> None:
    """Close and remove the SSH session for a device."""
    conn = _connections.pop(ip, None)
    if conn:
        try:
            conn.disconnect()
        except Exception:
            pass


# =========================================================================
# site.yaml inventory
# =========================================================================


def _devices() -> list[dict]:
    """Device list from site.yaml (empty list if file is missing/empty)."""
    if not SITE_FILE.is_file():
        return []
    data = yaml.safe_load(SITE_FILE.read_text()) or {}
    return data.get("devices") or []


def _resolve(device: str) -> dict | None:
    """Find a device by exact hostname/IP, then by case-insensitive hostname."""
    devices = _devices()
    for d in devices:
        if d.get("hostname") == device or d.get("ip") == device:
            return d
    for d in devices:
        if str(d.get("hostname", "")).lower() == device.lower():
            return d
    return None
