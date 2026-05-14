*** Settings ***
Name                DNS
Documentation       DNS domain and resolver configuration tests

Library             ../libraries/CXLibraryBase.py
Library             ../libraries/CXLibraryDNS.py

Suite Setup         Connect To Device    ${DEVICE_IP}    api_version=${API_VERSION}
Suite Teardown      Disconnect From Device


*** Test Cases ***
Domain Name Matches Design
    [Documentation]    DNS domain name matches design input.
    [Tags]
    ...    core
    ...    access
    Domain Name Should Match    ${DEVICE_IP}
    ...    expected_domain=${DOMAIN_NAME}

DNS Servers Match Design
    [Documentation]    DNS name servers match design input.
    [Tags]
    ...    core
    ...    access
    DNS Servers Should Match    ${DEVICE_IP}
    ...    management_vrf=${MANAGEMENT_VRF}
    ...    dns_servers=${DNS_SERVERS}
