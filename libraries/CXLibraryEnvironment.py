"""Robot Framework library: Environment keywords."""

import urllib.parse

from robot.api import logger

import _aoscx


class CXLibraryEnvironment:
    ROBOT_LIBRARY_SCOPE = "SUITE"

    def cpu_utilization_should_be_below(self, device_ip, threshold, vsf_members=None):
        """Verify every management module reports CPU utilization below threshold.

        Args:
            device_ip: Switch management IP.
            threshold: Maximum acceptable CPU utilization percent
                (${CPU_THRESHOLD}). Accepts ints or numeric strings.
            vsf_members: VSF stack member count (${VSF_MEMBERS}). When
                provided, limits inspection to the first ``int(vsf_members)``
                management_module entries (sorted numerically by slot), since
                the API always returns all 10 slots regardless of stack size.

        Filters _aoscx.subsystems to management_module entries, optionally
        slicing to vsf_members slots. Inspects each module's
        resource_utilization.cpu and collects any reporting cpu >= threshold.
        All failures are reported together together.
        Fails immediately if no management_module entries exist.
        """
        threshold = int(threshold)
        subsystems = _aoscx.subsystems(device_ip)
        modules = {k: v for k, v in subsystems.items() if k.startswith("management_module,")}
        if not modules:
            raise AssertionError(f"{device_ip}: no management_module entries found in subsystems")
        if vsf_members is not None:
            keys = sorted(modules, key=_aoscx.subsystem_sort_key)[: int(vsf_members)]
            modules = {k: modules[k] for k in keys}
        bad = []
        for mod_key, mod in modules.items():
            cpu = mod.get("resource_utilization", {}).get("cpu")
            if cpu is not None and float(cpu) >= threshold:
                logger.warn(
                    f"{device_ip}: {mod_key} cpu={float(cpu):.1f}% (threshold {threshold}%)"
                )
                bad.append(f"{mod_key}={float(cpu):.1f}%")
            else:
                logger.info(f"{device_ip}: {mod_key} cpu={cpu}% (threshold {threshold}%)")
        if bad:
            raise AssertionError(
                f"{device_ip}: {len(bad)} management module(s) with CPU above {threshold}%"
            )

    def memory_utilization_should_be_below(self, device_ip, threshold, vsf_members=None):
        """Verify every management module reports memory utilization below threshold.

        Args:
            device_ip: Switch management IP.
            threshold: Maximum acceptable memory utilization percent
                (${MEMORY_THRESHOLD}). Accepts ints or numeric strings.
            vsf_members: VSF stack member count (${VSF_MEMBERS}). When
                provided, limits inspection to the first ``int(vsf_members)``
                management_module entries (sorted numerically by slot), since
                the API always returns all 10 slots regardless of stack size.

        Filters _aoscx.subsystems to management_module entries, optionally
        slicing to vsf_members slots. Inspects each module's
        resource_utilization.memory and collects any reporting memory >=
        threshold. All failures are reported together via
        together. Fails immediately if no management_module entries exist.
        """
        threshold = int(threshold)
        subsystems = _aoscx.subsystems(device_ip)
        modules = {k: v for k, v in subsystems.items() if k.startswith("management_module,")}
        if not modules:
            raise AssertionError(f"{device_ip}: no management_module entries found in subsystems")
        if vsf_members is not None:
            keys = sorted(modules, key=_aoscx.subsystem_sort_key)[: int(vsf_members)]
            modules = {k: modules[k] for k in keys}
        bad = []
        for mod_key, mod in modules.items():
            mem = mod.get("resource_utilization", {}).get("memory")
            if mem is not None and float(mem) >= threshold:
                logger.warn(
                    f"{device_ip}: {mod_key} memory={float(mem):.1f}% (threshold {threshold}%)"
                )
                bad.append(f"{mod_key}={float(mem):.1f}%")
            else:
                logger.info(f"{device_ip}: {mod_key} memory={mem}% (threshold {threshold}%)")
        if bad:
            raise AssertionError(
                f"{device_ip}: {len(bad)} management module(s) with memory above {threshold}%"
            )

    def all_power_supplies_should_be_ok(self, device_ip, vsf_members=None):
        """Verify every PSU slot is populated and reports no faults or warnings.

        Args:
            device_ip: Switch management IP.
            vsf_members: VSF stack member count (${VSF_MEMBERS}). When
                provided, limits inspection to the first ``int(vsf_members)``
                chassis entries (sorted numerically by slot), since the API
                always returns all 10 slots regardless of stack size.

        Iterates the relevant chassis entries in _aoscx.subsystems. For each
        chassis, reads capacities.psu_slots to learn how many PSUs are
        expected, then fetches /system/subsystems/<chassis>/power_supplies
        and asserts:
          * the number of PSUs returned equals psu_slots
          * every PSU has status in {"ok", "OK"}
        All issues are collected and raised together via
        together. Fails immediately if no chassis entries exist.
        """
        subsystems = _aoscx.subsystems(device_ip)
        chassis_keys = sorted(
            (k for k in subsystems if k.startswith("chassis,")),
            key=_aoscx.subsystem_sort_key,
        )
        if not chassis_keys:
            raise AssertionError(f"{device_ip}: no chassis entries found in subsystems")
        if vsf_members is not None:
            chassis_keys = chassis_keys[: int(vsf_members)]
        bad = []
        for chassis_key in chassis_keys:
            expected_slots = subsystems[chassis_key].get("capacities", {}).get("psu_slots", 0)
            psus = _aoscx.cached_get(
                device_ip,
                f"/system/subsystems/{chassis_key}/power_supplies?depth=2",
            )
            actual = len(psus) if psus else 0
            if actual != expected_slots:
                logger.warn(
                    f"{device_ip}: {chassis_key} PSU count={actual} (expected {expected_slots})"
                )
                bad.append(f"{chassis_key}: expected {expected_slots} PSU(s), found {actual}")
            for psu_key, psu in (psus or {}).items():
                name = psu.get("name", psu_key)
                status = psu.get("status", "unknown")
                if status in ("ok", "OK"):
                    logger.info(f"{device_ip}: {chassis_key} PSU {name} status={status}")
                else:
                    logger.warn(f"{device_ip}: {chassis_key} PSU {name} status={status}")
                    bad.append(f"{chassis_key} PSU {name}: status={status}")
        if bad:
            raise AssertionError(f"{device_ip}: {len(bad)} PSU issue(s) found")

    def all_fans_should_be_ok(self, device_ip, vsf_members=None):
        """Verify every fan reports OK status.

        Args:
            device_ip: Switch management IP.
            vsf_members: VSF stack member count (${VSF_MEMBERS}). When
                provided, limits inspection to subsystem entries belonging
                to the first ``int(vsf_members)`` chassis members — identified
                by the leading number in the slot suffix (e.g. "2" in
                "fan_tray,2/1"). Required for VSF access stacks since the
                API always returns all 10 possible member slots regardless
                of stack size.

        Queries fans from every subsystem entry, deduplicating by fan name.
        This handles models where chassis, line_card, and management_module
        all report the same physical fans, as well as models where fan_tray
        entries hold tray fans and chassis holds PSU fans. Subsystems that
        return no fans are silently skipped. If no fans are found across
        any subsystem, logs an advisory and returns without failing —
        fanless platforms are valid. All status failures are collected and
        raised together together.
        """
        subsystems = _aoscx.subsystems(device_ip)
        if vsf_members is not None:
            n = int(vsf_members)
            filtered = {}
            for k, v in subsystems.items():
                _, _, suffix = k.rpartition(",")
                try:
                    member_num = int(suffix.split("/")[0])
                except ValueError:
                    filtered[k] = v
                    continue
                if member_num <= n:
                    filtered[k] = v
            subsystems = filtered
        all_fans = {}
        for sub_key in sorted(subsystems):
            encoded = urllib.parse.quote(sub_key, safe=",")
            fans = _aoscx.cached_get(device_ip, f"/system/subsystems/{encoded}/fans?depth=2")
            for fan_key, fan in (fans or {}).items():
                name = fan.get("name", fan_key)
                if name not in all_fans:
                    all_fans[name] = fan
        if not all_fans:
            logger.info(f"{device_ip}: no fans reported across any subsystem — skipping")
            return
        bad = []
        for name, fan in sorted(all_fans.items()):
            status = fan.get("status", "unknown")
            if status in ("ok", "OK"):
                logger.info(
                    f"{device_ip}: fan {name} status={status} speed={fan.get('speed')} rpm={fan.get('rpm')}"
                )
            else:
                logger.warn(f"{device_ip}: fan {name} status={status}")
                bad.append(f"fan {name}: status={status}")
        if bad:
            raise AssertionError(f"{device_ip}: {len(bad)} fan(s) with non-OK status")

    def all_thermal_states_should_be_safe(self, device_ip, vsf_members=None):
        """Verify every subsystem that reports a thermal_state reports safe.

        Args:
            device_ip: Switch management IP.
            vsf_members: VSF stack member count (${VSF_MEMBERS}). When
                provided, limits inspection to entries belonging to the first
                ``int(vsf_members)`` chassis members — identified by the
                leading number in the slot suffix (e.g. "1" in "fan_tray,1/2").

        Iterates all entries in _aoscx.subsystems. Entries whose
        thermal_state is None (absent or JSON null) are skipped — some
        models do not report thermal_state on line cards or fan trays.
        Any entry reporting a value other than "safe" is a failure. All
        failures are reported together together.
        """
        subsystems = _aoscx.subsystems(device_ip)
        if not subsystems:
            raise AssertionError(f"{device_ip}: no subsystem entries found")
        if vsf_members is not None:
            n = int(vsf_members)
            filtered = {}
            for k, v in subsystems.items():
                _, _, suffix = k.rpartition(",")
                try:
                    member_num = int(suffix.split("/")[0])
                except ValueError:
                    filtered[k] = v
                    continue
                if member_num <= n:
                    filtered[k] = v
            subsystems = filtered
        bad = []
        for key, entry in sorted(subsystems.items()):
            state = entry.get("thermal_state")
            if state is None:
                logger.info(f"{device_ip}: {key} thermal_state=null — skipping")
                continue
            if state == "safe":
                logger.info(f"{device_ip}: {key} thermal_state={state}")
            else:
                logger.warn(f"{device_ip}: {key} thermal_state={state}")
                bad.append(f"{key}: thermal_state={state}")
        if bad:
            raise AssertionError(f"{device_ip}: {len(bad)} subsystem(s) with unsafe thermal state")
