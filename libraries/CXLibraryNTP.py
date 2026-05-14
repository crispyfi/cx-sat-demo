"""Robot Framework library: Timezone and NTP synchronisation keywords."""

from robot.api import logger

import _aoscx


class CXLibraryNTP:
    ROBOT_LIBRARY_SCOPE = "SUITE"

    def timezone_should_be(self, device_ip, timezone):
        """Verify the device timezone matches the expected IANA value.

        Args:
            device_ip: Switch management IP.
            timezone: Expected IANA timezone string (${TIMEZONE}).
                Fails if not provided.

        Reads timezone from /system?depth=2 (via _aoscx.system) and fails
        on any mismatch. Comparison is exact (case-sensitive).
        """
        if not timezone:
            raise AssertionError(f"{device_ip}: timezone not provided")
        sys_data = _aoscx.system(device_ip)
        tz = sys_data.get("timezone", "")
        logger.info(f"{device_ip}: timezone = {tz} (expected {timezone})")
        if tz != timezone:
            raise AssertionError(f"{device_ip}: timezone is {tz!r}, expected {timezone!r}")

    def ntp_should_be_synced_to(self, device_ip, expected_servers):
        """Verify NTP is synchronised to the expected servers.

        Args:
            device_ip: Switch management IP.
            expected_servers: Expected NTP server IPs (${NTP_SERVERS}).
                May be a list, or a comma-separated string (which is
                split on commas). Fails if not provided.

        Fetches /system/vrfs/default/ntp_associations?depth=2 (cached
        — AOS-CX surfaces NTP associations on the default VRF regardless
        of which VRF the servers are configured under) and runs three
        checks, collecting all failures before raising:

        1. System peer present: at least one association has
           association_status.peer_status_word == "system_peer", and
           that peer's stratum is < 16 (16 means unreachable).
        2. Configured server set: the set of configured server IPs must
           equal the expected set exactly.
        3. Per-association attributes: every configured server must
           have association_attributes matching this environment's
           NTP profile — burst_mode "iburst", minpoll 4, maxpoll 4,
           ntp_version 4. These constants are hardcoded in
           _EXPECTED_ATTRS; adjust for sites that diverge.

        Fails immediately if no NTP associations are found on the VRF.
        """
        if not expected_servers:
            raise AssertionError(f"{device_ip}: expected_servers not provided")
        ntp = _aoscx.cached_get(
            device_ip,
            "/system/vrfs/default/ntp_associations?depth=2",
        )
        if not ntp:
            raise AssertionError(f"{device_ip}: no NTP associations found on default VRF")

        if isinstance(expected_servers, str):
            expected_servers = [s.strip() for s in expected_servers.split(",")]

        failures = []

        system_peer = None
        for server_ip, entry in ntp.items():
            peer_word = (entry.get("association_status") or {}).get("peer_status_word", "")
            if peer_word == "system_peer":
                system_peer = (server_ip, entry)
                break

        logger.info(
            f"{device_ip}: NTP configured={sorted(ntp.keys())} system_peer={system_peer[0] if system_peer else None}"
        )

        if system_peer is None:
            failures.append("no NTP server has peer_status_word 'system_peer'")
        else:
            peer_ip, peer_entry = system_peer
            stratum = (peer_entry.get("association_status") or {}).get("stratum")
            try:
                if int(stratum) >= 16:
                    failures.append(f"system peer {peer_ip} has stratum {stratum} (unreachable)")
            except (TypeError, ValueError):
                failures.append(f"system peer {peer_ip} has invalid stratum {stratum!r}")

        configured = set(ntp.keys())
        expected_set = set(expected_servers)
        if configured != expected_set:
            failures.append(
                f"configured NTP servers {sorted(configured)} do not match expected {sorted(expected_set)}"
            )

        _EXPECTED_ATTRS = {
            "burst_mode": "iburst",
            "maxpoll": 4,
            "minpoll": 4,
            "ntp_version": 4,
        }
        for server_ip, entry in ntp.items():
            attrs = entry.get("association_attributes") or {}
            for key, expected_val in _EXPECTED_ATTRS.items():
                actual_val = attrs.get(key)
                if actual_val != expected_val:
                    failures.append(
                        f"{server_ip} association_attributes.{key} is {actual_val!r}, expected {expected_val!r}"
                    )

        if failures:
            raise AssertionError(f"{device_ip}: " + "; ".join(failures))
