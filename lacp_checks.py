"""LACP troubleshooting checks.

Registers the ``check_lacp`` tool against the shared MCP server.
"""

# Imported first so libraries/ is on sys.path for the CXLibraryLACP import.
from mcp_core import mcp, run_checks

from CXLibraryLACP import CXLibraryLACP

# (result name, CXLibraryLACP method name)
_CHECKS = [
    ("lacp_lag_members_active", "all_lag_members_should_be_active"),
]


@mcp.tool()
def check_lacp(device: str) -> dict:
    """Run the LACP health checks against one switch.

    Args:
        device: Hostname or management IP of a switch in site.yaml.

    Runs one LACP check:
      * lacp_lag_members_active   every member port of every LAG is
                                  collecting and distributing (actor and
                                  partner state both show Col:1 / Dist:1)

    The check reports status (pass | fail | error), a message, and
    ``detail`` — the per-member actor/partner state it recorded, useful
    for pinpointing which LAG member is not bundling.
    """
    return run_checks(device, CXLibraryLACP, _CHECKS)
