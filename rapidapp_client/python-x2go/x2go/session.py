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
X2GoSession class - a public API of Python X2Go, handling standalone X2Go 
sessions.

This class is normally embedded into the context of an L{X2GoClient}
instance, but it is also possible to address L{X2GoSession}s directly via this
class.

To launch a session manually from the Python interactive shell, perform these
simple steps::

  $ python
  Python 2.6.6 (r266:84292, Dec 26 2010, 22:31:48) 
  [GCC 4.4.5] on linux2
  Type "help", "copyright", "credits" or "license" for more information.
  >>> import x2go
  >>> import gevent
  Xlib.protocol.request.QueryExtension
  >>> s = x2go.session.X2GoSession()
  >>> s.set_server('<my.x2go.server>')
  >>> s.set_port(<ssh-port>)
  >>> s.connect('<my-login>', '<my-password>')
  [<pidno>] (x2gocontrolsession-pylib) NOTICE: connecting to [<my.x2go.server>]:<ssh-port>
  [<pidno>] (x2gosession-pylib) NOTICE: SSH host key verification for host [<my.x2go.server>]:<ssh-port> with SSH-RSA fingerprint ,,<ssh-fingerprint>'' initiated. We are seeing this X2Go server for the first time.
  [<pidno>] (x2gosession-pylib) WARN: HOOK_check_host_dialog: host check requested for [<my.x2go.server>]:<ssh-port> with SSH-RSA fingerprint: ,,<ssh-fingerprint>''. Automatically adding host as known host.
  True
  >>> s.start(cmd="LXDE")
  True
  >>> while True: gevent.sleep(1)

