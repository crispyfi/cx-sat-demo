"""Robot Framework library: VSX keywords."""

import urllib.parse

from robot.api import logger

import _aoscx


class CXLibraryVSX:
    ROBOT_LIBRARY_SCOPE = "SUITE"

    def _vsx(self, device_ip):
        """Cached accessor for /system/vsx?depth=2."""
        return _aoscx.cached_get(device_ip, "/system/vsx?depth=2")

    @staticmethod
    def _ref_name(ref):
        """Extract a resource name from an AOS-CX reference field.

        A reference at depth=2 may arrive as a bare URI string
        (``/rest/v10.16/system/interfaces/lag256``), a ``{name: uri}``
        dict, or an expanded object carrying its own ``name`` field.
        Returns the decoded resource name, or None if it cannot be
        determined.
        """
        if not ref:
            return None
        if isinstance(ref, str):
            seg = ref.rstrip("/").split("/")[-1]
            return urllib.parse.unquote(seg)
        if isinstance(ref, dict):
            name = ref.get("name")
            if isinstance(name, str):
                return name
            for key in ref:
                seg = key.rstrip("/").split("/")[-1]
                return urllib.parse.unquote(seg)
        return None

    def vsx_peers_should_be_in_sync(self, device_ip):
        """Verify the VSX ISL is operational and the peer is established and config-synced.

        Args:
            device_ip: Switch management IP.

        Reads /system/vsx?depth=2 (cached) and asserts the following
        five fields together:
          * oper_status.isl_mgmt_state == "operational"
          * oper_status.islp_device_state == "peer_established"
          * oper_status.islp_link_state == "in_sync"
          * oper_status.config_sync_state == "in-sync"
            (note the dash, vs. the underscore in islp_link_state —
            both spellings are used by AOS-CX in different fields)
          * peer_status.peer_ready is true
        Together these mean the ISL is healthy AND the peer agrees
        on config. Any subset of failures is collected and raised
        together so the operator sees the full picture.
        """
        vsx = self._vsx(device_ip)
        oper = vsx.get("oper_status") or {}
        peer = vsx.get("peer_status") or {}

        checks = {
            "isl_mgmt_state": (oper.get("isl_mgmt_state"), "operational"),
            "islp_device_state": (oper.get("islp_device_state"), "peer_established"),
            "islp_link_state": (oper.get("islp_link_state"), "in_sync"),
            "config_sync_state": (oper.get("config_sync_state"), "in-sync"),
            "peer_ready": (peer.get("peer_ready"), True),
        }
        failures = []
        for field, (actual, expected) in checks.items():
            if actual != expected:
                logger.warn(f"{device_ip}: VSX {field} {actual!r} (expected {expected!r})")
                failures.append(f"{field}={actual!r} (expected {expected!r})")
            else:
                logger.info(f"{device_ip}: VSX {field} ok ({actual!r})")
        if failures:
            raise AssertionError(
                f"{device_ip}: {len(failures)} of {len(checks)} VSX status checks failed"
            )

    def vsx_keepalive_should_be_established(self, device_ip):
        """Verify the VSX keepalive state is in_sync_established.

        Args:
            device_ip: Switch management IP.

        Reads keepalive_status.state from /system/vsx?depth=2 (via
        self._vsx) and asserts it equals "in_sync_established". The
        keepalive runs over the management network as a separate
        liveness signal from the ISL — both must be healthy for the
        VSX pair to know whether a peer is genuinely down vs. just
        partitioned.
        """
        vsx = self._vsx(device_ip)
        ka_status = vsx.get("keepalive_status") or {}
        state = ka_status.get("state", "unknown")
        logger.info(f"{device_ip}: VSX keepalive_status.state = {state!r}")
        if state != "in_sync_established":
            raise AssertionError(
                f"{device_ip}: VSX keepalive_status.state is {state!r}, expected 'in_sync_established'"
            )

    def vsx_firmware_should_match(self, device_ip):
        """Verify both VSX peers are running the same software version.

        Args:
            device_ip: Switch management IP.

        Reads software_version from /system?depth=2 (this device) and
        peer_sw_version from /system/vsx?depth=2 (the peer's
        version, as reported back over the ISL) and asserts equality.
        Mismatched firmware between peers is a known cause of
        intermittent VSX issues — they must be upgraded in lockstep.
        """
        local_version = _aoscx.system(device_ip).get("software_version", "unknown")
        peer_version = self._vsx(device_ip).get("peer_sw_version", "unknown")
        logger.info(
            f"{device_ip}: local software_version={local_version!r}, peer_sw_version={peer_version!r}"
        )
        if local_version != peer_version:
            raise AssertionError(
                f"{device_ip}: VSX firmware mismatch — local={local_version!r}, peer={peer_version!r}"
            )

    def log_vsx_related_config(self, device_ip):
        """Log VSX-adjacent config for troubleshooting — diagnostic only, no assertions.

        Args:
            device_ip: Switch management IP.

        Reads /system/vsx?depth=2 and cross-references the config a VSX
        problem usually depends on but which the assertion keywords do
        not surface:
          * the keepalive VRF (``keepalive_vrf``) — fetched so its state
            lands in the log.
          * the interface carrying the keepalive — located by matching
            ``keepalive_src_ip`` against every interface's ``ip4_address``,
            so the port is found without hardcoding it.
          * the ISL LAG (``isl_port``) and the admin/link state of each
            of its member ports.
        Everything is emitted via logger so it appears in log.html.
        Intended as a Test Teardown: the context is then present whether
        or not the assertions passed, and the response cache makes the
        extra reads almost free.
        """
        vsx = self._vsx(device_ip)

        ka_vrf = self._ref_name(vsx.get("keepalive_vrf"))
        if ka_vrf:
            try:
                vrf_obj = _aoscx.vrf(device_ip, ka_vrf)
                logger.info(
                    f"{device_ip}: VSX keepalive VRF {ka_vrf!r} fetched "
                    f"(fields: {sorted(vrf_obj.keys())})"
                )
            except Exception as exc:
                logger.warn(f"{device_ip}: could not fetch keepalive VRF {ka_vrf!r}: {exc}")
        else:
            logger.warn(f"{device_ip}: VSX object has no keepalive_vrf reference")

        src_ip = vsx.get("keepalive_src_ip")
        if src_ip:
            match = None
            for name, data in _aoscx.interfaces(device_ip).items():
                ip4 = data.get("ip4_address")
                if isinstance(ip4, str) and ip4.split("/")[0] == src_ip:
                    match = (name, data)
                    break
            if match:
                name, data = match
                logger.info(
                    f"{device_ip}: VSX keepalive source {src_ip} is on interface {name} "
                    f"(admin_state={data.get('admin_state')!r} "
                    f"link_state={data.get('link_state')!r} "
                    f"vrf={self._ref_name(data.get('vrf'))!r})"
                )
            else:
                logger.warn(
                    f"{device_ip}: no interface found carrying keepalive source IP {src_ip}"
                )
        else:
            logger.warn(f"{device_ip}: VSX object has no keepalive_src_ip")

        isl = self._ref_name(vsx.get("isl_port"))
        if isl:
            members = _aoscx.lag_members(device_ip, isl)
            logger.info(
                f"{device_ip}: VSX ISL is {isl} with member(s): "
                f"{', '.join(members) or '(none)'}"
            )
            for port in members:
                encoded = port.replace("/", "%2F")
                try:
                    pdata = _aoscx.cached_get(
                        device_ip, f"/system/interfaces/{encoded}?depth=2"
                    )
                    logger.info(
                        f"{device_ip}: ISL member {port} — "
                        f"admin_state={pdata.get('admin_state')!r} "
                        f"link_state={pdata.get('link_state')!r}"
                    )
                except Exception as exc:
                    logger.warn(f"{device_ip}: could not fetch ISL member {port}: {exc}")
        else:
            logger.warn(f"{device_ip}: VSX object has no isl_port reference")
