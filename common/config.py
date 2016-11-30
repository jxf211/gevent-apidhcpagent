# Copyright 2011 VMware, Inc.
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

"""
Routines for configuring Neutron
"""

import os
import sys

#from keystoneclient import auth
#from keystoneclient import session as ks_session
from oslo_config import cfg
#from oslo_db import options as db_options
from oslo_log import log as logging
#import oslo_messaging
#from paste import deploy

#from neutron.api.v2 import attributes
from common import utils
#from neutron.i18n import _LI
import version
import re

LOG = logging.getLogger(__name__)

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
    cfg.StrOpt('host', default=utils.get_hostname(),
               help=("Hostname to be used by the neutron server, agents and "
                      "services running on this machine. All the agents and "
                      "services running on this machine must use the same "
                      "host value.")),
    cfg.BoolOpt('advertise_mtu', default=False,
                help=('If True, effort is made to advertise MTU settings '
                       'to VMs via network methods (DHCP and RA MTU options) '
                       'when the network\'s preferred MTU is known.')),
]

core_cli_opts = [
    cfg.StrOpt('state_path',
               default='/var/lib/neutron',
               help=("Where to store Neutron state files. "
                      "This directory must be writable by the agent.")),
]

# Register the configuration options
cfg.CONF.register_opts(core_opts)
cfg.CONF.register_cli_opts(core_cli_opts)

logging.register_options(cfg.CONF)

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
    # failure occurs
    #from common import rpc as n_rpc
    #n_rpc.init(cfg.CONF)

    # Validate that the base_mac is of the correct format
    msg = _validate_regex(cfg.CONF.base_mac, MAC_PATTERN)
    if msg:
        msg = _("Base MAC: %s") % msg
        raise Exception(msg)

def setup_logging():
    """Sets up the logging options for a log with supplied name."""
    product_name = "neutron"
    logging.setup(cfg.CONF, product_name)
    LOG.info(("Logging enabled!"))
    LOG.info("%(prog)s version %(version)s",
             {'prog': sys.argv[0],
              'version': '201020'})
    LOG.debug("command line: %s", " ".join(sys.argv))

