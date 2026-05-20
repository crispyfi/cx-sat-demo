#!/usr/bin/env python3
"""Entrypoint for the show-mcp server.

Exposes three tools for ad-hoc CLI inspection of AOS-CX switches:
  list_devices       — discover switches from site.yaml
  list_cli_commands  — list available show commands on a device
  run_show_command   — execute a show command and return its output
"""

from core import mcp

import cli_tools  # noqa: F401  (imported for its @mcp.tool registrations)


if __name__ == "__main__":
    mcp.run()
