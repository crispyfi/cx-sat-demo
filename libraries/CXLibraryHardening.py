"""Robot Framework library: Hardening keywords."""

from robot.api import logger

import _aoscx


class CXLibraryHardening:
    ROBOT_LIBRARY_SCOPE = "SUITE"

    def usb_should_be_disabled(self, device_ip):
        """Verify the USB port is disabled.

        Args:
            device_ip: Switch management IP.

        Reads usb_disable from /system?depth=2 (via _aoscx.system) and
        fails if the flag is not truthy.
        """
        sys_data = _aoscx.system(device_ip)
        usb = sys_data.get("usb_disable", False)
        logger.info(f"{device_ip}: usb_disable = {usb}")
        if not usb:
            raise AssertionError(f"{device_ip}: USB is not disabled (usb_disable={usb})")

    def bluetooth_should_be_disabled(self, device_ip):
        """Verify Bluetooth management is disabled.

        Args:
            device_ip: Switch management IP.

        Reads bluetooth_mgmt_disable from /system?depth=2 (via
        _aoscx.system) and fails if the flag is not truthy.
        """
        sys_data = _aoscx.system(device_ip)
        bt = sys_data.get("bluetooth_mgmt_disable", False)
        logger.info(f"{device_ip}: bluetooth_mgmt_disable = {bt}")
        if not bt:
            raise AssertionError(
                f"{device_ip}: Bluetooth is not disabled (bluetooth_mgmt_disable={bt})"
            )

    def telnet_server_should_be_disabled(self, device_ip, management_vrf):
        """Verify the Telnet server is disabled on the management VRF.

        Args:
            device_ip: Switch management IP.
            management_vrf: VRF to check for telnet_server_enable
                (${MANAGEMENT_VRF}).

        Reads ntp_config_vrf.<management_vrf>.telnet_server_enable from
        /system?depth=2 (via _aoscx.system) and fails if it is truthy.
        """
        vrf_name = management_vrf
        sys_data = _aoscx.system(device_ip)
        vrf_cfg = (sys_data.get("ntp_config_vrf") or {}).get(vrf_name) or {}
        telnet_en = vrf_cfg.get("telnet_server_enable")
        logger.info(f"{device_ip}: ntp_config_vrf.{vrf_name}.telnet_server_enable={telnet_en!r}")
        if telnet_en:
            raise AssertionError(
                f"{device_ip}: telnet_server_enable={telnet_en!r} on VRF {vrf_name} — telnet must be disabled"
            )

    def icmp_redirects_should_be_disabled(self, device_ip):
        """Verify ICMP redirect messages are disabled.

        Args:
            device_ip: Switch management IP.

        Reads icmp_redirect_disable from /system?depth=2 (via
        _aoscx.system) and fails if the flag is not truthy.
        """
        sys_data = _aoscx.system(device_ip)
        icmp = sys_data.get("icmp_redirect_disable", False)
        logger.info(f"{device_ip}: icmp_redirect_disable = {icmp}")
        if not icmp:
            raise AssertionError(
                f"{device_ip}: ICMP redirects not disabled (icmp_redirect_disable={icmp})"
            )

    def login_banner_should_be_configured(self, device_ip, banner_prefix):
        """Verify the login banner starts with the expected unauthorised-access warning.

        Args:
            device_ip: Switch management IP.
            banner_prefix: Expected text at the start of the banner
                (${LOGIN_BANNER_PREFIX}). Fails if not provided.

        Reads other_config.banner from /system?depth=2 (via
        _aoscx.system). The API returns the banner with a leading newline,
        which is stripped before the prefix check. Fails if the banner is
        empty or does not start with banner_prefix. Both failure modes are
        collected before raising.
        """
        if banner_prefix is None:
            raise AssertionError(f"{device_ip}: banner_prefix not provided")
        sys_data = _aoscx.system(device_ip)
        other_config = sys_data.get("other_config") or {}
        banner = other_config.get("banner", "")
        failures = []
        if not banner:
            logger.warn(f"{device_ip}: no login banner configured")
            failures.append("no login banner configured")
        elif not banner.lstrip("\n").startswith(banner_prefix):
            logger.warn(f"{device_ip}: banner does not start with {banner_prefix!r}")
            failures.append(f"banner does not start with {banner_prefix!r}")
        else:
            logger.info(f"{device_ip}: banner ok (starts with {banner_prefix!r})")
        if failures:
            raise AssertionError(f"{device_ip}: {'; '.join(failures)}")

    def control_plane_acl_should_be_applied(self, device_ip, acl_name, management_vrf):
        """Verify the named IPv4 ACL is applied to the control plane.

        Args:
            device_ip: Switch management IP.
            acl_name: Name of the ACL to verify (${CONTROLPLANE_ACL_NAME}).
                Fails if not provided.
            management_vrf: VRF whose control-plane ACL config is checked
                (${MANAGEMENT_VRF}).

        Reads aclv4_control_plane_cfg from /system/vrfs/<management_vrf> and
        looks for an entry where name == acl_name and list_type == "ipv4".
        Asserts that the matched entry's status.state is "applied". Fails
        immediately if no such ACL entry exists.
        """
        if acl_name is None:
            raise AssertionError(f"{device_ip}: acl_name not provided")
        vrf = _aoscx.cached_get(
            device_ip,
            f"/system/vrfs/{management_vrf}?attributes=aclv4_control_plane_cfg&depth=2",
        )
        acl_cfg = vrf.get("aclv4_control_plane_cfg") or {}
        entry = None
        for _, candidate in acl_cfg.items():
            if candidate.get("name") == acl_name and candidate.get("list_type") == "ipv4":
                entry = candidate
                break
        if entry is None:
            raise AssertionError(
                f"{device_ip}: no {acl_name} ipv4 ACL found on control plane (vrf={management_vrf})"
            )
        state = (entry.get("status") or {}).get("state")
        if state != "applied":
            logger.warn(f"{device_ip}: {acl_name} ACL state={state!r} (expected 'applied')")
            raise AssertionError(
                f"{device_ip}: {acl_name} ACL state is {state!r}, expected 'applied'"
            )
        logger.info(f"{device_ip}: {acl_name} ACL state ok ('applied')")

    def arp_protection_should_be_on_all_vlans(self, device_ip):
        """Verify dynamic ARP inspection is enabled on every VLAN.

        Args:
            device_ip: Switch management IP.

        Iterates _aoscx.vlans and, for each VLAN, reads
        arp_inspection_enable and collects any VLAN where it is falsy.
        All offending VLAN IDs are reported in a single failure.
        """
        vlans = _aoscx.vlans(device_ip)
        disabled = []
        for vid, vdata in sorted(vlans.items(), key=lambda x: _aoscx.vlan_sort_key(x[0])):
            arp_insp = vdata.get("arp_inspection_enable", False)
            if not arp_insp:
                logger.warn(f"{device_ip}: VLAN {vid} arp_inspection_enable={arp_insp}")
                disabled.append(str(vid))
            else:
                logger.info(f"{device_ip}: VLAN {vid} ok (arp_inspection_enable=True)")
        if disabled:
            raise AssertionError(
                f"{device_ip}: VLANs without ARP inspection: {', '.join(disabled)}"
            )

    def dhcp_snooping_should_be_on_all_vlans(self, device_ip):
        """Verify DHCP snooping is enabled on every VLAN.

        Args:
            device_ip: Switch management IP.

        Iterates _aoscx.vlans and, for each VLAN, reads
        dhcpv4_snooping_enable and collects any VLAN where it is falsy.
        All offending VLAN IDs are reported in a single failure.
        """
        vlans = _aoscx.vlans(device_ip)
        disabled = []
        for vid, vdata in sorted(vlans.items(), key=lambda x: _aoscx.vlan_sort_key(x[0])):
            snoop = vdata.get("dhcpv4_snooping_enable", False)
            if not snoop:
                logger.warn(f"{device_ip}: VLAN {vid} dhcpv4_snooping_enable={snoop}")
                disabled.append(str(vid))
            else:
                logger.info(f"{device_ip}: VLAN {vid} ok (dhcpv4_snooping_enable=True)")
        if disabled:
            raise AssertionError(f"{device_ip}: VLANs without DHCP snooping: {', '.join(disabled)}")

    def dhcp_snooping_trusted_port_should_be_configured(self, device_ip, trusted_port):
        """Verify the upstream uplink port is configured as a DHCP snooping trusted port.

        Args:
            device_ip: Switch management IP.
            trusted_port: Interface name to verify as trusted
                (${UPLINK_LAG}). Fails if not provided.

        Looks up trusted_port in _aoscx.interfaces and reads
        dhcpv4_snooping_configuration.trusted. Fails if the interface
        does not exist or trusted is not true.
        """
        if trusted_port is None:
            raise AssertionError(f"{device_ip}: trusted_port not provided")
        interfaces = _aoscx.interfaces(device_ip)
        port = interfaces.get(trusted_port)
        if port is None:
            raise AssertionError(f"{device_ip}: {trusted_port} interface not found")
        snoop_cfg = port.get("dhcpv4_snooping_configuration") or {}
        trusted = snoop_cfg.get("trusted", False)
        logger.info(f"{device_ip}: {trusted_port} dhcpv4_snooping trusted={trusted}")
        if not trusted:
            raise AssertionError(f"{device_ip}: {trusted_port} is not a DHCP snooping trusted port")

    def loop_protection_should_be_on_edge_ports(self, device_ip):
        """Verify loop protection is enabled on every edge port.

        Args:
            device_ip: Switch management IP.

        Iterates _aoscx.interfaces, filters to non-pluggable physical ports
        (client-facing edge ports), reads loop_protect_enable for each,
        and collects any port where it is falsy. Fails immediately if no
        edge ports are found. All offending ports are reported in a single
        failure.
        """
        interfaces = _aoscx.interfaces(device_ip)
        missing = []
        checked = 0
        for name, data in sorted(interfaces.items(), key=lambda x: _aoscx.interface_sort_key(x[0])):
            if not _aoscx.is_physical(name):
                continue
            if _aoscx.is_pluggable(data):
                continue
            checked += 1
            lp = data.get("loop_protect_enable", False)
            if not lp:
                logger.warn(f"{device_ip}: {name} loop_protect_enable not set")
                missing.append(name)
            else:
                logger.info(f"{device_ip}: {name} ok (loop_protect_enable=True)")
        if checked == 0:
            raise AssertionError(f"{device_ip}: no edge ports found")
        if missing:
            raise AssertionError(
                f"{device_ip}: {len(missing)} of {checked} edge ports without loop protection"
            )
