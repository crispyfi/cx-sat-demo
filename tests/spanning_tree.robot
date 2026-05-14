*** Settings ***
Documentation       Spanning tree (MST) configuration and state tests

Library             ../libraries/CXLibraryBase.py
Library             ../libraries/CXLibrarySpanningTree.py

Suite Setup         Connect To Device    ${DEVICE_IP}    api_version=${API_VERSION}
Suite Teardown      Disconnect From Device


*** Test Cases ***
MSTP Configuration Consistent
    [Documentation]    STP is enabled in MSTP mode with the expected region name (site_name),
    ...    revision 0, and config digest.
    [Tags]
    ...    core
    ...    access
    MSTP Configuration Should Be Consistent    ${DEVICE_IP}    ${SITE_NAME}    ${MSTP_CONFIG_DIGEST}

Core Is MST Root
    [Documentation]    Core devices are root for the expected MST instances.
    [Tags]
    ...    core
    STP Root Should Match    ${DEVICE_IP}
    ...    mstp_root_instances=${MSTP_ROOT_INSTANCES}

BPDU/TCN Guard On Edge Ports
    [Documentation]    Access edge ports have BPDU guard, TCN guard, and admin edge enabled.
    [Tags]
    ...    access
    STP Edge Port Guards Should Be Configured    ${DEVICE_IP}

No Ports In Inconsistent State
    [Documentation]    No spanning-tree port reports any inconsistency flag.
    [Tags]
    ...    core
    ...    access
    No STP Inconsistent Ports    ${DEVICE_IP}
