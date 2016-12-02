#!/usr/bin/env python
# encoding: utf-8
from gevent.wsgi import WSGIServer
import argparse
import os
import signal
import sys
import traceback
import logging as syslog
from oslo_config import cfg
from utils import get_ip_address
from common import config as common_config
from nspagent.dhcp.linux import interface
from router import API
from nspagent.dhcp.linux import daemon
from logger import log as LOG
import logger


common_cli_opts = [
    cfg.BoolOpt('daemon',
                short='m',
                default=False,
                help='run in background'),
    ]

class DeamonMain(daemon.Daemon):
    def __init__(self, ip, port, pid_file):
        self.register_options()
        common_config.init(sys.argv[1:])
        logger.init_logger()
        LOG.debug('Full set of CONF:')
        cfg.CONF.log_opt_values(LOG, syslog.DEBUG)
        self._ip = ip
        self._port = port
        super(DeamonMain, self).__init__(pid_file)

    def sigterm_handler(signal, frame):
            sys.exit(0)

    def run(self):
        signal.signal(signal.SIGTERM, self.sigterm_handler)
        LOG.info('Launching DhcpAgent API Stack (DHCP_AGENT) ...')
        try:
            LOG.info('Gevent approaching ... server ip:%s port:%s',
                        self._ip, self._port)
            app = API()
            server = WSGIServer((self._ip, self._port), app)
            server.serve_forever()
        except Exception as e:
            LOG.error('Exception: %s' % e)
            LOG.error('%s' % traceback.format_exc())
            sys.exit(1)

    def register_options(self):
        common_config.register_conf()
        cfg.CONF.register_cli_opts(common_cli_opts)
        pass

if __name__== '__main__':
    #local_ctrl_ip = get_ip_address("nspbr0")
    main = DeamonMain('192.168.49.22', 20010, '/var/dhcpagent/pid')
    if cfg.CONF.daemon:
        main.start()
    else:
        main.run()

