"""Robot Framework library: Spanning Tree keywords."""

from robot.api import logger

import _aoscx


class CXLibrarySpanningTree:
    ROBOT_LIBRARY_SCOPE = "SUITE"

    def mstp_configuration_should_be_consistent(self, device_ip, site_name, mstp_config_digest):
        """Verify STP is enabled in MSTP mode with the expected region, revision, and digest.

        Args:
            device_ip: Switch management IP.
            site_name: Expected mstp_config_name — this environment
                uses the site name (${SITE_NAME}) as the MST region
                name so all switches in a site share a region.
            mstp_config_digest: Expected mstp_config_digest. Computed
                from the VLAN-to-instance mapping by the design tool
                and supplied via the test runner. Fails if not
                provided.

        Reads /system?depth=2 (via _aoscx.system) and asserts:
          * stp_config.stp_enable is true
          * stp_config.stp_mode == "mstp"
          * stp_config.mstp_config_name == site_name
          * stp_config.mstp_config_revision == 0
          * stp_status.mstp_config_digest == mstp_config_digest
        All failures are collected and raised together.
        """
        if site_name is None:
            raise AssertionError(f"{device_ip}: site_name not provided")
        if mstp_config_digest is None:
            raise AssertionError(f"{device_ip}: mstp_config_digest not provided")
        sys_data = _aoscx.system(device_ip)
        stp_config = sys_data.get("stp_config") or {}
        stp_status = sys_data.get("stp_status") or {}
        failures = []
        if not stp_config.get("stp_enable"):
            failures.append("stp_config.stp_enable is not true")
        mode = stp_config.get("stp_mode", "")
        if mode != "mstp":
            failures.append(f"stp_config.stp_mode is {mode!r} (expected 'mstp')")
        name = stp_config.get("mstp_config_name", "")
        if name != site_name:
            failures.append(f"stp_config.mstp_config_name is {name!r} (expected {site_name!r})")
        revision = stp_config.get("mstp_config_revision")
        if revision != 0:
            failures.append(f"stp_config.mstp_config_revision is {revision!r} (expected 0)")
        digest = stp_status.get("mstp_config_digest", "")
        if digest != mstp_config_digest:
            failures.append(
                f"stp_status.mstp_config_digest is {digest!r} (expected {mstp_config_digest!r})"
            )
        logger.info(
            f"{device_ip}: stp_enable={stp_config.get('stp_enable')} stp_mode={stp_config.get('stp_mode')!r} name={stp_config.get('mstp_config_name')!r} revision={stp_config.get('mstp_config_revision')} digest={stp_status.get('mstp_config_digest')}"
        )
        if failures:
            raise AssertionError(f"{device_ip}: MSTP config issues: {'; '.join(failures)}")

    def stp_root_should_match(self, device_ip, mstp_root_instances):
        """Verify this device is MST root for the expected set of instances.

        Args:
            device_ip: Switch management IP.
            mstp_root_instances: List of MST instance numbers this device
                should be root for (${MSTP_ROOT_INSTANCES}). Fails if
                not provided.

        For each instance in _aoscx.stp_instances:
          * Detects "is root" by root_port == "0" (the magic value
            AOS-CX uses to mean "I am the root").
          * Reports both "should be root but isn't" and "should not
            be root but is" failures.
        All instance-level failures are collected and raised
        together.
        """
        if mstp_root_instances is None:
            raise AssertionError(f"{device_ip}: mstp_root_instances not provided")
        expected_root = {int(i) for i in mstp_root_instances}
        instances = _aoscx.stp_instances(device_ip)
        failures = []
        for inst_key, inst_data in instances.items():
            try:
                inst_num = int(inst_key.split(",")[1])
            except (IndexError, ValueError):
                continue
            is_root = str(inst_data.get("root_port", "")) == "0"
            should_be_root = inst_num in expected_root
            logger.info(
                f"{device_ip}: instance {inst_num} should_be_root={should_be_root} is_root={is_root}"
            )
            if should_be_root and not is_root:
                root_port = inst_data.get("root_port")
                failures.append(f"instance {inst_num}: expected root but root_port={root_port!r}")
            elif not should_be_root and is_root:
                failures.append(f"instance {inst_num}: not expected to be root but root_port=0")
        if failures:
            raise AssertionError(f"{device_ip}: MST root mismatch: {'; '.join(failures)}")

    def stp_edge_port_guards_should_be_configured(self, device_ip):
        """Verify BPDU guard, TCN guard, and admin edge are enabled on access edge ports.

        Args:
            device_ip: Switch management IP.

        For each non-pluggable (client-facing) physical port, asserts the
        three flags (bpdu_guard_enable, restricted_port_tcn_disable —
        AOS-CX's name for TCN guard, admin_edge_port_enable) are all
        truthy. All findings are collected and raised together.
        """
        interfaces = _aoscx.interfaces(device_ip)
        problems = []
        for name, data in sorted(interfaces.items(), key=lambda x: _aoscx.interface_sort_key(x[0])):
            if not _aoscx.is_physical(name):
                continue
            if _aoscx.is_pluggable(data):
                continue
            stp = data.get("stp_config") or {}
            intf_problems = []
            if not stp.get("bpdu_guard_enable"):
                intf_problems.append("bpdu_guard_enable not set")
            if not stp.get("restricted_port_tcn_disable"):
                intf_problems.append("restricted_port_tcn_disable not set")
            if not stp.get("admin_edge_port_enable"):
                intf_problems.append("admin_edge_port_enable not set")
            if intf_problems:
                logger.warn(f"{device_ip}: {name} {'; '.join(intf_problems)}")
                problems.extend(f"{name}: {p}" for p in intf_problems)
            else:
                logger.info(
                    f"{device_ip}: {name} ok (bpdu_guard={stp.get('bpdu_guard_enable')} tcn_guard={stp.get('restricted_port_tcn_disable')} edge={stp.get('admin_edge_port_enable')})"
                )
        if problems:
            bad_ports = len({p.split(":")[0] for p in problems})
            raise AssertionError(f"{device_ip}: {bad_ports} edge port(s) missing STP guards")

    def no_stp_inconsistent_ports(self, device_ip):
        """Verify no spanning-tree port reports any inconsistency flag.

        Args:
            device_ip: Switch management IP.

        For each MST instance in _aoscx.stp_instances, fetches
        /system/stp_instances/<type>/<num>/stp_instance_ports?depth=2
        (the instance key "mstp,0" is split into two path segments). For each
        port, walks port_inconsistent and collects any sub-key
        whose value is truthy. All inconsistencies across all
        instances and ports are reported together — the message
        identifies the (instance, port, check) triple.
        """
        instances = _aoscx.stp_instances(device_ip)
        problems = []
        for inst_key in instances:
            if "," not in inst_key:
                continue
            ports = _aoscx.cached_get(
                device_ip,
                f"/system/stp_instances/{inst_key}/stp_instance_ports?depth=2",
            )
            for port_name, port_data in sorted(
                ports.items(), key=lambda x: _aoscx.interface_sort_key(x[0])
            ):
                inconsistent = port_data.get("port_inconsistent") or {}
                port_problems = [
                    f"{check}={value!r}" for check, value in inconsistent.items() if value
                ]
                label = f"{inst_key},{port_name}"
                if port_problems:
                    logger.warn(f"{device_ip}: {label} {'; '.join(port_problems)}")
                    problems.extend(f"{label}: {p}" for p in port_problems)
                else:
                    logger.info(f"{device_ip}: {label} ok")
        if problems:
            raise AssertionError(f"{device_ip}: {len(problems)} STP inconsistency flag(s) found")
