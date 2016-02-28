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
#
# This code was initially written by:
#       2010 Dick Kniep <dick.kniep@lindix.nl>
#
# Other contributors:
#       none so far

__NAME__ = 'x2goxserver-pylib'

from defaults import X2GOCLIENT_OS as _X2GOCLIENT_OS
if _X2GOCLIENT_OS == 'Windows':
    import wmi
    import win32process

# modules
import os
import threading
import gevent
import copy

# Python X2Go modules
import log
from defaults import X2GO_XCONFIG_CONFIGFILES as _X2GO_XCONFIG_CONFIGFILES
from defaults import X2GO_CLIENTXCONFIG_DEFAULTS as _X2GO_CLIENTXCONFIG_DEFAULTS
import inifiles
import utils

class X2GoClientXConfig(inifiles.X2GoIniFile):
    """\
    Configuration file based XServer startup settings for X2GoClient instances.

    This class is needed for Windows systems and (maybe soon) for Unix desktops using Wayland.

    """

    def __init__(self, config_files=_X2GO_XCONFIG_CONFIGFILES, defaults=_X2GO_CLIENTXCONFIG_DEFAULTS, logger=None, loglevel=log.loglevel_DEFAULT):
        """\
        Constructs an L{X2GoClientXConfig} instance. This is normally done by an L{X2GoClient} instance.
        You can retrieve this L{X2GoClientXConfig} instance with the C{X2GoClient.get_client_xconfig()} 
        method.

        On construction the L{X2GoClientXConfig} instance is filled with values from the configuration files::

            /etc/x2goclient/xconfig
            ~/.x2goclient/xconfig

        The files are read in the specified order and config options of both files are merged. Options
        set in the user configuration file (C{~/.x2goclient/xconfig}) override global options set in
        C{/etc/x2goclient/xconfig}.

        @param config_files: a list of configuration file names
        @type config_files: C{list}
        @param defaults: a Python dictionary with configuration file defaults (use on your own risk)
        @type defaults: C{dict}
        @param logger: you can pass an L{X2GoLogger} object to the L{X2GoClientXConfig} constructor
        @type logger: C{obj}
        @param loglevel: if no L{X2GoLogger} object has been supplied a new one will be
            constructed with the given loglevel
        @type loglevel: C{int}

        """
        if _X2GOCLIENT_OS not in ("Windows"):
            import exceptions
            class OSNotSupportedException(exceptions.StandardError): pass
            raise OSNotSupportedException('classes of x2go.xserver module are for Windows only')

        inifiles.X2GoIniFile.__init__(self, config_files, defaults=defaults, logger=logger, loglevel=loglevel)

        _known_xservers = utils.merge_ordered_lists(self.defaultValues['XServers']['known_xservers'], self.known_xservers)

        if _known_xservers != self.known_xservers:
            self.update_value('XServers', 'known_xservers', _known_xservers)
            self.write_user_config = True
            self.write()

    def write(self):
        """\
        Store the Xserver configuration to the storage backend (i.e. on disk).

        For writing the first of the C{config_files} specified on instance construction
        that is writable will be used.

        @return: C{True} if the user config file has been successfully written, C{False} otherwise.
        @rtype: C{bool}

        """
        self._write_user_config = self.write_user_config
        return self._X2GoIniFile__write()

    def get_xserver_config(self, xserver_name):
        """\
        Retrieve the XServer configuration (from the xconfig file) for the given XServer application.

        @param xserver_name: name of the XServer application
        @type xserver_name: C{str}

        @return: A Python dictionary containing the XServer's configuration settings
        @rtype: C{list}

        """
        _xserver_config = {}
        for option in self.iniConfig.options(xserver_name):
            try:
                _xserver_config[option] = self.get(xserver_name, option, key_type=self.get_type(xserver_name, option))
            except KeyError:
                pass
        return _xserver_config

    @property
    def known_xservers(self):
        """\
        Renders a list of XServers that are known to Python X2Go.

        """
        return self.get_value('XServers', 'known_xservers')

    @property
    def installed_xservers(self):
        """\
        Among the known XServers renders a list of XServers that are actually
        installed on the system.

        """
        _installed = []
        for xserver_name in self.known_xservers:
            if os.path.exists(os.path.normpath(self.get_xserver_config(xserver_name)['test_installed'])):
                _installed.append(xserver_name)
        return _installed

    @property
    def running_xservers(self):
        """\
        Tries to render a list of running XServer processes from the system's process list.

        """
        _running = []
        _wmi = wmi.WMI()
        _my_wmi_sessionid = [ _p.SessionId for _p in _wmi.Win32_Process() if _p.ProcessId == os.getpid() ][0]

        _process_list = _wmi.Win32_Process()
        for xserver_name in self.installed_xservers:
            process_name = self.get_xserver_config(xserver_name)['process_name']
            if [ _p.Name for _p in _process_list if _p.Name == process_name and _p.SessionId == _my_wmi_sessionid ]:
                # XServer is already running
                _running.append(xserver_name)
                continue
        return _running

    @property
    def xserver_launch_possible(self):
        """\
        Detect if there is an XServer (that is known to Python X2Go) installed on the system.
        Equals C{True} if we have found an installed XServer that we can launch.

        """
        return bool(self.installed_xservers)

    @property
    def xserver_launch_needed(self):
        """\
        Detect if an XServer launch is really needed (or if we use an already running XServer instance).
        Equals C{True} if we have to launch an XServer before we can start/resume
        X2Go sessions.

        """
        return not bool(self.running_xservers)

    @property
    def preferred_xserver(self):
        """\
        Returns a tuple of (<xserver_name>, <xserver_config>).

        return: (<xserver_name>, <xserver_config>)
        rtype: C{tuple}

        """
        if self.xserver_launch_possible:
            return (self.installed_xservers[0], self.get_xserver_config(self.installed_xservers[0]))
        else:
            return None

    @property
    def preferred_xserver_names(self):
        """\
        Returns the list of preferred XServer names (most preferred first).

        """
        return self.installed_xservers

    def detect_unused_xdisplay_port(self, xserver_name):
        """\
        Get an unused TCP/IP port for the to-be-launched X server and write it
        to the user's X configuration file.

        @param xserver_name: name of the XServer application
        @type xserver_name: C{str}

        """
        _default_display = self.get_xserver_config(xserver_name)['display']
        _last_display = self.get_xserver_config(xserver_name)['last_display']

        try:
            _default_xserver_port = int(_default_display.split(":")[1].split(".")[0]) + 6000
            _last_xserver_port = int(_last_display.split(":")[1].split(".")[0]) + 6000

            # try the last used $DISPLAY first...
            if utils.detect_unused_port(preferred_port=_last_xserver_port) == _last_xserver_port:
                _detect_xserver_port = _last_xserver_port

            # then try the default $DISPLAY...
            elif utils.detect_unused_port(preferred_port=_default_xserver_port) == _default_xserver_port:
                _detect_xserver_port = _default_xserver_port

            # otherwise use a detection algorithm to find a free TCP/IP port
            else:
                _xserver_port = _default_xserver_port +1
                self.logger('Attempting to detect an unused TCP/IP port for our X-Server, starting with port %s' % _xserver_port, loglevel=log.loglevel_DEBUG)
                while utils.detect_unused_port(preferred_port=_xserver_port) != _xserver_port:
                    _xserver_port += 1
                    self.logger('TCP/IP port was in use, trying next port: %s' % _xserver_port, loglevel=log.loglevel_DEBUG)
                self.logger('allocating TCP/IP port %s for our X-Server' % _xserver_port, loglevel=log.loglevel_DEBUG)
                _detect_xserver_port = _xserver_port

            # if the port changed, let's write it to our configuration file
            if _detect_xserver_port != _last_xserver_port:
                _new_display = _last_display.replace(str(_last_xserver_port -6000), str(_detect_xserver_port -6000))
                self.logger('cannot use configured X DISPLAY, the new available DISPLAY port %s has been detected' % _new_display, loglevel=log.loglevel_NOTICE)
                self.update_value(xserver_name, 'last_display', _new_display)
                _parameters = self.get_value(xserver_name, 'parameters')
                _parameters[0] = ":%s" % (_detect_xserver_port -6000)
                self.update_value(xserver_name, 'parameters', tuple(_parameters))  
                self.write_user_config = True
                self.write()
                return _new_display

            return _last_display

        except TypeError:
            pass


