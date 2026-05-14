*** Settings ***
Documentation       Syslog configuration and event log health tests

Library             ../libraries/CXLibraryBase.py
Library             ../libraries/CXLibraryLogging.py

Suite Setup         Connect To Device    ${DEVICE_IP}    api_version=${API_VERSION}
Suite Teardown      Disconnect From Device


*** Test Cases ***
Syslog Configured
    [Documentation]    The expected syslog server is configured, enabled, and bound to the management VRF.
    [Tags]
    ...    core
    ...    access
    Syslog Should Be Configured    ${DEVICE_IP}
    ...    management_vrf=${MANAGEMENT_VRF}
    ...    syslog_server=${SYSLOG_SERVER}
