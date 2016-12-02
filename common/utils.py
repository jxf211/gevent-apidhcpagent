#!/usr/bin/env python
# encoding: utf-8
import signal
from logger import log
from oslo_utils import lockutils
from gevent import subprocess
import uuid
from logger import log as LOG


SYNCHRONIZED_PREFIX = 'agent-'
synchronized = lockutils.synchronized_with_prefix(SYNCHRONIZED_PREFIX)


def _subprocess_setup():
    # Python installs a SIGPIPE handler by default. This is usually not what
    # non-Python subprocesses expect.
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)


def subprocess_popen(args, stdin=None, stdout=None, stderr=None, shell=False,
                     env=None, preexec_fn=_subprocess_setup, close_fds=True):

    return subprocess.Popen(args, shell=shell, stdin=stdin, stdout=stdout,
                            stderr=stderr, preexec_fn=preexec_fn,
                            close_fds=close_fds, env=env)


def get_dhcp_agent_device_id(network_id, host):
    # Split host so as to always use only the hostname and
    # not the domain name. This will guarantee consistentcy
    # whether a local hostname or an fqdn is passed in.
    local_hostname = host.split('.')[0]
    LOG.debug("local_hostname:%s, uuid.NAMESPACE_DNS:%s", local_hostname, uuid.NAMESPACE_DNS)
    host_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, str(local_hostname))
    return 'dhcp%s' % (network_id)



