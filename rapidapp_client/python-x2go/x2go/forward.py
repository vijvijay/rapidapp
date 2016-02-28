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
Python Gevent based port forwarding server (openssh -L option) for the
proxying of graphical X2Go elements.

"""
__NAME__ = "x2gofwtunnel-pylib"

# modules
import copy

# gevent/greenlet
import gevent
from gevent import select, socket
from gevent.server import StreamServer

# Python X2Go modules
import log
from defaults import X2GOCLIENT_OS as _X2GOCLIENT_OS

class X2GoFwServer(StreamServer):
    """\
    L{X2GoFwServer} implements a gevent's StreamServer based Paramiko/SSH port
    forwarding server.

    An L{X2GoFwServer} class object is used to tunnel graphical trafic
    through an external proxy command launched by a C{X2GoProxy*} backend.

    """
    def __init__ (self, listener,
                  remote_host, remote_port,
                  ssh_transport, session_instance=None, session_name=None,
                  subsystem=None, logger=None, loglevel=log.loglevel_DEFAULT,):
        """\
        @param listener: listen on TCP/IP socket C{(<IP>, <Port>)}
        @type listener: C{tuple}
        @param remote_host: hostname or IP of remote host (in case of X2Go mostly 127.0.0.1)
        @type remote_host: C{str}
        @param remote_port: port of remote host
        @type remote_port: C{int}
        @param ssh_transport: a valid Paramiko/SSH transport object
        @type ssh_transport: C{obj}
        @param session_instance: the complete L{X2GoSession} instance of the X2Go session this port forwarding server belongs to.
            Note: for new L{X2GoSession} instances the object has the session name not yet set(!!!)
        @type session_instance: C{obj}
        @param session_name: the session name of the X2Go session this port forwarding server belongs to
        @type session_name: C{str}
        @param logger: you can pass an L{X2GoLogger} object to the
            L{X2GoFwServer} constructor
        @type logger: C{obj}
        @param loglevel: if no L{X2GoLogger} object has been supplied a new one will be
            constructed with the given loglevel
        @type loglevel: C{int}

        """
        if logger is None:
            self.logger = log.X2GoLogger(loglevel=loglevel)
        else:
            self.logger = copy.deepcopy(logger)
        self.logger.tag = __NAME__

        self.chan = None
        self.is_active = False
        self.failed = False
        self.keepalive = None
        self.listener = listener
        self.chain_host = remote_host
        self.chain_port = remote_port
        self.ssh_transport = ssh_transport
        self.session_name = session_name
        self.session_instance = session_instance
        self.subsystem = subsystem

        self.fw_socket = None

        StreamServer.__init__(self, self.listener, self.x2go_forward_tunnel_handle)

    def start(self):
        self.keepalive = True
        return StreamServer.start(self)

    def x2go_forward_tunnel_handle(self, fw_socket, address):
        """\
        Handle for SSH/Paramiko forwarding tunnel.

        @param fw_socket: local end of the forwarding tunnel
        @type fw_socket: C{obj}
        @param address: unused/ignored
        @type address: C{tuple}

        """
        self.fw_socket = fw_socket

        # disable Nagle algorithm in TCP/IP protocol
        self.fw_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

        _success = False
        _count = 0
        _maxwait = 20

        while not _success and _count < _maxwait and self.keepalive:

            _count += 1
            try:
                self.chan = self.ssh_transport.open_channel('direct-tcpip',
                                                            (self.chain_host, self.chain_port),
                                                            self.fw_socket.getpeername())
                chan_peername = self.chan.getpeername()
                _success = True
            except Exception, e:
                if self.keepalive:
                    self.logger('incoming request to %s:%d failed on attempt %d of %d: %s' % (self.chain_host,
                                                                                              self.chain_port,
                                                                                              _count,
                                                                                              _maxwait,
                                                                                              repr(e)),
                                                                                              loglevel=log.loglevel_WARN)
                gevent.sleep(.4)

        if not _success:
            if self.keepalive:
                self.logger('incoming request to %s:%d failed after %d attempts' % (self.chain_host,
                                                                                    self.chain_port,
                                                                                    _count),
                                                                                    loglevel=log.loglevel_ERROR)
                if self.session_instance:
                    self.session_instance.set_session_name(self.session_name)
                    self.session_instance.HOOK_forwarding_tunnel_setup_failed(chain_host=self.chain_host, chain_port=self.chain_port, subsystem=self.subsystem)
            self.failed = True

        else:
            self.logger('connected!  Tunnel open %r -> %r (on master connection %r -> %r)' % (
                        self.listener, (self.chain_host, self.chain_port),
                        self.fw_socket.getpeername(), chan_peername),
                        loglevel=log.loglevel_INFO)
            # once we are here, we can presume the tunnel to be active...
            self.is_active = True

            try:
                while self.keepalive:
                    r, w, x = select.select([self.fw_socket, self.chan], [], [])
                    if fw_socket in r:
                        data = fw_socket.recv(1024)
                        if len(data) == 0:
                            break
                        self.chan.send(data)
                    if self.chan in r:
                        data = self.chan.recv(1024)
                        if len(data) == 0:
                            break
                        fw_socket.send(data)
                self.close_channel()
                self.close_socket()
            except socket.error:
                pass

            self.logger('Tunnel closed from %r' % (chan_peername,),
                        loglevel=log.loglevel_INFO)

    def close_channel(self):
        """\
        Close an open channel again.

        """
        #if self.chan is not None and _X2GOCLIENT_OS != "Windows":
        if self.chan is not None:
            try:
                if _X2GOCLIENT_OS != 'Windows':
                    self.chan.close()
                self.chan = None
            except EOFError:
                pass

    def close_socket(self):
        """\
        Close the forwarding tunnel's socket again.

        """
        _success = False
        _count = 0
        _maxwait = 20

        # try at least <_maxwait> times
        while not _success and _count < _maxwait:
            _count += 1
            try:
                self.close_channel()
                if self.fw_socket is not None:
                    self.fw_socket.close()
                _success = True
            except socket.error:
                gevent.sleep(.2)
                self.logger('could not close fw_tunnel socket, try again (%s of %s)' % (_count, _maxwait), loglevel=log.loglevel_WARN)

        if _count >= _maxwait:
            self.logger('forwarding tunnel to [%s]:%d could not be closed properly' % (self.chain_host, self.chain_port), loglevel=log.loglevel_WARN)

    def stop(self):
        """\
        Stop the forwarding tunnel.

        """
        self.is_active = False
        self.close_socket()
        StreamServer.stop(self)


def start_forward_tunnel(local_host='127.0.0.1', local_port=22022,
                         remote_host='127.0.0.1', remote_port=22,
                         ssh_transport=None, 
                         session_instance=None,
                         session_name=None,
                         subsystem=None,
                         logger=None, ):
    """\
    Setup up a Paramiko/SSH port forwarding tunnel (like openssh -L option).

    The tunnel is used to transport X2Go graphics data through a proxy application like nxproxy.

    @param local_host: local starting point of the forwarding tunnel
    @type local_host: C{int}
    @param local_port: listen port of the local starting point
    @type local_port: C{int}
    @param remote_host: from the endpoint of the tunnel, connect to host C{<remote_host>}...
    @type remote_host: C{str}
    @param remote_port: ... on port C{<remote_port>}
    @type remote_port: C{int}
    @param ssh_transport: the Paramiko/SSH transport (i.e. the X2Go session's Paramiko/SSH transport object)
    @type ssh_transport: C{obj}
    @param session_instance: the L{X2GoSession} instance that initiates this tunnel
    @type session_instance: C{obj}
    @param session_name: the session name of the X2Go session this port forwarding server belongs to
    @type session_name: C{str}
    @param subsystem: a custom string with a component name that tries to evoke a new tunnel setup
    @type subsystem: C{str}
    @param logger: an X2GoLogger object
    @type logger: C{obj}

    @return: returns an L{X2GoFwServer} instance
    @rtype: C{obj}

    """
    fw_server = X2GoFwServer(listener=(local_host, local_port),
                             remote_host=remote_host, remote_port=remote_port,
                             ssh_transport=ssh_transport,
                             session_instance=session_instance, session_name=session_name,
                             subsystem=subsystem,
                             logger=logger,
                            )
    try:
        fw_server.start()
    except socket.error:
        fw_server.failed = True
        fw_server.is_active = False

    return fw_server

def stop_forward_tunnel(fw_server):
    """\
    Tear down a given Paramiko/SSH port forwarding tunnel.

    @param fw_server: an L{X2GoFwServer} instance as returned by the L{start_forward_tunnel()} function
    @type fw_server: C{obj}

    """
    if fw_server is not None:
        fw_server.keepalive = False
        gevent.sleep(.5)
        fw_server.stop()


if __name__ == '__main__':
    pass
