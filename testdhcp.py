#!/usr/bin/env python
# encoding: utf-8

import requests
import os
import json
import time
network = { "id": "44783e1a-63fe-43d5-9989-e1515c24eecd",
            "interfacename":"br-int",
            "subnets": [{
                                    "id": "ec1028b2-7cb0-4feb-b974-6b8ea7e7f08f",
                                    "ip_version": 4,
                                    "cidr":"10.10.40.0/24",
                                    "enable_dhcp": True,
                                    "network_id" : "44783e1a-63fe-43d5-9989-e1515c24eecd",
                                    "admin_state_up": True,
                                    "dns_nameservers":["114.114.114.114"],
                                    "host_routes":"",
                                    "ipv6_ra_mode": None,
                                    "ipv6_address_mode": None,
                                    "gateway_ip": "10.10.40.1",

                                    #"allocation_pools": [{"start": "10.10.40.2", "end": "10.10.40.254"}],
                                    },
                                    {
                                    "id": "ec1028b2-7cb0-4feb-b974-6b8ea7e7f082",
                                    "ip_version": 4,
                                    "cidr":"10.10.30.0/24",
                                    "enable_dhcp": True,
                                    "network_id" : "44783e1a-63fe-43d5-9989-e1515c24eecd",
                                    "admin_state_up": True,
                                    "dns_nameservers":["114.114.114.114"],
                                    "host_routes":"",
                                    "ipv6_ra_mode": None,
                                    "ipv6_address_mode": None,
                                    "gateway_ip": "10.10.30.1",

                                    #"allocation_pools": [{"start": "10.10.30.2", "end": "10.10.30.254"}],
                                    }   ],
            "ports": [{ "network_id": "44783e1a-63fe-43d5-9989-e1515c24eecd",
                        "admin_state_up":True,
                        "id":"cad98138-6e5f-4f83-a4c5-5497fa4758b4",
                        "mac_address": "fa:16:3e:65:29:6d",
                        "device_owner": "nova:computer",
                        "fixed_ips":
                            [{
                                u'subnet_id': u'ec1028b2-7cb0-4feb-b974-6b8ea7e7f08f',
                                u'subnet': {
                                   u'enable_dhcp': True,
                                   #u'network_id': u'8165bc3d-400a-48a0-9186-bf59f7f94b05',
                                   u'dns_nameservers': [],
                                   u'ipv6_ra_mode': None,
                                  #u'allocation_pools': [{u'start': u'10.10.40.2', u'end': u'10.10.40.254'}],
                                   u'gateway_ip': u'10.10.40.1',
                                   u'ip_version': 4,
                                   u'host_routes': [],
                                   u'cidr': u'10.10.40.0/24',
                                   u'ipv6_address_mode': None,
                                   #u'id': u'ec1028b2-7cb0-4feb-b974-6b8ea7e7f08f',
                                },
                                 u'ip_address': u'10.10.40.3'
                                }],
                        },
                        {
                        "network_id": "44783e1a-63fe-43d5-9989-e1515c24eecd",
                        "admin_state_up":True,
                        "id":"cad98138-6e5f-4f83-a4c5-5497fa4758b2",
                        "mac_address": "fa:16:3e:65:29:62",
                        "device_owner": "nova:computer",
                        "fixed_ips":
                            [{
                                u'subnet_id': u'ec1028b2-7cb0-4feb-b974-6b8ea7e7f082',
                                u'subnet': {
                                   u'enable_dhcp': True,
                                 #  u'network_id': u'8165bc3d-400a-48a0-9186-bf59f7f94b05',
                                   u'dns_nameservers': [],
                                   u'ipv6_ra_mode': None,
                                   u'gateway_ip': u'10.10.30.1',
                                   u'ip_version': 4,
                                   u'host_routes': [],
                                   u'cidr': u'10.10.30.0/24',
                                   u'ipv6_address_mode': None,
                                },
                                 u'ip_address': u'10.10.30.4'
                                }],
                        },
                       {
                            u'status': u'ACTIVE',
                            u'allowed_address_pairs': [],
                            u'extra_dhcp_opts': [],
                            u'device_owner': u'network:dhcp',
                            u'fixed_ips':
                                    [
                                        {
                                        u'subnet_id': u'ec1028b2-7cb0-4feb-b974-6b8ea7e7f082',
                                        u'subnet': {
                                            u'enable_dhcp': True,
                                            u'dns_nameservers': [],
                                            u'ipv6_ra_mode': None,
                                            u'gateway_ip': u'10.10.30.1',
                                            u'ip_version': 4,
                                            u'host_routes': [],
                                            u'cidr': u'10.10.30.0/24',
                                            u'ipv6_address_mode': None,
                                            },
                                        u'ip_address': u'10.10.30.2'
                                        },

                                        {
                                        u'subnet_id': u'ec1028b2-7cb0-4feb-b974-6b8ea7e7f08f',
                                        u'subnet': {
                                            u'enable_dhcp': True,
                                            u'dns_nameservers': [],
                                            u'ipv6_ra_mode': None,
                                            u'gateway_ip': u'10.10.40.1',
                                            u'ip_version': 4,
                                            u'host_routes': [],
                                            u'cidr': u'10.10.40.0/24',
                                            u'ipv6_address_mode': None,
                                            },
                                        u'ip_address': u'10.10.40.2'
                                        }
                                    ],
                            u'id': u'712a2c63-e610-42c9-9ab3-4e8b6540d125',
                            u'device_id': u'dhcp44783e1a-63fe-43d5-9989-e1515c24eecd',
                            u'admin_state_up': True,
                            }

                        ],
        "admin_state_up":True,
        "vlantag":1010,
        }

network_data = {"network": network }

def create_net_work():
    url =  "http://192.168.49.22:20010/v1/dhcp_network/"
    headers = {'content-type': 'application/json'}
    try:
        print url
        payload = json.dumps(network_data)
        r = requests.post(url, payload, headers = headers, verify=False)
        print r
        print r.text, r.tatus_code
        resp = r.json()
        print resp
    except Exception as e:
        print "Exception"
        print r.text

def delete_net_work():
    url =  "http://192.168.49.22:20010/v1/dhcp_network/44783e1a-63fe-43d5-9989-e1515c24eecd"
    headers = {'content-type': 'application/json'}
    try:
        print url
        payload = json.dumps(network_data)
        r = requests.delete(url, headers = headers, verify=False)
        print r
        print r.text, r.tatus_code
    except Exception as e:
        print "Exception"
        print r.text

def delete_subnet():
    url =  "http://192.168.49.22:20010/v1/dhcp_subnet/ec1028b2-7cb0-4feb-b974-6b8ea7e7f08f"
    headers = {'content-type': 'application/json'}
    try:
        print url
        r = requests.delete(url, headers = headers, verify=False)
        print r
        print r.text, r.tatus_code
    except Exception as e:
        print "Exception"
        print r.text

def delete_port():
    url =  "http://192.168.49.22:20010/v1/dhcp_port/cad98138-6e5f-4f83-a4c5-5497fa4758b4"
    headers = {'content-type': 'application/json'}
    payload = json.dumps(network_data)
    try:
        print url
        r = requests.delete(url, data = payload,headers = headers, verify=False)
        print r
        print r.text, r.tatus_code
    except Exception as e:
        print "Exception"
        print r.text



if __name__ == '__main__':
    create_net_work()
   # delete_net_work()
    #delete_subnet()
    #delete_port()
