*** Settings ***
Name                VSX
Documentation       VSX configuration and operational state tests

Library             ../libraries/CXLibraryBase.py
Library             ../libraries/CXLibraryVSX.py

Suite Setup         Connect To Device    ${DEVICE_IP}    api_version=${API_VERSION}
Suite Teardown      Disconnect From Device
Test Teardown       Log VSX Related Config    ${DEVICE_IP}


*** Test Cases ***
ISL In-Sync And Peer Established
    [Documentation]    The VSX ISL is operational, the peer is established and ready, and config sync is in-sync.
    [Tags]
    ...    core
    VSX Peers Should Be In Sync    ${DEVICE_IP}

Keepalive Established
    [Documentation]    The VSX keepalive is in_sync_established.
    [Tags]
    ...    core
    VSX Keepalive Should Be Established    ${DEVICE_IP}

Firmware Versions Match Between Peers
    [Documentation]    Both VSX peers run identical AOS-CX software versions.
    [Tags]
    ...    core
    VSX Firmware Should Match    ${DEVICE_IP}
