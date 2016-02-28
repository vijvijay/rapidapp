# -*- coding: utf-8 -*-

# Copyright (C) 2010-2014 by Mike Gabriel <mike.gabriel@das-netzwerkteam.de>
#
# Python X2Go is free software; you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# Python X2Go is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program; if not, write to the
# Free Software Foundation, Inc.,
# 51 Franklin St, Fifth Floor, Boston, MA 02110-1301, USA.

"""\
X2GoProxy class - proxying your connection through NX3 and others.

"""
__NAME__ = 'x2goproxy-pylib'

# modules
import gevent
import os
import copy
import threading
import socket

# Python X2Go modules
import x2go.forward as forward
import x2go.log as log
import x2go.utils as utils
import x2go.x2go_exceptions as x2go_exceptions

from x2go.defaults import X2GOCLIENT_OS as _X2GOCLIENT_OS
if _X2GOCLIENT_OS in ("Windows"):
    import subprocess
else:
    import x2go.gevent_subprocess as subprocess
    from x2go.x2go_exceptions import WindowsError

from x2go.defaults import LOCAL_HOME as _LOCAL_HOME
from x2go.defaults import X2GO_SESSIONS_ROOTDIR as _X2GO_SESSIONS_ROOTDIR


class X2GoProxy(threading.Thread):
    """\
    X2GoProxy is an abstract class for X2Go proxy connections.

    This class needs to be inherited from a concrete proxy class. Only 
    currently available proxy class is: L{x2go.backends.proxy.nx3.X2GoProxy}.

    """
    PROXY_CMD = ''
    """Proxy command. Needs to be set by a potential child class, might be OS specific."""
    PROXY_ARGS = []
    """Arguments to be passed to the proxy command. This needs to be set by a potential child class."""
    PROXY_ENV = {}
    """Provide environment variables to the proxy command. This also needs to be set by a child class."""

    session_info = None
    session_log_stdout = None
    session_log_stderr = None
    fw_tunnel = None
    proxy = None

    def __init__(self, session_info=None, 
                 ssh_transport=None, session_log="session.log", session_errors="session.err",
                 sessions_rootdir=os.path.join(_LOCAL_HOME, _X2GO_SESSIONS_ROOTDIR),
                 proxy_options={},
                 session_instance=None,
                 logger=None, loglevel=log.loglevel_DEFAULT, ):
        """\
        @param session_info: session information provided as an C{X2GoServerSessionInfo*} backend
            instance
        @type session_info: C{X2GoServerSessionInfo*} instance
        @param ssh_transport: SSH transport object from C{paramiko.SSHClient}
        @type ssh_transport: C{paramiko.Transport} instance
        @param session_log: name of the proxy's session logfile
        @type session_log: C{str}
        @param sessions_rootdir: base dir where X2Go session files are stored (by default: ~/.x2go)
        @type sessions_rootdir: C{str}
        @param proxy_options: a set of very L{base.X2GoProxy} backend specific options; any option that is not known
            to the L{base.X2GoProxy} backend will simply be ignored
        @type proxy_options: C{dict}
        @param logger: you can pass an L{X2GoLogger} object to the
            L{base.X2GoProxy} constructor
        @param session_instance: the L{X2GoSession} instance this L{base.X2GoProxy} instance belongs to
        @type session_instance: L{X2GoSession} instance
        @type logger: L{X2GoLogger} instance
        @param loglevel: if no L{X2GoLogger} object has been supplied a new one will be
            constructed with the given loglevel
        @type loglevel: int

        """
        if logger is None:
            self.logger = log.X2GoLogger(loglevel=loglevel)
        else:
            self.logger = copy.deepcopy(logger)
        self.logger.tag = __NAME__

        self.sessions_rootdir = sessions_rootdir
        self.session_info = session_info
        self.session_name = self.session_info.name
        self.ssh_transport = ssh_transport
        self.session_log = session_log
        self.session_errors = session_errors
        self.proxy_options = proxy_options
        self.session_instance = session_instance
        self.PROXY_ENV = os.environ.copy()
        self.proxy = None
        self.subsystem = 'X2Go Proxy'

        threading.Thread.__init__(self)
        self.daemon = True

    def __del__(self):
        """\
        On instance destruction make sure this proxy thread is stopped properly.

        """
        self.stop_thread()

    def _tidy_up(self):
        """\
        Close any left open port forwarding tunnel, also close session log file,
        if left open.

        """
        if self.proxy:
            self.logger('Shutting down X2Go proxy subprocess', loglevel=log.loglevel_DEBUG)
            try:
                self.proxy.kill()
            except OSError, e:
                self.logger('X2Go proxy shutdown gave a message that we may ignore: %s' % str(e), loglevel=log.loglevel_WARN)
            self.proxy = None
        if self.fw_tunnel is not None:
            self.logger('Shutting down Paramiko/SSH forwarding tunnel', loglevel=log.loglevel_DEBUG)
            forward.stop_forward_tunnel(self.fw_tunnel)
            self.fw_tunnel = None
        if self.session_log_stdout is not None:
            self.session_log_stdout.close()
        if self.session_log_stderr is not None:
            self.session_log_stderr.close()

    def stop_thread(self):
        """\
        End the thread runner and tidy up.

        """
        self._keepalive = False
        # wait for thread loop to finish...
        while self.proxy is not None:
            gevent.sleep(.5)

    def run(self):
        """\
        Start the X2Go proxy command. The X2Go proxy command utilizes a
        Paramiko/SSH based forwarding tunnel (openssh -L option). This tunnel
        gets started here and is forked into background (Greenlet/gevent).

        """
        self._keepalive = True
        self.proxy = None

        if self.session_info is None or self.ssh_transport is None:
            return None

        try:
            os.makedirs(self.session_info.local_container)
        except OSError, e:
            if e.errno == 17:
                # file exists
                pass

        local_graphics_port = self.session_info.graphics_port
        try:
            if self.ssh_transport.getpeername()[0] in ('::1', '127.0.0.1', 'localhost', 'localhost.localdomain'):
                local_graphics_port += 10000
        except socket.error:
            raise x2go_exceptions.X2GoControlSessionException('The control session has died unexpectedly.')
        local_graphics_port = utils.detect_unused_port(preferred_port=local_graphics_port)

        self.fw_tunnel = forward.start_forward_tunnel(local_port=local_graphics_port,
                                                      remote_port=self.session_info.graphics_port,
                                                      ssh_transport=self.ssh_transport,
                                                      session_instance=self.session_instance,
                                                      session_name=self.session_name,
                                                      subsystem=self.subsystem,
                                                      logger=self.logger,
                                                     )

        # update the proxy port in PROXY_ARGS
        self._update_local_proxy_socket(local_graphics_port)

        self.session_log_stdout = open('%s/%s' % (self.session_info.local_container, self.session_log, ), 'a')
        self.session_log_stderr = open('%s/%s' % (self.session_info.local_container, self.session_log, ), 'a')

        _stdin = None
        _shell = False
        if _X2GOCLIENT_OS == 'Windows':
            _stdin = file('nul', 'r')
            _shell = True

        # allow inheriting classes to do something with backend specific proxy_options...
        self.process_proxy_options()

        # if everything is in place, generate the command line for the subprocess call
        cmd_line = self._generate_cmdline()
        self.logger('forking threaded subprocess: %s' % " ".join(cmd_line), loglevel=log.loglevel_DEBUG)

        while not self.proxy:
            gevent.sleep(.2)
            p = self.proxy = subprocess.Popen(cmd_line,
                                              env=self.PROXY_ENV,
                                              stdin=_stdin,
                                              stdout=self.session_log_stdout,
                                              stderr=self.session_log_stderr,
                                              shell=_shell)

        while self._keepalive:
            gevent.sleep(1)

        if _X2GOCLIENT_OS == 'Windows':
            _stdin.close()
        try:
            p.terminate()
            self.logger('terminating proxy: %s' % p, loglevel=log.loglevel_DEBUG)
        except OSError, e:
            if e.errno == 3:
                # No such process
                pass
        except WindowsError:
            pass

        self._tidy_up()

    def process_proxy_options(self):
        """\
        Override this method to incorporate elements from C{proxy_options} 
        into actual proxy subprocess execution.

        This method (if overridden) should (by design) never fail nor raise an exception.
        Make sure to catch all possible errors appropriately.

        If you want to log ignored proxy_options then

            1. remove processed proxy_options from self.proxy_options
            2. once you have finished processing the proxy_options call
            the parent class method L{x2go.backends.proxy.base.X2GoProxy.process_proxy_options()}

        """
        # do the logging of remaining options
        if self.proxy_options:
            self.logger('ignoring non-processed proxy options: %s' % self.proxy_options, loglevel=log.loglevel_INFO)

    def _update_local_proxy_socket(self, port):
        pass

    def _generate_cmdline(self):
        return ''

    def start_proxy(self):
        """\
        Start the thread runner and wait for the proxy to come up.

        @return: a subprocess instance that knows about the externally started proxy command.
        @rtype: C{obj}

        """
        threading.Thread.start(self)

        # wait for proxy to get started
        _count = 0
        _maxwait = 40
        while self.proxy is None and _count < _maxwait:
            _count += 1
            self.logger('waiting for proxy to come up: 0.4s x %s' % _count, loglevel=log.loglevel_DEBUG)
            gevent.sleep(.4)

        if self.proxy:

            # also wait for fw_tunnel to become active
            _count = 0
            _maxwait = 40
            while self.fw_tunnel and (not self.fw_tunnel.is_active) and (not self.fw_tunnel.failed) and (_count < _maxwait):
                _count += 1
                self.logger('waiting for port fw tunnel to come up: 0.5s x %s' % _count, loglevel=log.loglevel_DEBUG)
                gevent.sleep(.5)

        return self.proxy, bool(self.proxy) and (self.fw_tunnel and self.fw_tunnel.is_active)

    def ok(self):
        """\
        Check if a proxy instance is up and running.

        @return: Proxy state, C{True} for proxy being up-and-running, C{False} otherwise
        @rtype C{bool}

        """
        return bool(self.proxy and self.proxy.poll() is None) and self.fw_tunnel.is_active
