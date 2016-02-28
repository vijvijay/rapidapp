# -*- coding: utf-8 -*-

modules ={}

import os
import re

# Python X2Go
import x2go
import gevent

import wx

import types
import copy
import threading
import locale

# PyHoca-GUI modules
import about
import logon
import brokerlogon
import passphrase
import taskbar
import profilemanager
import printingprefs
import notify
import basepath
import messages
import splash
import sessiontitle
import listdesktops
import serverinfo

wx.SetDefaultPyEncoding("utf-8")

#def SetExitHandler(func):
#    """\
#    An exit handler function for MS Windows / Unix. Currently unused.
#
#    @param func: function that shall get registered with win32api as exit handler.
#    @type func: C{func}
#
#    """
#    if os.name == 'nt' :
#        try :
#            import win32api
#            result = win32api.SetConsoleCtrlHandler( func, True )
#            if result == 0:
#                print '\nCould not SetConsoleCtrlHandler (error %r)\n' % win32api
#            else :
#                print '\nSetConsoleCtrlHandler SUCCESS\n'
#
#        except ImportError :
#            #version = '.'.join( map( str, sys.version_info[ :2] ) )
#            raise Exception( 'PyWin32 (win32api) is not installed.' )
#
#    else :
#        import signal
#        signal.signal( signal.SIGTERM, func )
#        signal.signal( signal.SIGINT, func )


