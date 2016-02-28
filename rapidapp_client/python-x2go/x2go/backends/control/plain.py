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
L{X2GoControlSession} class - core functions for handling your individual X2Go sessions.

This backend handles X2Go server implementations that respond via server-side PLAIN text output.

"""
__NAME__ = 'x2gocontrolsession-pylib'

# modules
import os
import types
import paramiko
import gevent
import copy
import string
import random
import re
import locale
import threading
import cStringIO
import base64
import uuid

from gevent import socket

# Python X2Go modules
import x2go.sshproxy as sshproxy
import x2go.log as log
import x2go.utils as utils
import x2go.x2go_exceptions as x2go_exceptions
import x2go.defaults as defaults
import x2go.checkhosts as checkhosts

from x2go.defaults import BACKENDS as _BACKENDS

import x2go._paramiko
x2go._paramiko.monkey_patch_paramiko()

def _rerewrite_blanks(cmd):
    """\
    In command strings X2Go server scripts expect blanks being rewritten to ,,X2GO_SPACE_CHAR''.
    Commands get rewritten in the terminal sessions. This re-rewrite function helps
    displaying command string in log output.

    @param cmd: command that has to be rewritten for log output
    @type cmd: C{str}

    @return: the command with ,,X2GO_SPACE_CHAR'' re-replaced by blanks
    @rtype: C{str}

    """
    # X2Go run command replace X2GO_SPACE_CHAR string with blanks
    if cmd:
        cmd = cmd.replace("X2GO_SPACE_CHAR", " ")
    return cmd

def _rewrite_password(cmd, user=None, password=None):
    """\
    In command strings Python X2Go replaces some macros with actual values:

      - X2GO_USER -> the user name under which the user is authenticated via SSH
      - X2GO_PASSWORD -> the password being used for SSH authentication

    Both macros can be used to on-the-fly authenticate via RDP.

    @param cmd: command that is to be sent to an X2Go server script
    @type cmd: C{str}
    @param user: the SSH authenticated user name
    @type password: the password being used for SSH authentication

    @return: the command with macros replaced
    @rtype: C{str}

    """
    # if there is a ,,-u X2GO_USER'' parameter in RDP options then we will replace 
    # it by our X2Go session password
    if cmd and user:
        cmd = cmd.replace('X2GO_USER', user)
    # if there is a ,,-p X2GO_PASSWORD'' parameter in RDP options then we will replace 
    # it by our X2Go session password
    if cmd and password:
        cmd = cmd.replace('X2GO_PASSWORD', password)
    return cmd


class X2GoControlSession(paramiko.SSHClient):
    """\
    In the Python X2Go concept, X2Go sessions fall into two parts: a control session and one to many terminal sessions.

    The control session handles the SSH based communication between server and client. It is mainly derived from
    C{paramiko.SSHClient} and adds on X2Go related functionality.

    """
    def __init__(self,
                 profile_name='UNKNOWN',
                 add_to_known_hosts=False,
                 known_hosts=None,
                 forward_sshagent=False,
                 unique_hostkey_aliases=False,
                 terminal_backend=_BACKENDS['X2GoTerminalSession']['default'],
                 info_backend=_BACKENDS['X2GoServerSessionInfo']['default'],
                 list_backend=_BACKENDS['X2GoServerSessionList']['default'],
                 proxy_backend=_BACKENDS['X2GoProxy']['default'],
                 client_rootdir=os.path.join(defaults.LOCAL_HOME, defaults.X2GO_CLIENT_ROOTDIR),
                 sessions_rootdir=os.path.join(defaults.LOCAL_HOME, defaults.X2GO_SESSIONS_ROOTDIR),
                 ssh_rootdir=os.path.join(defaults.LOCAL_HOME, defaults.X2GO_SSH_ROOTDIR),
                 logger=None, loglevel=log.loglevel_DEFAULT,
                 published_applications_no_submenus=0,
                 low_latency=False,
                 **kwargs):
        """\
        Initialize an X2Go control session. For each connected session profile there will be one SSH-based
        control session and one to many terminal sessions that all server-client-communicate via this one common control
        session.

        A control session normally gets set up by an L{X2GoSession} instance. Do not use it directly!!!

        @param profile_name: the profile name of the session profile this control session works for
        @type profile_name: C{str}
        @param add_to_known_hosts: Auto-accept server host validity?
        @type add_to_known_hosts: C{bool}
        @param known_hosts: the underlying Paramiko/SSH systems C{known_hosts} file
        @type known_hosts: C{str}
        @param forward_sshagent: forward SSH agent authentication requests to the X2Go client-side
        @type forward_sshagent: C{bool}
        @param unique_hostkey_aliases: instead of storing [<hostname>]:<port> in known_hosts file, use the
            (unique-by-design) profile ID
        @type unique_hostkey_aliases: C{bool}
        @param terminal_backend: X2Go terminal session backend to use
        @type terminal_backend: C{str}
        @param info_backend: backend for handling storage of server session information
        @type info_backend: C{X2GoServerSessionInfo*} instance
        @param list_backend: backend for handling storage of session list information
        @type list_backend: C{X2GoServerSessionList*} instance
        @param proxy_backend: backend for handling the X-proxy connections
        @type proxy_backend: C{X2GoProxy*} instance
        @param client_rootdir: client base dir (default: ~/.x2goclient)
        @type client_rootdir: C{str}
        @param sessions_rootdir: sessions base dir (default: ~/.x2go)
        @type sessions_rootdir: C{str}
        @param ssh_rootdir: ssh base dir (default: ~/.ssh)
        @type ssh_rootdir: C{str}
        @param published_applications_no_submenus: published applications menus with less items than C{published_applications_no_submenus}
            are rendered without submenus
        @type published_applications_no_submenus: C{int}
        @param logger: you can pass an L{X2GoLogger} object to the
            L{X2GoControlSession} constructor
        @type logger: L{X2GoLogger} instance
        @param loglevel: if no L{X2GoLogger} object has been supplied a new one will be
            constructed with the given loglevel
        @type loglevel: C{int}
        @param low_latency: set this boolean switch for weak connections, it will double all timeout values.
        @type low_latency: C{bool}
        @param kwargs: catch any non-defined parameters in C{kwargs}
        @type kwargs: C{dict}

        """
        self.associated_terminals = {}
        self.terminated_terminals = []

        self.profile_name = profile_name
        self.add_to_known_hosts = add_to_known_hosts
        self.known_hosts = known_hosts
        self.forward_sshagent = forward_sshagent
        self.unique_hostkey_aliases = unique_hostkey_aliases

        self.hostname = None
        self.port = None

        self.sshproxy_session = None

        self._session_auth_rsakey = None
        self._remote_home = None
        self._remote_group = {}
        self._remote_username = None
        self._remote_peername = None

        self._server_versions = None
        self._server_features = None

        if logger is None:
            self.logger = log.X2GoLogger(loglevel=loglevel)
        else:
            self.logger = copy.deepcopy(logger)
        self.logger.tag = __NAME__

        self._terminal_backend = terminal_backend
        self._info_backend = info_backend
        self._list_backend = list_backend
        self._proxy_backend = proxy_backend

        self.client_rootdir = client_rootdir
        self.sessions_rootdir = sessions_rootdir
        self.ssh_rootdir = ssh_rootdir

        self._published_applications_menu = {}

        self.agent_chan = None
        self.agent_handler = None

        paramiko.SSHClient.__init__(self)
        if self.add_to_known_hosts:
            self.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        self.session_died = False

        self.low_latency = low_latency

        self.published_applications_no_submenus = published_applications_no_submenus
        self._already_querying_published_applications = threading.Lock()

        self._transport_lock = threading.Lock()

    def set_hostname(self, hname):
        self.hostname = hname

    def get_hostname(self):
        """\
        Get the hostname as stored in the properties of this control session.

        @return: the hostname of the connected X2Go server
        @rtype: C{str}

        """
        return self.hostname

    def get_port(self):
        """\
        Get the port number of the SSH connection as stored in the properties of this control session.

        @return: the server-side port number of the control session's SSH connection
        @rtype: C{str}

        """
        return self.port

    def load_session_host_keys(self):
        """\
        Load known SSH host keys from the C{known_hosts} file.

        If the file does not exist, create it first.

        """
        if self.known_hosts is not None:
            utils.touch_file(self.known_hosts)
            self.load_host_keys(self.known_hosts)

    def __del__(self):
        """\
        On instance descruction, do a proper session disconnect from the server.

        """
        self.disconnect()

    def test_sftpclient(self):
        ssh_transport = self.get_transport()
        try:
            self.sftp_client = paramiko.SFTPClient.from_transport(ssh_transport)
        except (AttributeError, paramiko.SFTPError):
            raise x2go_exceptions.X2GoSFTPClientException('failed to initialize SFTP channel')

    def _x2go_sftp_put(self, local_path, remote_path, timeout=20):
        """
        Put a local file on the remote server via sFTP.

        During sFTP operations, remote command execution gets blocked.

        @param local_path: full local path name of the file to be put on the server
        @type local_path: C{str}
        @param remote_path: full remote path name of the server-side target location, path names have to be Unix-compliant
        @type remote_path: C{str}
        @param timeout: this SFTP put action should not take longer then the given value
        @type timeout: C{int}

        @raise X2GoControlSessionException: if the SSH connection dropped out

        """
        ssh_transport = self.get_transport()
        self._transport_lock.acquire()
        if ssh_transport and ssh_transport.is_authenticated():
            self.logger('sFTP-put: %s -> %s:%s' % (os.path.normpath(local_path), self.remote_peername(), remote_path), loglevel=log.loglevel_DEBUG)

            if self.low_latency: timeout = timeout * 2
            timer = gevent.Timeout(timeout)
            timer.start()

            try:
                try:
                    self.sftp_client = paramiko.SFTPClient.from_transport(ssh_transport)
                except paramiko.SFTPError:
                    self._transport_lock.release()
                    raise x2go_exceptions.X2GoSFTPClientException('failed to initialize SFTP channel')
                try:
                    self.sftp_client.put(os.path.normpath(local_path), remote_path)
                except (x2go_exceptions.SSHException, socket.error, IOError):
                    # react to connection dropped error for SSH connections
                    self.session_died = True
                    self._transport_lock.release()
                    raise x2go_exceptions.X2GoControlSessionException('The SSH connection was dropped during an sFTP put action.')

            except gevent.timeout.Timeout:
                self.session_died = True
                self._transport_lock.release()
                if self.sshproxy_session:
                    self.sshproxy_session.stop_thread()
                raise x2go_exceptions.X2GoControlSessionException('the X2Go control session timed out during an SFTP write command')
            finally:
                timer.cancel()

            self.sftp_client = None
        self._transport_lock.release()

    def _x2go_sftp_write(self, remote_path, content, timeout=20):
        """
        Create a text file on the remote server via sFTP.

        During sFTP operations, remote command execution gets blocked.

        @param remote_path: full remote path name of the server-side target location, path names have to be Unix-compliant
        @type remote_path: C{str}
        @param content: a text file, multi-line files use Unix-link EOL style
        @type content: C{str}
        @param timeout: this SFTP write action should not take longer then the given value
        @type timeout: C{int}

        @raise X2GoControlSessionException: if the SSH connection dropped out

        """
        ssh_transport = self.get_transport()
        self._transport_lock.acquire()
        if ssh_transport and ssh_transport.is_authenticated():
            self.logger('sFTP-write: opening remote file %s on host %s for writing' % (remote_path, self.remote_peername()), loglevel=log.loglevel_DEBUG)

            if self.low_latency: timeout = timeout * 2
            timer = gevent.Timeout(timeout)
            timer.start()

            try:
                try:
                    self.sftp_client = paramiko.SFTPClient.from_transport(ssh_transport)
                except paramiko.SFTPError:
                    self._transport_lock.release()
                    raise x2go_exceptions.X2GoSFTPClientException('failed to initialize SFTP channel')
                try:
                    remote_fileobj = self.sftp_client.open(remote_path, 'w')
                    self.logger('sFTP-write: writing content: %s' % content, loglevel=log.loglevel_DEBUG_SFTPXFER)
                    remote_fileobj.write(content)
                    remote_fileobj.close()
                except (x2go_exceptions.SSHException, socket.error, IOError):
                    self.session_died = True
                    self._transport_lock.release()
                    self.logger('sFTP-write: opening remote file %s on host %s failed' % (remote_path, self.remote_peername()), loglevel=log.loglevel_WARN)
                    if self.sshproxy_session:
                        self.sshproxy_session.stop_thread()
                    raise x2go_exceptions.X2GoControlSessionException('The SSH connection was dropped during an sFTP write action.')

            except gevent.timeout.Timeout:
                self.session_died = True
                self._transport_lock.release()
                if self.sshproxy_session:
                    self.sshproxy_session.stop_thread()
                raise x2go_exceptions.X2GoControlSessionException('the X2Go control session timed out during an SFTP write command')
            finally:
                timer.cancel()

            self.sftp_client = None
        self._transport_lock.release()

    def _x2go_sftp_remove(self, remote_path, timeout=20):
        """
        Remote a remote file from the server via sFTP.

        During sFTP operations, remote command execution gets blocked.

        @param remote_path: full remote path name of the server-side file to be removed, path names have to be Unix-compliant
        @type remote_path: C{str}
        @param timeout: this SFTP remove action should not take longer then the given value
        @type timeout: C{int}

        @raise X2GoControlSessionException: if the SSH connection dropped out

        """
        ssh_transport = self.get_transport()
        self._transport_lock.acquire()
        if ssh_transport and ssh_transport.is_authenticated():
            self.logger('sFTP-write: removing remote file %s on host %s' % (remote_path, self.remote_peername()), loglevel=log.loglevel_DEBUG)

            if self.low_latency: timeout = timeout * 2
            timer = gevent.Timeout(timeout)
            timer.start()

            try:
                try:
                    self.sftp_client = paramiko.SFTPClient.from_transport(ssh_transport)
                except paramiko.SFTPError:
                    self._transport_lock.release()
                    raise x2go_exceptions.X2GoSFTPClientException('failed to initialize SFTP channel')
                try:
                    self.sftp_client.remove(remote_path)
                except (x2go_exceptions.SSHException, socket.error, IOError):
                    self.session_died = True
                    self._transport_lock.release()
                    self.logger('sFTP-write: removing remote file %s on host %s failed' % (remote_path, self.remote_peername()), loglevel=log.loglevel_WARN)
                    if self.sshproxy_session:
                        self.sshproxy_session.stop_thread()
                    raise x2go_exceptions.X2GoControlSessionException('The SSH connection was dropped during an sFTP remove action.')

            except gevent.timeout.Timeout:
                self.session_died = True
                self._transport_lock.release()
                if self.sshproxy_session:
                    self.sshproxy_session.stop_thread()
                raise x2go_exceptions.X2GoControlSessionException('the X2Go control session timed out during an SFTP write command')
            finally:
                timer.cancel()

            self.sftp_client = None
        self._transport_lock.release()

    def _x2go_exec_command(self, cmd_line, loglevel=log.loglevel_INFO, timeout=20, **kwargs):
        """
        Execute an X2Go server-side command via SSH.

        During SSH command executions, sFTP operations get blocked.

        @param cmd_line: the command to be executed on the remote server
        @type cmd_line: C{str} or C{list}
        @param loglevel: use this loglevel for reporting about remote command execution
        @type loglevel: C{int}
        @param timeout: if commands take longer than C{<timeout>} to be executed, consider the control session connection
            to have died.
        @type timeout: C{int}
        @param kwargs: parameters that get passed through to the C{paramiko.SSHClient.exec_command()} method.
        @type kwargs: C{dict}

        @return: C{True} if the command could be successfully executed on the remote X2Go server
        @rtype: C{bool}

        @raise X2GoControlSessionException: if the command execution failed (due to a lost connection)

        """
        if type(cmd_line) == types.ListType:
            cmd = " ".join(cmd_line)
        else:
            cmd = cmd_line

        cmd_uuid = str(uuid.uuid1())
        cmd = 'echo X2GODATABEGIN:%s; PATH=/usr/local/bin:/usr/bin:/bin sh -c \"%s\"; echo X2GODATAEND:%s' % (cmd_uuid, cmd, cmd_uuid)

        if self.session_died:
            self.logger("control session seams to be dead, not executing command ,,%s'' on X2Go server %s" % (_rerewrite_blanks(cmd), self.profile_name,), loglevel=loglevel)
            return (cStringIO.StringIO(), cStringIO.StringIO(), cStringIO.StringIO('failed to execute command'))

        self._transport_lock.acquire()

        _retval = None
        _password = None

        ssh_transport = self.get_transport()
        if ssh_transport and ssh_transport.is_authenticated():

            if self.low_latency: timeout = timeout * 2
            timer = gevent.Timeout(timeout)
            timer.start()
            try:
                self.logger("executing command on X2Go server ,,%s'': %s" % (self.profile_name, _rerewrite_blanks(cmd)), loglevel=loglevel)
                if self._session_password:
                    _password = base64.b64decode(self._session_password)
                _retval = self.exec_command(_rewrite_password(cmd, user=self.get_transport().get_username(), password=_password), **kwargs)
            except AttributeError:
                self.session_died = True
                self._transport_lock.release()
                if self.sshproxy_session:
                    self.sshproxy_session.stop_thread()
                raise x2go_exceptions.X2GoControlSessionException('the X2Go control session has died unexpectedly')
            except EOFError:
                self.session_died = True
                self._transport_lock.release()
                if self.sshproxy_session:
                    self.sshproxy_session.stop_thread()
                raise x2go_exceptions.X2GoControlSessionException('the X2Go control session has died unexpectedly')
            except x2go_exceptions.SSHException:
                self.session_died = True
                self._transport_lock.release()
                if self.sshproxy_session:
                    self.sshproxy_session.stop_thread()
                raise x2go_exceptions.X2GoControlSessionException('the X2Go control session has died unexpectedly')
            except gevent.timeout.Timeout:
                self.session_died = True
                self._transport_lock.release()
                if self.sshproxy_session:
                    self.sshproxy_session.stop_thread()
                raise x2go_exceptions.X2GoControlSessionException('the X2Go control session command timed out')
            except socket.error:
                self.session_died = True
                self._transport_lock.release()
                if self.sshproxy_session:
                    self.sshproxy_session.stop_thread()
                raise x2go_exceptions.X2GoControlSessionException('the X2Go control session has died unexpectedly')
            finally:
                timer.cancel()

        else:
            self._transport_lock.release()
            raise x2go_exceptions.X2GoControlSessionException('the X2Go control session is not connected (while issuing SSH command=%s)' % cmd)

        self._transport_lock.release()

        # sanitized X2Go relevant data, protect against data injection via .bashrc files
        (_stdin, _stdout, _stderr) = _retval
        raw_stdout = _stdout.read()

        sanitized_stdout = ''
        is_x2go_data = False
        for line in raw_stdout.split('\n'):
            if line.startswith('X2GODATABEGIN:'+cmd_uuid): 
                is_x2go_data = True
                continue
            if not is_x2go_data: continue
            if line.startswith('X2GODATAEND:'+cmd_uuid): break
            sanitized_stdout += line + "\n"

        _stdout_new = cStringIO.StringIO(sanitized_stdout)

        _retval = (_stdin, _stdout_new, _stderr)
        return _retval

    @property
    def _x2go_server_versions(self):
        """\
        Render a dictionary of server-side X2Go components and their versions. Results get cached
        once there has been one successful query.

        """
        if self._server_versions is None:
            self._server_versions = {}
            (stdin, stdout, stderr) = self._x2go_exec_command('which x2goversion >/dev/null && x2goversion')
            _lines = stdout.read().split('\n')
            for _line in _lines:
                if ':' not in _line: continue
                comp = _line.split(':')[0].strip()
                version = _line.split(':')[1].strip()
                self._server_versions.update({comp: version})
            self.logger('server-side X2Go components and their versions are: %s' % self._server_versions, loglevel=log.loglevel_DEBUG)
        return self._server_versions

    def query_server_versions(self, force=False):
        """\
        Do a query for the server-side list of X2Go components and their versions.

        @param force: do not use the cached component list, really ask the server (again)
        @type force: C{bool}

        @return: dictionary of X2Go components (as keys) and their versions (as values)
        @rtype: C{list}

        """
        if force:
            self._server_versions = None
        return self._x2go_server_versions
    get_server_versions = query_server_versions

    @property
    def _x2go_server_features(self):
        """\
        Render a list of server-side X2Go features. Results get cached once there has been one successful query.

        """
        if self._server_features is None:
            (stdin, stdout, stderr) = self._x2go_exec_command('which x2gofeaturelist >/dev/null && x2gofeaturelist')
            self._server_features = stdout.read().split('\n')
            self._server_features = [ f for f in self._server_features if f ]
            self._server_features.sort()
            self.logger('server-side X2Go features are: %s' % self._server_features, loglevel=log.loglevel_DEBUG)
        return self._server_features

    def query_server_features(self, force=False):
        """\
        Do a query for the server-side list of X2Go features.

        @param force: do not use the cached feature list, really ask the server (again)
        @type force: C{bool}

        @return: list of X2Go feature names
        @rtype: C{list}

        """
        if force:
            self._server_features = None
        return self._x2go_server_features
    get_server_features = query_server_features

    #apprime server info code begin
    def get_apprime_server_info(self):
        (stdin, stdout, stderr) = self._x2go_exec_command('which vg_server_status >/dev/null && vg_server_status')
        return stdout.read()
    #apprime code end
    
    @property
    def _x2go_remote_home(self):
        """\
        Retrieve and cache the remote home directory location.

        """
        if self._remote_home is None:
            (stdin, stdout, stderr) = self._x2go_exec_command('echo $HOME')
            stdout_r = stdout.read()
            if stdout_r:
                self._remote_home = stdout_r.split()[0]
                self.logger('remote user\' home directory: %s' % self._remote_home, loglevel=log.loglevel_DEBUG)
            return self._remote_home
        else:
            return self._remote_home

    def _x2go_remote_group(self, group):
        """\
        Retrieve and cache the members of a server-side POSIX group.

        @param group: remote POSIX group name
        @type group: C{str}

        @return: list of POSIX group members
        @rtype: C{list}

        """
        if not self._remote_group.has_key(group):
            (stdin, stdout, stderr) = self._x2go_exec_command('getent group %s | cut -d":" -f4' % group)
            self._remote_group[group] = stdout.read().split('\n')[0].split(',')
            self.logger('remote %s group: %s' % (group, self._remote_group[group]), loglevel=log.loglevel_DEBUG)
            return self._remote_group[group]
        else:
            return self._remote_group[group]

    def is_x2gouser(self, username):
        """\
        Is the remote user allowed to launch X2Go sessions?

        FIXME: this method is currently non-functional.

        @param username: remote user name
        @type username: C{str}

        @return: C{True} if the remote user is allowed to launch X2Go sessions
        @rtype: C{bool}

        """
        ###
        ### FIXME:
        ###
        # discussion about server-side access restriction based on posix group membership or similar currently 
        # in process (as of 20110517, mg)
        #return username in self._x2go_remote_group('x2gousers')
        return True

    def is_sshfs_available(self):
        """\
        Check if the remote user is allowed to use SSHFS mounts.

        @return: C{True} if the user is allowed to connect client-side shares to the X2Go session
        @rtype: C{bool}

        """
        return True; #Do NOT check for fuse membership - Appri.me
#        if self.remote_username() in self._x2go_remote_group('fuse'):
#            return True
#        return False

    def remote_username(self):
        """\
        Returns (and caches) the control session's remote username.

        @return: SSH transport's user name
        @rtype: C{str}

        @raise X2GoControlSessionException: on SSH connection loss

        """
        if self._remote_username is None:
            if self.get_transport() is not None:
                try:
                    self._remote_username = self.get_transport().get_username()
                except:
                    self.session_died = True
                    raise x2go_exceptions.X2GoControlSessionException('Lost connection to X2Go server')
        return self._remote_username

    def remote_peername(self):
        """\
        Returns (and caches) the control session's remote host (name or ip).

        @return: SSH transport's peer name
        @rtype: C{tuple}

        @raise X2GoControlSessionException: on SSH connection loss

        """
        if self._remote_peername is None:
            if self.get_transport() is not None:
                try:
                    self._remote_peername = self.get_transport().getpeername()
                except:
                    self.session_died = True
                    raise x2go_exceptions.X2GoControlSessionException('Lost connection to X2Go server')
        return self._remote_peername

    @property
    def _x2go_session_auth_rsakey(self):
        """\
        Generate (and cache) a temporary RSA host key for the lifetime of this control session.

        """
        if self._session_auth_rsakey is None:
            self._session_auth_rsakey = paramiko.RSAKey.generate(defaults.RSAKEY_STRENGTH)
        return self._session_auth_rsakey

    def set_profile_name(self, profile_name):
        """\
        Manipulate the control session's profile name.

        @param profile_name: new profile name for this control session
        @type profile_name: C{str}

        """
        self.profile_name = profile_name

    def check_host(self, hostname, port=22):
        """\
        Wraps around a Paramiko/SSH host key check.

        @param hostname: the remote X2Go server's hostname
        @type hostname: C{str}
        @param port: the SSH port of the remote X2Go server
        @type port: C{int}

        @return: C{True} if the host key check succeeded, C{False} otherwise
        @rtype: C{bool}

        """
        # trailing whitespace tolerance
        hostname = hostname.strip()

        # force into IPv4 for localhost connections
        if hostname in ('localhost', 'localhost.localdomain'):
            hostname = '127.0.0.1'

        return checkhosts.check_ssh_host_key(self, hostname, port=port)

    """\
    #appprime implementation of load-balancer and port scanning, in this order: 22, 80, 443
    def connect(self, hostname, port=22, username=None, password=None, passphrase=None, pkey=None,
                key_filename=None, timeout=None, allow_agent=False, look_for_keys=False,
                use_sshproxy=False, sshproxy_host=None, sshproxy_port=22, sshproxy_user=None, sshproxy_password=None, sshproxy_force_password_auth=False,
                sshproxy_key_filename=None, sshproxy_pkey=None, sshproxy_look_for_keys=False, sshproxy_passphrase='', sshproxy_allow_agent=False,
                sshproxy_tunnel=None,
                add_to_known_hosts=None,
                forward_sshagent=None,
                unique_hostkey_aliases=None,
                force_password_auth=False,
                session_instance=None,
        ):
        #first connect to lb and find the server node ip for this user
        return connect_apprime('52.74.114.219', port, username, password, passphrase, pkey, key_filename, timeout, allow_agent,
                        look_for_keys, use_sshproxy, sshproxy_host, sshproxy_port, sshproxy_user, sshproxy_password,
                        sshproxy_force_password_auth, sshproxy_key_filename, sshproxy_pkey, sshproxy_look_for_keys, 
                        sshproxy_passphrase, sshproxy_allow_agent, sshproxy_tunnel,  add_to_known_hosts, forward_sshagent,
                        unique_hostkey_aliases, force_password_auth, session_instance);
        
    """    
    #def connect_apprime(self, hostname, port=22, username=None, password=None, passphrase=None, pkey=None,
    def connect(self, hostname, port=22, username=None, password=None, passphrase=None, pkey=None,
                key_filename=None, timeout=None, allow_agent=False, look_for_keys=False,
                use_sshproxy=False, sshproxy_host=None, sshproxy_port=22, sshproxy_user=None, sshproxy_password=None, sshproxy_force_password_auth=False,
                sshproxy_key_filename=None, sshproxy_pkey=None, sshproxy_look_for_keys=False, sshproxy_passphrase='', sshproxy_allow_agent=False,
                sshproxy_tunnel=None,
                add_to_known_hosts=None,
                forward_sshagent=None,
                unique_hostkey_aliases=None,
                force_password_auth=False,
                session_instance=None,
        ):
        """\
        Connect to an X2Go server and authenticate to it. This method is directly
        inherited from the C{paramiko.SSHClient} class. The features of the Paramiko
        SSH client connect method are recited here. The parameters C{add_to_known_hosts},
        C{force_password_auth}, C{session_instance} and all SSH proxy related parameters
        have been added as X2Go specific parameters

        The server's host key is checked against the system host keys 
        (see C{load_system_host_keys}) and any local host keys (C{load_host_keys}).
        If the server's hostname is not found in either set of host keys, the missing host
        key policy is used (see C{set_missing_host_key_policy}).  The default policy is
        to reject the key and raise an C{SSHException}.

        Authentication is attempted in the following order of priority:

            - The C{pkey} or C{key_filename} passed in (if any)
            - Any key we can find through an SSH agent
            - Any "id_rsa" or "id_dsa" key discoverable in C{~/.ssh/}
            - Plain username/password auth, if a password was given

        If a private key requires a password to unlock it, and a password is
        passed in, that password will be used to attempt to unlock the key.

        @param hostname: the server to connect to
        @type hostname: C{str}
        @param port: the server port to connect to
        @type port: C{int}
        @param username: the username to authenticate as (defaults to the
            current local username)
        @type username: C{str}
        @param password: a password to use for authentication or for unlocking
            a private key
        @type password: C{str}
        @param passphrase: a passphrase to use for unlocking
            a private key in case the password is already needed for two-factor
            authentication
        @type passphrase: C{str}
        @param key_filename: the filename, or list of filenames, of optional
            private key(s) to try for authentication
        @type key_filename: C{str} or list(str)
        @param pkey: an optional private key to use for authentication
        @type pkey: C{PKey}
        @param forward_sshagent: forward SSH agent authentication requests to the X2Go client-side
            (will update the class property of the same name)
        @type forward_sshagent: C{bool}
        @param unique_hostkey_aliases: update the unique_hostkey_aliases class property
        @type unique_hostkey_aliases: C{bool}
        @param timeout: an optional timeout (in seconds) for the TCP connect
        @type timeout: float
        @param look_for_keys: set to C{True} to enable searching for discoverable
            private key files in C{~/.ssh/}
        @type look_for_keys: C{bool}
        @param allow_agent: set to C{True} to enable connecting to a local SSH agent
            for acquiring authentication information
        @type allow_agent: C{bool}
        @param add_to_known_hosts: non-paramiko option, if C{True} paramiko.AutoAddPolicy() 
            is used as missing-host-key-policy. If set to C{False} paramiko.RejectPolicy() 
            is used
        @type add_to_known_hosts: C{bool}
        @param force_password_auth: non-paramiko option, disable pub/priv key authentication 
            completely, even if the C{pkey} or the C{key_filename} parameter is given
        @type force_password_auth: C{bool}
        @param session_instance: an instance L{X2GoSession} using this L{X2GoControlSession}
            instance.
        @type session_instance: C{obj}
        @param use_sshproxy: connect through an SSH proxy
        @type use_sshproxy: C{True} if an SSH proxy is to be used for tunneling the connection
        @param sshproxy_host: hostname of the SSH proxy server
        @type sshproxy_host: C{str}
        @param sshproxy_port: port of the SSH proxy server
        @type sshproxy_port: C{int}
        @param sshproxy_user: username that we use for authenticating against C{<sshproxy_host>}
        @type sshproxy_user: C{str}
        @param sshproxy_password: a password to use for SSH proxy authentication or for unlocking
            a private key
        @type sshproxy_password: C{str}
        @param sshproxy_passphrase: a passphrase to use for unlocking
            a private key needed for the SSH proxy host in case the sshproxy_password is already needed for
            two-factor authentication
        @type sshproxy_passphrase: C{str}
        @param sshproxy_force_password_auth: enforce using a given C{sshproxy_password} even if a key(file) is given
        @type sshproxy_force_password_auth: C{bool}
        @param sshproxy_key_filename: local file location of the private key file
        @type sshproxy_key_filename: C{str}
        @param sshproxy_pkey: an optional private key to use for SSH proxy authentication
        @type sshproxy_pkey: C{PKey}
        @param sshproxy_look_for_keys: set to C{True} to enable connecting to a local SSH agent
            for acquiring authentication information (for SSH proxy authentication)
        @type sshproxy_look_for_keys: C{bool}
        @param sshproxy_allow_agent: set to C{True} to enable connecting to a local SSH agent
            for acquiring authentication information (for SSH proxy authentication)
        @type sshproxy_allow_agent: C{bool}
        @param sshproxy_tunnel: the SSH proxy tunneling parameters, format is: <local-address>:<local-port>:<remote-address>:<remote-port>
        @type sshproxy_tunnel: C{str}

        @return: C{True} if an authenticated SSH transport could be retrieved by this method
        @rtype: C{bool}

        @raise BadHostKeyException: if the server's host key could not be
            verified
        @raise AuthenticationException: if authentication failed
        @raise SSHException: if there was any other error connecting or
            establishing an SSH session
        @raise socket.error: if a socket error occurred while connecting
        @raise X2GoSSHProxyException: any SSH proxy exception is passed through while establishing the SSH proxy connection and tunneling setup
        @raise X2GoSSHAuthenticationException: any SSH proxy authentication exception is passed through while establishing the SSH proxy connection and tunneling setup
        @raise X2GoRemoteHomeException: if the remote home directory does not exist or is not accessible

        """
        _fake_hostname = None

        if hostname and type(hostname) not in (types.UnicodeType, types.StringType):
            hostname = [hostname]
        if hostname and type(hostname) is types.ListType:
            hostname = random.choice(hostname)

        if not username:
            self.logger('no username specified, cannot connect without username', loglevel=log.loglevel_ERROR)
            raise paramiko.AuthenticationException('no username specified, cannot connect without username')

        if type(password) not in (types.StringType, types.UnicodeType):
            password = ''
        if type(sshproxy_password) not in (types.StringType, types.UnicodeType):
            sshproxy_password = ''

        if unique_hostkey_aliases is None:
            unique_hostkey_aliases = self.unique_hostkey_aliases
        # prep the fake hostname with the real hostname, so we trigger the corresponding code path in 
        # x2go.checkhosts and either of its missing host key policies
        if unique_hostkey_aliases:
            if port != 22: _fake_hostname = "[%s]:%s" % (hostname, port)
            else: _fake_hostname = hostname

        if add_to_known_hosts is None:
            add_to_known_hosts = self.add_to_known_hosts

        if forward_sshagent is None:
            forward_sshagent = self.forward_sshagent

        if look_for_keys:
            key_filename = None
            pkey = None

        _twofactorauth = False
        if password and (passphrase is None): passphrase = password

        if use_sshproxy and sshproxy_host and sshproxy_user:
            try:
                if not sshproxy_tunnel:
                    sshproxy_tunnel = "localhost:44444:%s:%s" % (hostname, port)
                self.sshproxy_session = sshproxy.X2GoSSHProxy(known_hosts=self.known_hosts,
                                                              add_to_known_hosts=add_to_known_hosts,
                                                              sshproxy_host=sshproxy_host,
                                                              sshproxy_port=sshproxy_port,
                                                              sshproxy_user=sshproxy_user,
                                                              sshproxy_password=sshproxy_password,
                                                              sshproxy_passphrase=sshproxy_passphrase,
                                                              sshproxy_force_password_auth=sshproxy_force_password_auth,
                                                              sshproxy_key_filename=sshproxy_key_filename,
                                                              sshproxy_pkey=sshproxy_pkey,
                                                              sshproxy_look_for_keys=sshproxy_look_for_keys,
                                                              sshproxy_allow_agent=sshproxy_allow_agent,
                                                              sshproxy_tunnel=sshproxy_tunnel,
                                                              session_instance=session_instance,
                                                              logger=self.logger,
                                                             )
                hostname = self.sshproxy_session.get_local_proxy_host()
                port = self.sshproxy_session.get_local_proxy_port()
                _fake_hostname = self.sshproxy_session.get_remote_host()
                _fake_port = self.sshproxy_session.get_remote_port()
                if _fake_port != 22:
                    _fake_hostname = "[%s]:%s" % (_fake_hostname, _fake_port)

            except:
                if self.sshproxy_session:
                    self.sshproxy_session.stop_thread()
                self.sshproxy_session = None
                raise

            if self.sshproxy_session is not None:
                self.sshproxy_session.start()

                # divert port to sshproxy_session's local forwarding port (it might have changed due to 
                # SSH connection errors
                gevent.sleep(.1)
                port = self.sshproxy_session.get_local_proxy_port()

        if not add_to_known_hosts and session_instance:
            self.set_missing_host_key_policy(checkhosts.X2GoInteractiveAddPolicy(caller=self, session_instance=session_instance, fake_hostname=_fake_hostname))

        if add_to_known_hosts:
            self.set_missing_host_key_policy(checkhosts.X2GoAutoAddPolicy(caller=self, session_instance=session_instance, fake_hostname=_fake_hostname))

        # trailing whitespace tolerance in hostname
        hostname = hostname.strip()

        self.logger('connecting to [%s]:%s' % (hostname, port), loglevel=log.loglevel_NOTICE)

        self.load_session_host_keys()

        _hostname = hostname
        # enforce IPv4 for localhost address
        if _hostname in ('localhost', 'localhost.localdomain'):
            _hostname = '127.0.0.1'

        # update self.forward_sshagent via connect method parameter
        if forward_sshagent is not None:
            self.forward_sshagent = forward_sshagent

        if timeout and self.low_latency:
            timeout = timeout * 2

        if key_filename and "~" in key_filename:
            key_filename = os.path.expanduser(key_filename)

        if key_filename or pkey or look_for_keys or allow_agent or (password and force_password_auth):
            try:
                if password and force_password_auth:
                    self.logger('trying password based SSH authentication with server', loglevel=log.loglevel_DEBUG)
                    paramiko.SSHClient.connect(self, _hostname, port=port, username=username, password=password, pkey=None, 
                                               key_filename=None, timeout=timeout, allow_agent=False,
                                               look_for_keys=False)
                elif (key_filename and os.path.exists(os.path.normpath(key_filename))) or pkey:
                    self.logger('trying SSH pub/priv key authentication with server', loglevel=log.loglevel_DEBUG)
                    paramiko.SSHClient.connect(self, _hostname, port=port, username=username, pkey=pkey,
                                               key_filename=key_filename, timeout=timeout, allow_agent=False,
                                               look_for_keys=False)
                else:
                    self.logger('trying SSH key discovery or agent authentication with server', loglevel=log.loglevel_DEBUG)
                    paramiko.SSHClient.connect(self, _hostname, port=port, username=username, pkey=None,
                                               key_filename=None, timeout=timeout, allow_agent=allow_agent,
                                               look_for_keys=look_for_keys)

            except (paramiko.PasswordRequiredException, paramiko.SSHException), e:
                self.close()
                if type(e) == paramiko.SSHException and str(e).startswith('Two-factor authentication requires a password'):
                    self.logger('X2Go Server requests two-factor authentication', loglevel=log.loglevel_NOTICE)
                    _twofactorauth = True
                if passphrase is not None:
                    self.logger('unlock SSH private key file with provided password', loglevel=log.loglevel_INFO)
                    try:
                        if not password: password = None
                        if (key_filename and os.path.exists(os.path.normpath(key_filename))) or pkey:
                            self.logger('re-trying SSH pub/priv key authentication with server', loglevel=log.loglevel_DEBUG)
                            try:
                                paramiko.SSHClient.connect(self, _hostname, port=port, username=username, password=password, passphrase=passphrase, pkey=pkey,
                                                           key_filename=key_filename, timeout=timeout, allow_agent=False,
                                                           look_for_keys=False)
                            except TypeError:
                                if _twofactorauth and password and passphrase and password != passphrase:
                                    self.logger('your version of Paramiko/SSH does not support authentication workflows which require SSH key decryption in combination with two-factor authentication', loglevel=log.loglevel_WARNING)
                                paramiko.SSHClient.connect(self, _hostname, port=port, username=username, password=password, pkey=pkey,
                                                           key_filename=key_filename, timeout=timeout, allow_agent=False,
                                                           look_for_keys=False)
                        else:
                            self.logger('re-trying SSH key discovery now with passphrase for unlocking the key(s)', loglevel=log.loglevel_DEBUG)
                            try:
                                paramiko.SSHClient.connect(self, _hostname, port=port, username=username, password=password, passphrase=passphrase, pkey=None,
                                                           key_filename=None, timeout=timeout, allow_agent=allow_agent,
                                                           look_for_keys=look_for_keys)
                            except TypeError:
                                if _twofactorauth and password and passphrase and password != passphrase:
                                    self.logger('your version of Paramiko/SSH does not support authentication workflows which require SSH key decryption in combination with two-factor authentication', loglevel=log.loglevel_WARNING)
                                paramiko.SSHClient.connect(self, _hostname, port=port, username=username, password=password, pkey=None,
                                                           key_filename=None, timeout=timeout, allow_agent=allow_agent,
                                                           look_for_keys=look_for_keys)

                    except paramiko.AuthenticationException, auth_e:
                        # the provided password cannot be used to unlock any private SSH key file (i.e. wrong password)
                        raise paramiko.AuthenticationException(str(auth_e))

                    except paramiko.SSHException, auth_e:
                        if str(auth_e) == 'No authentication methods available':
                            raise paramiko.AuthenticationException('Interactive password authentication required!')
                        else:
                            self.close()
                            if self.sshproxy_session:
                                self.sshproxy_session.stop_thread()
                            raise auth_e

                else:
                    self.close()
                    if self.sshproxy_session:
                        self.sshproxy_session.stop_thread()
                    raise e

            except paramiko.AuthenticationException, e:
                self.close()
                if password:
                    self.logger('next auth mechanism we\'ll try is password authentication', loglevel=log.loglevel_DEBUG)
                    try:
                        paramiko.SSHClient.connect(self, _hostname, port=port, username=username, password=password,
                                                   key_filename=None, pkey=None, timeout=timeout, allow_agent=False, look_for_keys=False)
                    except:
                        self.close()
                        if self.sshproxy_session:
                            self.sshproxy_session.stop_thread()
                        raise
                else:
                    self.close()
                    if self.sshproxy_session:
                        self.sshproxy_session.stop_thread()
                    raise e

            except paramiko.SSHException, e:
                if str(e) == 'No authentication methods available':
                    raise paramiko.AuthenticationException('Interactive password authentication required!')
                else:
                    self.close()
                    if self.sshproxy_session:
                        self.sshproxy_session.stop_thread()
                    raise e

            except:
                self.close()
                if self.sshproxy_session:
                    self.sshproxy_session.stop_thread()
                raise

        # if there is no private key (and no agent auth), we will use the given password, if any
        else:
            # create a random password if password is empty to trigger host key validity check
            if not password:
                password = "".join([random.choice(string.letters+string.digits) for x in range(1, 20)])
            self.logger('performing SSH password authentication with server', loglevel=log.loglevel_DEBUG)
            #try:
            paramiko.SSHClient.connect(self, _hostname, port=port, username=username, password=password,
                                           timeout=timeout, allow_agent=False, look_for_keys=False)
            #except paramiko.AuthenticationException, e:
            #    self.close()
            #    if self.sshproxy_session:
            #        self.sshproxy_session.stop_thread()
            #    raise e
            #except:
            #    self.close()
            #    if self.sshproxy_session:
            #        self.sshproxy_session.stop_thread()
            #    raise

        self.set_missing_host_key_policy(paramiko.RejectPolicy())

        self.hostname = hostname
        self.port = port

        # preparing reverse tunnels
        ssh_transport = self.get_transport()
        ssh_transport.reverse_tunnels = {}

        # mark Paramiko/SSH transport as X2GoControlSession
        ssh_transport._x2go_session_marker = True
        try:
            self._session_password = base64.b64encode(password)
        except TypeError:
            self._session_password = None

        if ssh_transport is not None:

            # since Paramiko 1.7.7.1 there is compression available, let's use it if present...
            if x2go._paramiko.PARAMIKO_FEATURE['use-compression']:
                ssh_transport.use_compression(compress=False)
            # enable keep alive callbacks
            ssh_transport.set_keepalive(30) #apprime: earlier this was 5 seconds. Why so frequent?

            self.session_died = False
            self.query_server_features(force=True)
            if self.forward_sshagent:
                if x2go._paramiko.PARAMIKO_FEATURE['forward-ssh-agent']:
                    self.agent_chan = ssh_transport.open_session()
                    self.agent_handler = paramiko.agent.AgentRequestHandler(self.agent_chan)
                    self.logger('Requesting SSH agent forwarding for control session of connected session profile %s' % self.profile_name, loglevel=log.loglevel_INFO)
                else:
                    self.logger('SSH agent forwarding is not available in the Paramiko version used with this instance of Python X2Go', loglevel=log.loglevel_WARN)
        else:
            self.close()
            if self.sshproxy_session:
                self.sshproxy_session.stop_thread()

        self._remote_home = None
        if not self.home_exists():
            self.close()
            if self.sshproxy_session:
                self.sshproxy_session.stop_thread()
            raise x2go_exceptions.X2GoRemoteHomeException('remote home directory does not exist')

        return (self.get_transport() is not None)

    def dissociate(self, terminal_session):
        """\
        Drop an associated terminal session.

        @param terminal_session: the terminal session object to remove from the list of associated terminals
        @type terminal_session: C{X2GoTerminalSession*}

        """
        for t_name in self.associated_terminals.keys():
            if self.associated_terminals[t_name] == terminal_session:
                del self.associated_terminals[t_name]
                if self.terminated_terminals.has_key(t_name):
                    del self.terminated_terminals[t_name]

    def disconnect(self):
        """\
        Disconnect this control session from the remote server.

        @return: report success or failure after having disconnected
        @rtype: C{bool}

        """
        if self.associated_terminals:
            t_names = self.associated_terminals.keys()
            for t_obj in self.associated_terminals.values():
                try:
                    if not self.session_died:
                        t_obj.suspend()
                except x2go_exceptions.X2GoTerminalSessionException:
                    pass
                except x2go_exceptions.X2GoControlSessionException:
                    self.session_died
                t_obj.__del__()
            for t_name in t_names:
                try:
                    del self.associated_terminals[t_name]
                except KeyError:
                    pass

        self._remote_home = None
        self._remote_group = {}

        self._session_auth_rsakey = None

        # in any case, release out internal transport lock
        self._transport_lock.release()

        # close SSH agent auth forwarding objects
        if self.agent_handler is not None:
            self.agent_handler.close()

        if self.agent_chan is not None:
            try:
                self.agent_chan.close()
            except EOFError:
                pass

        retval = False
        try:
            if self.get_transport() is not None:
                retval = self.get_transport().is_active()
                try:
                    self.close()
                except IOError:
                    pass
        except AttributeError:
            # if the Paramiko _transport object has not yet been initialized, ignore it
            # but state that this method call did not close the SSH client, but was already closed
            pass

        # take down sshproxy_session no matter what happened to the control session itself
        if self.sshproxy_session is not None:
            self.sshproxy_session.stop_thread()

        return retval

    def home_exists(self):
        """\
        Test if the remote home directory exists.

        @return: C{True} if the home directory exists, C{False} otherwise
        @rtype: C{bool}

        """
        (_stdin, _stdout, _stderr) = self._x2go_exec_command('stat -tL "%s"' % self._x2go_remote_home, loglevel=log.loglevel_DEBUG)
        if _stdout.read():
            return True
        return False


    def is_alive(self):
        """\
        Test if the connection to the remote X2Go server is still alive.

        @return: C{True} if the connection is still alive, C{False} otherwise
        @rtype: C{bool}

        """
        try:
            if self._x2go_exec_command('echo', loglevel=log.loglevel_DEBUG):
                return True
        except x2go_exceptions.X2GoControlSessionException:
            self.session_died = True
            self.disconnect()
        return False

    def has_session_died(self):
        """\
        Test if the connection to the remote X2Go server died on the way.

        @return: C{True} if the connection has died, C{False} otherwise
        @rtype: C{bool}

        """
        return self.session_died

    def get_published_applications(self, lang=None, refresh=False, raw=False, very_raw=False, max_no_submenus=defaults.PUBAPP_MAX_NO_SUBMENUS):
        """\
        Retrieve the menu tree of published applications from the remote X2Go server.

        The C{raw} option lets this method return a C{list} of C{dict} elements. Each C{dict} elements has a 
        C{desktop} key containing a shortened version of the text output of a .desktop file and an C{icon} key
        which contains the desktop base64-encoded icon data.

        The {very_raw} lets this method return the output of the C{x2gogetapps} script as is.

        @param lang: locale/language identifier
        @type lang: C{str}
        @param refresh: force reload of the menu tree from X2Go server
        @type refresh: C{bool}
        @param raw: retrieve a raw output of the server list of published applications
        @type raw: C{bool}
        @param very_raw: retrieve a very raw output of the server list of published applications
        @type very_raw: C{bool}

        @return: an i18n capable menu tree packed as a Python dictionary
        @rtype: C{list}

        """
        self._already_querying_published_applications.acquire()

        if defaults.X2GOCLIENT_OS != 'Windows' and lang is None:
            lang = locale.getdefaultlocale()[0]
        elif lang is None:
            lang = 'en'

        if 'X2GO_PUBLISHED_APPLICATIONS' in self.get_server_features():
            if self._published_applications_menu is {} or \
               not self._published_applications_menu.has_key(lang) or \
               raw or very_raw or refresh or \
               (self.published_applications_no_submenus != max_no_submenus):

                self.published_applications_no_submenus = max_no_submenus

                ### STAGE 1: retrieve menu from server

                self.logger('querying server (%s) for list of published applications' % self.profile_name, loglevel=log.loglevel_NOTICE)
                (stdin, stdout, stderr) = self._x2go_exec_command('which x2gogetapps >/dev/null && x2gogetapps')
                _raw_output = stdout.read()
                #self.logger('====>>>>VG: published applications %s' % _raw_output, loglevel=log.loglevel_NOTICE)
                
                if very_raw:
                    self.logger('published applications query for %s finished, return very raw output' % self.profile_name, loglevel=log.loglevel_NOTICE)
                    self._already_querying_published_applications.release()
                    return _raw_output

                ### STAGE 2: dissect the text file retrieved from server, cut into single menu elements

                _raw_menu_items = _raw_output.split('</desktop>\n')
                _raw_menu_items = [ i.replace('<desktop>\n', '') for i in _raw_menu_items ]
                _menu = []
                for _raw_menu_item in _raw_menu_items:
                    if '<icon>\n' in _raw_menu_item and '</icon>' in _raw_menu_item:
                        _menu_item = _raw_menu_item.split('<icon>\n')[0] + _raw_menu_item.split('</icon>\n')[1]
                        _icon_base64 = _raw_menu_item.split('<icon>\n')[1].split('</icon>\n')[0]
                    else:
                        _menu_item = _raw_menu_item
                        _icon_base64 = None
                    if _menu_item:
                        _menu.append({ 'desktop': _menu_item, 'icon': _icon_base64, })
                        _menu_item = None
                        _icon_base64 = None

                if raw:
                    self.logger('published applications query for %s finished, returning raw output' % self.profile_name, loglevel=log.loglevel_NOTICE)
                    self._already_querying_published_applications.release()
                    return _menu

                if len(_menu) > max_no_submenus >= 0:
                    _render_submenus = True
                else:
                    _render_submenus = False
                #Apprime force submenus
                #_render_submenus = True

                # STAGE 3: create menu structure in a Python dictionary

                _category_map = {
                    lang: {
                        'Multimedia': [],
                        'Development': [],
                        'Education': [],
                        'Games': [],
                        'Graphics': [],
                        'Internet': [],
                        'Office': [],
                        'System': [],
                        'Utilities': [],
                        'Other Applications': [],
                        'TOP': [],
                    }
                }
                _empty_menus = _category_map[lang].keys()

                for item in _menu:

                    _menu_entry_name = ''
                    _menu_entry_fallback_name = ''
                    _menu_entry_comment = ''
                    _menu_entry_fallback_comment = ''
                    _menu_entry_exec = ''
                    _menu_entry_cat = ''
                    _menu_entry_shell = False

                    lang_regio = lang
                    lang_only = lang_regio.split('_')[0]

                    for line in item['desktop'].split('\n'):
                        if re.match('^Name\[%s\]=.*' % lang_regio, line) or re.match('Name\[%s\]=.*' % lang_only, line):
                            _menu_entry_name = line.split("=")[1].strip()
                        elif re.match('^Name=.*', line):
                            _menu_entry_fallback_name = line.split("=")[1].strip()
                        elif re.match('^Comment\[%s\]=.*' % lang_regio, line) or re.match('Comment\[%s\]=.*' % lang_only, line):
                            _menu_entry_comment = line.split("=")[1].strip()
                        elif re.match('^Comment=.*', line):
                            _menu_entry_fallback_comment = line.split("=")[1].strip()
                        elif re.match('^Exec=.*', line):
                            _menu_entry_exec = line.split("=")[1].strip()
                        elif re.match('^Terminal=.*(t|T)(r|R)(u|U)(e|E).*', line):
                            _menu_entry_shell = True
                        elif re.match('^Categories=.*', line):
                            self.logger('====>>>> category line=%s' % line, loglevel=log.loglevel_NOTICE)
                            if 'X2Go-Top' in line:
                                _menu_entry_cat = 'TOP'
                            elif 'Audio' in line or 'Video' in line:
                                _menu_entry_cat = 'Multimedia'
                            elif 'Development' in line:
                                _menu_entry_cat = 'Development'
                            elif 'Education' in line:
                                _menu_entry_cat = 'Education'
                            elif 'Game' in line:
                                _menu_entry_cat = 'Games'
                            elif 'Graphics' in line:
                                _menu_entry_cat = 'Graphics'
                            elif 'Network' in line:
                                _menu_entry_cat = 'Internet'
                            elif 'Office' in line:
                                _menu_entry_cat = 'Office'
                            elif 'Settings' in line:
                                continue
                            elif 'System' in line:
                                _menu_entry_cat = 'System'
                            elif 'Utility' in line:
                                _menu_entry_cat = 'Utilities'
                            else:
                                _menu_entry_cat = 'Other Applications'
                    if not _menu_entry_exec:
                        continue
                    else:
                        # FIXME: strip off any noted options (%f, %F, %u, %U, ...), this can be more intelligent
                        _menu_entry_exec = _menu_entry_exec.replace('%f', '').replace('%F','').replace('%u','').replace('%U','')
                        if _menu_entry_shell:
                            _menu_entry_exec = "x-terminal-emulator -e '%s'" % _menu_entry_exec

                    if not _menu_entry_cat:
                        _menu_entry_cat = 'Other Applications'

                    if not _render_submenus:
                        _menu_entry_cat = 'TOP'

                    if _menu_entry_cat in _empty_menus:
                        _empty_menus.remove(_menu_entry_cat)

                    if not _menu_entry_name: _menu_entry_name = _menu_entry_fallback_name
                    if not _menu_entry_comment: _menu_entry_comment = _menu_entry_fallback_comment
                    if not _menu_entry_comment: _menu_entry_comment = _menu_entry_name

                    _menu_entry_icon = item['icon']

                    self.logger('====>>>> Pubapp name=%s, category=%s' % (_menu_entry_name, _menu_entry_cat), loglevel=log.loglevel_NOTICE)
                    _category_map[lang][_menu_entry_cat].append(
                        {
                            'name': _menu_entry_name,
                            'comment': _menu_entry_comment,
                            'exec': _menu_entry_exec,
                            'icon': _menu_entry_icon,
                        }
                    )

                for _cat in _empty_menus:
                    del _category_map[lang][_cat]

                for _cat in _category_map[lang].keys():
                    _sorted = sorted(_category_map[lang][_cat], key=lambda k: k['name'])
                    _category_map[lang][_cat] = _sorted

                self._published_applications_menu.update(_category_map)
                self.logger('published applications query for %s finished, return menu tree' % self.profile_name, loglevel=log.loglevel_NOTICE)

        else:
            # FIXME: ignoring the absence of the published applications feature for now, handle it appropriately later
            pass

        self._already_querying_published_applications.release()
        self.logger('====>>>>VG: published applications menu returned', loglevel=log.loglevel_NOTICE)
        return self._published_applications_menu

    def start(self, **kwargs):
        """\
        Start a new X2Go session.

        The L{X2GoControlSession.start()} method accepts any parameter
        that can be passed to any of the C{X2GoTerminalSession} backend class
        constructors.

        @param kwargs: parameters that get passed through to the control session's
            L{resume()} method, only the C{session_name} parameter will get removed
            before pass-through
        @type kwargs: C{dict}

        @return: return value of the cascaded L{resume()} method, denoting the success or failure
            of the session startup
        @rtype: C{bool}

        """
        if 'session_name' in kwargs.keys():
            del kwargs['session_name']
        return self.resume(**kwargs)

    def resume(self, session_name=None, session_instance=None, session_list=None, **kwargs):
        """\
        Resume a running/suspended X2Go session. 

        The L{X2GoControlSession.resume()} method accepts any parameter
        that can be passed to any of the C{X2GoTerminalSession*} backend class constructors.

        @return: True if the session could be successfully resumed
        @rtype: C{bool}

        @raise X2GoUserException: if the remote user is not allowed to launch/resume X2Go sessions.

        """
        if self.get_transport() is not None:

            if not self.is_x2gouser(self.get_transport().get_username()):
                raise x2go_exceptions.X2GoUserException('remote user %s is not allowed to run X2Go commands' % self.get_transport().get_username())

            session_info = None
            try:
                if session_name is not None:
                    if session_list:
                        session_info = session_list[session_name]
                    else:
                        session_info = self.list_sessions()[session_name]
            except KeyError:
                _success = False

            _terminal = self._terminal_backend(self,
                                               profile_name=self.profile_name,
                                               session_info=session_info,
                                               info_backend=self._info_backend,
                                               list_backend=self._list_backend,
                                               proxy_backend=self._proxy_backend,
                                               client_rootdir=self.client_rootdir,
                                               session_instance=session_instance,
                                               sessions_rootdir=self.sessions_rootdir,
                                               **kwargs)

            _success = False
            try:
                if session_name is not None:
                    _success = _terminal.resume()
                else:
                    _success = _terminal.start()
            except x2go_exceptions.X2GoTerminalSessionException:
                _success = False

            if _success:
                while not _terminal.ok():
                    gevent.sleep(.2)

                if _terminal.ok():
                    self.associated_terminals[_terminal.get_session_name()] = _terminal
                    self.get_transport().reverse_tunnels[_terminal.get_session_name()] = {
                        'sshfs': (0, None),
                        'snd': (0, None),
                    }

                    return _terminal or None

        return None

    def share_desktop(self, desktop=None, user=None, display=None, share_mode=0, **kwargs):
        """\
        Share another already running desktop session. Desktop sharing can be run
        in two different modes: view-only and full-access mode.

        @param desktop: desktop ID of a sharable desktop in format C{<user>@<display>}
        @type desktop: C{str}
        @param user: user name and display number can be given separately, here give the
            name of the user who wants to share a session with you
        @type user: C{str}
        @param display: user name and display number can be given separately, here give the
            number of the display that a user allows you to be shared with
        @type display: C{str}
        @param share_mode: desktop sharing mode, 0 stands for VIEW-ONLY, 1 for  FULL-ACCESS mode
        @type share_mode: C{int}

        @return: True if the session could be successfully shared
        @rtype: C{bool}

        @raise X2GoDesktopSharingException: if C{username} and C{dislpay} do not relate to a
            sharable desktop session

        """
        if desktop:
            user = desktop.split('@')[0]
            display = desktop.split('@')[1]
        if not (user and display):
            raise x2go_exceptions.X2GoDesktopSharingException('Need user name and display number of shared desktop.')

        cmd = '%sXSHAD%sXSHAD%s' % (share_mode, user, display)

        kwargs['cmd'] = cmd
        kwargs['session_type'] = 'shared'

        return self.start(**kwargs)

    def list_desktops(self, raw=False, maxwait=20):
        """\
        List all desktop-like sessions of current user (or of users that have 
        granted desktop sharing) on the connected server.

        @param raw: if C{True}, the raw output of the server-side X2Go command 
            C{x2golistdesktops} is returned.
        @type raw: C{bool}

        @return: a list of X2Go desktops available for sharing
        @rtype: C{list}

        @raise X2GoTimeOutException: on command execution timeouts, with the server-side C{x2golistdesktops}
            command this can sometimes happen. Make sure you ignore these time-outs and to try again

        """
        if raw:
            (stdin, stdout, stderr) = self._x2go_exec_command("export HOSTNAME && x2golistdesktops")
            return stdout.read(), stderr.read()

        else:

            # this _success loop will catch errors in case the x2golistsessions output is corrupt
            # this should not be needed and is a workaround for the current X2Go server implementation

            if self.low_latency:
                maxwait = maxwait * 2

            timeout = gevent.Timeout(maxwait)
            timeout.start()
            try:
                (stdin, stdout, stderr) = self._x2go_exec_command("export HOSTNAME && x2golistdesktops")
                _stdout_read = stdout.read()
                _listdesktops = _stdout_read.split('\n')
            except gevent.timeout.Timeout:
                # if we do not get a reply here after <maxwait> seconds we will raise a time out, we have to
                # make sure that we catch this at places where we want to ignore timeouts (e.g. in the 
                # desktop list cache)
                raise x2go_exceptions.X2GoTimeOutException('x2golistdesktop command timed out')
            finally:
                timeout.cancel()

            return _listdesktops

    def list_mounts(self, session_name, raw=False, maxwait=20):
        """\
        List all mounts for a given session of the current user on the connected server.

        @param session_name: name of a session to query a list of mounts for
        @type session_name: C{str}
        @param raw: if C{True}, the raw output of the server-side X2Go command 
            C{x2golistmounts} is returned.
        @type raw: C{bool}
        @param maxwait: stop processing C{x2golistmounts} after C{<maxwait>} seconds
        @type maxwait: C{int}

        @return: a list of client-side mounts for X2Go session C{<session_name>} on the server
        @rtype: C{list}

        @raise X2GoTimeOutException: on command execution timeouts, queries with the server-side
            C{x2golistmounts} query should normally be processed quickly, a time-out may hint that the
            control session has lost its connection to the X2Go server

        """
        if raw:
            (stdin, stdout, stderr) = self._x2go_exec_command("export HOSTNAME && x2golistmounts %s" % session_name)
            return stdout.read(), stderr.read()

        else:

            if self.low_latency:
                maxwait = maxwait * 2

            # this _success loop will catch errors in case the x2golistmounts output is corrupt

            timeout = gevent.Timeout(maxwait)
            timeout.start()
            try:
                (stdin, stdout, stderr) = self._x2go_exec_command("export HOSTNAME && x2golistmounts %s" % session_name)
                _stdout_read = stdout.read()
                _listmounts = {session_name: [ line for line in _stdout_read.split('\n') if line ] }
            except gevent.timeout.Timeout:
                # if we do not get a reply here after <maxwait> seconds we will raise a time out, we have to
                # make sure that we catch this at places where we want to ignore timeouts
                raise x2go_exceptions.X2GoTimeOutException('x2golistmounts command timed out')
            finally:
                timeout.cancel()

            return _listmounts

    def list_sessions(self, raw=False):
        """\
        List all sessions of current user on the connected server.

        @param raw: if C{True}, the raw output of the server-side X2Go command 
            C{x2golistsessions} is returned.
        @type raw: C{bool}

        @return: normally an instance of a C{X2GoServerSessionList*} backend is returned. However,
            if the raw argument is set, the plain text output of the server-side C{x2golistsessions}
            command is returned
        @rtype: C{X2GoServerSessionList} instance or str

        @raise X2GoControlSessionException: on command execution timeouts, if this happens the control session will
            be interpreted as disconnected due to connection loss
        """
        if raw:
            if 'X2GO_LIST_SHADOWSESSIONS' in self._x2go_server_features:
                (stdin, stdout, stderr) = self._x2go_exec_command("export HOSTNAME && { x2golistsessions; x2golistshadowsessions; }")
            else:
                (stdin, stdout, stderr) = self._x2go_exec_command("export HOSTNAME && x2golistsessions")
            #vgo = stdout.read()
            #vge = stderr.read()
            #self.logger('====>>>>x2golistsessions output: ' % vgo, loglevel=log.loglevel_NOTICE)
            #self.logger('====>>>>x2golistsessions error : ' % vge, loglevel=log.loglevel_NOTICE)
            #return vgo, vge
            return stdout.read(), stderr.read()
            
        else:

            # this _success loop will catch errors in case the x2golistsessions output is corrupt
            # this should not be needed and is a workaround for the current X2Go server implementation
            _listsessions = {}
            _success = False
            _count = 0
            _maxwait = 20

            # we will try this 20 times before giving up... we might simply catch the x2golistsessions
            # output in the middle of creating a session in the database...
            while not _success and _count < _maxwait:
                _count += 1
                try:
                    if 'X2GO_LIST_SHADOWSESSIONS' in self._x2go_server_features:
                        (stdin, stdout, stderr) = self._x2go_exec_command("export HOSTNAME && { x2golistsessions; x2golistshadowsessions; }")
                    else:
                        (stdin, stdout, stderr) = self._x2go_exec_command("export HOSTNAME && x2golistsessions")
                    self.logger('controlsession.list_session iteration = %d' % _count, loglevel=log.loglevel_INFO)
                    _stdout_read = stdout.read()
                    self.logger('====>>>>x2golistsessions output: %s' % _stdout_read, loglevel=log.loglevel_NOTICE)
                    _listsessions = self._list_backend(_stdout_read, info_backend=self._info_backend).sessions
                    _success = True
                except KeyError:
                    gevent.sleep(1)
                except IndexError:
                    gevent.sleep(1)
                except ValueError:
                    gevent.sleep(1)

            if _count >= _maxwait:
                self.session_died = True
                self.disconnect()
                raise x2go_exceptions.X2GoControlSessionException('x2golistsessions command failed after we have tried 20 times')

            # update internal variables when list_sessions() is called
            if _success and not self.session_died:
                for _session_name, _terminal in self.associated_terminals.items():
                    if _session_name in _listsessions.keys():
                        # update the whole session_info object within the terminal session
                        if hasattr(self.associated_terminals[_session_name], 'session_info') and not self.associated_terminals[_session_name].is_session_info_protected():
                            self.associated_terminals[_session_name].session_info.update(_listsessions[_session_name])
                    else:
                        self.associated_terminals[_session_name].__del__()
                        try: del self.associated_terminals[_session_name]
                        except KeyError: pass
                        self.terminated_terminals.append(_session_name)
                    if _terminal.is_suspended():
                        self.associated_terminals[_session_name].__del__()
                        try: del self.associated_terminals[_session_name]
                        except KeyError: pass

            return _listsessions

    def clean_sessions(self, destroy_terminals=True, published_applications=False):
        """\
        Find X2Go terminals that have previously been started by the
        connected user on the remote X2Go server and terminate them.

        @param destroy_terminals: destroy the terminal session instances after cleanup
        @type destroy_terminals: C{bool}
        @param published_applications: also clean up published applications providing sessions
        @type published_applications: C{bool}

        """
        session_list = self.list_sessions()
        if published_applications:
            session_names = session_list.keys()
        else:
            session_names = [ _sn for _sn in session_list.keys() if not session_list[_sn].is_published_applications_provider() ]
        for session_name in session_names:
            if self.associated_terminals.has_key(session_name):
                self.associated_terminals[session_name].terminate()
                if destroy_terminals:
                    if self.associated_terminals[session_name] is not None:
                        self.associated_terminals[session_name].__del__()
                    try: del self.associated_terminals[session_name]
                    except KeyError: pass
            else:
                self.terminate(session_name=session_name)

    def is_connected(self):
        """\
        Returns C{True} if this control session is connected to the remote server (that
        is: if it has a valid Paramiko/SSH transport object).

        @return: X2Go session connected?
        @rtype: C{bool}

        """
        return self.get_transport() is not None and self.get_transport().is_authenticated()

    def is_running(self, session_name):
        """\
        Returns C{True} if the given X2Go session is in running state,
        C{False} else.

        @param session_name: X2Go name of the session to be queried
        @type session_name: C{str}

        @return: X2Go session running? If C{<session_name>} is not listable by the L{list_sessions()} method then C{None} is returned
        @rtype: C{bool} or C{None}

        """
        session_infos = self.list_sessions()
        if session_name in session_infos.keys():
            return session_infos[session_name].is_running()
        return None

    def is_suspended(self, session_name):
        """\
        Returns C{True} if the given X2Go session is in suspended state,
        C{False} else.

        @return: X2Go session suspended? If C{<session_name>} is not listable by the L{list_sessions()} method then C{None} is returned
        @rtype: C{bool} or C{None}

        """
        session_infos = self.list_sessions()
        if session_name in session_infos.keys():
            return session_infos[session_name].is_suspended()
        return None

    def has_terminated(self, session_name):
        """\
        Returns C{True} if the X2Go session with name C{<session_name>} has been seen
        by this control session and--in the meantime--has been terminated.

        If C{<session_name>} has not been seen, yet, the method will return C{None}.

        @return: X2Go session has terminated?
        @rtype: C{bool} or C{None}

        """
        session_infos = self.list_sessions()
        if session_name in self.terminated_terminals:
            return True
        if session_name not in session_infos.keys() and session_name in self.associated_terminals.keys():
            # do a post-mortem tidy up
            self.terminate(session_name)
            return True
        if self.is_suspended(session_name) or self.is_running(session_name):
            return False

        return None

    def suspend(self, session_name):
        """\
        Suspend X2Go session with name C{<session_name>} on the connected
        server.

        @param session_name: X2Go name of the session to be suspended
        @type session_name: C{str}

        @return: C{True} if the session could be successfully suspended
        @rtype: C{bool}

        """
        _ret = False
        _session_names = [ t.get_session_name() for t in self.associated_terminals.values() ]
        if session_name in _session_names:

            self.logger('suspending associated terminal session: %s' % session_name, loglevel=log.loglevel_DEBUG)
            (stdin, stdout, stderr) = self._x2go_exec_command("x2gosuspend-session %s" % session_name, loglevel=log.loglevel_DEBUG)
            stdout.read()
            stderr.read()
            if self.associated_terminals.has_key(session_name):
                if self.associated_terminals[session_name] is not None:
                    self.associated_terminals[session_name].__del__()
                try: del self.associated_terminals[session_name]
                except KeyError: pass
            _ret = True

        else:

            self.logger('suspending non-associated terminal session: %s' % session_name, loglevel=log.loglevel_DEBUG)
            (stdin, stdout, stderr) = self._x2go_exec_command("x2gosuspend-session %s" % session_name, loglevel=log.loglevel_DEBUG)
            stdout.read()
            stderr.read()
            _ret = True

        return _ret

    def terminate(self, session_name, destroy_terminals=True):
        """\
        Terminate X2Go session with name C{<session_name>} on the connected
        server.

        @param session_name: X2Go name of the session to be terminated
        @type session_name: C{str}

        @return: C{True} if the session could be successfully terminated
        @rtype: C{bool}

        """

        _ret = False
        if session_name in self.associated_terminals.keys():

            self.logger('terminating associated session: %s' % session_name, loglevel=log.loglevel_DEBUG)
            (stdin, stdout, stderr) = self._x2go_exec_command("x2goterminate-session %s" % session_name, loglevel=log.loglevel_DEBUG)
            stdout.read()
            stderr.read()

            if destroy_terminals:
                if self.associated_terminals[session_name] is not None:
                    self.associated_terminals[session_name].__del__()
                try: del self.associated_terminals[session_name]
                except KeyError: pass

            self.terminated_terminals.append(session_name)
            _ret = True

        else:

            self.logger('terminating non-associated session: %s' % session_name, loglevel=log.loglevel_DEBUG)
            (stdin, stdout, stderr) = self._x2go_exec_command("x2goterminate-session %s" % session_name, loglevel=log.loglevel_DEBUG)
            stdout.read()
            stderr.read()
            _ret = True

        return _ret
