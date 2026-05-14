"""
AOS-CX REST API helpers — connection management, cached fetches, endpoint
accessors, and interface/VLAN classification.

State (connections, response cache) lives at module scope. There is one
copy per Python process, shared by every domain library that imports from
this module. Domain libraries call the public functions here directly
rather than reaching into a base class via inheritance.

The leading underscore on the module name marks it as internal to this
project — it is not a Robot Framework library and should not be imported
in a `.robot` file.

Credentials (``CX_USERNAME``, ``CX_PASSWORD``) are read from environment
variables. On import this module calls ``dotenv.load_dotenv()`` which
loads a ``.env`` file from the working directory (or any ancestor) and
treats its ``KEY=VALUE`` lines as defaults — explicit environment
variables always win. The REST API version is per-site configuration
passed by the caller as a parameter to ``connect()``, not via the
environment.
"""

import json
import os
import re
import ssl
import urllib.parse

from http.cookiejar import CookieJar
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import (
    HTTPCookieProcessor,
    HTTPSHandler,
    Request,
    build_opener,
)

from dotenv import load_dotenv
from robot.api import logger


# =========================================================================
# Module-level state
# =========================================================================

_connections = {}  # device_ip -> {opener, base_url, ssl_ctx}
_cache = {}  # (device_ip, path) -> parsed JSON


# Load .env once at import. find-from-cwd walks up to the nearest file;
# override=False keeps existing env vars authoritative.
load_dotenv(override=False)


# =========================================================================
# Low-level HTTP / session
# =========================================================================


