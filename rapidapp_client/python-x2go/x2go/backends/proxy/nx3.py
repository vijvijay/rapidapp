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
X2GoProxy classes - proxying your connection through NX3 and others.

"""
__NAME__ = 'x2goproxynx3-pylib'

# modules
import os

# Python X2Go modules
import x2go.log as log
import x2go.backends.proxy.base as base

from x2go.defaults import X2GOCLIENT_OS as _X2GOCLIENT_OS

class X2GoProxy(base.X2GoProxy):
    """\
    This L{X2GoProxy} class is a NX version 3 based X2Go proxy connection class.

    It basically fills L{x2go.backends.proxy.base.X2GoProxy} variables with sensible content. Its
    methods mostly wrap around the corresponding methods of the parent class.

    """
    def __init__(self, *args, **kwargs):
        """\
        For available parameters refer to L{x2go.backends.proxy.base.X2GoProxy} class documentation.

        """
        base.X2GoProxy.__init__(self, *args, **kwargs)
        self.subsystem = 'NX Proxy'

        # setting some default environment variables, nxproxy paths etc.
        if _X2GOCLIENT_OS == "Windows":
            _nxproxy_paths = [
                os.path.join(os.environ["ProgramFiles"], os.path.normpath("PyHoca-GUI/nxproxy/nxproxy.exe")),
                os.path.join(os.environ["ProgramFiles"], os.path.normpath("x2goclient/nxproxy.exe")),
                os.path.join(os.environ["ProgramFiles"], os.path.normpath("NX Client for Windows/bin/nxproxy.exe")),
                os.path.normpath("../pyhoca-contrib/mswin/nxproxy-mswin/nxproxy-3.5.0.12/nxproxy.exe"),
            ]
            if os.environ.has_key('NXPROXY_BINARY'):
                _nxproxy_paths.insert(0, os.environ['NXPROXY_BINARY'])
            for _nxproxy_cmd in _nxproxy_paths:
                if os.path.exists(_nxproxy_cmd):
                    break
            self.PROXY_CMD = _nxproxy_cmd
        else:
            self.PROXY_CMD = "/usr/bin/nxproxy"
        self.PROXY_ENV.update({
            "NX_CLIENT": "/bin/true",
            "NX_ROOT": self.sessions_rootdir
        })
        self.PROXY_MODE = '-S'
        if _X2GOCLIENT_OS == "Windows":
            self.PROXY_OPTIONS = [
                "nx/nx" ,
                "retry=5",
                "composite=1",
                "connect=127.0.0.1",
                "clipboard=1",
                "cookie=%s" % self.session_info.cookie,
                "port=%s" % self.session_info.graphics_port,
                "errors=%s" % os.path.join(".", "..", "S-%s" % self.session_info.name, self.session_errors, ),
            ]
        else:
            self.PROXY_OPTIONS = [
                "nx/nx" ,
                "retry=5",
                "composite=1",
                "connect=127.0.0.1",
                "clipboard=1",
                "cookie=%s" % self.session_info.cookie,
                "port=%s" % self.session_info.graphics_port,
                "errors=%s" % os.path.join(self.session_info.local_container, self.session_errors, ),
            ]

        self.PROXY_DISPLAY = self.session_info.display

    def _update_local_proxy_socket(self, port):
        """\
        Update the local proxy socket on port changes due to already-bound-to local TCP/IP port sockets.

        @param port: new local TCP/IP socket port
        @type port: C{int}

        """

        for idx, a in enumerate(self.PROXY_OPTIONS):
            if a.startswith('port='):
                self.PROXY_OPTIONS[idx] = 'port=%s' % port

    def _generate_cmdline(self):
        """\
        Generate the NX proxy command line for execution.

        """
        if _X2GOCLIENT_OS == "Windows":
            _options_filename = os.path.join(self.session_info.local_container, 'options')
            options = open(_options_filename, 'w')
            options.write('%s:%s' % (','.join(self.PROXY_OPTIONS), self.PROXY_DISPLAY))
            options.close()
            self.PROXY_OPTIONS= [ 'nx/nx', 'options=%s' % os.path.join("\\", "..", "S-%s" % self.session_info.name, 'options'), ]

        cmd_line = [ self.PROXY_CMD, ]
        cmd_line.append(self.PROXY_MODE)
        _proxy_options = "%s:%s" % (",".join(self.PROXY_OPTIONS), self.PROXY_DISPLAY)
        cmd_line.append(_proxy_options)
        return cmd_line

    def process_proxy_options(self):
        base.X2GoProxy.process_proxy_options(self)

    def start_proxy(self):
        """\
        Start the thread runner and wait for the proxy to come up.

        @return: a subprocess instance that knows about the externally started proxy command.
        @rtype: C{obj}

        """
        self.logger('starting local NX3 proxy...', loglevel=log.loglevel_INFO)
        self.logger('NX3 Proxy mode is server, cookie=%s, host=127.0.0.1, port=%s.' % (self.session_info.cookie, self.session_info.graphics_port,), loglevel=log.loglevel_DEBUG)
        self.logger('NX3 proxy writes session log to %s.' % os.path.join(self.session_info.local_container, 'session.log'), loglevel=log.loglevel_DEBUG)

        p, p_ok = base.X2GoProxy.start_proxy(self)

        if self.ok():
            self.logger('NX3 proxy is up and running.', loglevel=log.loglevel_INFO)
        else:
            self.logger('Bringing up NX3 proxy failed.', loglevel=log.loglevel_ERROR)

        return p, self.ok()
