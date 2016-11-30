# Copyright 2011 VMware, Inc
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
Neutron base exception handling.
"""

from oslo_utils import excutils


class NeutronException(Exception):
    """Base Neutron Exception.

    To correctly use this class, inherit from it and define
    a 'message' property. That message will get printf'd
    with the keyword arguments provided to the constructor.
    """
    message = ("An unknown exception occurred.")

    def __init__(self, **kwargs):
        try:
            super(NeutronException, self).__init__(self.message % kwargs)
            self.msg = self.message % kwargs
        except Exception:
            with excutils.save_and_reraise_exception() as ctxt:
                if not self.use_fatal_exceptions():
                    ctxt.reraise = False
                    # at least get the core message out if something happened
                    super(NeutronException, self).__init__(self.message)

    def __unicode__(self):
        return unicode(self.msg)

    def use_fatal_exceptions(self):
        return False


class BadRequest(NeutronException):
    message = ('Bad %(resource)s request: %(msg)s')


class NotFound(NeutronException):
    pass


class Conflict(NeutronException):
    pass


class NotAuthorized(NeutronException):
    message = "Not authorized."


class ServiceUnavailable(NeutronException):
    message = ("The service is unavailable")


class AdminRequired(NotAuthorized):
    message = ("User does not have admin privileges: %(reason)s")


class NetworkNotFound(NotFound):
    message = ("Network %(net_id)s could not be found")


class SubnetNotFound(NotFound):
    message = ("Subnet %(subnet_id)s could not be found")


class SubnetPoolNotFound(NotFound):
    message = ("Subnet pool %(subnetpool_id)s could not be found")


class PortNotFound(NotFound):
    message = ("Port %(port_id)s could not be found")


class PortNotFoundOnNetwork(NotFound):
    message = ("Port %(port_id)s could not be found "
                "on network %(net_id)s")

class DhcpPortNotFoundOnNetwork(NotFound):
    message = ("DHCP_PORT could not be found on network %(net_id)s")

class PolicyFileNotFound(NotFound):
    message = ("Policy configuration policy.json could not be found")


class PolicyInitError(NeutronException):
    message = ("Failed to init policy %(policy)s because %(reason)s")


class PolicyCheckError(NeutronException):
    message = ("Failed to check policy %(policy)s because %(reason)s")


class StateInvalid(BadRequest):
    message = ("Unsupported port state: %(port_state)s")


class InUse(NeutronException):
    message = ("The resource is inuse")


class NetworkInUse(InUse):
    message = ("Unable to complete operation on network %(net_id)s. "
                "There are one or more ports still in use on the network.")


class SubnetInUse(InUse):
    message = ("Unable to complete operation on subnet %(subnet_id)s. "
                "One or more ports have an IP allocation from this subnet.")


class PortInUse(InUse):
    message = ("Unable to complete operation on port %(port_id)s "
                "for network %(net_id)s. Port already has an attached "
                "device %(device_id)s.")


class ServicePortInUse(InUse):
    message = ("Port %(port_id)s cannot be deleted directly via the "
                "port API: %(reason)s")


class PortBound(InUse):
    message = ("Unable to complete operation on port %(port_id)s, "
                "port is already bound, port type: %(vif_type)s, "
                "old_mac %(old_mac)s, new_mac %(new_mac)s")


class MacAddressInUse(InUse):
    message = ("Unable to complete operation for network %(net_id)s. "
                "The mac address %(mac)s is in use.")


class HostRoutesExhausted(BadRequest):
    # NOTE(xchenum): probably make sense to use quota exceeded exception?
    message = ("Unable to complete operation for %(subnet_id)s. "
                "The number of host routes exceeds the limit %(quota)s.")


class DNSNameServersExhausted(BadRequest):
    # NOTE(xchenum): probably make sense to use quota exceeded exception?
    message = ("Unable to complete operation for %(subnet_id)s. "
                "The number of DNS nameservers exceeds the limit %(quota)s.")


class InvalidIpForNetwork(BadRequest):
    message = ("IP address %(ip_address)s is not a valid IP "
                "for any of the subnets on the specified network.")


class InvalidIpForSubnet(BadRequest):
    message = ("IP address %(ip_address)s is not a valid IP "
                "for the specified subnet.")


class IpAddressInUse(InUse):
    message = ("Unable to complete operation for network %(net_id)s. "
                "The IP address %(ip_address)s is in use.")


class VlanIdInUse(InUse):
    message = ("Unable to create the network. "
                "The VLAN %(vlan_id)s on physical network "
                "%(physical_network)s is in use.")


class FlatNetworkInUse(InUse):
    message = ("Unable to create the flat network. "
                "Physical network %(physical_network)s is in use.")


class TunnelIdInUse(InUse):
    message = ("Unable to create the network. "
                "The tunnel ID %(tunnel_id)s is in use.")


class TenantNetworksDisabled(ServiceUnavailable):
    message = ("Tenant network creation is not enabled.")


class ResourceExhausted(ServiceUnavailable):
    pass


class NoNetworkAvailable(ResourceExhausted):
    message = ("Unable to create the network. "
                "No tenant network is available for allocation.")


class NoNetworkFoundInMaximumAllowedAttempts(ServiceUnavailable):
    message = ("Unable to create the network. "
                "No available network found in maximum allowed attempts.")


class SubnetMismatchForPort(BadRequest):
    message = ("Subnet on port %(port_id)s does not match "
                "the requested subnet %(subnet_id)s")


class MalformedRequestBody(BadRequest):
    message = ("Malformed request body: %(reason)s")


class Invalid(NeutronException):
    def __init__(self, message=None):
        self.message = message
        super(Invalid, self).__init__()


class InvalidInput(BadRequest):
    message = ("Invalid input for operation: %(error_message)s.")


class InvalidAllocationPool(BadRequest):
    message = ("The allocation pool %(pool)s is not valid.")


class UnsupportedPortDeviceOwner(Conflict):
    message = ("Operation %(op)s is not supported for device_owner "
                "%(device_owner)s on port %(port_id)s.")


class OverlappingAllocationPools(Conflict):
    message = ("Found overlapping allocation pools: "
                "%(pool_1)s %(pool_2)s for subnet %(subnet_cidr)s.")


class OutOfBoundsAllocationPool(BadRequest):
    message = ("The allocation pool %(pool)s spans "
                "beyond the subnet cidr %(subnet_cidr)s.")


class MacAddressGenerationFailure(ServiceUnavailable):
    message = ("Unable to generate unique mac on network %(net_id)s.")


class IpAddressGenerationFailure(Conflict):
    message = ("No more IP addresses available on network %(net_id)s.")


class BridgeDoesNotExist(NeutronException):
    message = ("Bridge %(bridge)s does not exist.")


class PreexistingDeviceFailure(NeutronException):
    message = ("Creation failed. %(dev_name)s already exists.")


class QuotaResourceUnknown(NotFound):
    message = ("Unknown quota resources %(unknown)s.")


class OverQuota(Conflict):
    message = ("Quota exceeded for resources: %(overs)s")


class QuotaMissingTenant(BadRequest):
    message = ("Tenant-id was missing from Quota request")


class InvalidQuotaValue(Conflict):
    message = ("Change would make usage less than 0 for the following "
                "resources: %(unders)s")


class InvalidSharedSetting(Conflict):
    message = ("Unable to reconfigure sharing settings for network "
                "%(network)s. Multiple tenants are using it")


class InvalidExtensionEnv(BadRequest):
    message = ("Invalid extension environment: %(reason)s")


class ExtensionsNotFound(NotFound):
    message = ("Extensions not found: %(extensions)s")


class InvalidContentType(NeutronException):
    message = ("Invalid content type %(content_type)s")


class ExternalIpAddressExhausted(BadRequest):
    message = ("Unable to find any IP address on external "
                "network %(net_id)s.")


class TooManyExternalNetworks(NeutronException):
    message = ("More than one external network exists")


class InvalidConfigurationOption(NeutronException):
    message = ("An invalid value was provided for %(opt_name)s: "
                "%(opt_value)s")


class GatewayConflictWithAllocationPools(InUse):
    message = ("Gateway ip %(ip_address)s conflicts with "
                "allocation pool %(pool)s")


class GatewayIpInUse(InUse):
    message = ("Current gateway ip %(ip_address)s already in use "
                "by port %(port_id)s. Unable to update.")


class NetworkVlanRangeError(NeutronException):
    message = ("Invalid network VLAN range: '%(vlan_range)s' - '%(error)s'")

    def __init__(self, **kwargs):
        # Convert vlan_range tuple to 'start:end' format for display
        if isinstance(kwargs['vlan_range'], tuple):
            kwargs['vlan_range'] = "%d:%d" % kwargs['vlan_range']
        super(NetworkVlanRangeError, self).__init__(**kwargs)


class PhysicalNetworkNameError(NeutronException):
    message = ("Empty physical network name.")


class NetworkTunnelRangeError(NeutronException):
    message = ("Invalid network Tunnel range: "
                "'%(tunnel_range)s' - %(error)s")

    def __init__(self, **kwargs):
        # Convert tunnel_range tuple to 'start:end' format for display
        if isinstance(kwargs['tunnel_range'], tuple):
            kwargs['tunnel_range'] = "%d:%d" % kwargs['tunnel_range']
        super(NetworkTunnelRangeError, self).__init__(**kwargs)


class NetworkVxlanPortRangeError(NeutronException):
    message = ("Invalid network VXLAN port range: '%(vxlan_range)s'")


class VxlanNetworkUnsupported(NeutronException):
    message = ("VXLAN Network unsupported.")


class DuplicatedExtension(NeutronException):
    message = ("Found duplicate extension: %(alias)s")


class DeviceIDNotOwnedByTenant(Conflict):
    message = ("The following device_id %(device_id)s is not owned by your "
                "tenant or matches another tenants router.")


class InvalidCIDR(BadRequest):
    message = ("Invalid CIDR %(input)s given as IP prefix")


class RouterNotCompatibleWithAgent(NeutronException):
    message = ("Router '%(router_id)s' is not compatible with this agent")


class DvrHaRouterNotSupported(NeutronException):
    message = ("Router '%(router_id)s' cannot be both DVR and HA")


class FailToDropPrivilegesExit(SystemExit):
    """Exit exception raised when a drop privileges action fails."""
    code = 99


class FloatingIpSetupException(NeutronException):
    def __init__(self, message=None):
        self.message = message
        super(FloatingIpSetupException, self).__init__()


class IpTablesApplyException(NeutronException):
    def __init__(self, message=None):
        self.message = message
        super(IpTablesApplyException, self).__init__()


class NetworkIdOrRouterIdRequiredError(NeutronException):
    message = ('network_id and router_id are None. One must be provided.')


class AbortSyncRouters(NeutronException):
    message = ("Aborting periodic_sync_routers_task due to an error")


# Shared *aas exceptions, pending them being refactored out of Neutron
# proper.

class FirewallInternalDriverError(NeutronException):
    """Fwaas exception for all driver errors.

    On any failure or exception in the driver, driver should log it and
    raise this exception to the agent
    """
    message = ("%(driver)s: Internal driver error.")


class MissingMinSubnetPoolPrefix(BadRequest):
    message = ("Unspecified minimum subnet pool prefix")


class EmptySubnetPoolPrefixList(BadRequest):
    message = ("Empty subnet pool prefix list")


class PrefixVersionMismatch(BadRequest):
    message = ("Cannot mix IPv4 and IPv6 prefixes in a subnet pool")


class UnsupportedMinSubnetPoolPrefix(BadRequest):
    message = ("Prefix '%(prefix)s' not supported in IPv%(version)s pool")


class IllegalSubnetPoolPrefixBounds(BadRequest):
    message = ("Illegal prefix bounds: %(prefix_type)s=%(prefixlen)s, "
                "%(base_prefix_type)s=%(base_prefixlen)s")


class IllegalSubnetPoolPrefixUpdate(BadRequest):
    message = ("Illegal update to prefixes: %(msg)s")


class SubnetAllocationError(NeutronException):
    message = ("Failed to allocate subnet: %(reason)s")


class MinPrefixSubnetAllocationError(BadRequest):
    message = ("Unable to allocate subnet with prefix length %(prefixlen)s, "
                "minimum allowed prefix is %(min_prefixlen)s")


class MaxPrefixSubnetAllocationError(BadRequest):
    message = ("Unable to allocate subnet with prefix length %(prefixlen)s, "
                "maximum allowed prefix is %(max_prefixlen)s")


class SubnetPoolDeleteError(BadRequest):
    message = ("Unable to delete subnet pool: %(reason)s")


class SubnetPoolQuotaExceeded(OverQuota):
    message = ("Per-tenant subnet pool prefix quota exceeded")


class NetworkSubnetPoolAffinityError(BadRequest):
    message = ("Subnets hosted on the same network must be allocated from "
                "the same subnet pool")
