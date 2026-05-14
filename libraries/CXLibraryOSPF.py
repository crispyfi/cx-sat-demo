"""Robot Framework library: OSPF keywords."""

import time
from robot.api import logger

import _aoscx


class CXLibraryOSPF:
    ROBOT_LIBRARY_SCOPE = "SUITE"

    def _ospf_routers(self, device_ip, vrf_name="default"):
        """Cached accessor for /system/vrfs/<vrf_name>/ospf_routers?depth=2."""
        return _aoscx.cached_get(device_ip, f"/system/vrfs/{vrf_name}/ospf_routers?depth=2")

    def ospf_passive_default_should_be_configured(self, device_ip):
        """Verify OSPF passive-interface default is enabled in every OSPF process.

        Args:
            device_ip: Switch management IP.

        For each VRF and OSPF process, reads passive_interface_default
        and collects any process where it is falsy. Routed transit
        interfaces are expected to opt out individually; this keyword
        only enforces the default. All failures are reported together.
        """
        vrfs = _aoscx.cached_get(device_ip, "/system/vrfs?depth=2")
        failures = []
        for vrf_name in vrfs:
            routers = self._ospf_routers(device_ip, vrf_name)
            for rid, rdata in routers.items():
                passive = rdata.get("passive_interface_default", False)
                if not passive:
                    logger.warn(
                        f"{device_ip}: VRF {vrf_name} OSPF {rid} passive_interface_default={passive} (expected True)"
                    )
                    failures.append(f"VRF {vrf_name} instance {rid}")
                else:
                    logger.info(
                        f"{device_ip}: VRF {vrf_name} OSPF {rid} ok (passive_interface_default=True)"
                    )
        if failures:
            raise AssertionError(
                f"{device_ip}: {len(failures)} OSPF process(es) with passive_interface_default not enabled"
            )

    def ospf_graceful_restart_should_be_configured(self, device_ip, restart_interval):
        """Verify OSPF graceful restart restart_interval matches the expected value.

        Args:
            device_ip: Switch management IP.
            restart_interval: Expected restart_interval in seconds
                (${OSPF_GRACEFUL_RESTART_INTERVAL}). Accepts ints or
                numeric strings.

        For each VRF / OSPF process, reads restart_interval and
        asserts it equals restart_interval. A missing
        restart_interval is reported as "graceful restart not
        configured". All failures are collected and raised together.
        """
        restart_interval = int(restart_interval)
        vrfs = _aoscx.cached_get(device_ip, "/system/vrfs?depth=2")
        failures = []
        for vrf_name in vrfs:
            routers = self._ospf_routers(device_ip, vrf_name)
            for rid, rdata in routers.items():
                actual = rdata.get("restart_interval")
                if actual is None:
                    logger.warn(
                        f"{device_ip}: VRF {vrf_name} OSPF {rid} graceful restart not configured (restart_interval missing)"
                    )
                    failures.append(
                        f"VRF {vrf_name} instance {rid}: graceful restart not configured"
                    )
                elif int(actual) != restart_interval:
                    logger.warn(
                        f"{device_ip}: VRF {vrf_name} OSPF {rid} restart_interval={actual} (expected {restart_interval})"
                    )
                    failures.append(
                        f"VRF {vrf_name} instance {rid}: restart_interval={actual} (expected {restart_interval})"
                    )
                else:
                    logger.info(
                        f"{device_ip}: VRF {vrf_name} OSPF {rid} ok (restart_interval={restart_interval})"
                    )
        if failures:
            raise AssertionError(
                f"{device_ip}: {len(failures)} OSPF process(es) with graceful restart misconfigured"
            )

    def ospf_max_metric_on_startup_should_be_configured(self, device_ip, start_time=5000):
        """Verify OSPF lsa_throttle.start_time matches the expected value.

        Args:
            device_ip: Switch management IP.
            start_time: Expected lsa_throttle.start_time in
                milliseconds. Accepts ints or numeric strings.

        For each VRF / OSPF process, reads lsa_throttle.start_time and
        asserts equality with start_time. The start_time is the delay
        before the first LSA origination after boot, used to avoid
        announcing routes before convergence. All mismatches are
        collected and raised together.
        """
        start_time = int(start_time)
        vrfs = _aoscx.cached_get(device_ip, "/system/vrfs?depth=2")
        failures = []
        for vrf_name in vrfs:
            routers = self._ospf_routers(device_ip, vrf_name)
            for rid, rdata in routers.items():
                actual = (rdata.get("lsa_throttle") or {}).get("start_time")
                if actual != start_time:
                    logger.warn(
                        f"{device_ip}: VRF {vrf_name} OSPF {rid} lsa_throttle.start_time={actual} (expected {start_time})"
                    )
                    failures.append(
                        f"VRF {vrf_name} instance {rid}: lsa_throttle.start_time={actual} (expected {start_time})"
                    )
                else:
                    logger.info(
                        f"{device_ip}: VRF {vrf_name} OSPF {rid} ok (lsa_throttle.start_time={start_time})"
                    )
        if failures:
            raise AssertionError(
                f"{device_ip}: {len(failures)} OSPF process(es) with incorrect LSA throttle start_time"
            )

    def ospf_bfd_should_be_enabled(self, device_ip):
        """Verify every OSPF process has BFD enabled on all interfaces.

        Args:
            device_ip: Switch management IP.

        For each VRF / OSPF process, reads bfd_all_interfaces_enable
        and collects any process where it is falsy. All offending
        processes are reported together. This is the *configuration*
        check; ospf_bfd_sessions_should_be_active validates the
        resulting sessions are operationally up.
        """
        vrfs = _aoscx.cached_get(device_ip, "/system/vrfs?depth=2")
        failures = []
        for vrf_name in vrfs:
            routers = self._ospf_routers(device_ip, vrf_name)
            for rid, rdata in routers.items():
                bfd = rdata.get("bfd_all_interfaces_enable", False)
                if not bfd:
                    logger.warn(
                        f"{device_ip}: VRF {vrf_name} OSPF {rid} bfd_all_interfaces_enable={bfd} (expected True)"
                    )
                    failures.append(f"VRF {vrf_name} instance {rid}")
                else:
                    logger.info(
                        f"{device_ip}: VRF {vrf_name} OSPF {rid} ok (bfd_all_interfaces_enable=True)"
                    )
        if failures:
            raise AssertionError(
                f"{device_ip}: {len(failures)} OSPF process(es) with BFD not enabled on all interfaces"
            )

    def ospf_bfd_sessions_should_be_active(self, device_ip):
        """Verify every OSPF BFD session has all four state fields up.

        Args:
            device_ip: Switch management IP.

        For each VRF, fetches /system/vrfs/<vrf>/bfd_sessions?depth=2
        and filters to entries whose key starts with "ospf,". For each
        OSPF BFD session, asserts state.async, state.echo,
        state.remote, and state.session are all "up". All failures
        across all VRFs and sessions are collected and raised together.
        """
        vrfs = _aoscx.cached_get(device_ip, "/system/vrfs?depth=2")
        failures = []
        for vrf_name in vrfs:
            sessions = _aoscx.cached_get(
                device_ip,
                f"/system/vrfs/{vrf_name}/bfd_sessions?depth=2",
            )
            ospf_sessions = {k: v for k, v in sessions.items() if k.startswith("ospf,")}
            for session_key, session_data in ospf_sessions.items():
                state = session_data.get("state") or {}
                session_failures = []
                for field in ("async", "echo", "remote", "session"):
                    val = state.get(field)
                    if val != "up":
                        session_failures.append((field, val))
                if session_failures:
                    failure_summary = "; ".join(
                        f"state.{f}={v!r} (expected 'up')" for f, v in session_failures
                    )
                    logger.warn(f"{device_ip}: VRF {vrf_name} {session_key} {failure_summary}")
                    failures.extend(
                        f"VRF {vrf_name} {session_key}: state.{f}={v!r} (expected 'up')"
                        for f, v in session_failures
                    )
                else:
                    logger.info(f"{device_ip}: VRF {vrf_name} {session_key} ok (all states up)")
        if failures:
            raise AssertionError(f"{device_ip}: {len(failures)} OSPF BFD state field(s) not up")

    def all_ospf_neighbor_adjacencies_should_be_converged(self, device_ip):
        """Verify every OSPF neighbour is Full, or Two-Way on a multi-access segment.

        Args:
            device_ip: Switch management IP.

        Walks the full VRF → OSPF process → area → ospf_interface →
        ospf_neighbor hierarchy. For each interface, counts how many
        neighbours are in "full" state. A neighbour in "two_way" is
        accepted when the same interface has at least two "full"
        neighbours — the expected DROther behaviour on a broadcast
        segment where only the DR and BDR form full adjacencies. Any
        other state (or "two_way" with fewer than two full neighbours)
        is collected as a failure. All failures are raised together.
        """
        vrfs = _aoscx.cached_get(device_ip, "/system/vrfs?depth=2")
        failures = []
        for vrf_name in vrfs:
            routers = self._ospf_routers(device_ip, vrf_name)
            for rid in routers:
                areas = _aoscx.cached_get(
                    device_ip,
                    f"/system/vrfs/{vrf_name}/ospf_routers/{rid}/areas?depth=2",
                )
                for area_id in areas:
                    ospf_intfs = _aoscx.cached_get(
                        device_ip,
                        f"/system/vrfs/{vrf_name}/ospf_routers/{rid}/areas/{area_id}/ospf_interfaces?depth=2",
                    )
                    for intf_name in ospf_intfs:
                        neighbors = (
                            _aoscx.cached_get(
                                device_ip,
                                f"/system/vrfs/{vrf_name}/ospf_routers/{rid}/areas/{area_id}/ospf_interfaces/{intf_name}/ospf_neighbors?depth=2",
                            )
                            or {}
                        )
                        full_count = sum(
                            1 for nd in neighbors.values() if nd.get("nfsm_state") == "full"
                        )
                        for nbr_ip, nbr_data in neighbors.items():
                            state = nbr_data.get("nfsm_state", "unknown")
                            two_way_ok = state == "two_way" and full_count >= 2
                            if state == "full" or two_way_ok:
                                logger.info(
                                    f"{device_ip}: VRF {vrf_name} OSPF {rid} area {area_id} {intf_name} neighbor {nbr_ip} ok (state={state})"
                                )
                            else:
                                logger.warn(
                                    f"{device_ip}: VRF {vrf_name} OSPF {rid} area {area_id} {intf_name} neighbor {nbr_ip} state={state}"
                                )
                                failures.append(
                                    f"VRF {vrf_name} instance {rid} area {area_id} {intf_name}/{nbr_ip}: state={state}"
                                )
        if failures:
            raise AssertionError(
                f"{device_ip}: {len(failures)} OSPF neighbor(s) in unexpected state"
            )

    def no_ospf_routes_with_low_uptime(self, device_ip, min_age=300):
        """Verify no OSPF route across any VRF has a route_age below min_age.

        Args:
            device_ip: Switch management IP.
            min_age: Minimum acceptable age in seconds (default 300).
                OSPF routes younger than this are flagged as
                potentially unstable. Accepts ints or numeric strings.

        Iterates every VRF returned by /system/vrfs?depth=2. For each
        VRF fetches /system/vrfs/<vrf>/routes?depth=2 (uncached — route
        ages are live state) and inspects every entry where
        from == "ospf". Computes age as (now - route_age) and
        collects any route younger than min_age. Failures across all
        VRFs are reported together.
        """
        min_age = int(min_age)
        now = int(time.time())
        vrfs = _aoscx.cached_get(device_ip, "/system/vrfs?depth=2")
        failures = []
        for vrf_name in vrfs:
            routes = _aoscx.get(device_ip, f"/system/vrfs/{vrf_name}/routes?depth=2")
            if not isinstance(routes, dict):
                continue
            for prefix, rdata in routes.items():
                if rdata.get("from") != "ospf":
                    continue
                route_age = rdata.get("route_age")
                if route_age is None:
                    continue
                age_seconds = now - int(route_age)
                if age_seconds < min_age:
                    logger.warn(
                        f"{device_ip}: VRF {vrf_name} OSPF route {prefix} age={age_seconds}s (min {min_age}s)"
                    )
                    failures.append(prefix)
                else:
                    logger.info(
                        f"{device_ip}: VRF {vrf_name} OSPF route {prefix} ok (age={age_seconds}s)"
                    )
        if failures:
            raise AssertionError(
                f"{device_ip}: {len(failures)} OSPF route(s) with uptime below {min_age}s"
            )
