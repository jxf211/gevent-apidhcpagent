#!/usr/bin/env python
# encoding: utf-8

import os
from gevent.pool import Pool
import json
from oslo_config import cfg
from oslo_utils import importutils
from linux import dhcp
from linux import external_process
from linux import utils as linux_utils
from common import exceptions
from common import utils
import traceback
from webob import exc
from logger import log as LOG


class DhcpAgent(object):
    """DHCP agent service manager."""

    def __init__(self, host=None):
        if not host:
            host = cfg.CONF.host
        self.host = host
        self.conf = cfg.CONF
        self.pool = Pool(cfg.CONF.num_sync_threads)
        self.cache = NetworkCache()
        self.dhcp_driver_cls = importutils.import_class(self.conf.dhcp_driver)
        self.plugin_rpc = None
       # create dhcp dir to store dhcp info
        dhcp_dir = os.path.dirname("/%s/dhcp/" % self.conf.state_path)
        linux_utils.ensure_dir(dhcp_dir)
        self.dhcp_version = self.dhcp_driver_cls.check_version()
        self._populate_networks_cache()
        self._process_monitor = external_process.ProcessMonitor(
            config=self.conf,
            resource_type='dhcp')

    def _populate_networks_cache(self):
        """Populate the networks cache when the DHCP-agent starts."""
        try:
            LOG.debug("conf:%s", self.conf)
            existing_networks = self.dhcp_driver_cls.existing_dhcp_networks(
                self.conf
            )
            for net_id in existing_networks:
                net = dhcp.NetModel(self.conf.use_namespaces,
                                    {"id": net_id,
                                     "subnets": [],
                                     "ports": []})
                self.cache.put(net)
            LOG.debug("network_info:%s", self.cache.get_state())
        except NotImplementedError:
            # just go ahead with an empty networks cache
            LOG.debug("The '%s' DHCP-driver does not support retrieving of a "
                      "list of existing networks",
                      self.conf.dhcp_driver)

    def call_driver(self, action, network, **action_kwargs):
        """Invoke an action on a DHCP driver instance."""
        LOG.debug('Calling driver for network: %(net)s action: %(action)s',
                  {'net': network.id, 'action': action})
        try:
            # the Driver expects something that is duck typed similar to
            # the base models.
            driver = self.dhcp_driver_cls(self.conf,
                                          network,
                                          self._process_monitor,
                                          self.dhcp_version,
                                          self.plugin_rpc)
            getattr(driver, action)(**action_kwargs)
            return True
        except exceptions.Conflict:
            # No need to resync here, the agent will receive the event related
            # to a status update for the network
            LOG.error(traceback.format_exc())
            LOG.warning(('Unable to %(action)s dhcp for %(net_id)s: there '
                            'is a conflict with its current state; please '
                            'check that the network and/or its subnet(s) '
                            'still exist.'),
                        {'net_id': network.id, 'action': action})
        except Exception as e:
            if getattr(e, 'exc_type', '') != 'IpAddressGenerationFailure':
                # Don't resync if port could not be created because of an IP
                # allocation failure. When the subnet is updated with a new
                # allocation pool or a port is  deleted to free up an IP, this
                # will automatically be retried on the notification
                LOG.error(traceback.format_exc())
                LOG.debug("Network %s has been deleted.", network.id)
            else:
                LOG.exception(('Unable to %(action)s dhcp for %(net_id)s.'),
                              {'net_id': network.id, 'action': action})
                LOG.error("enable dhcp err:%s", e)
                LOG.error(traceback.format_exc())

    def enable_dhcp_helper(self, network_id, network_rs=None):
        """Enable DHCP for a network that meets enabling criteria."""
        if network_rs:
            network = dhcp.NetModel(self.conf.use_namespaces, network_rs)
        else:
            LOG.err("payload resource no network_rs")
        if network:
            self.configure_dhcp_for_network(network)

    def safe_configure_dhcp_for_network(self, network):
        try:
            self.configure_dhcp_for_network(network)
        except (exceptions.NetworkNotFound, RuntimeError):
            LOG.warn(('Network %s may have been deleted and its resources '
                         'may have already been disposed.'), network.id)

    def configure_dhcp_for_network(self, network):
        if not network.admin_state_up:
            return

        for subnet in network.subnets:
            if subnet.enable_dhcp:
                LOG.debug("subnet:%s", subnet)
                if self.call_driver('enable', network):
                    self.cache.put(network)
                break

    def disable_dhcp_helper(self, network_id):
        """Disable DHCP for a network known to the agent."""
        network = self.cache.get_network_by_id(network_id)
        if network:
            if self.call_driver('disable', network):
                self.cache.remove(network)

    def refresh_dhcp_helper(self, network_id, network=None):
        """Refresh or disable DHCP for a network depending on the current state
        of the network.
        """
        old_network = self.cache.get_network_by_id(network_id)
        if not old_network:
            # DHCP current not running for network.
            return self.enable_dhcp_helper(network_id, network)
        network = dhcp.NetModel(self.conf.use_namespaces, network)
        if not network:
            return

        old_cidrs = set(s.cidr for s in old_network.subnets if s.enable_dhcp)
        new_cidrs = set(s.cidr for s in network.subnets if s.enable_dhcp)

        if new_cidrs and old_cidrs == new_cidrs:
            self.call_driver('reload_allocations', network)
            self.cache.put(network)
        elif new_cidrs:
            if self.call_driver('restart', network):
                self.cache.put(network)
        else:
            self.disable_dhcp_helper(network.id)

    def network_create_end(self, req=None, **kwargs):
        try:
            payload = json.loads(req.body)
            network_id = payload['network']['id']
            network = payload['network']
            #self.pool.spawn(self._network_create, network_id, network)
            self._network_create(network_id, network)
            LOG.debug("network_info:%s", self.cache.get_state())
            return  200, "SUCCESS"
        except Exception as err:
            LOG.error(err)
            raise Exception('Error: %s' % err)

    @utils.synchronized('dhcp-agent')
    def _network_create(self, network_id, network):
        """Handle the network.create.end notification event."""
        try:
            self.enable_dhcp_helper(network_id, network)
        except Exception as err:
            LOG.error(err)
            LOG.error(traceback.format_exc())
            raise Exception('Error: %s' % err)

    def network_updata_end(self, req=None, **kwargs):
        try:
            payload = json.loads(req.body)
            network_id = payload['network']['id']
            network = payload['network']
            #self.pool.spawn(self._network_updata, network_id, network)
            self._network_updata(network_id, network)
            return 200, "SUCCESS"
        except Exception as err:
            LOG.error(err)
            raise Exception('Error: %s' % err)

    @utils.synchronized('dhcp-agent')
    def _network_update(self, network_id, network):
        """Handle the network.update.end notification event."""
        self.enable_dhcp_helper(network_id, network)

    def network_delete_end(self, req=None, network_id=None,**kwargs):
        try:
            msg = "OK"
            network = self.cache.get_network_by_id(network_id)
            if network:
                #self.pool.spawn(self._network_delete, network_id)
                self._network_delete(network_id)
            else:
                msg = "network_id: %s. network does not exist" % network_id
                LOG.debug(msg)
            return 200, msg
        except Exception  as err:
            LOG.error(err)
            raise Exception('Error: %s' % err)

    @utils.synchronized('dhcp-agent')
    def _network_delete(self, network_id=None):
        """Handle the network.delete.end notification event."""
        try:
            self.disable_dhcp_helper(network_id)
        except Exception  as err:
            LOG.error(err)
            raise Exception('Error: %s' % err)

    def subnet_update_end(self, req=None, **kwargs):
        try:
            msg = 'SUCCESS'
            payload = json.loads(req.body)
            network = payload['network']
            network_id = network['id']
            #self.pool.spawn(self._subnet_update, network_id, network)
            LOG.debug("network_info:%s", self.cache.get_state())
            ret = self._subnet_update(network_id, network)
            return 200, msg
        except Exception as err:
            LOG.error(err)
            raise Exception('Err: %s ' % err)

    @utils.synchronized('dhcp-agent')
    def _subnet_update(self, network_id, network):
        """Handle the subnet.update.end notification event."""
        self.refresh_dhcp_helper(network_id, network)

    # Use the update handler for the subnet create event.
    subnet_create_end = subnet_update_end

    def subnet_delete_end(self, req=None, subnet_id=None, **kwargs):
        try:
            subnet = self.cache.get_subnet_by_id(subnet_id)
            if subnet:
                network = self.cache.get_network_by_subnet_id(subnet_id)
                self.cache.remove_subnet(subnet)
                #self.pool.spawn(self._subnet_delete, network.id, network)
                self._subnet_delete(network.id, network)
            else:
                LOG.debug("subnet_id: %s. subnet does not exist", subnet_id)
        except Exception as err:
            LOG.error(err)
            raise Exception('Err: %s' % err)

    @utils.synchronized('dhcp-agent')
    def _subnet_delete(self, network_id, network):
        """Handle the subnet.delete.end notification event."""
        self.refresh_dhcp_helper(network_id, network)

    def port_update_end(self, req=None, **kwargs):
        try:
            payload = json.loads(req.body)
            updated_port = dhcp.DictModel(payload)
            LOG.debug("updated_port:%s", updated_port)
            if updated_port:
                #self.pool.spawn(self._port_update, updated_port)
                self._port_update(updated_port)
            else:
                LOG.debug("updated_port is NULL")
                return 200, "SUCCESS"
        except Exception as err:
            LOG.error(err)
            raise Exception('Err: %s' % err)

    @utils.synchronized('dhcp-agent')
    def _port_update(self, updated_port):
        """Handle the port.update.end notification event."""
        network = self.cache.get_network_by_id(updated_port.network_id)
        LOG.debug("network:%s", network)
        if network:
            driver_action = 'reload_allocations'
            if self._is_port_on_this_agent(updated_port):
                orig = self.cache.get_port_by_id(updated_port.id)
                if orig:
                    # assume IP change if not in cache
                    old_ips = {i['ip_address'] for i in orig['fixed_ips'] or []}
                else:
                    old_ips = {}

                new_ips = {i['ip_address'] for i in updated_port['fixed_ips']}
                if old_ips != new_ips:
                    driver_action = 'restart'
            self.cache.put_port(updated_port)
            self.call_driver(driver_action, network)
        else:
            msg = "network_id: %s. network does not exist" % network_id
            LOG.debug(msg)

    def _is_port_on_this_agent(self, port):
        thishost = utils.get_dhcp_agent_device_id(
            port['network_id'], self.conf.host)
        return True
        #return port['device_id'] == thishost

    # Use the update handler for the port create event.
    port_create_end = port_update_end

    def port_delete_end(self, req=None, port_id=None, **kwargs):
        try:
            msg = "SUCCESS"
            port = self.cache.get_port_by_id(port_id)
            if port:
                #self.pool.spawn(self._port_delete, port_id)
                self._port_delete(port_id)
            else:
                msg = "port_id: %s. PORT does not exist" % port_id
                LOG.debug(msg)
            return 200, msg
        except Exception as err:
            LOG.error(err)
            raise Exception('Err: %s' %  err)

    @utils.synchronized('dhcp-agent')
    def _port_delete(self, port_id):
        """Handle the port.delete.end notification event."""
        network = self.cache.get_network_by_port_id(port_id)
        port = self.cache.get_port_by_id(port_id)
        self.cache.remove_port(port)
        self.call_driver('reload_allocations', network)

    def default(self, req=None, **kwargs):
        raise exc.HTTPNotFound()

