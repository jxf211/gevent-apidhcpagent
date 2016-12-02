#!/usr/bin/env python
# encoding: utf-8

import sys
from oslo_config import cfg
from logger import log
import re

core_opts = [
    cfg.StrOpt('base_mac', default="fa:16:3e:00:00:00",
               help=("The base MAC address Neutron will use for VIFs")),
    cfg.IntOpt('mac_generation_retries', default=16,
               help=("How many times Neutron will retry MAC generation")),
    cfg.IntOpt('dhcp_lease_duration', default=86400,
               deprecated_name='dhcp_lease_time',
               help=("DHCP lease duration (in seconds). Use -1 to tell "
                      "dnsmasq to use infinite lease times.")),
    cfg.BoolOpt('dhcp_agent_notification', default=True,
                help=("Allow sending resource operation"
                       " notification to DHCP agent")),
    cfg.StrOpt('host', default='nsplocal',
               help=("Hostname to be used by the neutron server, agents and "
                      "services running on this machine. All the agents and "
                      "services running on this machine must use the same "
                      "host value.")),
    cfg.BoolOpt('advertise_mtu', default=False,
                help=('If True, effort is made to advertise MTU settings '
                       'to VMs via network methods (DHCP and RA MTU options) '
                       'when the network\'s preferred MTU is known.'))


]

ROOT_HELPER_OPTS = [
    cfg.StrOpt('root_helper', default='sudo',
               help=('Root helper application.')),
    cfg.BoolOpt('use_helper_for_ns_read',
                default=True,
                help=('Use the root helper to read the namespaces from '
                       'the operating system.')),
    # We can't just use root_helper=sudo neutron-rootwrap-daemon $cfg because
    # it isn't appropriate for long-lived processes spawned with create_process
    # Having a bool use_rootwrap_daemon option precludes specifying the
    # rootwrap daemon command, which may be necessary for Xen?
    cfg.StrOpt('root_helper_daemon',
               help=('Root helper daemon application to use when possible.')),
]


INTERFACE_DRIVER_OPTS = [
    cfg.StrOpt('interface_driver',
               help=("The driver used to manage the virtual interface.")),
]


USE_NAMESPACES_OPTS = [
    cfg.BoolOpt('use_namespaces', default=True,
                help=("Allow overlapping IP. This option is deprecated and "
                       "will be removed in a future release."),
                deprecated_for_removal=True),
]

IPTABLES_OPTS = [
    cfg.BoolOpt('comment_iptables_rules', default=True,
                help=("Add comments to iptables rules.")),
]


PROCESS_MONITOR_OPTS = [
    cfg.StrOpt('check_child_processes_action', default='respawn',
               choices=['respawn', 'exit'],
               help=('Action to be executed when a child process dies')),
    cfg.IntOpt('check_child_processes_interval', default=60,
               help=('Interval between checks of child process liveness '
                      '(seconds), use 0 to disable')),
]


SPOOFING_OPTS = [
    cfg.BoolOpt('enable_mac_spoofing_protection', default=True,
                help=("Set to False to prevent the agent from installing "
                       "anti-MAC-spoofing rules that address bug 1558658."))
]

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


DHCP_AGENT_OPTS = [
    cfg.IntOpt('resync_interval', default=5,
               help=("Interval to resync.")),
    cfg.StrOpt('dhcp_driver',
               default='nspagent.dhcp.linux.dhcp.Dnsmasq',
               help=("The driver used to manage the DHCP server.")),
    cfg.BoolOpt('enable_isolated_metadata', default=False,
                help=("Support Metadata requests on isolated networks.")),
    cfg.BoolOpt('enable_metadata_network', default=False,
                help=("Allows for serving metadata requests from a "
                       "dedicated network. Requires "
                       "enable_isolated_metadata = True")),
    cfg.IntOpt('num_sync_threads', default=4,
               help=('Number of threads to use during sync process.'))
]

DHCP_OPTS = [
    cfg.StrOpt('dhcp_confs',
               default='$state_path/dhcp',
               help=('Location to store DHCP server config files')),
    cfg.StrOpt('dhcp_domain',
               default='openstacklocal',
               help=('Domain to use for building the hostnames')),
]

DNSMASQ_OPTS = [
    cfg.StrOpt('dnsmasq_config_file',
               default='',
               help=('Override the default dnsmasq settings with this file')),
    cfg.ListOpt('dnsmasq_dns_servers',
                help=('Comma-separated list of the DNS servers which will be '
                       'used as forwarders.'),
                deprecated_name='dnsmasq_dns_server'),
    cfg.BoolOpt('dhcp_delete_namespaces', default=False,
                help=("Delete namespace after removing a dhcp server.")),
    cfg.IntOpt(
        'dnsmasq_lease_max',
        default=(2 ** 24),
        help=('Limit number of leases to prevent a denial-of-service.')),
    cfg.BoolOpt('dhcp_broadcast_reply', default=False,
                help=("Use broadcast in DHCP replies")),
]

core_cli_opts = [
    cfg.StrOpt('state_path',
               default='/var/lib/neutron',
               help=("Where to store Neutron state files. "
                      "This directory must be writable by the agent.")),
]

PID_OPTS = [
    cfg.StrOpt('external_pids',
               default='$state_path/external/pids',
               help=('Location to store child pid files')),
]

def register_conf():
# Register the configuration options
    cfg.CONF.register_opts(core_opts)
    cfg.CONF.register_opts(INTERFACE_DRIVER_OPTS)
    cfg.CONF.register_opts(USE_NAMESPACES_OPTS)
    cfg.CONF.register_opts(DHCP_AGENT_OPTS)
    cfg.CONF.register_opts(DHCP_OPTS)
    cfg.CONF.register_opts(DNSMASQ_OPTS)
    cfg.CONF.register_opts(OPTS)
    cfg.CONF.register_opts(PROCESS_MONITOR_OPTS, 'AGENT')
    cfg.CONF.register_opts(PID_OPTS)
    cfg.CONF.register_opts(ROOT_HELPER_OPTS, 'AGENT')

    cfg.CONF.register_cli_opts(core_cli_opts)


HEX_ELEM = '[0-9A-Fa-f]'

MAC_PATTERN = "^%s[aceACE02468](:%s{2}){5}$" % (HEX_ELEM, HEX_ELEM)

def _validate_regex(data, valid_values=None):
    try:
        if re.match(valid_values, data):
            return
    except TypeError:
        pass

    msg = ("'%s' is not a valid input") % data
    LOG.debug(msg)
    return msg


def init(args, **kwargs):
    cfg.CONF(args=args, project='neutron',
             #version='%%(prog)s %s' % version.version_info.release_string(),
             version='20161010',
             **kwargs)

    # FIXME(ihrachys): if import is put in global, circular import

    # Validate that the base_mac is of the correct format
    msg = _validate_regex(cfg.CONF.base_mac, MAC_PATTERN)
    if msg:
        msg = _("Base MAC: %s") % msg
        raise Exception(msg)


def get_root_helper(conf):
    return conf.AGENT.root_helper
