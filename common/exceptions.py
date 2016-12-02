#!/usr/bin/env python
# encoding: utf-8
from oslo_utils import excutils

class DhcpAgentException(Exception):
    """Base DhcpAgent Exception.

    To correctly use this class, inherit from it and define
    a 'message' property. That message will get printf'd
    with the keyword arguments provided to the constructor.
    """
    message = ("An unknown exception occurred.")

    def __init__(self, **kwargs):
        try:
            super(DhcpAgentException, self).__init__(self.message % kwargs)
            self.msg = self.message % kwargs
        except Exception:
            with excutils.save_and_reraise_exception() as ctxt:
                if not self.use_fatal_exceptions():
                    ctxt.reraise = False
                    # at least get the core message out if something happened
                    super(DhcpAgentException, self).__init__(self.message)

    def __unicode__(self):
        return unicode(self.msg)

    def use_fatal_exceptions(self):
        return False


class NotFound(DhcpAgentException):
    pass


class Conflict(DhcpAgentException):
        pass


class BridgeDoesNotExist(DhcpAgentException):
    message = ("Bridge %(bridge)s does not exist.")


class NetworkVxlanPortRangeError(DhcpAgentException):
    message = ("Invalid network VXLAN port range: '%(vxlan_range)s'")


class DhcpPortNotFoundOnNetwork(NotFound):
    message = ("DHCP_PORT could not be found on network %(net_id)s")


class NetworkNotFound(NotFound):
    message = ("Network %(net_id)s could not be found")