class NetworkCache(object):
    """Agent cache of the current network state."""
    def __init__(self):
        self.cache = {}
        self.subnet_lookup = {}
        self.port_lookup = {}

    def get_network_ids(self):
        return self.cache.keys()

    def get_network_by_id(self, network_id):
        return self.cache.get(network_id)

    def get_network_by_subnet_id(self, subnet_id):
        return self.cache.get(self.subnet_lookup.get(subnet_id))

    def get_network_by_port_id(self, port_id):
        return self.cache.get(self.port_lookup.get(port_id))

    def put(self, network):
        if network.id in self.cache:
            self.remove(self.cache[network.id])

        self.cache[network.id] = network

        for subnet in network.subnets:
            self.subnet_lookup[subnet.id] = network.id

        for port in network.ports:
            self.port_lookup[port.id] = network.id

    def remove(self, network):
        del self.cache[network.id]

        for subnet in network.subnets:
            del self.subnet_lookup[subnet.id]

        for port in network.ports:
            del self.port_lookup[port.id]

    def put_port(self, port):
        network = self.get_network_by_id(port.network_id)
        for index in range(len(network.ports)):
            if network.ports[index].id == port.id:
                network.ports[index] = port
                break
        else:
            network.ports.append(port)

        self.port_lookup[port.id] = network.id

    def remove_port(self, port):
        network = self.get_network_by_port_id(port.id)

        for index in range(len(network.ports)):
            if network.ports[index] == port:
                del network.ports[index]
                del self.port_lookup[port.id]
                break

    def remove_subnet(self, subnet):
        network = self.get_network_by_subnet_id(subnet.id)
        LOG.debug("remove_subnet")
        for index in range(len(network.subnets)):
            if network.subnets[index] == subnet:
                for port in network.ports:
                    for fixed_ip in port.fixed_ips:
                        if fixed_ip.subnet_id == subnet.id:
                            port.fixed_ips.remove(fixed_ip)
                        if len(port.fixed_ips) == 0:
                            self.remove_port(port)
                del network.subnets[index]
                del self.subnet_lookup[subnet.id]
                break

    def get_port_by_id(self, port_id):
        network = self.get_network_by_port_id(port_id)
        if network:
            for port in network.ports:
                if port.id == port_id:
                    return port

    def get_subnet_by_id(self, subnet_id):
        network = self.get_network_by_subnet_id(subnet_id)
        if network:
            for subnet in network.subnets:
                if subnet.id == subnet_id:
                    return subnet

    def get_state(self):
        net_ids = self.get_network_ids()
        num_nets = len(net_ids)
        num_subnets = 0
        num_ports = 0
        for net_id in net_ids:
            network = self.get_network_by_id(net_id)
            num_subnets += len(network.subnets)
            num_ports += len(network.ports)
        return {'networks': num_nets,
                'subnets': num_subnets,
                'ports': num_ports}



