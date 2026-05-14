*** Settings ***
Documentation       Software version and profile tests

Library             ../libraries/CXLibraryBase.py
Library             ../libraries/CXLibrarySoftware.py

Suite Setup         Connect To Device    ${DEVICE_IP}    api_version=${API_VERSION}
Suite Teardown      Disconnect From Device


*** Test Cases ***
Version Matches Design
    [Documentation]    The running software version matches the design's expected version.
    [Tags]
    ...    core
    ...    access
    Software Version Should Match    ${DEVICE_IP}
    ...    expected_version=${SOFTWARE_VERSION}

No Pending Unsafe Updates
    [Documentation]    No pending non-failsafe software updates exist on current, primary, or secondary ISP images.
    [Tags]
    ...    core
    ...    access
    No Unsafe Software Updates    ${DEVICE_IP}
    ...    vsf_members=${VSF_MEMBERS}
