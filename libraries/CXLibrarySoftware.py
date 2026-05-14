"""Robot Framework library: Software keywords."""

from robot.api import logger

import _aoscx


class CXLibrarySoftware:
    ROBOT_LIBRARY_SCOPE = "SUITE"

    def software_version_should_match(self, device_ip, expected_version):
        """Verify the running AOS-CX version matches the design's expected version.

        Args:
            device_ip: Switch management IP.
            expected_version: Expected software_version string
                (${EXPECTED_SW_VERSION}). Fails if not provided.

        Reads software_version from /system?depth=2 (via _aoscx.system).
        Strips the platform prefix (e.g. "FL." or "GL.") before comparing,
        so the design input need only specify the numeric portion (e.g. "10.16.1030").
        """
        if expected_version is None:
            raise AssertionError(f"{device_ip}: expected_version not provided")
        sys = _aoscx.system(device_ip)
        version = sys.get("software_version", "")
        normalized = version.split(".", 1)[-1] if "." in version else version
        logger.info(
            f"{device_ip}: software_version={version} (normalized={normalized} expected={expected_version})"
        )
        if normalized != expected_version:
            raise AssertionError(
                f"{device_ip}: software_version is {version!r} (normalized {normalized!r}), expected {expected_version!r}"
            )

    def no_unsafe_software_updates(self, device_ip, vsf_members=None):
        """Verify no pending non-failsafe software updates exist on any ISP image.

        Args:
            device_ip: Switch management IP.
            vsf_members: VSF stack member count (${VSF_MEMBERS}). When
                provided, limits inspection to the first ``int(vsf_members)``
                management modules (sorted numerically). Required for
                access stacks — /system/subsystems always returns all 10
                slots regardless of actual stack size.

        Reads /system/subsystems?depth=2 (cached) and filters entries
        whose key starts with "management_module,". For each found
        management module, inspects isp_needed_updates_<slot>
        .non_failsafe_update_count for the current, primary, and
        secondary ISP image slots. All non-zero counts are reported
        together. Non-failsafe updates would risk bricking the box if
        applied without coordination — the test forces awareness before
        any unattended upgrade. Fails immediately if no management
        module is found in the subsystem list.
        """
        subsystems = _aoscx.cached_get(device_ip, "/system/subsystems?depth=2") or {}
        all_modules = {k: v for k, v in subsystems.items() if k.startswith("management_module,")}
        if vsf_members is not None:
            sorted_keys = sorted(all_modules, key=_aoscx.subsystem_sort_key)[: int(vsf_members)]
            mgmt_modules = {k: all_modules[k] for k in sorted_keys}
        else:
            mgmt_modules = all_modules
        if not mgmt_modules:
            raise AssertionError(f"{device_ip}: no management_module found in /system/subsystems")
        total = 0
        for module_key, mgmt in sorted(
            mgmt_modules.items(), key=lambda x: _aoscx.subsystem_sort_key(x[0])
        ):
            for slot in (
                "isp_needed_updates_current",
                "isp_needed_updates_primary",
                "isp_needed_updates_secondary",
            ):
                count = (mgmt.get(slot) or {}).get("non_failsafe_update_count", 0)
                if count != 0:
                    logger.warn(
                        f"{device_ip}: {module_key} {slot} non_failsafe_update_count={count}"
                    )
                    total += count
                else:
                    logger.info(f"{device_ip}: {module_key} {slot} non_failsafe_update_count=0 ok")
        if total:
            raise AssertionError(f"{device_ip}: {total} non-failsafe updates pending")