def _make_ssl_context():
    """SSL context that accepts self-signed AOS-CX certs."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def _login(base_url, username, password, ssl_ctx, timeout=10):
    """POST /login with form-encoded credentials and return an opener with cookies + CSRF."""
    cookie_jar = CookieJar()
    https_handler = HTTPSHandler(context=ssl_ctx)
    opener = build_opener(https_handler, HTTPCookieProcessor(cookie_jar))

    login_data = urlencode({"username": username, "password": password}).encode("utf-8")
    req = Request(base_url + "/login", data=login_data)
    req.add_header("Accept", "*/*")
    req.add_header("x-use-csrf-token", "true")

    try:
        resp = opener.open(req, timeout=timeout)
    except HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Login failed: HTTP {e.code} — {body}")
    except URLError as e:
        raise RuntimeError(f"Login failed: {e.reason}")

    if resp.getcode() != 200:
        raise RuntimeError(f"Login failed: HTTP {resp.getcode()}")

    opener.csrf_token = resp.headers.get("X-Csrf-Token")
    opener.cookie_jar = cookie_jar
    return opener


def _logout(opener, base_url, ssl_ctx, timeout=10):
    """POST /logout to end the session. Errors are ignored — session may already be invalid."""
    req = Request(base_url + "/logout", data=b"")
    req.add_header("Accept", "*/*")
    if opener.csrf_token:
        req.add_header("x-csrf-token", opener.csrf_token)
    try:
        opener.open(req, timeout=timeout)
    except Exception:
        pass


def _fetch(base_url, path, opener, ssl_ctx, timeout=30):
    """GET a REST API path. Returns (status_code, body_string) or (None, error)."""
    url = base_url + path
    req = Request(url)
    req.add_header("Accept", "application/json")
    if opener.csrf_token:
        req.add_header("x-csrf-token", opener.csrf_token)

    try:
        resp = opener.open(req, timeout=timeout)
        body = resp.read().decode("utf-8", errors="replace")
        code = resp.getcode()
    except HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        code = e.code
    except URLError as e:
        return None, str(e.reason)
    except Exception as e:
        return None, str(e)

    return code, body


def _fetch_json(base_url, path, opener, ssl_ctx, timeout=30):
    """GET a REST API path and return parsed JSON. Raises RuntimeError on failure."""
    code, body = _fetch(base_url, path, opener, ssl_ctx, timeout)
    if code is None:
        raise RuntimeError(f"Request failed for {path}: {body}")
    if code != 200:
        raise RuntimeError(f"HTTP {code} for {path}: {body[:200]}")
    try:
        return json.loads(body)
    except (ValueError, TypeError):
        return body


# =========================================================================
# Connection management
# =========================================================================


def connect(device_ip, api_version, port="443"):
    """Open an authenticated REST session to an AOS-CX switch.

    Reads ``CX_USERNAME`` and ``CX_PASSWORD`` from os.environ (raises
    RuntimeError if either is missing). The REST API version is passed
    by the caller — typically forwarded from the ``${API_VERSION}``
    Robot variable set by ``verify.py`` from ``site.yaml``. Builds the
    base URL ``https://<device_ip>:<port>/rest/<api_version>`` and
    stores the opener / base_url / SSL context in the module-level
    ``_connections`` dict keyed by device_ip.
    """
    username = os.environ.get("CX_USERNAME")
    password = os.environ.get("CX_PASSWORD")
    if not username or not password:
        raise RuntimeError("CX_USERNAME and CX_PASSWORD environment variables must be set")
    base_url = f"https://{device_ip}:{port}/rest/{api_version}"
    ssl_ctx = _make_ssl_context()
    opener = _login(base_url, username, password, ssl_ctx)
    _connections[device_ip] = {
        "opener": opener,
        "base_url": base_url,
        "ssl_ctx": ssl_ctx,
    }
    logger.info(f"Connected to {device_ip}")


def disconnect(device_ip=None):
    """Log out and release the REST session for one device, or all of them.

    When device_ip is None, every active connection is closed.
    """
    if device_ip is None:
        for ip in list(_connections.keys()):
            disconnect(ip)
        return
    conn = _connections.pop(device_ip, None)
    if conn:
        _logout(conn["opener"], conn["base_url"], conn["ssl_ctx"])
        logger.info(f"Disconnected from {device_ip}")


# =========================================================================
# REST fetches
# =========================================================================


def get(device_ip, path):
    """Fetch a REST API path and return parsed JSON (uncached)."""
    conn = _connections.get(device_ip)
    if conn is None:
        raise RuntimeError(f"No connection to {device_ip} -- call Connect To Device first")
    result = _fetch_json(conn["base_url"], path, conn["opener"], conn["ssl_ctx"])
    logger.debug(f"{device_ip}: GET {path}\n{json.dumps(result, indent=2, default=str)}")
    return result


def cached_get(device_ip, path):
    """Like ``get`` but memoises ``(device_ip, path)`` for the process lifetime.

    Use for configuration-style endpoints whose values are stable. Live
    state (counters, log entries, route ages) should use ``get`` instead.

    Cache key includes any querystring — callers must use the same path
    string (e.g. ``?depth=2``) to share the cache entry.
    """
    key = (device_ip, path)
    if key not in _cache:
        _cache[key] = get(device_ip, path)
    else:
        logger.debug(f"{device_ip}: cache hit {path}")
    return _cache[key]


# =========================================================================
# Endpoint accessors (cached, named for readability)
# =========================================================================


def system(device_ip):
    """Cached accessor for /system?depth=2."""
    return cached_get(device_ip, "/system?depth=2")


def vrf(device_ip, vrf_name="default"):
    """Cached accessor for /system/vrfs/<vrf_name>?depth=2."""
    return cached_get(device_ip, f"/system/vrfs/{vrf_name}?depth=2")


def interfaces(device_ip):
    """Cached accessor for /system/interfaces?depth=2 (all interfaces)."""
    return cached_get(device_ip, "/system/interfaces?depth=2")


def vlans(device_ip):
    """Cached accessor for /system/vlans?depth=2."""
    return cached_get(device_ip, "/system/vlans?depth=2")


def stp_instances(device_ip):
    """Cached accessor for /system/stp_instances?depth=2."""
    return cached_get(device_ip, "/system/stp_instances?depth=2")


def subsystems(device_ip):
    """Cached accessor for /system/subsystems?depth=2."""
    return cached_get(device_ip, "/system/subsystems?depth=2")


def lag_members(device_ip, lag_name):
    """Return the sorted list of member port names for a LAG, read from the device.

    AOS-CX exposes LAG members under the LAG's ``interfaces`` field. At
    depth=2 the field is a dict whose keys are either member port names
    (e.g. ``"1/1/51"``) or fully-qualified REST URLs (e.g.
    ``"/rest/v10.16/system/interfaces/1%2F1%2F51"``); this helper
    handles both forms.
    """
    lag_data = interfaces(device_ip).get(lag_name) or {}
    members_field = lag_data.get("interfaces") or {}
    names = []
    for key in members_field:
        # URL form ("/rest/.../interfaces/1%2F1%2F51"): take the last
        # path segment and percent-decode it. Bare-name form ("1/1/51"):
        # use the key as-is — splitting on "/" would mangle it down to
        # just "51".
        if key.startswith("/"):
            last = key.rstrip("/").split("/")[-1]
            names.append(urllib.parse.unquote(last))
        else:
            names.append(key)
    return sorted(names, key=interface_sort_key)


# =========================================================================
# Classification helpers
# =========================================================================


def is_physical(name):
    """True if *name* looks like a physical port (three slash-separated integers, e.g. 1/1/1)."""
    parts = name.split("/")
    if len(parts) == 3:
        try:
            int(parts[0])
            int(parts[1])
            int(parts[2])
            return True
        except ValueError:
            pass
    return False


def is_lag(name):
    """True if *name* is a LAG interface (starts with ``lag``)."""
    return name.startswith("lag")


def is_vlan_interface(name):
    """True if *name* is a VLAN SVI (starts with ``vlan``)."""
    return name.startswith("vlan")


def is_pluggable(data):
    """True if the interface has a pluggable transceiver (SFP/uplink)."""
    val = (data.get("hw_intf_info") or {}).get("pluggable", False)
    if isinstance(val, str):
        return val.lower() == "true"
    return bool(val)


# =========================================================================
# Sort keys
# =========================================================================


def interface_sort_key(name):
    """Numeric sort key for interface names (1/1/1, lag1, vlan10, etc.)."""
    return [int(n) for n in re.findall(r"\d+", name)]


def vlan_sort_key(vid):
    """Numeric sort key for VLAN IDs (int or string)."""
    try:
        return int(vid)
    except (ValueError, TypeError):
        return 0


def subsystem_sort_key(key):
    """Sort key for subsystem dict keys, ordering numerically by slot suffix.

    Subsystem keys have the form ``<type>,<slot>`` (e.g. ``chassis,1``,
    ``management_module,10``, ``fan_tray,2/1``). Lexicographic sort would
    mis-order multi-digit slots (1, 10, 2, …); this extracts the suffix
    as an integer so slots sort naturally (1, 2, …, 10).
    """
    prefix, _, suffix = key.rpartition(",")
    try:
        return (prefix, int(suffix))
    except ValueError:
        try:
            return (prefix, int(suffix.split("/")[0]))
        except ValueError:
            return (prefix, suffix)
