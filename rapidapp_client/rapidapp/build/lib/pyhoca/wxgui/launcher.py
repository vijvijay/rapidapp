modules ={}

import sys
import os
import shutil
import argparse
import gettext
import subprocess
import copy
import socket
import urllib2
import zipfile
from subprocess import Popen

import wx

# we need to register a wx.App() instance before we load any
# of the X2Go modules. When importing x2go.*, gevent.monkey_patch_all()
# is called which seems to break wxPython 3.0...
_dummy_app = wx.App(redirect=False, clearSigInt=False)

from x2go import X2GOCLIENT_OS
from x2go import CURRENT_LOCAL_USER
from x2go import BACKENDS
from x2go import X2GoLogger

from pyhoca.wxgui import __VERSION__
from frontend import PyHocaGUI
from messages import PyHoca_MessageWindow_Ok

import defaults
import basepath


class PyHocaGUI_Launcher(object):

    def __init__(self):
        self.PROG_NAME = os.path.basename(sys.argv[0]).replace('.exe', '')
        self.PROG_PID = os.getpid()
        self.VERSION=__VERSION__
        self.VERSION_TEXT="""
%s[%s] - Appri.me Cloud app client.
VERSION: %s

""" % (self.PROG_NAME, self.PROG_PID, self.VERSION)

        self.default_options = defaults.default_options

    def setup_progname(self, pname):
        self.PROG_NAME = pname

    def setup_version(self, v):
        self.VERSION = v

    def setup_version_text(self, text):
        self.VERSION_TEXT = text

    def setup_process(self):
        PROG_OPTIONS = " ".join(sys.argv[1:]).replace("=", " ").split()
        try:
            _broker_password_index = PROG_OPTIONS.index('--broker-password')+1
            PROG_OPTIONS[_broker_password_index] = "XXXXXXXX"
        except ValueError:
            # ignore if --broker-password option is not specified
            pass
        if X2GOCLIENT_OS in ('Linux', 'Mac'):
            import setproctitle
            #setproctitle.setproctitle("%s %s" % (self.PROG_NAME, " ".join(PROG_OPTIONS)))
            setproctitle.setproctitle(self.PROG_NAME)

        if X2GOCLIENT_OS == 'Windows':
            from pyhoca.wxgui.basepath import nxproxy_binary
            os.environ.update({'NXPROXY_BINARY': nxproxy_binary, })

    def modify_default_option(self, option, value):
        if self.default_options.has_key(option):
            if type(self.default_options[option]) == type(value):
                self.default_options[option] = value

    def setup_devmode(self):
        if sys.argv[0].startswith('./') or sys.argv[0].startswith('python'):
            sys.path.insert(0, os.getcwd())
            os.environ['PYHOCAGUI_DEVELOPMENT'] = '1'
            print '### {progname} running in development mode ###'.format(progname=self.PROG_NAME)
            basepath.reload_base_paths()

    def check_running(self):
        _executable = os.path.basename(sys.argv[0])

        if X2GOCLIENT_OS  in ('Linux', 'Mac'):

            p = subprocess.Popen(['ps', '-U', CURRENT_LOCAL_USER, '-u', CURRENT_LOCAL_USER], stdout=subprocess.PIPE)
            psA_out = p.communicate()
            if psA_out[0].count(_executable) <= 1:

                if os.path.isdir(os.path.expanduser("~/.x2go/{progname}/".format(progname=_executable))):
                    shutil.rmtree(os.path.expanduser("~/.x2go/{progname}/".format(progname=_executable)))

            my_pid = str(os.getpid())
            if not os.path.exists(os.path.expanduser("~/.x2go/{progname}/".format(progname=_executable))):
                os.makedirs(os.path.expanduser("~/.x2go/{progname}/".format(progname=_executable)))
            my_pidfile = os.path.expanduser("~/.x2go/{progname}/display.{pid}".format(progname=_executable, pid=my_pid))

            my_display = os.environ['DISPLAY']
            open(my_pidfile, 'w').write(my_display)

            for pidfile in os.listdir(os.path.expanduser("~/.x2go/{progname}/".format(progname=_executable))):

                # this is our own pid file...
                if my_pidfile.endswith(pidfile):
                    continue

                display = open(os.path.expanduser("~/.x2go/{progname}/".format(progname=_executable)) + pidfile, 'r').read()

                if display.split('.')[0] == my_display.split('.')[0]:
                    other_pid = pidfile.split('.')[1]
                    print
                    print('One instance of {progname} (PID: {other_pid}) is already running for this $DISPLAY {display}'.format(progname=_executable, other_pid=other_pid, display=my_display))

                    return True

            return False

        elif X2GOCLIENT_OS == 'Windows':
            import wmi
            w = wmi.WMI()
            _p = {}
            for process in w.Win32_Process():
                if process.Name == _executable:
                    _p[process.ProcessId] = process.SessionId
            return len([ _p_id for _p_id in _p.keys() if _p[self.PROG_PID] ==  _p[_p_id] ]) > 1


    def version(self):
        # version information

        # print version text and exit
        sys.stderr.write ("%s\n" % self.VERSION_TEXT)
        self.remove_pidfile()

        sys.exit(0)


    # sometimes we have to fail...
    def runtime_error(self, m, parser=None, exitcode=-1):
        """\
        STILL UNDOCUMENTED
        """
        if parser is not None:
            parser.print_usage()
        sys.stderr.write ("%s: error: %s\n" % (self.PROG_NAME, m))

        self.remove_pidfile()
        sys.exit(exitcode)


    def remove_pidfile(self):

        if X2GOCLIENT_OS  in ('Linux', 'Mac'):
            my_pid = str(os.getpid())
            if os.path.exists(os.path.expanduser("~/.x2go/pyhoca-gui/display.{pid}".format(pid=my_pid))):
                os.remove(os.path.expanduser("~/.x2go/pyhoca-gui/display.{pid}".format(pid=my_pid)))


    def parseargs(self):

        _profiles_backend_default = BACKENDS['X2GoSessionProfiles']['default']
        _settings_backend_default = BACKENDS['X2GoClientSettings']['default']
        _printing_backend_default = BACKENDS['X2GoClientPrinting']['default']

        if X2GOCLIENT_OS == 'Windows':
            from x2go import X2GoClientXConfig
            _x = X2GoClientXConfig()
            _known_xservers = _x.known_xservers
            _installed_xservers = _x.installed_xservers

        if X2GOCLIENT_OS == 'Windows':
            _config_backends = ('FILE', 'WINREG')
        elif X2GOCLIENT_OS == 'Linux':
            _config_backends = ('FILE', 'GCONF')
        else:
            _config_backends = ('FILE')

        _default_options = copy.deepcopy(self.default_options)
        for key in _default_options.keys():
            if not _default_options[key]:
                _default_options[key] = None

        # debug options...
        debug_options =  [
            {'args':['-d','--debug'], 'default': _default_options['debug'], 'action': 'store_true', 'help': 'enable application debugging code', },
            {'args':['--quiet'], 'default': _default_options['quiet'], 'action': 'store_true', 'help': 'disable any kind of log output', },
            {'args':['--libdebug'], 'default': _default_options['libdebug'], 'action': 'store_true', 'help': 'enable debugging code of the underlying Python X2Go module', },
            {'args':['--libdebug-sftpxfer'], 'default': _default_options['libdebug_sftpxfer'], 'action': 'store_true', 'help': 'enable debugging code of Python X2Go\'s sFTP server code (very verbose, and even promiscuous)', },
            {'args':['-V', '--version'], 'default': _default_options['version'], 'action': 'store_true', 'help': 'print version number and exit', },
        ]
        x2go_gui_options = [
            {'args':['-P','--session-profile'], 'default': _default_options['session_profile'], 'metavar': '<profile-name>', 'help': 'directly connect to a session profile', },
            {'args':['--remember-username'], 'default': _default_options['remember_username'], 'action': 'store_true', 'help': 'for profiles with interactive authentication, remember the last-used username', },
            {'args':['--non-interactive'], 'default': _default_options['non_interactive'], 'action': 'store_true', 'help': 'run the session manager in non-interactive mode, this option sets the following options to true: --restricted-trayicon, --single_session_profile, --start-on-connect, --resume-all-on-connect, --exit-on-disconnect, --disconnect-on-suspend and --disconnect-on-terminate', },
            {'args':['--auto-connect'], 'default': _default_options['auto_connect'], 'action': 'store_true', 'help': 'connect sessions via SSH pubkey authentication if possible', },
            {'args':['--show-profile-metatypes'], 'default': _default_options['show_profile_metatypes'], 'action': 'store_true', 'help': 'show descriptive meta information on session profiles in menus (NOTE: this makes menus appear a bit more sluggish, use it mostly for debugging)', },
            {'args':['--single-session-profile'], 'default': _default_options['single_session_profile'], 'action': 'store_true', 'help': 'disable support of handling multiple session profiles', },
            {'args':['--tray-icon'], 'default': _default_options['tray_icon'], 'metavar': '<your-logo>', 'help': 'define an alternative system tray icon file (PNG files only, leave out file extension here, size 22x22 on Linux, 16x16 on Windows)', },
            {'args':['--tray-icon-connecting'], 'default': _default_options['tray_icon_connecting'], 'metavar': '<your-logo-while-connecting>', 'help': 'define an alternative system tray icon file while connecting to a server (PNG files only, leave out file extension here, size 22x22 on Linux, 16x16 on Windows)', },
            {'args':['--restricted-trayicon'], 'default': _default_options['restricted_trayicon'], 'action': 'store_true', 'help': 'restricts session manager\'s main icon functionality to information window and application exit; on left-click only a minimal session menu is shown', },
            {'args':['--add-to-known-hosts'], 'default': _default_options['add_to_known_hosts'], 'action': 'store_true', 'help': 'automatically add SSH host keys to the known_hosts files of the client-side user', },
            {'args':['--start-on-connect'], 'default': _default_options['start_on_connect'], 'action': 'store_true', 'help': 'This is now the hard-coded default. start a session directly after authentication if no session is currently running/suspended', },
            {'args':['--exit-on-disconnect'], 'default': _default_options['exit_on_disconnect'], 'action': 'store_true', 'help': 'exit the session manager after a server connection has died', },
            {'args':['--resume-newest-on-connect', '--resume-on-connect'], 'default': _default_options['resume_newest_on_connect'], 'action': 'store_true', 'help': 'This is now the hard-coded default. On connect auto-resume the newest suspended session', },
            {'args':['--resume-oldest-on-connect'], 'default': _default_options['resume_oldest_on_connect'], 'action': 'store_true', 'help': 'on connect auto-resume the oldest suspended session', },
            {'args':['--resume-all-on-connect'], 'default': _default_options['resume_all_on_connect'], 'action': 'store_true', 'help': 'auto-resume all suspended sessions on connect', },
            {'args':['--disconnect-on-suspend'], 'default': _default_options['disconnect_on_suspend'], 'action': 'store_true', 'help': 'disconnect a server if a session has been suspended', },
            {'args':['--disconnect-on-terminate'], 'default': _default_options['disconnect_on_terminate'], 'action': 'store_true', 'help': 'disconnect a server if a session has been terminated', },
            {'args':['--splash-image'], 'default': _default_options['splash_image'], 'metavar': '<your-splash-image>', 'help': 'define an alternative splash image that gets shown on application startup (PNG files only, full path or filename as found in <share>/img)', },
            {'args':['--about-image'], 'default': _default_options['about_image'], 'metavar': '<your-about-window-image>', 'help': 'define an alternative image for the application\'s ,,About\'\' window (PNG files only, full path or filename as found in <share>/img)', },
            {'args':['--disable-splash'], 'default': _default_options['disable_splash'], 'action': 'store_true', 'help': 'disable the applications splash screen', },
            {'args':['--disable-options'], 'default': _default_options['disable_options'], 'action': 'store_true', 'help': 'disable the client options configuration window', },
            {'args':['--disable-printingprefs'], 'default': _default_options['disable_printingprefs'], 'action': 'store_true', 'help': 'disable the client\'s printing preferences window', },
            {'args':['--disable-profilemanager'], 'default': _default_options['disable_profilemanager'], 'action': 'store_true', 'help': 'disable the session profile manager window', },
            {'args':['--disable-notifications'], 'default': _default_options['disable_notifications'], 'action': 'store_true', 'help': 'disable all applet notifications', },
            {'args':['--display'], 'default': _default_options['display'], 'metavar': '<hostname>:<screennumber>', 'help': 'set the DISPLAY environment variable to <hostname>:<screennumber>', },
            {'args':['--logon-window-position'], 'default': _default_options['logon_window_position'], 'metavar': '<x-pos>x<y-pos>', 'help': 'give a custom position for the logon window, use negative values to position relative to right/bottom border', },
            {'args':['--published-applications-no-submenus'], 'default': _default_options['published_applications_no_submenus'], 'metavar': '<number>', 'help': 'the number of published applications that will be rendered without submenus', },
        ]

        broker_options = [
            {'args':['-B','--broker-url'], 'default': _default_options['broker_url'], 'help': 'retrieve session profiles via an X2Go Session Broker under the given URL', },
            {'args':['--broker-password'], 'default': _default_options['broker_password'], 'help': 'password for authenticating against the X2Go Session Broker', },
            {'args':['--broker-name'], 'default': _default_options['broker_name'], 'help': 'tweak the wording of \'X2Go Session Broker\'', },
            {'args':['--broker-cacertfile'], 'default': _default_options['broker_cacertfile'], 'help': 'for https:// brokers with SSL certificates that have been signed against a self-signed root-CA, use this command line option to point to the self-signed root-CA certificate file', },
            {'args':['--broker-autoconnect'], 'default': _default_options['broker_autoconnect'], 'action': 'store_true', 'help': 'trigger broker authentication directly after application startup', },
        ]

        if X2GOCLIENT_OS == 'Windows':
            x2go_gui_options.append(
                {'args':['--lang'], 'default': _default_options['lang'], 'metavar': 'LANGUAGE', 'help': 'set the GUI language (currently available: en, de, nl, es)', },
            )

        backend_options = [
            {'args':['--backend-controlsession'], 'default': _default_options['backend_controlsession'], 'metavar': '<CONTROLSESSION_BACKEND>', 'choices': BACKENDS['X2GoControlSession'].keys(), 'help': 'force usage of a certain CONTROLSESSION_BACKEND (do not use this unless you know exactly what you are doing)', },
            {'args':['--backend-terminalsession'], 'default': _default_options['backend_terminalsession'], 'metavar': '<TERMINALSESSION_BACKEND>', 'choices': BACKENDS['X2GoTerminalSession'].keys(), 'help': 'force usage of a certain TERMINALSESSION_BACKEND (do not use this unless you know exactly what you are doing)', },
            {'args':['--backend-serversessioninfo'], 'default': _default_options['backend_serversessioninfo'], 'metavar': '<SERVERSESSIONINFO_BACKEND>', 'choices': BACKENDS['X2GoServerSessionInfo'].keys(), 'help': 'force usage of a certain SERVERSESSIONINFO_BACKEND (do not use this unless you know exactly what you are doing)', },
            {'args':['--backend-serversessionlist'], 'default': _default_options['backend_serversessionlist'], 'metavar': '<SERVERSESSIONLIST_BACKEND>', 'choices': BACKENDS['X2GoServerSessionList'].keys(), 'help': 'force usage of a certain SERVERSESSIONLIST_BACKEND (do not use this unless you know exactly what you are doing)', },
            {'args':['--backend-proxy'], 'default': _default_options['backend_proxy'], 'metavar': '<PROXY_BACKEND>', 'choices': BACKENDS['X2GoProxy'].keys(), 'help': 'force usage of a certain PROXY_BACKEND (do not use this unless you know exactly what you are doing)', },
            {'args':['--backend-sessionprofiles'], 'default': _default_options['backend_sessionprofiles'], 'metavar': '<SESSIONPROFILES_BACKEND>', 'choices': _config_backends, 'help': 'use given backend for accessing session profiles, available backends on your system: %s (default: %s)' % (', '.join(_config_backends), _profiles_backend_default), },
            {'args':['--backend-clientsettings'], 'default': _default_options['backend_clientsettings'], 'metavar': '<CLIENTSETTINGS_BACKEND>', 'choices': _config_backends, 'help': 'use given backend for accessing the client settings configuration, available backends on your system: %s (default: %s)' % (', '.join(_config_backends), _settings_backend_default), },
            {'args':['--backend-clientprinting'], 'default': _default_options['backend_clientprinting'], 'metavar': '<CLIENTPRINTING_BACKEND>', 'choices': _config_backends, 'help': 'use given backend for accessing the client printing configuration, available backends on your system: %s (default: %s)' % (', '.join(_config_backends), _printing_backend_default), },
        ]

        if X2GOCLIENT_OS == 'Windows':
            contrib_options = [
                {'args':['--start-xserver'], 'default': _default_options['start_xserver'], 'action': 'store_true', 'help': 'start the XServer before starting the session manager application, detect best XServer automatically, if more than one XServer is installed on your system', },
                {'args':['-X', '--preferred-xserver'], 'default': _default_options['preferred_xserver'], 'metavar': '<XSERVER>', 'choices': _known_xservers, 'help': 'start either of the currently supported XServers: %s -- make sure your preferred XServer is installed on your system' % _known_xservers, },
                {'args':['--start-pulseaudio'], 'default': _default_options['start_pulseaudio'], 'action': 'store_true', 'help': 'start the PulseAudio server before starting the session manager application', },
            ]

        portable_options = [
            {'args':['--client-rootdir'], 'default': _default_options['client_rootdir'], 'metavar': '</path/to/.x2goclient/dir>', 'help': 'define an alternative location where to find plain text config files (default: <HOME>/.x2goclient). This option will set ,,--backend-profiles FILE\'\', ,,--backend-clientsettings FILE\'\' and ,,--backend-clientprinting FILE\'\'', },
            {'args':['--sessions-rootdir'], 'default': _default_options['sessions_rootdir'], 'metavar': '</path/to/.x2go/dir>', 'help': 'define an alternative location for session runtime files'},
            {'args':['--ssh-rootdir'], 'default': _default_options['ssh_rootdir'], 'metavar': '</path/to/.ssh/dir>', 'help': 'define an alternative location for SSH files', },
        ]

        p = argparse.ArgumentParser(description='Graphical X2Go client implemented in (wx)Python.',\
                                    formatter_class=argparse.RawDescriptionHelpFormatter, \
                                    add_help=True, argument_default=None)
        p_debugopts = p.add_argument_group('Debug options')
        p_guiopts = p.add_argument_group('{progname} options'.format(progname=self.PROG_NAME))
        p_brokeropts = p.add_argument_group('Brokerage options')
        p_portableopts = p.add_argument_group('Portable application support')
        p_backendopts = p.add_argument_group('Python X2Go backend options (for experts only)')

        if X2GOCLIENT_OS == 'Windows':
            p_contribopts = p.add_argument_group('XServer options (MS Windows only)')
            p_portableopts = p.add_argument_group('File locations for portable setups (MS Windows only)')
            _option_groups = ((p_guiopts, x2go_gui_options), (p_brokeropts, broker_options), (p_debugopts, debug_options), (p_contribopts, contrib_options), (p_portableopts, portable_options), (p_backendopts, backend_options), )
        else:
            _option_groups = ((p_guiopts, x2go_gui_options), (p_brokeropts, broker_options), (p_debugopts, debug_options),  (p_portableopts, portable_options), (p_backendopts, backend_options), )
        for (p_group, opts) in _option_groups:
            for opt in opts:

                args = opt['args']
                del opt['args']
                p_group.add_argument(*args, **opt)

        a = p.parse_args()

        logger = X2GoLogger(tag=self.PROG_NAME)
        liblogger = X2GoLogger()

        if a.debug:
            logger.set_loglevel_debug()

        if a.libdebug:
            liblogger.set_loglevel_debug()

        if a.quiet:
            logger.set_loglevel_quiet()
            liblogger.set_loglevel_quiet()

        if a.libdebug_sftpxfer:
            liblogger.enable_debug_sftpxfer()

        if a.version:
            self.version()

        if a.single_session_profile and a.session_profile is None:
            self.runtime_error('The --single-session-profile option requires naming of a specific session profile!', parser=p)

        if a.non_interactive:
            if a.session_profile is None:
                self.runtime_error('In non-interactive mode you have to use the --session-profile option (or -P) to specify a certain session profile name!', parser=p)
            a.restricted_trayicon = True
            a.auto_connect = True
            a.start_on_connect = True
            a.resume_all_on_connect = True
            a.exit_on_disconnect = True
            a.disconnect_on_suspend = True
            a.disconnect_on_terminate = True
            a.single_session_profile = True

        if a.non_interactive and (a.resume_newest_on_connect or a.resume_oldest_on_connect):
            # allow override...
            a.resume_all_on_connect = False

        if X2GOCLIENT_OS == 'Windows' and a.preferred_xserver:
            if a.preferred_xserver not in _installed_xservers:
                self.runtime_error('Xserver ,,%s\'\' is not installed on your Windows system' % a.preferred_xserver, parser=p)
            a.start_xserver = a.preferred_xserver

        if X2GOCLIENT_OS == 'Windows' and a.start_xserver and a.display:
            self.runtime_error('You can tell %s to handle XServer startup and then specify a DISPLAY environment variable!'.format(progname=self.PROG_NAME), parser=p)

        if a.display:
            os.environ.update({'DISPLAY': a.display})
        else:
            if X2GOCLIENT_OS == 'Windows' and not a.start_xserver:
                os.environ.update({'DISPLAY': 'localhost:0'})

        if a.client_rootdir:
            a.client_rootdir = os.path.expanduser(a.client_rootdir)

        if a.sessions_rootdir:
            a.sessions_rootdir = os.path.expanduser(a.sessions_rootdir)

        if a.ssh_rootdir:
            a.ssh_rootdir = os.path.expanduser(a.ssh_rootdir)

        if a.client_rootdir:
            a.backend_sessionprofiles='FILE'
            a.backend_clientsettings='FILE'
            a.backend_clientprinting='FILE'

        return a, logger, liblogger


    def checkNewVersion(self):
        #Apprime Check
        response = None
        updateRequired = "0"
        try:
            response = urllib2.urlopen("http://ldap.ap.appocloud.com/updates/version.php?prgname=%s&version=%s" % (self.PROG_NAME, self.VERSION), timeout=3 )
            if(response.getcode() != 200):
                sys.stdout.write('====>>>>>VG: Version check failed. Response code = %d\n' % response.getcode() )
                return 0
            updateRequired = response.read().strip();
            sys.stdout.write('====>>>>>VG: Updater gave %s\n' % updateRequired)
        except Exception as ex:
            sys.stdout.write('====>>>>>VG: Unable to do version check %s\n' % ex.message)
            return 0
        if(updateRequired != '0'):
            sys.stdout.write('====>>>>>VG: New version found. Update\n')
        return updateRequired
    
    def update2latest(self, newversion):
        sys.stdout.write('====>>>>VG: Updating to new version\n')
        updatedirname = ""
        try:
            downloadpath = os.path.abspath(os.path.curdir) + "/updates"
            shutil.rmtree(downloadpath, ignore_errors=True) #remove any previous updates
            os.mkdir(downloadpath)
            outputFilename = downloadpath + "/" + newversion + ".zip";
            updatefile = "http://ldap.ap.appocloud.com/updates/" + newversion + ".upd"
            response = urllib2.urlopen(updatefile)
            zippedData = response.read()
            output = open(outputFilename,'wb')
            output.write(zippedData)
            output.close()
            with zipfile.ZipFile(outputFilename, "r") as z:
                z.extractall(downloadpath)
            updatedirname = downloadpath + "/" + newversion
            #execute the update
            #updatecmd = "index.bat " + "\""+updatedirname + "\" \"" + os.path.abspath(os.path.curdir) + "\""
            updatecmd = "index.bat"
            sys.stdout.write('====>>>>VG: updatecmd = %s\n' % updatecmd)
            p = Popen(updatecmd, cwd=updatedirname)
            sout, serr = p.communicate()
            sys.stdout.write('====>>>>VG: update process return flag is %d\n' % p.returncode)
            if p.returncode == 0:
                #update successful. restart the process
                python = sys.executable
                os.execl(python, python, * sys.argv)
        
        except Exception as ex:
            sys.stdout.write('====>>>>>VG: Unable to do version check %s\n' % ex.message)
            return
            
    
    def main(self, args, logger=None, liblogger=None):
        if X2GOCLIENT_OS == 'Windows':
            if args.lang:
                lang = gettext.translation('PyHoca-GUI', localedir=basepath.locale_basepath, languages=[args.lang], )
            else:
                lang = gettext.translation('PyHoca-GUI', localedir=basepath.locale_basepath, languages=['en'], )
            lang.install(unicode=True)
        else:
            gettext.install('PyHoca-GUI', localedir=basepath.locale_basepath, unicode=True)

        if self.check_running():
            sys.stderr.write("\n###############################\n### %s: already running for user %s\n###############################\n" % (self.PROG_NAME, CURRENT_LOCAL_USER))
            _dummy_app.appname = self.PROG_NAME
            m = PyHoca_MessageWindow_Ok(_dummy_app, shortmsg='ALREADY_RUNNING', title=u'%s (%s)...' % (self.PROG_NAME, self.VERSION), icon='{progname}_trayicon'.format(progname=self.PROG_NAME))
            m.ShowModal()
            self.version()

        thisPyHocaGUI = None
        try:
            #Apprime - check new version availability and upgrade
            newver = self.checkNewVersion()
            sys.stdout.write('====>>>>>VG: basepath = %s \n' % os.path.abspath(os.path.curdir))
            if (newver != '0'):
                self.update2latest(newver)
            #Apprime code end
            thisPyHocaGUI = PyHocaGUI(args, logger, liblogger, appname=self.PROG_NAME, version=self.VERSION)
            thisPyHocaGUI.MainLoop()
        except KeyboardInterrupt:
            if thisPyHocaGUI is not None:
                thisPyHocaGUI.WakeUpIdle()
                thisPyHocaGUI.ExitMainLoop()
        except SystemExit:
            if thisPyHocaGUI is not None:
                thisPyHocaGUI.WakeUpIdle()
                thisPyHocaGUI.ExitMainLoop()

        self.remove_pidfile()
