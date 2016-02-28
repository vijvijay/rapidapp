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
X2Go reverse SSH/Paramiko tunneling provides X2Go sound, X2Go printing and
X2Go sshfs for folder sharing and mounting remote devices in X2Go terminal
server sessions.

"""
__NAME__ = 'x2gorevtunnel-pylib'

# modules
import copy
import threading
import gevent
import paramiko

# gevent/greenlet
from gevent import select, socket, Timeout

# Python X2Go modules
import log


def x2go_transport_tcp_handler(chan, (origin_addr, origin_port), (server_addr, server_port)):
    """\
    An X2Go customized TCP handler for the Paramiko/SSH C{Transport()} class.

    Incoming channels will be put into Paramiko's default accept queue. This corresponds to 
    the default behaviour of Paramiko's C{Transport} class.

    However, additionally this handler function checks the server port of the incoming channel
    and detects if there are Paramiko/SSH reverse forwarding tunnels waiting for the incoming 
    channels. The Paramiko/SSH reverse forwarding tunnels are initiated by an L{X2GoSession} instance
    (currently supported: reverse tunneling auf audio data, reverse tunneling of SSH requests).

    If the server port of an incoming Paramiko/SSH channel matches the configured port of an L{X2GoRevFwTunnel} 
    instance, this instance gets notified of the incoming channel and a new L{X2GoRevFwChannelThread} is 
    started. This L{X2GoRevFwChannelThread} then takes care of the new channel's incoming data stream.

    """
    transport = chan.get_transport()
    transport._queue_incoming_channel(chan)
    rev_tuns = transport.reverse_tunnels

    for session_name in rev_tuns.keys():

        if int(server_port) in [ int(tunnel[0]) for tunnel in rev_tuns[session_name].values() ]:

            if rev_tuns[session_name]['snd'] is not None and int(server_port) == int(rev_tuns[session_name]['snd'][0]):
                rev_tuns[session_name]['snd'][1].notify()

            elif rev_tuns[session_name]['sshfs'] is not None and int(server_port) == int(rev_tuns[session_name]['sshfs'][0]):
                rev_tuns[session_name]['sshfs'][1].notify()


class X2GoRevFwTunnel(threading.Thread):
    """\
    L{X2GoRevFwTunnel} class objects are used to reversely tunnel 
    X2Go audio, X2Go printing and X2Go folder sharing / device mounting
    through Paramiko/SSH.

    """
    def __init__(self, server_port, remote_host, remote_port, ssh_transport, session_instance=None, logger=None, loglevel=log.loglevel_DEFAULT):
        """\
        Setup a reverse tunnel through Paramiko/SSH.

        After the reverse tunnel has been setup up with L{X2GoRevFwTunnel.start()} it waits
        for notification from L{X2GoRevFwTunnel.notify()} to accept incoming channels. This 
        notification (L{X2GoRevFwTunnel.notify()} gets called from within the transport's 
        TCP handler function L{x2go_transport_tcp_handler} of the L{X2GoSession} instance.

        @param server_port: the TCP/IP port on the X2Go server (starting point of the tunnel), 
            normally some number above 30000
        @type server_port: int
        @param remote_host: the target address for reversely tunneled traffic. With X2Go this should 
            always be set to the localhost (IPv4) address.
        @type remote_host: str
        @param remote_port: the TCP/IP port on the X2Go client (end point of the tunnel),
            normally an application's standard port (22 for SSH, 4713 for pulse audio, etc.)
        @type remote_port: int
        @param ssh_transport: the L{X2GoSession}'s Paramiko/SSH transport instance
        @type ssh_transport: C{paramiko.Transport} instance
        @param logger: you can pass an L{X2GoLogger} object to the
            L{X2GoRevFwTunnel} constructor
        @type logger: L{X2GoLogger} instance
        @param loglevel: if no L{X2GoLogger} object has been supplied a new one will be
            constructed with the given loglevel
        @type loglevel: int

        """
        if logger is None:
            self.logger = log.X2GoLogger(loglevel=loglevel)
        else:
            self.logger = copy.deepcopy(logger)
        self.logger.tag = __NAME__

        self.server_port = server_port
        self.remote_host = remote_host
        self.remote_port = remote_port
        self.ssh_transport = ssh_transport
        self.session_instance = session_instance

        self.open_channels = {}
        self.incoming_channel = threading.Condition()

        threading.Thread.__init__(self)
        self.daemon = True
        self._accept_channels = True

    def __del__(self):
        """\
        Class destructor.

        """
        self.stop_thread()
        self.cancel_port_forward('', self.server_port)

    def cancel_port_forward(self, address, port):
        """\
        Cancel a port forwarding request. This cancellation request is sent to the server and
        on the server the port forwarding should be unregistered.

        @param address: remote server address
        @type address: C{str}
        @param port: remote port
        @type port: C{int}

        """
        timeout = Timeout(10)
        timeout.start()
        try:
            self.ssh_transport.global_request('cancel-tcpip-forward', (address, port), wait=True)
        except:
            pass
        finally:
            timeout.cancel()

    def pause(self):
        """\
        Prevent acceptance of new incoming connections through the Paramiko/SSH
        reverse forwarding tunnel. Also, any active connection on this L{X2GoRevFwTunnel}
        instance will be closed immediately, if this method is called.

        """
        if self._accept_channels == True:
            self.cancel_port_forward('', self.server_port)
            self._accept_channels = False
            self.logger('paused thread: %s' % repr(self), loglevel=log.loglevel_DEBUG)

    def resume(self):
        """\
        Resume operation of the Paramiko/SSH reverse forwarding tunnel
        and continue accepting new incoming connections.

        """
        if self._accept_channels == False:
            self._accept_channels = True
            self._requested_port = self.ssh_transport.request_port_forward('127.0.0.1', self.server_port, handler=x2go_transport_tcp_handler)
            self.logger('resumed thread: %s' % repr(self), loglevel=log.loglevel_DEBUG)

    def notify(self):
        """\
        Notify an L{X2GoRevFwTunnel} instance of an incoming Paramiko/SSH channel.

        If an incoming reverse tunnel channel appropriate for this instance has
        been detected, this method gets called from the L{X2GoSession}'s transport
        TCP handler.

        The sent notification will trigger a C{thread.Condition()} waiting for notification
        in L{X2GoRevFwTunnel.run()}.

        """
        self.incoming_channel.acquire()
        self.logger('notifying thread of incoming channel: %s' % repr(self), loglevel=log.loglevel_DEBUG)
        self.incoming_channel.notify()
        self.incoming_channel.release()

    def stop_thread(self):
        """\
        Stops this L{X2GoRevFwTunnel} thread completely.

        """
        self.pause()
        self._keepalive = False
        self.logger('stopping thread: %s' % repr(self), loglevel=log.loglevel_DEBUG)
        self.notify()

    def _request_port_forwarding(self):
        try:
            self._requested_port = self.ssh_transport.request_port_forward('127.0.0.1', self.server_port, handler=x2go_transport_tcp_handler)
        except paramiko.SSHException:
            # if port forward request fails, we try to tell the server to cancel all foregoing port forward requests on 
            # self.server_port
            self.cancel_port_forward('', self.server_port)
            gevent.sleep(1)
            try:
                self._requested_port = self.ssh_transport.request_port_forward('127.0.0.1', self.server_port, handler=x2go_transport_tcp_handler)
            except paramiko.SSHException, e:
                if self.session_instance:
                    self.session_instance.HOOK_rforward_request_denied(server_port=self.server_port)
                else:
                    self.logger('Encountered SSHException: %s (for reverse TCP port forward with local destination port %s' % (str(e), self.server_port), loglevel=log.loglevel_WARN)

    def run(self):
        """\
        This method gets run once an L{X2GoRevFwTunnel} has been started with its
        L{start()} method. Use L{X2GoRevFwTunnel}.stop_thread() to stop the
        reverse forwarding tunnel again. You can also temporarily lock the tunnel
        down with L{X2GoRevFwTunnel.pause()} and L{X2GoRevFwTunnel.resume()}).

        L{X2GoRevFwTunnel.run()} waits for notifications of an appropriate incoming
        Paramiko/SSH channel (issued by L{X2GoRevFwTunnel.notify()}). Appropriate in
        this context means, that its start point on the X2Go server matches the class's
        property C{server_port}.

        Once a new incoming channel gets announced by the L{notify()} method, a new 
        L{X2GoRevFwChannelThread} instance will be initialized. As a data stream handler,
        the function L{x2go_rev_forward_channel_handler()} will be used.

        The channel will last till the connection gets dropped on the X2Go server side or 
        until the tunnel gets paused by an L{X2GoRevFwTunnel.pause()} call or stopped via the
        L{X2GoRevFwTunnel.stop_thread()} method.

        """
        self._request_port_forwarding()
        self._keepalive = True
        while self._keepalive:

            self.incoming_channel.acquire()

            self.logger('waiting for incoming data channel on X2Go server port: [127.0.0.1]:%s' % self.server_port, loglevel=log.loglevel_DEBUG)
            self.incoming_channel.wait()

            if self._keepalive:
                self.logger('detected incoming data channel on X2Go server port: [127.0.0.1]:%s' % self.server_port, loglevel=log.loglevel_DEBUG)
                _chan = self.ssh_transport.accept()
                self.logger('data channel %s for server port [127.0.0.1]:%s is up' % (_chan, self.server_port), loglevel=log.loglevel_DEBUG)
            else:
                self.logger('closing down rev forwarding tunnel on remote end [127.0.0.1]:%s' % self.server_port, loglevel=log.loglevel_DEBUG)

            self.incoming_channel.release()
            if self._accept_channels and self._keepalive:
                _new_chan_thread = X2GoRevFwChannelThread(_chan, (self.remote_host, self.remote_port), 
                                                          target=x2go_rev_forward_channel_handler, 
                                                          kwargs={ 
                                                            'chan': _chan,
                                                            'addr': self.remote_host,
                                                            'port': self.remote_port,
                                                            'parent_thread': self, 
                                                            'logger': self.logger, 
                                                          }
                                                  )
                _new_chan_thread.start()
                self.open_channels['[%s]:%s' % _chan.origin_addr] = _new_chan_thread


def x2go_rev_forward_channel_handler(chan=None, addr='', port=0, parent_thread=None, logger=None, ):
    """\
    Handle the data stream of a requested channel that got set up by a L{X2GoRevFwTunnel} (Paramiko/SSH 
    reverse forwarding tunnel).

    The channel (and the corresponding connections) close either ...

        - ... if the connecting application closes the connection and thus, drops 
        the channel, or
        - ... if the L{X2GoRevFwTunnel} parent thread gets paused. The call
        of L{X2GoRevFwTunnel.pause()} on the instance can be used to shut down all incoming 
        tunneled SSH connections associated to this L{X2GoRevFwTunnel} instance
        from within a Python X2Go application.

    @param chan: channel
    @type chan: C{class}
    @param addr: bind address
    @type addr: C{str}
    @param port: bind port
    @type port: C{int}
    @param parent_thread: the calling L{X2GoRevFwTunnel} instance
    @type parent_thread: L{X2GoRevFwTunnel} instance
    @param logger: you can pass an L{X2GoLogger} object to the
        L{X2GoRevFwTunnel} constructor
    @type logger: L{X2GoLogger} instance

    """
    fw_socket = socket.socket()
    fw_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    if logger is None:
        def _dummy_logger(msg, l):
            pass
        logger = _dummy_logger

    try:
        fw_socket.connect((addr, port))
    except Exception, e:
        logger('Reverse forwarding request to %s:%d failed: %r' % (addr, port, e), loglevel=log.loglevel_INFO)
        return

    logger('Connected! Reverse tunnel open %r -> %r -> %r' % (chan.origin_addr,
                                                              chan.getpeername(), (addr, port)), 
                                                              loglevel=log.loglevel_INFO)
    while parent_thread._accept_channels:
        r, w, x = select.select([fw_socket, chan], [], [])
        try:
            if fw_socket in r:
                data = fw_socket.recv(1024)
                if len(data) == 0:
                    break
                chan.send(data)
            if chan in r:
                data = chan.recv(1024)
                if len(data) == 0:
                    break
                fw_socket.send(data)
        except socket.error, e:
            logger('Reverse tunnel %s encoutered socket error: %s' % (chan, str(e)), loglevel=log.loglevel_WARN)

    chan.close()
    fw_socket.close()
    logger('Reverse tunnel %s closed from %r' % (chan, chan.origin_addr,), loglevel=log.loglevel_INFO)


class X2GoRevFwChannelThread(threading.Thread):
    """\
    Starts a thread for each incoming Paramiko/SSH data channel trough the reverse
    forwarding tunnel.

    """
    def __init__(self, channel, remote=None, **kwargs):
        """\
        Initializes a reverse forwarding channel thread.

        @param channel: incoming Paramiko/SSH channel from the L{X2GoSession}'s transport
            accept queue
        @type channel: class
        @param remote: tuple (addr, port) that specifies the data endpoint of the channel
        @type remote: C{tuple(str, int)}

        """
        self.channel = channel
        if remote is not None:
            self.remote_host = remote[0]
            self.remote_port = remote[1]
        threading.Thread.__init__(self, **kwargs)
        self.daemon = True