class X2GoXServer(threading.Thread):
    """
    This class is responsible for starting/stopping an external XServer application.

    X2Go applications require a running XServer on the client system. This class will
    manage/handle the XServer while your X2Go application is running.

    """
    def __init__(self, xserver_name, xserver_config, logger=None, loglevel=log.loglevel_DEFAULT):
        """\
        Initialize an XServer thread.

        @param xserver_name: name of the XServer to start (refer to the xconfig file for available names)
        @type xserver_name: C{str}
        @param xserver_config: XServer configuration node (as derived from L{X2GoClientXConfig.get_xserver_config()}
        @type xserver_config: C{dict}
        @param logger: you can pass an L{X2GoLogger} object to the L{X2GoClientXConfig} constructor
        @type logger: C{obj}
        @param loglevel: if no L{X2GoLogger} object has been supplied a new one will be
            constructed with the given loglevel
        @type loglevel: C{int}

        """
        if _X2GOCLIENT_OS not in ("Windows"):
            import exceptions
            class OSNotSupportedException(exceptions.StandardError): pass
            raise OSNotSupportedException('classes of x2go.xserver module are for Windows only')

        if logger is None:
            self.logger = log.X2GoLogger(loglevel=loglevel)
        else:
            self.logger = copy.deepcopy(logger)
        self.logger.tag = __NAME__

        self._keepalive = None

        self.xserver_name = xserver_name
        self.xserver_config = xserver_config
        self.hProcess = None

        if self.xserver_config.has_key('last_display'):

            self.logger('setting DISPLAY environment variable to %s' % self.xserver_config['last_display'], loglevel=log.loglevel_NOTICE)
            os.environ.update({'DISPLAY': str(self.xserver_config['last_display'])})
        threading.Thread.__init__(self)
        self.daemon = True
        self.start()

    def __del__(self):
        """\
        Class destructor. Terminate XServer process.

        """
        self._terminate_xserver()

    def run(self):
        """\
        Start this L{X2GoXServer} thread. This will launch the configured XServer application.

        """
        self._keepalive = True
        cmd_line = [self.xserver_config['run_command']]
        cmd_line.extend(self.xserver_config['parameters'])
        self.logger('starting XServer ,,%s\'\' with command line: %s' % (self.xserver_name, ' '.join(cmd_line)), loglevel=log.loglevel_DEBUG)

        if _X2GOCLIENT_OS == 'Windows':
            si = win32process.STARTUPINFO()
            p_info = win32process.CreateProcess(None,
                                                ' '.join(cmd_line),
                                                None,
                                                None,
                                                0,
                                                win32process.NORMAL_PRIORITY_CLASS,
                                                None,
                                                None,
                                                si,
                                               )
            (self.hProcess, hThread, processId, threadId) = p_info

        while self._keepalive:
            gevent.sleep(1)

        self._terminate_xserver()

    def _terminate_xserver(self):
        """\
        Terminate the runnint XServer process.

        """
        self.logger('terminating running XServer ,,%s\'\'' % self.xserver_name, loglevel=log.loglevel_DEBUG)

        if _X2GOCLIENT_OS == 'Windows' and self.hProcess is not None:
            try:
                win32process.TerminateProcess(self.hProcess, 0)
            except win32process.error:
                self.logger('XServer ,,%s\'\' could not be terminated.' % self.xserver_name, loglevel=log.loglevel_DEBUG)

    def stop_thread(self):
        """\
        A call to this method will stop the XServer application and do a cleanup afterwards.

        """
        self._keepalive = False
        self.logger('stop_thread() method has been called', loglevel=log.loglevel_DEBUG)

