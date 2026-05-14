"""Robot Framework library: LACP keywords."""

from robot.api import logger

import _aoscx


class CXLibraryLACP:
    ROBOT_LIBRARY_SCOPE = "SUITE"

    def all_lag_members_should_be_active(self, device_ip):
        """Verify every member of every LAG is collecting and distributing.

        Args:
            device_ip: Switch management IP.

        Walks every LAG present on the device (entries whose interface
        name starts with ``lag``). For each LAG, enumerates its member
        ports via ``_aoscx.lag_members``, then fetches each member's own
        interface endpoint (``/system/interfaces/<member>?depth=2``) and
        reads its ``lacp_status``. ``lacp_status`` is per-member and is
        not returned on the LAG-level interface entry, so each member
        must be queried individually. Asserts, on every member, that:
          * actor_state is non-empty (LACP is established)
          * actor_state contains both "Col:1" and "Dist:1"
          * partner_state contains both "Col:1" and "Dist:1"
        All failures across all LAGs and members are collected and
        raised together. Fails if no LAGs are present.
        """
        device_ifaces = _aoscx.interfaces(device_ip)
        lag_names = sorted(
            (name for name in device_ifaces if _aoscx.is_lag(name)),
            key=_aoscx.interface_sort_key,
        )
        if not lag_names:
            raise AssertionError(f"{device_ip}: no LAGs found on device")
        problems = []
        for lag_name in lag_names:
            members = _aoscx.lag_members(device_ip, lag_name)
            if not members:
                logger.warn(f"{device_ip}: {lag_name} has no members")
                problems.append(f"{lag_name}: no members")
                continue
            for port_name in members:
                encoded = port_name.replace("/", "%2F")
                port_data = _aoscx.cached_get(
                    device_ip,
                    f"/system/interfaces/{encoded}?depth=2",
                )
                lacp_st = port_data.get("lacp_status") or {}
                actor = lacp_st.get("actor_state", "")
                partner = lacp_st.get("partner_state", "")
                port_problems = []
                if not actor:
                    port_problems.append("no LACP state (not established)")
                elif "Col:1" not in actor or "Dist:1" not in actor:
                    port_problems.append(f"actor_state={actor!r} (Col or Dist not active)")
                elif "Col:1" not in partner or "Dist:1" not in partner:
                    port_problems.append(f"partner_state={partner!r} (Col or Dist not active)")
                if port_problems:
                    logger.warn(
                        f"{device_ip}: {lag_name} member {port_name} actor_state={actor!r} partner_state={partner!r} — {'; '.join(port_problems)}"
                    )
                    problems.extend(f"{lag_name}/{port_name}: {p}" for p in port_problems)
                else:
                    logger.info(
                        f"{device_ip}: {lag_name} member {port_name} ok (actor_state={actor!r} partner_state={partner!r})"
                    )
        if problems:
            raise AssertionError(f"{device_ip}: {len(problems)} LAG member(s) with LACP issues")
