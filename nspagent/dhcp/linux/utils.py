#!/usr/bin/env python
# encoding: utf-8
import os
import client
import threading
import gevent
import shlex
import socket
import struct
import tempfile
from common import utils
from oslo_utils import excutils
from oslo_config import cfg
from logger import log as LOG
from gevent import subprocess
from common import config


def ensure_dir(dir_path):
    """Ensure a directory with 755 permissions mode."""
    if not os.path.isdir(dir_path):
        os.makedirs(dir_path, 0o755)


def get_value_from_file(filename, converter=None):

    try:
        with open(filename, 'r') as f:
            try:
                return converter(f.read()) if converter else f.read()
            except ValueError:
                LOG.error(('Unable to convert value in %s'), filename)
    except IOError:
        LOG.debug('Unable to access %s', filename)


class RootwrapDaemonHelper(object):
    __client = None
    __lock = threading.Lock()

    def __new__(cls):
        """There is no reason to instantiate this class"""
        raise NotImplementedError()

    @classmethod
    def get_client(cls):
        with cls.__lock:
            if cls.__client is None:
                cls.__client = client.Client(
                    shlex.split(cfg.CONF.AGENT.root_helper_daemon))
            return cls.__client


def addl_env_args(addl_env):
    """Build arugments for adding additional environment vars with env"""

    # NOTE (twilson) If using rootwrap, an EnvFilter should be set up for the
    # command instead of a CommandFilter.
    if addl_env is None:
        return []
    return ['env'] + ['%s=%s' % pair for pair in addl_env.items()]


def create_process(cmd, run_as_root=False, addl_env=None):
    """Create a process object for the given command.

    The return value will be a tuple of the process object and the
    list of command arguments used to create it.
    """
    cmd = map(str, addl_env_args(addl_env) + cmd)
    if run_as_root:
        cmd = shlex.split(config.get_root_helper(cfg.CONF)) + cmd
    LOG.debug("Running command: %s", cmd)
    obj = utils.subprocess_popen(cmd, shell=False,
                                 stdin=subprocess.PIPE,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)

    return obj, cmd


def execute_rootwrap_daemon(cmd, process_input, addl_env):
    cmd = map(str, addl_env_args(addl_env) + cmd)
    # NOTE(twilson) oslo_rootwrap.daemon will raise on filter match
    # errors, whereas oslo_rootwrap.cmd converts them to return codes.
    # In practice, no neutron code should be trying to execute something that
    # would throw those errors, and if it does it should be fixed as opposed to
    # just logging the execution error.
    LOG.debug("Running command (rootwrap daemon): %s", cmd)
    client = RootwrapDaemonHelper.get_client()
    return client.execute(cmd, process_input)


def execute(cmd, process_input=None, addl_env=None,
            check_exit_code=True, return_stderr=False, log_fail_as_error=True,
            extra_ok_codes=None, run_as_root=False):
    try:
        if run_as_root and cfg.CONF.AGENT.root_helper_daemon:
            returncode, _stdout, _stderr = (
                execute_rootwrap_daemon(cmd, process_input, addl_env))
        else:
            obj, cmd = create_process(cmd, run_as_root=run_as_root,
                                      addl_env=addl_env)
            _stdout, _stderr = obj.communicate(process_input)
            returncode = obj.returncode
            obj.stdin.close()

        m = ("\nCommand: {cmd}\nExit code: {code}\nStdin: {stdin}\n"
              "Stdout: {stdout}\nStderr: {stderr}").format(
                  cmd=cmd,
                  code=returncode,
                  stdin=process_input or '',
                  stdout=_stdout,
                  stderr=_stderr)

        extra_ok_codes = extra_ok_codes or []
        if returncode and returncode in extra_ok_codes:
            returncode = None

        if returncode and log_fail_as_error:
            LOG.error(m)
        else:
            LOG.debug(m)

        if returncode and check_exit_code:
            raise RuntimeError(m)
    finally:
        # NOTE(termie): this appears to be necessary to let the subprocess
        #               call clean something up in between calls, without
        #               it two execute calls in a row hangs the second one
        gevent.sleep(0)

    return (_stdout, _stderr) if return_stderr else _stdout


def replace_file(file_name, data, file_mode=0o644):
    """Replaces the contents of file_name with data in a safe manner.

    First write to a temp file and then rename. Since POSIX renames are
    atomic, the file is unlikely to be corrupted by competing writes.

    We create the tempfile on the same device to ensure that it can be renamed.
    """

    base_dir = os.path.dirname(os.path.abspath(file_name))
    tmp_file = tempfile.NamedTemporaryFile('w+', dir=base_dir, delete=False)
    tmp_file.write(data)
    tmp_file.close()
    os.chmod(tmp_file.name, file_mode)
    os.rename(tmp_file.name, file_name)

