"""Robot Framework library: AAA Port Access keywords."""

from robot.api import logger

import _aoscx


class CXLibraryAAAPortAccess:
    ROBOT_LIBRARY_SCOPE = "SUITE"

    def radius_servers_should_be_reachable(
        self,
        device_ip,
        primary_radius_server=None,
        secondary_radius_server=None,
        management_vrf=None,
    ):
        """Verify primary and secondary RADIUS servers are reachable and tracked.

        Args:
            device_ip: Switch management IP.
            primary_radius_server: Hostname/IP of the expected primary
                RADIUS server (${PRIMARY_RADIUS_SERVER}).
            secondary_radius_server: Hostname/IP of the expected secondary
                RADIUS server (${SECONDARY_RADIUS_SERVER}).
            management_vrf: VRF holding the RADIUS server entries
                (${MANAGEMENT_VRF}).

        For each expected server, fetches
        /system/vrfs/<vrf>/radius_servers/<host>,1812,udp via
        _aoscx.cached_get and asserts that:
          * reachability_status is "reachable"
          * tracking_enable is true
        All failures are collected and raised together.
        """
        if primary_radius_server is None:
            raise AssertionError(f"{device_ip}: primary_radius_server not provided")
        if secondary_radius_server is None:
            raise AssertionError(f"{device_ip}: secondary_radius_server not provided")

        vrf = management_vrf
        servers = [
            ("primary", primary_radius_server),
            ("secondary", secondary_radius_server),
        ]
        bad_servers = 0
        failures = []
        for role, hostname in servers:
            key = f"{hostname},1812,udp"
            data = _aoscx.cached_get(
                device_ip,
                f"/system/vrfs/{vrf}/radius_servers/{key}",
            )
            if not data:
                logger.warn(f"{device_ip}: RADIUS {hostname} ({role}) not found")
                failures.append(f"{hostname} ({role}): not found")
                bad_servers += 1
                continue

            reachability = data.get("reachability_status", "unknown")
            tracking = data.get("tracking_enable", False)

            server_failures = []
            if reachability.lower() != "reachable":
                server_failures.append(f"reachability_status={reachability}")
            if not tracking:
                server_failures.append("tracking_enable is not true")
            if server_failures:
                logger.warn(f"{device_ip}: RADIUS {hostname} ({role}) {'; '.join(server_failures)}")
                failures.extend(f"{hostname} ({role}): {f}" for f in server_failures)
                bad_servers += 1
            else:
                logger.info(
                    f"{device_ip}: RADIUS {hostname} ({role}) ok (reachability={reachability} tracking={tracking})"
                )

        if failures:
            raise AssertionError(
                f"{device_ip}: {bad_servers} of 2 RADIUS servers with configuration issues"
            )

    def radius_coa_should_be_configured(
        self,
        device_ip,
        primary_radius_ip=None,
        secondary_radius_ip=None,
        management_vrf=None,
    ):
        """Verify RADIUS Change of Authorization is enabled and CoA clients are configured.

        Args:
            device_ip: Switch management IP.
            primary_radius_ip: Expected primary RADIUS CoA client IP
                (${PRIMARY_RADIUS_IP}).
            secondary_radius_ip: Expected secondary RADIUS CoA client IP
                (${SECONDARY_RADIUS_IP}).
            management_vrf: VRF holding the CoA client entries
                (${MANAGEMENT_VRF}).

        Reads /system?depth=2 to confirm radius_dynamic_authorization.enable
        is true, then reads
        /system/vrfs/<vrf>/radius_dynamic_authorization_clients?depth=2 to
        confirm both expected client IPs appear as CoA clients. All
        failures are collected and raised together.
        """
        if primary_radius_ip is None:
            raise AssertionError(f"{device_ip}: primary_radius_ip not provided")
        if secondary_radius_ip is None:
            raise AssertionError(f"{device_ip}: secondary_radius_ip not provided")

        vrf = management_vrf
        failures = []

        system_data = _aoscx.cached_get(device_ip, "/system?depth=2")
        coa_cfg = (system_data or {}).get("radius_dynamic_authorization", {})
        enabled = coa_cfg.get("enable", False)
        if not enabled:
            logger.warn(
                f"{device_ip}: radius_dynamic_authorization.enable={enabled!r} (expected True)"
            )
            failures.append("radius_dynamic_authorization.enable is not true")
        else:
            logger.info(f"{device_ip}: radius_dynamic_authorization.enable=True ok")

        clients = _aoscx.cached_get(
            device_ip,
            f"/system/vrfs/{vrf}/radius_dynamic_authorization_clients?depth=2",
        )
        client_addresses = {
            v.get("address") for v in (clients or {}).values() if isinstance(v, dict)
        }
        for role, ip in [
            ("primary", primary_radius_ip),
            ("secondary", secondary_radius_ip),
        ]:
            if ip not in client_addresses:
                logger.warn(
                    f"{device_ip}: {role} CoA client {ip} not found (configured: {sorted(client_addresses)})"
                )
                failures.append(f"{role} CoA client {ip} not found")
            else:
                logger.info(f"{device_ip}: {role} CoA client {ip} ok")

        if failures:
            raise AssertionError(f"{device_ip}: {len(failures)} RADIUS CoA configuration issue(s)")

    def colourless_ports_should_have_auth(self, device_ip):
        """Verify edge ports described as COLOURLESS have 802.1X / MAC auth configured.

        Args:
            device_ip: Switch management IP.

        Iterates over all interfaces from _aoscx.interfaces, filters down to
        non-pluggable physical ports (via _aoscx.is_physical and _aoscx.is_pluggable),
        and for each one asserts that:
          * description contains "COLOURLESS"
          * applied_vlan_mode is "access"
          * dot1x and mac-auth both have auth_enable, cached_reauth_enable,
            and reauth_enable set to true
            (read from
            /system/interfaces/<port>/port_access_auth_configurations).
        All failures (across all ports and checks) are collected and raised
        together.
        """
        interfaces = _aoscx.interfaces(device_ip)
        failures = []
        bad_ports = 0

        for name, data in sorted(interfaces.items(), key=lambda x: _aoscx.interface_sort_key(x[0])):
            if not _aoscx.is_physical(name):
                continue
            if _aoscx.is_pluggable(data):
                continue

            port_failures = []
            desc = data.get("description") or ""
            if "COLOURLESS" not in desc.upper():
                port_failures.append(f"description {desc!r} does not contain COLOURLESS")
            if data.get("applied_vlan_mode") != "access":
                port_failures.append(
                    f"applied_vlan_mode={data.get('applied_vlan_mode')!r} (expected access)"
                )
            encoded = name.replace("/", "%2F")
            auth_cfg = _aoscx.cached_get(
                device_ip,
                f"/system/interfaces/{encoded}/port_access_auth_configurations?depth=2",
            )
            for auth_type in ("dot1x", "mac-auth"):
                cfg = (auth_cfg or {}).get(auth_type, {})
                for field in ("auth_enable", "cached_reauth_enable", "reauth_enable"):
                    if not cfg.get(field, False):
                        port_failures.append(f"{auth_type}.{field} is not true")
            if port_failures:
                logger.warn(f"{device_ip}: {name} {'; '.join(port_failures)}")
                failures.extend(f"{name}: {f}" for f in port_failures)
                bad_ports += 1
            else:
                logger.info(
                    f"{device_ip}: {name} ok (desc={desc!r} vlan_mode={data.get('applied_vlan_mode')} dot1x+mac-auth enabled)"
                )

        if failures:
            raise AssertionError(
                f"{device_ip}: {bad_ports} colourless port(s) with configuration issues"
            )

    def client_ip_tracking_should_be_enabled(self, device_ip):
        """Verify client IP tracking is enabled globally and across all VLANs.

        Args:
            device_ip: Switch management IP.

        Reads client_ip_track_config from /system?depth=2. Both enable and
        all_vlans must be true. All failures are collected and raised
        together.
        """
        system_data = _aoscx.cached_get(device_ip, "/system?depth=2")
        cfg = (system_data or {}).get("client_ip_track_config", {})
        failures = []
        if not cfg.get("enable", False):
            logger.warn(
                f"{device_ip}: client_ip_track_config.enable={cfg.get('enable')!r} (expected True)"
            )
            failures.append("client_ip_track_config.enable is not true")
        else:
            logger.info(f"{device_ip}: client_ip_track_config.enable=True ok")
        if not cfg.get("all_vlans", False):
            logger.warn(
                f"{device_ip}: client_ip_track_config.all_vlans={cfg.get('all_vlans')!r} (expected True)"
            )
            failures.append("client_ip_track_config.all_vlans is not true")
        else:
            logger.info(f"{device_ip}: client_ip_track_config.all_vlans=True ok")

        if failures:
            raise AssertionError(
                f"{device_ip}: {len(failures)} client IP tracking configuration issue(s)"
            )
