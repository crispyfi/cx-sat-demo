*** Settings ***
Documentation       Interface configuration and operational state tests

Library             ../libraries/CXLibraryBase.py
Library             ../libraries/CXLibraryInterfaces.py

Suite Setup         Connect To Device    ${DEVICE_IP}    api_version=${API_VERSION}
Suite Teardown      Disconnect From Device


*** Test Cases ***
Physical Interface MTU Is 9198
    [Documentation]    Every physical interface has MTU 9198.
    [Tags]
    ...    core
    All Physical Interfaces MTU Should Be    ${DEVICE_IP}
    ...    expected_mtu=${PHYSICAL_MTU}

Uplink MTU Is 9198
    [Documentation]    Every member port of the uplink LAG has MTU 9198.
    [Tags]
    ...    access
    Physical Uplinks MTU Should Be    ${DEVICE_IP}
    ...    expected_mtu=${PHYSICAL_MTU}
    ...    uplink_lag=${UPLINK_LAG}

VLAN Interface IP MTU Is 9198
    [Documentation]    Every VLAN interface (except VLAN 1) has IP MTU 9198.
    [Tags]
    ...    core
    All VLAN Interfaces MTU Should Be    ${DEVICE_IP}
    ...    expected_mtu=${VLAN_IP_MTU}

SVI Interfaces Are Administratively Up
    [Documentation]    Every VLAN SVI (except VLAN 1) is administratively up.
    [Tags]
    ...    core
    SVIs Should Be Admin Up    ${DEVICE_IP}

Enabled Interfaces Are Up
    [Documentation]    Every administratively enabled physical interface has link up.
    [Tags]
    ...    core
    Enabled Interfaces Should Be Up    ${DEVICE_IP}

Up Interfaces Have Correct Speed And Duplex
    [Documentation]    Every up physical interface is running at the correct speed and duplex.
    [Tags]
    ...    core
    All Interfaces Should Be Correct Speed And Duplex    ${DEVICE_IP}
