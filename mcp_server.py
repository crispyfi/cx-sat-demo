#!/usr/bin/env python3
"""Entrypoint for the AOS-CX troubleshooting MCP server.

Wires the shared server (``mcp_core``) together with the per-domain
check modules and starts the stdio transport. To add a new
troubleshooting domain, create its check module and import it here.
"""

from mcp_core import mcp

import vsx_checks     # noqa: F401  (imported for its @mcp.tool registration)
import config_checks  # noqa: F401


if __name__ == "__main__":
    mcp.run()
