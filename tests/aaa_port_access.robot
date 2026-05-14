*** Settings ***
Name                AAA Port Access
Documentation       AAA port access (RADIUS, 802.1X, MAC auth) tests

Library             ../libraries/CXLibraryBase.py
Library             ../libraries/CXLibraryAAAPortAccess.py

Suite Setup         Connect To Device    ${DEVICE_IP}    api_version=${API_VERSION}
Suite Teardown      Disconnect From Device


*** Test Cases ***
RADIUS Servers Reachable
    [Documentation]    Primary and secondary RADIUS servers are reachable and tracked.
    [Tags]
    ...    access
    RADIUS Servers Should Be Reachable    ${DEVICE_IP}
    ...    primary_radius_server=${PRIMARY_RADIUS_SERVER}
    ...    secondary_radius_server=${SECONDARY_RADIUS_SERVER}
    ...    management_vrf=${MANAGEMENT_VRF}

RADIUS CoA Configured
    [Documentation]    RADIUS Change of Authorization is enabled and the expected CoA clients are configured.
    [Tags]
    ...    access
    RADIUS CoA Should Be Configured    ${DEVICE_IP}
    ...    primary_radius_ip=${PRIMARY_RADIUS_IP}
    ...    secondary_radius_ip=${SECONDARY_RADIUS_IP}
    ...    management_vrf=${MANAGEMENT_VRF}

Colourless Ports Have Standard Auth
    [Documentation]    Edge ports have access VLAN mode with dot1x/mac-auth enabled.
    [Tags]
    ...    access
    Colourless Ports Should Have Auth    ${DEVICE_IP}

Client IP Tracking Enabled
    [Documentation]    Client IP tracking is enabled globally and across all VLANs.
    [Tags]
    ...    access
    Client IP Tracking Should Be Enabled    ${DEVICE_IP}
