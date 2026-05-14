"""Robot Framework library: Multicast keywords."""

from robot.api import logger

import _aoscx


class CXLibraryMulticast:
    ROBOT_LIBRARY_SCOPE = "SUITE"

    def igmp_snooping_should_be_on_every_vlan(self, device_ip, version):
        """Verify IGMP snooping is enabled and operating on every VLAN on the device.

        Args:
            device_ip: Switch management IP.
            version: Expected IGMP snooping version (${IGMP_VERSION}) — typically 2 or 3.

        Reads every VLAN from the device and asserts each has:
          * mgmd_enable.igmp truthy                   → IGMP snooping configured
          * mgmd_enable_status.igmp truthy            → IGMP snooping operationally up
          * mgmd_oper_version.igmp == int(version)    → expected version
        All failures across all VLANs are reported together. Intended
        for L2 switches (access) where every carried VLAN must have
        IGMP snooping enabled — no design input is required.
        """
        live_vlans = _aoscx.vlans(device_ip)
        if not live_vlans:
            raise AssertionError(f"{device_ip}: no VLANs on device")
        version = int(version)
        bad_vlans = []
        sorted_vids = sorted(live_vlans.keys(), key=_aoscx.vlan_sort_key)
        for vid in sorted_vids:
            vdata = live_vlans.get(vid) or {}
            mgmd_en = (vdata.get("mgmd_enable") or {}).get("igmp", False)
            en_status = (vdata.get("mgmd_enable_status") or {}).get("igmp", False)
            oper_ver = (vdata.get("mgmd_oper_version") or {}).get("igmp")
            vlan_failures = []
            if not mgmd_en:
                vlan_failures.append("igmp not enabled")
            if not en_status:
                vlan_failures.append("igmp not operationally enabled")
            if oper_ver != version:
                vlan_failures.append(f"oper_version={oper_ver} (expected {version})")
            if vlan_failures:
                logger.warn(
                    f"{device_ip}: VLAN {vid} igmp_enable={mgmd_en} enable_status={en_status} oper_version={oper_ver} — {'; '.join(vlan_failures)}"
                )
                bad_vlans.append(str(vid))
            else:
                logger.info(
                    f"{device_ip}: VLAN {vid} ok (igmp_enable={mgmd_en} enable_status={en_status} oper_version={oper_ver})"
                )
        if bad_vlans:
            raise AssertionError(
                f"{device_ip}: {len(bad_vlans)} of {len(sorted_vids)} VLANs with IGMP snooping issues"
            )
