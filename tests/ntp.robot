*** Settings ***
Name                NTP
Documentation       Timezone and NTP synchronisation tests

Library             ../libraries/CXLibraryBase.py
Library             ../libraries/CXLibraryNTP.py

Suite Setup         Connect To Device    ${DEVICE_IP}    api_version=${API_VERSION}
Suite Teardown      Disconnect From Device


*** Test Cases ***
Timezone Configured
    [Documentation]    The device timezone is set to the desired timezone.
    [Tags]
    ...    core
    ...    access
    Timezone Should Be    ${DEVICE_IP}
    ...    timezone=${TIMEZONE}

NTP Synced To Expected Servers
    [Documentation]    The device is synchronised to the design NTP servers.
    [Tags]
    ...    core
    ...    access
    NTP Should Be Synced To    ${DEVICE_IP}
    ...    expected_servers=${NTP_SERVERS}
