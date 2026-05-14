*** Settings ***
Name                VSF
Documentation       VSF stack configuration and operational state tests

Library             ../libraries/CXLibraryBase.py
Library             ../libraries/CXLibraryVSF.py

Suite Setup         Connect To Device    ${DEVICE_IP}    api_version=${API_VERSION}
Suite Teardown      Disconnect From Device


*** Test Cases ***
Split Detection Configured
    [Documentation]    VSF split detection is configured to use the management interface and no split is active.
    [Tags]
    ...    access
    VSF Split Detection Should Be Configured    ${DEVICE_IP}

Management Interface Up
    [Documentation]    The management interface (used for split detection) is admin and link up.
    [Tags]
    ...    access
    VSF Management Interface Should Be Up    ${DEVICE_IP}

Topology Is Ring
    [Documentation]    The active VSF topology is ring.
    [Tags]
    ...    access
    VSF Topology Should Be Ring    ${DEVICE_IP}

Member Count Matches Design
    [Documentation]    The VSF stack has exactly the expected number of members.
    [Tags]
    ...    access
    VSF Member Count Should Match    ${DEVICE_IP}
    ...    vsf_members=${VSF_MEMBERS}

All Members Ready And Links Up
    [Documentation]    Every VSF member is in ready state and has both inter-member links up.
    [Tags]
    ...    access
    All VSF Members And Links Should Be Healthy    ${DEVICE_IP}
    ...    vsf_members=${VSF_MEMBERS}

Member 1 Is Conductor
    [Documentation]    VSF member 1 holds the conductor role.
    [Tags]
    ...    access
    VSF Member Should Be Conductor    ${DEVICE_IP}    1

Member 2 Is Standby
    [Documentation]    VSF member 2 is the configured secondary and holds the standby role.
    [Tags]
    ...    access
    VSF Member Should Be Standby    ${DEVICE_IP}    2
