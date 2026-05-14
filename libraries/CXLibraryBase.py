"""
Robot Framework library: connection lifecycle for AOS-CX devices.

Exposes two keywords — ``Connect To Device`` and ``Disconnect From
Device`` — that other AOS-CX domain libraries rely on for an active
session. All shared state (open connections, response cache) lives in
the module-level singleton in ``_aoscx``, so any domain library
imported in the same process automatically sees the connection without
having to do its own library lookup.
"""

import _aoscx


class CXLibraryBase:
    """Connection lifecycle keywords."""

    ROBOT_LIBRARY_SCOPE = "SUITE"

    def connect_to_device(self, device_ip, api_version, port="443"):
        """Open an authenticated REST session to an AOS-CX switch.

        Args:
            device_ip: Switch management IP.
            api_version: AOS-CX REST API version segment (e.g. ``v10.16``).
                Sourced from ``${API_VERSION}`` (site.yaml's ``api_version``).
            port: HTTPS port (default ``443``).

        Reads ``CX_USERNAME`` / ``CX_PASSWORD`` from the environment and
        registers the new session in ``_aoscx``'s module-level connection
        dict.
        """
        _aoscx.connect(device_ip, api_version, port)

    def disconnect_from_device(self, device_ip=None):
        """Log out and release the REST session for one device, or all of them.

        Args:
            device_ip: Switch management IP to disconnect. When ``None``
                (the default), every active connection is closed.
        """
        _aoscx.disconnect(device_ip)
