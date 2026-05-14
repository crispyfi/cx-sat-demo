*** Settings ***
Name                OSPF
Documentation       OSPF configuration and operational state tests

Library             ../libraries/CXLibraryBase.py
Library             ../libraries/CXLibraryOSPF.py

Suite Setup         Connect To Device    ${DEVICE_IP}    api_version=${API_VERSION}
Suite Teardown      Disconnect From Device


*** Test Cases ***
Passive-Interface Default Enabled
    [Documentation]    OSPF passive-interface default is enabled in every OSPF instance and VRF.
    [Tags]
    ...    core
    OSPF Passive Default Should Be Configured    ${DEVICE_IP}

Graceful Restart Configured
    [Documentation]    OSPF graceful restart restart_interval matches the expected value in every VRF.
    [Tags]
    ...    core
    OSPF Graceful Restart Should Be Configured    ${DEVICE_IP}
    ...    restart_interval=${OSPF_GRACEFUL_RESTART_INTERVAL}

Max-Metric Router-LSA On Startup Configured
    [Documentation]    OSPF lsa_throttle.start_time is 5000ms in every VRF (avoid premature LSA after boot).
    [Tags]
    ...    core
    OSPF Max Metric On Startup Should Be Configured    ${DEVICE_IP}

BFD Enabled On All OSPF Interfaces
    [Documentation]    Every OSPF process has bfd_all_interfaces_enable true.
    [Tags]
    ...    core
    OSPF BFD Should Be Enabled    ${DEVICE_IP}

BFD Sessions Active
    [Documentation]    Every OSPF BFD session has async, echo, remote, and session state up.
    [Tags]
    ...    core
    OSPF BFD Sessions Should Be Active    ${DEVICE_IP}

All OSPF Neighbor Adjacencies Converged
    [Documentation]    Every OSPF neighbour is Full, or Two-Way where at least two Full neighbours
    ...    exist on the same interface (expected DROther behaviour).
    [Tags]
    ...    core
    All OSPF Neighbor Adjacencies Should Be Converged    ${DEVICE_IP}

No Routes With Low Uptime
    [Documentation]    No OSPF route in any VRF has a route_age below the minimum threshold.
    [Tags]
    ...    core
    No OSPF Routes With Low Uptime    ${DEVICE_IP}
    ...    min_age=${OSPF_ROUTE_MIN_AGE}
