*** Settings ***
Documentation       Multicast (IGMP snooping and PIM) tests

Library             ../libraries/CXLibraryBase.py
Library             ../libraries/CXLibraryMulticast.py

Suite Setup         Connect To Device    ${DEVICE_IP}    api_version=${API_VERSION}
Suite Teardown      Disconnect From Device


*** Test Cases ***
IGMP Snooping On Every VLAN
    [Documentation]    IGMP snooping is enabled and operating at the expected version on every VLAN on this L2 switch.
    [Tags]
    ...    core
    ...    access
    IGMP Snooping Should Be On Every Vlan    ${DEVICE_IP}
    ...    version=${IGMP_VERSION}
