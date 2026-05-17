"""VSX troubleshooting checks.

Registers the ``check_vsx`` tool against the shared MCP server.
"""

# Imported first so libraries/ is on sys.path for the CXLibraryVSX import.
from mcp_core import mcp, run_checks, API_VERSION

import _aoscx

from CXLibraryVSX import CXLibraryVSX

# (result name, CXLibraryVSX method name)
_CHECKS = [
    ("vsx_peers_in_sync", "vsx_peers_should_be_in_sync"),
    ("vsx_keepalive_established", "vsx_keepalive_should_be_established"),
    ("vsx_firmware_match", "vsx_firmware_should_match"),
]


def _ref_name(ref):
    """Extract a resource name from an AOS-CX reference field.

    A reference may arrive as a bare URI string, a ``{name: uri}`` dict,
    or an expanded object carrying its own ``name``. Returns the decoded
    name, or None if it cannot be determined.
    """
    if not ref:
        return None
    if isinstance(ref, str):
        return ref.rstrip("/").split("/")[-1].replace("%2F", "/")
    if isinstance(ref, dict):
        name = ref.get("name")
        if isinstance(name, str):
            return name
        for key in ref:
            return key.rstrip("/").split("/")[-1].replace("%2F", "/")
    return None


def _vsx_related(ip):
    """Cross-reference /system/vsx to the config a VSX problem depends on.

    Returns ``(related, next_steps)`` — the keepalive VRF, the keepalive
    source interface (located by matching ``keepalive_src_ip`` against
    interface addresses), and the ISL LAG with its members, plus the
    get_running_config calls worth making to inspect that config.
    """
    vsx = _aoscx.cached_get(ip, "/system/vsx?depth=2")

    ka_vrf = _ref_name(vsx.get("keepalive_vrf"))
    isl_lag = _ref_name(vsx.get("isl_port"))
    src_ip = vsx.get("keepalive_src_ip")
    peer_ip = vsx.get("keepalive_peer")

    ka_interface = None
    if src_ip:
        for name, data in _aoscx.interfaces(ip).items():
            ip4 = data.get("ip4_address")
            if isinstance(ip4, str) and ip4.split("/")[0] == src_ip:
                ka_interface = name
                break

    isl_members = _aoscx.lag_members(ip, isl_lag) if isl_lag else []

    related = {
        "keepalive_vrf": ka_vrf,
        "keepalive_src_ip": src_ip,
        "keepalive_peer_ip": peer_ip,
        "keepalive_interface": ka_interface,
        "isl_lag": isl_lag,
        "isl_members": isl_members,
    }
    next_steps = [
        "get_running_config(device, element='vsx') — the full VSX config block",
        "get_running_config(device, element='interface') — inspect the keepalive "
        f"interface ({ka_interface}) and ISL members "
        f"({', '.join(isl_members) or 'none'})",
    ]
    if ka_vrf:
        next_steps.append(
            f"get_running_config(device, element='vrf') — inspect the keepalive "
            f"VRF ({ka_vrf})"
        )
    return related, next_steps


@mcp.tool()
def check_vsx(device: str) -> dict:
    """Run the VSX health checks against one switch, with related-config pointers.

    Args:
        device: Hostname or management IP of a switch in site.yaml.

    Runs three VSX checks:
      * vsx_peers_in_sync         ISL operational, peer established and
                                  ready, config sync in-sync
      * vsx_keepalive_established keepalive state is in_sync_established
      * vsx_firmware_match        both VSX peers run identical software

    Each check reports status (pass | fail | error), a message, and
    ``detail`` — the per-field values it recorded.

    The result also carries a ``related`` block naming the config a VSX
    problem usually depends on — the keepalive VRF, the keepalive source
    interface, and the ISL LAG and its members — and a ``next_steps``
    list. When a check fails or errors, do not stop at the VSX block:
    follow the ``next_steps`` in order before concluding what is wrong.
    If the ISL check fails, ``next_steps`` will begin with a
    ``check_lacp`` call to inspect LACP member state on the ISL LAG —
    run that first, before any get_running_config calls.
    """
    report = run_checks(device, CXLibraryVSX, _CHECKS)
    ip = report.get("ip")
    if ip and "error" not in report:
        try:
            _aoscx.connect(ip, API_VERSION)
            report["related"], report["next_steps"] = _vsx_related(ip)
        except Exception as exc:
            report["related_error"] = f"could not gather related config: {exc}"
        finally:
            _aoscx.disconnect(ip)

    isl_failed = any(
        c["name"] == "vsx_peers_in_sync" and c["status"] != "pass"
        for c in report.get("checks", [])
    )
    if isl_failed and "next_steps" in report:
        isl_lag = report.get("related", {}).get("isl_lag", "the ISL LAG")
        report["next_steps"].insert(
            0,
            f"check_lacp(device) — inspect LACP member state for {isl_lag} before checking config",
        )

    return report
