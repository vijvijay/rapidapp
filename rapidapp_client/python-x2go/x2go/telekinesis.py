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
X2GoTelekinesisClient class - Connect to Telekinesis Server on X2Go Server.

"""
__NAME__ = 'x2gotelekinesisclient-pylib'

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

from x2go.defaults import LOCAL_HOME as _LOCAL_HOME
from x2go.defaults import X2GO_SESSIONS_ROOTDIR as _X2GO_SESSIONS_ROOTDIR
from x2go.defaults import CURRENT_LOCAL_USER as _CURRENT_LOCAL_USER


class X2GoTelekinesisClient(threading.Thread):
    """\
    Telekinesis is a communication framework used by X2Go.

    This class implements the startup of the telekinesis client used by
    Python X2Go.

    """
    TEKICLIENT_CMD = 'telekinesis-client'
    """Telekinesis client command. Might be OS specific."""
    TEKICLIENT_ARGS = ['-setWORMHOLEPORT={port}', '-setX2GOSID={sid}', ]
    """Arguments to be passed to the Telekinesis client."""
    TEKICLIENT_ENV = {}
    """Provide environment variables to the Telekinesis client command."""

    def __init__(self, session_info=None, 
                 ssh_transport=None,
                 sessions_rootdir=os.path.join(_LOCAL_HOME, _X2GO_SESSIONS_ROOTDIR),
                 session_instance=None,
                 logger=None, loglevel=log.loglevel_DEFAULT, ):
        """\
        @param session_info: session information provided as an C{X2GoServerSessionInfo*} backend
            instance
        @type session_info: C{X2GoServerSessionInfo*} instance
        @param ssh_transport: SSH transport object from C{paramiko.SSHClient}
        @type ssh_transport: C{paramiko.Transport} instance
        @param sessions_rootdir: base dir where X2Go session files are stored (by default: ~/.x2go)
        @type sessions_rootdir: C{str}
        @param logger: you can pass an L{X2GoLogger} object to the
            L{X2GoTelekinesisClient} constructor
        @param session_instance: the L{X2GoSession} instance this C{X2GoProxy*} instance belongs to
        @type session_instance: L{X2GoSession} instance
        @type logger: L{X2GoLogger} instance
        @param loglevel: if no L{X2GoLogger} object has been supplied a new one will be
            constructed with the given loglevel
        @type loglevel: int

        """
        self.tekiclient_log_stdout = None
        self.tekiclient_log_stderr = None
        self.tekiclient_datalog_stdout = None
        self.tekiclient_datalog_stderr = None
        self.fw_ctrl_tunnel = None
        self.fw_data_tunnel = None
        self.telekinesis_client = None
        self.telekinesis_sshfs = None

        if ssh_transport is None:
            # we cannot go on without a valid SSH transport object
            raise x2go_exceptions.X2GoTelekinesisClientException('SSH transport not available')

        if session_instance is None:
            # we can neither go on without a valid X2GoSession instance
            raise x2go_exceptions.X2GoTelekinesisClientException('X2GoSession instance not available')

        if logger is None:
            self.logger = log.X2GoLogger(loglevel=loglevel)
        else:
            self.logger = copy.deepcopy(logger)
        self.logger.tag = __NAME__

        if self.logger.get_loglevel() & log.loglevel_DEBUG:
            self.TEKICLIENT_ARGS.extend(['-setDEBUG=1',])

        self.sessions_rootdir = sessions_rootdir
        self.session_info = session_info
        self.session_name = self.session_info.name
        self.ssh_transport = ssh_transport
        self.session_instance = session_instance
        self.tekiclient = None
        self.tekiclient_log = 'telekinesis-client.log'
        self.tekiclient_datalog = 'telekinesis-client-sshfs.log'
        self.TEKICLIENT_ENV = os.environ.copy()
        self.local_tekictrl_port = self.session_info.tekictrl_port
        self.local_tekidata_port = self.session_info.tekidata_port

        threading.Thread.__init__(self)
        self.daemon = True

    def __del__(self):
        """\
        On instance destruction make sure this telekinesis client thread is stopped properly.

        """
        self.stop_thread()

    def has_telekinesis_client(self):
        """\
        Test if the Telekinesis client command is installed on this machine.

        @return: C{True} if the Telekinesis client command is available
        @rtype: C{bool}

        """
        ###
        ### FIXME: Test if user is in fuse group, as well!!!
        ###
        if utils.which('telekinesis-client'):
            return True
        else:
            return False

    def _tidy_up(self):
        """\
        Close any left open port forwarding tunnel, also close Telekinesis client's log file,
        if left open.

        """
        if self.tekiclient:
            self.logger('Shutting down Telekinesis client subprocess', loglevel=log.loglevel_DEBUG)
            try:
                self.tekiclient.kill()
            except OSError, e:
                self.logger('Telekinesis client shutdown gave a message that we may ignore: %s' % str(e), loglevel=log.loglevel_WARN)
            self.tekiclient = None

        if self.fw_ctrl_tunnel is not None:
            self.logger('Shutting down Telekinesis wormhole', loglevel=log.loglevel_DEBUG)
            forward.stop_forward_tunnel(self.fw_ctrl_tunnel)
            self.fw_ctrl_tunnel = None

        if self.telekinesis_sshfs is not None:
            telekinesis_sshfs_command = ['fusermount', '-u', '/tmp/.x2go-{local_user}/telekinesis/S-{sid}/'.format(local_user=_CURRENT_LOCAL_USER, sid=self.session_name), ]
            self.logger('Umounting SSHFS mount for Telekinesis via forking a threaded subprocess: %s' % " ".join(telekinesis_sshfs_command), loglevel=log.loglevel_DEBUG)
            self.telekinesis_sshfs_umount = subprocess.Popen(telekinesis_sshfs_command,
                                                             env=self.TEKICLIENT_ENV,
                                                             stdin=None,
                                                             stdout=self.tekiclient_datalog_stdout,
                                                             stderr=self.tekiclient_datalog_stderr,
                                                             shell=False)
            self.telekinesis_sshfs = None

        if self.fw_data_tunnel is not None:
            self.logger('Shutting down Telekinesis DATA tunnel', loglevel=log.loglevel_DEBUG)
            forward.stop_forward_tunnel(self.fw_data_tunnel)
            self.fw_data_tunnel = None
        if self.tekiclient_log_stdout is not None:
            self.tekiclient_log_stdout.close()
        if self.tekiclient_log_stderr is not None:
            self.tekiclient_log_stderr.close()
        if self.tekiclient_datalog_stdout is not None:
            self.tekiclient_datalog_stdout.close()
        if self.tekiclient_datalog_stderr is not None:
            self.tekiclient_datalog_stderr.close()

    def stop_thread(self):
        """\
        End the thread runner and tidy up.

        """
        self._keepalive = False
        # wait for thread loop to finish...
        _count = 0
        _maxwait = 40
        while self.tekiclient is not None and (_count < _maxwait):
            _count += 1
            self.logger('waiting for Telekinesis client to shut down: 0.5s x %s' % _count, loglevel=log.loglevel_DEBUG)
            gevent.sleep(.5)

    def run(self):
        """\
        Start the X2Go Telekinesis client command. The Telekinesis client command utilizes a
        Paramiko/SSH based forwarding tunnel (openssh -L option). This tunnel
        gets started here and is forked into background (Greenlet/gevent).

        """
        self._keepalive = True
        self.tekiclient = None

        try:
            os.makedirs(self.session_info.local_container)
        except OSError, e:
            if e.errno == 17:
                # file exists
                pass

        try:
            if self.ssh_transport.getpeername()[0] in ('::1', '127.0.0.1', 'localhost', 'localhost.localdomain'):
                self.local_tekictrl_port += 10000
        except socket.error:
            raise x2go_exceptions.X2GoControlSessionException('The control session has died unexpectedly.')
        self.local_tekictrl_port = utils.detect_unused_port(preferred_port=self.local_tekictrl_port)

        self.fw_ctrl_tunnel = forward.start_forward_tunnel(local_port=self.local_tekictrl_port,
                                                           remote_port=self.session_info.tekictrl_port,
                                                           ssh_transport=self.ssh_transport,
                                                           session_instance=self.session_instance,
                                                           session_name=self.session_name,
                                                           subsystem='Telekinesis Wormhole',
                                                           logger=self.logger,
                                                          )
        # update the proxy port in PROXY_ARGS
        self._update_local_tekictrl_socket(self.local_tekictrl_port)

        cmd_line = self._generate_cmdline()

        self.tekiclient_log_stdout = open('%s/%s' % (self.session_info.local_container, self.tekiclient_log, ), 'a')
        self.tekiclient_log_stderr = open('%s/%s' % (self.session_info.local_container, self.tekiclient_log, ), 'a')
        self.logger('forking threaded subprocess: %s' % " ".join(cmd_line), loglevel=log.loglevel_DEBUG)

        while not self.tekiclient:
            gevent.sleep(.2)
            p = self.tekiclient = subprocess.Popen(cmd_line,
                                                   env=self.TEKICLIENT_ENV,
                                                   stdin=None,
                                                   stdout=self.tekiclient_log_stdout,
                                                   stderr=self.tekiclient_log_stderr,
                                                   shell=False)

        while self._keepalive:
            gevent.sleep(1)

        try:
            p.terminate()
            self.logger('terminating Telekinesis client: %s' % p, loglevel=log.loglevel_DEBUG)
        except OSError, e:
            if e.errno == 3:
                # No such process
                pass

        # once all is over...
        self._tidy_up()

    def _update_local_tekictrl_socket(self, port):
        for idx, a in enumerate(self.TEKICLIENT_ARGS):
            if a.startswith('-setWORMHOLEPORT='):
                self.TEKICLIENT_ARGS[idx] = '-setWORMHOLEPORT=%s' % port

    def _generate_cmdline(self):
        """\
        Generate the NX proxy command line for execution.

        """
        cmd_line = [ self.TEKICLIENT_CMD, ]
        _tekiclient_args = " ".join(self.TEKICLIENT_ARGS).format(sid=self.session_name).split(' ')
        cmd_line.extend(_tekiclient_args)
        return cmd_line

    def start_telekinesis(self):
        """\
        Start the thread runner and wait for the Telekinesis client to come up.

        @return: a subprocess instance that knows about the externally started Telekinesis client command.
        @rtype: C{obj}

        """
        self.logger('starting local Telekinesis client...', loglevel=log.loglevel_INFO)

        # set up Telekinesis data channel first... (via an SSHFS mount)
        self.logger('Connecting Telekinesis data channel first via SSHFS host=127.0.0.1, port=%s.' % (self.session_info.tekidata_port,), loglevel=log.loglevel_DEBUG)

        if self.session_info is None or self.ssh_transport is None or not self.session_info.local_container:
            return None, False

        try:
            if self.ssh_transport.getpeername()[0] in ('::1', '127.0.0.1', 'localhost', 'localhost.localdomain'):
                self.local_tekidata_port += 10000
        except socket.error:
            raise x2go_exceptions.X2GoControlSessionException('The control session has died unexpectedly.')
        self.local_tekidata_port = utils.detect_unused_port(preferred_port=self.local_tekidata_port)

        self.fw_data_tunnel = forward.start_forward_tunnel(local_port=self.local_tekidata_port,
                                                           remote_port=self.session_info.tekidata_port,
                                                           ssh_transport=self.ssh_transport,
                                                           session_instance=self.session_instance,
                                                           session_name=self.session_name,
                                                           subsystem='Telekinesis Data',
                                                           logger=self.logger,
                                                          )
        self.tekiclient_datalog_stdout = open('%s/%s' % (self.session_info.local_container, self.tekiclient_datalog, ), 'a')
        self.tekiclient_datalog_stderr = open('%s/%s' % (self.session_info.local_container, self.tekiclient_datalog, ), 'a')
        try:
            os.makedirs(os.path.normpath('/tmp/.x2go-{local_user}/telekinesis/S-{sid}/'.format(local_user=_CURRENT_LOCAL_USER, sid=self.session_name)))
        except OSError, e:
            if e.errno == 17:
                # file exists
                pass
        if self.session_instance.has_server_feature('X2GO_TELEKINESIS_TEKISFTPSERVER'):
            # the Perl-based SFTP-Server shipped with Telekinesis Server (teki-sftpserver) supports
            # chroot'ing. Let's use this by default, if available.
            telekinesis_sshfs_command = ['sshfs',
                                         '-o', 'compression=no',
                                         '-o', 'follow_symlinks',
                                         '-o', 'directport={tekidata_port}'.format(tekidata_port=self.local_tekidata_port),
                                         '127.0.0.1:/',
                                         '/tmp/.x2go-{local_user}/telekinesis/S-{sid}/'.format(local_user=_CURRENT_LOCAL_USER, sid=self.session_name),
                                        ]
        else:
            # very first Telekinesis Server implementation used OpenSSH's sftp-server
            # that lacks/lacked chroot capability
            telekinesis_sshfs_command = ['sshfs',
                                         '-o', 'compression=no',
                                         '-o', 'follow_symlinks',
                                         '-o', 'directport={tekidata_port}'.format(tekidata_port=self.local_tekidata_port),
                                         '127.0.0.1:{remote_home}/.x2go/C-{sid}/telekinesis/remote/'.format(remote_home=self.session_instance.get_remote_home(), sid=self.session_name),
                                         '/tmp/.x2go-{local_user}/telekinesis/S-{sid}/'.format(local_user=_CURRENT_LOCAL_USER, sid=self.session_name),
                                        ]
        self.logger('forking threaded subprocess: %s' % " ".join(telekinesis_sshfs_command), loglevel=log.loglevel_DEBUG)
        try:
            self.telekinesis_sshfs = subprocess.Popen(telekinesis_sshfs_command,
                                                      env=self.TEKICLIENT_ENV,
                                                      stdin=None,
                                                      stdout=self.tekiclient_datalog_stdout,
                                                      stderr=self.tekiclient_datalog_stderr,
                                                      shell=False)
        except OSError, e:
            if e.errno == 2:
                self.logger("The 'sshfs' command is not available on your client machine, please install it to get Telekinesis up and running!!!", loglevel=log.loglevel_WARN)
            else:
                self.logger("An error occurred while setting up the Telekinesis data stream (via SSHFS): %s (errno: %s)" % (str(e), e.errno), loglevel=log.loglevel_WARN)
            return None, False

        # also wait for telekinesis data tunnel to become active
        _count = 0
        _maxwait = 40
        while self.fw_data_tunnel and (not self.fw_data_tunnel.is_active) and (not self.fw_data_tunnel.failed) and (_count < _maxwait):
            _count += 1
            self.logger('waiting for Telekinesis data tunnel to come up: 0.5s x %s' % _count, loglevel=log.loglevel_DEBUG)
            gevent.sleep(.5)

        # only start TeKi client if the data connection is up and running...
        if self.fw_data_tunnel.is_active and self.telekinesis_sshfs:

            gevent.sleep(1)
            threading.Thread.start(self)

            self.logger('Telekinesis client tries to connect to host=127.0.0.1, port=%s.' % (self.session_info.tekictrl_port,), loglevel=log.loglevel_DEBUG)
            self.logger('Telekinesis client writes its log to %s.' % os.path.join(self.session_info.local_container, self.tekiclient_log), loglevel=log.loglevel_DEBUG)
            while self.tekiclient is None and _count < _maxwait:
                _count += 1
                self.logger('waiting for Telekinesis client to come up: 0.4s x %s' % _count, loglevel=log.loglevel_DEBUG)
                gevent.sleep(.4)

            # only wait for the TeKi wormhole tunnel (ctrl tunnel) if TeKi could be started successfully...
            if self.tekiclient is not None:

                # also wait for telekinesis wormhole to become active
                _count = 0
                _maxwait = 40
                while self.fw_ctrl_tunnel and (not self.fw_ctrl_tunnel.is_active) and (not self.fw_ctrl_tunnel.failed) and (_count < _maxwait):
                    _count += 1
                    self.logger('waiting for Telekinesis wormhole to come up: 0.5s x %s' % _count, loglevel=log.loglevel_DEBUG)
                    gevent.sleep(.5)

        else:
            self.logger('Aborting Telekinesis client startup for session %s, because the Telekinesis data connection failed to be established.' % (self.session_name,), loglevel=log.loglevel_WARN)

        return self.tekiclient, bool(self.tekiclient) and (self.fw_ctrl_tunnel and self.fw_ctrl_tunnel.is_active)

    def ok(self):
        """\
        Check if a proxy instance is up and running.

        @return: Proxy state, C{True} for proxy being up-and-running, C{False} otherwise
        @rtype C{bool}

        """
        return bool(self.tekiclient and self.tekiclient.poll() is None) and self.fw_ctrl_tunnel.is_active and self.fw_data_tunnel.is_active
