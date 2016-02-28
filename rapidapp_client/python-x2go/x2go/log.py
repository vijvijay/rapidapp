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
X2GoLogger class - flexible handling of log and debug output.

"""
__NAME__ = 'x2gologger-pylib'

# modules
import os
import sys
import types

loglevel_NONE = 0
loglevel_ERROR = 8
loglevel_WARN = 16
loglevel_NOTICE = 32
loglevel_INFO = 64
loglevel_DEBUG = 128
loglevel_DEBUG_SFTPXFER = 1024

loglevel_DEFAULT = loglevel_ERROR | loglevel_WARN | loglevel_NOTICE
"""\
Default loglevel of X2GoLogger objects is: NOTICE & WARN & ERROR
"""

# Python X2Go modules
import utils

class X2GoLogger(object):
    """\
    A simple logger class, that is used by all Python X2Go classes.

    """
    name = ''
    tag = ''
    progpid = -1
    level = -1
    destination = sys.stderr

    _loglevel_NAMES = {8: 'error', 
                   16: 'warn', 
                   32: 'notice', 
                   64: 'info', 
                   128: 'debug', 
                   1024: 'debug-sftpxfer', 
                  }

    def __init__(self, name=sys.argv[0], loglevel=loglevel_DEFAULT, tag=None):
        """\
        @param name: name of the programme that uses Python X2Go
        @type name: C{str}
        @param loglevel: log level for Python X2Go
        @type loglevel: C{int}
        @param tag: additional tag for all log entries
        @type tag: C{str}

        """
        self.name = os.path.basename(name)
        self.tag = tag
        self.loglevel = loglevel
        self.progpid = os.getpid()

    def message(self, msg, loglevel=loglevel_NONE, tag=None):
        """\
        Log a message.

        @param msg: log message text
        @type msg: C{str}
        @param loglevel: log level of this message
        @type loglevel: C{int}
        @param tag: additional tag for this log entry
        @type tag: C{str}

        """
        if tag is None:
            tag = self.tag
        if loglevel & self.loglevel:

            msg = msg.replace('\n', ' ')
            msg = msg.encode(utils.get_encoding())
            from datetime import datetime
            minsec = datetime.now().strftime("%H:%M:%S.%f")
            if self.tag is not None:
                self.destination.write('%s: %s[%s] (%s) %s: %s\n' % (minsec, self.name, self.progpid, tag, self._loglevel_NAMES[loglevel].upper(), msg))
            else:
                self.destination.write('%s: %s[%s] %s: %s\n' % (minsec, self.name, self.progpid, self._loglevel_NAMES[loglevel].upper(), msg))
    __call__ = message

    def get_loglevel(self):
        """\
        Get the current loglevel.

        @return: current log level
        @rtype: C{int}

        """
        return self.loglevel

    def set_loglevel(self, loglevel_name='none'):
        """\
        Set log level by name.

        @param loglevel_name: name of loglevel to be set
        @type loglevel_name: C{str}

        """
        if type(loglevel_name) is types.IntegerType:
            self.loglevel = loglevel_name
        elif type(loglevel_name) is types.StringType and loglevel_name in self._loglevel_NAMES.values():
            _method = getattr(self, 'self.set_loglevel_%s' % loglevel_name)
            _method()
        else:
            self.loglevel = loglevel_DEFAULT

    def set_loglevel_quiet(self):
        """\
        Silence logging completely.

        """
        self.loglevel = 0

    def set_loglevel_error(self):
        """\
        Set log level to I{ERROR}.

        """
        self.loglevel = loglevel_ERROR

    def set_loglevel_warn(self):
        """\
        Set log level to I{WARN}.

        """
        self.loglevel = loglevel_ERROR | loglevel_WARN

    def set_loglevel_notice(self):
        """\
        Set log level to I{NOTICE} (default).

        """
        self.loglevel = loglevel_ERROR | loglevel_WARN | loglevel_NOTICE

    def set_loglevel_info(self):
        """\
        Set log level to I{INFO}.

        """
        self.loglevel = loglevel_ERROR | loglevel_WARN | loglevel_NOTICE | loglevel_INFO

    def set_loglevel_debug(self):
        """\
        Set log level to I{DEBUG}.

        """
        self.loglevel = loglevel_ERROR | loglevel_WARN | loglevel_NOTICE | loglevel_INFO | loglevel_DEBUG

    def enable_debug_sftpxfer(self):
        """\
        Additionally, switch on sFTP data transfer debugging

        """
        self.loglevel = self.loglevel | loglevel_DEBUG_SFTPXFER

    def disable_debug_sftpxfer(self):
        """\
        Switch off sFTP data transfer debugging.

        """
        self.loglevel = self.loglevel ^ loglevel_DEBUG_SFTPXFER

# compat section
X2goLogger = X2GoLogger

