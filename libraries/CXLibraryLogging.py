"""Robot Framework library: Syslog configuration and event log health keywords."""

from robot.api import logger
from robot.api.exceptions import SkipExecution

import _aoscx


class CXLibraryLogging:
    ROBOT_LIBRARY_SCOPE = "SUITE"

    def syslog_should_be_configured(self, device_ip, management_vrf, syslog_server=None):
        """Verify the expected syslog server is configured, enabled, and on the right VRF.

        Args:
            device_ip: Switch management IP.
            management_vrf: VRF the syslog remote must be bound to
                (${MANAGEMENT_VRF}).
            syslog_server: Hostname/IP of the expected syslog destination
                (${SYSLOG_SERVER}). When None, logs an advisory and
                returns without checking — syslog is an optional feature.

        Reads /system/syslog_remotes?depth=2 (cached) and asserts:
          * at least one remote is configured (always)
          * the entry keyed by syslog_server exists (when supplied)
          * that entry's disable flag is falsy
          * the entry's vrf map includes management_vrf
        All failures are collected and raised together.
        """
        if syslog_server is None:
            raise SkipExecution(f"{device_ip}: syslog_server not provided")
        remotes = _aoscx.cached_get(device_ip, "/system/syslog_remotes?depth=2") or {}
        failures = []

        if not remotes:
            logger.warn(f"{device_ip}: no syslog remote servers configured")
            failures.append("no syslog remote servers configured")
        elif syslog_server:
            entry = remotes.get(syslog_server)
            if entry is None:
                logger.warn(
                    f"{device_ip}: syslog server {syslog_server!r} not found (configured: {sorted(remotes.keys())})"
                )
                failures.append(
                    f"syslog server {syslog_server!r} not found (configured: {sorted(remotes.keys())})"
                )
            else:
                disabled = entry.get("disable", False)
                if disabled:
                    logger.warn(f"{device_ip}: syslog server {syslog_server!r} is disabled")
                    failures.append(f"syslog server {syslog_server!r} is disabled")
                else:
                    logger.info(f"{device_ip}: syslog server {syslog_server!r} enabled ok")
                vrf_keys = list((entry.get("vrf") or {}).keys())
                if management_vrf not in vrf_keys:
                    logger.warn(
                        f"{device_ip}: syslog server {syslog_server!r} VRF {vrf_keys} (expected {management_vrf!r})"
                    )
                    failures.append(
                        f"syslog server {syslog_server!r} uses VRF {vrf_keys}, expected {management_vrf!r}"
                    )
                else:
                    logger.info(
                        f"{device_ip}: syslog server {syslog_server!r} VRF {management_vrf!r} ok"
                    )

        if failures:
            raise AssertionError(f"{device_ip}: syslog configuration has {len(failures)} issue(s)")
