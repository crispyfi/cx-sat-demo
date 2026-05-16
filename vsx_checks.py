"""VSX troubleshooting checks.

Registers the ``check_vsx`` tool against the shared MCP server.
"""

# Imported first so libraries/ is on sys.path for the CXLibraryVSX import.
from mcp_core import mcp, run_checks

from CXLibraryVSX import CXLibraryVSX

# (result name, CXLibraryVSX method name)
_CHECKS = [
    ("vsx_peers_in_sync", "vsx_peers_should_be_in_sync"),
    ("vsx_keepalive_established", "vsx_keepalive_should_be_established"),
    ("vsx_firmware_match", "vsx_firmware_should_match"),
]


@mcp.tool()
def check_vsx(device: str) -> dict:
    """Run the VSX health checks against one switch.

    Args:
        device: Hostname or management IP of a switch in site.yaml.

    Runs three VSX checks:
      * vsx_peers_in_sync         ISL operational, peer established and
                                  ready, config sync in-sync
      * vsx_keepalive_established keepalive state is in_sync_established
      * vsx_firmware_match        both VSX peers run identical software

    Each check reports status (pass | fail | error), a message, and
    ``detail`` — the per-field values the check recorded, useful for
    pinpointing which part of VSX is unhealthy.
    """
    return run_checks(device, CXLibraryVSX, _CHECKS)