"""

__NAME__ = 'x2gosession-pylib'

import os
import copy
import types
import uuid
import time
import gevent
import re
import threading
import base64

# FIXME: we need the list of keys from a potentially used SSH agent. This part of code has to be moved into the control session code
import paramiko

# Python X2Go modules
import defaults
import log
import utils
import session
import x2go_exceptions

from defaults import X2GOCLIENT_OS as _X2GOCLIENT_OS
from defaults import LOCAL_HOME as _LOCAL_HOME
from defaults import X2GO_CLIENT_ROOTDIR as _X2GO_CLIENT_ROOTDIR
from defaults import X2GO_SESSIONS_ROOTDIR as _X2GO_SESSIONS_ROOTDIR
from defaults import X2GO_SSH_ROOTDIR as _X2GO_SSH_ROOTDIR

from defaults import BACKENDS as _BACKENDS

from defaults import SUPPORTED_SOUND, SUPPORTED_PRINTING, SUPPORTED_FOLDERSHARING, SUPPORTED_MIMEBOX, SUPPORTED_TELEKINESIS

_X2GO_SESSION_PARAMS = ('use_sshproxy', 'sshproxy_reuse_authinfo',
                        'profile_id', 'session_name',
                        'auto_start_or_resume', 'auto_connect',
                        'printing', 'allow_mimebox',
                        'mimebox_extensions', 'mimebox_action',
                        'allow_share_local_folders', 'share_local_folders', 'restore_shared_local_folders',
                        'control_backend', 'terminal_backend', 'info_backend', 'list_backend', 'proxy_backend', 'settings_backend', 'printing_backend',
                        'client_rootdir', 'sessions_rootdir', 'ssh_rootdir',
                        'keep_controlsession_alive', 'add_to_known_hosts', 'known_hosts', 'forward_sshagent',
                        'connected', 'virgin', 'running', 'suspended', 'terminated', 'faulty'
                        'client_instance',
                       )
"""A list of allowed X2Go pure session parameters (i.e. parameters that are passed on neither to an X2GoControlSession, X2GoSSHProxy nor an X2GoControlSession object."""
# options of the paramiko.SSHClient().connect() method, any option that is allowed for a terminal session instance
_X2GO_TERMINAL_PARAMS = ('geometry', 'depth', 'link', 'pack', 'dpi',
                         'cache_type', 'kbtype', 'kblayout', 'kbvariant', 'clipboard',
                         'session_type', 'snd_system', 'snd_port',
                         'cmd', 'set_session_title', 'session_title',
                         'rdp_server', 'rdp_options', 'applications',
                         'xdmcp_server',
                         'rootdir', 'loglevel', 'profile_name', 'profile_id',
                         'print_action', 'print_action_args',
                         'convert_encoding', 'client_encoding', 'server_encoding',
                         'proxy_options', 'published_applications', 'published_applications_no_submenus',
                         'logger',
                         'control_backend', 'terminal_backend', 'proxy_backend',
                         'profiles_backend', 'settings_backend', 'printing_backend',
                        )
"""A list of allowed X2Go terminal session parameters."""
_X2GO_SSHPROXY_PARAMS = ('sshproxy_host', 'sshproxy_port', 'sshproxy_user', 'sshproxy_password',
                         'sshproxy_key_filename', 'sshproxy_pkey', 'sshproxy_passphrase',
                         'sshproxy_look_for_keys', 'sshproxy_allow_agent',
                         'sshproxy_tunnel',
                        )
"""A list of allowed X2Go SSH proxy parameters."""


class X2GoSession(object):
    """\
    Public API class for launching X2Go sessions. Recommended is to manage X2Go sessions from
    within an L{X2GoClient} instance. However, Python X2Go is designed in a way that it also
    allows the management of singel L{X2GoSession} instance.

    Thus, you can use the L{X2GoSession} class to manually set up X2Go sessions without 
    L{X2GoClient} context (session registry, session list cache, auto-registration of new
    sessions etc.).

    """
    def __init__(self, server=None, port=22, control_session=None,
                 use_sshproxy=False,
                 sshproxy_reuse_authinfo=False,
                 profile_id=None, profile_name='UNKNOWN',
                 session_name=None,
                 auto_start_or_resume=False,
                 auto_connect=False,
                 printing=False,
                 allow_mimebox=False,
                 mimebox_extensions=[],
                 mimebox_action='OPEN',
                 allow_share_local_folders=False,
                 share_local_folders=[],
                 restore_shared_local_folders=False,
                 control_backend=_BACKENDS['X2GoControlSession']['default'],
                 terminal_backend=_BACKENDS['X2GoTerminalSession']['default'],
                 info_backend=_BACKENDS['X2GoServerSessionInfo']['default'],
                 list_backend=_BACKENDS['X2GoServerSessionList']['default'],
                 proxy_backend=_BACKENDS['X2GoProxy']['default'],
                 settings_backend=_BACKENDS['X2GoClientSettings']['default'],
                 printing_backend=_BACKENDS['X2GoClientPrinting']['default'],
                 client_rootdir=os.path.join(_LOCAL_HOME, _X2GO_CLIENT_ROOTDIR),
                 sessions_rootdir=os.path.join(_LOCAL_HOME, _X2GO_SESSIONS_ROOTDIR),
                 ssh_rootdir=os.path.join(_LOCAL_HOME, _X2GO_SSH_ROOTDIR),
                 keep_controlsession_alive=False,
                 add_to_known_hosts=False,
                 known_hosts=None,
                 forward_sshagent=False,
                 logger=None, loglevel=log.loglevel_DEFAULT,
                 connected=False, activated=False, virgin=True, running=None, suspended=None, terminated=None, faulty=None,
                 client_instance=None,
                 **params):
        """\
        @param server: hostname of X2Go server
        @type server: C{str}
        @param control_session: an already initialized C{X2GoControlSession*} instance
        @type control_session: C{X2GoControlSession*} instance
        @param use_sshproxy: for communication with X2Go server use an SSH proxy host
        @type use_sshproxy: C{bool}
        @param sshproxy_reuse_authinfo: for proxy authentication re-use the X2Go session's password / key file
        @type sshproxy_reuse_authinfo: C{bool}
        @param profile_id: profile ID
        @type profile_id: C{str}
        @param profile_name: profile name
        @type profile_name: C{str}
        @param session_name: session name (if available)
        @type session_name: C{str}
        @param auto_start_or_resume: automatically start a new or resume latest session after connect
        @type auto_start_or_resume: C{bool}
        @param auto_connect: call a hook method that handles connecting the session profile automatically after a session for this profile has been registered
        @type auto_connect: C{bool}
        @param printing: enable X2Go printing
        @type printing: C{bool}
        @param allow_mimebox: enable X2Go MIME box support
        @type allow_mimebox: C{bool}
        @param mimebox_extensions: whitelist of allowed X2Go MIME box extensions
        @type mimebox_extensions: C{list}
        @param mimebox_action: action for incoming X2Go MIME box files
        @type mimebox_action: C{X2GoMimeBoxAction*} or C{str}
        @param allow_share_local_folders: enable local folder sharing support
        @type allow_share_local_folders: C{bool}
        @param share_local_folders: list of local folders to share with the remote X2Go session
        @type share_local_folders: C{list}
        @param restore_shared_local_folders: store actual list of shared local folders after session has been suspended or terminated
        @type restore_shared_local_folders: C{bool}
        @param control_backend: X2Go control session backend to use
        @type control_backend: C{str}
        @param terminal_backend: X2Go terminal session backend to use
        @type terminal_backend: C{str}
        @param info_backend: X2Go session info backend to use
        @type info_backend: C{str}
        @param list_backend: X2Go session list backend to use
        @type list_backend: C{str}
        @param proxy_backend: X2Go proxy backend to use
        @type proxy_backend: C{str}
        @param settings_backend: X2Go client settings backend to use
        @type settings_backend: C{str}
        @param printing_backend: X2Go client printing backend to use
        @type printing_backend: C{str}
        @param client_rootdir: client base dir (default: ~/.x2goclient)
        @type client_rootdir: C{str}
        @param sessions_rootdir: sessions base dir (default: ~/.x2go)
        @type sessions_rootdir: C{str}
        @param ssh_rootdir: ssh base dir (default: ~/.ssh)
        @type ssh_rootdir: C{str}
        @param keep_controlsession_alive: On last L{X2GoSession.disconnect()} keep the associated C{X2GoControlSession*} instance alive?
        @ŧype keep_controlsession_alive: C{bool}
        @param add_to_known_hosts: Auto-accept server host validity?
        @type add_to_known_hosts: C{bool}
        @param known_hosts: the underlying Paramiko/SSH systems C{known_hosts} file
        @type known_hosts: C{str}
        @param forward_sshagent: forward SSH agent authentication requests to the SSH agent on the X2Go client-side
        @type forward_sshagent: C{bool}
        @param connected: manipulate session state »connected« by giving a pre-set value
        @type connected: C{bool}
        @param activated: normal leave this untouched, an activated session is a session that is about to be used
        @type activated: C{bool}
        @param virgin: manipulate session state »virgin« by giving a pre-set value
        @type virgin: C{bool}
        @param running: manipulate session state »running« by giving a pre-set value
        @type running: C{bool}
        @param suspended: manipulate session state »suspended« by giving a pre-set value
        @type suspended: C{bool}
        @param terminated: manipulate session state »terminated« by giving a pre-set value
        @type terminated: C{bool}
        @param faulty: manipulate session state »faulty« by giving a pre-set value
        @type faulty: C{bool}
        @param client_instance: if available, the underlying L{X2GoClient} instance
        @type client_instance: C{X2GoClient} instance
        @param params: further control session, terminal session and SSH proxy class options
        @type params: C{dict}

        """
        if logger is None:
            self.logger = log.X2GoLogger(loglevel=loglevel)
        else:
            self.logger = copy.deepcopy(logger)
        self.logger.tag = __NAME__

        self._keep = None

        self.uuid = uuid.uuid1()
        self.connected = connected

        self.activated = activated
        self.virgin = virgin
        self.running = running
        self.suspended = suspended
        self.terminated = terminated
        self.faulty = faulty
        self.keep_controlsession_alive = keep_controlsession_alive

        self.profile_id = profile_id
        self.profile_name = profile_name
        self.session_name = session_name
        self.server = server
        self.port = port

        self._last_status = None

        self.locked = False

        self.auto_start_or_resume = auto_start_or_resume
        self.auto_connect = auto_connect
        self.printing = printing
        self.allow_share_local_folders = allow_share_local_folders
        self.share_local_folders = share_local_folders
        self.restore_shared_local_folders = restore_shared_local_folders
        self.allow_mimebox = allow_mimebox
        self.mimebox_extensions = mimebox_extensions
        self.mimebox_action = mimebox_action
        self.control_backend = utils._get_backend_class(control_backend, "X2GoControlSession")
        self.terminal_backend = utils._get_backend_class(terminal_backend, "X2GoTerminalSession")
        self.info_backend = utils._get_backend_class(info_backend, "X2GoServerSessionInfo")
        self.list_backend = utils._get_backend_class(list_backend, "X2GoServerSessionList")
        self.proxy_backend = utils._get_backend_class(proxy_backend, "X2GoProxy")
        self.settings_backend = utils._get_backend_class(settings_backend, "X2GoClientSettings")
        self.printing_backend = utils._get_backend_class(printing_backend, "X2GoClientPrinting")
        self.client_rootdir = client_rootdir
        self.sessions_rootdir = sessions_rootdir
        self.ssh_rootdir = ssh_rootdir
        self.control_session = control_session

        if params.has_key('published_applications'):
            self.published_applications = params['published_applications']
            if self.published_applications:
                params['cmd'] = 'PUBLISHED'
        else:
            self.published_applications = params['published_applications'] = False

        if params.has_key('cmd') and params['cmd'] != 'PUBLISHED':
            self.published_applications = params['published_applications'] = False
        self.published_applications_menu = None

        if self.session_name:
            if not re.match('.*_stRPUBLISHED_.*',self.session_name):
                self.published_applications = params['published_applications'] = False

        self.use_sshproxy = use_sshproxy
        self.sshproxy_reuse_authinfo = sshproxy_reuse_authinfo

        self.control_params = {}
        self.terminal_params = {}
        self.sshproxy_params = {}
        self.update_params(params)
        self.shared_folders = {}

        self.session_environment = {}
        self.server_features = []

        try: del self.control_params['server']
        except: pass

        self.client_instance = client_instance

        if self.logger.get_loglevel() & log.loglevel_DEBUG:
            self.logger('X2Go control session parameters for profile %s:' % profile_name, loglevel=log.loglevel_DEBUG)
            for p in [ _p for _p in self.control_params if not _p.endswith('pkey') ]:
                self.logger('    %s: %s' % (p, self.control_params[p]), log.loglevel_DEBUG)
            self.logger('X2Go terminal session parameters for profile %s:' % profile_name, loglevel=log.loglevel_DEBUG)
            for p in self.terminal_params:
                self.logger('    %s: %s' % (p,self.terminal_params[p]), log.loglevel_DEBUG)
            self.logger('X2Go sshproxy parameters for profile %s:' % profile_name, loglevel=log.loglevel_DEBUG)
            for p in self.sshproxy_params:
                self.logger('    %s: %s' % (p,self.sshproxy_params[p]), loglevel=log.loglevel_DEBUG)

        self.add_to_known_hosts = add_to_known_hosts
        self.known_hosts = known_hosts
        self.forward_sshagent = forward_sshagent

        self._current_status = {
            'timestamp': time.time(),
            'server': self.server,
            'virgin': self.virgin,
            'connected': self.connected,
            'running': self.running,
            'suspended': self.suspended,
            'terminated': self.terminated,
            'faulty': self.faulty,
        }

        self._SUPPORTED_SOUND = SUPPORTED_SOUND
        self._SUPPORTED_PRINTING = SUPPORTED_PRINTING
        self._SUPPORTED_MIMEBOX = SUPPORTED_MIMEBOX
        self._SUPPORTED_TELEKINESIS = SUPPORTED_TELEKINESIS
        self._SUPPORTED_FOLDERSHARING = SUPPORTED_FOLDERSHARING

        self.master_session = None
        self.init_control_session()
        self.terminal_session = None

        if self.is_connected():
            self.retrieve_server_features()

        self._progress_status = 0
        self._lock = threading.Lock()

        self._restore_exported_folders = {}
        if self.client_instance and self.restore_shared_local_folders:
            self._restore_exported_folders = self.client_instance.get_profile_config(self.profile_name, 'export')

    def __str__(self):
        return self.__get_uuid()

    def __repr__(self):
        result = 'X2GoSession('
        for p in dir(self):
            if '__' in p or not p in self.__dict__ or type(p) is types.InstanceType: continue
            result += p + '=' + str(self.__dict__[p]) + ','
        result = result.strip(',')
        return result + ')'

    def __call__(self):
        return self.__get_uuid()

    def __del__(self):
        """\
        Class destructor.

        """
        if self.has_control_session() and self.has_terminal_session():
            self.get_control_session().dissociate(self.get_terminal_session())

        if self.has_control_session():
            if self.keep_controlsession_alive:
                # regenerate this session instance for re-usage if this is the last session for a certain session profile
                # and keep_controlsession_alive is set to True...
                self.virgin = True
                self.activated = False
                self.connected = self.is_connected()
                self.running = None
                self.suspended = None
                self.terminated = None
                self._current_status = {
                    'timestamp': time.time(),
                    'server': self.server,
                    'virgin': self.virgin,
                    'connected': self.connected,
                    'running': self.running,
                    'suspended': self.suspended,
                    'terminated': self.terminated,
                    'faulty': self.faulty,
                }
                self._last_status = None
                self.session_name = None

            else:
                self.get_control_session().__del__()
                self.control_session = None

        if self.has_terminal_session():
            self.get_terminal_session().__del__()
            self.terminal_session = None

    def get_client_instance(self):
        """\
        Return parent L{X2GoClient} instance if avaiable.

        return: L{X2GoClient} instance this session is associated with
        rtype: C{obj}

        """
        return self.client_instance
    __get_client_instance = get_client_instance

    def HOOK_on_control_session_death(self):
        """\
        HOOK method: called if a control session (server connection) has unexpectedly encountered a failure.

        """
        if self.client_instance:
            self.client_instance.HOOK_on_control_session_death(profile_name=self.profile_name)
        else:
            self.logger('HOOK_on_control_session_death: the control session of profile %s has died unexpectedly' % self.profile_name, loglevel=log.loglevel_WARN)

    def HOOK_on_failing_SFTP_client(self):
        """\
        HOOK method: called SFTP client support is unavailable for the session.

        """
        if self.client_instance:
            self.client_instance.HOOK_on_failing_SFTP_client(profile_name=self.profile_name)
        else:
            self.logger('HOOK_on_failing_SFTP_client: new session for profile: %s will lack SFTP client support. Check your server setup. Avoid echoing ~/.bashrc files on server.' % self.profile_name, loglevel=log.loglevel_ERROR)

    def HOOK_auto_connect(self):
        """\
        HOOK method: called if the session demands to auto connect.

        """
        if self.client_instance:
            self.client_instance.HOOK_profile_auto_connect(profile_name=self.profile_name)
        else:
            self.logger('HOOK_auto_connect: profile ,,%s\'\' wants to auto-connect to the X2Go server.' % self.profile_name, loglevel=log.loglevel_WARN)

    def HOOK_session_startup_failed(self):
        """\
        HOOK method: called if the startup of a session failed.

        """
        if self.client_instance:
            self.client_instance.HOOK_session_startup_failed(profile_name=self.profile_name)
        else:
            self.logger('HOOK_session_startup_failed: session startup for session profile ,,%s\'\' failed.' % self.profile_name, loglevel=log.loglevel_WARN)

    def HOOK_desktop_sharing_denied(self):
        """\
        HOOK method: called if the startup of a shadow session was denied by the other user.

        """
        if self.client_instance:
            self.client_instance.HOOK_desktop_sharing_denied(profile_name=self.profile_name)
        else:
            self.logger('HOOK_desktop_sharing_denied: desktop sharing for session profile ,,%s\'\' was denied by the other user.' % self.profile_name, loglevel=log.loglevel_WARN)

    def HOOK_list_desktops_timeout(self):
        """\
        HOOK method: called if the x2golistdesktops command generates a timeout due to long execution time.

        """
        if self.client_instance:
            self.client_instance.HOOK_list_desktops_timeout(profile_name=self.profile_name)
        else:
            self.logger('HOOK_list_desktops_timeout: the server-side x2golistdesktops command for session profile %s took too long to return results. This can happen from time to time, please try again.' % self.profile_name, loglevel=log.loglevel_WARN)

    def HOOK_no_such_desktop(self, desktop='UNKNOWN'):
        """\
        HOOK method: called if it is tried to connect to a shared desktop that's not available (anymore).

        """
        if self.client_instance:
            self.client_instance.HOOK_no_such_desktop(profile_name=self.profile_name, desktop=desktop)
        else:
            self.logger('HOOK_no_such_desktop: the desktop %s (via session profile %s) is not available for sharing (anymore).' % (desktop, self.profile_name), loglevel=log.loglevel_WARN)

    def HOOK_rforward_request_denied(self, server_port=0):
        """\
        HOOK method: called if a reverse port forwarding request has been denied.

        @param server_port: remote server port (starting point of reverse forwarding tunnel)
        @type server_port: C{str}

        """
        if self.client_instance:
            self.client_instance.HOOK_rforward_request_denied(profile_name=self.profile_name, session_name=self.session_name, server_port=server_port)
        else:
            self.logger('HOOK_rforward_request_denied: TCP port (reverse) forwarding request for session %s to server port %s has been denied by server %s. This is a common issue with SSH, it might help to restart the server\'s SSH daemon.' % (self.session_name, server_port, self.profile_name), loglevel=log.loglevel_WARN)

    def HOOK_forwarding_tunnel_setup_failed(self, chain_host='UNKNOWN', chain_port=0, subsystem=None):
        """\
        HOOK method: called if a port forwarding tunnel setup failed.

        @param chain_host: hostname of chain host (forwarding tunnel end point)
        @type chain_host: C{str}
        @param chain_port: port of chain host (forwarding tunnel end point)
        @type chain_port: C{str}
        @param subsystem: information on the subsystem that provoked this hook call
        @type subsystem: C{str}

        """
        if type(subsystem) in (types.StringType, types.UnicodeType):
            _subsystem = '(%s) ' % subsystem
        else:
            _subsystem = ''

        if subsystem.endswith('Proxy'):
            self.faulty = True

        if self.client_instance:
            self.client_instance.HOOK_forwarding_tunnel_setup_failed(profile_name=self.profile_name, session_name=self.session_name, chain_host=chain_host, chain_port=chain_port, subsystem=subsystem)
        else:
            self.logger('HOOK_forwarding_tunnel_setup_failed: Forwarding tunnel request to [%s]:%s for session %s (%s) was denied by remote X2Go/SSH server. Subsystem (%s) startup failed.' % (chain_host, chain_port, self.session_name, self.profile_name, _subsystem), loglevel=log.loglevel_WARN)

    def HOOK_printing_not_available(self):
        """\
        HOOK method: called if X2Go client-side printing is not available.

        """
        if self.client_instance:
            self.client_instance.HOOK_printing_not_available(profile_name=self.profile_name, session_name=self.session_name)
        else:
            self.logger('HOOK_printing_not_available: X2Go\'s client-side printing feature is not available with this session (%s) of profile %s.' % (self.session_name, self.profile_name), loglevel=log.loglevel_WARN)

    def HOOK_mimebox_not_available(self):
        """\
        HOOK method: called if the X2Go MIME box is not available.

        """
        if self.client_instance:
            self.client_instance.HOOK_mimebox_not_available(profile_name=self.profile_name, session_name=self.session_name)
        else:
            self.logger('HOOK_mimebox_not_available: X2Go\'s MIME box feature is not available with this session (%s) of profile %s.' % (self.session_name, self.profile_name), loglevel=log.loglevel_WARN)

    def HOOK_foldersharing_not_available(self):
        """\
        HOOK method: called if X2Go client-side folder-sharing is not available.

        """
        if self.client_instance:
            self.client_instance.HOOK_foldersharing_not_available(profile_name=self.profile_name, session_name=self.session_name)
        else:
            self.logger('HOOK_foldersharing_not_available: X2Go\'s client-side folder sharing feature is not available with this session (%s) of profile %s.' % (self.session_name, self.profile_name), loglevel=log.loglevel_WARN)

    def HOOK_sshfs_not_available(self):
        """\
        HOOK method: called if the X2Go server denies SSHFS access.

        """
        if self.client_instance:
            self.client_instance.HOOK_sshfs_not_available(profile_name=self.profile_name, session_name=self.session_name)
        else:
            self.logger('HOOK_sshfs_not_available: the remote X2Go server (%s) denies SSHFS access for session %s. This will result in client-side folder sharing, printing and the MIME box feature being unavailable' % (self.profile_name, self.session_name), loglevel=log.loglevel_WARN)

    def HOOK_check_host_dialog(self, host, port, fingerprint='no fingerprint', fingerprint_type='UNKNOWN'):
        """\
        HOOK method: called if a host check is requested. This hook has to either return C{True} (default) or C{False}.

        @param host: SSH server name to validate
        @type host: C{str}
        @param port: SSH server port to validate
        @type port: C{int}
        @param fingerprint: the server's fingerprint
        @type fingerprint: C{str}
        @param fingerprint_type: finger print type (like RSA, DSA, ...)
        @type fingerprint_type: C{str}
        @return: if host validity is verified, this hook method should return C{True}
        @rtype: C{bool}

        """
        if self.client_instance:
            return self.client_instance.HOOK_check_host_dialog(profile_name=self.profile_name, host=host, port=port, fingerprint=fingerprint, fingerprint_type=fingerprint_type)
        else:
            self.logger('HOOK_check_host_dialog: host check requested for [%s]:%s with %s fingerprint: ,,%s\'\'. Automatically adding host as known host.' % (host, port, fingerprint_type, fingerprint), loglevel=log.loglevel_WARN)
            return True

    def init_control_session(self):
        """\
        Initialize a new control session (C{X2GoControlSession*}).

        """
        low_latency = self.terminal_params.has_key('link') and self.terminal_params['link'].lower() in ('modem', 'isdn')

        if self.control_session is None:
            self.logger('initializing X2GoControlSession', loglevel=log.loglevel_DEBUG)
            self.control_session = self.control_backend(profile_name=self.profile_name,
                                                        add_to_known_hosts=self.add_to_known_hosts,
                                                        known_hosts=self.known_hosts,
                                                        forward_sshagent=self.forward_sshagent,
                                                        terminal_backend=self.terminal_backend,
                                                        info_backend=self.info_backend,
                                                        list_backend=self.list_backend,
                                                        proxy_backend=self.proxy_backend,
                                                        client_rootdir=self.client_rootdir,
                                                        sessions_rootdir=self.sessions_rootdir,
                                                        ssh_rootdir=self.ssh_rootdir,
                                                        low_latency=low_latency,
                                                        logger=self.logger)
        else:
            self.control_session.low_latency = low_latency
    __init_control_session = init_control_session

    def is_master_session(self):
        """\
        Is this session a/the master session of sessions.

        The master session is the session has been launched first for a specific connection,
        it also is _the_ session that controls the client-side shared folders.

        If this L{X2GoSession} instance is a standalone instance (without parent L{X2GoClient})
        this method will always return C{True}.

        @return: returns C{True} if this session is a master session
        @rtype: C{bool}

        """
        if self.master_session is None and self.client_instance is None:
            return True
        return bool(self.master_session)
    __is_master_session = is_master_session

    def set_master_session(self, wait=0, max_wait=20):
        """\
        Declare this as a master session of a connection channel.

        This method gets called by the L{X2GoSessionRegistry} while sessions are starting or resuming and it relies on
        an already set-up terminal session.

        @param wait: wait for <wait> seconds before sharing local folders via the new master session
            of the corresponding session profile.
        @type wait: C{int}
        @param max_wait: wait for <max_wait> seconds for the terminal session to appear
        @type max_wait: C{int}

        """
        self.logger('Using session %s as master session for profile %s.' % (self.get_session_name(), self.get_profile_name()), loglevel=log.loglevel_NOTICE)
        self.master_session = True

        # retrieve an up-to-date list of sharable local folders from the client instance
        if self.client_instance:
            _exports = self.client_instance.get_profile_config(self.profile_name, 'export')
            self.share_local_folders = [ sf for sf in _exports.keys() if _exports[sf] ]

        i = 0
        while i < max_wait:
            i += 1
            if self.has_terminal_session():
                break
            gevent.sleep(1)

        if wait:
            gevent.spawn_later(wait, self.share_all_local_folders, update_exported_folders=False)
        else:
            gevent.spawn(self.share_all_local_folders, update_exported_folders=False)
    __set_master_session = set_master_session

    def unset_master_session(self):
        """\
        Declare this as a non-master session of a connection channel.

        """
        # unmount shared folders
        if self.has_terminal_session():
            self.unshare_all_local_folders(update_exported_folders=False)
        self.master_session = False
    __unset_master_session = unset_master_session

    def set_server(self, server):
        """\
        Modify server name after L{X2GoSession} has already been initialized.

        @param server: new server name
        @type server: C{str}

        """
        self.server = server
    __set_server = set_server

    def set_port(self, port):
        """\
        Modify server port after L{X2GoSession} has already been initialized.

        @param port: socket port of server to connect to
        @type port: C{int}

        """
        self.port = port
    __set_port = set_port

    def set_profile_name(self, profile_name):
        """\
        Modify session profile name after L{X2GoSession} has already been initialized.

        @param profile_name: new session profile name
        @type profile_name: C{str}

        """
        self.profile_name = profile_name
        self.control_session.set_profile_name(profile_name)
    __set_profile_name = set_profile_name

    def get_session_profile_option(self, option):
        """\
        Retrieve a specific profile parameter for this session.

        @param option: name of a specific profile option to be queried.
        @type option: C{str}

        @return: value for profile option C{<option>}
        @rtype: C{bool,str,int}

        @raise X2GoProfileException: if the session profile option is unknown

        """
        if option in _X2GO_SESSION_PARAMS + _X2GO_TERMINAL_PARAMS + _X2GO_SSHPROXY_PARAMS and hasattr(self, option):
            return eval("self.%s" % option)
        else:
            raise x2go_exceptions.X2GoProfileException('Unknown session profile option: %s.' % option)
    __get_session_profile_option = get_session_profile_option

    def update_params(self, params):
        """\
        This method can be used to modify L{X2GoSession} parameters after the
        L{X2GoSession} instance has already been initialized.

        @param params: a Python dictionary with L{X2GoSession} parameters
        @type params: C{dict}

        """
        try: del params['server'] 
        except KeyError: pass
        try: del params['profile_name']
        except KeyError: pass
        try: del params['profile_id'] 
        except KeyError: pass
        try:
            self.printing = params['printing']
            del params['printing'] 
        except KeyError: pass
        try:
            self.allow_share_local_folders = params['allow_share_local_folders']
            del params['allow_share_local_folders']
        except KeyError: pass
        try:
            self.share_local_folders = params['share_local_folders']
            del params['share_local_folders'] 
        except KeyError: pass
        try:
            self.restore_shared_local_folders = params['restore_shared_local_folders']
            del params['restore_shared_local_folders']
        except KeyError: pass
        try:
            self.allow_mimebox = params['allow_mimebox']
            del params['allow_mimebox']
        except KeyError: pass
        try:
            self.mimebox_extensions = params['mimebox_extensions']
            del params['mimebox_extensions']
        except KeyError: pass
        try: 
            self.mimebox_action = params['mimebox_action']
            del params['mimebox_action']
        except KeyError: pass
        try:
            self.use_sshproxy = params['use_sshproxy']
            del params['use_sshproxy']
        except KeyError: pass
        try:
            self.sshproxy_reuse_authinfo = params['sshproxy_reuse_authinfo']
            del params['sshproxy_reuse_authinfo']
        except KeyError: pass
        try:
            self.auto_connect = params['auto_connect']
            del params['auto_connect']
        except KeyError: pass
        try:
            self.forward_sshagent = params['forward_sshagent']
            del params['forward_sshagent']
        except KeyError: pass
        try:
            self.auto_start_or_resume = params['auto_start_or_resume']
            del params['auto_start_or_resume']
        except KeyError: pass

        if self.sshproxy_reuse_authinfo:
            if params.has_key('key_filename'):
                params['sshproxy_key_filename'] = params['key_filename']
            if params.has_key('pkey'):
                params['sshproxy_pkey'] = params['pkey']
            if params.has_key('password'):
                params['sshproxy_password'] = params['password']

        _terminal_params = copy.deepcopy(params)
        _control_params = copy.deepcopy(params)
        _sshproxy_params = copy.deepcopy(params)
        for p in params.keys():
            if p in session._X2GO_TERMINAL_PARAMS:
                del _control_params[p]
                del _sshproxy_params[p]
            elif p in session._X2GO_SSHPROXY_PARAMS:
                del _control_params[p]
                del _terminal_params[p]
            else:
                del _sshproxy_params[p]
                del _terminal_params[p]

        self.control_params.update(_control_params)
        self.terminal_params.update(_terminal_params)
        self.sshproxy_params.update(_sshproxy_params)

    def get_uuid(self):
        """\
        Retrieve session UUID hash for this L{X2GoSession}.

        @return: the session's UUID hash
        @rtype: C{str}

        """
        return str(self.uuid)
    __get_uuid = get_uuid

    def get_username(self):
        """\
        After a session has been set up you can query the
        username the session runs as.

        @return: the remote username the X2Go session runs as
        @rtype: C{str}

        """
        # try to retrieve the username from the control session, if already connected
        try:
            return self.control_session.get_transport().get_username()
        except AttributeError:
            return self.control_params['username']
    __get_username = get_username

    def get_remote_home(self):
        """\
        After a session has been set up you can query the
        remote user's home directory path.

        @return: the remote home directory path
        @rtype: C{str}

        """
        # try to retrieve the username from the control session, if already connected
        if self.is_connected():
            return self.control_session._x2go_remote_home
        else:
            return None
    __get_remote_home = get_remote_home

    def user_is_x2gouser(self, username=None):
        """\
        Check if a given user is valid server-side X2Go user.

        @param username: username to check validity for
        @type username: C{str}

        @return: C{True} if the username is allowed to launch X2Go sessions
        @rtype: C{bool}

        """
        if username is None:
            username = self.__get_username()
        return self.control_session.is_x2gouser(username)
    __user_is_x2gouser = user_is_x2gouser

    def get_password(self):
        """\
        After a session has been setup up you can query the
        username's password from the session.

        @return: the username's password
        @rtype: C{str}

        """
        return base64.base64decode(self.control_session._session_password)
    __get_password = get_password

    def get_server_peername(self):
        """\
        After a session has been setup up you can query the
        peername of the host this session is connected to (or
        about to connect to).

        @return: the address of the server the X2Go session is
            connected to (as an C{(addr,port)} tuple)
        @rtype: C{tuple}

        """
        return self.control_session.remote_peername()
    __get_server_peername = get_server_peername
    remote_peername = get_server_peername
    __remote_peername = get_server_peername

    def get_server_hostname(self):
        """\
        After a session has been setup up you can query the
        hostname of the host this session is connected to (or
        about to connect to).

        @return: the hostname of the server the X2Go session is
            connected to / about to connect to
        @rtype: C{str}

        """
        self.server = self.control_session.get_hostname()
        return self.server
    __get_server_hostname = get_server_hostname

    def get_server_port(self):
        """\
        After a session has been setup up you can query the
        IP socket port used for connecting the remote X2Go server.

        @return: the server-side IP socket port that is used by the X2Go session to
            connect to the server
        @rtype: C{str}

        """
        return self.control_session.get_port()
    __get_server_port = get_server_port

    def get_session_name(self):
        """\
        Retrieve the server-side X2Go session name for this session.

        @return: X2Go session name
        @rtype: C{str}

        """
        return self.session_name
    __get_session_name = get_session_name

    def set_session_name(self, session_name):
        """\
        Manipulate the L{X2GoSession}'s session name.

        @param session_name: the new session name to be set
        @type session_name: C{str}

        """
        self.session_name = session_name
    __set_session_name = set_session_name

    def get_session_info(self):
        """\
        Retrieve the server-side X2Go session info object for this session.

        @return: X2Go session info
        @rtype: C{obj}

        """
        if self.has_terminal_session():
            self.terminal_session.get_session_info()
    __get_session_info = get_session_info

    def get_session_cmd(self):
        """\
        Retrieve the server-side command that is used to start a session
        on the remote X2Go server.

        @return: server-side session command
        @rtype: C{str}

        """
        if self.has_terminal_session():
            return self.terminal_session.get_session_cmd()
        if self.terminal_params.has_key('cmd'):
            return self.terminal_params['cmd']
        return None
    __get_session_cmd = get_session_cmd

    def get_session_type(self):
        """\
        Retrieve the session type of a session (R, D, S or P).

          - R: rootless session
          - D: desktop session
          - S: shadow session
          - P: session in published applications mode

        @return: session type
        @rtype: C{str}

        """
        if self.has_terminal_session():
            return self.terminal_session.get_session_type()
        else:
            return None
    __get_session_type = get_session_type

    def get_session_title(self):
        """\
        Retrieve the session window title of this
        session.

        @return: session window title
        @rtype: C{str}

        """
        if self.has_terminal_session():
            return self.terminal_session.session_title
        else:
            return 'X2GO-%s' % self.get_session_name()
    __get_session_title = get_session_title

    def get_control_session(self):
        """\
        Retrieve the control session (C{X2GoControlSession*} backend) of this L{X2GoSession}.

        @return: the L{X2GoSession}'s control session
        @rtype: C{X2GoControlSession*} instance

        """
        return self.control_session
    __get_control_session = get_control_session

    def has_control_session(self):
        """\
        Check if this L{X2GoSession} instance has an associated control session.

        @return: returns C{True} if this L{X2GoSession} has a control session associated to itself
        @rtype: C{bool}

        """
        return self.control_session is not None
    __has_control_session = has_control_session

    def get_terminal_session(self):
        """\
        Retrieve the terminal session (C{X2GoTerminalSession*} backend) of this L{X2GoSession}.

        @return: the L{X2GoSession}'s terminal session
        @rtype: C{X2GoControlTerminal*} instance

        """
        if self.terminal_session == 'PENDING':
            return None
        return self.terminal_session
    __get_terminal_session = get_terminal_session

    def has_terminal_session(self):
        """\
        Check if this L{X2GoSession} instance has an associated terminal session.

        @return: returns C{True} if this L{X2GoSession} has a terminal session associated to itself
        @rtype: C{bool}

        """
        return self.terminal_session not in (None, 'PENDING')
    __has_terminal_session = has_terminal_session
    is_associated = has_terminal_session
    __is_associated = has_terminal_session

    def check_host(self):
        """\
        Provide a host check mechanism. This method basically calls the L{HOOK_check_host_dialog()} method
        which by itself calls the L{X2GoClient.HOOK_check_host_dialog()} method. Make sure you
        override any of these to enable user interaction on X2Go server validity checks.

        @return: returns C{True} if an X2Go server host is valid for authentication
        @rtype: C{bool}

        """
        if self.connected:
            return True

        _port = self.control_params['port']
        (_valid, _host, _port, _fingerprint, _fingerprint_type) = self.control_session.check_host(self.server, port=_port)
        return _valid or self.HOOK_check_host_dialog(host=_host, port=_port, fingerprint=_fingerprint, fingerprint_type=_fingerprint_type)
    __check_host = check_host

    def uses_sshproxy(self):
        """\
        Check if a session is configured to use an intermediate SSH proxy server.

        @return: returns C{True} if the session is configured to use an SSH proxy, C{False} otherwise.
        @rtype: C{bool}

        """
        return self.use_sshproxy
    __uses_sshproxy = uses_sshproxy

    def reuses_sshproxy_authinfo(self):
        """\
        Check if a session is configured to re-use the X2Go session's password / key for
        proxy authentication, as well.

        @return: returns C{True} if the session is configured to re-use session password / key for proxy authentication
        @rtype: C{bool}

        """
        return self.sshproxy_reuse_authinfo
    __reuses_sshproxy_authinfo = reuses_sshproxy_authinfo

    def can_sshproxy_auto_connect(self):
        """\
        Check if a session's SSH proxy (if used) is configured adequately to be able to auto-connect
        to the SSH proxy server (e.g. by public key authentication).

        @return: returns C{True} if the session's SSH proxy can auto-connect, C{False} otherwise, C{None}
            if no SSH proxy is used for this session, C{None} is returned.
        @rtype: C{bool}

        """
        if self.use_sshproxy:
            if self.sshproxy_params.has_key('sshproxy_key_filename') and self.sshproxy_params['sshproxy_key_filename'] and os.path.exists(os.path.normpath(self.sshproxy_params['sshproxy_key_filename'])):
                return True
            elif self.sshproxy_reuse_authinfo and self.control_params.has_key('key_filename') and self.control_params['key_filename'] and os.path.exists(os.path.normpath(self.control_params['key_filename'])):
                return True
            elif self.sshproxy_params.has_key('sshproxy_pkey') and self.sshproxy_params['sshproxy_pkey']:
                return True
            elif self.sshproxy_reuse_authinfo and self.control_params.has_key('pkey') and self.control_params['pkey']:
                return True
            elif self.sshproxy_params.has_key('sshproxy_look_for_keys') and self.sshproxy_params['sshproxy_look_for_keys'] and (os.path.exists(os.path.expanduser('~/.ssh/id_rsa')) or os.path.exists(os.path.expanduser('~/.ssh/id_dsa'))):
                return True
            elif self.sshproxy_params.has_key('sshproxy_allow_agent') and self.sshproxy_params['sshproxy_allow_agent'] and paramiko.Agent().get_keys():
                return True
            else:
                return False
        else:
            return None
    __can_sshproxy_auto_connect = can_sshproxy_auto_connect

    def can_auto_connect(self):
        """\
        Check if a session is configured adequately to be able to auto-connect to the X2Go
        server (e.g. public key authentication).

        @return: returns C{True} if the session can auto-connect, C{False} otherwise, C{None}
            if no control session has been set up yet.
        @rtype: C{bool}

        """
        if self.control_session is None:
            return None

        _can_sshproxy_auto_connect = self.can_sshproxy_auto_connect()

        # do we have a key file passed as control parameter?
        if self.control_params.has_key('key_filename') and self.control_params['key_filename'] and os.path.exists(os.path.normpath(self.control_params['key_filename'])):
            return (_can_sshproxy_auto_connect is None) or _can_sshproxy_auto_connect

        # or a private key?
        elif self.control_params.has_key('pkey') and self.control_params['pkey']:
            return (_can_sshproxy_auto_connect is None) or _can_sshproxy_auto_connect

        # or a key auto discovery?
        elif self.control_params.has_key('look_for_keys') and self.control_params['look_for_keys'] and (os.path.exists(os.path.expanduser('~/.ssh/id_rsa')) or os.path.exists(os.path.expanduser('~/.ssh/id_dsa'))):
            return (_can_sshproxy_auto_connect is None) or _can_sshproxy_auto_connect

        # or an SSH agent usage?
        elif self.control_params.has_key('allow_agent') and self.control_params['allow_agent'] and paramiko.Agent().get_keys():
            return (_can_sshproxy_auto_connect is None) or _can_sshproxy_auto_connect

        else:
            return False
    __can_auto_connect = can_auto_connect

    def do_auto_connect(self, redirect_to_client=True):
        """\
        Automatically connect this session.

        @return: Return success (or failure) of connecting this sessions
        @rtype: C{bool}

        """
        if not self.is_connected():
            if self.client_instance and redirect_to_client:
                return self.client_instance.session_auto_connect(self())
            else:
                if self.can_auto_connect() and self.auto_connect:
                    gevent.spawn(self.connect)
                elif self.auto_connect:
                    gevent.spawn(self.HOOK_auto_connect)
    __do_auto_connect = do_auto_connect

    def connect(self, username=None, password=None, passphrase=None, add_to_known_hosts=None,
                force_password_auth=None, look_for_keys=None, allow_agent=None,
                use_sshproxy=None, sshproxy_user=None, sshproxy_password=None, sshproxy_passphrase=None,
                sshproxy_force_password_auth=None, sshproxy_reuse_authinfo=None, apprime_server=None, apprime_port=None):
        """\
        Connects to the L{X2GoSession}'s server host. This method basically wraps around 
        the C{X2GoControlSession*.connect()} method.

        @param username: the username for the X2Go server that is going to be
            connected to (as a last minute way of changing the session username)
        @type username: C{str}
        @param password: the user's password for the X2Go server that is going to be
            connected to
        @type password: C{str}
        @param passphrase: a passphrase to use for unlocking
            a private key in case the password is already needed for two-factor
            authentication
        @type passphrase: C{str}
        @param add_to_known_hosts: non-paramiko option, if C{True} paramiko.AutoAddPolicy()
            is used as missing-host-key-policy. If set to C{False} paramiko.RejectPolicy()
            is used
        @type add_to_known_hosts: C{bool}
        @param force_password_auth: disable SSH pub/priv key authentication mechanisms
            completely
        @type force_password_auth: C{bool}
        @param look_for_keys: set to C{True} to enable searching for discoverable
            private key files in C{~/.ssh/}
        @type look_for_keys: C{bool}
        @param allow_agent: set to C{True} to enable connecting to a local SSH agent
            for acquiring authentication information
        @type allow_agent: C{bool}
        @param use_sshproxy: use an SSH proxy host for connecting the target X2Go server
        @type use_sshproxy: C{bool}
        @param sshproxy_reuse_authinfo: for proxy authentication re-use the X2Go session's password / key file
        @type sshproxy_reuse_authinfo: C{bool}
        @param sshproxy_user: username for authentication against the SSH proxy host
        @type sshproxy_user: C{str}
        @param sshproxy_password: password for authentication against the SSH proxy host
        @type sshproxy_password: C{str}
        @param sshproxy_passphrase: a passphrase to use for unlocking
            a private key needed for the SSH proxy host in case the sshproxy_password is already needed for
            two-factor authentication
        @type sshproxy_passphrase: C{str}
        @param sshproxy_force_password_auth: enforce password authentication even is a key(file) is present
        @type sshproxy_force_password_auth: C{bool}

        @return: returns C{True} is the connection to the X2Go server has been successful
        @rtype C{bool}

        @raise X2GoSessionException: on control session exceptions
        @raise X2GoRemoteHomeException: if the remote home directory does not exist
        @raise Exception: any other exception during connecting is passed through

        """
        if self.control_session and self.control_session.is_connected():
            self.logger('control session is already connected, skipping authentication', loglevel=log.loglevel_DEBUG)
            self.connected = True
        else:
            #Apprime code begin
            if apprime_server is not None:
                self.server = apprime_server
            if apprime_port is not None:
                self.port = apprime_port
            #Apprime code end
            
            if use_sshproxy is not None:
                self.use_sshproxy = use_sshproxy

            if sshproxy_reuse_authinfo is not None:
                self.sshproxy_reuse_authinfo = sshproxy_reuse_authinfo

            if username:
                self.control_params['username'] = username
            if add_to_known_hosts is not None:
                self.control_params['add_to_known_hosts'] = add_to_known_hosts
            if force_password_auth is not None:
                self.control_params['force_password_auth'] = force_password_auth
            if look_for_keys is not None:
                self.control_params['look_for_keys'] = look_for_keys
            if allow_agent is not None:
                self.control_params['allow_agent'] = allow_agent

            if sshproxy_user:
                self.sshproxy_params['sshproxy_user'] = sshproxy_user
            if sshproxy_password:
                self.sshproxy_params['sshproxy_password'] = sshproxy_password
            if sshproxy_passphrase:
                self.sshproxy_params['sshproxy_passphrase'] = sshproxy_passphrase
            if sshproxy_force_password_auth is not None:
                self.sshproxy_params['sshproxy_force_password_auth'] = sshproxy_force_password_auth

            self.control_params['password'] = password
            if passphrase:
                self.control_params['passphrase'] = passphrase

            if self.sshproxy_reuse_authinfo:
                if self.control_params.has_key('key_filename'):
                    self.sshproxy_params['sshproxy_key_filename'] = self.control_params['key_filename']
                if self.control_params.has_key('pkey'):
                    self.sshproxy_params['sshproxy_pkey'] = self.control_params['pkey']
                if self.control_params.has_key('password'):
                    self.sshproxy_params['sshproxy_password'] = self.control_params['password']
                if self.control_params.has_key('passphrase'):
                    self.sshproxy_params['sshproxy_passphrase'] = self.control_params['passphrase']

            _params = {}
            _params.update(self.control_params)
            _params.update(self.sshproxy_params)

            #if 'port' not in _params:
            #    _params['port'] = self.port
            _params['port'] = self.port

            try:
                self.logger('VG connecting to server %s' % self.server, loglevel=log.loglevel_INFO)
                self.connected = self.control_session.connect(self.server,
                                                              use_sshproxy=self.use_sshproxy,
                                                              session_instance=self,
                                                              forward_sshagent=self.forward_sshagent,
                                                              **_params)
            except x2go_exceptions.X2GoControlSessionException, e:
                raise x2go_exceptions.X2GoSessionException(str(e))
            except x2go_exceptions.X2GoRemoteHomeException, e:
                self.disconnect()
                raise e
            except:
                # remove credentials immediately
                self.control_params['password'] = ''
                if self.control_params and self.control_params.has_key('passphrase'):
                    del self.control_params['passphrase']
                if self.sshproxy_params and self.sshproxy_params.has_key('sshproxy_password'):
                    self.sshproxy_params['sshproxy_password'] = ''
                if self.sshproxy_params and self.sshproxy_params.has_key('sshproxy_passphrase'):
                    del self.sshproxy_params['sshproxy_passphrase']
                raise
            finally:
                # remove credentials immediately
                self.control_params['password'] = ''
                if self.control_params and self.control_params.has_key('passphrase'):
                    del self.control_params['passphrase']
                if self.sshproxy_params and self.sshproxy_params.has_key('sshproxy_password'):
                    self.sshproxy_params['sshproxy_password'] = ''
                if self.sshproxy_params and self.sshproxy_params.has_key('sshproxy_passphrase'):
                    del self.sshproxy_params['sshproxy_passphrase']

            if not self.connected:
                # then tidy up...
                self.disconnect()

            self.get_server_hostname()

        if self.connected:
            self.update_status()
            self.retrieve_server_features()
            if self.auto_start_or_resume:
                gevent.spawn(self.do_auto_start_or_resume)

        return self.connected
    __connect = connect

    def disconnect(self):
        """\
        Disconnect this L{X2GoSession} instance.

        @return: returns C{True} if the disconnect operation has been successful
        @rtype: C{bool}

        """
        self.connected = False
        self.running = None
        self.suspended = None
        self.terminated = None
        self.faults = None
        self.active = False
        self._lock.release()
        self.unset_master_session()
        try:
            self.update_status(force_update=True)
        except x2go_exceptions.X2GoControlSessionException:
            pass
        retval = self.control_session.disconnect()
        return retval
    __disconnect = disconnect

    def retrieve_server_features(self):
        """\
        Query the X2Go server for a list of supported features.

        """
        self.server_features = self.control_session.query_server_features()
        self._SUPPORTED_TELEKINESIS = SUPPORTED_TELEKINESIS and self.has_server_feature('X2GO_TELEKINESIS')
    __retrieve_server_features = retrieve_server_features

    def get_server_features(self):
        """\
        Return a list of X2Go server-sides features (supported functionalities).

        @return: a C{list} of X2Go feature names
        @rtype: C{list}

        """
        return self.server_features
    __get_server_features = get_server_features

    def has_server_feature(self, feature):
        """\
        Check if C{feature} is a present feature of the connected X2Go server.

        @param feature: an X2Go server feature as found in C{$SHAREDIR/x2go/feature.d/*}
        @type feature: C{str}

        @return: returns C{True} if the feature is present
        @rtype: C{bool}

        """
        return feature in self.get_server_features()
    __has_server_feature = has_server_feature

    def set_session_window_title(self, title=''):
        """\
        Modify session window title. If the session ID does not occur in the
        given title, it will be prepended, so that every X2Go session window
        always contains the X2Go session ID of that window.

        @param title: new title for session window
        @type title: C{str}

        """
        if self.terminal_session is not None:
            self.terminal_session.set_session_window_title(title=title)
    __set_session_window_title = set_session_window_title

    def raise_session_window(self):
        """\
        Try to lift the session window above all other windows and bring
        it to focus.

        """
        if self.terminal_session is not None:
            self.terminal_session.raise_session_window()
    __raise_session_window = raise_session_window

    def set_print_action(self, print_action, **kwargs):
        """\
        If X2Go client-side printing is enable within this X2Go session you can use
        this method to alter the way how incoming print spool jobs are handled/processed.

        For further information, please refer to the documentation of the L{X2GoClient.set_session_print_action()}
        method.

        @param print_action: one of the named above print actions, either as string or class instance
        @type print_action: C{str} or C{instance}
        @param kwargs: additional information for the given print action (print 
            action arguments), for possible print action arguments and their values see each individual
            print action class
        @type kwargs: C{dict}

        """
        if type(print_action) is not types.StringType:
            return False
        self.terminal_session.set_print_action(print_action, **kwargs)
    __set_print_action = set_print_action

    def is_alive(self):
        """\
        Find out if this X2Go session is still alive (that is: connected to the server).

        @return: returns C{True} if the server connection is still alive
        @rtype: C{bool}

        """
        self.connected = self.control_session.is_alive()
        if self.control_session.has_session_died():
            self.HOOK_on_control_session_death()
        if not self.connected:
            self._X2GoSession__disconnect()
        return self.connected
    __is_alive = is_alive

    def clean_sessions(self, destroy_terminals=True, published_applications=False):
        """\
        Clean all running sessions for the authenticated user on the remote X2Go server.

        @param destroy_terminals: destroy associated terminal sessions
        @type destroy_terminals: C{bool}
        @param published_applications: clean sessions that are published applications providers, too
        @type published_applications: C{bool}

        """
        if self.is_alive():

            # unmount shared folders
            if self.has_terminal_session():
                self.unshare_all_local_folders(force_all=True)

            self.control_session.clean_sessions(destroy_terminals=destroy_terminals, published_applications=published_applications)
        else:
            self._X2GoSession__disconnect()
    __clean_sessions = clean_sessions

    def list_sessions(self, raw=False):
        """\
        List all sessions on the remote X2Go server that are owned by the authenticated user 

        @param raw: if C{True} the output of this method equals
            the output of the server-side C{x2golistsessions} command
        @type raw: C{bool}

        @return: a session list (as data object or list of strings when called with C{raw=True} option)
        @rtype: C{X2GoServerSessionList*} instance or C{list}

        """
        try:
            return self.control_session.list_sessions(raw=raw)
        except x2go_exceptions.X2GoControlSessionException:
            if self.connected: self.HOOK_on_control_session_death()
            self._X2GoSession__disconnect()
            return None
    __list_sessions = list_sessions

    def list_desktops(self, raw=False):
        """\
        List X2Go desktops sessions available for desktop sharing on the remote X2Go server.

        @param raw: if C{True} the output of this method equals
            the output of the server-side C{x2golistdesktops} command
        @type raw: C{bool}

        @return: a list of strings representing available desktop sessions
        @rtype: C{list}

        """
        try:
            return self.control_session.list_desktops(raw=raw)
        except x2go_exceptions.X2GoTimeoutException:
            if self.is_alive(): self.HOOK_list_desktop_timeout()
            return []
        except x2go_exceptions.X2GoControlSessionException:
            if self.connected: self.HOOK_on_control_session_death()
            self._X2GoSession__disconnect()
            return None
    __list_desktops = list_desktops

    def list_mounts(self, raw=False):
        """\
        Use the X2Go session registered under C{session_uuid} to
        retrieve its list of mounted client shares for that session.

        @param raw: output the list of mounted client shares in X2Go's
            raw C{x2golistmounts} format
        @type raw: C{bool}

        @return: a list of strings representing mounted client shares for this session
        @rtype: C{list}

        """
        try:
            return self.control_session.list_mounts(self.session_name, raw=raw)
        except x2go_exceptions.X2GoControlSessionException:
            if self.connected: self.HOOK_on_control_session_death()
            self._X2GoSession__disconnect()
            return None
    __list_mounts = list_mounts

    def update_status(self, session_list=None, force_update=False):
        """\
        Update the current session status. The L{X2GoSession} instance uses an internal
        session status cache that allows to query the session status without the need
        of retrieving data from the remote X2Go server for each query.

        The session status (if initialized properly with the L{X2GoClient} constructor gets
        updated in regularly intervals.

        In case you use the L{X2GoSession} class in standalone instances (that is: without
        being embedded into an L{X2GoSession} context) then run this method in regular
        intervals to make sure the L{X2GoSession}'s internal status cache information
        is always up-to-date.

        @param session_list: provide an C{X2GoServerSessionList*} that refers to X2Go sessions we want to update.
            This option is mainly for reducing server/client traffic.
        @type session_list: C{X2GoServerSessionList*} instance
        @param force_update: force a session status update, if if the last update is less then 1 second ago
        @type force_update: C{bool}

        @raise Exception: any exception is passed through in case the session disconnected surprisingly
            or has been marked as faulty

        """
        if not force_update and self._last_status is not None:
            _status_update_timedelta = time.time() - self._last_status['timestamp']

            # skip this session status update if not longer than a second ago...
            if  _status_update_timedelta < 1:
                self.logger('status update interval too short (%s), skipping status update this time...' % _status_update_timedelta, loglevel=log.loglevel_DEBUG)
                return False

        e = None
        self._last_status = copy.deepcopy(self._current_status)
        if session_list is None:
            try:
                session_list = self.control_session.list_sessions()
                self.connected = True
            except x2go_exceptions.X2GoControlSessionException, e:
                self.connected = False
                self.running = None
                self.suspended = None
                self.terminated = None
                self.faulty = None

        if self.connected:
            try:
                _session_name = self.get_session_name()
                _session_info = session_list[_session_name]
                self.running = _session_info.is_running()
                self.suspended = _session_info.is_suspended()
                if not self.virgin:
                    self.terminated = not (self.running or self.suspended)
                else:
                    self.terminated = None
            except KeyError, e:
                self.running = False
                self.suspended = False
                if not self.virgin:
                    self.terminated = True
            self.faulty = not (self.running or self.suspended or self.terminated or self.virgin)

        self._current_status = {
            'timestamp': time.time(),
            'server': self.server,
            'virgin': self.virgin,
            'connected': self.connected,
            'running': self.running,
            'suspended': self.suspended,
            'terminated': self.terminated,
            'faulty': self.faulty,
        }

        if (not self.connected or self.faulty) and e:
            raise e

        return True
    __update_status = update_status

    def is_published_applications_provider(self):
        """\
        Returns true if this session runs in published applications mode.

        @return: returns C{True} if this session is a provider session for published applications.
        @rtype: C{bool}

        """
        if self.has_terminal_session() and self.is_running() :
            return self.terminal_session.is_published_applications_provider()
        return False
    __is_published_applications_provider = is_published_applications_provider

    def get_published_applications(self, lang=None, refresh=False, raw=False, very_raw=False, max_no_submenus=defaults.PUBAPP_MAX_NO_SUBMENUS):
        """\
        Return a list of published menu items from the X2Go server
        for session type published applications.

        @param lang: locale/language identifier
        @type lang: C{str}
        @param refresh: force reload of the menu tree from X2Go server
        @type refresh: C{bool}
        @param raw: retrieve a raw output of the server list of published applications
        @type raw: C{bool}
        @param very_raw: retrieve a very raw output of the server list of published applications (as-is output of x2gogetapps script)
        @type very_raw: C{bool}

        @return: A C{list} of C{dict} elements. Each C{dict} elements has a 
            C{desktop} key containing the text output of a .desktop file and
            an C{icon} key which contains the desktop icon data base64 encoded 
        @rtype: C{list}

        """
        if self.client_instance and hasattr(self.client_instance, 'lang'):
            lang = self.client_instance.lang
        return self.control_session.get_published_applications(lang=lang, refresh=refresh, raw=raw, very_raw=very_raw, max_no_submenus=max_no_submenus)
    __get_published_applications = get_published_applications

    def exec_published_application(self, exec_name, timeout=20):
        """\
        Execute an application while in published application mode.

        @param exec_name: command to execute on server
        @type exec_name: C{str}

        """
        if self.terminal_session is not None:
            self.logger('for %s executing published application: %s' % (self.profile_name, exec_name), loglevel=log.loglevel_NOTICE)
            self.terminal_session.exec_published_application(exec_name, timeout=timeout, env=self.session_environment)
    __exec_published_application = exec_published_application

    def do_auto_start_or_resume(self, newest=True, oldest=False, all_suspended=False, start=True, redirect_to_client=True):
        """\
        Automatically start or resume this session, if already associated with a server session. Otherwise
        resume a server-side available/suspended session (see options to declare which session to resume).
        If no session is available for resuming a new session will be launched.

        Sessions in published applications mode are not resumed/started by this method.

        @param newest: if resuming, only resume newest/youngest session
        @type newest: C{bool}
        @param oldest: if resuming, only resume oldest session
        @type oldest: C{bool}
        @param all_suspended: if resuming, resume all suspended sessions
        @type all_suspended: C{bool}
        @param start: is no session is to be resumed, start a new session
        @type start: C{bool}
        @param redirect_to_client: redirect this call to the L{X2GoClient} instance (if available) to allow frontend interaction
        @type redirect_to_client: C{bool}

        @return: returns success (or failure) of starting/resuming this sessions
        @rtype: C{bool}

        """
        if self.client_instance and redirect_to_client:
            return self.client_instance.session_auto_start_or_resume(self())
        else:
            if self.session_name is not None and 'PUBLISHED' not in self.session_name:
                return self.resume()
            else:
                session_infos = self.list_sessions()

                # only auto start/resume non-pubapp sessions
                for session_name in session_infos.keys():
                    if session_infos[session_name].is_published_applications_provider():
                        del session_infos[session_name]

                if session_infos:
                    sorted_session_names = utils.session_names_by_timestamp(session_infos)
                    if newest:
                        if sorted_session_names[0].find('RDP') == -1:
                            return self.resume(session_name=sorted_session_names[-1])
                    elif oldest:
                        if sorted_session_names[-1].find('RDP') == -1:
                            return self.resume(session_name=sorted_session_names[0])
                    elif all_suspended:
                        for session_name in [ _sn for _sn in session_infos.keys() if session_infos[_sn].is_suspended() ]:
                            return self.resume(session_name=session_name)
                else:
                    if not self.published_applications:
                        return self.start()
    __do_auto_start_or_resume = do_auto_start_or_resume

    def reset_progress_status(self):
        """\
        Reset session startup/resumption progress status.

        """
        self._progress_status = 0

    def get_progress_status(self):
        """\
        Retrieve session startup/resumption progress status.

        @return: returns an C{int} value between 0 and 100 reflecting the session startup/resumption status
        @rtype: C{int}

        """
        return self._progress_status

    def resume(self, session_name=None, session_list=None, cmd=None, progress_event=None):
        """\
        Resume or continue a suspended / running X2Go session on the
        remote X2Go server.

        @param session_name: the server-side name of an X2Go session
        @type session_name: C{str}
        @param session_list: a session list to avoid a server-side session list query
        @type session_list: C{dict}
        @param cmd: if starting a new session, manually hand over the command to be launched in
            the new session
        @type cmd: C{str}
        @param progress_event: a C{thread.Event} object that notifies a status object like the one in
            L{utils.ProgressStatus}.
        @type progress_event: C{obj}

        @return: returns C{True} if resuming the session has been successful, C{False} otherwise
        @rtype: C{bool}

        @raise Exception: any exception that occurs during published application menu retrieval is passed through

        """
        self._lock.acquire()
        try:
            _retval = self._resume(session_name=session_name, session_list=session_list, cmd=cmd, progress_event=progress_event)
        except:
            self._lock.release()
            raise
        finally:
            self._lock.release()
        return _retval

    def _resume(self, session_name=None, session_list=None, cmd=None, progress_event=None):
        """\
        Resume or continue a suspended / running X2Go session on the
        remote X2Go server.

        @param session_name: the server-side name of an X2Go session
        @type session_name: C{str}
        @param session_list: a session list to avoid a server-side session list query
        @type session_list: C{dict}
        @param cmd: if starting a new session, manually hand over the command to be launched in
            the new session
        @type cmd: C{str}
        @param progress_event: a C{thread.Event} object that notifies a status object like the one in
            L{utils.ProgressStatus}.
        @type progress_event: C{obj}

        @return: returns C{True} if resuming the session has been successful, C{False} otherwise
        @rtype: C{bool}

        @raise Exception: any exception that occurs during published application menu retrieval is passed through

        """
        if self.terminal_session is None:
            self.terminal_session = 'PENDING'

        # initialize a dummy event to avoid many if clauses further down in the code
        self.reset_progress_status()
        _dummy_event = threading.Event()
        if type(progress_event) != type(_dummy_event):
            progress_event = _dummy_event

        self._progress_status = 1
        progress_event.set()

        _new_session = False
        if self.session_name is None:
            self.session_name = session_name

        self._progress_status = 2
        progress_event.set()

        if self.is_alive():

            self._progress_status = 5
            progress_event.set()

            _control = self.control_session

            self._progress_status = 7
            progress_event.set()

            # FIXME: normally this part gets called if you suspend a session that is associated to another client
            # we do not have a possibility to really check if SSH has released port forwarding channels or
            # sockets, thus  we plainly have to wait a while

            try:
                _control.test_sftpclient()
            except x2go_exceptions.X2GoSFTPClientException:
                self.HOOK_on_failing_SFTP_client()
                self.terminal_session = None
                self._progress_status = -1
                progress_event.set()
                return False

            if self.is_running():
                try:

                    self._suspend()
                    self.terminal_session = 'PENDING'

                    self._progress_status = 10
                    progress_event.set()

                    self._lock.release()
                    gevent.sleep(5)
                    self._lock.acquire()

                    self._progress_status = 15
                    progress_event.set()

                except x2go_exceptions.X2GoSessionException:
                    pass


            self._progress_status = 20
            progress_event.set()

            try:
                if self.published_applications:
                    self.published_applications_menu = gevent.spawn(self.get_published_applications)
            except:
                # FIXME: test the code to see what exceptions may occur here...

                self._progress_status = -1
                progress_event.set()
                raise

            if cmd is not None:
                self.terminal_params['cmd'] = cmd

            self.terminal_session = _control.resume(session_name=self.session_name,
                                                    session_instance=self,
                                                    session_list=session_list,
                                                    logger=self.logger, **self.terminal_params)

            self._progress_status = 25
            progress_event.set()

            if self.session_name is None:
                _new_session = True
                try:
                    self.session_name = self.terminal_session.session_info.name
                except AttributeError:
                    # if self.terminal_session is None, we end up with a session failure...
                    self.HOOK_session_startup_failed()

                    self._progress_status = -1
                    progress_event.set()

                    return False

            self._progress_status = 30
            progress_event.set()

            if self.has_terminal_session() and not self.faulty:

                self.terminal_session.session_info_protect()

                if self.get_session_cmd() != 'PUBLISHED':
                    self.published_applications = False

                self._progress_status = 35
                progress_event.set()

                if self._SUPPORTED_SOUND and self.terminal_session.params.snd_system is not 'none':
                    self.has_terminal_session() and not self.faulty and self.terminal_session.start_sound()
                else:
                    self._SUPPORTED_SOUND = False

                self._progress_status = 40
                progress_event.set()

                if self._SUPPORTED_TELEKINESIS and self.has_terminal_session() and not self.faulty:
                    gevent.spawn(self.terminal_session.start_telekinesis)

                self._progress_status = 50
                progress_event.set()

                try:
                    if (self._SUPPORTED_PRINTING and self.printing) or \
                       (self._SUPPORTED_MIMEBOX and self.allow_mimebox) or \
                       (self._SUPPORTED_FOLDERSHARING and self.allow_share_local_folders):
                        self.has_terminal_session() and not self.faulty and self.terminal_session.start_sshfs()
                except x2go_exceptions.X2GoUserException, e:
                    self.logger('%s' % str(e), loglevel=log.loglevel_WARN)
                    self.HOOK_sshfs_not_available()
                    self._SUPPORTED_PRINTING = False
                    self._SUPPORTED_MIMEBOX = False
                    self._SUPPORTED_FOLDERSHARING = False

                self._progress_status = 60
                progress_event.set()

                if self._SUPPORTED_PRINTING and self.printing:
                    try:
                        self.has_terminal_session() and not self.faulty and self.terminal_session.start_printing()
                        self.has_terminal_session() and not self.faulty and self.session_environment.update({'X2GO_SPOOLDIR': self.terminal_session.get_printing_spooldir(), })
                    except (x2go_exceptions.X2GoUserException, x2go_exceptions.X2GoSFTPClientException), e:
                        self.logger('%s' % str(e), loglevel=log.loglevel_WARN)
                        self.HOOK_printing_not_available()
                        self._SUPPORTED_PRINTING = False
                    except x2go_exceptions.X2GoControlSessionException, e:
                        self.logger('%s' % str(e), loglevel=log.loglevel_ERROR)
                        self.HOOK_on_control_session_death()
                        self._X2GoSession__disconnect()
                        return False

                self._progress_status = 70
                progress_event.set()

                if self._SUPPORTED_MIMEBOX and self.allow_mimebox:
                    try:
                        self.has_terminal_session() and not self.faulty and self.terminal_session.start_mimebox(mimebox_extensions=self.mimebox_extensions, mimebox_action=self.mimebox_action)
                        self.has_terminal_session() and self.session_environment.update({'X2GO_MIMEBOX': self.terminal_session.get_mimebox_spooldir(), })
                    except (x2go_exceptions.X2GoUserException, x2go_exceptions.X2GoSFTPClientException), e:
                        self.logger('%s' % str(e), loglevel=log.loglevel_WARN)
                        self.HOOK_mimebox_not_available()
                        self._SUPPORTED_MIMEBOX = False
                    except x2go_exceptions.X2GoControlSessionException, e:
                        self.logger('%s' % str(e), loglevel=log.loglevel_ERROR)
                        self.HOOK_on_control_session_death()
                        self._X2GoSession__disconnect()
                        return False

                self._progress_status = 80
                progress_event.set()

                # only run the session startup command if we do not resume...
                if _new_session:
                    self.has_terminal_session() and self.terminal_session.run_command(env=self.session_environment)

                self.virgin = False
                self.suspended = False
                self.running = True
                self.terminated = False
                self.faulty = False

                self._progress_status = 90
                progress_event.set()

                # if self.client_instance exists than the folder sharing is handled via the self.set_master_session() evoked by the session registry
                if (not self.client_instance) and \
                   self._SUPPORTED_FOLDERSHARING and \
                   self.allow_share_local_folders:
                        gevent.spawn(self.share_all_local_folders)

                self._progress_status = 100
                progress_event.set()

                self.has_terminal_session() and self.terminal_session.session_info_unprotect()
                return True

            else:
                self.terminal_session = None

                self._progress_status = -1
                progress_event.set()

                return False

        else:

            self._progress_status = -1
            progress_event.set()

            self._X2GoSession__disconnect()
            return False
    __resume = resume

    def start(self, cmd=None, progress_event=None):
        """\
        Start a new X2Go session on the remote X2Go server.

        @param cmd: manually hand over the command that is to be launched in the new session
        @type cmd: C{str}
        @param progress_event: a C{thread.Event} object that notifies a status object like the one in
            L{utils.ProgressStatus}.
        @type progress_event: C{obj}

        @return: returns C{True} if starting the session has been successful, C{False} otherwise
        @rtype: C{bool}

        """
        self.session_name = None
        return self.resume(cmd=cmd, progress_event=progress_event)
    __start = start

    def share_desktop(self, desktop=None, user=None, display=None, share_mode=0, check_desktop_list=True, progress_event=None):
        """\
        Share an already running X2Go session on the remote X2Go server locally. The shared session may be either
        owned by the same user or by a user that grants access to his/her desktop session by the local user.

        @param desktop: desktop ID of a sharable desktop in format <user>@<display>
        @type desktop: C{str}
        @param user: user name and display number can be given separately, here give the
            name of the user who wants to share a session with you.
        @type user: C{str}
        @param display: user name and display number can be given separately, here give the
            number of the display that a user allows you to be shared with.
        @type display: C{str}
        @param share_mode: desktop sharing mode, 0 is VIEW-ONLY, 1 is FULL-ACCESS.
        @type share_mode: C{int}
        @param check_desktop_list: check if the given desktop is available on the X2Go server; handle with care as
            the server-side C{x2golistdesktops} command might block client I/O.
        @type check_desktop_list: C{bool}
        @param progress_event: a C{thread.Event} object that notifies a status object like the one in
            L{utils.ProgressStatus}.
        @type progress_event: C{obj}

        @return: returns C{True} if starting the session has been successful, C{False} otherwise
        @rtype: C{bool}

        @raise X2GoDesktopSharingException: if a given desktop ID does not specify an available desktop session
        @raise X2GoSessionException: if the available desktop session appears to be dead, in fact

        """
        self._lock.acquire()
        try:
            _retval = self._share_desktop(desktop=desktop, user=user, display=display, share_mode=share_mode, check_desktop_list=check_desktop_list, progress_event=progress_event)
        except:
            self._lock.release()
            raise
        finally:
            self._lock.release()
        return _retval

    def _share_desktop(self, desktop=None, user=None, display=None, share_mode=0, check_desktop_list=True, progress_event=None):
        """\
        Share an already running X2Go session on the remote X2Go server locally. The shared session may be either
        owned by the same user or by a user that grants access to his/her desktop session by the local user.

        @param desktop: desktop ID of a sharable desktop in format <user>@<display>
        @type desktop: C{str}
        @param user: user name and display number can be given separately, here give the
            name of the user who wants to share a session with you.
        @type user: C{str}
        @param display: user name and display number can be given separately, here give the
            number of the display that a user allows you to be shared with.
        @type display: C{str}
        @param share_mode: desktop sharing mode, 0 is VIEW-ONLY, 1 is FULL-ACCESS.
        @type share_mode: C{int}
        @param check_desktop_list: check if the given desktop is available on the X2Go server; handle with care as
            the server-side C{x2golistdesktops} command might block client I/O.
        @type check_desktop_list: C{bool}
        @param progress_event: a C{thread.Event} object that notifies a status object like the one in
            L{utils.ProgressStatus}.
        @type progress_event: C{obj}

        @return: returns C{True} if starting the session has been successful, C{False} otherwise
        @rtype: C{bool}

        @raise X2GoDesktopSharingException: if a given desktop ID does not specify an available desktop session
        @raise X2GoSessionException: if the available desktop session appears to be dead, in fact

        """
        self.terminal_session = 'PENDING'

        # initialize a dummy event to avoid many if clauses further down in the code
        self.reset_progress_status()
        _dummy_event = threading.Event()
        if type(progress_event) != type(_dummy_event):
            progress_event = _dummy_event

        self._progress_status = 5
        progress_event.set()

        _desktop = desktop or '%s@%s' % (user, display)
        if check_desktop_list:
            desktop_list = self._X2GoSession__list_desktops()
            if not _desktop in desktop_list:
                _orig_desktop = _desktop
                _desktop = '%s.0' % _desktop
                if not _desktop in desktop_list:
                    self.HOOK_no_such_desktop(desktop=_orig_desktop)
                    self._progress_status = -1
                    progress_event.set()
                    return False

        self._progress_status = 33
        progress_event.set()

        _session_owner = _desktop.split('@')[0]

        if self.is_alive():
            if self.get_username() != _session_owner:
                self.logger('waiting for user ,,%s\'\' to interactively grant you access to his/her desktop session...' % _session_owner, loglevel=log.loglevel_NOTICE)
                self.logger('THIS MAY TAKE A WHILE!', loglevel=log.loglevel_NOTICE)

                self._progress_status = 50
                progress_event.set()

            _control = self.control_session
            try:
                self.terminal_session = _control.share_desktop(desktop=_desktop, share_mode=share_mode,
                                                               logger=self.logger, **self.terminal_params)

                self._progress_status = 80
                progress_event.set()

            except ValueError:
                # x2gostartagent output parsing will result in a ValueError. This one we will catch
                # here and change it into an X2GoSessionException

                self._progress_status = -1
                progress_event.set()

                raise x2go_exceptions.X2GoSessionException('the session on desktop %s is seemingly dead' % _desktop)

            except x2go_exceptions.X2GoDesktopSharingDenied:

                self._progress_status = -1
                progress_event.set()

                self.HOOK_desktop_sharing_denied()
                return False

            self._progress_status = 90
            progress_event.set()

            if self.has_terminal_session():
                self.session_name = self.terminal_session.session_info.name

                # shared desktop sessions get their startup command set by the control
                # session, run this pre-set command now...
                self.terminal_session.run_command(env=self.session_environment)

                self.virgin = False
                self.suspended = False
                self.running = True
                self.terminated = False
                self.faulty = False

                self._progress_status = 100
                progress_event.set()

                return self.running
            else:
                self.terminal_session = None

                self._progress_status = -1
                progress_event.set()

        else:

            self._progress_status = -1
            progress_event.set()

            self._X2GoSession__disconnect()

        return False
    __share_desktop = share_desktop

    def is_desktop_session(self):
        """\
        Test if this X2Go session is a desktop session.

        @return: C{True} if this session is of session type desktop ('D').
        @rtype: C{bool}

        """
        if self.has_terminal_session():
            return self.terminal_session.is_desktop_session()
    __is_desktop_session = is_desktop_session

    def is_rootless_session(self):
        """\
        Test if this X2Go session is a rootless session.

        @return: C{True} if this session is of session type rootless ('R').
        @rtype: C{bool}

        """
        if self.has_terminal_session():
            return self.terminal_session.is_rootless_session()
    __is_rootless_session = is_rootless_session

    def is_shadow_session(self):
        """\
        Test if this X2Go session is a desktop sharing (aka shadow) session.

        @return: C{True} if this session is of session type shadow ('S').
        @rtype: C{bool}

        """
        if self.has_terminal_session():
            return self.terminal_session.is_shadow_session()
    __is_shadow_session = is_shadow_session

    def is_pubapp_session(self):
        """\
        Test if this X2Go session is a published applications session.

        @return: C{True} if this session is of session type published applications ('P').
        @rtype: C{bool}

        """
        if self.has_terminal_session():
            return self.terminal_session.is_pubapp_session()
    __is_pubapp_session = is_pubapp_session

    def suspend(self):
        """\
        Suspend this X2Go session.

        @return: returns C{True} if suspending the session has been successful, C{False} otherwise
        @rtype: C{bool}

        @raise X2GoSessionException: if the session could not be suspended

        """
        self._lock.acquire()
        try:
            _retval = self._suspend()
        except:
            self._lock.release()
            raise
        finally:
            self._lock.release()
        return _retval

    def _suspend(self):
        """\
        Suspend this X2Go session.

        @return: returns C{True} if suspending the session has been successful, C{False} otherwise
        @rtype: C{bool}

        @raise X2GoSessionException: if the session could not be suspended

        """
        if self.is_alive():
            if self.has_terminal_session():

                self.running = False
                self.suspended = True
                self.terminated = False
                self.faulty = False
                self.active = False

                # unmount shared folders
                self.unshare_all_local_folders(force_all=True, update_exported_folders=False)

                self.unset_master_session()

                if self.has_terminal_session():
                    if self.terminal_session.suspend():
                        self.session_cleanup()
                        del self.terminal_session
                        self.terminal_session = None
                        return True

            elif self.has_control_session() and self.session_name:
                if self.control_session.suspend(session_name=self.session_name):

                    self.running = False
                    self.suspended = True
                    self.terminated = False
                    self.faulty = False
                    self.active = False
                    self.session_cleanup()
                    return True

            else:
                raise x2go_exceptions.X2GoSessionException('cannot suspend session')

        else:
            self._X2GoSession__disconnect()

        return False
    __suspend = suspend

    def terminate(self):
        """\
        Terminate this X2Go session.

        @return: returns C{True} if terminating the session has been successful, C{False} otherwise
        @rtype: C{bool}

        @raise X2GoSessionException: if the session could not be terminated

        """
        self._lock.acquire()
        try:
            _retval = self._terminate()
        except:
            self._lock.release()
            raise
        finally:
            self._lock.release()
        return _retval

    def _terminate(self):
        """\
        Terminate this X2Go session.

        @return: returns C{True} if terminating the session has been successful, C{False} otherwise
        @rtype: C{bool}

        @raise X2GoSessionException: if the session could not be terminated

        """
        if self.is_alive():
            if self.has_terminal_session():

                self.running = False
                self.suspended = False
                self.terminated = True
                self.faulty = False
                self.active = False

                # unmount shared folders
                self.unshare_all_local_folders(force_all=True, update_exported_folders=False)

                self.unset_master_session()

                if self.has_terminal_session():
                    if self.terminal_session.terminate():
                        self.session_cleanup()
                        del self.terminal_session
                        self.terminal_session = None
                        return True

            elif self.has_control_session() and self.session_name:
                if self.control_session.terminate(session_name=self.session_name):

                    self.running = False
                    self.suspended = False
                    self.terminated = True
                    self.faulty = False
                    self.active = False
                    self.session_cleanup()
                    return True
            else:
                raise x2go_exceptions.X2GoSessionException('cannot terminate session')

        else:
            self._X2GoSession__disconnect()

        return False
    __terminate = terminate

    def get_profile_name(self):
        """\
        Retrieve the profile name of this L{X2GoSession} instance.

        @return: X2Go client profile name of the session
        @rtype: C{str}

        """
        return self.profile_name
    __get_profile_name = get_profile_name

    def get_profile_id(self):
        """\
        Retrieve the profile ID of this L{X2GoSession} instance.

        @return: the session profile's id
        @rtype: C{str}

        """
        return self.profile_id
    __get_profile_id = get_profile_id

    ###
    ### QUERYING INFORMATION
    ###

    def session_ok(self):
        """\
        Test if this C{X2GoSession} is
        in a healthy state.

        @return: C{True} if session is ok, C{False} otherwise
        @rtype: C{bool}

        """
        if self.has_terminal_session():
            return self.terminal_session.ok()
        return False
    __session_ok = session_ok

    def color_depth_from_session_name(self):
        """\
        Extract color depth from session name.

        @return: the session's color depth (as found in the session name)
        @rtype: C{str}

        """
        try:
            return int(self.get_session_name().split('_')[2][2:])
        except:
            return None
    __color_depth_from_session_name = color_depth_from_session_name

    def is_color_depth_ok(self):
        """\
        Check if this session will display properly with the local screen's color depth.

        @return: C{True} if the session will display on this client screen, 
            C{False} otherwise. If no terminal session is yet registered with this session, C{None} is returned.
        @rtype: C{bool}

        """
        _depth_local = utils.local_color_depth()
        _depth_session = self.color_depth_from_session_name()
        if type(_depth_session) == types.IntType:
            return utils.is_color_depth_ok(depth_session=_depth_session, depth_local=_depth_local)

        # we assume the color depth is ok, if _depth_session could not be obtained from the session name
        # (this should not happen, but it does...)
        return True
    __is_color_depth_ok = is_color_depth_ok

    def is_connected(self):
        """\
        Test if the L{X2GoSession}'s control session is connected to the 
        remote X2Go server.

        @return: C{True} if session is connected, C{False} otherwise
        @rtype: C{bool}

        """
        self.connected = bool(self.control_session and self.control_session.is_connected())
        if not self.connected:
            self.running = None
            self.suspended = None
            self.terminated = None
            self.faulty = None
        return self.connected
    __is_connected = is_connected

    def is_running(self, update_status=False):
        """\
        Test if the L{X2GoSession}'s terminal session is up and running.

        @return: C{True} if session is running, C{False} otherwise
        @rtype: C{bool}

        """
        if not update_status:
            return self.running

        if self.is_connected():
            self.running = self.control_session.is_running(self.get_session_name())
            if self.running:
                self.suspended = False
                self.terminated = False
                self.faulty = False
            if self.virgin and not self.running:
                self.running = None
        return self.running
    __is_running = is_running

    def is_suspended(self, update_status=False):
        """\
        Test if the L{X2GoSession}'s terminal session is in suspended state.

        @return: C{True} if session is suspended, C{False} otherwise
        @rtype: C{bool}

        """
        if not update_status:
            return self.suspended

        if self.is_connected():
            self.suspended = self.control_session.is_suspended(self.get_session_name())
            if self.suspended:
                self.running = False
                self.terminated = False
                self.faulty = False
            if self.virgin and not self.suspended:
                self.suspended = None
        return self.suspended
    __is_suspended = is_suspended

    def has_terminated(self, update_status=False):
        """\
        Test if the L{X2GoSession}'s terminal session has terminated.

        @return: C{True} if session has terminated, C{False} otherwise
        @rtype: C{bool}

        """
        if not update_status:
            return self.terminated

        if self.is_connected():
            self.terminated = not self.virgin and self.control_session.has_terminated(self.get_session_name())
            if self.terminated:
                self.running = False
                self.suspended = False
                self.faulty = False
            if self.virgin and not self.terminated:
                self.terminated = None
        return self.terminated
    __has_terminated = has_terminated

    def is_folder_sharing_available(self):
        """\
        Test if the remote session allows sharing of local folders with the session.

        @return: returns C{True} if local folder sharing is available in the remote session
        @rtype: C{bool}

        """
        if self._SUPPORTED_FOLDERSHARING and self.allow_share_local_folders:
            if self.is_connected():
                return self.control_session.is_sshfs_available()
            else:
                self.logger('session is not connected, cannot share local folders now', loglevel=log.loglevel_WARN)
        else:
            self.logger('local folder sharing is disabled for this session profile', loglevel=log.loglevel_WARN)
        return False
    __is_folder_sharing_available = is_folder_sharing_available

    def _update_restore_exported_folders(self):

        # remember exported folders for restoring them on session suspension/termination
        if self.client_instance and self.restore_shared_local_folders:
            _exported_folders = copy.deepcopy(self._restore_exported_folders)
            for folder in [ sf for sf in self.shared_folders.keys() if self.shared_folders[sf]['status'] in ('new', 'mounted') ]:
                _exported_folders.update({ unicode(folder): True })
            for folder in _exported_folders.keys():
                if folder in [ sf for sf in self.shared_folders.keys() if self.shared_folders[sf]['status'] == 'unmounted' ]:
                    _exported_folders.update({ unicode(folder): False })
            self._restore_exported_folders = _exported_folders

    def share_local_folder(self, local_path=None, folder_name=None, update_exported_folders=True):
        """\
        Share a local folder with this registered X2Go session.

        @param local_path: the full path to an existing folder on the local
            file system
        @type local_path: C{str}
        @param folder_name: synonymous to C{local_path}
        @type folder_name: C{str}
        @param update_exported_folders: do an update of the session profile option ,,export'' after the operation
        @type update_exported_folders: C{bool}

        @return: returns C{True} if the local folder has been successfully mounted within
            this X2Go session
        @rtype: C{bool}

        @raise X2GoSessionException: if this L{X2GoSession} does not have an associated terminal session

        """
        # compat for Python-X2Go (<=0.1.1.6)
        if folder_name: local_path=folder_name

        local_path = unicode(local_path)

        retval = False
        if self.has_terminal_session():
            if self.is_folder_sharing_available() and self.is_master_session():

                # for the sake of non-blocking I/O: let's pretend the action has already been successful
                if self.shared_folders.has_key(local_path):
                    self.shared_folders[local_path]['status'] = 'mounted'
                else:
                    self.shared_folders.update({ local_path: { 'status': 'new', 'mountpoint': '', }, })
                try:
                    if self.terminal_session.share_local_folder(local_path=local_path):
                        if update_exported_folders:
                            self._update_restore_exported_folders()
                        retval = True
                    else:
                        # remove local_path from folder again if the unmounting process failed
                        if self.shared_folders[local_path]['status'] == 'new':
                            del self.shared_folders[local_path]
                        else:
                            self.shared_folders[local_path]['status'] = 'unmounted'

                        # disable this local folder in session profile if restoring shared folders for following sessions is activated
                        if self.client_instance and self.restore_shared_local_folders:
                            if local_path in self._restore_exported_folders.keys():
                                self._restore_exported_folders[local_path] = False

                except x2go_exceptions.X2GoControlSessionException:
                    if self.connected: self.HOOK_on_control_session_death()
                    self._X2GoSession__disconnect()
                    return retval

                # save exported folders to session profile config if requested by session profile parameter ,,restoreexports''...
                if update_exported_folders and self.client_instance and self.restore_shared_local_folders:
                    self._update_restore_exported_folders()
                    self.client_instance.set_profile_config(self.profile_name, 'export', self._restore_exported_folders)

        else:
            raise x2go_exceptions.X2GoSessionException('this X2GoSession object does not have any associated terminal')
        return retval

    __share_local_folder = share_local_folder

    def share_all_local_folders(self, update_exported_folders=True):
        """\
        Share all local folders configured to be mounted within this X2Go session.

        @param update_exported_folders: do an update of the session profile option ,,export'' after the operation
        @type update_exported_folders: C{bool}

        @return: returns C{True} if all local folders could be successfully mounted
            inside this X2Go session
        @rtype: C{bool}

        """
        retval = False
        if self.is_running() and not self.faulty  and self._SUPPORTED_FOLDERSHARING and self.share_local_folders and self.allow_share_local_folders and self.has_terminal_session():
            if self.is_master_session():
                if self.is_folder_sharing_available():
                    retval = True
                    for _folder in self.share_local_folders:
                        try:
                            retval = self.share_local_folder(_folder, update_exported_folders=False) and retval
                        except x2go_exceptions.X2GoUserException, e:
                            retval = False
                            self.logger('%s' % str(e), loglevel=log.loglevel_WARN)
                        except x2go_exceptions.X2GoControlSessionException, e:
                            retval = False
                            self.logger('%s' % str(e), loglevel=log.loglevel_ERROR)
                            self.HOOK_on_control_session_death()
                            self._X2GoSession__disconnect()
                            break

                    if update_exported_folders:
                        self._update_restore_exported_folders()
                        self.client_instance.set_profile_config(self.profile_name, 'export', self._restore_exported_folders)
                else:
                    self.HOOK_foldersharing_not_available()
        return retval
    __share_all_local_folders = share_all_local_folders

    def unshare_local_folder(self, local_path=None, update_exported_folders=True):
        """\
        Unshare a local folder that is mounted within this X2Go session.

        @param local_path: the full path to an existing folder on the local
            file system that is mounted in this X2Go session and shall be
            unmounted
        @type local_path: C{str}
        @param update_exported_folders: do an update of the session profile option ,,export'' after the operation
        @type update_exported_folders: C{bool}

        @return: returns C{True} if all local folders could be successfully unmounted
            inside this X2Go session
        @rtype: C{bool}

        @raise X2GoSessionException: if this L{X2GoSession} does not have an associated terminal session

        """
        retval = False

        local_path = unicode(local_path)

        if self.has_terminal_session():
            if self.is_folder_sharing_available() and self.is_master_session() and local_path in self.shared_folders.keys():

                # for the sake of non-blocking I/O: let's pretend the action has already been successful
                self.shared_folders[local_path]['status'] = 'unmounted'
                if self.terminal_session.unshare_local_folder(local_path=local_path):
                    retval = True
                else:
                    # if unmounting failed restore the status with ,,mounted'', not sure if that works ok...
                    self.shared_folders[local_path]['status'] = 'mounted'

                # save exported folders to session profile config if requested by session profile parameter ,,restoreexports''...
                if update_exported_folders and self.client_instance and self.restore_shared_local_folders:
                    self._update_restore_exported_folders()
                    self.client_instance.set_profile_config(self.profile_name, 'export', self._restore_exported_folders)

        else:
            raise x2go_exceptions.X2GoSessionException('this X2GoSession object does not have any associated terminal')

        return retval
    __unshare_local_folder = unshare_local_folder

    def unshare_all_local_folders(self, force_all=False, update_exported_folders=True):
        """\
        Unshare all local folders mounted within this X2Go session.

        @param force_all: Really unmount _all_ shared folders, including the print spool folder and
            the MIME box spool dir (not recommended).
        @type force_all: C{bool}
        @param update_exported_folders: do an update of the session profile option ,,export'' after the operation
        @type update_exported_folders: C{bool}

        @return: returns C{True} if all local folders could be successfully unmounted
            inside this X2Go session
        @rtype: C{bool}

        @raise X2GoSessionException: if this L{X2GoSession} does not have an associated terminal session

        """
        if self.has_terminal_session():
            if self.is_folder_sharing_available() and self.is_master_session():

                if force_all:
                    retval = self.terminal_session.unshare_all_local_folders()
                    if retval:
                        self.shared_folders = {}
                    return retval
                else:
                    retval = True
                    _shared_folders = copy.deepcopy(self.shared_folders)
                    for _folder in _shared_folders.keys():
                        retval = self.unshare_local_folder(_folder, update_exported_folders=False) and retval
                    if update_exported_folders:
                        self._update_restore_exported_folders()
                        self.client_instance.set_profile_config(self.profile_name, 'export', self._restore_exported_folders)
                    return retval
        else:
            raise x2go_exceptions.X2GoSessionException('this X2GoSession object does not have any associated terminal')
        return False
    __unshare_all_local_folders = unshare_all_local_folders

    def get_shared_folders(self, check_list_mounts=False, mounts=None):
        """\
        Get a list of local folders mounted within this X2Go session from this client.

        @param check_list_mounts: if set to C{True} the list of shared folders is referenced against
            the latest status of the server-side mount list.
        @type check_list_mounts: C{bool}
        @param mounts: a server-side dictionary of session name keys and lists of mounted shares (server-side mount points)
        @type mounts: C{dict}

        @return: returns a C{list} of those local folder names that are mounted with this X2Go session.
        @rtype: C{list}

        """
        if self.is_folder_sharing_available and self.is_master_session() and self.shared_folders and check_list_mounts:

            unshared_folders = []
            if mounts is None:
                mounts = self.list_mounts()
            _defacto_mounts = [ unicode(m.split('|')[1].split('/')[-1]) for m in mounts ]

            for shared_folder in self.shared_folders.keys():

                if _X2GOCLIENT_OS == 'Windows':
                    _driveletter, _path = os.path.splitdrive(shared_folder)
                    _mount_point = '_windrive_%s%s' % (_driveletter[0], _path.replace('\\', '_'))
                    _mount_point = _mount_point.replace(' ', '_')

                else:
                    _mount_point = shared_folder.replace('/', '_')
                    _mount_point = _mount_point.replace(' ', '_')

                self.shared_folders[shared_folder]['status'] = 'mounted'
                self.shared_folders[shared_folder]['mountpoint'] = unicode(_mount_point)

            for m in _defacto_mounts:
                for sf in self.shared_folders.keys():
                    if self.shared_folders[sf]['mountpoint'] == m:
                        self.shared_folders[sf]['status'] = 'mounted'
                        break

            unshared_folders = False

            for sf in self.shared_folders.keys():
                m = self.shared_folders[sf]['mountpoint']
                if m and m not in _defacto_mounts:
                    try:
                        if self.shared_folders[sf]['status'] == 'mounted':
                            self.shared_folders[sf]['status'] = 'unmounted'
                            self.logger('Detected server-side unsharing of client-side folder for profile %s: %s:' % (self.get_profile_name(), sf), loglevel=log.loglevel_INFO)
                            unshared_folders = True
                    except IndexError:
                        pass

            if unshared_folders:
                self._update_restore_exported_folders()

        return [ unicode(sf) for sf in self.shared_folders if self.shared_folders[sf]['status'] in ('new', 'mounted') ]
    __get_shared_folders = get_shared_folders

    def is_locked(self):
        """\
        Query session if it is locked by some command being processed.

        @return: returns C{True} is the session is locked, C{False} if not; returns C{None}, if there is no
            control session yet.
        @rtype: C{bool}

        """
        if self.control_session is not None:
            return self.control_session.locked or self.locked
        return None
    __is_locked = is_locked

    def session_cleanup(self):
        """\
        Clean up X2Go session.

        """
        # release terminal session's proxy
        if self.has_terminal_session():
            self.terminal_session.release_proxy()

        # remove client-side session cache
        if self.terminated and self.has_terminal_session():
            self.terminal_session.post_terminate_cleanup()

        # destroy terminal session
        if self.has_terminal_session():
            self.terminal_session.__del__()

        self.terminal_session = None
    __session_cleanup = session_cleanup

    def is_locked(self):
        """\
        Test if the session is lock at the moment. This normally occurs
        if there is some action running that will result in a session status
        change.

        @return: returns C{True} if the session is locked
        @rtype: C{bool}

        """
        self._lock.locked()
