"""SSH show-command tools for the aoscx-ssh-mcp MCP server."""

import re

from core import (
    _connect,
    _devices,
    _disconnect,
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
def run_show_command(device: str, command: str, include_filter: str | None = None) -> dict:
    """Execute a show command on an AOS-CX switch over SSH.

    Only ``show`` commands are accepted; any other input is rejected to
    prevent accidental configuration changes.

    ## Choosing a command

    Prefer scoped commands to reduce output — e.g. ``show vsx status``
    rather than ``show vsx``.  Use ``get_completions`` if you are unsure
    what sub-commands are available.

    ## Filtering output on the switch

    Use ``include_filter`` whenever possible.  The filter string is passed
    directly to the AOS-CX CLI as ``| include <filter>``, which runs on the
    switch itself and is faster and more token-efficient than post-processing.

    Examples:
      - ``include_filter="up"``        → only lines containing "up"
      - ``include_filter="lag|port"``  → lines matching either word

    AOS-CX also supports these filters — append them manually to ``command``
    when needed:
      - ``| exclude <regex>``  drop matching lines
      - ``| begin <regex>``    start output from the first matching line

    ## Tab completion on AOS-CX

    AOS-CX supports ``?`` at any point in a command to list available
    options.  Use the ``get_completions`` tool (which sends ``<partial> ?``
    over SSH) instead of guessing command names.

    Args:
        device: Hostname or management IP of a switch in site.yaml.
        command: A show command string, e.g. ``show vsx status`` or
                 ``show interface lag256``.
        include_filter: Optional filter string passed to the switch as
                        ``| include <include_filter>``.

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

    full_command = command
    if include_filter:
        full_command = f"{command} | include {include_filter}"

    try:
        conn = _connect(ip)
        output = conn.send_command(full_command)
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}
    finally:
        _disconnect(ip)

    return {"device": hostname, "ip": ip, "command": full_command, "output": output}


@mcp.tool()
def get_completions(device: str, partial_command: str) -> dict:
    """Show AOS-CX tab completions for a partial show command.

    Sends ``<partial_command> ?`` to the switch over SSH and returns the
    list of available sub-commands with their descriptions.  Use this
    instead of guessing command names.

    Only partial ``show`` commands are accepted.

    ## How AOS-CX tab completion works

    Appending ``?`` after any word shows what can follow.  For example:
      - ``show ?``       lists all top-level show sub-commands
      - ``show vsx ?``   lists all ``show vsx *`` options
      - ``show ip ?``    lists IP-related show commands

    The switch returns each option with a short description, which helps
    you choose the most relevant command before running it.

    Args:
        device: Hostname or management IP of a switch in site.yaml.
        partial_command: The beginning of a show command, e.g. ``show vsx``
                         or ``show interface``.

    Returns a dict with the raw ``completions`` text from the switch,
    or an ``error`` key if the connection fails.
    """
    if not partial_command.strip().lower().startswith("show"):
        return {"error": f"only show commands are permitted (got: {partial_command!r})"}

    dev = _resolve(device)
    if dev is None:
        known = ", ".join(str(d.get("hostname") or d.get("ip")) for d in _devices())
        return {"error": f"device {device!r} not found in site.yaml (known: {known})"}

    ip = dev["ip"]
    hostname = dev.get("hostname")

    try:
        conn = _connect(ip)
        # send_command_timing reads until output stops arriving — needed because
        # '?' doesn't end with a normal prompt
        raw = conn.send_command_timing(f"{partial_command.rstrip()} ?")
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}
    finally:
        _disconnect(ip)

    # Strip ANSI escape sequences and carriage returns
    clean = re.sub(r"\x1b\[[0-9;]*[A-Za-z]|\r", "", raw)

    return {
        "device": hostname,
        "ip": ip,
        "partial_command": partial_command,
        "completions": clean,
    }
