#!/usr/bin/env python3
"""Entrypoint for the aoscx-ssh-mcp server.

Exposes three tools for SSH-based inspection of AOS-CX switches:
  list_devices      — discover switches from site.yaml
  run_show_command  — execute a show command over SSH with optional | include filter
  get_completions   — send <partial> ? to discover available sub-commands
"""

from core import mcp

import ssh_tools  # noqa: F401  (imported for its @mcp.tool registrations)


if __name__ == "__main__":
    mcp.run()
