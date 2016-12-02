#!/usr/bin/env python
# encoding: utf-8

IP_VERSION_4 = 4
IP_VERSION_6 = 6
# Device names start with "tap"
TAP_DEVICE_PREFIX = 'tap'
IPV6_SLAAC = 'slaac'
DHCPV6_STATELESS = 'dhcpv6-stateless'
DEVICE_OWNER_DHCP = "network:dhcp"
IPv4_ANY = '0.0.0.0/0'

DEVICE_OWNER_DVR_INTERFACE = "network:router_interface_distributed"
DEVICE_OWNER_ROUTER_INTF = "network:router_interface"
ROUTER_INTERFACE_OWNERS = (DEVICE_OWNER_ROUTER_INTF,
                           DEVICE_OWNER_DVR_INTERFACE)

