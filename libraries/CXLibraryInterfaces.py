"""Robot Framework library: Interface keywords."""

from robot.api import logger

import _aoscx


class CXLibraryInterfaces:
    ROBOT_LIBRARY_SCOPE = "SUITE"

    def all_physical_interfaces_mtu_should_be(self, device_ip, expected_mtu):
        """Verify every admin-up physical interface has the expected MTU.

        Args:
            device_ip: Switch management IP.
            expected_mtu: Expected interface MTU in bytes
                (${PHYSICAL_MTU}). Accepts ints or numeric strings.

        Iterates _aoscx.interfaces, filters to physical ports
        (_aoscx.is_physical), skips admin_down ports (operators may
        intentionally shut unused ports with non-default MTU), reads mtu,
        and collects any port whose mtu is set and not equal to
        expected_mtu. Ports without an mtu value are skipped. All
        mismatches are reported in a single failure.
        """
        expected_mtu = int(expected_mtu)
        interfaces = _aoscx.interfaces(device_ip)
        mismatches = []
        for name, data in sorted(interfaces.items(), key=lambda x: _aoscx.interface_sort_key(x[0])):
            if not _aoscx.is_physical(name):
                continue
            if data.get("admin_state") != "up":
                logger.info(f"{device_ip}: {name} admin_down (skipping)")
                continue
            mtu = data.get("mtu")
            if mtu is None:
                logger.info(f"{device_ip}: {name} mtu=None (skipping)")
                continue
            if int(mtu) != expected_mtu:
                logger.warn(f"{device_ip}: {name} mtu={mtu} (expected {expected_mtu})")
                mismatches.append(f"{name}: mtu={mtu} (expected {expected_mtu})")
            else:
                logger.info(f"{device_ip}: {name} ok (mtu={mtu})")
        if mismatches:
            raise AssertionError(
                f"{device_ip}: {len(mismatches)} physical interface(s) with unexpected MTU (expected {expected_mtu})"
            )

    def physical_uplinks_mtu_should_be(self, device_ip, expected_mtu, uplink_lag):
        """Verify every member port of the named uplink LAG has the expected MTU.

        Args:
            device_ip: Switch management IP.
            expected_mtu: Expected interface MTU in bytes
                (${PHYSICAL_MTU}). Accepts ints or numeric strings.
            uplink_lag: Name of the uplink LAG (${UPLINK_LAG}, e.g.
                ``lag1``). Member ports are enumerated from the LAG on
                the device via ``_aoscx.lag_members``. Fails if the LAG
                is absent or has no members.

        For each member port, reads mtu and collects any port whose mtu
        is set and not equal to expected_mtu. All mismatches are
        reported in a single failure.
        """
        if not uplink_lag:
            raise AssertionError(f"{device_ip}: uplink_lag not provided")
        members = _aoscx.lag_members(device_ip, uplink_lag)
        if not members:
            raise AssertionError(f"{device_ip}: uplink LAG {uplink_lag!r} has no members on device")
        interfaces = _aoscx.interfaces(device_ip)
        expected_mtu = int(expected_mtu)
        mismatches = []
        for name in members:
            data = interfaces.get(name, {})
            mtu = data.get("mtu")
            if mtu is None:
                logger.info(f"{device_ip}: {name} mtu=None (skipping)")
                continue
            if int(mtu) != expected_mtu:
                logger.warn(f"{device_ip}: {name} mtu={mtu} (expected {expected_mtu})")
                mismatches.append(f"{name}: mtu={mtu} (expected {expected_mtu})")
            else:
                logger.info(f"{device_ip}: {name} ok (mtu={mtu})")
        if mismatches:
            raise AssertionError(
                f"{device_ip}: {len(mismatches)} uplink interface(s) with unexpected MTU (expected {expected_mtu})"
            )

    def all_vlan_interfaces_mtu_should_be(self, device_ip, expected_mtu):
        """Verify every VLAN SVI (except vlan1) has the expected IP MTU.

        Args:
            device_ip: Switch management IP.
            expected_mtu: Expected IP MTU in bytes (${VLAN_IP_MTU}).
                Accepts ints or numeric strings.

        Iterates _aoscx.interfaces, filters to VLAN SVIs via
        _aoscx.is_vlan_interface, skips vlan1 (which is shut down by the
        hardening suite), reads active_ip_mtu.value, and collects any
        SVI whose IP MTU is set and not equal to expected_mtu. All
        mismatches are reported in a single failure.
        """
        expected_mtu = int(expected_mtu)
        interfaces = _aoscx.interfaces(device_ip)
        mismatches = []
        for name, data in sorted(interfaces.items(), key=lambda x: _aoscx.interface_sort_key(x[0])):
            if not _aoscx.is_vlan_interface(name):
                continue
            if name == "vlan1":
                logger.info(f"{device_ip}: vlan1 excluded (skipping)")
                continue
            active_ip_mtu = data.get("active_ip_mtu") or {}
            ip_mtu = active_ip_mtu.get("value")
            if ip_mtu is None:
                logger.warn(f"{device_ip}: {name} active_ip_mtu not present")
                mismatches.append(f"{name}: active_ip_mtu not present")
                continue
            if int(ip_mtu) != expected_mtu:
                logger.warn(f"{device_ip}: {name} active_ip_mtu={ip_mtu} (expected {expected_mtu})")
                mismatches.append(f"{name}: active_ip_mtu={ip_mtu} (expected {expected_mtu})")
            else:
                logger.info(f"{device_ip}: {name} ok (active_ip_mtu={ip_mtu})")
        if mismatches:
            raise AssertionError(
                f"{device_ip}: {len(mismatches)} VLAN SVI(s) with unexpected IP MTU (expected {expected_mtu})"
            )

    def svis_should_be_admin_up(self, device_ip):
        """Verify every VLAN SVI (except vlan1) is administratively up.

        Args:
            device_ip: Switch management IP.

        Iterates _aoscx.interfaces, filters to VLAN SVIs via
        _aoscx.is_vlan_interface, skips vlan1, and collects any SVI whose
        admin_state is not "up". All offending SVIs are reported in a
        single failure.
        """
        interfaces = _aoscx.interfaces(device_ip)
        failures = []
        for name, data in sorted(interfaces.items(), key=lambda x: _aoscx.interface_sort_key(x[0])):
            if not _aoscx.is_vlan_interface(name):
                continue
            if name == "vlan1":
                logger.info(f"{device_ip}: vlan1 excluded (skipping)")
                continue
            admin_state = data.get("admin_state")
            if admin_state != "up":
                logger.warn(f"{device_ip}: {name} admin_state={admin_state!r} (expected 'up')")
                failures.append(name)
            else:
                logger.info(f"{device_ip}: {name} ok (admin_state={admin_state!r})")
        if failures:
            raise AssertionError(f"{device_ip}: {len(failures)} SVI(s) not administratively up")

    def enabled_interfaces_should_be_up(self, device_ip):
        """Verify every administratively enabled physical interface has link up.

        Args:
            device_ip: Switch management IP.

        Iterates _aoscx.interfaces, filters to physical ports whose
        admin_state is "up", reads link_state, and collects any port
        whose link is not "up". All offending ports are reported in a
        single failure.
        """
        interfaces = _aoscx.interfaces(device_ip)
        down = []
        for name, data in sorted(interfaces.items(), key=lambda x: _aoscx.interface_sort_key(x[0])):
            if not _aoscx.is_physical(name):
                continue
            if data.get("admin_state") != "up":
                logger.info(f"{device_ip}: {name} admin_down (skipping)")
                continue
            link = data.get("link_state", "unknown")
            if link != "up":
                logger.warn(f"{device_ip}: {name} link_state={link!r} (expected 'up')")
                down.append(f"{name}: link_state={link!r}")
            else:
                logger.info(f"{device_ip}: {name} ok (link_state=up)")
        if down:
            raise AssertionError(f"{device_ip}: {len(down)} admin-up interface(s) with link down")

    def all_interfaces_should_be_correct_speed_and_duplex(self, device_ip):
        """Verify every up physical interface is at the correct speed and duplex.

        Args:
            device_ip: Switch management IP.

        Iterates _aoscx.interfaces, filters to physical interfaces with
        link_state "up", and applies one of two rules:

        Pluggable port (hw_intf_info.pluggable true):
          * link_speed must equal pm_info.supported_speeds (the
            transceiver's rated speed)
          * duplex must be "full"

        Non-pluggable port (fixed copper):
          * link_speed must be in hw_intf_info.speeds (the
            comma-separated list of supported speeds) and duplex must
            be "full".

        All failures are collected and raised together.
        """
        interfaces = _aoscx.interfaces(device_ip)
        failures = []

        for name, data in sorted(interfaces.items(), key=lambda x: _aoscx.interface_sort_key(x[0])):
            if not _aoscx.is_physical(name):
                continue
            if data.get("link_state") != "up":
                continue

            speed_bps = data.get("link_speed")
            # link_speed is in bps; supported_speeds and hw speeds are in Mbps
            speed_mbps = speed_bps // 1_000_000 if speed_bps is not None else None
            duplex = data.get("duplex", "")
            hw = data.get("hw_intf_info") or {}
            pluggable = hw.get("pluggable", False)
            intf_failures = []

            if pluggable:
                pm = data.get("pm_info") or {}
                expected_speed = pm.get("supported_speeds")
                if expected_speed is not None and speed_mbps != int(expected_speed):
                    intf_failures.append(f"speed={speed_mbps}Mbps (expected {expected_speed}Mbps)")
                if duplex != "full":
                    intf_failures.append(f"duplex={duplex!r} (expected full)")
            else:
                raw_speeds = hw.get("speeds", "")
                supported = {int(s.strip()) for s in raw_speeds.split(",") if s.strip().isdigit()}
                if supported and speed_mbps not in supported:
                    intf_failures.append(
                        f"speed={speed_mbps}Mbps not in supported speeds {sorted(supported, reverse=True)}"
                    )
                if duplex != "full":
                    intf_failures.append(f"duplex={duplex!r} (expected full)")

            if intf_failures:
                logger.warn(f"{device_ip}: {name} {'; '.join(intf_failures)}")
                failures.extend(f"{name}: {f}" for f in intf_failures)
            else:
                logger.info(f"{device_ip}: {name} ok (speed={speed_mbps}Mbps duplex={duplex})")

        if failures:
            bad_intfs = len({f.split(":")[0] for f in failures})
            raise AssertionError(
                f"{device_ip}: {bad_intfs} interface(s) with unexpected speed or duplex"
            )
