"""Robot Framework library: VSF keywords."""

from robot.api import logger

import _aoscx


class CXLibraryVSF:
    ROBOT_LIBRARY_SCOPE = "SUITE"

    def vsf_split_detection_should_be_configured(self, device_ip):
        """Verify VSF split detection is configured via the management interface and no split is active.

        Args:
            device_ip: Switch management IP.

        Reads vsf_config.split_detection_method and
        vsf_status.stack_split_state from /system?depth=2 (via
        _aoscx.system) and asserts:
          * split_detection_method == "mgmt" (the OOB mgmt interface
            is the keepalive path so a data-plane split can be
            distinguished from a real partition)
          * stack_split_state == "no_split"
        Both checks are collected and raised together.
        """
        sys_data = _aoscx.system(device_ip)
        vsf_config = sys_data.get("vsf_config") or {}
        vsf_status = sys_data.get("vsf_status") or {}
        method = vsf_config.get("split_detection_method", "unknown")
        split_state = vsf_status.get("stack_split_state", "unknown")
        logger.info(
            f"{device_ip}: VSF split_detection_method={method} stack_split_state={split_state}"
        )
        failures = []
        if method != "mgmt":
            failures.append(f"split_detection_method is {method!r}, expected 'mgmt'")
        if split_state != "no_split":
            failures.append(f"stack_split_state is {split_state!r}, expected 'no_split'")
        if failures:
            raise AssertionError(f"{device_ip}: failures: {'; '.join(failures)}")

    def vsf_management_interface_should_be_up(self, device_ip):
        """Verify the management interface (the split-detection path) is admin and link up.

        Args:
            device_ip: Switch management IP.

        Reads mgmt_intf.admin_state and mgmt_intf_status.link_state
        from /system?depth=2 (via _aoscx.system) and asserts both are
        "up". Both checks are collected and raised together. Note
        this is the *opposite* requirement to the OOB-disabled check
        in management.robot — for VSF stacks, the OOB interface is
        deliberately used as the split-detection keepalive.
        """
        sys_data = _aoscx.system(device_ip)
        admin_state = (sys_data.get("mgmt_intf") or {}).get("admin_state", "unknown")
        link_state = (sys_data.get("mgmt_intf_status") or {}).get("link_state", "unknown")
        logger.info(f"{device_ip}: mgmt_intf admin_state={admin_state} link_state={link_state}")
        failures = []
        if admin_state != "up":
            failures.append(f"admin_state is {admin_state!r}, expected 'up'")
        if link_state != "up":
            failures.append(f"link_state is {link_state!r}, expected 'up'")
        if failures:
            raise AssertionError(
                f"{device_ip}: management interface failures: {'; '.join(failures)}"
            )

    def vsf_topology_should_be_ring(self, device_ip):
        """Verify the active VSF topology type is "ring".

        Args:
            device_ip: Switch management IP.

        Reads /system/vsf_topologies?depth=2 (cached) and filters to
        topologies with active true. Asserts at least one active
        topology exists and that every active topology has type
        "ring". Ring is this environment's design choice; chain
        topologies pass two-member stacks but lose redundancy.
        """
        topos = _aoscx.cached_get(device_ip, "/system/vsf_topologies?depth=2")
        active = {tid: t for tid, t in topos.items() if t.get("active")}
        if not active:
            raise AssertionError(f"{device_ip}: no active VSF topology found")
        failures = []
        for topo_id, topo in active.items():
            topo_type = topo.get("type", "unknown")
            logger.info(f"{device_ip}: VSF topology {topo_id} type={topo_type}")
            if topo_type != "ring":
                failures.append(f"topology {topo_id} type is {topo_type!r}, expected 'ring'")
        if failures:
            raise AssertionError(f"{device_ip}: failures: {'; '.join(failures)}")

    def vsf_member_count_should_match(self, device_ip, vsf_members):
        """Verify the VSF stack has exactly the expected number of members.

        Args:
            device_ip: Switch management IP.
            vsf_members: Expected VSF member count (${VSF_MEMBERS}).
                Fails if not provided.

        Reads /system/vsf_members?depth=2 (cached) and asserts the
        entry count equals vsf_members. Catches both under- and
        over-membership (e.g. an unexpected switch joined the stack).
        """
        if vsf_members is None:
            raise AssertionError(f"{device_ip}: vsf_members not provided")
        members = _aoscx.cached_get(device_ip, "/system/vsf_members?depth=2")
        actual = len(members)
        expected = int(vsf_members)
        logger.info(f"{device_ip}: VSF member count actual={actual} expected={expected}")
        if actual != expected:
            raise AssertionError(f"{device_ip}: VSF member count is {actual}, expected {expected}")

    def all_vsf_members_and_links_should_be_healthy(self, device_ip, vsf_members):
        """Verify every VSF member is ready and has both inter-member links up.

        Args:
            device_ip: Switch management IP.
            vsf_members: Expected VSF member count (${VSF_MEMBERS}).
                Checks member IDs 1 through vsf_members. Fails if not
                provided.

        Reads /system/vsf_members?depth=2 (cached). For each expected
        member ID, asserts status == "ready", then fetches
        /system/vsf_members/<id>/links?depth=2 and asserts:
          * exactly 2 links exist (one to each neighbour in the ring
            topology)
          * every link's oper_status is "up"
        All findings across all members and links are collected and
        raised together.
        """
        if vsf_members is None:
            raise AssertionError(f"{device_ip}: vsf_members not provided")
        member_count = int(vsf_members)
        members = _aoscx.cached_get(device_ip, "/system/vsf_members?depth=2")
        failures = []
        for i in range(1, member_count + 1):
            member_id = str(i)
            member_data = members.get(member_id)
            if member_data is None:
                failures.append(f"member {member_id} not found")
                continue
            status = member_data.get("status", "unknown")
            logger.info(f"{device_ip}: VSF member {member_id} status={status}")
            if status != "ready":
                failures.append(f"member {member_id} status={status!r} (expected 'ready')")
            links = _aoscx.cached_get(
                device_ip,
                f"/system/vsf_members/{member_id}/links?depth=2",
            )
            if len(links) != 2:
                failures.append(f"member {member_id} has {len(links)} link(s), expected 2")
            for link_id, link_data in links.items():
                oper = link_data.get("oper_status", "unknown")
                logger.info(
                    f"{device_ip}: VSF member {member_id} link {link_id} oper_status={oper}"
                )
                if oper != "up":
                    failures.append(
                        f"member {member_id} link {link_id} oper_status={oper!r} (expected 'up')"
                    )
        if failures:
            raise AssertionError(f"{device_ip}: failures: {'; '.join(failures)}")

    def vsf_member_should_be_conductor(self, device_ip, member_id=1):
        """Verify the specified member currently holds the VSF conductor role.

        Args:
            device_ip: Switch management IP.
            member_id: VSF member number expected to be conductor
                (default 1, this environment's convention).

        Reads /system/vsf_members?depth=2 (cached) and asserts the
        named member exists and its role is "conductor". Fails
        immediately on either condition.
        """
        member_id_str = str(member_id)
        members = _aoscx.cached_get(device_ip, "/system/vsf_members?depth=2")
        member = members.get(member_id_str)
        active_role = (member or {}).get("role", "unknown")
        logger.info(f"{device_ip}: VSF member {member_id_str} role={active_role}")
        if member is None:
            raise AssertionError(
                f"{device_ip}: VSF member {member_id_str} not found in vsf_members"
            )
        if active_role != "conductor":
            raise AssertionError(
                f"{device_ip}: VSF member {member_id_str} role is {active_role!r}, expected 'conductor'"
            )

    def vsf_member_should_be_standby(self, device_ip, member_id=2):
        """Verify the specified member is the configured secondary and holds the standby role.

        Args:
            device_ip: Switch management IP.
            member_id: VSF member number expected to be standby
                (default 2, this environment's convention).

        Reads vsf_config.secondary_member from /system?depth=2 and
        the member entry from /system/vsf_members?depth=2 and
        asserts:
          * vsf_config.secondary_member == member_id
            (configuration intent)
          * the member's role is "standby" (operational state)
        Both checks are collected and raised together.
        """
        member_id_int = int(member_id)
        member_id_str = str(member_id)
        sys_data = _aoscx.system(device_ip)
        configured_secondary = (sys_data.get("vsf_config") or {}).get("secondary_member")
        members = _aoscx.cached_get(device_ip, "/system/vsf_members?depth=2")
        member = members.get(member_id_str)
        active_role = (member or {}).get("role", "unknown")
        logger.info(
            f"{device_ip}: VSF secondary_member={configured_secondary} member {member_id_str} role={active_role}"
        )
        failures = []
        if configured_secondary != member_id_int:
            failures.append(
                f"vsf_config.secondary_member is {configured_secondary!r}, expected {member_id_int}"
            )
        if member is None:
            failures.append(f"VSF member {member_id_str} not found in vsf_members")
        elif active_role != "standby":
            failures.append(f"member {member_id_str} role is {active_role!r}, expected 'standby'")
        if failures:
            raise AssertionError(f"{device_ip}: failures: {'; '.join(failures)}")
