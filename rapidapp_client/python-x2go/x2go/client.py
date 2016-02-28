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
L{X2GoClient} is a public API class. Use this class in your Python X2Go based 
applications.  Use it as a parent class for your own object oriented L{X2GoClient}'ish
class implementation.

Supported Features
==================
    Supported features are:

        - X2Go multi-session management
        - keep track of initiated sessions
        - grant access to X2Go client config files: C{settings}, C{printing}, C{sessions}
          and C{xconfig} (Windows only) as normally found in C{~/.x2goclient}
        - instantiate an X2Go session by a set of Python parameters
        - load a session profile from x2goclient's C{sessions} configuration file
          and start the---profile-based pre-configured---session
        - sharing of local folders with remote X2Go sessions
        - enabling and mangaging X2Go printing (real printing, viewing as PDF, saving
          to a local folder or executing a custom »print« command
        - transparent tunneling of audio (Pulseaudio, ESD)
        - sharing of other desktops
        - LDAP support for X2Go server clusters (NOT IMPLEMENTED YET)

Non-Profile Sessions
====================
    A new non-profile based X2Go session within an L{X2GoClient} instance is setup in the 
    following way:

        - import the Python X2Go module and call the session constructor::

            import x2go
            x2go_client = x2go.X2GoClient()

        - register a new L{X2GoClient} session; this creates an L{X2GoSession} instance
          and calls its constructor method::

            x2go_sess_uuid = x2go_client.register_session(<many-options>)

        - connect to the session's remote X2Go server (SSH/Paramiko)::

            x2go_client.connect_session(x2go_sess_uuid)

        - via the connected X2Go client session you can start or resume a remote 
          X-windows session on an X2Go server now::

            x2go_client.start_session(x2go_sess_uuid)

          resp.::

            x2go_client.resume_session(x2go_sess_uuid, session_name=<session_name_of_resumable_session>)

        - a list of available sessions on the respective server (for resuming) can be obtained in
          this way::

            x2go_client.list_sessions(x2go_sess_uuid, session_name=<session_name_of_resumable_session>)

Profiled Sessions
=================
    A new profile based X2Go session (i.e. using pre-defined session profiles) within an 
    L{X2GoClient} instance is setup in a much easier way:

        - import the Python X2Go module and call the session constructor::

            import x2go
            x2go_client = x2go.X2GoClient()

        - register an X2GoClient session based on a pre-configured session profile::

            x2go_sess_uuid = x2go_client.register_session(profile_name=<session_profile_name>)

        - or alternatively by the profile id in the »sessions« file (the name of the [<section>]
          in the »sessions« file::

            x2go_sess_uuid = x2go_client.register_session(profile_id=<session_profile_id>)

        - now you proceed in a similar way as shown above::

            x2go_client.connect_session(x2go_sess_uuid)
            x2go_client.start_session(x2go_sess_uuid)

          resp.::

            x2go_client.resume_session(x2go_sess_uuid, session_name=<session_name_of_resumable_session>)


Session Suspending/Terminating
==============================

    You can suspend or terminate your sessions by calling the follwing commands::

        x2go_client.suspend_session(x2go_sess_uuid)

    resp.::

        x2go_client.terminate_session(x2go_sess_uuid)

"""
__NAME__ = 'x2goclient-pylib'

#modules
import copy
import sys
import types
import os
import socket
import urllib2
import datetime

# Python X2Go modules
from registry import X2GoSessionRegistry
from guardian import X2GoSessionGuardian
from cache import X2GoListSessionsCache
import x2go_exceptions
import log
import utils

# we hide the default values from epydoc (that's why we transform them to _UNDERSCORE variables)
from defaults import X2GOCLIENT_OS as _X2GOCLIENT_OS
from defaults import LOCAL_HOME as _LOCAL_HOME
from defaults import CURRENT_LOCAL_USER as _CURRENT_LOCAL_USER
from defaults import X2GO_CLIENT_ROOTDIR as _X2GO_CLIENT_ROOTDIR
from defaults import X2GO_SESSIONS_ROOTDIR as _X2GO_SESSIONS_ROOTDIR
from defaults import X2GO_SSH_ROOTDIR as _X2GO_SSH_ROOTDIR
from defaults import X2GO_SESSIONPROFILES_FILENAME as _X2GO_SESSIONPROFILES_FILENAME
from defaults import X2GO_SETTINGS_FILENAME as _X2GO_SETTINGS_FILENAME
from defaults import X2GO_PRINTING_FILENAME as _X2GO_PRINTING_FILENAME
from defaults import X2GO_XCONFIG_FILENAME as _X2GO_XCONFIG_FILENAME
from defaults import PUBAPP_MAX_NO_SUBMENUS as _PUBAPP_MAX_NO_SUBMENUS

from defaults import BACKENDS as _BACKENDS

if _X2GOCLIENT_OS == 'Windows':
    from xserver import X2GoClientXConfig, X2GoXServer
    from pulseaudio import X2GoPulseAudio


class X2GoClient(object):
    """\
    The X2GoClient implements _THE_ public Python X2Go API. With it you can
    construct your own X2Go client application in Python.

    Most methods in this class require that you have registered a session
    with a remote X2Go server (passing of session options, initialization of the
    session object etc.) and connected to it (authentication). For these two steps
    use these methods: L{X2GoClient.register_session()} and L{X2GoClient.connect_session()}.

    """

    lang = 'en'
    apprime_server = None
    apprime_port = 22

    def __init__(self,
                 control_backend=_BACKENDS['X2GoControlSession']['default'],
                 terminal_backend=_BACKENDS['X2GoTerminalSession']['default'],
                 info_backend=_BACKENDS['X2GoServerSessionInfo']['default'],
                 list_backend=_BACKENDS['X2GoServerSessionList']['default'],
                 proxy_backend=_BACKENDS['X2GoProxy']['default'],
                 profiles_backend=_BACKENDS['X2GoSessionProfiles']['default'],
                 settings_backend=_BACKENDS['X2GoClientSettings']['default'],
                 printing_backend=_BACKENDS['X2GoClientPrinting']['default'],
                 broker_url=None,
                 broker_password=None,
                 broker_noauth=False,
                 client_rootdir=None,
                 sessions_rootdir=None,
                 ssh_rootdir=None,
                 start_xserver=False,
                 start_pulseaudio=False,
                 use_cache=False,
                 use_listsessions_cache=False,
                 auto_update_listsessions_cache=False,
                 auto_update_listdesktops_cache=False,
                 auto_update_listmounts_cache=False,
                 auto_update_sessionregistry=False,
                 auto_register_sessions=False,
                 no_auto_reg_pubapp_sessions=False,
                 refresh_interval=60,
                 pulseaudio_installdir=os.path.join(os.getcwd(), 'pulseaudio'),
                 logger=None, loglevel=log.loglevel_DEFAULT):
        """\
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
        @param profiles_backend: X2Go session profiles backend to use
        @type profiles_backend: C{str}
        @param settings_backend: X2Go client settings backend to use
        @type settings_backend: C{str}
        @param printing_backend: X2Go client printing backend to use
        @type printing_backend: C{str}
        @param broker_url: URL pointing to the X2Go Session Broker
        @type broker_url: C{str}
        @param broker_password: use this password for authentication against the X2Go Session Broker
        @type broker_password: C{str}
        @param broker_noauth: accessing the X2Go Session Broker works without credentials
        @type broker_noauth: C{bool}
        @param client_rootdir: client base dir (default: ~/.x2goclient)
        @type client_rootdir: C{str}
        @param sessions_rootdir: sessions base dir (default: ~/.x2go)
        @type sessions_rootdir: C{str}
        @param ssh_rootdir: ssh base dir (default: ~/.ssh)
        @type ssh_rootdir: C{str}
        @param start_xserver: start XServer when registering an L{X2GoClient} instance
        @type start_xserver: C{bool}
        @param start_pulseaudio: start Pulseaudio daemon when registering an L{X2GoClient} instance
        @type start_pulseaudio: C{bool}
        @param use_cache: alias for C{use_listsessions_cache}
        @type use_cache: C{bool}
        @param use_listsessions_cache: activate the X2Go session list cache in (L{X2GoListSessionsCache})
        @type use_listsessions_cache: C{bool}
        @param auto_update_listsessions_cache: activate automatic updates of the X2Go session list cache (L{X2GoListSessionsCache})
        @type auto_update_listsessions_cache: C{bool}
        @param auto_update_listdesktops_cache: activate automatic updates of desktop lists in (L{X2GoListSessionsCache})
        @type auto_update_listdesktops_cache: C{bool}
        @param auto_update_listmounts_cache: activate automatic updates of mount lists in (L{X2GoListSessionsCache})
        @type auto_update_listmounts_cache: C{bool}
        @param auto_update_sessionregistry: activate automatic updates of the X2Go session registry
        @type auto_update_sessionregistry: C{bool}
        @param auto_register_sessions: activate automatic X2Go session registration
        @type auto_register_sessions: C{bool}
        @param no_auto_reg_pubapp_sessions: skip automatic X2Go session registration for suspended/running published applications sessions
        @type no_auto_reg_pubapp_sessions: C{bool}
        @param refresh_interval: refresh session list cache and session status every C{refresh_interval} seconds
        @type refresh_interval: C{int}
        @param pulseaudio_installdir: install path of Pulseaudio binary
        @type pulseaudio_installdir: C{str}
        @param logger: you can pass an L{X2GoLogger} object to the
            L{X2GoClient} constructor
        @type logger: L{X2GoLogger} instance
        @param loglevel: if no X2GoLogger object has been supplied a new one will be
            constructed with the given loglevel
        @type loglevel: C{int}

        """
        self.listsessions_cache = None

        if logger is None:
            self.logger = log.X2GoLogger(loglevel=loglevel)
        else:
            self.logger = copy.deepcopy(logger)
        self._logger_tag = __NAME__
        if self.logger.tag is None:
            self.logger.tag = self._logger_tag

        self.control_backend = utils._get_backend_class(control_backend, "X2GoControlSession")
        self.terminal_backend = utils._get_backend_class(terminal_backend, "X2GoTerminalSession")
        self.info_backend = utils._get_backend_class(info_backend, "X2GoServerSessionInfo")
        self.list_backend = utils._get_backend_class(list_backend, "X2GoServerSessionList")
        self.proxy_backend = utils._get_backend_class(proxy_backend, "X2GoProxy")
        if broker_url is not None:
            if broker_url.lower().startswith('ssh'):
                profiles_backend = 'sshbroker'
            elif broker_url.lower().startswith('http'):
                profiles_backend = 'httpbroker'
        self.profiles_backend = utils._get_backend_class(profiles_backend, "X2GoSessionProfiles")
        self.settings_backend = utils._get_backend_class(settings_backend, "X2GoClientSettings")
        self.printing_backend = utils._get_backend_class(printing_backend, "X2GoClientPrinting")

        self.client_rootdir = client_rootdir or os.path.normpath(os.path.join(_LOCAL_HOME, _X2GO_CLIENT_ROOTDIR))
        self.sessions_rootdir = sessions_rootdir or os.path.normpath(os.path.join(_LOCAL_HOME, _X2GO_SESSIONS_ROOTDIR))
        self.ssh_rootdir = ssh_rootdir or os.path.normpath(os.path.join(_LOCAL_HOME, _X2GO_SSH_ROOTDIR))

        self.client_rootdir = os.path.normpath(self.client_rootdir)
        self.sessions_rootdir = os.path.normpath(self.sessions_rootdir)
        self.ssh_rootdir = os.path.normpath(self.ssh_rootdir)

        self.pulseaudio_installdir = os.path.normpath(pulseaudio_installdir)

        if self.client_rootdir is not None:
            self._has_custom_client_rootdir = True
            _sessions_config_file = os.path.join(self.client_rootdir, _X2GO_SESSIONPROFILES_FILENAME)
            _settings_config_file = os.path.join(self.client_rootdir, _X2GO_SETTINGS_FILENAME)
            _printing_config_file = os.path.join(self.client_rootdir, _X2GO_PRINTING_FILENAME)
            self.session_profiles = self.profiles_backend(config_files=[_sessions_config_file], logger=self.logger, broker_url=broker_url, broker_password=broker_password, broker_noauth=broker_noauth)
            self.client_settings = self.settings_backend(config_files=[_settings_config_file], logger=self.logger)
            self.client_printing = self.printing_backend(config_files=[_printing_config_file], client_instance=self, logger=self.logger)
        else:
            self.session_profiles = self.profiles_backend(logger=self.logger)
            self.client_settings = self.settings_backend(logger=self.logger)
            self.client_printing = self.printing_backend(client_instance=self, logger=self.logger)

        if _X2GOCLIENT_OS == 'Windows' and start_xserver:

            if self.client_rootdir:
                _xconfig_config_file = os.path.join(self.client_rootdir, _X2GO_XCONFIG_FILENAME)
                self.client_xconfig = X2GoClientXConfig(config_files=[_xconfig_config_file], logger=self.logger)
            else:
                self.client_xconfig = X2GoClientXConfig(logger=self.logger)

            if not self.client_xconfig.installed_xservers:
                self.HOOK_no_installed_xservers_found()
            else:

                _last_display = None
                if  type(start_xserver) is types.BooleanType:
                    p_xs_name = self.client_xconfig.preferred_xserver_names[0]
                    _last_display = self.client_xconfig.get_xserver_config(p_xs_name)['last_display']
                    _new_display = self.client_xconfig.detect_unused_xdisplay_port(p_xs_name)
                    p_xs = (p_xs_name, self.client_xconfig.get_xserver_config(p_xs_name))
                elif type(start_xserver) is types.StringType:
                    _last_display = self.client_xconfig.get_xserver_config(start_xserver)['last_display']
                    _new_display = self.client_xconfig.detect_unused_xdisplay_port(start_xserver)
                    p_xs = (start_xserver, self.client_xconfig.get_xserver_config(start_xserver))

                if not self.client_xconfig.running_xservers:

                    if p_xs is not None:
                        self.xserver = X2GoXServer(p_xs[0], p_xs[1], logger=self.logger)

                else:

                    if p_xs is not None and _last_display is not None:
                        if _last_display == _new_display:
                            #
                            # FIXME: this trick is nasty, client implementation should rather cleanly shutdown launch X-server processes
                            #
                            # re-use a left behind X-server instance of a previous/crashed run of Python X2Go Client
                            self.logger('found a running (and maybe stray) X-server, trying to re-use it on X DISPLAY port: %s' % _last_display, loglevel=log.loglevel_WARN)
                            os.environ.update({'DISPLAY': str(_last_display)})
                    else:
                        # presume the running XServer listens on :0
                        self.logger('using fallback display for X-server: localhost:0', loglevel=log.loglevel_WARN)
                        os.environ.update({'DISPLAY': 'localhost:0'})

        if _X2GOCLIENT_OS == 'Windows' and start_pulseaudio:
            self.pulseaudio = X2GoPulseAudio(path=self.pulseaudio_installdir, client_instance=self, logger=self.logger)

        self.auto_register_sessions = auto_register_sessions
        self.no_auto_reg_pubapp_sessions = no_auto_reg_pubapp_sessions
        self.session_registry = X2GoSessionRegistry(self, logger=self.logger)
        self.session_guardian = X2GoSessionGuardian(self, auto_update_listsessions_cache=auto_update_listsessions_cache & (use_listsessions_cache|use_cache),
                                                    auto_update_listdesktops_cache=auto_update_listdesktops_cache & use_listsessions_cache,
                                                    auto_update_listmounts_cache=auto_update_listmounts_cache & use_listsessions_cache,
                                                    auto_update_sessionregistry=auto_update_sessionregistry,
                                                    auto_register_sessions=auto_register_sessions, 
                                                    no_auto_reg_pubapp_sessions=no_auto_reg_pubapp_sessions,
                                                    refresh_interval=refresh_interval,
                                                    logger=self.logger
                                                   )
        self.auto_update_sessionregistry = auto_update_sessionregistry

        if use_listsessions_cache:
            self.listsessions_cache = X2GoListSessionsCache(self, logger=self.logger)

        self.use_listsessions_cache = use_listsessions_cache | use_cache
        self.auto_update_listsessions_cache = auto_update_listsessions_cache
        self.auto_update_listdesktops_cache = auto_update_listdesktops_cache
        self.auto_update_listmounts_cache = auto_update_listmounts_cache

    def HOOK_profile_auto_connect(self, profile_name='UNKNOWN'):
        """\
        HOOK method: called if a session demands to auto connect the session profile.

        @param profile_name: profile name of session that called this hook method
        @type profile_name: C{str}

        """
        self.logger('HOOK_profile_auto_connect: profile ,,%s'' wants to be auto-connected to the X2Go server.' % profile_name, loglevel=log.loglevel_WARN)

    def HOOK_broker_connection_exception(self, profile_name='UNKNOWN'):
        """\
        HOOK method: called if a session demands to auto connect the session profile.

        @param profile_name: profile name of a session that triggered this hook method
        @type profile_name: C{str}

        """
        self.logger('HOOK_broker_connection_exception: a broker connection problem occurred triggered by an action on profile ,,%s''.' % profile_name, loglevel=log.loglevel_WARN)

    def HOOK_broker_ignore_connection_problems(self, profile_name='UNKNOWN', is_profile_connected=False):
        """\
        HOOK method: called after a broker connection failed for a certain profile. This hook can
        be used to allow the user to decide how to proceed after connection problems with the broker.

        @param profile_name: profile name of a session that triggered this hook method
        @type profile_name: C{str}
        @param is_profile_connected: C{True} if the given session profile is already conneced to the server
        @type is_profile_connected: C{bool}

        @return: If this hook returns C{True}, the session startup/resumption will be continued, even if the
            broker connection is down. (Default: broker connection problems cause session start-up to fail).
        @rtype: C{bool}

        """
        self.logger('HOOK_broker_ignore_connection_problems: use this hook to let the user to decide how to proceed on connection failures (profile name: %s, connected: %s)' % (profile_name, is_profile_connected), loglevel=log.loglevel_WARN)
        return False

    def HOOK_session_startup_failed(self, profile_name='UNKNOWN'):
        """\
        HOOK method: called if the startup of a session failed.

        @param profile_name: profile name of session that called this hook method
        @type profile_name: C{str}

        """
        self.logger('HOOK_session_startup_failed: session startup for session profile ,,%s'' failed.' % profile_name, loglevel=log.loglevel_WARN)

    def HOOK_desktop_sharing_denied(self, profile_name='UNKNOWN'):
        """\
        HOOK method: called if the startup of a shadow session was denied by the other user.

        @param profile_name: profile name of session that called this hook method
        @type profile_name: C{str}

        """
        self.logger('HOOK_desktop_sharing_failed: desktop sharing for profile ,,%s'' was denied by the other user.' % profile_name, loglevel=log.loglevel_WARN)

    def HOOK_list_desktops_timeout(self, profile_name='UNKNOWN'):
        """\
        HOOK method: called if the x2golistdesktops command generates a timeout due to long execution time.

        @param profile_name: profile name of session that called this hook method
        @type profile_name: C{str}

        """
        self.logger('HOOK_list_desktops_timeout: the server-side x2golistdesktops command for session profile %s took too long to return results. This can happen from time to time, please try again.' % profile_name, loglevel=log.loglevel_WARN)

    def HOOK_no_such_desktop(self, profile_name='UNKNOWN', desktop='UNKNOWN'):
        """\
        HOOK method: called if it is tried to connect to a (seen before) sharable desktop that's not available (anymore).

        @param profile_name: profile name of session that called this hook method
        @type profile_name: C{str}
        @param desktop: desktop identifier (the X session's $DISPLAY)
        @type desktop: C{str}

        """
        self.logger('HOOK_no_such_desktop: the desktop %s (via session profile %s) is not available for sharing (anymore).' % (desktop, profile_name), loglevel=log.loglevel_WARN)

    def HOOK_no_known_xserver_found(self):
        self.logger('DEPRECATION WARNING: The hook method HOOK_no_known_xserver_found is obsolete. Use HOOK_no_installed_xservers_found instead', loglevel=log.loglevel_WARN)
        self.HOOk_no_installed_xservers_found()

    def HOOK_no_installed_xservers_found(self):
        """\
        HOOK method: called if the Python X2Go module could not find any usable XServer
        application to start. You will not be able to start X2Go sessions without an XServer.

        """
        self.logger('the Python X2Go module could not find any usable XServer application, you will not be able to start X2Go sessions without an XServer', loglevel=log.loglevel_WARN)

    def HOOK_open_print_dialog(self, profile_name='UNKNOWN', session_name='UNKNOWN'):
        """\
        HOOK method: called if an incoming print job has been detected by L{X2GoPrintQueue} and a print dialog box is
        requested.

        @param profile_name: profile name of session that called this hook method
        @type profile_name: C{str}
        @param session_name: X2Go session name
        @type session_name: C{str}

        """
        self.logger('HOOK_open_print_dialog: incoming print job detected by X2GoClient hook method', loglevel=log.loglevel_WARN)

    def HOOK_no_such_command(self, cmd, profile_name='UNKNOWN', session_name='UNKNOWN'):
        """\
        HOOK: the command <cmd> is not available on the connected X2Go server.

        @param cmd: the command that failed
        @type cmd: C{str}
        @param profile_name: profile name of session that called this hook method
        @type profile_name: C{str}
        @param session_name: X2Go session name
        @type session_name: C{str}

        """
        self.logger('HOOK_no_such_command: the command %s is not available for X2Go server (profile: %s, session: %s)' % (cmd, profile_name, session_name), loglevel=log.loglevel_WARN)

    def HOOK_open_mimebox_saveas_dialog(self, filename, profile_name='UNKNOWN', session_name='UNKNOWN'):
        """\
        HOOK method: called on detection of an incoming MIME box job ,,<filename>''.

        @param filename: file name of the incoming MIME box job
        @type filename: C{str}
        @param profile_name: profile name of session that called this hook method
        @type profile_name: C{str}
        @param session_name: X2Go session name
        @type session_name: C{str}

        """
        self.logger('HOOK_open_mimebox_saveas_dialog: incoming MIME box job ,, %s'' detected by X2GoClient hook method' % filename, loglevel=log.loglevel_WARN)

    def HOOK_printaction_error(self, filename, profile_name='UNKNOWN', session_name='UNKNOWN', err_msg='GENERIC_ERROR', printer=None):
        """\
        HOOK method: called if an incoming print job caused an error.

        @param filename: file name of the print job that failed
        @type filename: C{str}
        @param profile_name: profile name of session that called this hook method
        @type profile_name: C{str}
        @param session_name: X2Go session name
        @type session_name: C{str}
        @param err_msg: if available, an appropriate error message
        @type err_msg: C{str}
        @param printer: if available, the printer name the print job failed on
        @type printer: C{str}

        """
        if printer:
            self.logger('HOOK_printaction_error: incoming print job ,, %s'' on printer %s caused error: %s' % (filename, printer, err_msg), loglevel=log.loglevel_ERROR)
        else:
            self.logger('HOOK_printaction_error: incoming print job ,, %s'' caused error: %s' % (filename, err_msg), loglevel=log.loglevel_ERROR)

    def HOOK_check_host_dialog(self, profile_name='UNKNOWN', host='UNKNOWN', port=22, fingerprint='no fingerprint', fingerprint_type='UNKNOWN'):
        """\
        HOOK method: called if a host check is requested. This hook has to either return C{True} (default) or C{False}.

        @param profile_name: profile name of session that called this hook method
        @type profile_name: C{str}
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
        self.logger('HOOK_check_host_dialog: host check requested for session profile %s: Automatically adding host [%s]:%s with fingerprint: ,,%s\'\' as a known host.' % (profile_name, host, port, fingerprint), loglevel=log.loglevel_WARN)
        # this HOOK has to return either True (accept host connection) or False (deny host conection)
        return True

    def HOOK_on_control_session_death(self, profile_name):
        """\
        HOOK method: called if a control session (server connection) has unexpectedly encountered a failure.

        @param profile_name: profile name of session that called this hook method
        @type profile_name: C{str}

        """
        self.logger('HOOK_on_control_session_death: the control session of profile %s has died unexpectedly' % profile_name, loglevel=log.loglevel_WARN)
 
    def HOOK_on_failing_SFTP_client(self, profile_name, session_name):
        """\
        HOOK method: called SFTP client support is unavailable for the session.

        @param profile_name: profile name of the session that experiences failing SFTP client support
        @type profile_name: C{str}
        @param session_name: name of session experiencing failing SFTP client support
        @type session_name: C{str}

        """
        self.logger('HOOK_on_failing_SFTP_client: new session for profile %s will lack SFTP client support. Check your server setup. Avoid echoing ~/.bashrc files on server.' % profile_name, loglevel=log.loglevel_ERROR)

    def HOOK_pulseaudio_not_supported_in_RDPsession(self):
        """HOOK method: called if trying to run the Pulseaudio daemon within an RDP session, which is not supported by Pulseaudio."""
        self.logger('HOOK_pulseaudio_not_supported_in_RDPsession: The pulseaudio daemon cannot be used within RDP sessions', loglevel=log.loglevel_WARN)

    def HOOK_pulseaudio_server_startup_failed(self):
        """HOOK method: called if the Pulseaudio daemon startup failed."""
        self.logger('HOOK_pulseaudio_server_startup_failed: The pulseaudio daemon could not be started', loglevel=log.loglevel_ERROR)

    def HOOK_pulseaudio_server_died(self):
        """HOOK method: called if the Pulseaudio daemon has died away unexpectedly."""
        self.logger('HOOK_pulseaudio_server_died: The pulseaudio daemon has just died away', loglevel=log.loglevel_ERROR)

    def HOOK_on_sound_tunnel_failed(self, profile_name='UNKNOWN', session_name='UNKNOWN'):
        """\
        HOOK method: called if a sound tunnel setup failed.

        @param profile_name: profile name of session that called this hook method
        @type profile_name: C{str}
        @param session_name: X2Go session name
        @type session_name: C{str}

        """
        self.logger('HOOK_on_sound_tunnel_failed: setting up X2Go sound for %s (%s) support failed' % (profile_name, session_name))

    def HOOK_rforward_request_denied(self, profile_name='UNKNOWN', session_name='UNKNOWN', server_port=0):
        """\
        HOOK method: called if a reverse port forwarding request has been denied.

        @param profile_name: profile name of session that called this hook method
        @type profile_name: C{str}
        @param session_name: X2Go session name
        @type session_name: C{str}
        @param server_port: remote server port (starting point of reverse forwarding tunnel)
        @type server_port: C{str}

        """
        self.logger('TCP port (reverse) forwarding request for session %s to server port %s has been denied by the X2Go server. This is a common issue with SSH, it might help to restart the X2Go server\'s SSH daemon.' % (session_name, server_port), loglevel=log.loglevel_WARN)

    def HOOK_forwarding_tunnel_setup_failed(self, profile_name='UNKNOWN', session_name='UNKNOWN', chain_host='UNKNOWN', chain_port=0, subsystem=None):
        """\
        HOOK method: called if a port forwarding tunnel setup failed.

        @param profile_name: profile name of session that called this hook method
        @type profile_name: C{str}
        @param session_name: X2Go session name
        @type session_name: C{str}
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

        self.logger('Forwarding tunnel request to [%s]:%s for session %s (%s) was denied by remote X2Go/SSH server. Subsystem %s startup failed.' % (chain_host, chain_port, session_name, profile_name, _subsystem), loglevel=log.loglevel_ERROR)

    def HOOK_on_session_has_started_by_me(self, session_uuid='UNKNOWN', profile_name='UNKNOWN', session_name='UNKNOWN'):
        """\
        HOOK method: called if a session has been started by this instance of L{X2GoClient}.

        @param session_uuid: unique session identifier of the calling session
        @type session_uuid: C{str}
        @param profile_name: profile name of session that called this hook method
        @type profile_name: C{str}
        @param session_name: X2Go session name
        @type session_name: C{str}

        """
        self.logger('HOOK_on_session_has_started_by_me (session_uuid: %s, profile_name: %s): a new session %s has been started by this application' %  (session_uuid, profile_name, session_name), loglevel=log.loglevel_NOTICE)

    def HOOK_on_session_has_started_by_other(self, session_uuid='UNKNOWN', profile_name='UNKNOWN', session_name='UNKNOWN'):
        """\
        HOOK method: called if a session has been started by another C{x2goclient}.

        @param session_uuid: unique session identifier of the calling session
        @type session_uuid: C{str}
        @param profile_name: profile name of session that called this hook method
        @type profile_name: C{str}
        @param session_name: X2Go session name
        @type session_name: C{str}

        """
        self.logger('HOOK_on_session_has_started (session_uuid: %s, profile_name: %s): a new session %s has started been started by other application' %  (session_uuid, profile_name, session_name), loglevel=log.loglevel_NOTICE)

    def HOOK_on_session_has_resumed_by_me(self, session_uuid='UNKNOWN', profile_name='UNKNOWN', session_name='UNKNOWN'):
        """\
        HOOK method: called if a session has been resumed by this instance of L{X2GoClient}.

        @param session_uuid: unique session identifier of the calling session
        @type session_uuid: C{str}
        @param profile_name: profile name of session that called this hook method
        @type profile_name: C{str}
        @param session_name: X2Go session name
        @type session_name: C{str}

        """
        self.logger('HOOK_on_session_has_resumed_by_me (session_uuid: %s, profile_name: %s): suspended session %s has been resumed by this application' %  (session_uuid, profile_name, session_name), loglevel=log.loglevel_NOTICE)

    def HOOK_on_session_has_resumed_by_other(self, session_uuid='UNKNOWN', profile_name='UNKNOWN', session_name='UNKNOWN'):
        """\
        HOOK method: called if a session has been resumed by another C{x2goclient}.

        @param session_uuid: unique session identifier of the calling session
        @type session_uuid: C{str}
        @param profile_name: profile name of session that called this hook method
        @type profile_name: C{str}
        @param session_name: X2Go session name
        @type session_name: C{str}

        """
        self.logger('HOOK_on_session_has_resumed_by_other (session_uuid: %s, profile_name: %s): suspended session %s has been resumed by other application' %  (session_uuid, profile_name, session_name), loglevel=log.loglevel_NOTICE)

    def HOOK_on_found_session_running_after_connect(self, session_uuid='UNKNOWN', profile_name='UNKNOWN', session_name='UNKNOWN'):
        """\
        HOOK method: called after server connect if an already running session has been found.

        @param session_uuid: unique session identifier of the calling session
        @type session_uuid: C{str}
        @param profile_name: profile name of session that called this hook method
        @type profile_name: C{str}
        @param session_name: X2Go session name
        @type session_name: C{str}

        """
        self.logger('HOOK_found_session_running_after_connect (session_uuid: %s, profile_name: %s): running session %s has been found after connecting to session profile %s' %  (session_uuid, profile_name, session_name, profile_name), loglevel=log.loglevel_NOTICE)

    def HOOK_on_session_has_been_suspended(self, session_uuid='UNKNOWN', profile_name='UNKNOWN', session_name='UNKNOWN'):
        """\
        HOOK method: called if a session has been suspended by this instance of L{X2GoClient}.

        @param session_uuid: unique session identifier of the calling session
        @type session_uuid: C{str}
        @param profile_name: profile name of session that called this hook method
        @type profile_name: C{str}
        @param session_name: X2Go session name
        @type session_name: C{str}

        """
        self.logger('HOOK_on_session_has_been_suspended (session_uuid: %s, profile_name: %s): session %s has been suspended' %  (session_uuid, profile_name, session_name), loglevel=log.loglevel_NOTICE)

    def HOOK_on_session_has_terminated(self, session_uuid='UNKNOWN', profile_name='UNKNOWN', session_name='UNKNOWN'):
        """\
        HOOK method: called if a session has been suspended by another C{x2goclient}.

        @param session_uuid: unique session identifier of the calling session
        @type session_uuid: C{str}
        @param profile_name: profile name of session that called this hook method
        @type profile_name: C{str}
        @param session_name: X2Go session name
        @type session_name: C{str}

        """
        self.logger('HOOK_on_session_has_terminated (session_uuid: %s, profile_name: %s): session %s has terminated' % (session_uuid, profile_name, session_name), loglevel=log.loglevel_NOTICE)

    def HOOK_printing_not_available(self, profile_name='UNKNOWN', session_name='UNKNOWN'):
        """\
        HOOK method: called if X2Go client-side printing is not available.

        @param profile_name: profile name of session that called this hook method
        @type profile_name: C{str}
        @param session_name: X2Go session name
        @type session_name: C{str}

        """
        self.logger('HOOK_foldersharing_not_available: X2Go\'s client-side printing feature is not available with this session (%s) of profile %s.' % (session_name, profile_name), loglevel=log.loglevel_WARN)

    def HOOK_mimebox_not_available(self, profile_name='UNKNOWN', session_name='UNKNOWN'):
        """\
        HOOK method: called if the X2Go MIME box is not available.

        @param profile_name: profile name of session that called this hook method
        @type profile_name: C{str}
        @param session_name: X2Go session name
        @type session_name: C{str}

        """
        self.logger('HOOK_mimebox_not_available: X2Go\'s MIME box feature is not available with this session (%s) of profile %s.' % (session_name, profile_name), loglevel=log.loglevel_WARN)

    def HOOK_foldersharing_not_available(self, profile_name='UNKNOWN', session_name='UNKNOWN'):
        """\
        HOOK method: called if X2Go client-side folder-sharing is not available.

        @param profile_name: profile name of session that called this hook method
        @type profile_name: C{str}
        @param session_name: X2Go session name
        @type session_name: C{str}

        """
        self.logger('HOOK_foldersharing_not_available: X2Go\'s client-side folder sharing feature is not available with this session (%s) of profile %s.' % (session_name, profile_name), loglevel=log.loglevel_WARN)

    def HOOK_sshfs_not_available(self, profile_name='UNKNOWN', session_name='UNKNOWN'):
        """\
        HOOK method: called if the X2Go server denies SSHFS access.

        @param profile_name: profile name of session that called this hook method
        @type profile_name: C{str}
        @param session_name: X2Go session name
        @type session_name: C{str}

        """
        self.logger('HOOK_sshfs_not_available: the remote X2Go server (%s) denies SSHFS access for session %s. This will result in client-side folder sharing, printing and the MIME box feature being unavailable' % (session_name, profile_name), loglevel=log.loglevel_WARN)

    def get_client_rootdir(self):
        """\
        Retrieve the settings root directory of this L{X2GoClient} instance.

        @return: X2Go client root directory
        @rtype: C{str}
        """
        return os.path.normpath(self.client_rootdir)
    __get_client_rootdir = get_client_rootdir

    @property
    def has_custom_client_rootdir(self):
        """\
        Does this L{X2GoClient} instance have a customized root dir path?
        Equals C{True} in case it has.

        """
        return self._has_custom_client_rootdir
    __has_custom_client_rootdir = has_custom_client_rootdir

    def get_sessions_rootdir(self):
        """\
        Retrieve the sessions root directory of this L{X2GoClient} instance.

        @return: X2Go sessions root directory
        @rtype: C{str}
        """
        return os.path.normpath(self.sessions_rootdir)
    __get_sessions_rootdir = get_sessions_rootdir

    def get_ssh_rootdir(self):
        """\
        Retrieve the SSH client root dir used with this L{X2GoClient} instance.

        @return: SSH client root directory
        @rtype: C{str}
        """
        return os.path.normpath(self.ssh_rootdir)
    __get_ssh_rootdir = get_ssh_rootdir

    def get_client_username(self):
        """\
        Query the local user's username (i.e. the user running the X2Go client).

        @return: the local username this L{X2GoClient} instance runs as
        @rtype: C{str}

        """
        return _CURRENT_LOCAL_USER
    __get_client_username = get_client_username

    def register_all_session_profiles(self, return_objects=False):
        """\
        Register all session profiles found in the C{sessions} configuration node 
        as potential X2Go sessions.

        @param return_objects: if set to C{True} this methods returns a list of L{X2GoSession}
            instances, otherwise a list of session UUIDs representing the corresponding 
            registered sessions is returned
        @type return_objects: C{bool}

        @return: a Python dictionary containing one registered session for each available session profile 
            configuration, whereas the profile names are used as dictionary keys and L{X2GoSession} 
            instances as their values
        @rtype: C{list}

        """
        sessions = {}
        for profile_name in self.session_profiles.profile_names:
            _obj = self._X2GoClient__register_session(profile_name=profile_name, return_object=True)
            sessions[_obj.get_profile_name()] = _obj
        return sessions
    __register_all_session_profiles = register_all_session_profiles

    def register_session(self, server=None, profile_id=None, profile_name=None, session_name=None,
                         allow_printing=False, 
                         allow_share_local_folders=False, share_local_folders=[], 
                         allow_mimebox=False, mimebox_extensions=[], mimebox_action='OPEN',
                         add_to_known_hosts=False, known_hosts=None, forward_sshagent=False,
                         proxy_options={},
                         return_object=False, **kwargs):
        """\
        Register a new L{X2GoSession}. Within one L{X2GoClient}
        instance you can manage several L{X2GoSession} instances on serveral
        remote X2Go servers under different user names.

        These sessions can be instantiated by passing direct L{X2GoSession}
        parameters to this method or by specifying the name of an existing session profile
        (as found in the L{X2GoClient}'s C{sessions} configuration node.

        A session profile is a pre-defined set of session options stored in a sessions
        profile node (e.g. a configuration file). With the FILE backend such session
        profiles are stored as a file (by default: C{~/.x2goclient/sessions} or globally (for all users on the
        client) in C{/etc/x2goclient/sessions}).

        Python X2Go also supports starting multiple X2Go sessions for the same
        session profile simultaneously.

        This method (L{X2GoClient.register_session()}) accepts a similar set of parameters
        as the L{X2GoSession} constructor itself. For a complete set of session options refer
        there.

        Alternatively, you can also pass a profile name or a profile id 
        to this method. If you do this, Python X2Go tries to find the specified session
        in the C{sessions} configuration node and then derives the necessary session parameters
        from the session profile configuration. Additional L{X2GoSession} parameters can
        also be passed to this method---they will override the option values retrieved from
        the session profile.

        @param server: hostname of the remote X2Go server
        @type server: C{str}
        @param profile_id: id (config section name) of a session profile to load 
            from your session config
        @type profile_id: C{str}
        @param profile_name: name of a session profile to load from your session
            config
        @type profile_name: C{str}
        @param allow_printing: enable X2Go printing support for the to-be-registered X2Go session
        @type allow_printing: C{bool}
        @param allow_share_local_folders: set local folder sharing to enabled/disabled
        @type allow_share_local_folders: C{bool}
        @param share_local_folders: a list of local folders (as strings) to be shared directly
            after session start up
        @type share_local_folders: C{list}
        @param allow_mimebox: enable X2Go MIME box support for the to-be-registered X2Go session
        @type allow_mimebox: C{bool}
        @param mimebox_extensions: MIME box support is only allowed for the given file extensions
        @type mimebox_extensions: C{list}
        @param mimebox_action: MIME box action to use on incoming MIME job files
        @type mimebox_action: C{str}
        @param add_to_known_hosts: add unknown host keys to the C{known_hosts} file and accept the connection
            automatically
        @type add_to_known_hosts: C{bool}
        @param known_hosts: full path to C{known_hosts} file
        @type known_hosts: C{str}
        @param forward_sshagent: forward SSH agent authentication requests to the X2Go client-side
        @type forward_sshagent: C{bool}
        @param proxy_options: a set of very C{X2GoProxy*} backend specific options; any option that is not known
            to the C{X2GoProxy*} backend will simply be ignored
        @type proxy_options: C{dict}
        @param return_object: normally this method returns a unique session UUID. If 
            C{return_object} is set to C{True} an X2GoSession object will be returned 
            instead
        @type return_object: C{bool}
        @param kwargs: any option that is also valid for the L{X2GoSession} constructor
        @type kwargs: C{dict}

        @return: a unique identifier (UUID) for the newly registered X2Go session (or an
            X2GoSession object if C{return_object} is set to True
        @rtype: C{str}

        """
        _p = None
        # detect profile name and profile id properly
        if profile_id and self.session_profiles.has_profile_id(profile_id):
            _p = profile_id
        elif profile_name and self.session_profiles.has_profile_name(profile_name):
            _p = profile_name
        elif profile_id:
            try:
                _p = self.session_profiles.check_profile_id_or_name(profile_id)
            except x2go_exceptions.X2GoProfileException:
                pass
        elif profile_name:
            try:
                _p = self.session_profiles.check_profile_id_or_name(profile_name)
            except x2go_exceptions.X2GoProfileException:
                pass
        if _p:
            _profile_id = self.session_profiles.check_profile_id_or_name(_p)
            _profile_name = self.session_profiles.to_profile_name(_profile_id)
        else:
            _profile_id = None

        # test if session_name has already been registered. If yes, return it immediately.
        if type(session_name) is types.StringType:
            _retval = self.get_session_of_session_name(session_name, return_object=return_object, match_profile_name=profile_name)
            if _retval is not None:
                return _retval

        if known_hosts is None:
            known_hosts = os.path.join(_LOCAL_HOME, self.ssh_rootdir, 'known_hosts')

        if _profile_id:

            # initialize session profile cache
            self.session_profiles.init_profile_cache(_profile_id)

            _params = self.session_profiles.to_session_params(profile_id=_profile_id)
            del _params['profile_name']

            # override any available session parameter passed to this method
            for k in _params.keys():
                if k in kwargs.keys():
                    _params[k] = kwargs[k]

            _pkey = None
            try:
                server = self.session_profiles.get_server_hostname(_profile_id)
                _params['port'] = self.session_profiles.get_server_port(_profile_id)
                _pkey = self.session_profiles.get_pkey_object(_profile_id)
            except x2go_exceptions.X2GoBrokerConnectionException, e:
                _profile_name = self.to_profile_name(_profile_id)
                self.HOOK_broker_connection_exception(_profile_name)
                if not self.HOOK_broker_ignore_connection_problems(_profile_name, is_profile_connected=self.is_profile_connected(_profile_name)):
                    raise e
                server = self.session_profiles.get_profile_config(_profile_name, parameter='host')[0]
                _params['port'] = self.session_profiles.get_profile_config(_profile_name, parameter='sshport')

            if _pkey is not None:
                self.logger('received PKey object for authentication, ignoring all other auth mechanisms', log.loglevel_NOTICE, tag=self._logger_tag)
                _params['pkey'] = _pkey
                _params['sshproxy_pkey'] = _pkey
                _params['allow_agent'] = False
                _params['look_for_keys'] = False
                _params['key_filename'] = []

            del _params['server']
            _params['client_instance'] = self

        else:
            if server is None:
                return None
            _profile_id = utils._genSessionProfileId()
            _profile_name = profile_name or sys.argv[0]
            _params = kwargs
            _params['printing'] = allow_printing
            _params['allow_share_local_folders'] = allow_share_local_folders
            _params['share_local_folders'] = share_local_folders
            _params['allow_mimebox'] = allow_mimebox
            _params['mimebox_extensions'] = mimebox_extensions
            _params['mimebox_action'] = mimebox_action
            _params['client_instance'] = self
            _params['proxy_options'] = proxy_options
            _params['forward_sshagent'] = forward_sshagent

        session_uuid = self.session_registry.register(server=server,
                                                      profile_id=_profile_id, profile_name=_profile_name,
                                                      session_name=session_name,
                                                      control_backend=self.control_backend,
                                                      terminal_backend=self.terminal_backend,
                                                      info_backend=self.info_backend,
                                                      list_backend=self.list_backend,
                                                      proxy_backend=self.proxy_backend,
                                                      settings_backend=self.settings_backend,
                                                      printing_backend=self.printing_backend,
                                                      client_rootdir=self.client_rootdir,
                                                      sessions_rootdir=self.sessions_rootdir,
                                                      ssh_rootdir=self.ssh_rootdir,
                                                      keep_controlsession_alive=True,
                                                      add_to_known_hosts=add_to_known_hosts,
                                                      known_hosts=known_hosts,
                                                      **_params)

        self.logger('initializing X2Go session...', log.loglevel_NOTICE, tag=self._logger_tag)
        if return_object:
            return self.session_registry(session_uuid)
        else:
            return session_uuid
    __register_session = register_session

    ###
    ### WRAPPER METHODS FOR X2GoSessionRegistry objects
    ###

    def get_session_summary(self, session_uuid):
        """\
        Retrieves a Python dictionary, containing a short session summary (session status, names, etc.)

        @param session_uuid: the X2Go session's UUID registry hash
        @type session_uuid: C{str}

        """
        return self.session_registry.session_summary(session_uuid)
    __get_session_summary = get_session_summary

    ###
    ### WRAPPER METHODS FOR X2GoSession objects
    ###

    def get_session_username(self, session_uuid):
        """\
        After an L{X2GoSession} has been set up you can query the
        username that the remote sessions runs as.

        @param session_uuid: the X2Go session's UUID registry hash
        @type session_uuid: C{str}

        @return: the remote username the X2Go session runs as
        @rtype: C{str}

        """
        return self.session_registry(session_uuid).get_username()
    __get_session_username = get_session_username

    def get_session_server_peername(self, session_uuid):
        """\
        After a session has been set up you can query the
        hostname of the host the session is connected to (or
        about to connect to).

        @param session_uuid: the X2Go session's UUID registry hash
        @type session_uuid: C{str}

        @return: the host an X2Go session is connected to 
            (as an C{(addr,port)} tuple) 
        @rtype: tuple

        """
        return self.session_registry(session_uuid).get_server_peername()
    __get_session_server_peername = get_session_server_peername

    def get_session_server_hostname(self, session_uuid):
        """\
        Retrieve the server hostname as provided by the calling
        application (e.g. like it has been specified in the session 
        profile).

        @param session_uuid: the X2Go session's UUID registry hash
        @type session_uuid: C{str}

        @return: the hostname for the queried X2Go session as specified 
            by the calling application
        @rtype: str

        """
        return self.session_registry(session_uuid).get_server_hostname()
    __get_session_server_hostname = get_session_server_hostname

    def get_session(self, session_uuid):
        """\
        Retrieve the complete L{X2GoSession} object that has been
        registered under the given session registry hash.

        @param session_uuid: the X2Go session's UUID registry hash
        @type session_uuid: C{str}

        @return: the L{X2GoSession} instance
        @rtype: obj

        """
        return self.session_registry(session_uuid)
    __get_session = get_session
    with_session = __get_session
    """Alias for L{get_session()}."""

    def get_session_of_session_name(self, session_name, return_object=False, match_profile_name=None):
        """\
        Retrieve session UUID or L{X2GoSession} for session name
        <session_name> from the session registry.

        @param session_name: the X2Go session's UUID registry hash
        @type session_name: C{str}
        @param return_object: session UUID hash or L{X2GoSession} instance wanted?
        @type return_object: C{bool}
        @param match_profile_name: only return sessions that match this profile name
        @type match_profile_name: C{str}

        @return: the X2Go session's UUID registry hash or L{X2GoSession} instance
        @rtype: C{str} or L{X2GoSession} instance

        """
        try:
            return self.session_registry.get_session_of_session_name(session_name=session_name, return_object=return_object, match_profile_name=match_profile_name)
        except x2go_exceptions.X2GoSessionRegistryException:
            return None
    __get_session_of_session_name = get_session_of_session_name

    def get_session_name(self, session_uuid):
        """\
        Retrieve the server-side X2Go session name for the session that has
        been registered under C{session_uuid}.

        @param session_uuid: the X2Go session's UUID registry hash
        @type session_uuid: C{str}

        @return: X2Go session name
        @rtype: C{str}

        """
        return self.session_registry(session_uuid).get_session_name()
    __get_session_name = get_session_name

    def get_session_info(self, session_uuid):
        """\
        Retrieve the server-side X2Go session information object for the session that has
        been registered under C{session_uuid}.

        @param session_uuid: the X2Go session's UUID registry hash
        @type session_uuid: C{str}

        @return: X2Go session info
        @rtype: C{obj}

        """
        return self.session_registry(session_uuid).get_session_info()
    __get_session_info = get_session_info

    def get_published_applications(self, session_uuid=None, profile_name=None, lang=None, refresh=False, raw=False, very_raw=False, max_no_submenus=_PUBAPP_MAX_NO_SUBMENUS):
        """\
        Retrieve the server-side X2Go published applications menu for the session
        registered under C{session_uuid} or for profile name C{profile_name}.

        @param session_uuid: the X2Go session's UUID registry hash
        @type session_uuid: C{str}
        @param profile_name: a valid session profile name
        @type profile_name: C{str}

        @return: a representative of the published applications menu tree
        @rtype: C{dict}

        """
        if session_uuid is None and profile_name:
            _session_uuids = self._X2GoClient__client_pubapp_sessions_of_profile_name(profile_name, return_objects=False)
            if len(_session_uuids): session_uuid = _session_uuids[0]
        if session_uuid:
            try:
                if self.session_registry(session_uuid).is_published_applications_provider():
                    return self.session_registry(session_uuid).get_published_applications(lang=lang, refresh=refresh, raw=raw, very_raw=False, max_no_submenus=max_no_submenus)
            except x2go_exceptions.X2GoSessionRegistryException:
                pass
        else:
            self.logger('Cannot find a terminal session for profile ,,%s\'\' that can be used to query a published applications menu tree' % profile_name, loglevel=log.loglevel_INFO)
        return None
    __get_published_applications = get_published_applications
    profile_get_published_applications = get_published_applications
    __profile_get_published_applications = get_published_applications

    def set_session_username(self, session_uuid, username):
        """\
        Set the session username for the L{X2GoSession} that has been registered under C{session_uuid}.
        This can be helpful for modifying user credentials during an authentication phase.

        @param session_uuid: the X2Go session's UUID registry hash
        @type session_uuid: C{str}
        @param username: new user name to be used for session authentication
        @type username: C{str}

        @return: return C{True} on success
        @rtype: C{bool}

        """
        return self.session_registry(session_uuid).set_username(username=username)
    __set_session_username = set_session_username

    def check_session_host(self, session_uuid):
        """\
        Provide a mechanism to evaluate the validity of an X2Go server host.

        @param session_uuid: the X2Go session's UUID registry hash
        @type session_uuid: C{str}

        @return: return C{True} if host validation has been successful.
        @rtype: C{bool}

        """
        return self.session_registry(session_uuid).check_host()
    __check_session_host = check_session_host

    def session_reuses_sshproxy_authinfo(self, session_uuid):
        """\
        Check if session with unique identifier <session_uuid> is configured to re-use the X2Go session's
        password / key for proxy authentication, as well.

        @return: returns C{True} if the session is configured to re-use session password / key for proxy authentication
        @rtype: C{bool}
        """
        return self.session_registry(session_uuid).reuses_sshproxy_authinfo()
    __session_reuses_sshproxy_authinfo = session_reuses_sshproxy_authinfo

    def session_uses_sshproxy(self, session_uuid):
        """\
        Check if session with unique identifier <session_uuid> is configured to use an
        intermediate SSH proxy server.

        @return: returns C{True} if the session is configured to use an SSH proxy, C{False} otherwise.
        @rtype: C{bool}

        """
        return self.session_registry(session_uuid).uses_sshproxy()
    __session_uses_sshproxy = session_uses_sshproxy

    def session_can_sshproxy_auto_connect(self, session_uuid):
        """\
        Check if the SSH proxy of session with unique identifier <session_uuid> is configured adequately
        to be able to auto-connect to the SSH proxy server (e.g. by public key authentication).

        @param session_uuid: the X2Go session's UUID registry hash
        @type session_uuid: C{str}

        @return: returns C{True} if the session's SSH proxy can auto-connect, C{False} otherwise, C{None}
            if no control session has been set up yet.
        @rtype: C{bool}

        """
        return self.session_registry(session_uuid).can_sshproxy_auto_connect()
    __session_can_sshproxy_auto_connect = session_can_sshproxy_auto_connect

    def session_can_auto_connect(self, session_uuid):
        """\
        Check if session with unique identifier <session_uuid> is configured adequately
        to be able to auto-connect to the X2Go server (e.g. by public key authentication).

        @param session_uuid: the X2Go session's UUID registry hash
        @type session_uuid: C{str}

        @return: returns C{True} if the session can auto-connect, C{False} otherwise, C{None}
            if no control session has been set up yet.
        @rtype: C{bool}

        """
        return self.session_registry(session_uuid).can_auto_connect()
    __session_can_auto_connect = session_can_auto_connect

    # user hooks for detecting/notifying what happened during application runtime
    def session_auto_connect(self, session_uuid):
        """\
        Auto-connect a given session. This method is called from within the session itself
        and can be used to override the auto-connect procedure from within your
        client implementation.

        @param session_uuid: the X2Go session's UUID registry hash
        @type session_uuid: C{str}

        @return: returns C{True} if the session could be auto-connected.
        @rtype: C{bool}

        """
        self.session_registry(session_uuid).do_auto_connect(redirect_to_client=False)
    __session_auto_connect = session_auto_connect

    #apprime code begin
    def apprimeLoadBalancer(self, username):
        response = None
        try:
            response = urllib2.urlopen("http://lb.rapidapp.online/lb/loadbalancer.php?uid=%s" % username)
            self.vglbip = response.read().strip();
            self.logger('====>>>>>RapidApp: LB gave node %s' % self.vglbip, loglevel=log.loglevel_INFO)
        except:
            raise ValueError('Unable to connect to loadbalancer. Is your network connection working?')
        if(self.vglbip == '-1'):
            raise ValueError('Your session is being optimized. Please try after a few seconds')
        if(self.vglbip == '-99'):
            raise ValueError('All servers are overloaded. Please try after a few minutes')
        if(self.vglbip == '-1000'):
            raise ValueError('Unknown loadbalancer error (-1000). Please try after a few minutes')
        if(response.getcode() != 200):
            raise ValueError('Unknown loadbalancer error (HTTP %d). Please try after a few minutes' % response.getcode())
        
        #If we reach here, we've got a node IP. Lets check port reachability to it
        X2GoClient.apprime_server = self.vglbip.strip() #set the server node
        
        #try port reachability
        X2GoClient.apprime_port = 22 #default
        portoptions = [22, 80, 443, 25, 110, 21, 20, 995, 2525, 465, 143, 993] #most commonly used ports
        for vgport in portoptions:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(2)
                s.connect((X2GoClient.apprime_server, vgport))
                s.close()
                X2GoClient.apprime_port = vgport
                break
            except:
                self.logger('====>>>>>VG: Port %d NOT open on node %s' % (vgport, X2GoClient.apprime_server), loglevel=log.loglevel_INFO,)
            
    #apprime code end 
    

    def getServerLatency(self):
        latency = -1
        try:
            starttime = datetime.datetime.now()
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(5)
            s.connect((X2GoClient.apprime_server, X2GoClient.apprime_port))
            endtime = datetime.datetime.now()
            diff = endtime - starttime
            latency = (int)(diff.seconds*1000 + diff.microseconds/1000)
            s.close()
        except Exception, ex:
            self.logger('====>>>>>VG: Pinging server failed: %s ' % ex.strerror, loglevel=log.loglevel_INFO, )
        return latency

    def connect_session(self, session_uuid,
                        username=None,
                        password=None,
                        passphrase=None,
                        sshproxy_user=None,
                        sshproxy_password=None,
                        sshproxy_passphrase=None,
                        add_to_known_hosts=False,
                        force_password_auth=False,
                        sshproxy_force_password_auth=False,
                       ):
        """\
        Connect to a registered X2Go session with registry hash C{session_uuid}
        This method basically wraps around paramiko.SSHClient.connect() for the
        corresponding session.

        @param session_uuid: the X2Go session's UUID registry hash
        @type session_uuid: C{str}
        @param username: user name to be used for session authentication
        @type username: C{str}
        @param password: the user's password for the X2Go server that is going to be 
            connected to
        @type password: C{str}
        @param passphrase: a passphrase to use for unlocking
            a private key in case the password is already needed for
            two-factor authentication
        @type passphrase: C{str}
        @param sshproxy_user: user name to be used for SSH proxy authentication
        @type sshproxy_user: C{str}
        @param sshproxy_password: the SSH proxy user's password
        @type sshproxy_password: C{str}
        @param sshproxy_passphrase: a passphrase to use for unlocking
            a private key needed for the SSH proxy host in case the sshproxy_password is already needed for
            two-factor authentication
        @type sshproxy_passphrase: C{str}
        @param add_to_known_hosts: non-Paramiko option, if C{True} paramiko.AutoAddPolicy() 
            is used as missing-host-key-policy. If set to C{False} L{checkhosts.X2GoInteractiveAddPolicy()} 
            is used
        @type add_to_known_hosts: C{bool}
        @param force_password_auth: disable SSH pub/priv key authentication mechanisms
            completely
        @type force_password_auth: C{bool}
        @param sshproxy_force_password_auth: disable SSH pub/priv key authentication mechanisms
            completely for SSH proxy connection
        @type sshproxy_force_password_auth: C{bool}

        @return: returns True if this method has been successful
        @rtype: C{bool}

        """
        self.apprimeLoadBalancer(username)
        _success = self.session_registry(session_uuid).connect(username=username,
                                                               password=password,
                                                               passphrase=passphrase,
                                                               sshproxy_user=sshproxy_user,
                                                               sshproxy_password=sshproxy_password,
                                                               sshproxy_passphrase=sshproxy_passphrase,
                                                               add_to_known_hosts=add_to_known_hosts,
                                                               force_password_auth=force_password_auth,
                                                               sshproxy_force_password_auth=sshproxy_force_password_auth,
                                                               apprime_server=X2GoClient.apprime_server,
                                                               apprime_port=X2GoClient.apprime_port,
                                                              )
        if self.auto_register_sessions:
            self.session_registry.register_available_server_sessions(profile_name=self.get_session_profile_name(session_uuid),
                                                                     newly_connected=True,
                                                                    )
        return _success
    __connect_session = connect_session

    def disconnect_session(self, session_uuid):
        """\
        Disconnect an L{X2GoSession} by closing down its Paramiko/SSH Transport thread.

        @param session_uuid: the X2Go session's UUID registry hash
        @type session_uuid: C{str}
        """
        self.session_registry(session_uuid).disconnect()
        if self.use_listsessions_cache:
            self.__update_cache_all_profiles()
    __disconnect_session = disconnect_session

    def set_session_print_action(self, session_uuid, print_action, **kwargs):
        """\
        If X2Go client-side printing is enable within an X2Go session you can use
        this method to alter the way how incoming print spool jobs are handled/processed.

        Currently, there are five different print actions available, each defined as an individual
        print action class:

            - B{PDFVIEW} (L{X2GoPrintActionPDFVIEW}): view an incoming spool job (a PDF file) 
              locally in a PDF viewer
            - B{PDFSAVE} (L{X2GoPrintActionPDFSAVE}): save an incoming spool job (a PDF file) 
              under a nice name in a designated folder
            - B{PRINT} (L{X2GoPrintActionPRINT}): really print the incoming spool job on a real printing device
            - B{PRINTCMD} L{X2GoPrintActionPRINTCMD}: on each incoming spool job execute an 
              external command that lets the client user handle the further processing of the 
              print job (PDF) file
            - B{DIALOG} (L{X2GoPrintActionDIALOG}): on each incoming spool job this print action 
              will call L{X2GoClient.HOOK_open_print_dialog()}

        Each of the print action classes accepts different print action arguments. For detail
        information on these print action arguments please refer to the constructor methods of 
        each class individually.

        @param session_uuid: the X2Go session's UUID registry hash
        @type session_uuid: C{str}
        @param print_action: one of the named above print actions, either as string or class instance
        @type print_action: C{str} or C{instance}
        @param kwargs: additional information for the given print action (print 
            action arguments), for possible print action arguments and their values see each individual
            print action class
        @type kwargs: C{dict}

        """
        self.session_registry(session_uuid).set_print_action(print_action=print_action, **kwargs)
    __set_session_print_action = set_session_print_action

    def set_session_window_title(self, session_uuid, title=''):
        """\
        Modify session window title. If the session ID does not occur in the
        given title, it will be prepended, so that every X2Go session window
        always contains the X2Go session ID of that window.

        @param session_uuid: the X2Go session's UUID registry hash
        @type session_uuid: C{str}
        @param title: new title for session window
        @type title: C{str}

        """
        self.session_registry(session_uuid).set_session_window_title(title=title)
    __set_session_window_title = set_session_window_title

    def raise_session_window(self, session_uuid):
        """\
        Try to lift the session window above all other windows and bring
        it to focus.

        @param session_uuid: the X2Go session's UUID registry hash
        @type session_uuid: C{str}
        """
        self.session_registry(session_uuid).raise_session_window()
    __raise_session_window = raise_session_window

    def session_auto_start_or_resume(self, session_uuid, newest=True, oldest=False, all_suspended=False, start=True):
        """\
        Automatically start or resume one or several sessions.

        This method is called from within the session itself on session registration, so this method
        can be used to handle auto-start/-resume events.

        @param session_uuid: the X2Go session's UUID registry hash
        @type session_uuid: C{str}
        @param newest: if resuming, only resume newest/youngest session
        @type newest: C{bool}
        @param oldest: if resuming, only resume oldest session
        @type oldest: C{bool}
        @param all_suspended: if resuming, resume all suspended sessions
        @type all_suspended: C{bool}
        @param start: if no session is to be resumed, start a new session
        @type start: C{bool}

        """
        self.session_registry(session_uuid).do_auto_start_or_resume(newest=newest, oldest=oldest, all_suspended=all_suspended, start=start, redirect_to_client=False)
    __session_auto_start_or_resume = session_auto_start_or_resume

    def start_session(self, session_uuid, **sessionopts):
        """\
        Start a new X2Go session on the remote X2Go server. This method
        will open---if everything has been successful till here---the X2Go 
        session window.

        Before calling this method you have to register your desired session
        with L{register_session} (initialization of session parameters) and 
        connect to it with L{connect_session} (authentication).

        @param session_uuid: the X2Go session's UUID registry hash
        @type session_uuid: C{str}
        @param sessionopts: pass-through of options directly to the session instance's L{X2GoSession.start()} method
        @type sessionopts: C{dict}

        @return: returns True if this method has been successful
        @rtype: C{bool}

        """
        # prevent the newly started session from being registered twice
        if self.auto_register_sessions:
            self.session_registry.disable_session_auto_registration()

        # start the actual session
        _retval = self.session_registry(session_uuid).start(**sessionopts)

        # re-enable session auto-registration...
        if self.auto_register_sessions:
            self.session_registry.enable_session_auto_registration()

        return _retval
    __start_session = start_session

    def share_desktop_session(self, session_uuid, desktop=None, user=None, display=None, share_mode=0, check_desktop_list=False, **sessionopts):
        """\
        Share another already running desktop session. Desktop sharing can be run
        in two different modes: view-only and full-access mode. Like new sessions
        a to-be-shared session has be registered first with the L{X2GoClient}
        instance.

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
        @param sessionopts: pass-through of options directly to the session instance's L{X2GoSession.share_desktop()} method
        @type sessionopts: C{dict}

        @return: True if the session could be successfully shared.
        @rtype: C{bool}

        @raise X2GoDesktopSharingException: if a given desktop ID does not specify an available desktop session

        """

        # X2GoClient.list_desktops() uses caching (if enabled, so we prefer lookups here...)
        if desktop:
            _desktop = desktop
            user = None
            display = None
        else:
            _desktop = '%s@%s' % (user, display)

        if not _desktop in self._X2GoClient__list_desktops(session_uuid):
            _desktop = '%s.0' % _desktop

        return self.session_registry(session_uuid).share_desktop(desktop=_desktop, share_mode=share_mode, check_desktop_list=check_desktop_list, **sessionopts)
    __share_desktop_session = share_desktop_session

    def resume_session(self, session_uuid=None, session_name=None, match_profile_name=None, **sessionopts):
        """\
        Resume or continue a suspended / running X2Go session on a
        remote X2Go server (as specified when L{register_session} was
        called).

        @param session_uuid: the X2Go session's UUID registry hash
        @type session_uuid: C{str}
        @param session_name: the server-side name of an X2Go session
        @type session_name: C{str}
        @param match_profile_name: only resume a session if this profile name matches
        @type match_profile_name: C{str}
        @param sessionopts: pass-through of options directly to the session instance's L{X2GoSession.resume()} method
        @type sessionopts: C{dict}

        @return: returns True if this method has been successful
        @rtype: C{bool}

        @raise X2GoClientException: if the method does not know what session to resume

        """
        try:
            if session_uuid is None and session_name is None:
                raise x2go_exceptions.X2GoClientException('can\'t resume a session without either session_uuid or session_name')
            if session_name is None and self.session_registry(session_uuid).session_name is None:
                raise x2go_exceptions.X2GoClientException('don\'t know which session to resume')
            if session_uuid is None:
                session_uuid = self.session_registry.get_session_of_session_name(session_name=session_name, return_object=False, match_profile_name=match_profile_name)
                return self.session_registry(session_uuid).resume(session_list=self._X2GoClient__list_sessions(session_uuid=session_uuid), **sessionopts)
            else:
                return self.session_registry(session_uuid).resume(session_name=session_name, session_list=self._X2GoClient__list_sessions(session_uuid=session_uuid), **sessionopts)
        except x2go_exceptions.X2GoControlSessionException:
            profile_name = self.get_session_profile_name(session_uuid)
            if self.session_registry(session_uuid).connected: self.HOOK_on_control_session_death(profile_name)
            self.disconnect_profile(profile_name)
    __resume_session = resume_session

    def suspend_session(self, session_uuid, session_name=None, match_profile_name=None, **sessionopts):
        """\
        Suspend an X2Go session.

        Normally, you will use this method to suspend a registered session that you
        have formerly started/resumed from within your recent
        L{X2GoClient} instance. For this you simply call this method
        using the session's C{session_uuid}, leave the C{session_name}
        empty.

        Alternatively, you can suspend a non-associated X2Go session:
        To do this you simply neeed to register (with the L{register_session}
        method) an X2Go session on the to-be-addressed remote X2Go server and 
        connect (L{connect_session}) to it. Then call this method with 
        the freshly obtained C{session_uuid} and the remote X2Go session
        name (as shown e.g. in x2golistsessions output).

        @param session_uuid: the X2Go session's UUID registry hash
        @type session_uuid: C{str}
        @param session_name: the server-side name of an X2Go session (for 
            non-associated session suspend)
        @type session_name: C{str}
        @param match_profile_name: only suspend a session if this profile name matches
        @type match_profile_name: C{str}
        @param sessionopts: pass-through of options directly to the session instance's L{X2GoSession.suspend()} method
        @type sessionopts: C{dict}

        @return: returns True if this method has been successful
        @rtype: C{bool}

        """
        try:
            if session_name is None:

                # make sure that the current list of shared folders is up-to-date before the session suspends
                self.get_shared_folders(session_uuid, check_list_mounts=True)

                return self.session_registry(session_uuid).suspend(**sessionopts)
            else:
                if match_profile_name is None:
                    running_sessions = self.session_registry.running_sessions()
                else:
                    running_sessions = self.session_registry.running_sessions_of_profile_name(match_profile_name)
                for session in running_sessions:
                    if session_name == session.get_session_name():
                        return session.suspend()
            return self.session_registry(session_uuid).control_session.suspend(session_name=session_name, **sessionopts)
        except x2go_exceptions.X2GoControlSessionException:
            profile_name = self.get_session_profile_name(session_uuid)
            if self.session_registry(session_uuid).conntected: self.HOOK_on_control_session_death(profile_name)
            self.disconnect_profile(profile_name)
    __suspend_session = suspend_session

    def terminate_session(self, session_uuid, session_name=None, match_profile_name=None, **sessionopts):
        """\
        Terminate an X2Go session.

        Normally you will use this method to terminate a registered session that you 
        have formerly started/resumed from within your recent
        L{X2GoClient} instance. For this you simply call this method
        using the session's C{session_uuid}, leave the C{session_name}
        empty.

        Alternatively, you can terminate a non-associated X2Go session:
        To do this you simply neeed to register (L{register_session})
        an X2Go session on the to-be-addressed remote X2Go server and 
        connect (L{connect_session}) to it. Then call this method with 
        the freshly obtained C{session_uuid} and the remote X2Go session
        name (as shown in e.g. x2golistsessions output).

        @param session_uuid: the X2Go session's UUID registry hash
        @type session_uuid: C{str}
        @param session_name: the server-side name of an X2Go session
        @type session_name: C{str}
        @param match_profile_name: only terminate a session if this profile name matches
        @type match_profile_name: C{str}
        @param sessionopts: pass-through of options directly to the session instance's L{X2GoSession.terminate()} method
        @type sessionopts: C{dict}

        @return: returns True if this method has been successful
        @rtype: C{bool}

        """
        try:
            if session_name is None:

                # make sure that the current list of shared folders is up-to-date before the session terminates
                self.get_shared_folders(session_uuid, check_list_mounts=True)

                return self.session_registry(session_uuid).terminate(**sessionopts)
            else:
                if match_profile_name is None:
                    terminatable_sessions = self.session_registry.running_sessions() + self.session_registry.suspended_sessions()
                else:
                    terminatable_sessions = self.session_registry.running_sessions_of_profile_name(match_profile_name) + self.session_registry.suspended_sessions_of_profile_name(match_profile_name)
                for session in terminatable_sessions:
                    if session_name == session.get_session_name():
                        return session.terminate()
            return self.session_registry(session_uuid).control_session.terminate(session_name=session_name, **sessionopts)
        except x2go_exceptions.X2GoControlSessionException:
            profile_name = self.get_session_profile_name(session_uuid)
            if self.session_registry(session_uuid).conntected: self.HOOK_on_control_session_death(profile_name)
            self.disconnect_profile(profile_name)
    __terminate_session = terminate_session

    def get_session_profile_name(self, session_uuid):
        """\
        Retrieve the profile name of the session that has been registered
        under C{session_uuid}.

        For profile based sessions this will be the profile name as used
        in x2goclient's »sessions« configuration file.

        For non-profile based session this will either be a C{profile_name} that 
        was passed to L{register_session} or it will be the application that
        instantiated this L{X2GoClient} instance.

        @param session_uuid: the X2Go session's UUID registry hash
        @type session_uuid: C{str}

        @return: X2Go session profile name
        @rtype: C{str}

        """
        return self.session_registry(session_uuid).get_profile_name()
    __get_session_profile_name = get_session_profile_name

    def get_session_profile_id(self, session_uuid):
        """\
        Retrieve the profile id of the session that has been registered
        under C{session_uuid}.

        For profile based sessions this will be the profile id as used
        in x2goclient's »sessions« configuration node (section header of
        a session profile in the config, normally a timestamp created on
        session profile creation/modification).

        For non-profile based sessions this will be a timestamp created on
        X2Go session registration by C{register_session}.

        @param session_uuid: the session profile name
        @type session_uuid: C{str}

        @return: the X2Go session profile's id
        @rtype: C{str}

        """
        return self.session_registry(session_uuid).profile_id
    __get_session_profile_id = get_session_profile_id

    def session_ok(self, session_uuid):
        """\
        Test if the X2Go session registered as C{session_uuid} is
        in a healthy state.

        @param session_uuid: the X2Go session's UUID registry hash
        @type session_uuid: C{str}

        @return: C{True} if session is ok, C{False} otherwise
        @rtype: C{bool}

        """
        return self.session_registry(session_uuid).session_ok()
    __session_ok = session_ok

    def is_session_connected(self, session_uuid):
        """\
        Test if the X2Go session registered as C{session_uuid} connected
        to the X2Go server.

        @param session_uuid: the X2Go session's UUID registry hash
        @type session_uuid: C{str}

        @return: C{True} if session is connected, C{False} otherwise
        @rtype: C{bool}

        """
        return self.session_registry(session_uuid).is_connected()
    __is_session_connected = is_session_connected

    def is_profile_connected(self, profile_name):
        """\
        Test if the X2Go given session profile has open connections
        to the X2Go server.

        @param profile_name: a valid session profile name
        @type profile_name: C{str}

        @return: C{True} if profile has a connected session, C{False} otherwise
        @rtype: C{bool}

        """
        return bool(self.client_connected_sessions_of_profile_name(profile_name=profile_name))
    __is_profile_connected = is_profile_connected

    def is_session_profile(self, profile_id_or_name):
        """\
        Test if the X2Go given session profile is configured in the client's C{sessions} file.

        @param profile_id_or_name: test existence of this session profile name (or id)
        @type profile_id_or_name: C{str}

        @return: C{True} if session profile exists, C{False} otherwise
        @rtype: C{bool}

        """
        return self.session_profiles.has_profile(profile_id_or_name)
    __is_session_profile = is_session_profile

    def is_session_running(self, session_uuid, session_name=None):
        """\
        Test if the X2Go session registered as C{session_uuid} is up 
        and running.

        @param session_uuid: the X2Go session's UUID registry hash
        @type session_uuid: C{str}
        @param session_name: the server-side name of an X2Go session
        @type session_name: C{str}

        @return: C{True} if session is running, C{False} otherwise
        @rtype: C{bool}

        """
        if session_name is None:
            return self.session_registry(session_uuid).is_running()
        else:
            return session_name in [ s for s in self.server_running_sessions(session_uuid) ]
    __is_session_running = is_session_running

    def is_session_suspended(self, session_uuid, session_name=None):
        """\
        Test if the X2Go session registered as C{session_uuid} 
        is in suspended state.

        @param session_uuid: the X2Go session's UUID registry hash
        @type session_uuid: C{str}
        @param session_name: the server-side name of an X2Go session
        @type session_name: C{str}

        @return: C{True} if session is suspended, C{False} otherwise
        @rtype: C{bool}

        """
        if session_name is None:
            return self.session_registry(session_uuid).is_suspended()
        else:
            return session_name in [ s for s in self.server_suspended_sessions(session_uuid) ]
    __is_session_suspended = is_session_suspended

    def has_session_terminated(self, session_uuid, session_name=None):
        """\
        Test if the X2Go session registered as C{session_uuid} 
        has terminated.

        @param session_uuid: the X2Go session's UUID registry hash
        @type session_uuid: C{str}
        @param session_name: the server-side name of an X2Go session
        @type session_name: C{str}

        @return: C{True} if session has terminated, C{False} otherwise
        @rtype: C{bool}

        """
        if session_name is None:
            return self.session_registry(session_uuid).has_terminated()
        else:
            return session_name not in [ s for s in self.server_running_sessions(session_uuid)  + self.server_suspended_sessions(session_uuid) ]
    __has_session_terminated = has_session_terminated

    def is_folder_sharing_available(self, session_uuid=None, profile_name=None):
        """\
        Test if local folder sharing is available for X2Go session with unique ID <session_uuid> or
        session profile <profile_name>.

        @param session_uuid: the X2Go session's UUID registry hash
        @type session_uuid: C{str}
        @param profile_name: alternatively, the profile name can be used to perform this query
        @type profile_name: C{str}

        @return: returns C{True} if the profile/session supports local folder sharing
        @rtype: C{bool}

        """
        if session_uuid is None and profile_name:
            session_uuid = self._X2GoClient__get_master_session(profile_name, return_object=False)
        if session_uuid:
            try:
                return self.session_registry(session_uuid).is_folder_sharing_available()
            except x2go_exceptions.X2GoSessionRegistryException:
                return False
        else:
            self.logger('Cannot find a terminal session for profile ,,%s\'\' that can be used to query folder sharing capabilities' % profile_name, loglevel=log.loglevel_INFO)
            return False
    __is_folder_sharing_available = is_folder_sharing_available
    __profile_is_folder_sharing_available = is_folder_sharing_available
    __session_is_folder_sharing_available = is_folder_sharing_available

    def share_local_folder(self, session_uuid=None, local_path=None, profile_name=None, folder_name=None):
        """\
        Share a local folder with the X2Go session registered as C{session_uuid}.

        When calling this method the given client-side folder is mounted
        on the X2Go server (via sshfs) and (if in desktop mode) provided as a 
        desktop icon on your remote session's desktop.

        @param session_uuid: the X2Go session's UUID registry hash
        @type session_uuid: C{str}
        @param local_path: the full path to an existing folder on the local (client-side)
            file system
        @type local_path: C{str}
        @param folder_name: synonymous to C{local_path}
        @type folder_name: C{str}
        @param profile_name: alternatively, the profile name can be used to share local folders
        @type profile_name: C{str}

        @return: returns C{True} if the local folder has been successfully mounted
        @rtype: C{bool}

        """
        # compat for Python-X2Go (<=0.1.1.6)
        if folder_name: local_path = folder_name

        if session_uuid is None and profile_name:
            session_uuid = self._X2GoClient__get_master_session(profile_name, return_object=False)
        if session_uuid:
            try:
                return self.session_registry(session_uuid).share_local_folder(local_path=local_path)
            except x2go_exceptions.X2GoSessionException:
                return False
        else:
            self.logger('Cannot find a terminal session for profile ,,%s\'\' to share a local folder with' % profile_name, loglevel=log.loglevel_WARN)
            return False
    __share_local_folder = share_local_folder
    __share_local_folder_with_session = share_local_folder
    __share_local_folder_with_profile = share_local_folder

    def unshare_all_local_folders(self, session_uuid=None, profile_name=None):
        """\
        Unshare all local folders mounted in X2Go session registered as
        C{session_uuid}.

        When calling this method all client-side mounted folders on the X2Go 
        server (via sshfs) for session with ID <session_uuid> will get
        unmounted.

        @param session_uuid: the X2Go session's UUID registry hash
        @type session_uuid: C{str}
        @param profile_name: alternatively, the profile name can be used to unshare
            mounted folders
        @type profile_name: C{str}

        @return: returns C{True} if all local folders could be successfully unmounted
        @rtype: C{bool}

        """
        if session_uuid is None and profile_name:
            session_uuid = self._X2GoClient__get_master_session(profile_name, return_object=False)
        if session_uuid:
            return self.session_registry(session_uuid).unshare_all_local_folders()
        else:
            self.logger('Cannot find a terminal session for profile ,,%s\'\' from which to unmount local folders' % profile_name, loglevel=log.loglevel_WARN)
            return False
    unshare_all_local_folders_from_session = unshare_all_local_folders
    unshare_all_local_folders_from_profile = unshare_all_local_folders
    __unshare_all_local_folders_from_session = unshare_all_local_folders
    __unshare_all_local_folders_from_profile = unshare_all_local_folders

    def unshare_local_folder(self, session_uuid=None, profile_name=None, local_path=None):
        """\
        Unshare local folder that is mounted in the X2Go session registered as
        C{session_uuid}.

        When calling this method the given client-side mounted folder on the X2Go 
        server (via sshfs) for session with ID <session_uuid> will get
        unmounted.

        @param session_uuid: the X2Go session's UUID registry hash
        @type session_uuid: C{str}
        @param profile_name: alternatively, the profile name can be used to unshare
            mounted folders
        @type profile_name: C{str}
        @param local_path: the full path of a local folder that is mounted within X2Go
            session with session ID <session_uuid> (or recognized via profile name) and that
            shall be unmounted from that session.
        @type local_path: C{str}

        @return: returns C{True} if all local folders could be successfully unmounted
        @rtype: C{bool}

        """
        if session_uuid is None and profile_name:
            session_uuid = self._X2GoClient__get_master_session(profile_name, return_object=False)
        if session_uuid:
            return self.session_registry(session_uuid).unshare_local_folder(local_path=local_path)
        else:
            self.logger('Cannot find a terminal session for profile ,,%s\'\' from which to unmount local folders' % profile_name, loglevel=log.loglevel_WARN)
            return False
    unshare_local_folder_from_session = unshare_local_folder
    unshare_local_folder_from_profile = unshare_local_folder
    __unshare_local_folder_from_session = unshare_local_folder
    __unshare_local_folder_from_profile = unshare_local_folder

    def get_shared_folders(self, session_uuid=None, profile_name=None, check_list_mounts=False):
        """\
        Get a list of local folders mounted within X2Go session with session hash <session_uuid>
        from this client.

        @param session_uuid: the X2Go session's UUID registry hash
        @type session_uuid: C{str}
        @param profile_name: alternatively, the profile name can be used to get mounted folders of a session connected profile
        @type profile_name: C{str}
        @param check_list_mounts: query the server-side mount list for up-to-date information
        @type check_list_mounts: C{bool}

        @return: returns a C{list} of those local folder names that are mounted within X2Go session <session_uuid>.
        @rtype: C{list}

        """
        if session_uuid is None and profile_name:
            session_uuid = self._X2GoClient__get_master_session(profile_name, return_object=False)

        if session_uuid and profile_name is None:
            profile_name = self.session_registry(session_uuid).get_profile_name()

        if session_uuid and profile_name:

            mounts = None
            if check_list_mounts:
                _mounts = self.list_mounts_by_profile_name(profile_name)
                mounts = []
                for mount_list in _mounts.values():
                    mounts.extend(mount_list)

            return self.session_registry(session_uuid).get_shared_folders(check_list_mounts=check_list_mounts, mounts=mounts)

    session_get_shared_folders = get_shared_folders
    profile_get_shared_folders = get_shared_folders
    __session_get_shared_folders = get_shared_folders
    __profile_get_shared_folders = get_shared_folders

    def get_master_session(self, profile_name, return_object=True, return_session_name=False):
        """\
        Retrieve the master session of a specific profile.

        @param profile_name: the profile name that we query the master session of
        @type profile_name: C{str}
        @param return_object: return L{X2GoSession} instance
        @type return_object: C{bool}
        @param return_session_name: return X2Go session name
        @type return_session_name: C{bool}

        @return: a session list (as UUID hashes, objects, profile names/IDs or session names)
        @rtype: C{list}

        """
        return self.session_registry.get_master_session(profile_name, return_object=return_object, return_session_name=return_session_name)
    profile_master_session = get_master_session
    __get_master_session = get_master_session
    __profile_master_session = profile_master_session

    ###
    ### Provide access to the X2GoClient's session registry
    ### 

    def client_connected_sessions(self, return_objects=False, return_profile_names=False, return_profile_ids=False, return_session_names=False):
        """\
        Retrieve a list of X2Go sessions that this L{X2GoClient} instance is connected to.

        @param return_objects: return as list of X2Go session objects
        @type return_objects: C{bool}
        @param return_profile_names: return as list of session profile names
        @type return_profile_names: C{bool}
        @param return_profile_ids: return as list of session profile IDs
        @type return_profile_ids: C{bool}
        @param return_session_names: return as list of session names
        @type return_session_names: C{bool}

        @return: list of connected sessions
        @rtype: C{list}

        """
        return self.session_registry.connected_sessions(return_objects=return_objects, return_profile_names=return_profile_names, return_profile_ids=return_profile_ids, return_session_names=return_session_names)
    __client_connected_sessions = client_connected_sessions

    @property
    def client_has_connected_sessions(self):
        """\
        Equals C{True} if there are any connected sessions with this L{X2GoClient} instance.

        """
        return self.session_registry.has_connected_sessions
    __client_has_connected_sessions = client_has_connected_sessions

    def client_associated_sessions(self, return_objects=False, return_profile_names=False, return_profile_ids=False, return_session_names=False):
        """\
        Retrieve a list of X2Go sessions associated to this L{X2GoClient} instance.

        @param return_objects: return as list of X2Go session objects
        @type return_objects: C{bool}
        @param return_profile_names: return as list of session profile names
        @type return_profile_names: C{bool}
        @param return_profile_ids: return as list of session profile IDs
        @type return_profile_ids: C{bool}
        @param return_session_names: return as list of session names
        @type return_session_names: C{bool}

        @return: list of associated sessions
        @rtype: C{list}

        """
        return self.session_registry.associated_sessions(return_objects=return_objects, return_profile_names=return_profile_names, return_profile_ids=return_profile_ids, return_session_names=return_session_names)
    __client_associated_sessions = client_associated_sessions

    @property
    def client_has_associated_sessions(self):
        """\
        Equals C{True} if there are any associated sessions with this L{X2GoClient} instance.

        """
        return self.session_registry.has_associated_sessions
    __client_has_associated_sessions = client_has_associated_sessions

    def client_running_sessions(self, return_objects=False, return_profile_names=False, return_profile_ids=False, return_session_names=False):
        """\
        Retrieve a list of running X2Go sessions.

        @param return_objects: return as list of X2Go session objects
        @type return_objects: C{bool}
        @param return_profile_names: return as list of session profile names
        @type return_profile_names: C{bool}
        @param return_profile_ids: return as list of session profile IDs
        @type return_profile_ids: C{bool}
        @param return_session_names: return as list of session names
        @type return_session_names: C{bool}

        @return: list of running sessions
        @rtype: C{list}

        """
        return self.session_registry.running_sessions(return_objects=return_objects, return_profile_names=return_profile_names, return_profile_ids=return_profile_ids, return_session_names=return_session_names)
    __client_running_sessions = client_running_sessions

    @property
    def client_has_running_sessions(self):
        """\
        Equals C{True} if there are any running sessions with this L{X2GoClient} instance.

        """
        return self.session_registry.has_running_sessions
    __client_has_running_sessions = client_has_running_sessions

    def client_suspended_sessions(self, return_objects=False, return_profile_names=False, return_profile_ids=False, return_session_names=False):
        """\
        Retrieve a list of suspended X2Go sessions.

        @param return_objects: return as list of X2Go session objects
        @type return_objects: C{bool}
        @param return_profile_names: return as list of session profile names
        @type return_profile_names: C{bool}
        @param return_profile_ids: return as list of session profile IDs
        @type return_profile_ids: C{bool}
        @param return_session_names: return as list of session names
        @type return_session_names: C{bool}

        @return: list of suspended sessions
        @rtype: C{list}

        """
        return self.session_registry.running_sessions(return_objects=return_objects, return_profile_names=return_profile_names, return_profile_ids=return_profile_ids, return_session_names=return_session_names)
    __client_suspended_sessions = client_suspended_sessions

    @property
    def client_has_suspended_sessions(self):
        """\
        Equals C{True} if there are any suspended sessions with this L{X2GoClient} instance.

        """
        return self.session_registry.has_suspended_sessions
    __client_has_suspended_sessions = client_has_suspended_sessions

    def client_registered_sessions(self, return_objects=True, return_profile_names=False, return_profile_ids=False, return_session_names=False):
        """\
        Retrieve a list of registered X2Go sessions.

        @param return_objects: return as list of X2Go session objects
        @type return_objects: C{bool}
        @param return_profile_names: return as list of session profile names
        @type return_profile_names: C{bool}
        @param return_profile_ids: return as list of session profile IDs
        @type return_profile_ids: C{bool}
        @param return_session_names: return as list of session names
        @type return_session_names: C{bool}

        @return: list of registered sessions
        @rtype: C{list}

        """
        return self.session_registry.registered_sessions(return_objects=return_objects, return_profile_names=return_profile_names, return_profile_ids=return_profile_ids, return_session_names=return_session_names)
    __client_registered_sessions = client_registered_sessions

    @property
    def client_control_sessions(self):
        """\
        Equals a list of all registered X2Go control sessions.

        """
        return self.session_registry.control_sessions
    __client_control_sessions = client_control_sessions

    def client_control_session_of_profile_name(self, profile_name):
        """\
        Retrieve control session for profile name <profile_name>.

        @param profile_name: profile name
        @type profile_name: C{str}

        @return: control session instance
        @rtype: C{X2GoControlSession} instance

        """
        return self.session_registry.control_session_of_profile_name(profile_name)
    __client_control_session_of_profile_name = client_control_session_of_profile_name

    def get_server_versions(self, profile_name, component=None, force=False):
        """\
        Query the server configured in session profile <profile_name> for the list of install X2Go components
        and its versions.

        @param profile_name: use the control session of this profile to query the X2Go server for its component list
        @type profile_name: C{str}
        @param component: only return the version of a specific component
        @type component: C{str}
        @param force: refresh component/version data by a query to the server
        @type force: C{bool}

        @return: dictionary of server components (as keys) and their versions (as values) or the version of the given <component>
        @rtype: C{dict} or C{str}

        @raise X2GoClientException: if component is not available on the X2Go Server.

        """
        control_session = self.client_control_session_of_profile_name(profile_name)
        if component is None:
            return control_session.get_server_versions(force=force)
        else:
            try:
                return control_session.get_server_versions(force=force)[component]
            except KeyError:
                raise x2go_exceptions.X2GoClientException('No such component on X2Go Server')
    __get_server_versions = get_server_versions
    get_server_components = get_server_versions
    __get_server_components = get_server_components

    def get_server_features(self, profile_name, force=False):
        """\
        Query the server configured in session profile <profile_name> for the list of server-side
        X2Go features.

        @param profile_name: use the control session of this profile to query the X2Go server for its feature list
        @type profile_name: C{str}
        @param force: refresh feature list by a query to the server
        @type force: C{bool}

        @return: list of server feature names (as returned by server-side command ,,x2gofeaturelist''
        @rtype: C{list}

        """
        control_session = self.client_control_session_of_profile_name(profile_name)
        return control_session.get_server_features(force=force)
    __get_server_features = get_server_features

    def get_apprime_server_info(self, profile_name):
        """\
        Query the server configured in session profile <profile_name> for performance related and general info.

        @param profile_name: use the control session of this profile to query the X2Go server for its feature list
        @type profile_name: C{str}
        @param force: refresh feature list by a query to the server
        @type force: C{bool}

        @return: list of server feature names (as returned by server-side command ,,x2gofeaturelist''
        @rtype: C{list}

        """
        control_session = self.client_control_session_of_profile_name(profile_name)
        return control_session.get_apprime_server_info()

    def has_server_feature(self, profile_name, feature):
        """\
        Query the server configured in session profile <profile_name> for the availability
        of a certain server feature.

        @param profile_name: use the control session of this profile to query the X2Go server for its feature
        @type profile_name: C{str}
        @param feature: test the availability of this feature on the X2Go server
        @type feature: C{str}

        @return: C{True} if the feature is available on the queried server
        @rtype: C{bool}

        """
        control_session = self.client_control_session_of_profile_name(profile_name)
        return feature in control_session.get_server_features()
    __has_server_feature = has_server_feature

    def client_registered_session_of_name(self, session_name, return_object=False):
        """\
        Retrieve X2Go session of a given session name.

        @param session_name: session name
        @type session_name: C{str}

        @return: session instance of the given name
        @rtype: C{X2GoSession} or C{str}

        """
        return self.session_registry.get_session_of_session_name(session_name, return_object=return_object)
    __client_registered_session_of_name = client_registered_session_of_name

    def client_has_registered_session_of_name(self, session_name):
        """\
        Equals C{True} if there is a registered session of name <session_name>.

        @param session_name: session name
        @type session_name: C{str}

        @return: C{True} if the given session is registered
        @rtype: C{bool}

        """
        return self.client_registered_session_of_name(session_name) is not None
    __client_has_registered_session_of_name = client_registered_session_of_name

    def client_registered_sessions_of_profile_name(self, profile_name, return_objects=False, return_session_names=False):
        """\
        Retrieve registered X2Go sessions of profile name <profile_name>.

        @param profile_name: profile name
        @type profile_name: C{str}
        @param return_objects: return as list of X2Go session objects
        @type return_objects: C{bool}
        @param return_session_names: return as list of session names
        @type return_session_names: C{bool}

        @return: list of registered sessions of profile name
        @rtype: C{list}

        """
        return self.session_registry.registered_sessions_of_profile_name(profile_name, return_objects=return_objects, return_session_names=return_session_names)
    __client_registered_sessions_of_profile_name = client_registered_sessions_of_profile_name

    def client_connected_sessions_of_profile_name(self, profile_name, return_objects=False, return_session_names=False):
        """\
        Retrieve connected X2Go sessions of profile name <profile_name>.

        @param profile_name: profile name
        @type profile_name: C{str}
        @param return_objects: return as list of X2Go session objects
        @type return_objects: C{bool}
        @param return_session_names: return as list of session names
        @type return_session_names: C{bool}

        @return: list of connected sessions of profile name
        @rtype: C{list}

        """
        return self.session_registry.connected_sessions_of_profile_name(profile_name, return_objects=return_objects, return_session_names=return_session_names)
    __client_connected_sessions_of_profile_name = client_connected_sessions_of_profile_name

    def client_associated_sessions_of_profile_name(self, profile_name, return_objects=False, return_session_names=False):
        """\
        Retrieve associated X2Go sessions of profile name <profile_name>.

        @param profile_name: profile name
        @type profile_name: C{str}
        @param return_objects: return as list of X2Go session objects
        @type return_objects: C{bool}
        @param return_session_names: return as list of session names
        @type return_session_names: C{bool}

        @return: list of associated sessions of profile name
        @rtype: C{list}

        """
        return self.session_registry.associated_sessions_of_profile_name(profile_name, return_objects=return_objects, return_session_names=return_session_names)
    __client_associated_sessions_of_profile_name = client_associated_sessions_of_profile_name

    def client_pubapp_sessions_of_profile_name(self, profile_name, return_objects=False, return_session_names=False):
        """\
        Retrieve X2Go sessions of profile name <profile_name> that provide published applications.

        @param profile_name: profile name
        @type profile_name: C{str}
        @param return_objects: return as list of X2Go session objects
        @type return_objects: C{bool}
        @param return_session_names: return as list of session names
        @type return_session_names: C{bool}

        @return: list of application publishing sessions of profile name
        @rtype: C{list}

        """
        return self.session_registry.pubapp_sessions_of_profile_name(profile_name, return_objects=return_objects, return_session_names=return_session_names)
    __client_pubapp_sessions_of_profile_name = client_pubapp_sessions_of_profile_name


    def client_running_sessions_of_profile_name(self, profile_name, return_objects=False, return_session_names=False):
        """\
        Retrieve running X2Go sessions of profile name <profile_name>.

        @param profile_name: profile name
        @type profile_name: C{str}
        @param return_objects: return as list of X2Go session objects
        @type return_objects: C{bool}
        @param return_session_names: return as list of session names
        @type return_session_names: C{bool}

        @return: list of running sessions of profile name
        @rtype: C{list}

        """
        return self.session_registry.running_sessions_of_profile_name(profile_name, return_objects=return_objects, return_session_names=return_session_names)
    __client_running_sessions_of_profile_name = client_running_sessions_of_profile_name

    def client_suspended_sessions_of_profile_name(self, profile_name, return_objects=False, return_session_names=False):
        """\
        Retrieve suspended X2Go sessions of profile name <profile_name>.

        @param profile_name: profile name
        @type profile_name: C{str}
        @param return_objects: return as list of X2Go session objects
        @type return_objects: C{bool}
        @param return_session_names: return as list of session names
        @type return_session_names: C{bool}

        @return: list of suspended sessions of profile name
        @rtype: C{list}

        """
        return self.session_registry.suspended_sessions_of_profile_name(profile_name, return_objects=return_objects, return_session_names=return_session_names)
    __client_suspended_sessions_of_profile_name = client_suspended_sessions_of_profile_name

    ###
    ### Provide access to the X2Go server's sessions DB
    ### 

    def server_is_alive(self, session_uuid):
        """\
        Test if server that corresponds to the terminal session C{session_uuid} is alive.

        If the session is not connected anymore the L{X2GoClient.HOOK_on_control_session_death()} gets called.

        @param session_uuid: the X2Go session's UUID registry hash
        @type session_uuid: C{str}

        @return: C{True} if X2Go server connection for L{X2GoSession} instance with <session_uuid> is alive.
        @rtype: C{bool}

        @raise X2GoControlSessionException: if the session is not connected anymore; in that case the L{HOOK_on_control_session_death} gets called.

        """
        try:
            return self.session_registry(session_uuid).is_alive()
        except x2go_exceptions.X2GoControlSessionException:
            profile_name = self.get_session_profile_name(session_uuid)
            if self.session_registry(session_uuid).conntected: self.HOOK_on_control_session_death(profile_name)
            self.disconnect_profile(profile_name)
            return False
    __server_is_alive = server_is_alive

    def all_servers_are_alive(self):
        """\
        Test vitality of all connected X2Go servers.

        @return: C{True} if all connected X2Go servers are alive.
        @rtype: C{bool}

        """
        _all_alive = True
        for session_uuid in self.client_connected_sessions():
            _all_alive = _all_alive and self.server_is_alive(session_uuid)
        return _all_alive
    __all_servers_are_alive = all_servers_are_alive

    def server_valid_x2gouser(self, session_uuid, username=None):
        """\
        Check if user is allowed to start an X2Go session on a remote server.

        @param session_uuid: the X2Go session's UUID registry hash
        @type session_uuid: C{str}
        @param username: user name to test validity for
        @type username: C{str}

        @return: Is remote user allowed to start an X2Go session?
        @rtype: C{str}

        """
        return self.session_registry(session_uuid).user_is_x2gouser(username=username)
    __server_valid_x2gouser = server_valid_x2gouser

    def server_running_sessions(self, session_uuid):
        """\
        Retrieve a list of session names of all server-side running sessions (including those not
        instantiated by our L{X2GoClient} instance).

        @param session_uuid: the X2Go session's UUID registry hash
        @type session_uuid: C{str}

        @return: list of session names
        @rtype: C{list}

        @raise X2GoClientException: if the session with UUID C{session_uuid} is not connected

        """
        if self._X2GoClient__is_session_connected(session_uuid):
            session_list = self._X2GoClient__list_sessions(session_uuid)
            return [ key for key in session_list.keys() if session_list[key].status == 'R' ]
        else:
            raise x2go_exceptions.X2GoClientException('X2Go session with UUID %s is not connected' % session_uuid)
    __server_running_sessions = server_running_sessions

    def server_has_running_sessions(self, session_uuid):
        """\
        Equals C{True} if the X2Go server has any running sessions.

        @param session_uuid: the X2Go session's UUID registry hash
        @type session_uuid: C{str}
        @return: C{True}, if there are running sessions
        @rtype: C{bool}

        """
        return len(self._X2GoClient__server_running_sessions(session_uuid)) > 0
    __server_has_running_sessions = server_has_running_sessions

    def server_has_running_session_of_name(self, session_uuid, session_name):
        """\
        Equals C{True} if the X2Go server has a running session of name <session_name>.

        @param session_uuid: the X2Go session's UUID registry hash
        @type session_uuid: C{str}
        @param session_name: session name
        @type session_name: C{str}

        """
        return session_name in self._X2GoClient__server_running_sessions(session_uuid)
    __server_has_running_session_of_name = server_has_running_session_of_name

    def server_suspended_sessions(self, session_uuid):
        """\
        Retrieve a list of session names of all server-side suspended sessions (including those not
        instantiated by our L{X2GoClient} instance).

        @param session_uuid: the X2Go session's UUID registry hash
        @type session_uuid: C{str}

        @return: list of session names
        @rtype: C{list}

        @raise X2GoClientException: if the session with UUID C{session_uuid} is not connected

        """
        if self._X2GoClient__is_session_connected(session_uuid):
            session_list = self._X2GoClient__list_sessions(session_uuid)
            return [ key for key in session_list.keys() if session_list[key].status == 'S' ]
        else:
            raise x2go_exceptions.X2GoClientException('X2Go session with UUID %s is not connected' % session_uuid)
    __server_suspended_sessions = server_suspended_sessions

    def server_has_suspended_sessions(self, session_uuid):
        """\
        Equals C{True} if the X2Go server has any suspended sessions.

        @param session_uuid: the X2Go session's UUID registry hash
        @type session_uuid: C{str}

        """
        return len(self._X2GoClient__server_suspended_sessions(session_uuid)) > 0
    __server_has_suspended_sessions = server_has_suspended_sessions

    def server_has_suspended_session_of_name(self, session_uuid, session_name):
        """\
        Equals C{True} if the X2Go server has a suspended session of name <session_name>.

        @param session_uuid: the X2Go session's UUID registry hash
        @type session_uuid: C{str}
        @param session_name: session name
        @type session_name: C{str}
        @return: C{True}, if there are running sessions
        @rtype: C{bool}

        """
        return session_name in self._X2GoClient__server_suspended_sessions(session_uuid)
    __server_has_suspended_session_of_name = server_has_suspended_session_of_name

    ###
    ### CLIENT OPERATIONS ON SESSIONS (listing sessions, terminating non-associated sessions etc.)
    ###

    def clean_sessions(self, session_uuid, published_applications=False):
        """\
        Find running X2Go sessions that have previously been started by the
        connected user on the remote X2Go server and terminate them.

        Before calling this method you have to setup a pro forma remote X2Go session 
        with L{X2GoClient.register_session()} (even if you do not intend to open 
        a real X2Go session window on the remote server) and connect to this session (with
        L{X2GoClient.connect_session()}.

        @param session_uuid: the X2Go session's UUID registry hash
        @type session_uuid: C{str}
        @param published_applications: if C{True}, also terminate sessions that are published applications
            provider
        @type published_applications: C{bool}

        """
        _destroy_terminals = not ( self.auto_update_sessionregistry == True)
        try:
            session = self.session_registry(session_uuid)
            session.clean_sessions(destroy_terminals=_destroy_terminals, published_applications=published_applications)
        except x2go_exceptions.X2GoSessionRegistryException:
            # silently ignore a non-registered session UUID (mostly occurs during disconnects)
            pass
    __clean_sessions = clean_sessions

    def list_sessions(self, session_uuid=None,
                      profile_name=None, profile_id=None,
                      no_cache=False, refresh_cache=False,
                      update_sessionregistry=True,
                      register_sessions=False,
                      raw=False):
        """\
        Use the X2Go session registered under C{session_uuid} to
        retrieve a list of running or suspended X2Go sessions from the
        connected X2Go server (for the authenticated user).

        Before calling this method you have to setup a pro forma remote X2Go session 
        with L{X2GoClient.register_session()} (even if you do not intend to open 
        a real X2Go session window on the remote server) and connect to this session (with
        L{X2GoClient.connect_session()}.

        @param session_uuid: the X2Go session's UUID registry hash
        @type session_uuid: C{str}
        @param profile_name: use profile name instead of <session_uuid>
        @type profile_name: C{str}
        @param profile_id: use profile id instead of <profile_name> or <session_uuid>
        @type profile_id: C{str}
        @param no_cache: do not get the session list from cache, query the X2Go server directly
        @type no_cache: C{bool}
        @param refresh_cache: query the X2Go server directly and update the session list cache
            with the new information
        @type refresh_cache: C{bool}
        @param update_sessionregistry: query the X2Go server directly and update the
            session registry according to the obtained information
        @type update_sessionregistry: C{bool}
        @param register_sessions: query the X2Go server directly and register newly found X2Go session
            as L{X2GoSession} instances associated to this L{X2GoClient} instance
        @type register_sessions: C{bool}
        @param raw: output the session list in X2Go's raw C{x2golistsessions} format
        @type raw: C{bool}

        @raise X2GoClientException: if the session profile specified by C{session_uuid}, C{profile_name} or C{profile_id} is not connected
            or if none of the named parameters has been specified

        """
        if profile_id is not None:
            profile_name = self.to_profile_name(profile_id)

        if profile_name is not None:

            _connected_sessions = self.client_connected_sessions_of_profile_name(profile_name, return_objects=True)
            if _connected_sessions:
                # it does not really matter which session to use for getting a server-side session list
                # thus, we simply grab the first that comes in...
                session_uuid = _connected_sessions[0].get_uuid()
            else:
                raise x2go_exceptions.X2GoClientException('profile ,,%s\'\' is not connected' % profile_name)

        elif session_uuid is not None:
            pass
        else:
            raise x2go_exceptions.X2GoClientException('must either specify session UUID or profile name')

        if raw:
            return self.session_registry(session_uuid).list_sessions(raw=raw)

        if not self.use_listsessions_cache or not self.auto_update_listsessions_cache or no_cache:
            _session_list = self.session_registry(session_uuid).list_sessions()
        elif refresh_cache:
            self.update_cache_by_session_uuid(session_uuid)
            _session_list = self.listsessions_cache.list_sessions(session_uuid)
        else:
            # if there is no cache for this session_uuid available, make sure the cache gets updated
            # before reading from it...
            if self.use_listsessions_cache and (not self.listsessions_cache.is_cached(session_uuid=session_uuid, cache_type='sessions') or refresh_cache):
                self.__update_cache_by_session_uuid(session_uuid)
            _session_list = self.listsessions_cache.list_sessions(session_uuid)

        if update_sessionregistry:
            self.update_sessionregistry_status_by_profile_name(profile_name=self.get_session_profile_name(session_uuid), session_list=_session_list)

        if register_sessions:
            self.session_registry.register_available_server_sessions(profile_name=self.get_session_profile_name(session_uuid),
                                                                     session_list=_session_list)

        return _session_list
    __list_sessions = list_sessions

    def list_desktops(self, session_uuid=None, 
                      profile_name=None, profile_id=None,
                      no_cache=False, refresh_cache=False,
                      exclude_session_types=[],
                      raw=False):
        """\
        Use the X2Go session registered under C{session_uuid} to
        retrieve a list of X2Go desktop sessions that are available
        for desktop sharing.

        Before calling this method you have to setup a pro forma remote X2Go session
        with L{X2GoClient.register_session()} (even if you do not intend to open
        a real X2Go session window on the remote server) and connect to this session (with
        L{X2GoClient.connect_session()}.

        @param session_uuid: the X2Go session's UUID registry hash
        @type session_uuid: C{str}
        @param profile_name: use profile name instead of <session_uuid>
        @type profile_name: C{str}
        @param profile_id: use profile id instead of <profile_name> or <session_uuid>
        @type profile_id: C{str}
        @param no_cache: do not get the desktop list from cache, query the X2Go server directly
        @type no_cache: C{bool}
        @param refresh_cache: query the X2Go server directly and update the desktop list cache
            with the new information
        @type refresh_cache: C{bool}
        @param exclude_session_types: session types (e.g. "D", "R", "S" or "P") to be excluded from the
            returned list of sharable desktops (this only works for sharing someone's own sessions, for
            sharing other users' sessions, the X2Go Desktop Sharing decides on what is sharable and what not).
        @type exclude_session_types: C{list}
        @param raw: output the session list in X2Go's raw C{x2golistdesktops} format
        @type raw: C{bool}

        @return: a list of available desktops to be shared
        @rtype: C{list}

        @raise X2GoClientException: if the session profile specified by C{session_uuid}, C{profile_name} or C{profile_id} is not connected
            or if none of the named parameters has been specified

        """
        if profile_id is not None:
            profile_name = self.to_profile_name(profile_id)

        if profile_name is not None:

            _connected_sessions = self.client_connected_sessions_of_profile_name(profile_name, return_objects=True)
            if _connected_sessions:
                # it does not really matter which session to use for getting a server-side session list
                # thus, we simply grab the first that comes in...
                session_uuid = _connected_sessions[0].get_uuid()
            else:
                raise x2go_exceptions.X2GoClientException('profile ,,%s\'\' is not connected' % profile_name)

        elif session_uuid is not None:
            pass
        else:
            raise x2go_exceptions.X2GoClientException('must either specify session UUID or profile name')

        if raw:
            return self.session_registry(session_uuid).list_desktops(raw=raw)

        if not self.use_listsessions_cache or not self.auto_update_listdesktops_cache or no_cache:
            _desktop_list = self.session_registry(session_uuid).list_desktops()
        else:
            if self.use_listsessions_cache and (not self.listsessions_cache.is_cached(session_uuid=session_uuid, cache_type='desktops') or refresh_cache):
                self.__update_cache_by_session_uuid(session_uuid, update_sessions=False, update_desktops=True)
            _desktop_list = self.listsessions_cache.list_desktops(session_uuid)

        # attempt to exclude session types that are requested to be excluded
        if exclude_session_types:

            # create an X2GoServerSessionList* instance and operate on that
            session_list = self.list_backend()
            session_list.set_sessions(self._X2GoClient__list_sessions(session_uuid))

            # search for a match among the listed sessions
            for desktop in copy.deepcopy(_desktop_list):
                user = desktop.split('@')[0]
                if user == self.get_session_username(session_uuid):
                    display = desktop.split('@')[1]
                    session = session_list.get_session_with('display', display, hostname=self.get_session_server_hostname(session_uuid))
                    if session is None: continue
                    if session.get_session_type() in exclude_session_types:
                        _desktop_list.remove(desktop)

        return _desktop_list
    __list_desktops = list_desktops

    def list_mounts_by_profile_name(self, profile_name,
                                    no_cache=False, refresh_cache=False,
                                    raw=False):
        """
        For a given profil C{profile_name} to
        retrieve its list of mounted client shares for that session.

        @param profile_name: a valid profile name
        @type profile_name: C{str}
        @param no_cache: do not get the session list from cache, query the X2Go server directly
        @type no_cache: C{bool}
        @param raw: output the session list in X2Go's raw C{x2golistmounts} format
        @type raw: C{bool}

        @return: list of server-side mounted shares for a given profile name
        @rtype: C{list}

        """
        sessions = [ s for s in self.client_running_sessions(return_objects=True) if s.get_profile_name() == profile_name ]

        if raw:
            _list_mounts = ""
            for session in sessions:
                _list_mounts += self.__list_mounts(session_uuid=session(), no_cache=no_cache, refresh_cache=refresh_cache, raw=True)
        else:
            _list_mounts = {}
            for session in sessions:
                _list_mounts.update(self.__list_mounts(session_uuid=session(), no_cache=no_cache, refresh_cache=refresh_cache, raw=False))
        return _list_mounts
    __list_mounts_by_profile_name = list_mounts_by_profile_name

    def list_mounts(self, session_uuid,
                    no_cache=False, refresh_cache=False,
                    raw=False):
        """\
        Use the X2Go session registered under C{session_uuid} to
        retrieve its list of mounted client shares for that session.

        @param session_uuid: the X2Go session's UUID registry hash
        @type session_uuid: C{str}
        @param no_cache: do not get the session list from cache, query the X2Go server directly
        @type no_cache: C{bool}
        @param raw: output the session list in X2Go's raw C{x2golistmounts} format
        @type raw: C{bool}

        @return: list of server-side mounted shares for a given session UUID
        @rtype: C{list}

        """
        if raw:
            return self.session_registry(session_uuid).list_mounts(raw=raw)

        if not self.use_listsessions_cache or not self.auto_update_listmounts_cache or no_cache:
            _mounts_list = self.session_registry(session_uuid).list_mounts()
        else:
            if self.use_listsessions_cache and (not self.listsessions_cache.is_cached(session_uuid=session_uuid, cache_type='mounts') or refresh_cache):
                self.__update_cache_by_session_uuid(session_uuid, update_sessions=False, update_mounts=True)
            _mounts_list = self.listsessions_cache.list_mounts(session_uuid)

        return _mounts_list
    __list_mounts = list_mounts

    ###
    ### Provide access to config file class objects
    ### 

    def get_profiles(self):
        """\
        Returns the L{X2GoClient} instance's C{X2GoSessionProfiles*} object.

        Use this method for object retrieval if you want to modify the »sessions«
        configuration node (e.g. in ~/.x2goclient with the FILE backend) from within your
        Python X2Go based application.

        return: returns the client's session profiles instance
        rtype: C{X2GoSessionProfiles*} instance

        """
        return self.session_profiles
    __get_profiles = get_profiles
    get_session_profiles = get_profiles
    """Alias for L{get_profiles()}."""

    @property
    def profile_names(self):
        """\
        Equals a list of all profile names that are known to this L{X2GoClient} instance.

        """
        return self.session_profiles.profile_names
    __profile_names = profile_names

    def get_client_settings(self):
        """\
        Returns the L{X2GoClient} instance's C{X2GoClientSettings*} object.

        Use this method for object retrieval if you want to modify the »settings«
        configuration node (e.g. in ~/.x2goclient with the FILE backend) from within your
        Python X2Go based application.

        return: returns the client's settings configuration node
        rtype: C{bool}

        """
        return self.client_settings
    __get_client_settings = get_client_settings

    def get_client_printing(self):
        """\
        Returns the L{X2GoClient} instance's C{X2GoClientPrinting*} object.

        Use this method for object retrieval if you want to modify the printing
        configuration node (e.g. in ~/.x2goclient with the FILE backend) from within your
        Python X2Go based application.

        return: returns the client's printing configuration node
        rtype: C{bool}

        """
        return self.client_printing
    __get_client_printing = get_client_printing

    ###
    ### Session profile oriented methods
    ### 

    def get_profile_config(self, profile_id_or_name, parameter=None):
        """\
        Returns a dictionary with session options and values that represent
        the session profile for C{profile_id_or_name}.

        @param profile_id_or_name: name or id of an X2Go session profile as found
            in the sessions configuration file
        @type profile_id_or_name: C{str}
        @param parameter: if specified, only the value for the given parameter is returned
        @type parameter: C{str}

        @return: a Python dictionary with session profile options
        @rtype: C{dict} or C{bool}, C{int}, C{str}

        """
        return self.session_profiles.get_profile_config(profile_id_or_name, parameter=parameter)
    __get_profile_config = get_profile_config
    with_profile_config = get_profile_config

    def set_profile_config(self, profile_id_or_name, parameter, value):
        """\
        Set individual session profile parameters for session profile C{profile_id_or_name}.

        @param profile_id_or_name: name or id of an X2Go session profile as found
            in the sessions configuration file
        @type profile_id_or_name: C{str}
        @param parameter: set this parameter with the given C{value}
        @type parameter: C{str}
        @param value: set this value for the given C{parameter}
        @type value: C{bool}, C{int}, C{str}, C{list} or C{dict}

        @return: returns C{True} if this operation has been successful
        @rtype: C{dict}

        """
        self.session_profiles.update_value(profile_id_or_name, parameter, value)
        self.session_profiles.write_user_config = True
        self.session_profiles.write()
    __set_profile_config = set_profile_config

    def to_profile_id(self, profile_name):
        """\
        Retrieve the session profile ID of the session whose profile name
        is C{profile_name}

        @param profile_name: the session profile name
        @type profile_name: C{str}

        @return: the session profile's ID
        @rtype: C{str}

        """
        return self.session_profiles.to_profile_id(profile_name)
    __to_profile_id = to_profile_id

    def to_profile_name(self, profile_id):
        """\
        Retrieve the session profile name of the session whose profile ID
        is C{profile_id}

        @param profile_id: the session profile ID
        @type profile_id: C{str}

        @return: the session profile's name
        @rtype: C{str}

        """
        return self.session_profiles.to_profile_name(profile_id)
    __to_profile_name = to_profile_name

    def get_profile_metatype(self, profile_name):
        """\
        Evaluate a session profile and return a human readable meta type
        (classification) for the session profile C{profile_name}.

        @param profile_name: a profile name
        @type profile_name: C{str}

        @return: the profile's meta type
        @rtype: C{str}

        """
        return self.session_profiles.get_profile_metatype(profile_name)
    __get_profile_metatype = get_profile_metatype

    def client_connected_profiles(self, return_profile_names=False):
        """\
        Retrieve a list of session profiles that are currently connected to an X2Go server.

        @param return_profile_names: return as list of session profile names
        @type return_profile_names: C{bool}
        @return: a list of profile names or IDs
        @rtype: C{list}

        """
        if return_profile_names:
            return [ self.to_profile_name(p_id) for p_id in self.session_registry.connected_profiles() ]
        else:
            return self.session_registry.connected_profiles()
    __client_connected_profiles = client_connected_profiles

    def disconnect_profile(self, profile_name):
        """\
        Disconnect all L{X2GoSession} instances that relate to C{profile_name} by closing down their
        Paramiko/SSH Transport thread.

        @param profile_name: the X2Go session profile name
        @type profile_name: C{str}
        @return: a return value
        @rtype: C{bool}

        """
        _retval = False
        _session_uuid_list = []
        # disconnect individual sessions and make a list of session UUIDs for later cleanup (s. below)
        for s in self.session_registry.registered_sessions_of_profile_name(profile_name, return_objects=True):
            _session_uuid_list.append(s.get_uuid())
            _retval = s.disconnect() | _retval

        # tell session registry to forget attached sessions completely on disconnect action
        for uuid in _session_uuid_list:
            self.session_registry.forget(uuid)

        # clear cache, as well...
        if self.use_listsessions_cache:
            self.listsessions_cache.delete(profile_name)
        return _retval
    __disconnect_profile = disconnect_profile

    def update_sessionregistry_status_by_profile_name(self, profile_name, session_list=None):
        """\
        Update the session registry stati by profile name.

        @param profile_name: the X2Go session profile name
        @type profile_name: C{str}
        @param session_list: a manually passed on list of X2Go sessions
        @type session_list: C{X2GoServerList*} instances

        """
        session_uuids = self.client_registered_sessions_of_profile_name(profile_name, return_objects=False)
        if session_uuids:
            if session_list is None:
                session_list = self._X2GoClient__list_sessions(session_uuids[0],
                                                               update_sessionregistry=False,
                                                               register_sessions=False,
                                                              )
            try:
                self.session_registry.update_status(profile_name=profile_name, session_list=session_list)
            except x2go_exceptions.X2GoControlSessionException:
                if self.session_registry(session_uuids[0]).connected: self.HOOK_on_control_session_death(profile_name)
                self.disconnect_profile(profile_name)
    __update_sessionregistry_status_by_profile_name = update_sessionregistry_status_by_profile_name

    def update_sessionregistry_status_by_session_uuid(self, session_uuid):
        """\
        Update the session registry status of a specific L{X2GoSession} instance with
        session identifier <session_uuid>.

        @param session_uuid: the X2Go session's UUID registry hash
        @type session_uuid: C{str}

        """
        session_list = self._X2GoClient__list_sessions(session_uuid, update_sessionregistry=False, register_sessions=False)
        if session_list:
            self.session_registry.update_status(session_uuid=session_uuid, session_list=session_list)
    __update_sessionregistry_status_by_session_uuid = update_sessionregistry_status_by_session_uuid

    def update_sessionregistry_status_all_profiles(self):
        """\
        Update the session registry stati of all session profiles.

        """
        for profile_name in self.client_connected_profiles(return_profile_names=True):
            self.__update_sessionregistry_status_by_profile_name(profile_name)
    __update_sessionregistry_status_all_profiles = update_sessionregistry_status_all_profiles

    def update_cache_by_profile_name(self, profile_name, cache_types=('sessions'), update_sessions=None, update_desktops=None, update_mounts=None):
        """\
        Update the session list cache by profile name.

        @param profile_name: the X2Go session profile name
        @type profile_name: C{str}
        @param cache_types: specify what cache type to update (available: C{sessions}, C{desktops}, C{mounts})
        @type cache_types: C{tuple} or C{list}
        @param update_sessions: instead of giving a list of cache types, plainly say C{True} here, if 
            you want to update sessions in the session list cache.
        @type update_sessions: C{bool}
        @param update_desktops: instead of giving a list of cache types, plainly say C{True} here, if 
            you want to update available desktops in the desktop list cache.
        @type update_desktops: C{bool}
        @param update_mounts: instead of giving a list of cache types, plainly say C{True} here, if 
            you want to update mounted shares in the mount list cache.
        @type update_mounts: C{bool}

        """
        if self.listsessions_cache is not None:
            _update_sessions = ('sessions' in cache_types) or update_sessions
            _update_desktops = ('desktops' in cache_types) or update_desktops
            _update_mounts = ('mounts' in cache_types) or update_mounts
            try:
                self.logger("====>>>> update_cache_by_profile_name(%s)" % profile_name, loglevel=log.loglevel_INFO)
                self.listsessions_cache.update(profile_name, update_sessions=_update_sessions, update_desktops=_update_desktops, update_mounts=_update_mounts, )
            except x2go_exceptions.X2GoControlSessionException as ex:
                self.logger("====>>>> update_cache_by_profile_name(%s) Exception: %s" % (profile_name, ex.message), loglevel=log.loglevel_INFO)
                c_sessions = self.client_connected_sessions_of_profile_name(profile_name, return_objects=True)
                if len(c_sessions) and c_sessions[0].connected: self.HOOK_on_control_session_death(profile_name)
                self.disconnect_profile(profile_name)
    __update_cache_by_profile_name = update_cache_by_profile_name

    def update_cache_by_session_uuid(self, session_uuid, cache_types=('sessions'), update_sessions=None, update_desktops=None, update_mounts=None):
        """\
        Update the session list cache of a specific L{X2GoSession} instance with
        session identifier <session_uuid>.

        @param session_uuid: the X2Go session's UUID registry hash
        @type session_uuid: C{str}
        @param cache_types: specify what cache type to update (available: C{sessions}, C{desktops}, C{mounts})
        @type cache_types: C{tuple} or C{list}
        @param update_sessions: instead of giving a list of cache types, plainly say C{True} here, if 
            you want to update sessions in the session list cache.
        @type update_sessions: C{bool}
        @param update_desktops: instead of giving a list of cache types, plainly say C{True} here, if 
            you want to update available desktops in the desktop list cache.
        @type update_desktops: C{bool}
        @param update_mounts: instead of giving a list of cache types, plainly say C{True} here, if 
            you want to update mounted shares in the mount list cache.
        @type update_mounts: C{bool}

        """
        profile_name = self.get_session_profile_name(session_uuid)
        self.__update_cache_by_profile_name(profile_name,
                                            cache_types=cache_types,
                                            update_sessions=update_sessions,
                                            update_desktops=update_desktops,
                                            update_mounts=update_mounts,
                                           )
    __update_cache_by_session_uuid = update_cache_by_session_uuid

    def update_cache_all_profiles(self, cache_types=('sessions'), update_sessions=None, update_desktops=None, update_mounts=None):
        """\
        Update the session list cache of all session profiles.

        @param cache_types: specify what cache type to update (available: C{sessions}, C{desktops}, C{mounts})
        @type cache_types: C{tuple} or C{list}
        @param update_sessions: instead of giving a list of cache types, plainly say C{True} here, if 
            you want to update sessions in the session list cache.
        @type update_sessions: C{bool}
        @param update_desktops: instead of giving a list of cache types, plainly say C{True} here, if 
            you want to update available desktops in the desktop list cache.
        @type update_desktops: C{bool}
        @param update_mounts: instead of giving a list of cache types, plainly say C{True} here, if 
            you want to update mounted shares in the mount list cache.
        @type update_mounts: C{bool}

        """
        if self.listsessions_cache is not None:
            for profile_name in self.client_connected_profiles(return_profile_names=True):
                self.__update_cache_by_profile_name(profile_name,
                                                    cache_types=cache_types,
                                                    update_sessions=update_sessions,
                                                    update_desktops=update_desktops,
                                                    update_mounts=update_mounts,
                                                   )

            # remove profiles that are not connected any more from cache object
            self.listsessions_cache.check_cache()

    __update_cache_all_profiles = update_cache_all_profiles

    def apprime_update_cache_all_profiles(self):
        """\
        Update the menu tree, if not present.

        """
        try:
            self.logger('====>>>> apprime_update_cache_all_profiles', loglevel=log.loglevel_INFO)
            for sess in self.session_registry.connected_sessions():
                self.logger('====>>>> apprime_update_cache_all_profiles(%s)' % sess.profile_name, loglevel=log.loglevel_INFO)
                if sess.control_session._published_applications_menu is {}:
                    self.logger('====>>>> apprime_update_cache_all_profiles(%s) refreshing due to empty menu' % sess.profile_name, loglevel=log.loglevel_INFO)
                    sess.control_session.get_published_applications()
        except Exception as e:
            self.logger('====>>>> apprime_update_cache_all_profiles Exception %' % e.message, loglevel=log.loglevel_WARN)

    def register_available_server_sessions_by_profile_name(self, profile_name, re_register=False, skip_pubapp_sessions=False):
        """\
        Register available sessions that are found on the X2Go server the profile
        of name C{profile_name} is connected to.

        @param profile_name: the X2Go session profile name
        @type profile_name: C{str}
        @param re_register: re-register available sessions, needs to be done after session profile changes
        @type re_register: C{bool}
        @param skip_pubapp_sessions: Do not auto-register published applications sessions.
        @type skip_pubapp_sessions: C{bool}

        """
        if profile_name not in self.client_connected_profiles(return_profile_names=True):
            return
        session_list = self._X2GoClient__list_sessions(profile_name=profile_name,
                                                       update_sessionregistry=False,
                                                       register_sessions=False,
                                                      )
        try:
            self.session_registry.register_available_server_sessions(profile_name, session_list=session_list, re_register=re_register, skip_pubapp_sessions=skip_pubapp_sessions)
        except x2go_exceptions.X2GoControlSessionException, e:
            c_sessions = self.client_connected_sessions_of_profile_name(profile_name, return_objects=True)
            if len(c_sessions) and c_sessions[0].connected: self.HOOK_on_control_session_death(profile_name)
            self.disconnect_profile(profile_name)
            raise e
    __register_available_server_sessions_by_profile_name = register_available_server_sessions_by_profile_name

    def register_available_server_sessions_by_session_uuid(self, session_uuid, skip_pubapp_sessions=False):
        """\
        Register available sessions that are found on the X2Go server that the L{X2GoSession} instance 
        with session identifier <session_uuid> is connected to.

        @param session_uuid: the X2Go session's UUID registry hash
        @type session_uuid: C{str}
        @param skip_pubapp_sessions: Do not auto-register published applications sessions.
        @type skip_pubapp_sessions: C{bool}

        """
        profile_name = self.get_session_profile_name(session_uuid)
        self.__register_available_server_sessions_by_profile_name(profile_name, skip_pubapp_sessions=skip_pubapp_sessions)
    __register_available_server_sessions_by_session_uuid = register_available_server_sessions_by_session_uuid

    def register_available_server_sessions_all_profiles(self, skip_pubapp_sessions=False):
        """\
        Register all available sessions found on an X2Go server for each session profile.

        @param skip_pubapp_sessions: Do not auto-register published applications sessions.
        @type skip_pubapp_sessions: C{bool}

        """
        for profile_name in self.client_connected_profiles(return_profile_names=True):
            try:
                self.__register_available_server_sessions_by_profile_name(profile_name, skip_pubapp_sessions=skip_pubapp_sessions)
            except x2go_exceptions.X2GoSessionRegistryException:
                pass
    __register_available_server_sessions_all_profiles = register_available_server_sessions_all_profiles
