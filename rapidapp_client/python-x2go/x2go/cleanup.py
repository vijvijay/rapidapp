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
A recommended X2Go session clean up helper function.

"""

import gevent
import paramiko
import threading

# Python X2Go modules
import guardian
import rforward
from defaults import X2GOCLIENT_OS as _X2GOCLIENT_OS

if _X2GOCLIENT_OS == 'Windows':
    import xserver
    import pulseaudio

def x2go_cleanup(e=None, threads=None):
    """\
    For every Python X2Go application you write, please make sure to 
    capture the C{KeyboardInterrupt} and the C{SystemExit} exceptions and 
    call this function if either of the exceptions occurs.

    Example::

        import x2go

        try:
            my_x2goclient = x2go.X2GoClient(...)

            [... your code ...]

            sys.exit(0)
        except (KeyboardInterrupt, SystemExit):
            x2go.x2go_cleanup()

    @param e: if L{x2go_cleanup} got called as you caught an exception in your code this can be the 
        C{Exception} that we will process at the end of the clean-up (or if clean-up failed or was not 
        appropriate)
    @type e: C{exception}
    @param threads: a list of threads to clean up
    @type threads: C{list}

    """
    try:
        if threads is None:
            threads = threading.enumerate()
        else:
            threads = threads

        # stop X2Go reverse forwarding tunnels
        for t in threads:
            if type(t) == rforward.X2GoRevFwTunnel:
                t.stop_thread()
                del t

        # stop X2Go paramiko transports used by X2GoTerminalSession objects
        for t in threads:
            if type(t) == paramiko.Transport:
                if hasattr(t, '_x2go_session_marker'):
                    t.stop_thread()
                    del t

        # on Windows: stop the XServer that we evoked
        if _X2GOCLIENT_OS == 'Windows':
            for t in threads:
                if type(t) == xserver.X2GoXServer:
                    t.stop_thread()
                    del t

        # on Windows: stop the PulseAudio daemon that we evoked
        if _X2GOCLIENT_OS == 'Windows':
            for t in threads:
                if type(t) == pulseaudio.X2GoPulseAudio:
                    t.stop_thread()
                    del t

        for t in threads:
            if type(t) == guardian.X2GoSessionGuardian:
                t.stop_thread()
                del t

        gevent.sleep(1)

        if e is not None:
            raise e

    except KeyboardInterrupt:
        # do not allow keyboard interrupts during Python X2Go cleanup
        pass
    except SystemExit:
        # neither do we allow SIGTERM signals during cleanup...
        pass
