"""CLI show-command tools for the show-mcp MCP server."""

import re

from core import (
    API_VERSION,
    _connect,
    _devices,
    _disconnect,
    _get_json,
    _post_text,
    _resolve,
    mcp,
)


@mcp.tool()
def list_devices() -> list[dict]:
    """List the switches defined in site.yaml.

    Returns each device's hostname and management IP (and persona if set).
    Use the hostname or IP as the ``device`` argument to the other tools.
    """
    result = []
    for d in _devices():
        entry: dict = {"hostname": d.get("hostname"), "ip": d.get("ip")}
        if d.get("persona"):
            entry["persona"] = d["persona"]
        result.append(entry)
    return result


@mcp.tool()
def list_cli_commands(device: str) -> dict:
    """List all CLI commands available via the REST interface on a device.

    Call this before ``run_show_command`` to discover which show commands
    are permitted on the target switch. The set of available commands varies
    by firmware version and device role.

    Args:
        device: Hostname or management IP of a switch in site.yaml.

    Returns a dict with a ``commands`` list of permitted command strings,
    or an ``error`` key if the device cannot be reached.
    """
    dev = _resolve(device)
    if dev is None:
        known = ", ".join(str(d.get("hostname") or d.get("ip")) for d in _devices())
        return {"error": f"device {device!r} not found in site.yaml (known: {known})"}

    ip = dev["ip"]
    hostname = dev.get("hostname")
    try:
        _connect(ip, API_VERSION)
        commands = _get_json(ip, "/cli/commands")
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}
    finally:
        _disconnect(ip)

    return {"device": hostname, "ip": ip, "commands": commands}


@mcp.tool()
def run_show_command(device: str, command: str, filter: str | None = None) -> dict:
    """Execute a show command on a switch via the REST CLI interface.

    Use ``list_cli_commands`` first to discover which commands are available
    on the target device. Only ``show`` commands are accepted; any other
    input is rejected to prevent accidental configuration changes.

    Prefer scoped commands where available to reduce output size — for example,
    ``show interface lag`` rather than ``show interface brief`` when only LAG
    state is needed. Only use ``show interface brief`` when a full port
    inventory is required.

    For wide commands that may produce verbose output, pass a ``filter``
    regex to return only matching lines (e.g. ``filter="up|blocked"`` on
    ``show interface brief`` to skip ports that are administratively down or
    have no transceiver installed).

    Args:
        device: Hostname or management IP of a switch in site.yaml.
        command: A show command string, e.g. ``show version`` or
                 ``show vsx status``.
        filter: Optional regex pattern. When provided, only lines matching
                the pattern (case-insensitive) are returned. Header/separator
                lines are always kept so the output remains readable.

    Returns a dict with the plain-text ``output`` from the switch,
    or an ``error`` key if the command or connection fails.
    """
    if not command.strip().lower().startswith("show"):
        return {"error": f"only show commands are permitted (got: {command!r})"}

    dev = _resolve(device)
    if dev is None:
        known = ", ".join(str(d.get("hostname") or d.get("ip")) for d in _devices())
        return {"error": f"device {device!r} not found in site.yaml (known: {known})"}

    ip = dev["ip"]
    hostname = dev.get("hostname")
    try:
        _connect(ip, API_VERSION)
        output = _post_text(ip, "/cli", {"cmd": command})
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}
    finally:
        _disconnect(ip)

    if filter:
        try:
            pattern = re.compile(filter, re.IGNORECASE)
            # Keep header/separator lines (dashes, equals, empty) plus matching lines
            filtered = [
                line for line in output.splitlines()
                if re.match(r"^[-= ]*$", line) or pattern.search(line)
            ]
            output = "\n".join(filtered)
        except re.error as e:
            return {"error": f"invalid filter regex {filter!r}: {e}"}

    return {"device": hostname, "ip": ip, "command": command, "output": output}
