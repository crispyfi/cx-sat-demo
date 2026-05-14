*** Settings ***
Name                LACP
Documentation       LACP and LAG configuration tests

Library             ../libraries/CXLibraryBase.py
Library             ../libraries/CXLibraryLACP.py

Suite Setup         Connect To Device    ${DEVICE_IP}    api_version=${API_VERSION}
Suite Teardown      Disconnect From Device


*** Test Cases ***
LAG Members Active
    [Documentation]    Every member port of every LAG on the device is collecting and distributing.
    [Tags]
    ...    core
    ...    access
    All LAG Members Should Be Active    ${DEVICE_IP}
