*** Settings ***
Documentation       Environmental health tests (CPU, memory, PSU, fans)

Library             ../libraries/CXLibraryBase.py
Library             ../libraries/CXLibraryEnvironment.py

Suite Setup         Connect To Device    ${DEVICE_IP}    api_version=${API_VERSION}
Suite Teardown      Disconnect From Device


*** Test Cases ***
CPU Utilization Below Threshold
    [Documentation]    CPU utilization on every management module is under ${CPU_THRESHOLD}%.
    [Tags]
    ...    core
    ...    access
    CPU Utilization Should Be Below    ${DEVICE_IP}
    ...    threshold=${CPU_THRESHOLD}
    ...    vsf_members=${VSF_MEMBERS}

Memory Utilization Below Threshold
    [Documentation]    Memory utilization on every management module is under ${MEMORY_THRESHOLD}%.
    [Tags]
    ...    core
    ...    access
    Memory Utilization Should Be Below    ${DEVICE_IP}
    ...    threshold=${MEMORY_THRESHOLD}
    ...    vsf_members=${VSF_MEMBERS}

All Power Supplies OK
    [Documentation]    Every expected PSU slot is populated and reports no faults or warnings.
    [Tags]
    ...    core
    ...    access
    All Power Supplies Should Be OK    ${DEVICE_IP}
    ...    vsf_members=${VSF_MEMBERS}

All Fans OK
    [Documentation]    Every fan reports OK status.
    [Tags]
    ...    core
    ...    access
    All Fans Should Be OK    ${DEVICE_IP}
    ...    vsf_members=${VSF_MEMBERS}

All Thermal States Safe
    [Documentation]    Every subsystem with a non-null thermal_state reports safe.
    [Tags]
    ...    core
    ...    access
    All Thermal States Should Be Safe    ${DEVICE_IP}
    ...    vsf_members=${VSF_MEMBERS}
