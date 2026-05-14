*** Settings ***
Documentation       Security hardening tests

Library             ../libraries/CXLibraryBase.py
Library             ../libraries/CXLibraryHardening.py

Suite Setup         Connect To Device    ${DEVICE_IP}    api_version=${API_VERSION}
Suite Teardown      Disconnect From Device


*** Test Cases ***
USB Disabled
    [Documentation]    The USB port is disabled.
    [Tags]
    ...    core
    ...    access
    USB Should Be Disabled    ${DEVICE_IP}

Bluetooth Disabled
    [Documentation]    Bluetooth management is disabled.
    [Tags]
    ...    core
    ...    access
    Bluetooth Should Be Disabled    ${DEVICE_IP}

Telnet Server Disabled
    [Documentation]    The Telnet server is disabled on the management VRF.
    [Tags]
    ...    core
    ...    access
    Telnet Server Should Be Disabled    ${DEVICE_IP}
    ...    management_vrf=${MANAGEMENT_VRF}

ICMP Redirects Disabled
    [Documentation]    ICMP redirect messages are disabled system-wide.
    [Tags]
    ...    core
    ...    access
    ICMP Redirects Should Be Disabled    ${DEVICE_IP}

Login Banner Configured
    [Documentation]    A login banner is configured starting with the expected unauthorised-access warning.
    [Tags]
    ...    core
    ...    access
    Login Banner Should Be Configured    ${DEVICE_IP}
    ...    banner_prefix=${LOGIN_BANNER_PREFIX}

Control Plane ACL Applied
    [Documentation]    The CONTROLPLANE IPv4 ACL is applied to the control plane.
    [Tags]
    ...    core
    ...    access
    Control Plane ACL Should Be Applied    ${DEVICE_IP}
    ...    acl_name=${CONTROLPLANE_ACL_NAME}
    ...    management_vrf=${MANAGEMENT_VRF}

ARP Protection On All VLANs
    [Documentation]    Dynamic ARP inspection is enabled on every VLAN.
    [Tags]
    ...    access
    ARP Protection Should Be On All Vlans    ${DEVICE_IP}

DHCP Snooping On All VLANs
    [Documentation]    DHCP snooping is enabled on every VLAN.
    [Tags]
    ...    access
    DHCP Snooping Should Be On All Vlans    ${DEVICE_IP}

DHCP Snooping Trusted Port Configured
    [Documentation]    The upstream uplink port is configured as a DHCP snooping trusted port.
    [Tags]
    ...    access
    DHCP Snooping Trusted Port Should Be Configured    ${DEVICE_IP}
    ...    trusted_port=${UPLINK_LAG}

Loop Protection On All Edge Ports
    [Documentation]    Loop protection is enabled on every edge port.
    [Tags]
    ...    access
    Loop Protection Should Be On Edge Ports    ${DEVICE_IP}
