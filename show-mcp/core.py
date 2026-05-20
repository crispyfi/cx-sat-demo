"""Shared infrastructure for the show-mcp server.

Provides the FastMCP instance, site.yaml inventory helpers, and
self-contained REST session management for the AOS-CX CLI endpoints.
Modelled on the existing mcp_core.py / _aoscx.py but without the
Robot Framework dependency.

Credentials (CX_USERNAME / CX_PASSWORD) are read from the repo's .env file.
CX_SITE_FILE optionally overrides the path to site.yaml.
"""

import json
import os
import ssl
from http.cookiejar import CookieJar
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import (
    HTTPCookieProcessor,
    HTTPSHandler,
    Request,
    build_opener,
)

import yaml
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

_REPO_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_REPO_ROOT / ".env")

SITE_FILE = Path(os.environ.get("CX_SITE_FILE") or _REPO_ROOT / "site.yaml")
API_VERSION = "v10.16"

mcp = FastMCP("show-mcp")

# device_ip -> {opener, base_url}
_connections: dict = {}


# =========================================================================
# REST session helpers
# =========================================================================


def _ssl_context():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def _connect(ip: str, api_version: str = API_VERSION, port: str = "443") -> None:
    """Open an authenticated REST session to an AOS-CX switch."""
    username = os.environ.get("CX_USERNAME")
    password = os.environ.get("CX_PASSWORD")
    if not username or not password:
        raise RuntimeError("CX_USERNAME and CX_PASSWORD environment variables must be set")

    base_url = f"https://{ip}:{port}/rest/{api_version}"
    ssl_ctx = _ssl_context()
    opener = build_opener(HTTPSHandler(context=ssl_ctx), HTTPCookieProcessor(CookieJar()))

    login_data = urlencode({"username": username, "password": password}).encode()
    req = Request(base_url + "/login", data=login_data)
    req.add_header("Accept", "*/*")
    req.add_header("x-use-csrf-token", "true")

    try:
        resp = opener.open(req, timeout=10)
    except HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Login failed: HTTP {e.code} — {body}")
    except URLError as e:
        raise RuntimeError(f"Login failed: {e.reason}")

    opener.csrf_token = resp.headers.get("X-Csrf-Token")
    _connections[ip] = {"opener": opener, "base_url": base_url}


def _disconnect(ip: str) -> None:
    """Log out and release the REST session."""
    conn = _connections.pop(ip, None)
    if not conn:
        return
    req = Request(conn["base_url"] + "/logout", data=b"")
    req.add_header("Accept", "*/*")
    if conn["opener"].csrf_token:
        req.add_header("x-csrf-token", conn["opener"].csrf_token)
    try:
        conn["opener"].open(req, timeout=10)
    except Exception:
        pass


def _get_json(ip: str, path: str, timeout: int = 30):
    """GET a REST path and return parsed JSON."""
    conn = _connections[ip]
    req = Request(conn["base_url"] + path)
    req.add_header("Accept", "application/json")
    if conn["opener"].csrf_token:
        req.add_header("x-csrf-token", conn["opener"].csrf_token)
    try:
        resp = conn["opener"].open(req, timeout=timeout)
        return json.loads(resp.read().decode("utf-8", errors="replace"))
    except HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code} for {path}: {body[:200]}")
    except URLError as e:
        raise RuntimeError(f"Request failed for {path}: {e.reason}")


def _post_text(ip: str, path: str, body: dict, timeout: int = 60) -> str:
    """POST a JSON body and return the plain-text response."""
    conn = _connections[ip]
    data = json.dumps(body).encode("utf-8")
    req = Request(conn["base_url"] + path, data=data)
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "text/plain")
    if conn["opener"].csrf_token:
        req.add_header("x-csrf-token", conn["opener"].csrf_token)
    try:
        resp = conn["opener"].open(req, timeout=timeout)
        return resp.read().decode("utf-8", errors="replace")
    except HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code} for {path}: {body[:200]}")
    except URLError as e:
        raise RuntimeError(f"Request failed for {path}: {e.reason}")


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
