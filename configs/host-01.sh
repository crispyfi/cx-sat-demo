#!/bin/sh
ip addr add 10.32.10.10/24 dev eth1
route add default gw 10.32.20.1
route del default gw 172.20.20.1