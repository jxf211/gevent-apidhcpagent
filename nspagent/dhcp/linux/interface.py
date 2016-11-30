# Copyright 2012 OpenStack Foundation
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import abc

import netaddr
from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import importutils
import six

from nspagent.dhcpcommon import ovs_lib
from nspagent.dhcp.linux import ip_lib
from nspagent.dhcp.linux import utils
from common import constants as n_const
from common import exceptions


LOG = logging.getLogger(__name__)

OPTS = [
    cfg.StrOpt('ovs_integration_bridge',
               default='nspbr1',
               help=('Name of Open vSwitch bridge to use')),
    cfg.BoolOpt('ovs_use_veth',
                default=False,
                help=('Uses veth for an interface or not')),
    cfg.IntOpt('network_device_mtu',
               help=('MTU setting for device.')),
]


@six.add_metaclass(abc.ABCMeta)
class LinuxInterfaceDriver(object):

    # from linux IF_NAMESIZE
    DEV_NAME_LEN = 14
    DEV_NAME_PREFIX = n_const.TAP_DEVICE_PREFIX

    def __init__(self, conf):
        self.conf = conf

    def init_l3(self, device_name, ip_cidrs, namespace=None,
                preserve_ips=[], gateway_ips=None, extra_subnets=[],
                enable_ra_on_gw=False):
        """Set the L3 settings for the interface using data from the port.

        ip_cidrs: list of 'X.X.X.X/YY' strings
        preserve_ips: list of ip cidrs that should not be removed from device
        gateway_ips: For gateway ports, list of external gateway ip addresses
        enable_ra_on_gw: Boolean to indicate configuring acceptance of IPv6 RA
        """
        device = ip_lib.IPDevice(device_name, namespace=namespace)

        previous = set()
        for address in device.addr.list(scope='global', filters=['permanent']):
            previous.add(address['cidr'])

        # add new addresses
        for ip_cidr in ip_cidrs:

            net = netaddr.IPNetwork(ip_cidr)
            # Convert to compact IPv6 address because the return values of
            # "ip addr list" are compact.
            if net.version == 6:
                ip_cidr = str(net)
            if ip_cidr in previous:
                previous.remove(ip_cidr)
                continue

            device.addr.add(ip_cidr)

        # clean up any old addresses
        for ip_cidr in previous:
            if ip_cidr not in preserve_ips:
                device.addr.delete(ip_cidr)
                self.delete_conntrack_state(namespace=namespace, ip=ip_cidr)

        for gateway_ip in gateway_ips or []:
            device.route.add_gateway(gateway_ip)

        if enable_ra_on_gw:
            self.configure_ipv6_ra(namespace, device_name)

        new_onlink_routes = set(s['cidr'] for s in extra_subnets)
        existing_onlink_routes = set(
            device.route.list_onlink_routes(n_const.IP_VERSION_4) +
            device.route.list_onlink_routes(n_const.IP_VERSION_6))
        for route in new_onlink_routes - existing_onlink_routes:
            device.route.add_onlink_route(route)
        for route in existing_onlink_routes - new_onlink_routes:
            device.route.delete_onlink_route(route)

    def delete_conntrack_state(self, namespace, ip):
        """Delete conntrack state associated with an IP address.

        This terminates any active connections through an IP.  Call this soon
        after removing the IP address from an interface so that new connections
        cannot be created before the IP address is gone.

        namespace: the name of the namespace where the IP has been configured
        ip: the IP address for which state should be removed.  This can be
            passed as a string with or without /NN.  A netaddr.IPAddress or
            netaddr.Network representing the IP address can also be passed.
        """
        ip_str = str(netaddr.IPNetwork(ip).ip)
        ip_wrapper = ip_lib.IPWrapper(namespace=namespace)

        # Delete conntrack state for ingress traffic
        # If 0 flow entries have been deleted
        # conntrack -D will return 1
        try:
            ip_wrapper.netns.execute(["conntrack", "-D", "-d", ip_str],
                                     check_exit_code=True,
                                     extra_ok_codes=[1])

        except RuntimeError:
            LOG.exception(("Failed deleting ingress connection state of"
                              " floatingip %s"), ip_str)

        # Delete conntrack state for egress traffic
        try:
            ip_wrapper.netns.execute(["conntrack", "-D", "-q", ip_str],
                                     check_exit_code=True,
                                     extra_ok_codes=[1])
        except RuntimeError:
            LOG.exception(("Failed deleting egress connection state of"
                              " floatingip %s"), ip_str)

    def check_bridge_exists(self, bridge):
        if not ip_lib.device_exists(bridge):
            raise exceptions.BridgeDoesNotExist(bridge=bridge)

    def get_device_name(self, port):
        return (self.DEV_NAME_PREFIX + port.id)[:self.DEV_NAME_LEN]

    @staticmethod
    def configure_ipv6_ra(namespace, dev_name):
        """Configure acceptance of IPv6 route advertisements on an intf."""
        # Learn the default router's IP address via RAs
        ip_lib.IPWrapper(namespace=namespace).netns.execute(
            ['sysctl', '-w', 'net.ipv6.conf.%s.accept_ra=2' % dev_name])

    @abc.abstractmethod
    def plug(self, network_id, port_id, device_name, mac_address,
             bridge=None, namespace=None, prefix=None):
        """Plug in the interface."""

    @abc.abstractmethod
    def unplug(self, device_name, bridge=None, namespace=None, prefix=None):
        """Unplug the interface."""

