"""Running-config read tool for the AOS-CX MCP server."""

import re

from mcp_core import mcp, _resolve, _devices, API_VERSION
import _aoscx

# Key names whose values should always be redacted.
_SENSITIVE_KEY_TERMS = {"password", "passwd", "secret", "passphrase", "psk", "credential"}

# Long base64 strings are almost certainly ciphertext/hashes regardless of key name.
_CIPHERTEXT_RE = re.compile(r"^[A-Za-z0-9+/]{40,}={0,2}$")


@mcp.tool()
def get_running_config(device: str, element: str = "") -> dict:
    """Fetch the running configuration for a switch, optionally filtered by element.

    Args:
        device:  Hostname or management IP of a switch in site.yaml.
        element: Optional keyword to filter the config (e.g. 'vsx', 'ospf',
                 'stp', 'vlan', 'acl'). When provided, only subtrees whose
                 key name contains this term (case-insensitive) are returned,
                 significantly reducing token usage. Omit to get the full
                 config (warning: large).

    The filtered result is a flat dict keyed by dotted path
    (e.g. ``System.vsx``, ``VRF.default.ospf_routers``) mapping to the
    full subtree at that key.
    """
    dev = _resolve(device)
    if dev is None:
        known = ", ".join(str(d.get("hostname") or d.get("ip")) for d in _devices())
        return {"error": f"device {device!r} not found in site.yaml (known: {known})"}

    ip = dev.get("ip")
    hostname = dev.get("hostname")

    _aoscx.clear_cache(ip)

    try:
        _aoscx.connect(ip, API_VERSION)
    except Exception as e:
        return {"device": hostname, "ip": ip, "error": f"connection failed: {e}"}

    try:
        data = _aoscx.get(ip, "/configs/running-config")
    except Exception as e:
        return {"device": hostname, "ip": ip, "error": f"fetch failed: {e}"}
    finally:
        _aoscx.disconnect(ip)

    data = _redact(data)

    if not element:
        return {"device": hostname, "ip": ip, "config": data}

    matches = {}
    _collect_matches(data, element.lower(), path="", out=matches)

    return {
        "device": hostname,
        "ip": ip,
        "element": element,
        "config": matches or {"note": f"no config keys matching '{element}' found"},
    }


def _redact(obj):
    """Return a copy of obj with sensitive values replaced by '<redacted>'."""
    if isinstance(obj, dict):
        result = {}
        for k, v in obj.items():
            if any(term in k.lower() for term in _SENSITIVE_KEY_TERMS):
                result[k] = "<redacted>"
            elif isinstance(v, str) and _CIPHERTEXT_RE.match(v):
                result[k] = "<redacted>"
            else:
                result[k] = _redact(v)
        return result
    if isinstance(obj, list):
        return [_redact(v) for v in obj]
    return obj


def _collect_matches(obj, term, path, out):
    """Recursively collect subtrees whose key name contains term."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            cur = f"{path}.{k}" if path else k
            if term in k.lower():
                out[cur] = v
            else:
                _collect_matches(v, term, cur, out)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            _collect_matches(v, term, f"{path}[{i}]", out)
