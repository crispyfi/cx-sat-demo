*** Settings ***
Documentation       Management plane access tests (SSH, HTTPS, OOB)

Library             ../libraries/CXLibraryBase.py
Library             ../libraries/CXLibraryManagement.py

Suite Setup         Connect To Device    ${DEVICE_IP}    api_version=${API_VERSION}
Suite Teardown      Disconnect From Device


*** Test Cases ***
SSH Enabled On Management VRF
    [Documentation]    SSH is enabled on the management VRF.
    [Tags]
    ...    core
    ...    access
    SSH Should Be Enabled On Management VRF    ${DEVICE_IP}
    ...    management_vrf=${MANAGEMENT_VRF}

HTTPS Enabled On Management VRF
    [Documentation]    HTTPS is enabled on the management VRF.
    [Tags]
    ...    core
    ...    access
    HTTPS Should Be Enabled On Management VRF    ${DEVICE_IP}
    ...    management_vrf=${MANAGEMENT_VRF}

Loopback0 In MANAGEMENT VRF
    [Documentation]    loopback0 is bound to the MANAGEMENT VRF.
    [Tags]
    ...    core
    Loopback0 Should Be In Management VRF    ${DEVICE_IP}
    ...    management_vrf=${MANAGEMENT_VRF}

Source Interface Is Loopback0
    [Documentation]    loopback0 is the source interface for outbound services (RADIUS, TACACS, SNMP, syslog, NTP).
    [Tags]
    ...    core
    Source Interface Should Be Loopback0    ${DEVICE_IP}

Device Connected To Central
    [Documentation]    Device reports an active connection to HPE Aruba Networking Central.
    [Tags]
    ...    core
    ...    access
    Central Should Be Connected    ${DEVICE_IP}
    ...    management_vrf=${MANAGEMENT_VRF}

Configuration Lockout Managed By Central
    [Documentation]    Central-managed configuration lockout is enabled, blocking local config changes.
    [Tags]
    ...    core
    ...    access
    Configuration Lockout Should Be Central    ${DEVICE_IP}
