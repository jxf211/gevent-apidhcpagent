# Copyright (c) 2014 Mirantis Inc.
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

import logging
from multiprocessing import managers
from multiprocessing import util as mp_util
import os
import subprocess
import threading
import weakref
# Copyright (c) 2014 Mirantis Inc.
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


import functools
import os
import shutil
import signal
import stat
import sys
import tempfile
import wrapper

LOG = logging.getLogger(__name__)

# Since multiprocessing supports only pickle and xmlrpclib for serialization of
# RPC requests and responses, we declare another 'jsonrpc' serializer

#managers.listener_client['jsonrpc'] = jsonrpc.JsonListener, jsonrpc.JsonClient


class RootwrapClass(object):
    def __init__(self, config, filters):
        self.config = config
        self.filters = filters

    def run_one_command(self, userargs, stdin=None):
        obj = wrapper.start_subprocess(
            self.filters, userargs,
            exec_dirs=self.config.exec_dirs,
            log=self.config.use_syslog,
            close_fds=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)
        out, err = obj.communicate(stdin)
        return obj.returncode, out, err

    def shutdown(self):
        # Suicide to force break of the main thread
        os.kill(os.getpid(), signal.SIGINT)


