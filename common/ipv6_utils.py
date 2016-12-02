#!/usr/bin/env python
# encoding: utf-8
import constants


def is_auto_address_subnet(subnet):
    """Check if subnet is an auto address subnet."""
    modes = [constants.IPV6_SLAAC, constants.DHCPV6_STATELESS]
    return (subnet['ipv6_address_mode'] in modes
            or subnet['ipv6_ra_mode'] in modes)
