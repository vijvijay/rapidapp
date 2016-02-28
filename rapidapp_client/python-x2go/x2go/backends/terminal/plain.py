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
X2GoTerminalSession class - core functions for handling your individual X2Go sessions.

This backend handles X2Go server implementations that respond with session infos 
via server-side PLAIN text output.

"""
__NAME__ = 'x2goterminalsession-pylib'

# modules
import os
import types
import gevent
import cStringIO
import copy
import shutil
import threading

# Python X2Go modules
import x2go.rforward as rforward
import x2go.sftpserver as sftpserver
import x2go.printqueue as printqueue
import x2go.mimebox as mimebox
import x2go.telekinesis as telekinesis
import x2go.log as log
import x2go.defaults as defaults
import x2go.utils as utils
import x2go.x2go_exceptions as x2go_exceptions

# we hide the default values from epydoc (that's why we transform them to _UNDERSCORE variables)
from x2go.defaults import X2GOCLIENT_OS as _X2GOCLIENT_OS
from x2go.defaults import LOCAL_HOME as _LOCAL_HOME
from x2go.defaults import CURRENT_LOCAL_USER as _CURRENT_LOCAL_USER
from x2go.defaults import X2GO_CLIENT_ROOTDIR as _X2GO_CLIENT_ROOTDIR
from x2go.defaults import X2GO_SESSIONS_ROOTDIR as _X2GO_SESSIONS_ROOTDIR
from x2go.defaults import X2GO_GENERIC_APPLICATIONS as _X2GO_GENERIC_APPLICATIONS
from x2go.defaults import X2GO_DESKTOPSESSIONS as _X2GO_DESKTOPSESSIONS

from x2go.defaults import BACKENDS as _BACKENDS

_local_color_depth = utils.local_color_depth()

def _rewrite_cmd(cmd, params=None):
    """\
    Mechansim that rewrites X2Go server commands into something that gets understood by
    the server-side script C{x2goruncommand}.

    @param cmd: the current command for execution (as found in the session profile parameter C{cmd})
    @type cmd: C{str}
    @param params: an session paramter object
    @type params: L{X2GoSessionParams}

    @return: the rewritten command for server-side execution
    @rtype: C{str}

    """
    # start with an empty string
    cmd = cmd or ''

    # find window manager commands
    if cmd in _X2GO_DESKTOPSESSIONS.keys():
        cmd = _X2GO_DESKTOPSESSIONS[cmd]

    if (cmd == 'RDP') and (type(params) == X2GoSessionParams):
        _depth = params.depth
        if int(_depth) == 17:
            _depth = 16
        if params.geometry == 'fullscreen':
            cmd = 'rdesktop -f -N %s %s -a %s' % (params.rdp_options, params.rdp_server, _depth)
        else:
            cmd = 'rdesktop -g %s -N %s %s -a %s' % (params.geometry, params.rdp_options, params.rdp_server, _depth)

    # place quot marks around cmd if not empty string
    if cmd:
        cmd = '"%s"' % cmd

    if ((type(params) == X2GoSessionParams) and params.published_applications and cmd == ''):
        cmd = 'PUBLISHED'

    return cmd


def _rewrite_blanks(cmd):
    """\
    In command strings X2Go server scripts expect blanks being rewritten to ,,X2GO_SPACE_CHAR''.

    @param cmd: command that has to be rewritten for passing to the server
    @type cmd: C{str}

    @return: the command with blanks rewritten to ,,X2GO_SPACE_CHAR''
    @rtype: C{str}

    """
    # X2Go run command replace X2GO_SPACE_CHAR string with blanks
    if cmd:
        cmd = cmd.replace(" ", "X2GO_SPACE_CHAR")
    return cmd


class X2GoSessionParams(object):
    """\
    The L{X2GoSessionParams} class is used to store all parameters that
    C{X2GoTerminalSession} backend objects are constructed with.

    """
    def rewrite_session_type(self):
        """\
        Rewrite the X2Go session type, so that the X2Go server
        can understand it (C{desktop} -> C{D}, etc.).

        Also if the object's C{command} property is a known window 
        manager, the session type will be set to 'D' 
        (i.e. desktop).

        @return: 'D' if session should probably a desktop session,
            'R' for rootless sessions, 'P' for sessions providing published
            applications, and 'S' for desktop sharing sessions
        @rtype: C{str}

        """
        cmd = self.cmd
        published = self.published_applications

        if published and self.cmd in ('', 'PUBLISHED'):
            self.session_type = 'P'
            self.cmd = 'PUBLISHED'
        else:
            if cmd == 'RDP' or cmd.startswith('rdesktop') or cmd.startswith('xfreedrp'):
                if self.geometry == 'fullscreen': self.session_type = 'D'
                else: self.session_type = 'R'
            elif cmd == 'XDMCP':
                self.session_type = 'D'
            elif cmd in _X2GO_DESKTOPSESSIONS.keys():
                self.session_type = 'D'
            elif os.path.basename(cmd) in _X2GO_DESKTOPSESSIONS.values():
                self.session_type = 'D'

        if self.session_type in ("D", "desktop"):
            self.session_type = 'D'
        elif self.session_type in ("S", "shared", "shadow"):
            self.session_type = 'S'
        elif self.session_type in ("R", "rootless", "application"):
            self.session_type = 'R'
        elif self.session_type in ("P", "published", "published_applications"):
            self.session_type = 'P'

        return self.session_type

    def update(self, **properties_to_be_updated):
        """\
        Update all properties in the object L{X2GoSessionParams} object from
        the passed on dictionary.

        @param properties_to_be_updated: a dictionary with L{X2GoSessionParams}
            property names as keys und their values to be update in 
            L{X2GoSessionParams} object.
        @type properties_to_be_updated: C{dict}

        """
        for key in properties_to_be_updated.keys():
            setattr(self, key, properties_to_be_updated[key] or '')
        self.rewrite_session_type()


class X2GoTerminalSession(object):
    """\
    Class for managing X2Go terminal sessions on a remote X2Go server via Paramiko/SSH.

    With the L{x2go.backends.terminal.plain.X2GoTerminalSession} class you can start new X2Go sessions, resume suspended 
    sessions or suspend resp. terminate currently running sessions on a 
    connected X2Go server.

    An L{x2go.backends.terminal.plain.X2GoTerminalSession} object uses two main data structure classes:

        - L{X2GoSessionParams}: stores all parameters that have been passed to the 
        constructor method.

        - C{X2GoServerSessionInfo*} backend class: when starting or resuming a session, an object of this class 
        will be used to store all information retrieved from the X2Go server.

    The terminal session instance works closely together (i.e. depends on) a connected control
    session instance (e.g. L{x2go.backends.control.plain.X2GoControlSession}). You never should use either of them as a standalone
    instance. Both, control session and terminal session(s) get managed/controlled via L{X2GoSession} instances.

    """
    def __init__(self, control_session, session_info=None,
                 geometry="800x600", depth=_local_color_depth, link="adsl", pack="16m-jpeg-9", dpi='',
                 cache_type="unix-kde",
                 kbtype='null/null', kblayout='null', kbvariant='null',
                 clipboard='both',
                 session_type="application", snd_system='pulse', snd_port=4713, cmd=None,
                 published_applications=False,
                 set_session_title=False, session_title="", applications=[],
                 rdp_server=None, rdp_options=None,
                 xdmcp_server=None,
                 convert_encoding=False, server_encoding='UTF-8', client_encoding='UTF-8',
                 rootdir=None,
                 profile_name='UNKNOWN', profile_id=utils._genSessionProfileId(),
                 print_action=None, print_action_args={},
                 info_backend=_BACKENDS['X2GoServerSessionInfo']['default'],
                 list_backend=_BACKENDS['X2GoServerSessionList']['default'],
                 proxy_backend=_BACKENDS['X2GoProxy']['default'], proxy_options={},
                 printing_backend=_BACKENDS['X2GoClientPrinting']['default'],
                 client_rootdir=os.path.join(_LOCAL_HOME, _X2GO_CLIENT_ROOTDIR),
                 sessions_rootdir=os.path.join(_LOCAL_HOME, _X2GO_SESSIONS_ROOTDIR),
                 session_instance=None,
                 logger=None, loglevel=log.loglevel_DEFAULT):
        """\
        Initialize an X2Go session. With the L{x2go.backends.terminal.plain.X2GoTerminalSession} class you can start
        new X2Go sessions, resume suspended sessions or suspend resp. terminate
        currently running sessions on a connected X2Go server.

        @param geometry: screen geometry of the X2Go session. Can be either C{<width>x<height>},
            C{maximize} or C{fullscreen}
        @type geometry: C{str}
        @param depth: color depth in bits (common values: C{16}, C{24})
        @type depth: C{int}
        @param link: network link quality (either one of C{modem}, C{isdn}, C{adsl}, C{wan} or C{lan})
        @type link: C{str}
        @param pack: compression method for NX based session proxying
        @type pack: C{str}
        @param dpi: dots-per-inch value for the session screen (has an impact on the font size on screen)
        @type dpi: C{str}
        @param cache_type: a dummy parameter that is passed to the L{x2go.backends.proxy.base.X2GoProxy}. In NX Proxy 
            (class C{X2GoProxyNX3}) this originally is the session name. With X2Go it 
            defines the name of the NX cache directory. Best is to leave it untouched.
        @type cache_type: C{str}
        @param kbtype: keyboard type, e.g. C{pc105/us} (default), C{pc105/de}, ...
        @type kbtype: C{str}
        @param kblayout: keyboard layout, e.g. C{us} (default), C{de}, C{fr}, ...
        @type kblayout: C{str}
        @param kbvariant: keyboard variant, e.g. C{nodeadkeys} (for C{de} layout), C{intl} (for C{us} layout), etc.
        @type kbvariant: C{str}
        @param clipboard: clipboard mode (C{both}: bidirectional copy+paste, C{server}: copy+paste from server to
            client, C{client}: copy+paste from client to server, C{none}: disable clipboard completely
        @type clipboard: C{str}
        @param session_type: either C{desktop}, C{application} (rootless session) or C{shared}
        @type session_type: C{str}
        @param snd_system: sound system to be used on server (C{none}, C{pulse} (default), 
            C{arts} (obsolete) or C{esd})
        @type snd_system: C{str}
        @param snd_port: local sound port for network capable audio system
        @type snd_port: C{int}
        @param cmd: command to be run on X2Go server after session start (only used
            when L{x2go.backends.terminal.plain.X2GoTerminalSession.start()} is called, ignored on resume, suspend etc.
        @type cmd: C{str}
        @param published_applications: session is published applications provider
        @type published_applications: C{bool}
        @param set_session_title: modify the session title (i.e. the Window title) of desktop or shared desktop sessions
        @type set_session_title: C{bool}
        @param session_title: session title for this (desktop or shared desktop) session
        @type session_title: C{str}
        @param applications: applications available for rootless application execution
        @type applications: C{list}
        @param rdp_server: host name of server-side RDP server
        @type rdp_server: C{str}
        @param rdp_options: options for the C{rdesktop} command executed on the X2Go server (RDP proxy mode of X2Go)
        @type rdp_options: C{str}
        @param xdmcp_server: XDMCP server to connect to
        @type xdmcp_server: C{str}
        @param convert_encoding: convert file system encodings between server and client (for client-side shared folders)
        @type convert_encoding: C{bool}
        @param server_encoding: server-side file system / session encoding
        @type server_encoding: C{str}
        @param client_encoding: client-side file system encoding (if client-side is MS Windows, this parameter gets overwritten to WINDOWS-1252)
        @type client_encoding: C{str}
        @param rootdir: X2Go session directory, normally C{~/.x2go}
        @type rootdir: C{str}
        @param profile_name: the session profile name for this terminal session
        @type profile_name: C{str}
        @param profile_id: the session profile ID for this terminal session
        @type profile_id: C{str}
        @param print_action: either a print action short name (PDFVIEW, PDFSAVE, PRINT, PRINTCMD) or the
            resp. C{X2GoPrintActionXXX} class (where XXX equals one of the given short names)
        @type print_action: C{str} or C{class}
        @param print_action_args: optional arguments for a given print_action (for further info refer to
            L{X2GoPrintActionPDFVIEW}, L{X2GoPrintActionPDFSAVE}, L{X2GoPrintActionPRINT} and L{X2GoPrintActionPRINTCMD})
        @type print_action_args: dict
        @param info_backend: backend for handling storage of server session information
        @type info_backend: C{X2GoServerSessionInfo*} instance
        @param list_backend: backend for handling storage of session list information
        @type list_backend: C{X2GoServerSessionList*} instance
        @param proxy_backend: backend for handling the X-proxy connections
        @type proxy_backend: C{X2GoProxy*} instance
        @param proxy_options: a set of very C{X2GoProxy} backend specific options; any option that is not known
            to the C{X2GoProxy} backend will simply be ignored
        @type proxy_options: C{dict}
        @param client_rootdir: client base dir (default: ~/.x2goclient)
        @type client_rootdir: C{str}
        @param sessions_rootdir: sessions base dir (default: ~/.x2go)
        @type sessions_rootdir: C{str}
        @param session_instance: the L{X2GoSession} instance that is parent to this terminal session
        @type session_instance: C{obj}
        @param logger: you can pass an L{X2GoLogger} object to the
            L{x2go.backends.terminal.plain.X2GoTerminalSession} constructor
        @type logger: L{X2GoLogger} instance
        @param loglevel: if no L{X2GoLogger} object has been supplied a new one will be
            constructed with the given loglevel
        @type loglevel: C{int}

        """
        self.proxy = None
        self.proxy_subprocess = None
        self.proxy_options = proxy_options

        self.telekinesis_client = None

        self.active_threads = []
        self.reverse_tunnels = {}

        self.print_queue = None
        self.mimebox_queue = None

        if logger is None:
            self.logger = log.X2GoLogger(loglevel=loglevel)
        else:
            self.logger = copy.deepcopy(logger)
        self.logger.tag = __NAME__

        self.control_session = control_session
        self.reverse_tunnels = self.control_session.get_transport().reverse_tunnels

        self.client_rootdir = client_rootdir
        self.sessions_rootdir = sessions_rootdir

        self.params = X2GoSessionParams()

        self.params.geometry = str(geometry)
        self.params.link = str(link)
        self.params.pack = str(pack)
        self.params.dpi = str(dpi)
        self.params.cache_type = str(cache_type)
        self.params.session_type = str(session_type)
        self.params.kbtype = str(kbtype)
        self.params.kblayout = str(kblayout)
        self.params.kbvariant = str(kbvariant)
        self.params.snd_system = str(snd_system)
        self.params.cmd = str(cmd)
        self.params.depth = str(depth)
        self.params.clipboard = str(clipboard)

        self.params.published_applications = published_applications
        self.published_applications = published_applications

        self.params.rdp_server = str(rdp_server)
        self.params.rdp_options = str(rdp_options)
        self.params.xdmcp_server = str(xdmcp_server)

        self.params.convert_encoding = convert_encoding
        self.params.client_encoding = str(client_encoding)
        self.params.server_encoding = str(server_encoding)

        self.params.rootdir = (type(rootdir) is types.StringType) and rootdir or self.sessions_rootdir
        self.params.update()

        self.profile_name = profile_name
        self.set_session_title = set_session_title
        self.session_title = session_title
        self.session_window = None
        self.proxy_backend = utils._get_backend_class(proxy_backend, "X2GoProxy")

        self.snd_port = snd_port
        self.print_action = print_action
        self.print_action_args = print_action_args
        self.printing_backend = utils._get_backend_class(printing_backend, "X2GoClientPrinting")
        self.session_instance = session_instance
        if self.session_instance:
            self.client_instance = self.session_instance.client_instance
        else:
            self.client_instance = None

        self._share_local_folder_busy = False
        self._mk_sessions_rootdir(self.params.rootdir)

        self.session_info = session_info
        if self.session_info is not None:
            if self.session_info.name:
                self.session_info.local_container = os.path.join(self.params.rootdir, 'S-%s' % self.session_info.name)
            else:
                raise x2go_exceptions.X2GoTerminalSessionException('no valid session info availble')
        else:
            self.session_info = info_backend()

        self._share_local_folder_lock = threading.Lock()
        self._cleaned_up = False

        self.telekinesis_subprocess = None

    def __del__(self):
        """\
        Tidy up if terminal session gets destructed.

        """
        self._x2go_tidy_up()

    def _x2go_tidy_up(self):
        """\
        Tidy up this terminal session...
          - shutdown all forwarding and reverse forwarding tunnels
          - shutdown the print queue (if running)
          - shutdown the MIME box queue (if running)
          - clear the session info

        """
        self._share_local_folder_lock.release()
        self.release_telekinesis()
        self.release_proxy()
        self.session_window = None
        self.update_session_window_file()

        try:

            if self.control_session.get_transport() is not None:
                try:
                    for _tunnel in [ _tun[1] for _tun in self.reverse_tunnels[self.session_info.name].values() ]:
                        if _tunnel is not None:
                            _tunnel.__del__()
                except KeyError:
                    pass

            if self.print_queue is not None:
                self.print_queue.__del__()

            if self.mimebox_queue is not None:
                self.mimebox_queue.__del__()

        except AttributeError:
            pass

        self.session_info.clear()

    def _mk_sessions_rootdir(self, rootdir):
        """\
        Create the server-side session root dir (normally ~/.x2go).

        @param rootdir: server-side session root directory
        @type rootdir: C{str}

        """
        try:
            os.makedirs(rootdir)
        except OSError, e:
            if e.errno == 17:
                # file exists
                pass
            else:
                raise OSError, e

    def _rm_session_dirtree(self):
        """\
        Purge client-side session dir (session cache directory).

        """
        if self.session_info.name:
            shutil.rmtree('%s/S-%s' % (self.params.rootdir, self.session_info), ignore_errors=True)

    def _rm_desktop_dirtree(self):
        """\
        Purge client-side session dir (C-<display> directory)

        """
        if self.session_info.display:
            shutil.rmtree('%s/S-%s' % (self.params.rootdir, self.session_info.display), ignore_errors=True)

    def get_session_name(self):
        """\
        Retrieve the X2Go session's name from the session info object.

        @return: the session name
        @rtype: C{str}

        """
        return self.session_info.name

    def get_session_info(self):
        """\
        Retrieve the X2Go session's session info object.

        @return: the session info object
        @rtype: C{X2GoServerSessionInfo*}

        """
        return self.session_info

    def get_session_cmd(self):
        """\
        Retrieve the X2Go session's command as stored in the session parameter object.

        @return: the session command
        @rtype: C{str}

        """
        return self.params.cmd

    def get_session_type(self):
        """\
        Retrieve the X2Go session's session type as stored in the session parameter object.

        @return: the session type
        @rtype: C{str}

        """
        return self.params.session_type

    def start_sound(self):
        """\
        Initialize Paramiko/SSH reverse forwarding tunnel for X2Go sound.

        Currently supported audio protocols:

            - PulseAudio
            - Esound (not tested very much)

        @raise X2GoControlSessionException: if the control session of this terminal session is not connected

        """
        _tunnel = None
        if self.reverse_tunnels[self.session_info.name]['snd'][1] is None:
            if self.params.snd_system == 'pulse':
                self.logger('initializing PulseAudio sound support in X2Go session', loglevel=log.loglevel_INFO)
                ###
                ### PULSEAUDIO
                ###
                cookie_filepath = None
                if os.path.exists(os.path.normpath('%s/.pulse-cookie' % _LOCAL_HOME)):
                    cookie_filepath = os.path.normpath('%s/.pulse-cookie' % _LOCAL_HOME)
                elif os.path.exists(os.path.normpath('%s/.config/pulse/cookie' % _LOCAL_HOME)):
                    cookie_filepath = os.path.normpath('%s/.config/pulse/cookie' % _LOCAL_HOME)
                if cookie_filepath is not None:
                    # setup pulse client config file on X2Go server
                    cmd_line = "echo 'default-server=127.0.0.1:%s'>%s/.pulse-client.conf;" % (self.session_info.snd_port, self.session_info.remote_container) + \
                               "echo 'cookie-file=%s/.pulse-cookie'>>%s/.pulse-client.conf" % (self.session_info.remote_container, self.session_info.remote_container)
                    (stdin, stdout, stderr) = self.control_session._x2go_exec_command(cmd_line)

                    self.control_session._x2go_sftp_put(local_path=cookie_filepath, remote_path='%s/.pulse-cookie' % self.session_info.remote_container)

                    # start reverse SSH tunnel for pulse stream
                    _tunnel = rforward.X2GoRevFwTunnel(server_port=self.session_info.snd_port, 
                                                       remote_host='127.0.0.1', 
                                                       remote_port=self.snd_port, 
                                                       ssh_transport=self.control_session.get_transport(),
                                                       session_instance=self.session_instance,
                                                       logger=self.logger
                                                      )
                else:
                    if self.client_instance:
                        self.client_instance.HOOK_on_sound_tunnel_failed(profile_name=self.profile_name, session_name=self.session_info.name)
            elif self.params.snd_system == 'arts':
                ###
                ### ARTSD AUDIO
                ###
                self.logger('the ArtsD sound server (as in KDE3) is obsolete and will not be supported by Python X2Go...', loglevel=log.loglevel_WARNING)

            elif self.params.snd_system == 'esd':
                ###
                ### ESD AUDIO
                ###

                self.logger('initializing ESD sound support in X2Go session', loglevel=log.loglevel_INFO)
                self.control_session._x2go_sftp_put(local_path='%s/.esd_auth' % _LOCAL_HOME, remote_path='%s/.esd_auth' % self.control_session._x2go_remote_home)

                # start reverse SSH tunnel for pulse stream
                _tunnel = rforward.X2GoRevFwTunnel(server_port=self.session_info.snd_port, 
                                                   remote_host='127.0.0.1', 
                                                   remote_port=self.snd_port, 
                                                   ssh_transport=self.control_session.get_transport(),
                                                   session_instance=self.session_instance,
                                                   logger=self.logger
                                                  )


            if _tunnel is not None:
                self.reverse_tunnels[self.session_info.name]['snd'] = (self.session_info.snd_port, _tunnel)
                _tunnel.start()
                self.active_threads.append(_tunnel)

        else:
            # tunnel has already been started and might simply need a resume call
            self.reverse_tunnels[self.session_info.name]['snd'][1].resume()

    def start_sshfs(self):
        """\
        Initialize Paramiko/SSH reverse forwarding tunnel for X2Go folder sharing.

        """
        self.logger('Not checking FUSE membership for user!!!', loglevel=log.loglevel_INFO)
        #if not self.control_session.is_sshfs_available():
        #    raise x2go_exceptions.X2GoUserException('Remote user %s is not allowed to share SSHFS resources with the server.' % self.session_info.username)

        # start reverse SSH tunnel for sshfs (folder sharing, printing)
        ssh_transport = self.control_session.get_transport()
        if self.reverse_tunnels[self.session_info.name]['sshfs'][1] is None:

            _tunnel = sftpserver.X2GoRevFwTunnelToSFTP(server_port=self.session_info.sshfs_port,
                                                       ssh_transport=ssh_transport,
                                                       auth_key=self.control_session._x2go_session_auth_rsakey,
                                                       session_instance=self.session_instance,
                                                       logger=self.logger
                                                      )

            if _tunnel is not None:
                self.reverse_tunnels[self.session_info.name]['sshfs'] = (self.session_info.sshfs_port, _tunnel)
                _tunnel.start()
                self.active_threads.append(_tunnel)
                while not _tunnel.ready:
                    gevent.sleep(.1)

        else:
            # tunnel has already been started and might simply need a resume call
            self.reverse_tunnels[self.session_info.name]['sshfs'][1].resume()

    def _x2go_pause_rev_fw_tunnel(self, name):
        """\
        Pause reverse SSH tunnel of name <name>.

        @param name: tunnel name (either of C{sshfs}, C{snd})
        @type name: C{str}

        """
        _tunnel = self.reverse_tunnels[self.session_info.name][name][1]
        if _tunnel is not None:
            _tunnel.pause()

    def stop_sound(self):
        """\
        Shutdown (pause) Paramiko/SSH reverse forwarding tunnel for X2Go sound.

        """
        self._x2go_pause_rev_fw_tunnel('snd')

    def stop_sshfs(self):
        """\
        Shutdown (pause) Paramiko/SSH reverse forwarding tunnel for X2Go folder sharing.

        """
        self._x2go_pause_rev_fw_tunnel('sshfs')

    def start_printing(self):
        """\
        Initialize X2Go print spooling.

        @raise X2GoUserException: if the X2Go printing feature is not available to this user

        """
        if not self.control_session.is_sshfs_available():
            raise x2go_exceptions.X2GoUserException('Remote user %s is not allowed to use client-side printing.' % self.session_info.username)

        spool_dir = os.path.join(self.session_info.local_container, 'spool')
        if not os.path.exists(spool_dir):
            os.makedirs(spool_dir)
        self.share_local_folder(local_path=spool_dir, folder_type='spool')
        self.print_queue = printqueue.X2GoPrintQueue(profile_name=self.profile_name,
                                                     session_name=self.session_info.name,
                                                     spool_dir=spool_dir,
                                                     print_action=self.print_action, 
                                                     print_action_args=self.print_action_args,
                                                     client_instance=self.client_instance,
                                                     printing_backend=self.printing_backend,
                                                     logger=self.logger,
                                                    )
        self.print_queue.start()
        self.active_threads.append(self.print_queue)

    def set_print_action(self, print_action, **kwargs):
        """\
        Set a print action for the next incoming print jobs.

        This method is a wrapper for L{X2GoPrintQueue}C{.set_print_action()}.

        @param print_action: print action name or object (i.e. an instance of C{X2GoPrintAction*} classes)
        @type print_action: C{str} or C{X2GoPrintAction*}
        @param kwargs: print action specific parameters
        @type kwargs: dict

        """
        self.print_queue.set_print_action(print_action, logger=self.logger, **kwargs)

    def stop_printing(self):
        """\
        Shutdown (pause) the X2Go Print Queue thread.

        """
        if self.print_queue is not None:
            self.print_queue.pause()

    def get_printing_spooldir(self):
        """\
        Return the server-side printing spooldir path.

        @return: the directory for remote print job spooling
        @rtype: C{str}

        """
        return '%s/%s' % (self.session_info.remote_container, 'spool')

    def start_mimebox(self, mimebox_extensions=[], mimebox_action=None):
        """\
        Initialize the X2Go MIME box. Open/process incoming files from the server-side locally.

        @param mimebox_extensions: file name extensions that are allowed for local opening/processing
        @type mimebox_extensions: C{list}
        @param mimebox_action: MIME box action given as name or object (i.e. an instance of C{X2GoMIMEboxAction*} classes).
        @type mimebox_action: C{str} or C{obj}

        @raise X2GoUserException: if the X2Go MIME box feature is not available to this user

        """
        if not self.control_session.is_sshfs_available():
            raise x2go_exceptions.X2GoUserException('Remote user %s is not allowed to use the MIME box.' % self.session_info.username)

        mimebox_dir = os.path.join(self.session_info.local_container, 'mimebox')
        if not os.path.exists(mimebox_dir):
            os.makedirs(mimebox_dir)
        self.share_local_folder(local_path=mimebox_dir, folder_type='mimebox')
        self.mimebox_queue = mimebox.X2GoMIMEboxQueue(profile_name=self.profile_name,
                                                      session_name=self.session_info.name,
                                                      mimebox_dir=mimebox_dir,
                                                      mimebox_extensions=mimebox_extensions,
                                                      mimebox_action=mimebox_action,
                                                      client_instance=self.client_instance,
                                                      logger=self.logger,
                                                     )
        self.mimebox_queue.start()
        self.active_threads.append(self.mimebox_queue)

    def set_mimebox_action(self, mimebox_action, **kwargs):
        """\
        Set a MIME box action for the next incoming MIME jobs.

        This method is a wrapper for L{X2GoMIMEboxQueue}C{set_mimebox_action()}.

        @param mimebox_action: MIME box action name or object (i.e. an instance of C{X2GoMIMEboxAction*} classes)
        @type mimebox_action: C{str} or C{X2GoMIMEboxAction*}
        @param kwargs: MIME box action specific parameters
        @type kwargs: dict

        """
        self.mimebox_queue.set_mimebox_action(mimebox_action, logger=self.logger, **kwargs)

    def stop_mimebox(self):
        """\
        Shutdown (pause) the X2Go MIME box Queue thread.

        """
        if self.mimebox_queue is not None:
            self.mimebox_queue.pause()

    def get_mimebox_spooldir(self):
        """\
        Return the server-side MIME box spooldir path.

        @return: the directory where remote MIME box jobs are placed
        @rtype: C{str}

        """
        return '%s/%s' % (self.session_info.remote_container, 'mimebox')

    def start_telekinesis(self):
        """\
        Initialize Telekinesis client for X2Go.

        """
        if self.telekinesis_client is not None:
            del self.telekinesis_client
            self.telekinesis_client = None
        if self.telekinesis_subprocess is not None:
            self.telekinesis_subprocess = None
        if self.session_info.tekictrl_port != -1 and self.session_info.tekidata_port != -1:
            self.telekinesis_client = telekinesis.X2GoTelekinesisClient(session_info=self.session_info,
                                                                        ssh_transport=self.control_session.get_transport(),
                                                                        sessions_rootdir=self.sessions_rootdir,
                                                                        session_instance=self.session_instance,
                                                                        logger=self.logger)
            if self.telekinesis_client.has_telekinesis_client():
                self.telekinesis_subprocess, telekinesis_ok = self.telekinesis_client.start_telekinesis()
            else:
                del self.telekinesis_client
                self.telekinesis_client = None

    def is_session_info_protected(self):
        """\
        Test if this terminal's session info object is write-protected.

        @return: C{True}, if session info object is read-only, C{False} for read-write.
        @rtype: C{bool}

        """
        self.session_info.is_protected()

    def session_info_protect(self):
        """\
        Protect this terminal session's info object against updates.

        """
        self.session_info.protect()

    def session_info_unprotect(self):
        """\
        Allow session info updates from within the list_sessions method of the control session.

        """
        self.session_info.unprotect()

    def share_local_folder(self, local_path=None, folder_type='disk'):
        """\
        Share a local folder with the X2Go session.

        @param local_path: the full path to an existing folder on the local 
            file system
        @type local_path: C{str}
        @param folder_type: one of 'disk' (a folder on your local hard drive), 'rm' (removeable device), 
            'cdrom' (CD/DVD Rom) or 'spool' (for X2Go print spooling)
        @type folder_type: C{str}

        @return: returns C{True} if the local folder has been successfully mounted within the X2Go server session
        @rtype: C{bool}

        @raise X2GoUserException: if local folder sharing is not available to this user
        @raise Exception: any other exception occuring on the way is passed through by this method

        """
        if not self.control_session.is_sshfs_available():
            raise x2go_exceptions.X2GoUserException('Remote user %s is not allowed to share local folders with the server.' % self.session_info.username)

        if local_path is None:
            self.logger('no folder name given...', log.loglevel_WARN)
            return False

        if type(local_path) not in (types.StringType, types.UnicodeType):
            self.logger('folder name needs to be of type StringType...', log.loglevel_WARN)
            return False

        if not os.path.exists(local_path):
            self.logger('local folder does not exist: %s' % local_path, log.loglevel_WARN)
            return False

        local_path = os.path.normpath(local_path)
        self.logger('sharing local folder: %s' % local_path, log.loglevel_INFO)

        _auth_rsakey = self.control_session._x2go_session_auth_rsakey
        _host_rsakey = defaults.RSAHostKey

        _tmp_io_object = cStringIO.StringIO()
        _auth_rsakey.write_private_key(_tmp_io_object)
        _tmp_io_object.write('----BEGIN RSA IDENTITY----')
        _tmp_io_object.write('%s %s' % (_host_rsakey.get_name(),_host_rsakey.get_base64(),))

        # _x2go_key_fname must be a UniX path
        _x2go_key_fname = '%s/%s/%s' % (os.path.dirname(self.session_info.remote_container), 'ssh', 'key.z%s' % self.session_info.agent_pid)
        _x2go_key_bundle = _tmp_io_object.getvalue()

        # if there is another call to this method currently being processed, wait for that one to finish
        self._share_local_folder_lock.acquire()

        try:
            self.control_session._x2go_sftp_write(_x2go_key_fname, _x2go_key_bundle)

            _convert_encoding = self.params.convert_encoding
            _client_encoding = self.params.client_encoding
            _server_encoding = self.params.server_encoding

            if _X2GOCLIENT_OS == 'Windows':
                if local_path.startswith('\\\\'):
                    # we are on a UNC path
                    if 'X2GO_MOUNT_UNCPATHS' in self.control_session.get_server_features():
                        local_path = local_path.repalce('\\\\', '/uncpath/')
                    else:
                        local_path = local_path.repalce('\\\\', '/windrive/')
                    local_path = local_path.replace('\\', '/')
                else:
                    local_path = local_path.replace('\\', '/')
                    local_path = local_path.replace(':', '')
                    local_path = '/windrive/%s' % local_path
                _convert_encoding = True
                _client_encoding = 'WINDOWS-1252'

            if _convert_encoding:
                export_iconv_settings = 'export X2GO_ICONV=modules=iconv,from_code=%s,to_code=%s && ' % (_client_encoding, _server_encoding)
            else:
                export_iconv_settings = ''

            if folder_type == 'disk':

                cmd_line = [ '%sexport HOSTNAME &&' % export_iconv_settings,
                             'x2gomountdirs',
                             'dir',
                             str(self.session_info.name),
                             '\'%s\'' % _CURRENT_LOCAL_USER,
                             _x2go_key_fname,
                             '%s__REVERSESSH_PORT__%s; ' % (local_path, self.session_info.sshfs_port),
                             'rm -f %s %s.ident' % (_x2go_key_fname, _x2go_key_fname),
                           ]

            elif folder_type == 'spool':

                cmd_line = [ '%sexport HOSTNAME &&' % export_iconv_settings,
                             'x2gomountdirs',
                             'dir',
                             str(self.session_info.name),
                             '\'%s\'' % _CURRENT_LOCAL_USER,
                             _x2go_key_fname,
                             '%s__PRINT_SPOOL___REVERSESSH_PORT__%s; ' % (local_path, self.session_info.sshfs_port),
                             'rm -f %s %s.ident' % (_x2go_key_fname, _x2go_key_fname), 
                           ]

            elif folder_type == 'mimebox':

                cmd_line = [ '%sexport HOSTNAME &&' % export_iconv_settings,
                             'x2gomountdirs',
                             'dir',
                             str(self.session_info.name),
                             '\'%s\'' % _CURRENT_LOCAL_USER,
                             _x2go_key_fname,
                             '%s__MIMEBOX_SPOOL___REVERSESSH_PORT__%s; ' % (local_path, self.session_info.sshfs_port),
                             'rm -f %s %s.ident' % (_x2go_key_fname, _x2go_key_fname), 
                           ]

            (stdin, stdout, stderr) = self.control_session._x2go_exec_command(cmd_line)
            _stdout = stdout.read().split('\n')
            self.logger('x2gomountdirs output is: %s' % _stdout, log.loglevel_NOTICE)

        except:
            self._share_local_folder_lock.release()
            raise
        self._share_local_folder_lock.release()

        if len(_stdout) >= 6 and _stdout[5].endswith('ok'):
            return True
        return False

    def unshare_all_local_folders(self):
        """\
        Unshare all local folders mount in the X2Go session.

        @return: returns C{True} if all local folders could be successfully unmounted from the X2Go server session
        @rtype: C{bool}

        """
        self.logger('unsharing all local folders from session %s' % self.session_info, log.loglevel_INFO)

        cmd_line = [ 'export HOSTNAME &&',
                     'x2goumount-session', 
                     self.session_info.name,
                   ]

        (stdin, stdout, stderr) = self.control_session._x2go_exec_command(cmd_line)
        if not stderr.read():
            self.logger('x2goumount-session (all mounts) for session %s has been successful' % self.session_info, log.loglevel_NOTICE)
            return True
        else:
            self.logger('x2goumount-session (all mounts) for session %s failed' % self.session_info, log.loglevel_ERROR)
            return False

    def unshare_local_folder(self, local_path):
        """\
        Unshare local folder given as <local_path> from X2Go session.

        @return: returns C{True} if the local folder <local_path> could be successfully unmounted from the X2Go server session
        @rtype: C{bool}

        """
        self.logger('unsharing local folder from session %s' % self.session_info, log.loglevel_INFO)

        cmd_line = [ 'export HOSTNAME &&',
                     'x2goumount-session', 
                     self.session_info.name,
                     "'%s'" % local_path,
                   ]

        (stdin, stdout, stderr) = self.control_session._x2go_exec_command(cmd_line)
        if not stderr.read():
            self.logger('x2goumount-session (%s) for session %s has been successful' % (local_path, self.session_info, ), log.loglevel_NOTICE)
            return True
        else:
            self.logger('x2goumount-session (%s) for session %s failed' % (local_path, self.session_info, ), log.loglevel_ERROR)
            return False

    def color_depth(self):
        """\
        Retrieve the session's color depth.

        @return: the session's color depth
        @rtype: C{int}

        """
        return self.params.depth

    def auto_session_window_title(self, dont_set=False):
        """\
        Automatically generate an appropriate human-readable session window title.

        The session window title will be provider in the C{session_title} property of
        this method.

        @param dont_set: generate the session window title, but do not actually set it
        @type dont_set: C{bool}

        """
        _generic_title = 'X2GO-%s' % self.session_info.name

        # no blanks at beginning or end, no blanks-only...
        self.session_title = self.session_title.strip()

        if self.params.session_type == 'D':
            if self.set_session_title:

                if not self.session_title:
                    self.session_title = '%s for %s@%s' % (self.params.cmd, self.control_session.remote_username(), self.control_session.get_hostname())

            else:
                # session title fallback... (like X2Go server does it...)
                self.session_title = _generic_title

        elif self.params.session_type == 'S':
            if self.set_session_title:

                shared_user = _generic_title.split('XSHAD')[1]
                shared_display = _generic_title.split('XSHAD')[2].replace('PP', ':').split("_")[0]

                self.session_title = 'Desktop %s@%s shared with %s@%s' % (shared_user, shared_display, self.control_session.remote_username(), self.control_session.get_hostname())

            else:
                # session title fallback... (like X2Go server does it...)
                self.session_title = _generic_title

        else:
            # do nothing for rootless sessions
            self.session_title = _generic_title

        if self.session_title != _generic_title and not dont_set:
            self.set_session_window_title(title=self.session_title)

    def find_session_window(self, timeout=60):
        """\
        Try for <timeout> seconds to find the X2Go session window of this
        terminal session.

        A background thread will get spawned for this operation.

        @param timeout: try for <timeout> seconds to find the session window
        @type timeout: C{int}

        """
        gevent.spawn(self._find_session_window, timeout=timeout)

    def _find_session_window(self, timeout=0):
        """\
        Try for <timeout> seconds to find the X2Go session window of this
        terminal session.

        @param timeout: try for <timeout> seconds to find the session window
        @type timeout: C{int}

        """
        self.session_window = None

        # search for the window of our focus, do this in a loop till the window as been found
        # or timeout forces us to give up...
        timeout += 1
        while timeout:

            timeout -= 1

            window = utils.find_session_window(self.session_info.name)

            if window is not None:
                if _X2GOCLIENT_OS == "Windows":
                    self.logger('Session window handle for session %s is: %s' % (self.session_info.name, window), loglevel=log.loglevel_DEBUG)
                else:
                    self.logger('Session window ID for session %s is: %s' % (self.session_info.name, window.id), loglevel=log.loglevel_DEBUG)
                self.session_window = window

                self.update_session_window_file()
                break

            gevent.sleep(1)

    def update_session_window_file(self):
        """\
        Create a file that contains information on the session window.
        .
        If the file already exists, its content gets update.

        """
        session_window_file = os.path.join(self.session_info.local_container, 'session.window')
        if self.session_window is not None:
            f = open(session_window_file,'w')
            if _X2GOCLIENT_OS != "Windows":
                _id = self.session_window.id
            else:
                _id = self.session_window
            f.write('ID:{window_id}\n'.format(window_id=_id))
            f.close()
            self.logger('Updating session.window file %s: Window-ID->%s' % (session_window_file, _id), loglevel=log.loglevel_DEBUG)
        else:
            try:
                os.remove(session_window_file)
            except OSError,e:
                # this is no error in most cases...
                self.logger('The session window file %s is already gone (we failed to remove it with error: %s). In most cases this can be safely ignored.' % (session_window_file, str(e)), loglevel=log.loglevel_INFO)

    def set_session_window_title(self, title, timeout=60):
        """\
        Modify the session window title.

        A background thread will get spawned for this operation.

        @param title: new title for the terminal session's session window
        @type title: C{str}
        @param timeout: try for <timeout> seconds to find the session window
        @type timeout: C{int}

        """
        gevent.spawn(self._set_session_window_title, title=title.strip(), timeout=timeout)

    def _set_session_window_title(self, title, timeout=0):
        """\
        Modify the session window title.

        @param title: new title for the terminal session's session window
        @type title: C{str}
        @param timeout: try for <timeout> seconds to find the session window
        @type timeout: C{int}

        """
        self.session_title = title

        if not self.session_title:
            self.auto_session_title(dont_set=True)

        timeout += 1
        while timeout:

            timeout -= 1

            if self.session_window is not None:
                self.logger('Setting session window title for session %s is: %s' % (self.session_info.name, self.session_title), loglevel=log.loglevel_DEBUG)
                utils.set_session_window_title(self.session_window, self.session_title)
                break

            gevent.sleep(1)

    def raise_session_window(self, timeout=60):
        """\
        Try for <timeout> seconds to raise the X2Go session window of this
        terminal session to the top and bring it to focus.

        A background thread will get spawned for this operation.

        @param timeout: try for <timeout> seconds to raise the session window
        @type timeout: C{int}

        """
        gevent.spawn(self._raise_session_window, timeout=timeout)

    def _raise_session_window(self, timeout=0):
        """
        Try for <timeout> seconds to raise the X2Go session window of this
        terminal session to the top and bring it to focus.

        @param timeout: try for <timeout> seconds to raise the session window
        @type timeout: C{int}

        """
        timeout += 1
        while timeout:

            timeout -= 1

            if self.session_window is not None:

                utils.raise_session_window(self.session_window)
                break

            gevent.sleep(1)

    def has_command(self, cmd):
        """\
        ,,Guess'' if the command C{<cmd>} exists on the X2Go server and is executable.
        The expected result is not 100% safe, however, it comes with a high probability to
        be correct.

        @param cmd: session command
        @type cmd: C{str}

        @return: C{True} if this method reckons that the command is executable on the remote X2Go server
        @rtype: C{bool}

        """
        test_cmd = None;

        cmd = cmd.strip('"').strip('"')
        if cmd.find('RDP') != -1:
            cmd = 'rdesktop'

        if cmd in _X2GO_GENERIC_APPLICATIONS:
            return True
        if cmd in _X2GO_DESKTOPSESSIONS.keys():
            return True
        elif 'XSHAD' in cmd:
            return True
        elif 'PUBLISHED' in cmd and 'X2GO_PUBLISHED_APPLICATIONS' in self.control_session.get_server_features():
            return True
        elif cmd and cmd.startswith('/'):
            # check if full path is correct _and_ if application is in server path
            test_cmd = 'test -x %s && which %s && echo OK' % (cmd, os.path.basename(cmd.split()[0]))
        elif cmd and '/' not in cmd.split()[0]:
            # check if application is in server path only
            test_cmd = 'which %s && echo OK' % os.path.basename(cmd.split()[0])

        if test_cmd:
            (stdin, stdout, stderr) = self.control_session._x2go_exec_command([test_cmd])
            _stdout = stdout.read()
            return _stdout.find('OK') != -1
        else:
            return False

    def run_command(self, cmd=None, env={}):
        """\
        Run a command in this session.

        After L{x2go.backends.terminal.plain.X2GoTerminalSession.start()} has been called 
        one or more commands can be executed with L{x2go.backends.terminal.plain.X2GoTerminalSession.run_command()}
        within the current X2Go session.

        @param cmd: Command to be run
        @type cmd: C{str}
        @param env: add server-side environment variables
        @type env: C{dict}

        @return: stdout.read() and stderr.read() as returned by the run command
            on the X2Go server
        @rtype: C{tuple} of C{str}

        """
        self.logger('====>Entering run_command...', loglevel=log.loglevel_DEBUG)
        if not self.has_command(_rewrite_cmd(str(self.params.cmd), params=self.params)):
            if self.client_instance:
                self.client_instance.HOOK_no_such_command(profile_name=self.profile_name, session_name=self.session_info.name, cmd=self.params.cmd)
            return False

        if cmd in ("", None):
            if self.params.cmd is None:
                cmd = 'TERMINAL'
            else:
                cmd = self.params.cmd

        if cmd == 'XDMCP':
            # do not run command when in XDMCP mode...
            return None

        if 'XSHAD' in cmd:
            # do not run command when in DESKTOP SHARING mode...
            return None

        self.params.update(cmd=cmd)

        # do not allow the execution of full path names
        if '/' in cmd:
            cmd = os.path.basename(cmd)

        cmd_line = [ "setsid x2goruncommand", 
                     str(self.session_info.display),
                     str(self.session_info.agent_pid),
                     str(self.session_info.name), 
                     str(self.session_info.snd_port),
                     _rewrite_blanks(_rewrite_cmd(cmd, params=self.params)),
                     str(self.params.snd_system),
                     str(self.params.session_type),
                     "1>/dev/null 2>/dev/null & exit",
                   ]

        if self.params.snd_system == 'pulse':
            cmd_line = [ 'PULSE_CLIENTCONFIG=%s/.pulse-client.conf' % self.session_info.remote_container ] + cmd_line

        if env:
            for env_var in env.keys():
                cmd_line = [ '%s=%s' % (env_var, env[env_var]) ] + cmd_line

        (stdin, stdout, stderr) = self.control_session._x2go_exec_command(cmd_line)

        if self.params.kbtype not in ('null/null', 'auto') and (self.params.kblayout not in ('null', '') or self.params.kbvariant not in ('null', '')):
            self.set_keyboard(layout=self.params.kblayout, variant=self.params.kbvariant)

        self.logger('====>Returning from run_command...', loglevel=log.loglevel_DEBUG)
        return stdout.read(), stderr.read()

    def is_desktop_session(self):
        """\
        Is this (terminal) session a desktop session?

        @return: Returns C{True} is this session is a desktop session.
        @rtype: C{bool}

        """
        if self.session_info:
            return self.session_info.is_desktop_session()
        return False

    def is_published_applications_provider(self):
        """\
        Is this (terminal) session a published applications provider?

        @return: Returns C{True} is this session is a provider session for published applications.
        @rtype: C{bool}

        """
        if self.session_info and self.is_running():
            return self.session_info.is_published_applications_provider()
        return False

    def set_keyboard(self, layout='null', variant='null'):
        """\
        Set the keyboard layout and variant for this (running) session.

        @param layout: keyboard layout to be set
        @type layout: C{str}
        @param variant: keyboard variant to be set
        @type variant: C{str}

        @return: returns C{True} if the {setxkbmap} command could be executed successfully.
        @rtype: C{bool}

        """
        if not self.is_running():
            return False

        cmd_line = [ 'export DISPLAY=:%s && ' % str(self.session_info.display),
                     'setxkbmap '
                   ]

        if layout != 'null':
            self.logger('setting keyboad layout ,,%s\'\' for session %s' % (layout, self.session_info), log.loglevel_INFO)
            cmd_line.append('-layout %s' % layout)
        if variant != 'null':
            self.logger('setting keyboad variant ,,%s\'\' for session %s' % (variant, self.session_info), log.loglevel_INFO)
            cmd_line.append('-variant %s' % variant)

        (stdin, stdout, stderr) = self.control_session._x2go_exec_command(cmd_line)
        _stderr = stderr.read()
        if not _stderr:
            self.logger('setting keyboard layout ,,%s\'\' and variant ,,%s\'\' for session %s has been successful' % (layout, variant, self.session_info), log.loglevel_NOTICE)
            return True
        else:
            self.logger('setting keyboard layout ,,%s\'\' and variant ,,%s\'\' for session %s failed: %s' % (layout, variant, self.session_info, _stderr.replace('\n', ' ')), log.loglevel_ERROR)
            return False

    def exec_published_application(self, exec_name, timeout=20, env={}):
        """\
        Executed a published application.

        @param exec_name: application to be executed
        @type exec_name: C{str}
        @param timeout: execution timeout
        @type timeout: C{int}
        @param env: session environment dictionary
        @type env: C{dict}

        """
        cmd_line = [
            "export DISPLAY=:%s && " % str(self.session_info.display),
            "export X2GO_SESSION=%s && " % str(self.get_session_name()),
        ]

        if self.params.snd_system == 'pulse':
            cmd_line.append("export PULSE_CLIENTCONFIG=%s/.pulse-client.conf && " % self.session_info.remote_container)

        if env:
            for env_var in env.keys():
                cmd_line = [ 'export %s=%s && ' % (env_var, env[env_var]) ] + cmd_line

        cmd_line.extend(
            [
                "setsid %s" % exec_name,
                "1>/dev/null 2>/dev/null & exit",
            ]
        )

        self.logger('executing published application %s for %s with command line: %s' % (exec_name, self.profile_name, cmd_line), loglevel=log.loglevel_DEBUG)
        (stdin, stdout, stderr) = self.control_session._x2go_exec_command(cmd_line, timeout=timeout)

    def ok(self):
        """\
        X2Go session OK?

        @return: Returns C{True} if this X2Go (terminal) session is up and running,
            C{False} otherwise.
        @rtype: C{bool}

        """
        _ok = bool(self.session_info.name and self.proxy.ok())
        return _ok

    def is_running(self):
        """\
        X2Go session running?

        @return: Returns C{True} if this X2Go (terminal) session is in running state,
            C{False} otherwise.
        @rtype: C{bool}

        """
        return self.session_info.is_running()

    def is_suspended(self):
        """\
        X2Go session suspended?

        @return: Returns C{True} if this X2Go (terminal) session is in suspended state,
            C{False} otherwise.
        @rtype: C{bool}

        """
        return self.session_info.is_suspended()

    def is_connected(self):
        """\
        X2Go session connected?

        @return: Returns C{True} if this X2Go session's Paramiko/SSH transport is 
            connected/authenticated, C{False} else.
        @rtype: C{bool}

        """
        return self.control_session.is_connected()

    def start(self):
        """\
        Start a new X2Go session.

        @return: C{True} if session startup has been successful and the X2Go proxy is up-and-running
        @rtype: C{bool}

        @raise X2GoTerminalSessionException: if the session startup failed
        @raise X2GoDesktopSharingDenied: if desktop sharing fails because of denial by the user running the desktop to be shared

        """
        self.params.rewrite_session_type()

        if not self.has_command(_rewrite_cmd(self.params.cmd, params=self.params)):
            if self.client_instance:
                self.client_instance.HOOK_no_such_command(profile_name=self.profile_name, session_name=self.session_info.name, cmd=self.params.cmd)
            return False

        setkbd = "0"
        if self.params.kbtype != "null/null":
            setkbd = "1"

        if '/' in self.params.cmd:
            self.params.cmd = os.path.basename(self.params.cmd)

        self.params.rewrite_session_type()

        if self.params.geometry == 'maximize':
            _geometry = utils.get_workarea_geometry()
            if _geometry is None or len(_geometry) != 2:
                _geometry = utils.get_desktop_geometry()
            if _geometry and len(_geometry) == 2:
                self.params.geometry = "%sx%s" % _geometry
            else:
                self.logger('failed to detect best maximized geometry of your client-side desktop', loglevel=log.loglevel_WARN)
                self.params.geometry = "1024x768"

        cmd_line = [ "x2gostartagent",
                     str(self.params.geometry),
                     str(self.params.link),
                     str(self.params.pack),
                     str(self.params.cache_type+'-depth_'+self.params.depth),
                     str(self.params.kblayout),
                     str(self.params.kbtype),
                     str(setkbd),
                     str(self.params.session_type),
                     str(self.params.cmd),
                     str(self.params.clipboard),
                   ]

        if self.params.cmd == 'XDMCP' and self.params.xdmcp_server:
            cmd_line = ['X2GOXDMCP=%s' % self.params.xdmcp_server] + cmd_line

        if self.params.dpi:
            cmd_line = ['X2GODPI=%s' % self.params.dpi] + cmd_line

        (stdin, stdout, stderr) = self.control_session._x2go_exec_command(cmd_line)

        _stdout = stdout.read()
        _stderr = stderr.read()

        # if the first line of stdout is a "DEN(Y)" string then we will presume that
        # we tried to use X2Go desktop sharing and the sharing was rejected
        if "ACCESS DENIED" in _stderr and "XSHAD" in _stderr:
            raise x2go_exceptions.X2GoDesktopSharingDenied('X2Go desktop sharing has been denied by the remote user')

        try:
            self.session_info.initialize(_stdout,
                                         username=self.control_session.remote_username(),
                                         hostname=self.control_session.remote_peername(),
                                        )
        except ValueError:
            raise x2go_exceptions.X2GoTerminalSessionException("failed to start X2Go session")
        except IndexError:
            raise x2go_exceptions.X2GoTerminalSessionException("failed to start X2Go session")

        # local path may be a Windows path, so we use the path separator of the local system
        self.session_info.local_container = os.path.join(self.params.rootdir, 'S-%s' % self.session_info.name)
        # remote path is always a UniX path...
        self.session_info.remote_container = '%s/.x2go/C-%s' % (self.control_session._x2go_remote_home,
                                                                self.session_info.name,
                                                               )

        # set up SSH tunnel for X11 graphical elements
        self.proxy = self.proxy_backend(session_info=self.session_info, 
                                        ssh_transport=self.control_session.get_transport(),
                                        sessions_rootdir=self.sessions_rootdir,
                                        session_instance=self.session_instance,
                                        proxy_options=self.proxy_options,
                                        logger=self.logger)
        self.proxy_subprocess, proxy_ok = self.proxy.start_proxy()

        if proxy_ok:
            self.active_threads.append(self.proxy)

            if self.params.session_type in ('D', 'S'):
                self.find_session_window()
                self.auto_session_window_title()
                self.raise_session_window()

            if self.params.published_applications:
                self.control_session.get_published_applications()

        else:
            raise x2go_exceptions.X2GoTerminalSessionException("failed to start X2Go session")

        return proxy_ok

    def resume(self):
        """\
        Resume a running/suspended X2Go session. 

        @return: C{True} if the session could successfully be resumed
        @rtype: C{bool}

        @raise X2GoTerminalSessionException: if the terminal session failed to update server-side reported port changes

        """
        setkbd = "0"
        if self.params.kbtype != "null/null":
            setkbd = "1"

        if self.params.geometry == 'maximize':
            _geometry = utils.get_workarea_geometry()
            if _geometry is None or len(_geometry) != 2:
                _geometry = utils.get_desktop_geometry()
            if _geometry and len(_geometry) == 2:
                self.params.geometry = "%sx%s" % _geometry
            else:
                self.logger('failed to detect best maxmimized geometry of your client-side desktop, using 1024x768 instead', loglevel=log.loglevel_WARN)
                self.params.geometry = "1024x768"

        cmd_line = [ "x2goresume-session", self.session_info.name,
                     self.params.geometry,
                     self.params.link,
                     self.params.pack,
                     self.params.kblayout,
                     self.params.kbtype,
                     setkbd,
                     self.params.clipboard,
                   ]

        (stdin, stdout, stderr) = self.control_session._x2go_exec_command(cmd_line)

        # re-allocate (if needed) server-side ports for graphics, sound and sshfs
        for stdout_line in stdout.read():
            #self.logger('x2goresume-session output: %s' % stdout_line, loglevel=log.loglevel_INFO)
            try:
                _new_value = stdout_line.split("=")[1].strip()
                if 'gr_port=' in stdout_line and _new_value != str(self.session_info.graphics_port):
                    try:
                        self.session_info.graphics_port = int(_new_value)
                        self.logger('re-allocating graphics port for session %s, old server-side port is in use; new graphics port is %s' % (self.session_info, self.session_info.graphics_port), loglevel=log.loglevel_NOTICE)
                    except TypeError:
                        # if the re-allocation fails, this is fatal!!!
                        raise x2go_exceptions.X2GoTerminalSessionException('Failed to retrieve new graphics port from server. X2Go Session cannot be resumed.')
                elif 'sound_port=' in stdout_line and _new_value != str(self.session_info.snd_port):
                    try:
                        self.session_info.snd_port = int(_new_value)
                        self.logger('re-allocating sound port for session %s, old server-side port is in use; new sound port is %s' % (self.session_info, self.session_info.snd_port), loglevel=log.loglevel_NOTICE)
                    except TypeError:
                        self.logger('Failed to retrieve new sound port from server for session %s, session will be without sound.' % self.session_info, loglevel=log.loglevel_WARN)
                elif 'fs_port=' in stdout_line and _new_value != str(self.session_info.sshfs_port):
                    try:
                        self.session_info.sshfs_port = int(_new_value)
                        self.logger('re-allocating sshfs port for session %s, old server-side port is in use; new sshfs port is %s' % (self.session_info, self.session_info.sshfs_port), loglevel=log.loglevel_NOTICE)
                    except TypeError:
                        self.logger('Failed to retrieve new sshfs port from server for session %s, session will be without client-side folder sharing. Neither will there be X2Go printing nor X2Go MIME box support.' % self.session_info, loglevel=log.loglevel_WARN)
            except IndexError:
                continue

        # local path may be a Windows path, so we use the path separator of the local system
        self.session_info.local_container = os.path.join(self.params.rootdir, 'S-%s' % self.session_info.name)
        # remote path is always a UniX path...
        self.session_info.remote_container = '%s/.x2go/C-%s' % (self.control_session._x2go_remote_home, 
                                                                self.session_info.name,
                                                               )
        self.proxy = self.proxy_backend(session_info=self.session_info, 
                                        ssh_transport=self.control_session.get_transport(), 
                                        sessions_rootdir=self.sessions_rootdir,
                                        session_instance=self.session_instance,
                                        proxy_options=self.proxy_options,
                                        logger=self.logger
                                       )
        self.proxy_subprocess, proxy_ok = self.proxy.start_proxy()

        if proxy_ok:
            self.params.depth = self.session_info.name.split('_')[2][2:]

            # on a session resume the user name comes in as a user ID. We have to translate this...
            self.session_info.username = self.control_session.remote_username()

            if self.params.kbtype not in ('null/null', 'auto') and (self.params.kblayout not in ('null', '') or self.params.kbvariant not in ('null', '')):
                self.set_keyboard(layout=self.params.kblayout, variant=self.params.kbvariant)

            if self.params.session_type in ('D', 'S'):
                self.find_session_window()
                self.auto_session_window_title()
                self.raise_session_window()

            if self.is_published_applications_provider():
                self.control_session.get_published_applications()
                self.published_applications = True
        else:
            raise x2go_exceptions.X2GoTerminalSessionException("failed to start X2Go session")

        return proxy_ok

    def suspend(self):
        """\
        Suspend this X2Go (terminal) session.

        @return: C{True} if the session terminal could be successfully suspended
        @rtype: C{bool}

        """
        self.release_telekinesis()
        self.control_session.suspend(session_name=self.session_info.name)
        self.release_proxy()

        # TODO: check if session has really suspended
        _ret = True

        return _ret

    def terminate(self):
        """\
        Terminate this X2Go (terminal) session.

        @return: C{True} if the session could be successfully terminated
        @rtype: C{bool}

        """
        self.release_telekinesis()
        self.control_session.terminate(session_name=self.session_info.name, destroy_terminals=False)
        self.release_proxy()
        self.post_terminate_cleanup()
        self.__del__()

        # TODO: check if session has really suspended
        _ret = True

        return _ret

    def release_proxy(self):
        """\
        Let the X2Go proxy command cleanly die away... (by calling its destructor).

        """
        if self.proxy is not None:
            self.proxy.__del__()
            self.proxy = None

    def release_telekinesis(self):
        """\
        Let the attached Telekinesis client cleanly die away... (by calling its destructor).

        """
        if self.telekinesis_client is not None:
            self.telekinesis_client.__del__()
            self.telekinesis_client = None

    def post_terminate_cleanup(self):
        """\
        Do some cleanup after this session has terminated.

        """
        # this method might be called twice (directly and from update_status in the session
        # registry instance. So we have to make sure, that this code will not fail
        # if called twice.
        if not self._cleaned_up and self.session_info.name:

            # otherwise we wipe the session files locally
            self.logger('cleaning up session %s after termination' % self.session_info, loglevel=log.loglevel_NOTICE)

            # if we run in debug mode, we keep local session directories
            if self.logger.get_loglevel() & log.loglevel_DEBUG != log.loglevel_DEBUG:

                self._rm_session_dirtree()
                self._rm_desktop_dirtree()

            self._cleaned_up = True

    def is_rootless_session(self):
        """\
        Test if this terminal session is a rootless session.

        @return: C{True} if this session is of session type rootless ('R').
        @rtype: C{bool}

        """
        self.params.rewrite_session_type()
        return self.params.session_type == 'R'

    def is_shadow_session(self):
        """\
        Test if this terminal session is a desktop sharing (aka shadow) session.

        @return: C{True} if this session is of session type shadow ('S').
        @rtype: C{bool}

        """
        self.params.rewrite_session_type()
        return self.params.session_type == 'S'

    def is_pubapp_session(self):
        """\
        Test if this terminal session is a published applications session.

        @return: C{True} if this session is of session type published applications ('P').
        @rtype: C{bool}

        """
        self.params.rewrite_session_type()
        return self.params.session_type == 'P'

