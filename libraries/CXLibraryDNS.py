"""Robot Framework library: DNS domain name and resolver keywords."""

from robot.api import logger

import _aoscx


class CXLibraryDNS:
    ROBOT_LIBRARY_SCOPE = "SUITE"

    def domain_name_should_match(self, device_ip, expected_domain):
        """Verify the configured dns_domain_name matches design input.

        Args:
            device_ip: Switch management IP.
            expected_domain: Expected domain name (${DOMAIN_NAME}). Fails
                if not provided.

        Reads dns_domain_name from the default VRF and asserts exact string
        equality with expected_domain.
        """
        if expected_domain is None:
            raise AssertionError(f"{device_ip}: expected_domain not provided")
        domain = _aoscx.vrf(device_ip, "default").get("dns_domain_name", "")
        logger.info(f"{device_ip}: dns_domain_name={domain!r} (expected {expected_domain!r})")
        if domain != expected_domain:
            raise AssertionError(
                f"{device_ip}: dns_domain_name is {domain!r}, expected {expected_domain!r}"
            )

    def dns_servers_should_match(self, device_ip, management_vrf, dns_servers):
        """Verify the configured DNS name servers match design input.

        Args:
            device_ip: Switch management IP.
            management_vrf: VRF holding the DNS name server entries
                (${MANAGEMENT_VRF}).
            dns_servers: List of expected DNS server IPs (${DNS_SERVERS}).
                At least one entry is required.

        Reads dns_name_servers from management_vrf. Fails if dns_servers
        is not provided or empty, if no servers are configured on the
        device, or if the configured set does not exactly match the
        expected set.
        """
        if not dns_servers:
            raise AssertionError(f"{device_ip}: dns_servers not provided")
        servers_dict = _aoscx.vrf(device_ip, management_vrf).get("dns_name_servers") or {}
        actual = set(servers_dict.values())
        expected = set(dns_servers)
        failures = []
        if not actual:
            logger.warn(f"{device_ip}: VRF {management_vrf} no DNS servers configured")
            failures.append(f"no DNS servers configured on VRF {management_vrf}")
        else:
            for server in sorted(expected):
                if server in actual:
                    logger.info(f"{device_ip}: VRF {management_vrf} DNS server {server} ok")
                else:
                    logger.warn(
                        f"{device_ip}: VRF {management_vrf} DNS server {server} not configured (actual: {sorted(actual)})"
                    )
                    failures.append(f"DNS server {server} not found (configured: {sorted(actual)})")
            for server in sorted(actual - expected):
                logger.warn(f"{device_ip}: VRF {management_vrf} unexpected DNS server {server}")
                failures.append(f"unexpected DNS server {server}")
        if failures:
            raise AssertionError(
                f"{device_ip}: DNS server mismatch on VRF {management_vrf} ({len(failures)} issue(s))"
            )