class PyHocaGUI(wx.App, x2go.X2GoClient):
    """\
    The main application instance.

    L{PyHocaGUI} provides a system tray icon (like the GNOME network manager applet) that
    provides a multi-session / multi-connection X2Go client.

    L{PyHocaGUI} has been developed with the focus of easy customization by SaaS providers.
    Product branding is a wanted feature. The customizable elements are:

      - application name
      - system tray icon (idle icon, while-connecting icon)
      - splash screen
      - window that shows the ,,About'' dialog

    With L{PyHocaGUI} you can also restrict several functionalities: For example, it is possible
    to disable the multi-session support completely and use L{PyHocaGUI} only or one
    session in published applications mode. This turns L{PyHocaGUI} into a pseudo-startmenu that
    blends in X2Go server-side application into one's desktop shell.

    L{PyHocaGUI}'s main challenge is to combine two different event handlers:
    wxPython and gevent.

    """
    def __init__(self, args, logger, liblogger,
                 appname='Appri.Me',
                 vendorname='Apprime Cloud Apps',
                 version=None,):
        """\
        Initialize the application (constructor).

        The main control data structure if the C{args} object that gets passed on to L{PyHocaGUI}'s constructor.

        @param args: a class with properties representing the command-line options that are available to L{PyHocaGUI} instances.
        @type args: C{argparse.ArgumentParser} (or similar)
        @param logger: you can pass an L{X2GoLogger} object to the
            L{PyHocaGUI} constructor for logging application events
        @type logger: Python X2Go C{X2GoLogger} instance
        @param liblogger: you can pass an L{X2GoLogger} object to the
            L{PyHocaGUI} constructor for logging application events, this object is forwarded to the C{X2GoClient}. class in Python X2Go.
        @type liblogger: Python X2Go C{X2GoLogger} instance
        @param appname: name of the application instance
        @type appname: C{str}
        @param vendorname: name of the company distributing this application
        @type vendorname: C{str}
        @param version: version of the application
        @type version: C{str}

        """

        self.appname = appname
        self.vendorname = vendorname
        self.version = version
        self._exiting = False

        self.args = args

        self.gevent_sleep_when_idle = 0.25

        if logger is None:
            self._pyhoca_logger = x2go.X2GoLogger(tag=self.appname)
        else:
            self._pyhoca_logger = copy.deepcopy(logger)
            self._pyhoca_logger.tag = self.appname

        if liblogger is None:
            self._pyhoca_liblogger = x2go.X2GoLogger()
        else:
            self._pyhoca_liblogger = copy.deepcopy(liblogger)

        if x2go.defaults.X2GOCLIENT_OS == 'Windows':
            if self.args.lang is not None:
                self.lang = self.args.lang
            else:
                self.lang = 'en'
        else:
            self.lang = locale.getdefaultlocale()[0]
        self._pyhoca_logger('%s\'s user interface language is: %s.' % (self.appname, self.lang), loglevel=x2go.loglevel_DEBUG)

        _x2goclient_kwargs = {
            'use_listsessions_cache': True,
            'auto_update_listsessions_cache': True,
            'auto_update_listmounts_cache': True,
            'auto_update_sessionregistry': True,
            'auto_register_sessions': True,
            'no_auto_reg_pubapp_sessions': True,
            'logger': self._pyhoca_liblogger,
        }
        if self.args.backend_controlsession is not None:
            _x2goclient_kwargs['control_backend'] = self.args.backend_controlsession
        if self.args.backend_terminalsession is not None:
            _x2goclient_kwargs['terminal_backend'] = self.args.backend_terminalsession
        if self.args.backend_serversessioninfo is not None:
            _x2goclient_kwargs['info_backend'] = self.args.backend_serversessioninfo
        if self.args.backend_serversessionlist is not None:
            _x2goclient_kwargs['list_backend'] = self.args.backend_serversessionlist
        if self.args.backend_proxy is not None:
            _x2goclient_kwargs['proxy_backend'] = self.args.backend_proxy
        if self.args.backend_sessionprofiles is not None:
            _x2goclient_kwargs['profiles_backend'] = self.args.backend_sessionprofiles
        if self.args.backend_clientsettings is not None:
            _x2goclient_kwargs['settings_backend'] = self.args.backend_clientsettings
        if self.args.backend_clientprinting is not None:
            _x2goclient_kwargs['printing_backend'] = self.args.backend_clientprinting

        if self.args.client_rootdir is not None:
            _x2goclient_kwargs['client_rootdir'] = self.args.client_rootdir
        if self.args.sessions_rootdir is not None:
            _x2goclient_kwargs['sessions_rootdir'] = self.args.sessions_rootdir
        if self.args.ssh_rootdir is not None:
            _x2goclient_kwargs['ssh_rootdir'] = self.args.ssh_rootdir

        if x2go.X2GOCLIENT_OS == 'Windows':
            _x2goclient_kwargs['start_xserver'] = self.args.start_xserver
            _x2goclient_kwargs['start_pulseaudio'] = self.args.start_pulseaudio

        if x2go.X2GOCLIENT_OS == 'Windows' and self.args.start_pulseaudio and os.environ.has_key('PYHOCAGUI_DEVELOPMENT') and os.environ['PYHOCAGUI_DEVELOPMENT'] == '1':
            _x2goclient_kwargs['pulseaudio_installdir'] = os.path.dirname(basepath.pulseaudio_binary)

        self.broker_autoconnect = self.args.broker_autoconnect
        if self.args.broker_url:
            _x2goclient_kwargs['broker_url'] = self.args.broker_url
            if not re.match('^(http://|https://|ssh://).*', self.args.broker_url):
                self.broker_autoconnect = True
            else:
                if not re.match('(http|ssh)', self.args.broker_url.lower()):
                    # fall back broker mode... -> HTTP (and trigger querying for the exact URL)
                    _x2goclient_kwargs['broker_url'] = 'HTTP'
            self.with_brokerage = True
        else:
            self.with_brokerage = False

        if self.args.broker_password:
            _x2goclient_kwargs['broker_password'] = self.args.broker_password

        if self.args.broker_name:
            self.broker_name = self.args.broker_name

        if self.args.broker_cacertfile is not None:
            self.broker_cacertfile = os.path.expanduser(self.args.broker_cacertfile)
            if self.broker_cacertfile and os.path.exists(self.broker_cacertfile):
                os.environ['REQUESTS_CA_BUNDLE'] = self.broker_cacertfile

        try:
            if self.args.logon_window_position:
                self.logon_window_position_x = int(self.args.logon_window_position.split('x')[0])
                self.logon_window_position_y = int(self.args.logon_window_position.split('x')[1])
            else:
                raise
        except:
            self.logon_window_position_x = self.logon_window_position_y = None

        x2go.X2GoClient.__init__(self, **_x2goclient_kwargs)

        wx.App.__init__(self, redirect=False, clearSigInt=False)
        #SetExitHandler(self._exit_handler)

        if not self.args.disable_splash:
            splash.PyHocaGUI_SplashScreen(self, splash_image=self.args.splash_image)

        self.Bind(wx.EVT_IDLE, self.OnIdle)

    def OnInit(self):
        """\
        Gets called once the application (wx.App) gets initialized.

        @return: always C{True}
        @rtype: C{bool}

        """
        wx.BeginBusyCursor()

        self.SetAppName(self.appname)
        self.SetVendorName(self.vendorname)
        self.startGUI()

        try: wx.EndBusyCursor()
        except: pass
        return True

    def OnIdle(self, evt):
        """\
        Integration of gevent/libevent and wxPython.

        Whenever wxPython seems to be idle, inject a gevent.sleep().

        @return: always C{True}
        @rtype: C{bool}

        """
        try:
            gevent.sleep(self.gevent_sleep_when_idle)
        except KeyboardInterrupt:
            self._pyhoca_logger('Received Ctrl-C keyboard interrupt... Wait till %s has exited cleanly.' % self.appname, loglevel=x2go.loglevel_NOTICE)
            self.WakeUpIdle()
            self.ExitMainLoop()
        except SystemExit:
            self._pyhoca_logger('Received SIGTERM signal... Wait till %s has exited cleanly.' % self.appname, loglevel=x2go.loglevel_NOTICE)
            self.WakeUpIdle()
            self.ExitMainLoop()
        evt.RequestMore()
        return True

    def startGUI(self):
        """\
        Startup method for L{PyHocaGUI}.

        """
        # cmd line options
        self.add_to_known_hosts = self.args.add_to_known_hosts
        self.auto_connect = self.args.auto_connect
        self.start_on_connect = True
        self.resume_newest_on_connect = True
        self.resume_oldest_on_connect = self.args.resume_oldest_on_connect
        self.resume_all_on_connect = self.args.resume_all_on_connect
        self.exit_on_disconnect = self.args.exit_on_disconnect
        self.disconnect_on_suspend = self.args.disconnect_on_suspend
        self.disconnect_on_terminate = self.args.disconnect_on_terminate
        self.show_profile_metatypes = self.args.show_profile_metatypes
        self.restricted_trayicon = self.args.restricted_trayicon
        self.tray_icon = self.args.tray_icon
        self.tray_icon_connecting = self.args.tray_icon_connecting
        self.disable_notifications = self.args.disable_notifications
        self.remember_username = self.args.remember_username

        self._pyhoca_logger('Appri.Me is starting up', loglevel=x2go.log.loglevel_INFO, )

        if self.args.tray_icon:
            self.about = about.PyHocaGUI_AboutFrame(self, about_image=self.args.about_image, icon_name=self.args.tray_icon)
        else:
            self.about = about.PyHocaGUI_AboutFrame(self, about_image=self.args.about_image)
        self.about.Show(False)

        self.about_pythonx2go = about.PyHocaGUI_AboutFrame(self, about_image='Python-X2Go_about-logo.png', about_what="Python X2Go")
        self.about_pythonx2go.Show(False)

        self.taskbar = taskbar.PyHocaGUI_TaskBarIcon(self.about)
        self.taskbar.Bind(wx.EVT_TASKBAR_LEFT_DCLICK, lambda _Show: self.about.Show(True))
        self.taskbar.Bind(wx.EVT_TASKBAR_LEFT_DOWN, self.taskbar.CreateSessionManagerPopupMenu)

        if x2go.X2GOCLIENT_OS in ('Linux', 'Mac'):
            self.notifier = notify.libnotify_NotifierPopup(self)
        if x2go.X2GOCLIENT_OS in ('Windows'):
            self.notifier = notify.showballoon_NotifierPopup(self.about)

        self._sub_windows = []
        self._logon_windows = {}
        self._hide_notifications_map = {}
        self._eventid_profilenames_map = {}
        self._eventid_exportprofiles_map = {}
        self._eventid_sessionnames_map = {}
        self._eventid_applications_map = {}
        self._eventid_shared_folders_map = {}
        self._eventid_unshared_folders_map = {}
        self._eventid_pubapp_execmap = {}
        self._temp_launching_pubapp_profiles = []
        self._temp_launching_pubapp_locks = {}
        self._temp_disabled_profile_names = []
        self._temp_disabled_session_names = {}
        self._remember_shared_folders = {}

        self.profilemanager_disabled = self.args.disable_profilemanager
        self.printingprefs_disabled = self.args.disable_printingprefs

        ###
        ### disable functionality for release versions
        ###
        if os.environ.has_key('PYHOCAGUI_DEVELOPMENT') and os.environ['PYHOCAGUI_DEVELOPMENT'] == '1':
            self.options_disabled = self.args.disable_options
        else:
            self._pyhoca_logger('the current release of %s does not support client configuration' % self.appname, loglevel=x2go.log.loglevel_WARN)
            self.options_disabled = True

        if self.args.session_profile:
            for profile_name in self.args.session_profile.split(','):
                self.start_on_connect = True
                self.resume_newest_on_connect = True
                if not self.args.single_session_profile:
                    self.auto_connect = True
                self._pyhoca_logger('opening default session profile %s' % profile_name, loglevel=x2go.log.loglevel_NOTICE)
                try:
                    self._X2GoClient__register_session(profile_name=profile_name, auto_connect=self.auto_connect)
                except x2go.x2go_exceptions.X2GoBrokerConnectionException:
                    self.session_registration_failed(profile_name=profile_name)

        if self.auto_connect or self.broker_autoconnect:
            gevent.spawn(self._auto_connect)

    def _auto_connect(self):
        """\
        Register all available session profiles on application start.

        If brokerage is used, handle auto connecting to the broker before that, as well.

        The auto-registration of all session profiles will trigger the auto-connect feature
        implemented in C{X2GoClient} of Python X2Go.

        """
        # wait for splash to appear
        if not self.args.disable_splash:
            gevent.sleep(1)

        # auto connect to the broker if requested
        if self.with_brokerage and self.broker_autoconnect:
            self.OnBrokerAuthenticate(None)

        if self.auto_connect and not self.args.session_profile:
            self._X2GoClient__register_all_session_profiles()

    def session_auto_connect(self, session_uuid, **kwargs):
        """\
        Override C{X2GoClient.session_auto_connect()} to always divert authentication to L{OnSessionAuthenticate}.

        @param session_uuid: session UUID
        @type session_uuid: C{str}

        """
        # override X2GoClient method
        if self.auto_connect and self.get_session(session_uuid).get_session_profile_option('auto_connect'):
            self.HOOK_profile_auto_connect(self.get_session_profile_name(session_uuid))

    def HOOK_profile_auto_connect(self, profile_name, **kwargs):
        """\
        Override C{X2GoClient.HOOK_profile_auto_connect()} to always divert authentication to L{OnSessionAuthenticate}.

        @param profile_name: session profile name
        @type profile_name: C{str}

        """
        session_uuids = self.client_registered_sessions_of_profile_name(profile_name=profile_name)
        if session_uuids:
            session_uuid = session_uuids[0]

            _dummy_id = wx.NewId()
            self._eventid_profilenames_map[_dummy_id] = profile_name
            evt = wx.CommandEvent()
            evt.SetId(_dummy_id)

            self.OnSessionAuthenticate(evt, session_uuid=session_uuid)

    def session_auto_start_or_resume(self, session_uuid, newest=True, oldest=False, all_suspended=False, **kwargs):
        """\
        Override C{X2GoClient.session_auto_start_or_resume()} to differentiate between the application options
        C{resume_newest_on_connect}, C{resume_oldest_on_connect} and C{resume_all_on_connect}.

        @param profile_name: session profile name
        @type profile_name: C{str}

        """
        if not self.get_session(session_uuid).published_applications:
            if self.resume_oldest_on_connect:
                self._X2GoClient__session_auto_start_or_resume(session_uuid, newest=False, oldest=True, start=self.start_on_connect, **kwargs)
            if self.resume_all_on_connect:
                self._X2GoClient__session_auto_start_or_resume(session_uuid, newest=False, all_suspended=True, start=self.start_on_connect, **kwargs)
            elif self.resume_newest_on_connect:
                self._X2GoClient__session_auto_start_or_resume(session_uuid, newest=True, start=self.start_on_connect, **kwargs)

    def _exit_handler(self, *args):
        """\
        L{PyHocaGUI}'s exit handler method.

        Currently unused.

        """
        self.WakeUpIdle()
        self.ExitMainLoop()

    # wx.App's OnExit method
    def OnExit(self):
        """\
        Cleanly exit the application.

          - suspend all sessions
          - disconnect all connected session profiles
          - close all associated windows

        """
        self._exiting = True
        # close open password dialogs (or other remaining windows)
        for _win in self._sub_windows:
            _win.Close()
        for session_obj in [ _s for _s in self._X2GoClient__client_running_sessions(return_objects=True) if _s.is_associated() ]:
            profile_name = session_obj.get_profile_name()
            if not self._hide_notifications_map.has_key(profile_name):
                self._hide_notifications_map[profile_name] = []
            self._hide_notifications_map[profile_name].append(session_obj.get_session_name())
            try: session_obj.suspend()
            except: pass
        x2go.x2go_cleanup()
        self.about.Close()
        self.taskbar.Close()

    # the taskbar's OnExit method...
    def OnTaskbarExit(self, evt):
        """\
        Gets called if the user chooses to exit the application via the system tray icon in the taskbar.

        @param evt: event
        @type evt: C{obj}

        """
        self._pyhoca_logger('exit application', loglevel=x2go.log.loglevel_INFO, )
        if self.args.single_session_profile:
            if not x2go.defaults.X2GOCLIENT_OS == 'Windows':
                if self.client_running_sessions_of_profile_name(self.args.session_profile):
                    self.notifier.send(self.appname, _(u'Suspending sessions and exiting application...'), icon='application-exit', timeout=10000)
                else:
                    if self.is_profile_connected(profile_name=self.args.session_profile):
                        self.notifier.send(self.appname, _(u'Disconnecting %s and exiting application...') % str(self.args.session_profile), icon='application-exit', timeout=10000)
                    else:
                        self.notifier.send(self.appname, _(u'Exiting application...'), icon='application-exit', timeout=10000)
            self._eventid_profilenames_map[evt.GetId()] = self.args.session_profile
        self.WakeUpIdle()
        self.ExitMainLoop()

    def _init_pubapp_session(self, session_uuid=None, profile_name=None):
        """\
        Initialize a single session in published applications mode for a given profile.

        NOTE: L{PyHocaGUI} by design only supports _one_ published applications session per connected profile.

        @param session_uuid: session UUID
        @type session_uuid: C{str}
        @param profile_name: session profile name
        @type profile_name: C{str}

        """
        #apprime code begin
        self.update_cache_all_profiles()
        #apprime code end
        
        if profile_name is None and session_uuid:
            profile_name = self._X2GoClient__get_session_profile_name(session_uuid)

        if not self._temp_launching_pubapp_locks.has_key(profile_name):
            self._temp_launching_pubapp_locks[profile_name] = threading.Lock()

        if not self._X2GoClient__client_connected_sessions_of_profile_name(profile_name):
            return None

        if session_uuid is None and profile_name:
            session_uuid = self._X2GoClient__client_connected_sessions_of_profile_name(profile_name, return_objects=False)[0]

        connected_session = self._X2GoClient__get_session(session_uuid)
        if connected_session.has_server_feature('X2GO_PUBLISHED_APPLICATIONS') and self.get_profile_config(profile_name)['published']:

            if len(self.client_pubapp_sessions_of_profile_name(profile_name=profile_name)):
                return False

            self._temp_launching_pubapp_locks[profile_name].acquire()
            if profile_name not in self._temp_launching_pubapp_profiles:
                self._temp_launching_pubapp_profiles.append(profile_name)

            pubapp_session_started = False
            pubapp_session_resumed = False

            ### PyHoca-GUI does not support more than one session in published applications mode...

            # suspend any running session that is in published applications mode (unless we are already associated with it)
            session_list = self._X2GoClient__list_sessions(session_uuid=session_uuid, profile_name=profile_name)
            if session_list:
                pubapp_sessions_running = [ _sn for _sn in session_list.keys() if session_list[_sn].is_running() and session_list[_sn].is_published_applications_provider() ]
                for session_name in pubapp_sessions_running:
                    self.suspend_session(session_uuid=connected_session(), session_name=session_name)

                # resume first available session in published applications mode... (from PyHoca-GUI's perspective there should only
                # be one)
                if pubapp_sessions_running:
                    gevent.sleep(1)
                    session_list = self._X2GoClient__list_sessions(session_uuid=session_uuid, profile_name=profile_name, refresh_cache=True)

            if session_list:
                pubapp_sessions_suspended = [ _sn for _sn in session_list.keys() if session_list[_sn].is_suspended() and session_list[_sn].is_published_applications_provider() ]

                for session_name in pubapp_sessions_suspended:

                    if not pubapp_session_resumed:
                        # resume one single session in published applications mode immediately, if available
                        pubapp_session = self._X2GoClient__register_session(profile_name=profile_name,
                                                                            published_applications=True,
                                                                            cmd='PUBLISHED',
                                                                            session_type='published',
                                                                            session_name=session_name,
                                                                            published_applications_no_submenus=self.args.published_applications_no_submenus,
                                                                            return_object=True
                                                                           )
                        pubapp_session_resumed = pubapp_session.resume()
                    elif session_list[session_name].is_published_applications_provider() and pubapp_session_resumed:

                        # if there are more then one published applications mode sessions (in suspended state), terminate them now...
                        try:
                            connected_session.terminate()
                        except x2go.X2GoSessionException:
                            pass

            if not pubapp_session_resumed:

                pubapp_session = self._X2GoClient__register_session(profile_name=profile_name,
                                                                    published_applications=True,
                                                                    cmd='PUBLISHED',
                                                                    session_type='published',
                                                                    published_applications_no_submenus=self.args.published_applications_no_submenus,
                                                                    return_object=True
                                                                   )
                pubapp_session_started = pubapp_session.start()

            if profile_name in self._temp_launching_pubapp_profiles:
                self._temp_launching_pubapp_profiles.remove(profile_name)
            self._temp_launching_pubapp_locks[profile_name].release()

            return pubapp_session_started | pubapp_session_resumed

        elif not connected_session.has_server_feature('X2GO_PUBLISHED_APPLICATIONS') and self.get_profile_config(profile_name)['published']:
            self.notifier.send(_(u'%s - server warning') % profile_name, _(u'The X2Go Server does not publish an application menu.'), icon='session_warning', timeout=10000)

        return None

    def _post_authenticate(self, evt, session_uuid):
        """\
        Tasks that have to be done directly after authentication of a session profile.

        @param evt: event
        @type evt: C{obj}
        @param session_uuid: session UUID
        @type session_uuid: C{str}

        """
        try:
            profile_name = self.get_session(session_uuid).get_profile_name()
            self._hide_notifications_map[profile_name] = []
            gevent.spawn(self._init_pubapp_session, session_uuid)
            #apprime
            self._pyhoca_logger('====>>>>x2go.guardian.X2GoSessionGuardian.seconds = 0', loglevel=x2go.log.loglevel_INFO, )
            x2go.guardian.X2GoSessionGuardian.seconds = 0

        except x2go.X2GoSessionRegistryException:
            # there might have been a disconnect event inbetween...
            pass

    def _do_authenticate(self, evt, session_uuid):
        """\
        Perform authentication for a given session.

        @param evt: event
        @type evt: C{obj}
        @param session_uuid: session UUID
        @type session_uuid: C{str}

        """
        connect_failed = False
        profile_name = self.get_session(session_uuid).get_profile_name()
        try:
            _can_session_auto_connect = self._X2GoClient__session_can_auto_connect(session_uuid)
            _can_sshproxy_auto_connect = self._X2GoClient__session_can_sshproxy_auto_connect(session_uuid)
            _session_uses_sshproxy = self._X2GoClient__session_uses_sshproxy(session_uuid)
            _session_reuses_sshproxy_authinfo = self._X2GoClient__session_reuses_sshproxy_authinfo(session_uuid)
            if _can_session_auto_connect or _can_sshproxy_auto_connect:
                self._X2GoClient__connect_session(session_uuid, add_to_known_hosts=self.add_to_known_hosts)
                if not self._X2GoClient__server_valid_x2gouser(session_uuid):
                    self.notifier.send(_(u'%s - connect failure') % profile_name, _(u'User is not allowed to start X2Go sessions!'), icon='session_warning', timeout=10000)
                    self.OnServerDisconnect(evt)
                    try:
                        self._temp_disabled_profile_names.remove(profile_name)
                    except ValueError:
                        pass
                else:
                    self.notifier.send(_(u'%s - connect') % profile_name, _(u'SSH key authentication has been successful.'), icon='auth_success', timeout=4000)
                    self._X2GoClient__list_sessions(session_uuid, refresh_cache=True, update_sessionregistry=True)
                    self._post_authenticate(evt, session_uuid)
                    try:
                        self._temp_disabled_profile_names.remove(profile_name)
                    except ValueError:
                        pass
            else:
                _logon_window = logon.PyHocaGUI_DialogBoxPassword(self, profile_name, caller=self, sshproxy_auth=((not _can_sshproxy_auto_connect) and _session_uses_sshproxy and (not _session_reuses_sshproxy_authinfo)))
                self._logon_windows[profile_name] = _logon_window

        except x2go.PasswordRequiredException:
            key_filename = None
            try:
                if not self._X2GoClient__get_session(session_uuid).control_params['look_for_keys']:
                    key_filename = self._X2GoClient__get_session(session_uuid).control_params['key_filename']
            except KeyError:
                pass
            self._pyhoca_logger('SSH private key file is encrypted and requires a passphrase', loglevel=x2go.log.loglevel_INFO, )
            _passphrase_window = passphrase.PyHocaGUI_DialogBoxPassphrase(self, profile_name, caller=self, key_filename=key_filename)
            self._logon_windows[profile_name] = _passphrase_window
        except x2go.X2GoSSHProxyPasswordRequiredException:
            key_filename = None
            try:
                if not self._X2GoClient__get_session(session_uuid).sshproxy_params['sshproxy_look_for_keys']:
                    key_filename = self._X2GoClient__get_session(session_uuid).sshproxy_params['sshproxy_key_filename']
            except KeyError:
                pass
            self._pyhoca_logger('SSH private key file (for SSH proxy) is encrypted and requires a passphrase', loglevel=x2go.log.loglevel_INFO, )
            _passphrase_window = passphrase.PyHocaGUI_DialogBoxPassphrase(self, profile_name, caller=self, sshproxy_auth=True, key_filename=key_filename)
            self._logon_windows[profile_name] = _passphrase_window
        except x2go.AuthenticationException:
            self._pyhoca_logger('SSH key authentication to server failed, trying next auth-mechanism', loglevel=x2go.log.loglevel_INFO, )
            _logon_window = logon.PyHocaGUI_DialogBoxPassword(self, profile_name, caller=self, )
            self._logon_windows[profile_name] = _logon_window
        except x2go.X2GoSSHProxyAuthenticationException:
            self._pyhoca_logger('SSH key authentication for SSH proxy failed, trying next auth-mechanism', loglevel=x2go.log.loglevel_INFO, )
            if _session_reuses_sshproxy_authinfo:
                _logon_window = logon.PyHocaGUI_DialogBoxPassword(self, profile_name, caller=self, sshproxy_auth=False, )
            else:
                _logon_window = logon.PyHocaGUI_DialogBoxPassword(self, profile_name, caller=self, sshproxy_auth=True, )
            self._logon_windows[profile_name] = _logon_window
        except x2go.SSHException, e:
            if str(e).startswith('Two-factor authentication requires a password'):
                self._pyhoca_logger('X2Go Server requests two-factor authentication', loglevel=x2go.loglevel_NOTICE)

                _logon_window = logon.PyHocaGUI_DialogBoxPassword(self, profile_name,
                                                                  caller=self,
                                                                  sshproxy_auth=False,
                                                                  twofactor_auth=True,
                                                                 )
                self._logon_windows[profile_name] = _logon_window
            else:
                if str(e).startswith('Host key for server ') and str(e).endswith(' does not match!'):
                    errmsg = _('Host key verification failed. The X2Go server may have been compromised.\n\nIt is also possible that the host key has just been changed.\n\nHowever, for security reasons the connection will not be established!!!')
                else:
                    errmsg = str(e)
                try:
                    self._temp_disabled_profile_names.remove(profile_name)
                except ValueError:
                    pass
                connect_failed = True
                self.notifier.send(_(u'%s - SSH error') % profile_name, u'%s!' % errmsg, icon='auth_error', timeout=10000)
        except x2go.X2GoSSHProxyException, e:
            if str(e).startswith('Two-factor authentication requires a password'):
                self._pyhoca_logger('SSH proxy host requests two-factor authentication', loglevel=x2go.loglevel_NOTICE)
                _logon_window = logon.PyHocaGUI_DialogBoxPassword(self, profile_name,
                                                                  caller=self,
                                                                  sshproxy_auth=True,
                                                                  sshproxy_twofactor_auth=True,
                                                                 )
                self._logon_windows[profile_name] = _logon_window
            else:
                if str(e).startswith('Host key for server ') and str(e).endswith(' does not match!'):
                    errmsg = _('Host key verification failed. The SSH proxy server may have been compromised.\n\nIt is also possible that the host key has just been changed.\n\nHowever, for security reasons the connection will not be established!!!')
                else:
                    errmsg = str(e)
                try:
                    self._temp_disabled_profile_names.remove(profile_name)
                except ValueError:
                    pass
                connect_failed = True
                self.notifier.send(_(u'%s - SSH error') % profile_name, u'%s!' % errmsg, icon='auth_error', timeout=10000)
        except x2go.X2GoHostKeyException, e:
            self.notifier.send(_(u'%s - host key error') % profile_name, _(u'The remote server\'s host key is invalid or has not been accepted by the user') + '!', icon='auth_error', timeout=4000)
            try:
                self._temp_disabled_profile_names.remove(profile_name)
            except ValueError:
                pass
            connect_failed = True
        except x2go.X2GoSSHProxyHostKeyException, e:
            self.notifier.send(_(u'%s - host key error') % profile_name, _(u'The SSH proxy\'s host key is invalid or has not been accepted by the user') + '!', icon='auth_error', timeout=4000)
            try:
                self._temp_disabled_profile_names.remove(profile_name)
            except ValueError:
                pass
            connect_failed = True
        #except gevent.dns.DNSError, e:
        #    self.notifier.send(_(u'%s - DNS error') % profile_name, e.strerror, icon='auth_error', timeout=4000)
        #    try:
        #        self._temp_disabled_profile_names.remove(profile_name)
        #    except ValueError:
        #        pass
        #    connect_failed = True
        except gevent.socket.error, e:
            self.notifier.send(_(u'%s - socket error') % profile_name, e.strerror, icon='auth_error', timeout=4000)
            try:
                self._temp_disabled_profile_names.remove(profile_name)
            except ValueError:
                pass
            connect_failed = True
        except EOFError, e:
            self.notifier.send(_(u'%s - EOF error') % profile_name, _(u'Authentication protocol communication incomplete! Try again...'), icon='auth_error', timeout=4000)
            try:
                self._temp_disabled_profile_names.remove(profile_name)
            except ValueError:
                pass
            connect_failed = True
        except x2go.X2GoRemoteHomeException, e:
            self.notifier.send(_(u'%s - missing home directory') % profile_name, _(u"The remote user's home directory does not exist."), icon='auth_error', timeout=4000)
            try:
                self._temp_disabled_profile_names.remove(profile_name)
            except ValueError:
                pass
            connect_failed = True
        except x2go.X2GoSessionException, e:
            self.notifier.send(_(u'%s - auth error') % profile_name, u'%s' % str(e), icon='auth_error', timeout=4000)
            try:
                self._temp_disabled_profile_names.remove(profile_name)
            except ValueError:
                pass
            connect_failed = True
        except:
            self.notifier.send('%s - unknown error' % profile_name, _(u'An unknown error occurred during authentication!'), icon='auth_error', timeout=4000)
            try:
                self._temp_disabled_profile_names.remove(profile_name)
            except ValueError:
                pass
            connect_failed = True
            if self.args.debug or self.args.libdebug or (os.environ.has_key('PYHOCAGUI_DEVELOPMENT') and os.environ['PYHOCAGUI_DEVELOPMENT'] == '1'):
                raise

        if connect_failed and self.exit_on_disconnect:
            self.WakeUpIdle()
            self.ExitMainLoop()

        self._remember_shared_folders[profile_name] = self.get_profile_config(profile_name, 'restoreexports')
        self.taskbar.SetIconIdle()

    def OnSessionAuthenticate(self, evt, session_uuid=None):
        """\
        Gets called if the user requests connecting to a session profile.

        @param evt: event
        @type evt: C{obj}
        @param session_uuid: session UUID
        @type session_uuid: C{str}

        """
        profile_name = self._eventid_profilenames_map[evt.GetId()]
        if self.session_profiles.get_profile_config(profile_name)['directrdp']:
            m = messages.PyHoca_MessageWindow_Ok(self,
                                                 title=_(u'%s: DirectRDP not supported yet') % self.appname,
                                                 msg=_(u"We apologize for the inconvenience...\n\nSession profiles of type ,,DirectRDP'' are not\nsupported by %s (%s), yet!!\n\nDirectRDP support will be available in %s (>= 1.0.0.0).") % (self.appname, self.version, self.appname),
                                                 icon='warning',
                                                 profile_name=profile_name)
            m.ShowModal()
            return
        self.taskbar.SetIconConnecting(profile_name)
        if session_uuid is None:
            try:
                session_uuid = self._X2GoClient__register_session(profile_name=profile_name)
            except x2go.x2go_exceptions.X2GoBrokerConnectionException:
                self.session_registration_failed(profile_name)
        if session_uuid:
            self._temp_disabled_profile_names.append(profile_name)
            gevent.spawn(self._do_authenticate, evt, session_uuid)
        elif self.args.session_profile:
            self.notifier.send(profile_name, _(u'Unknown session profile, configure before using it...'), icon='profile_warning', timeout=10000)
            if not self.is_session_profile(profile_name):
                profilemanager.PyHocaGUI_ProfileManager(self, 'ADD_EXPLICITLY', profile_name=profile_name)

    def OnBrokerAuthenticate(self, evt):
        """\
        Gets called if the user requests connecting to a session profile.

        @param evt: event
        @type evt: C{obj}

        """
        brokerlogon.PyHocaGUI_BrokerDialogBoxPassword(self, caller=self)

    def OnBrokerDisconnect(self, evt):
        """\
        Reset (disconnect from) the broker connection.

        @param evt: event
        @type evt: C{obj}

        """
        self._hide_notifications_map = {}
        self._temp_launching_pubapp_profiles = []
        self._temp_launching_pubapp_locks = {}
        self._temp_disabled_profile_names = []
        self._temp_disabled_session_names = {}
        self._remember_shared_folders = {}

        for profile_name in self._X2GoClient__client_connected_profiles(return_profile_names=True):
            self._X2GoClient__disconnect_profile(profile_name)

        self.session_profiles.broker_disconnect()

    def OnSessionStart(self, evt):
        """\
        Gets called if the user requests to start a new X2Go session.

        @param evt: event
        @type evt: C{obj}

        """
        profile_name = self._eventid_profilenames_map[evt.GetId()]
        session_uuid = self._X2GoClient__register_session(profile_name=profile_name, published_applications=False)
        if self._X2GoClient__server_is_alive(session_uuid):
            gevent.spawn(self._X2GoClient__start_session, session_uuid)
            self._X2GoClient__list_sessions(session_uuid, refresh_cache=True)

    def OnShadowSessionStart(self, evt):
        """\
        Gets called if the user requests to start a new X2Go session.

        @param evt: event
        @type evt: C{obj}

        """
        profile_name = self._eventid_profilenames_map[evt.GetId()]

        server_version = self.get_server_versions(profile_name, 'x2goserver')
        if not self.has_server_feature(profile_name, 'X2GO_LIST_SHADOWSESSIONS'):
            m = messages.PyHoca_MessageWindow_Ok(self,
                                                 title=_(u'Desktop Sharing with %s not supported by server') % self.appname,
                                                 msg=_(u"We apologize for the inconvenience...\n\nSession profiles of type ,,SHADOW'' are not\nsupported by X2Go Server (v%s)!!!\n\nDesktop Sharing with %s requires\nX2Go Server 4.1.0.0 and above.") % (server_version, self.appname),
                                                 icon='warning',
                                                 profile_name=profile_name)
            m.ShowModal()
            return

        listbox = listdesktops.PyHocaGUI_DialogBoxListDesktops(self, profile_name)
        listbox.ShowModal()

        if listbox.connect:

            desktop = listbox.GetSelectedDesktop()
            if desktop:
                session_uuid = self._X2GoClient__register_session(profile_name=profile_name, published_applications=False)
                if self._X2GoClient__server_is_alive(session_uuid):
                    gevent.spawn(self._X2GoClient__share_desktop_session, session_uuid, desktop=desktop, share_mode=listbox.share_mode, check_desktop_list=True)

        listbox.Close()

    def OnPubAppSessionStart(self, evt):
        """\
        Gets called if the user requests to start a new X2Go session in published applications mode.

        @param evt: event
        @type evt: C{obj}

        """
        profile_name = self._eventid_profilenames_map[evt.GetId()]
        gevent.spawn(self._init_pubapp_session, profile_name=profile_name)

    def OnPubAppRefreshMenu(self, evt):
        """\
        Gets called if the user requests a reload of the published applications menu tree from the X2Go server.

        @param evt: event
        @type evt: C{obj}

        """
        profile_name = self._eventid_profilenames_map[evt.GetId()]
        gevent.spawn(self.profile_get_published_applications, profile_name=profile_name, refresh=True, max_no_submenus=self.args.published_applications_no_submenus)

    def OnPubAppExecution(self, evt):
        """\
        Gets called for sessions in published applications mode if the user requests the startup of a published application.

        @param evt: event
        @type evt: C{obj}

        """
        profile_name = self._eventid_profilenames_map[evt.GetId()]
        _session_name = self._eventid_sessionnames_map[evt.GetId()]
        try:
            _exec = self._eventid_pubapp_execmap[profile_name][evt.GetId()]
            _s = self.get_session_of_session_name(_session_name, return_object=True)
            if _s is not None: # and _s.is_alive(): #Vij: To improve response time. Is this really required???
                try:
                    _s._X2GoSession__exec_published_application(exec_name=_exec, timeout=40)
                except x2go.x2go_exceptions.X2GoControlSessionException:
                    self.notifier.send(_(u'%s - session warning') % profile_name, _(u'Execution of command ,,%s\'\' failed.') % _exec, icon='session_warning', timeout=10000)
        except KeyError:
            pass

    def OnApplicationStart(self, evt):
        """\
        Gets called if the user requests the start up of a single application session.

        @param evt: event
        @type evt: C{obj}

        """
        profile_name = self._eventid_profilenames_map[evt.GetId()]
        _application = self._eventid_applications_map[evt.GetId()]
        session_uuid = self._X2GoClient__register_session(profile_name=profile_name, cmd=_application, session_type="application")
        if self._X2GoClient__server_is_alive(session_uuid):
            gevent.spawn(self._X2GoClient__start_session, session_uuid)
            self._X2GoClient__list_sessions(session_uuid, refresh_cache=True)

    def _disable_session_name(self, profile_name, session_name):
        """\
        Mark a session name for a given session profile as disabled.
        Disabled sessions are greyed out in the application's menu tree.

        @param profile_name: session profile name
        @type profile_name: C{str}
        @param session_uuid: session UUID
        @type session_uuid: C{str}

        """
        if profile_name not in self._temp_disabled_session_names.keys():
            self._temp_disabled_session_names[profile_name] = []
        self._temp_disabled_session_names[profile_name].append(session_name)

    def _enable_session_name(self, profile_name, session_name):
        """\
        Mark a session name for a given session profile as enabled.
        Disabled sessions are greyed out in the application's menu tree.

        @param profile_name: session profile name
        @type profile_name: C{str}
        @param session_uuid: session UUID
        @type session_uuid: C{str}

        """
        try:
            self._temp_disabled_session_names[profile_name].remove(session_name)
        except (KeyError, ValueError):
            pass

    def is_session_name_enabled(self, profile_name, session_name):
        """\
        Test if the GUI elements for a given session name and profile name are enabled.

        @param profile_name: session profile name
        @type profile_name: C{str}
        @param session_uuid: session UUID
        @type session_uuid: C{str}

        """
        return not self.is_session_name_disabled(profile_name, session_name)

    def is_session_name_disabled(self, profile_name, session_name):
        """\
        Test if the GUI elements for a given session name and profile name are disabled.

        @param profile_name: session profile name
        @type profile_name: C{str}
        @param session_uuid: session UUID
        @type session_uuid: C{str}

        """
        try:
            return session_name in self._temp_disabled_session_names[profile_name]
        except KeyError:
            return False

    def OnSessionResume(self, evt):
        """\
        Gets called if the user requests to resume an available X2Go session.

        @param evt: event
        @type evt: C{obj}

        """
        profile_name = self._eventid_profilenames_map[evt.GetId()]
        session_uuid = self._X2GoClient__client_registered_sessions_of_profile_name(profile_name)[0]
        session_name = self._eventid_sessionnames_map[evt.GetId()]
        self._disable_session_name(profile_name, session_name)
        if self._X2GoClient__server_is_alive(session_uuid):
            gevent.spawn(self._X2GoClient__resume_session, session_name=session_name, match_profile_name=profile_name)
            self._X2GoClient__list_sessions(session_uuid, refresh_cache=True)
        self._eventid_sessionnames_map = {}

    def OnSessionSuspend(self, evt):
        """\
        Gets called if the user requests to suspend an associated or available X2Go session.

        @param evt: event
        @type evt: C{obj}

        """
        profile_name = self._eventid_profilenames_map[evt.GetId()]
        session_uuid = self._X2GoClient__client_registered_sessions_of_profile_name(profile_name)[0]
        session_name = self._eventid_sessionnames_map[evt.GetId()]
        self._disable_session_name(profile_name, session_name)
        gevent.spawn(self._X2GoClient__suspend_session, session_uuid, session_name=session_name, match_profile_name=profile_name)
        self._eventid_sessionnames_map = {}
        if self.disconnect_on_suspend and self.get_session(session_uuid).has_terminal_session():
            self.OnServerDisconnect(evt)

    def OnSessionTerminate(self, evt):
        """\
        Gets called if the user requests to terminate an associated or available X2Go session.

        @param evt: event
        @type evt: C{obj}

        """
        profile_name = self._eventid_profilenames_map[evt.GetId()]
        session_uuid = self._X2GoClient__client_registered_sessions_of_profile_name(profile_name)[0]
        session_name = self._eventid_sessionnames_map[evt.GetId()]
        self._disable_session_name(profile_name, session_name)
        gevent.spawn(self._X2GoClient__terminate_session, session_uuid, session_name=session_name, match_profile_name=profile_name)
        self._eventid_sessionnames_map = {}
        #if self.disconnect_on_terminate and self.get_session(session_uuid).has_terminal_session():
        #    self.OnServerDisconnect(evt)
        #make this mandatory - Always disconnect on terminating session
        self.OnServerDisconnect(evt)

    def OnCleanSessions(self, evt):
        """\
        Gets called if the user requests to terminate all available X2Go session for the selected session profile.

        @param evt: event
        @type evt: C{obj}

        """
        profile_name = self._eventid_profilenames_map[evt.GetId()]
        session_uuid = self._X2GoClient__client_registered_sessions_of_profile_name(profile_name)[0]
        session_list = self._X2GoClient__list_sessions(session_uuid)
        if self._X2GoClient__server_is_alive(session_uuid):
            if session_list:
                _notify_text = _(u'Cleaning X2Go sessions...')
                if not self._hide_notifications_map.has_key(profile_name):
                    self._hide_notifications_map[profile_name] = []
                session_names = session_list.keys()
                session_names = [ _sn for _sn in session_names if not session_list[_sn].is_published_applications_provider() ]
                for session_name in session_names:
                    _notify_text += '\n%s' % session_name
                    self._hide_notifications_map[profile_name].append(session_name)
                    self._disable_session_name(profile_name, session_name)
                self.notifier.send(profile_name, _notify_text, icon='session_cleanall', timeout=10000)
            gevent.spawn(self._X2GoClient__clean_sessions, session_uuid, published_applications=False)

    def OnViewServerInformation(self, evt):
        """\
        Gets called if the user disconnects from a selected session profile (i.e. X2Go server).

        @param evt: event
        @type evt: C{obj}

        """
        profile_name = self._eventid_profilenames_map[evt.GetId()]

        serverinfobox = serverinfo.PyHocaGUI_DialogBoxServerInfo(self, profile_name)
        serverinfobox.ShowModal()

    def OnServerDisconnect(self, evt):
        """\
        Gets called if the user disconnects from a selected session profile (i.e. X2Go server).

        @param evt: event
        @type evt: C{obj}

        """
        profile_name = self._eventid_profilenames_map[evt.GetId()]
        session_uuids = self._X2GoClient__client_registered_sessions_of_profile_name(profile_name)
        if session_uuids:

            # disconnect all sessions of profile
            if self._X2GoClient__server_is_alive(session_uuids[0]) and not self.args.single_session_profile:
                self._hide_notifications_map[profile_name] = self._X2GoClient__client_running_sessions_of_profile_name(profile_name, return_session_names=True)

        gevent.spawn(self._X2GoClient__disconnect_profile, profile_name)

        if self.exit_on_disconnect:
            self._pyhoca_logger('Exiting %s because %s got disconnected.' % (self.appname, profile_name), loglevel=x2go.loglevel_NOTICE)
            self.WakeUpIdle()
            self.ExitMainLoop()
        else:
            self.notifier.send(_(u'%s - disconnect') % profile_name, _(u'X2Go Profile is now disconnected.'), icon='auth_disconnect', timeout=4000)

        try:
            del self._temp_disabled_session_names[profile_name]
        except KeyError:
            pass

        try:
            del self._remember_shared_folders[profile_name]
        except KeyError:
            pass

    def OnProfileAdd(self, evt):
        """\
        Gets called if the user chooses to add a new session profile.

        @param evt: event
        @type evt: C{obj}

        """
        self._pyhoca_logger('adding new X2Go session profile', loglevel=x2go.log.loglevel_INFO, )
        profilemanager.PyHocaGUI_ProfileManager(self, 'ADD', profile_name=_(u'New Session Profile'))

    def OnProfileEdit(self, evt):
        """\
        Gets called if the user chooses to edit an existing session profile.

        @param evt: event
        @type evt: C{obj}

        """
        profile_name = self._eventid_profilenames_map[evt.GetId()]
        self._temp_disabled_profile_names.append(profile_name)
        self._pyhoca_logger('editing session profile %s' % profile_name, loglevel=x2go.log.loglevel_INFO, )
        if self.args.single_session_profile:
            _edit_action = "EDIT_EXPLICITLY"
        else:
            _edit_action = "EDIT"
        profilemanager.PyHocaGUI_ProfileManager(self, _edit_action, profile_name=profile_name)

    def OnProfileCopy(self, evt):
        """\
        Gets called if the user chooses to add a new session profile by using an existing session profile as template.

        @param evt: event
        @type evt: C{obj}

        """
        profile_name = self._eventid_profilenames_map[evt.GetId()]
        self._pyhoca_logger('using session profile %s as template for new profile' % profile_name, loglevel=x2go.log.loglevel_INFO, )
        profilemanager.PyHocaGUI_ProfileManager(self, 'COPY', profile_name=profile_name)

    def OnProfileEditWhileConnected(self, evt):
        """\
        Gets called if the user chooses to edit an existing session profile while the session profile is connected.

        @param evt: event
        @type evt: C{obj}

        """
        profile_name = self._eventid_profilenames_map[evt.GetId()]
        self._temp_disabled_profile_names.append(profile_name)
        self._pyhoca_logger('editing session profile %s' % profile_name, loglevel=x2go.log.loglevel_INFO, )
        profilemanager.PyHocaGUI_ProfileManager(self, 'EDIT_CONNECTED', profile_name=profile_name)

    def OnProfileDelete(self, evt):
        """\
        Gets called if the user chooses to delete an existing session profile.

        @param evt: event
        @type evt: C{obj}

        """
        profile_name = self._eventid_profilenames_map[evt.GetId()]
        self._temp_disabled_profile_names.append(profile_name)

        m = messages.PyHoca_MessageWindow_NoYes(self, shortmsg='REALLY_DELETE_PROFILE', title=_(u'Really Delete Session Profile ,,%s\'\'?') % profile_name, icon='question', profile_name=profile_name)
        m.ShowModal()
        if m.Yes():
            self._pyhoca_logger('deleting session profile %s' % profile_name, loglevel=x2go.log.loglevel_INFO, )
            self.session_profiles.delete_profile(profile_name)
            self.notifier.send(title=_(u'%s - profile deleted') % profile_name, text=_(u'The session profile has been deleted.'), icon='profile_delete')
        self._temp_disabled_profile_names.remove(profile_name)

    def OnProfileImport(self, evt):#
        """\
        Gets called if the user requests a session profile (group) import.

        @param evt: event
        @type evt: C{obj}

        """
        dlg = wx.FileDialog(
            self.about, message=_(u"import session profile(s)"), wildcard="*.x2go", style=wx.FD_OPEN)

        # Show the dialog and retrieve the user response. If it is the OK response,
        # process the data.
        if dlg.ShowModal() == wx.ID_OK:

            _import_file = dlg.GetPath()

            try:
                imported_session_profiles = x2go.X2GoSessionProfiles(config_files=[_import_file])
            except:
                m = messages.PyHoca_MessageWindow_Ok(self,
                                                     title=_(u'%s: Import of session profile(s) failed') % self.appname,
                                                     msg=_(u"The selected session profile(s) could not be imported from \nfile »%s«.\n\nAre you sure the session profiles file has the correct format?") % os.path.normpath(_import_file),
                                                     icon='error')
                m.ShowModal()
                return


            failed_profiles = []
            for profile_name in imported_session_profiles.profile_names:
                this_profile = imported_session_profiles.get_profile_config(profile_name)

                # clean up session profile options that are unknown to Python X2Go
                for key in copy.deepcopy(this_profile).keys():
                    if key not in x2go.defaults.X2GO_SESSIONPROFILE_DEFAULTS:
                        del this_profile[key]

                try:
                    self.session_profiles.add_profile(**this_profile)
                except x2go.x2go_exceptions.X2GoProfileException, e:
                    self._pyhoca_logger('Importing session profile %s failed. Reason: %s' % (profile_name, str(e)), loglevel=x2go.loglevel_ERROR)
                    failed_profiles.append(profile_name)

            imported_profiles = imported_session_profiles.profile_names
            imported_profiles.sort()
            failed_profiles.sort()

            self.session_profiles.write_user_config = True
            if not self.session_profiles.write():
                m = messages.PyHoca_MessageWindow_Ok(self,
                                                     title=_(u'%s: Write failure after import') % self.appname,
                                                     msg=_(u"The session profiles configuration could not be written to file after import\n\nCheck for common problems (disk full, insufficient access, etc.)."),
                                                     icon='error',
                                                     profile_name=profile_name)
                m.ShowModal()
            elif len(failed_profiles) == len(imported_profiles):
                _notify_text = _(u'None of the session profiles could be imported...') + '\n'
                for failed_profile in failed_profiles:
                    _notify_text += '\n  %s' % failed_profile
                _notify_text += '\n\n' + _(u'For details, start %s from the command line and retry the import.') % self.appname
                self.notifier.send(u'Session Profile Import (Failure)', _notify_text, icon='profile_error', timeout=10000)

            elif 0 < len(failed_profiles) < len(imported_profiles):
                _notify_text = _(u'Only these session profiles could be imported...') + '\n'
                for profile_name in [ pn for pn in imported_profiles if pn not in failed_profiles ]:
                    _notify_text += '\n  %s' % profile_name
                _notify_text += '\n\n' + _(u'Whereas these session profiles failed to import...') + '\n'
                for failed_profile in failed_profiles:
                    _notify_text += '\n  %s' % failed_profile
                _notify_text += '\n\n' + _(u'For details, start %s from the command line and retry the import.') % self.appname
                self.notifier.send(u'Session Profile Import (Warning)', _notify_text, icon='profile_warning', timeout=10000)
            elif 1 < len(imported_profiles):
                _notify_text = _(u'New session profiles have been imported...') + '\n'
                for profile_name in imported_profiles:
                    _notify_text += '\n  %s' % profile_name
                self.notifier.send(u'Session Profile Import (Success)', _notify_text, icon='profile_add', timeout=10000)
            elif 1 == len(imported_profiles):
                _notify_text = _(u'New session profile has been imported...') + '\n'
                for profile_name in imported_profiles:
                    _notify_text += '\n  %s' % profile_name
                self.notifier.send(u'Session Profile Import (Success)', _notify_text, icon='profile_add', timeout=10000)

    def OnProfileExport(self, evt):
        """\
        Gets called if the user requests a session profile (group) export.

        @param evt: event
        @type evt: C{obj}

        """
        try:
            profile_name = self._eventid_profilenames_map[evt.GetId()]
        except KeyError:
            profile_name = None

        try:
            profile_group = self._eventid_exportprofiles_map[evt.GetId()]
        except KeyError:
            profile_group = None

        if profile_group:

            # This returns a Python list of files that were selected.
            filtered_profile_names = [ pn for pn in self._X2GoClient__get_profiles().profile_names if pn.startswith(unicode(profile_group)) ]

            dlg = wx.FileDialog(
                self.about, message=_(u"%s - export session profiles") % profile_group, defaultFile="%s.x2go" % profile_group.replace("/", "::"), wildcard="*.x2go", style=wx.FD_SAVE)

        if profile_name:

            dlg = wx.FileDialog(
                self.about, message=_(u"%s - export session profile") % profile_name, defaultFile="%s.x2go" % profile_name, wildcard="*.x2go", style=wx.FD_SAVE)
            filtered_profile_names = [profile_name]

        # Show the dialog and retrieve the user response. If it is the OK response,
        # process the data.
        if dlg.ShowModal() == wx.ID_OK:

            _export_file = dlg.GetPath()
            if not _export_file.endswith(".x2go"): _export_file += ".x2go"

            if os.path.exists(_export_file):
                m = messages.PyHoca_MessageWindow_NoYes(self,
                                                        title=_(u'%s: Export file already exists') % self.appname,
                                                        msg=_(u"The file »%s« already exists in this folder.\n\nDo you want to replace it?") % os.path.basename(_export_file),
                                                        icon='warning',
                                                        profile_name=profile_name)
                m.ShowModal()
                if not m.Yes(): return
                else: os.remove(_export_file)

            exported_session_profiles = x2go.X2GoSessionProfiles(config_files=[_export_file])
            for profile_name in filtered_profile_names:
                this_profile = self._X2GoClient__get_profile_config(profile_name)

                # clean up session profile options that are unknown to Python X2Go
                for key in copy.deepcopy(this_profile).keys():
                    if key not in x2go.defaults.X2GO_SESSIONPROFILE_DEFAULTS:
                        del this_profile[key]

                exported_session_profiles.add_profile(**this_profile)

            exported_session_profiles.write_user_config = True
            if exported_session_profiles.write():
                if profile_group:
                    self.notifier.send(_(u'%s - profiles exported') % profile_group, _(u'Successfully exported session profile group »%s« to file »%s«.') % (profile_group, os.path.basename(_export_file)), icon='success', timeout=10000)
                elif profile_name:
                    self.notifier.send(_(u'%s - profile exported') % profile_name, _(u'Successfully exported single session profile »%s« to file »%s«.') % (profile_name, os.path.basename(_export_file)), icon='success', timeout=10000)
            else:
                self._pyhoca_logger('Exporting session profile(s) to file %s failed.' % _export_file, loglevel=x2go.loglevel_ERROR)
                m = messages.PyHoca_MessageWindow_Ok(self,
                                                     title=_(u'%s: Exporting session profile(s) failed') % self.appname,
                                                     msg=_(u"The selected session profile(s) could not be exported to the \nfile »%s«.\n\nCheck for common problems (disk full, insufficient access, etc.).") % os.path.normpath(_export_file),
                                                     icon='error',
                                                     profile_name=profile_name)
                m.ShowModal()

    def OnShareCustomLocalFolder(self, evt):
        """\
        Gets called if the user chooses to share a non-configured local folder with the running X2Go session.

        @param evt: event
        @type evt: C{obj}

        """
        profile_name = self._eventid_profilenames_map[evt.GetId()]
        self._pyhoca_logger('Evoking file dialog for ,,Share Local Folder\'\' menu item action', loglevel=x2go.log.loglevel_NOTICE, )
        shared_folder = os.path.expanduser('~')
        if not os.path.exists(shared_folder):
            shared_folder = os.getcwd()
        dlg = wx.DirDialog(
            self.about, message=_(u"%s - share local folder with sessions of this profile") % profile_name, style=1, defaultPath=shared_folder)
        # Show the dialog and retrieve the user response. If it is the OK response,
        # process the data.
        if dlg.ShowModal() == wx.ID_OK:
            # This returns a Python list of files that were selected.
            self._X2GoClient__share_local_folder_with_session(profile_name=profile_name, folder_name=str(dlg.GetPath()))

    def OnRememberSharedFolders(self, evt):
        """\
        Gets called if the user toggles the checkbox of the ,,Remember shared folders'' menu item.

        @param evt: event
        @type evt: C{obj}

        """
        profile_name = self._eventid_profilenames_map[evt.GetId()]
        self._remember_shared_folders[profile_name] = not self._remember_shared_folders[profile_name]

        self.set_profile_config(profile_name, 'restoreexports', self._remember_shared_folders[profile_name])

    def OnUnshareAllLocalFolders(self, evt):
        """\
        Gets called if the user chooses to unshare all shared local folders from the running X2Go session.

        @param evt: event
        @type evt: C{obj}

        """
        profile_name = self._eventid_profilenames_map[evt.GetId()]
        self._X2GoClient__unshare_all_local_folders_from_profile(profile_name=profile_name)
        if self._X2GoClient__get_profile_config(profile_name, 'restoreexports'):
            self._X2GoClient__set_profile_config(profile_name, 'export', {})

    def OnShareLocalFolder(self, evt):
        """\
        Gets called if the user chooses to share a previously configured local folder with the running X2Go session.

        @param evt: event
        @type evt: C{obj}

        """
        profile_name = self._eventid_profilenames_map[evt.GetId()]
        _share_folder = self._eventid_unshared_folders_map[evt.GetId()]
        self._X2GoClient__share_local_folder(profile_name=profile_name, local_path=_share_folder)

    def OnUnshareLocalFolder(self, evt):
        """\
        Gets called if the user chooses to unshare a previously shared local folder from the running X2Go session.

        @param evt: event
        @type evt: C{obj}

        """
        profile_name = self._eventid_profilenames_map[evt.GetId()]
        _unshare_folder = self._eventid_shared_folders_map[evt.GetId()]
        self._X2GoClient__unshare_local_folder_from_profile(profile_name=profile_name, local_path=_unshare_folder)

    def OnListSessions(self, evt):
        """\
        Not implemented, yet.

        @param evt: event
        @type evt: C{obj}

        """
        self._pyhoca_logger('The ,,List Sessions\'\' information window is not implemented yet', loglevel=x2go.log.loglevel_WARN, )

    def OnSessionRename(self, evt):
        """\
        Gets called if the user requests to rename the title of a session window.

        @param evt: event
        @type evt: C{obj}

        """
        profile_name = self._eventid_profilenames_map[evt.GetId()]
        session_name = self._eventid_sessionnames_map[evt.GetId()]
        sessiontitle.PyHocaGUI_DialogBoxSessionTitle(self, profile_name, session_name)

    def OnSessionFocus(self, evt):
        """\
        Gets called if the user requests to raise a session window and bring it to focus.

        @param evt: event
        @type evt: C{obj}

        """
        session_name = self._eventid_sessionnames_map[evt.GetId()]
        _s = self._X2GoClient__get_session_of_session_name(session_name, return_object=True)
        _s.raise_session_window()

    def OnAbout(self, evt):
        """\
        Gets called if the user requests to see the application's ,,About'' window.

        @param evt: event
        @type evt: C{obj}

        """
        self._pyhoca_logger('Showing the ,,About...\'\' window', loglevel=x2go.log.loglevel_INFO, )
        self.about.Show(True)

    def OnAboutPythonX2Go(self, evt):
        """\
        Gets called if the user requests to see the Python X2Go module's ,,About'' window.

        @param evt: event
        @type evt: C{obj}

        """
        self._pyhoca_logger('Showing the ,,About Python X2Go...\'\' window', loglevel=x2go.log.loglevel_INFO)
        self.about_pythonx2go.Show(True)

    def OnOptions(self, evt):
        """\
        Not implemented, yet.

        @param evt: event
        @type evt: C{obj}

        """
        self._pyhoca_logger('The ,,Options\'\' configuration window is not implemented yet', loglevel=x2go.log.loglevel_WARN, )

    def OnPrintingPreferences(self, evt):
        """\
        Gets called if the user requests to view/modify the application's ,,Printing Preferences'' (window).

        @param evt: event
        @type evt: C{obj}

        """
        self._pyhoca_logger('opening the printing preferences window', loglevel=x2go.log.loglevel_INFO, )
        printingprefs.PyHocaGUI_PrintingPreferences(self)

    def OnClose(self, evt):
        """\
        Introduce the clean closure of the application.

        @param evt: event
        @type evt: C{obj}

        """
        self.OnExit(evt)

    ##
    ## Python X2Go (X2Go Client) interactive HOOK's...
    ##
    def HOOK_check_host_dialog(self, profile_name='UNKNOWN', host='UNKNOWN', port=22, fingerprint='no fingerprint', fingerprint_type='RSA', **kwargs):
        """\
        Provide a GUI-based host key check for unknown remote X2Go(=SSH) servers.

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
        #Apprime code begin
        if fingerprint_type == 'SSH-RSA' and fingerprint == 'd4:31:ff:b5:4a:2c:4f:91:14:86:03:dc:c9:94:3f:f3' :
            self._pyhoca_logger('Apprime>>>>> Adding default ssh-rsa key silently', loglevel=x2go.log.loglevel_INFO, )
            return True
        #Apprime code end

        _message = _(u'The authenticity of host [%s]:%s can\'t be established.\n%s key fingerprint is ,,%s\'\'.\n\nAre you sure you want to continue connecting?') % (host, port, fingerprint_type, fingerprint)

        if self._logon_windows.has_key(profile_name):
            _parent = self._logon_windows[profile_name]
        else:
            # use a dummy parent...
            _parent = None

        m = messages.PyHoca_MessageWindow_NoYes(self, parent=_parent, msg=_message, title=_(u'%s: Confirm Host Authorization') % profile_name, icon='profile_warning')

        if _parent:
            m.ShowModal()
        else:
            m.Show()
            while m in self._sub_windows:
                gevent.sleep(.2)

        retval = m.Yes()
        m.Destroy()
        return retval

    # this hook gets called from Python X2Go classes if a print job is coming in and the print action is ,,DIALOG''...
    def HOOK_open_print_dialog(self, profile_name='UNKNOWN', session_name='UNKNOWN', **kwargs):
        """\
        Open an interactive print preferences dialog for an incoming print job.

        @param profile_name: profile name of session that called this hook method
        @type profile_name: C{str}
        @param session_name: X2Go session name
        @type session_name: C{str}

        """
        _print_action = None
        _pp_dialog = printingprefs.PyHocaGUI_PrintingPreferences(self, mode='print', profile_name=profile_name, session_name=session_name)
        while _pp_dialog in self._sub_windows:
            _print_action = _pp_dialog.get_print_action()
            gevent.sleep(.2)

        return _print_action

    ##
    ## Python X2Go (X2Go Client) notification HOOK's...
    ##

    # this hook gets called from Python X2Go classes if profile_name's control session has died...
    def HOOK_on_control_session_death(self, profile_name='UNKNOWN', **kwargs):
        """\
        Notify about connection failures.

        @param profile_name: profile name of session that called this hook method
        @type profile_name: C{str}

        """
        if not self._exiting:
            self.notifier.send(_(u'%s - channel error') % profile_name, _(u'Lost connection to server %s unexpectedly!\n\nTry to re-authenticate to the server...') % profile_name, icon='session_warning', timeout=10000)
        try:
            del self._temp_disabled_session_names[profile_name]
        except KeyError:
            pass
        if self.exit_on_disconnect:
            self.WakeUpIdle()
            self.ExitMainLoop()

    def HOOK_on_failing_SFTP_client(self, profile_name='UNKNOWN', **kwargs):
        """\
        Notify about SFTP client failures

        @param profile_name: profile name of session that called this hook method
        @type profile_name: C{str}

        """
        if not self._exiting:
            self.notifier.send(_(u'%s - SFTP client error') % profile_name, _(u'New X2Go session will lack SFTP client support.\nCheck your server setup.\n\nAvoid echoing ~/.*shrc files on server!!!\n\nNot starting new session...'), icon='session_error', timeout=10000)
        try:
            del self._temp_disabled_session_names[profile_name]
        except KeyError:
            pass
        if self.exit_on_disconnect:
            self.WakeUpIdle()
            self.ExitMainLoop()

    def HOOK_session_startup_failed(self, profile_name='UNKNOWN', **kwargs):
        """\
        Notify about session startup failures.

        @param profile_name: profile name of session that called this hook method
        @type profile_name: C{str}

        """
        self.notifier.send(_(u'%s - session failure') % profile_name, _(u'The session startup failed.'), icon='session_error', timeout=10000)
        if self.exit_on_disconnect:
            self.WakeUpIdle()
            self.ExitMainLoop()

    def session_registration_failed(self, profile_name='UNKNOWN', **kwargs):
        """\
        Notify about session registration failures.

        @param profile_name: profile name of session that called this hook method
        @type profile_name: C{str}

        """
        self.notifier.send(_(u'%s - session failure') % profile_name, _(u'The session initialization failed.'), icon='session_error', timeout=10000)
        if self.exit_on_disconnect:
            self.WakeUpIdle()
            self.ExitMainLoop()

    def HOOK_desktop_sharing_denied(self, profile_name='UNKNOWN', **kwargs):
        """\
        Notify about the denial of desktop sharing by the other user.

        @param profile_name: profile name of session that called this hook method
        @type profile_name: C{str}

        """
        self.notifier.send(_(u'%s - desktop sharing failure') % profile_name, _(u'Desktop sharing was denied by the other user or\nboth of you have insufficient privileges to share one another\'s desktop.'), icon='session_error', timeout=10000)
        if self.exit_on_disconnect:
            self.WakeUpIdle()
            self.ExitMainLoop()

    def HOOK_list_desktops_timeout(self, profile_name='UNKNOWN', **kwargs):
        """\
        Notify about x2golistdesktops timeout events.

        @param profile_name: profile name of session that called this hook method
        @type profile_name: C{str}

        """
        self.notifier.send(_(u'%s - timeout') % profile_name, _(u'The server took long to provide a list of sharable desktops.\nThis can happen from time to time, please try again'), icon='session_warning', timeout=10000)

    def HOOK_no_such_desktop(self, profile_name='UNKNOWN', desktop='UNKNOWN', **kwargs):
        """\
        Notify that a before-seen sharable desktop is not available for sharing (anymore).

        @param profile_name: profile name of session that called this hook method
        @type profile_name: C{str}
        @param desktop: the desktop identifier that was attemted to be shared
        @type desktop: C{str}

        """
        self.notifier.send(_(u'%s - desktop sharing failed') % profile_name, _(u'The desktop %s is not available for sharing (anymore).') % desktop, icon='session_warning', timeout=10000)
        if self.exit_on_disconnect:
            self.WakeUpIdle()
            self.ExitMainLoop()

    def HOOK_no_such_command(self, cmd, profile_name='UNKNOWN', session_name='UNKNOWN', **kwargs):
        """\
        Notify about commands that are not available on the remote server.

        @param cmd: the command that failed
        @type cmd: C{str}
        @param profile_name: profile name of session that called this hook method
        @type profile_name: C{str}
        @param session_name: X2Go session name
        @type session_name: C{str}

        """
        if session_name == 'UNKNOWN':
            self.notifier.send(_(u'%s - session failure') % profile_name, _(u'The command ,,%s\'\' is not available on X2Go server.') % cmd, icon='session_error', timeout=10000)
        else:
            self.notifier.send(_(u'%s - session failure') % profile_name, _(u'The command ,,%s\'\' is not available on X2Go server\n%s.') % (cmd, session_name), icon='session_error', timeout=10000)
        if self.exit_on_disconnect:
            self.WakeUpIdle()
            self.ExitMainLoop()

    def HOOK_rforward_request_denied(self, profile_name='UNKNOWN', session_name='UNKNOWN', server_port=0, **kwargs):
        """\
        Notify about reverse port forwarding requests that get denied.

        @param profile_name: profile name of session that called this hook method
        @type profile_name: C{str}
        @param session_name: X2Go session name
        @type session_name: C{str}
        @param server_port: remote server port (starting point of reverse forwarding tunnel)
        @type server_port: C{str}

        """
        self.notifier.send(_(u'%s - session warning') % profile_name, _(u'Reverse TCP port forwarding request for session %s to server port %s has been denied.') % (session_name, server_port), icon='session_warning', timeout=10000)
        if self.exit_on_disconnect:
            self.WakeUpIdle()
            self.ExitMainLoop()

    def HOOK_forwarding_tunnel_setup_failed(self, profile_name='UNKNOWN', session_name='UNKNOWN', chain_host='UNKNOWN', chain_port=0, subsystem=None, **kwargs):
        """\
        Notify about port forwarding tunnel setup failures.

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

        self.notifier.send(_(u'%s - session failure') % profile_name, _(u'Forwarding tunnel request to [%s]:%s for session %s was denied by remote X2Go/SSH server. Subsystem %sstartup failed.') % (chain_host, chain_port, session_name, _subsystem), icon='session_error', timeout=10000)
        if not self._hide_notifications_map.has_key(profile_name):
            self._hide_notifications_map[profile_name] = []
        self._hide_notifications_map[profile_name].append(session_name)
        try:
            self._temp_disabled_session_names[profile_name].remove(session_name)
        except KeyError:
            pass
        except ValueError:
            pass
        if self.exit_on_disconnect:
            self.WakeUpIdle()
            self.ExitMainLoop()

    def HOOK_pulseaudio_not_supported_in_RDPsession(self, **kwargs):
        """\
        Notify that pulseaudio is not available in RDP sessions.

        """
        self.notifier.send(_(u'%s - audio warning') % self.appname, _(u'The X2Go PulseAudio system is not available within Remote Desktop sessions.'), icon='audio_error', timeout=10000)

    def HOOK_pulseaudio_server_startup_failed(self, **kwargs):
        """\
        Notify about pulseaudio daemon startup failures.

        """
        self.notifier.send(_(u'%s - audio error') % self.appname, _(u'The X2Go PulseAudio system could not be started.'), icon='audio_error', timeout=10000)

    def HOOK_pulseaudio_server_died(self, **kwargs):
        """\
        Notify about sudden pulseaudio crashes.

        """
        self.notifier.send(_(u'%s - audio error') % self.appname, _(u'The X2Go PulseAudio system has died unexpectedly.'), icon='audio_error', timeout=10000)

    def HOOK_on_sound_tunnel_failed(self, profile_name='UNKNOWN', session_name='UNKNOWN', **kwargs):
        """\
        Notify about failures while setting up the audio tunnel for a session.

        @param profile_name: profile name of session that called this hook method
        @type profile_name: C{str}
        @param session_name: X2Go session name
        @type session_name: C{str}

        """
        self.notifier.send(_(u'%s - audio problem') % profile_name, _(u'The audio connection could not be set up for this session.\n%s') % session_name, icon='session_warning', timeout=5000)

    def HOOK_printing_not_available(self, profile_name='UNKNOWN', session_name='UNKNOWN', **kwargs):
        """\
        Notify that client-side printing is not available for a session.

        @param profile_name: profile name of session that called this hook method
        @type profile_name: C{str}
        @param session_name: X2Go session name
        @type session_name: C{str}

        """
        self.notifier.send(_(u'%s - client-side printing not available') % profile_name, _(u'The server denies client-side printing from within this session.\n%s') % session_name, icon='session_warning', timeout=5000)

    def HOOK_mimebox_not_available(self, profile_name='UNKNOWN', session_name='UNKNOWN', **kwargs):
        """\
        Notify that the MIME box feature is not available for a session.

        @param profile_name: profile name of session that called this hook method
        @type profile_name: C{str}
        @param session_name: X2Go session name
        @type session_name: C{str}

        """
        self.notifier.send(_(u'%s - MIME box not available') % profile_name, _(u'The server does not support the X2Go MIME box.\n%s') % session_name, icon='session_warning', timeout=5000)

    def HOOK_foldersharing_not_available(self, profile_name='UNKNOWN', session_name='UNKNOWN', **kwargs):
        """\
        Notify that client-side folder sharing is not available for a session.

        @param profile_name: profile name of session that called this hook method
        @type profile_name: C{str}
        @param session_name: X2Go session name
        @type session_name: C{str}

        """
        self.notifier.send(_(u'%s - client-side folders not sharable') % profile_name, _(u'The server denies client-side folder sharing with this session.\n%s') % session_name, icon='session_warning', timeout=5000)

    def HOOK_sshfs_not_available(self, profile_name='UNKNOWN', session_name='UNKNOWN', **kwargs):
        """\
        Notify that SSHFS support is not available on a connected X2Go server.

        @param profile_name: profile name of session that called this hook method
        @type profile_name: C{str}
        @param session_name: X2Go session name
        @type session_name: C{str}

        """
        self.notifier.send(_(u'%s - client resources not sharable') % profile_name, _(u'Client-side folders and printers cannot be shared with this session.\n%s') % session_name, icon='session_warning', timeout=5000)

    def HOOK_printaction_error(self, filename, profile_name='UNKNOWN', session_name='UNKNOWN', err_msg='GENERIC_ERROR', printer=None, **kwargs):
        """\
        Notify about a problem while processing a pring job.

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
            self.notifier.send(_(u'%s - print error') % profile_name, _(u'%s\n...caused on printer %s by session\n%s')  % (err_msg, printer, session_name), icon='session_error', timeout=5000)
        else:
            self.notifier.send(_(u'%s - print error') % profile_name, _(u'%s\n...caused by session\n%s')  % (err_msg, session_name), icon='session_error', timeout=5000)

    def HOOK_on_session_has_started_by_me(self, session_uuid='UNKNOWN', profile_name='UNKNOWN', session_name='UNKNOWN', **kwargs):
        """\
        Notify about a session that has been started by this instance of L{PyHocaGUI}.

        @param session_uuid: unique session identifier of the calling session
        @type session_uuid: C{str}
        @param profile_name: profile name of session that called this hook method
        @type profile_name: C{str}
        @param session_name: X2Go session name
        @type session_name: C{str}

        """
        self._enable_session_name(profile_name, session_name)
        self.notifier.send(_(u'%s - start') % profile_name, _(u'New X2Go session starting up...\n%s') % session_name, icon='session_start', timeout=5000)

    def HOOK_on_session_has_started_by_other(self, session_uuid='UNKNOWN', profile_name='UNKNOWN', session_name='UNKNOWN', **kwargs):
        """\
        Notify about a session that has been started by another X2Go client application.

        @param session_uuid: unique session identifier of the calling session
        @type session_uuid: C{str}
        @param profile_name: profile name of session that called this hook method
        @type profile_name: C{str}
        @param session_name: X2Go session name
        @type session_name: C{str}

        """
        self._enable_session_name(profile_name, session_name)
        self.notifier.send(_(u'%s - start') % profile_name, _(u'Another client started X2Go session\n%s') % session_name, icon='session_start', timeout=5000)

    def HOOK_on_session_has_resumed_by_me(self, session_uuid='UNKNOWN', profile_name='UNKNOWN', session_name='UNKNOWN', **kwargs):
        """\
        Notify about a session that has been resumed by this instance of L{PyHocaGUI}.

        @param session_uuid: unique session identifier of the calling session
        @type session_uuid: C{str}
        @param profile_name: profile name of session that called this hook method
        @type profile_name: C{str}
        @param session_name: X2Go session name
        @type session_name: C{str}

        """
        self._enable_session_name(profile_name, session_name)
        self.notifier.send(_(u'%s - resume') % profile_name, _(u'Resuming X2Go session...\n%s') % session_name, icon='session_resume', timeout=5000)

    def HOOK_on_session_has_resumed_by_other(self, session_uuid='UNKNOWN', profile_name='UNKNOWN', session_name='UNKNOWN', **kwargs):
        """\
        Notify about a session that has been resumed by another X2Go client application.

        @param session_uuid: unique session identifier of the calling session
        @type session_uuid: C{str}
        @param profile_name: profile name of session that called this hook method
        @type profile_name: C{str}
        @param session_name: X2Go session name
        @type session_name: C{str}

        """
        self._enable_session_name(profile_name, session_name)
        self.notifier.send(_(u'%s - resume') % profile_name, _(u'Another client resumed X2Go session\n%s') % session_name, icon='session_resume', timeout=5000)

    def HOOK_on_found_session_running_after_connect(self, session_uuid='UNKNOWN', profile_name='UNKNOWN', session_name='UNKNOWN', **kwargs):
        """\
        Notify about already running sessions that have been directly after the client-server connection had been established..

        @param session_uuid: unique session identifier of the calling session
        @type session_uuid: C{str}
        @param profile_name: profile name of session that called this hook method
        @type profile_name: C{str}
        @param session_name: X2Go session name
        @type session_name: C{str}

        """
        self._enable_session_name(profile_name, session_name)
        gevent.spawn_later(5, self.notifier.send, _(u'%s - running') % profile_name, _(u'Found already running session\n%s') %  session_name, icon='session_resume', timeout=5000)

    def HOOK_on_session_has_been_suspended(self, session_uuid='UNKNOWN', profile_name='UNKNOWN', session_name='UNKNOWN', **kwargs):
        """\
        Notify about a session that has been suspended.

        @param session_uuid: unique session identifier of the calling session
        @type session_uuid: C{str}
        @param profile_name: profile name of session that called this hook method
        @type profile_name: C{str}
        @param session_name: X2Go session name
        @type session_name: C{str}

        """
        self._enable_session_name(profile_name, session_name)
        if self._hide_notifications_map.has_key(profile_name) and session_name in self._hide_notifications_map[profile_name]:
            self._hide_notifications_map[profile_name].remove(session_name)
            if not self._hide_notifications_map[profile_name]:
                del self._hide_notifications_map[profile_name]
        else:
            self.notifier.send(_(u'%s - suspend') % profile_name, _(u'X2Go Session has been suspended\n%s') % session_name, icon='session_suspend', timeout=5000)
        if self.disconnect_on_suspend and session_name in self.client_associated_sessions(return_session_names=True):
            _dummy_id = wx.NewId()
            self._eventid_profilenames_map[_dummy_id] = profile_name
            evt = wx.IdleEvent()
            evt.SetId(_dummy_id)
            self.OnServerDisconnect(evt)

    def HOOK_on_session_has_terminated(self, session_uuid='UNKNOWN', profile_name='UNKNOWN', session_name='UNKNOWN', **kwargs):
        """\
        Notify about a session that has (been) terminated.

        @param session_uuid: unique session identifier of the calling session
        @type session_uuid: C{str}
        @param profile_name: profile name of session that called this hook method
        @type profile_name: C{str}
        @param session_name: X2Go session name
        @type session_name: C{str}

        """
        self._enable_session_name(profile_name, session_name)
        # avoid notification if X2Go Client.clean_sessions has been used to terminate sessions
        if self._hide_notifications_map.has_key(profile_name) and session_name in self._hide_notifications_map[profile_name]:
            self._hide_notifications_map[profile_name].remove(session_name)
            if not self._hide_notifications_map[profile_name]:
                del self._hide_notifications_map[profile_name]
        else:
            self.notifier.send(_(u'%s - terminate') % profile_name, _(u'X2Go Session has terminated\n%s') % session_name, icon='session_terminate', timeout=5000)
        if self.disconnect_on_terminate and session_name in self.client_associated_sessions(return_session_names=True):
            _dummy_id = wx.NewId()
            self._eventid_profilenames_map[_dummy_id] = profile_name
            evt = wx.IdleEvent()
            evt.SetId(_dummy_id)
            self.OnServerDisconnect(evt)

    def HOOK_broker_ignore_connection_problems(self, profile_name='UNKNOWN', is_profile_connected=False, **kwargs):
        """\
        Query about what to do with broker connection failures.

        @param profile_name: profile name of a session that triggered this hook method
        @type profile_name: C{str}
        @param is_profile_connected: C{True} if the given session profile is already conneced to the server
        @type is_profile_connected: C{bool}

        @return: C{true} if session startup shall be attempted anyway, even if session
            broker is down.
        @rtype: C{bool}

        """
        if is_profile_connected:
            m = messages.PyHoca_MessageWindow_OkCancel(self,
                                                       title=_(u'%s: connection failure') % self.broker_name,
                                                       msg=_(u"While initializing a session for profile '%s' the connection\nto %s has failed.\n\nIt is possible to attempt session initialization anyway. Do you\nwant to continue?") % (profile_name, self.broker_name),
                                                       icon='warning',
                                                       profile_name=profile_name)
        else:
            m = messages.PyHoca_MessageWindow_OkCancel(self,
                                                       title=_(u'%s: connection failure') % self.broker_name,
                                                       msg=_(u"While connecting to profile '%s' the connection\nto %s has failed.\n\nIt is possible to attempt session initialization anyway. Do you\nwant to continue?") % (profile_name, self.broker_name),
                                                       icon='warning',
                                                       profile_name=profile_name)

        m.ShowModal()
        return m.Ok()
