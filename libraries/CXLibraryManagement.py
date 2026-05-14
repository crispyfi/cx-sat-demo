"""Robot Framework library: Management plane access keywords (SSH, HTTPS, OOB)."""

from robot.api import logger

import _aoscx


class CXLibraryManagement:
    ROBOT_LIBRARY_SCOPE = "SUITE"

    def ssh_should_be_enabled_on_management_vrf(self, device_ip, management_vrf):
        """Verify SSH is enabled on the management VRF.

        Args:
            device_ip: Switch management IP.
            management_vrf: VRF on which SSH must be enabled
                (${MANAGEMENT_VRF}).

        Reads the VRF via _aoscx.vrf and asserts ssh_enable is True on
        management_vrf. ssh_server_status is not checked — it reflects
        a system-wide process state and returns "running" even on VRFs
        where ssh_enable is False.
        """
        en_data = _aoscx.vrf(device_ip, management_vrf)
        ssh_en = en_data.get("ssh_enable")
        if ssh_en is True:
            logger.info(f"{device_ip}: VRF {management_vrf} ssh_enable=True ok")
            return
        logger.warn(f"{device_ip}: VRF {management_vrf} ssh_enable={ssh_en} (expected True)")
        raise AssertionError(f"{device_ip}: SSH not enabled on VRF {management_vrf}")

    def https_should_be_enabled_on_management_vrf(self, device_ip, management_vrf):
        """Verify HTTPS is enabled on the management VRF.

        Args:
            device_ip: Switch management IP.
            management_vrf: VRF on which HTTPS must be enabled
                (${MANAGEMENT_VRF}).

        When management_vrf is "default", HTTPS on that VRF is confirmed by
        the active REST connection. Otherwise reads _aoscx.vrf and asserts
        https_server.enable is True on management_vrf.
        """
        if management_vrf == "default":
            logger.info(f"{device_ip}: VRF default HTTPS ok (confirmed by active connection)")
            return
        en_data = _aoscx.vrf(device_ip, management_vrf)
        https_en = (en_data.get("https_server") or {}).get("enable", False)
        if https_en:
            logger.info(f"{device_ip}: VRF {management_vrf} https_server.enable=True ok")
            return
        logger.warn(
            f"{device_ip}: VRF {management_vrf} https_server.enable={https_en!r} (expected True)"
        )
        raise AssertionError(f"{device_ip}: HTTPS not enabled on VRF {management_vrf}")

    def loopback0_should_be_in_management_vrf(self, device_ip, management_vrf):
        """Verify loopback0 is bound to the management VRF.

        Args:
            device_ip: Switch management IP.
            management_vrf: Expected VRF for loopback0 (${MANAGEMENT_VRF}).

        Reads loopback0 from _aoscx.interfaces and asserts that
        management_vrf appears in its vrf map.
        """
        interfaces = _aoscx.interfaces(device_ip)
        lo0 = interfaces.get("loopback0") or {}
        vrf = lo0.get("vrf") or {}
        logger.info(f"{device_ip}: loopback0 vrf={list(vrf.keys())}")
        if management_vrf not in vrf:
            raise AssertionError(
                f"{device_ip}: loopback0 not in expected VRF {management_vrf!r} (actual={list(vrf.keys())})"
            )

    def source_interface_should_be_loopback0(self, device_ip):
        """Verify outbound services source from loopback0.

        Args:
            device_ip: Switch management IP.

        Reads ntp_config_vrf.source_interface from /system?depth=2 (via
        _aoscx.system) — despite the name, this map covers the source
        interface for all VRF-bound services (RADIUS, TACACS, SNMP,
        syslog, NTP), not just NTP. Asserts that at least one of the
        configured source interfaces references "loopback0"
        (case-insensitive substring match across the map's values).
        Fails immediately if the map is empty.
        """
        sys = _aoscx.system(device_ip)
        ntp_config_vrf = sys.get("ntp_config_vrf") or {}
        src_intf = {}
        for vrf_data in ntp_config_vrf.values():
            if isinstance(vrf_data, dict):
                src_intf.update(vrf_data.get("source_interface") or {})
        summary = {k: str(v).rstrip("/").split("/")[-1] for k, v in src_intf.items()}
        logger.info(f"{device_ip}: ntp_config_vrf source_interface = {summary}")
        if not src_intf:
            raise AssertionError(f"{device_ip}: no source_interface configured in ntp_config_vrf")
        if not any("loopback0" in str(v).lower() for v in src_intf.values()):
            raise AssertionError(
                f"{device_ip}: source_interface does not reference loopback0: {src_intf}"
            )

    def central_should_be_connected(self, device_ip, management_vrf):
        """Verify the device reports an active connection to Aruba Central.

        Args:
            device_ip: Switch management IP.
            management_vrf: Expected VRF name used for the Central
                connection (${MANAGEMENT_VRF}).

        Reads aruba_central from /system?depth=2 (via _aoscx.system) and
        asserts that status.central_connection equals "connected" and that
        management_vrf is present in aruba_central.vrf. Both failures are
        collected and raised together.
        """
        sys_data = _aoscx.system(device_ip)
        central = sys_data.get("hpe_anw_central") or {}
        status = central.get("status") or {}
        connection = status.get("central_connection", "")
        vrf = central.get("vrf") or {}
        logger.info(
            f"{device_ip}: central_connection={connection}, vrf={list(vrf.keys())}, expected_management_vrf={management_vrf}"
        )
        failures = []
        if connection != "connected":
            failures.append(f"central_connection is {connection!r}, expected 'connected'")
        if management_vrf not in vrf:
            failures.append(
                f"management_vrf {management_vrf!r} not found in aruba_central.vrf {list(vrf.keys())!r}"
            )
        if failures:
            raise AssertionError(f"{device_ip}: " + "; ".join(failures))

    def configuration_lockout_should_be_central(self, device_ip):
        """Verify configuration lockout is in Central-managed mode.

        Args:
            device_ip: Switch management IP.

        Reads /system?depth=2 (via _aoscx.system) and asserts that both
        configuration_lockout_config.central and
        configuration_lockout_status.central are "managed". This blocks
        local CLI configuration changes — only Central can write
        configuration. Both checks are collected and raised together so
        the operator sees whether the issue is config (intent) or status
        (effective state) or both.
        """
        sys_data = _aoscx.system(device_ip)
        cfg_val = (sys_data.get("configuration_lockout_config") or {}).get("central", "")
        sts_val = (sys_data.get("configuration_lockout_status") or {}).get("central", "")
        logger.info(
            f"{device_ip}: configuration_lockout_config.central={cfg_val!r}, configuration_lockout_status.central={sts_val!r}"
        )
        failures = []
        if cfg_val != "managed":
            failures.append(
                f"configuration_lockout_config.central is {cfg_val!r}, expected 'managed'"
            )
        if sts_val != "managed":
            failures.append(
                f"configuration_lockout_status.central is {sts_val!r}, expected 'managed'"
            )
        if failures:
            raise AssertionError(f"{device_ip}: " + "; ".join(failures))