class OVSInterfaceDriver(LinuxInterfaceDriver):
    """Driver for creating an internal interface on an OVS bridge."""

    DEV_NAME_PREFIX = n_const.TAP_DEVICE_PREFIX

    def __init__(self, conf):
        LOG.debug("start init OVSInterfaceDriver")
        super(OVSInterfaceDriver, self).__init__(conf)
        if self.conf.ovs_use_veth:
            self.DEV_NAME_PREFIX = 'ns-'
        LOG.debug("ok init OVSInterfaceDriver")
    def _get_tap_name(self, dev_name, prefix=None):
        if self.conf.ovs_use_veth:
            dev_name = dev_name.replace(prefix or self.DEV_NAME_PREFIX,
                                        n_const.TAP_DEVICE_PREFIX)
        return dev_name

    def _ovs_add_port(self, bridge, device_name, port_id, mac_address,
                      internal=True):
        attrs = [('external_ids', {'iface-id': port_id,
                                   'iface-status': 'active',
                                   'attached-mac': mac_address})]
        if internal:
            attrs.insert(0, ('type', 'internal'))

        ovs = ovs_lib.OVSBridge(bridge)
        ovs.replace_port(device_name, *attrs)

    def plug(self, network_id, port_id=None, device_name=None, mac_address=None,
             bridge=None, namespace=None, prefix=None):
        """Plug in the interface."""
        if not bridge:
            bridge = self.conf.ovs_integration_bridge

        if not ip_lib.device_exists(device_name, namespace=namespace):

            self.check_bridge_exists(bridge)

            ip = ip_lib.IPWrapper()
            tap_name = self._get_tap_name(device_name, prefix)
            LOG.debug("tap_name:%s, device_name:%s, namespace=%s", tap_name, device_name, namespace)
            if self.conf.ovs_use_veth:
                # Create ns_dev in a namespace if one is configured.
                root_dev, ns_dev = ip.add_veth(tap_name,
                                               device_name,
                                               namespace2=namespace)
                root_dev.disable_ipv6()
            else:
                ns_dev = ip.device(device_name)

            internal = not self.conf.ovs_use_veth
            self._ovs_add_port(bridge, tap_name, port_id, mac_address,
                               internal=internal)
            if mac_address:
                ns_dev.link.set_address(mac_address)

            if self.conf.network_device_mtu:
                ns_dev.link.set_mtu(self.conf.network_device_mtu)
                if self.conf.ovs_use_veth:
                    root_dev.link.set_mtu(self.conf.network_device_mtu)

            # Add an interface created by ovs to the namespace.
            if not self.conf.ovs_use_veth and namespace:
                namespace_obj = ip.ensure_namespace(namespace)
                namespace_obj.add_device_to_namespace(ns_dev)

            ns_dev.link.set_up()
            if self.conf.ovs_use_veth:
                root_dev.link.set_up()
        else:
	    
            LOG.info(("Device %s already exists"), device_name)

    def unplug(self, device_name, bridge=None, namespace=None, prefix=None):
        """Unplug the interface."""
        if not bridge:
            bridge = self.conf.ovs_integration_bridge

        tap_name = self._get_tap_name(device_name, prefix)
        self.check_bridge_exists(bridge)
        ovs = ovs_lib.OVSBridge(bridge)

        try:
            ovs.delete_port(tap_name)
            if self.conf.ovs_use_veth:
                device = ip_lib.IPDevice(device_name, namespace=namespace)
                device.link.delete()
                LOG.debug("Unplugged interface '%s'", device_name)
        except RuntimeError:
            LOG.error(("Failed unplugging interface '%s'"),
                      device_name)


class BridgeInterfaceDriver(LinuxInterfaceDriver):
    """Driver for creating bridge interfaces."""

    DEV_NAME_PREFIX = 'ns-'

    def plug(self, network_id, port_id, device_name, mac_address,
             bridge=None, namespace=None, prefix=None):
        """Plugin the interface."""
        if not ip_lib.device_exists(device_name, namespace=namespace):

            ip = ip_lib.IPWrapper()

            # Enable agent to define the prefix
            tap_name = device_name.replace(prefix or self.DEV_NAME_PREFIX,
                                        n_const.TAP_DEVICE_PREFIX)
            # Create ns_veth in a namespace if one is configured.
            root_veth, ns_veth = ip.add_veth(tap_name, device_name,
                                             namespace2=namespace)
            root_veth.disable_ipv6()
            ns_veth.link.set_address(mac_address)
            if self.conf.network_device_mtu:
                root_veth.link.set_mtu(self.conf.network_device_mtu)
                ns_veth.link.set_mtu(self.conf.network_device_mtu)
            root_veth.link.set_up()
            ns_veth.link.set_up()

        else:
            LOG.info(("Device %s already exists"), device_name)

    def unplug(self, device_name, bridge=None, namespace=None, prefix=None):
        """Unplug the interface."""
        device = ip_lib.IPDevice(device_name, namespace=namespace)
        try:
            device.link.delete()
            LOG.debug("Unplugged interface '%s'", device_name)
        except RuntimeError:
            LOG.error(("Failed unplugging interface '%s'"),
                      device_name)

