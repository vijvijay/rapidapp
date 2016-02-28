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
# Other contributors:
#       none so far

"""\
X2GoPulseAudio class - a Pulseaudio daemon guardian thread.

"""

__NAME__ = 'x2gopulseaudio-pylib'

from defaults import X2GOCLIENT_OS as _X2GOCLIENT_OS
if _X2GOCLIENT_OS == 'Windows':
    import win32process
    import win32con
    import win32event

# modules
import os
import sys
import threading
import gevent
import copy
import socket

from defaults import LOCAL_HOME as _LOCAL_HOME

# Python X2Go modules
import log

import exceptions
class OSNotSupportedException(exceptions.StandardError): pass
""" Exception denoting that this operating system is not supported. """

class X2GoPulseAudio(threading.Thread):
    """
    This class controls the Pulse Audio daemon.
    """

    def __init__(self, path=None, client_instance=None, logger=None, loglevel=log.loglevel_DEFAULT):
        """\
        Initialize a Pulse Audio daemon instance.

        @param path: full path to pulseaudio.exe
        @type path: C{str}
        @param client_instance: the calling L{X2GoClient} instance
        @type client_instance: L{X2GoClient} instance
        @param logger: you can pass an L{X2GoLogger} object to the L{X2GoClientXConfig} constructor
        @type logger: C{obj}
        @param loglevel: if no L{X2GoLogger} object has been supplied a new one will be
            constructed with the given loglevel
        @type loglevel: C{int}

        @raise OSNotSupportedException: on non-Windows platforms Python X2Go presumes that pulseaudio is already launched

        """
        if _X2GOCLIENT_OS not in ("Windows"):
            raise OSNotSupportedException('classes of x2go.pulseaudio module are for Windows only')

        if logger is None:
            self.logger = log.X2GoLogger(loglevel=loglevel)
        else:
            self.logger = copy.deepcopy(logger)
        self.logger.tag = __NAME__

        self.path = path
        self.client_instance = client_instance
        self._keepalive = None

        threading.Thread.__init__(self)
        self.daemon = True
        self.start()

    def run(self):
        """\
        This method is called once the C{X2GoPulseAudio.start()} method has been called. To tear 
        down the Pulseaudio daemon call the L{X2GoPulseAudio.stop_thread()} method.

        """
        self._keepalive = True
        cmd = 'pulseaudio.exe'
        cmd_options = [
            '-n',
            '--exit-idle-time=-1',
            '-L "module-native-protocol-tcp port=4713 auth-cookie=\\\\.pulse-cookie"',
            '-L "module-esound-protocol-tcp port=16001"',
            '-L module-waveout',
        ]

        # Fix for python-x2go bug #537.
        # Works Around PulseAudio bug #80772.
        # Tested with PulseAudio 5.0.
        # This argument will not cause PulseAudio 1.1 to fail to launch.
        # However, PulseAudio 1.1 ignores it for some reason.
        # So yes, the fact that 1.1 ignores it would be a bug in python-x2go if
        # we ever ship 1.1 again.
        #
        # wv.major == 5 matches 2000, XP, and Server 2003 (R2).
        # (Not that we support 2000.)
        wv = sys.getwindowsversion()
        if (wv.major==5):
            self.logger('Windows XP or Server 2003 (R2) detected.', loglevel=log.loglevel_DEBUG)
            self.logger('Setting PulseAudio to "Normal" CPU priority.', loglevel=log.loglevel_DEBUG)
            cmd_options.insert(0,"--high-priority=no")

        cmd_options = " %s" % " ".join(cmd_options)

        if not os.path.isdir(os.path.join(_LOCAL_HOME, '.pulse', '%s-runtime' % socket.gethostname())):
            os.makedirs(os.path.join(_LOCAL_HOME, '.pulse', '%s-runtime' % socket.gethostname()))
        self.logger('starting PulseAudio server with command line: %s%s' % (cmd, cmd_options), loglevel=log.loglevel_DEBUG)

        si = win32process.STARTUPINFO()
        p_info = win32process.CreateProcess(None,
                                            '%s\\%s %s' % (self.path, cmd, cmd_options),
                                            None,
                                            None,
                                            0,
                                            win32con.CREATE_NO_WINDOW|win32process.NORMAL_PRIORITY_CLASS,
                                            None,
                                            None,
                                            si,
                                           )
        (hProcess, hThread, processId, threadId) = p_info

        gevent.sleep(5)
        rc = win32event.WaitForMultipleObjects([hProcess],
                                               1,
                                               1, # wait just one millisec
                                              )
        _is_alive = ( rc != win32event.WAIT_OBJECT_0 )
        if self.client_instance and not _is_alive:
            if os.environ.has_key('CLIENTNAME'):
                self.client_instance.HOOK_pulseaudio_not_supported_in_RDPsession()
            else:
                self.client_instance.HOOK_pulseaudio_server_startup_failed()

        while self._keepalive and _is_alive:
            gevent.sleep(1)
            rc = win32event.WaitForMultipleObjects([hProcess],
                                               1,
                                               1, # wait just one millisec
                                              )
            _is_alive = ( rc != win32event.WAIT_OBJECT_0 )
            if self.client_instance and not _is_alive:
                self.client_instance.HOOK_pulseaudio_server_died()

        self.logger('terminating running PulseAudio server', loglevel=log.loglevel_DEBUG)

        # there is no real kill command on Windows...
        self.logger('PulseAudio process ID to terminate: %s' % processId, loglevel=log.loglevel_DEBUG)
        try:
            win32process.TerminateProcess(hProcess, 0)
        except win32process.error:
            pass

    def stop_thread(self):
        """\
        Tear down a running Pulseaudio daemon.

        """
        self.logger('stop_thread() method has been called', loglevel=log.loglevel_DEBUG)
        self._keepalive = False

