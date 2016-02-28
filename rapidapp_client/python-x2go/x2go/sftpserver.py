# -*- coding: utf-8 -*-

# Copyright (C) 2010-2014 by Mike Gabriel <mike.gabriel@das-netzwerkteam.de>

# The Python X2Go sFTPServer code was originally written by Richard Murri, 
# for further information see his website: http://www.richardmurri.com

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
For sharing local folders via sFTP/sshfs Python X2Go implements its own sFTP 
server (as end point of reverse forwarding tunnel requests). Thus, Python X2Go
does not need a locally installed SSH daemon on the client side machine.

The Python X2Go sFTP server code was originally written by Richard Murri, 
for further information see his website: http://www.richardmurri.com

"""
__NAME__ = "x2gosftpserver-pylib"

import os
import shutil
import copy
import threading
import paramiko
import gevent

# Python X2Go modules
import rforward
import defaults
import log

class _SSHServer(paramiko.ServerInterface):
    """\
    Implementation of a basic SSH server that is supposed 
    to run with its sFTP server implementation.

    """
    def __init__(self, auth_key=None, session_instance=None, logger=None, loglevel=log.loglevel_DEFAULT, *args, **kwargs):
        """\
        Initialize a new sFTP server interface.

        @param auth_key: Server key that the client has to authenticate against
        @type auth_key: C{paramiko.RSAKey} instance
        @param session_instance: the calling L{X2GoSession} instance
        @type session_instance: L{X2GoSession} instance
        @param logger: you can pass an L{X2GoLogger} object to the L{X2GoClientXConfig} constructor
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

        self.current_local_user = defaults.CURRENT_LOCAL_USER
        self.auth_key = auth_key
        self.session_instance = session_instance
        paramiko.ServerInterface.__init__(self, *args, **kwargs)
        logger('initializing internal SSH server for handling incoming sFTP requests, allowing connections for user ,,%s\'\' only' % self.current_local_user, loglevel=log.loglevel_DEBUG)

    def check_channel_request(self, kind, chanid):
        """\
        Only allow session requests.

        @param kind: request type
        @type kind: C{str}
        @param chanid: channel id (unused)
        @type chanid: C{any}

        @return: returns a Paramiko/SSH return code
        @rtype: C{int}

        """
        self.logger('detected a channel request for sFTP', loglevel=log.loglevel_DEBUG_SFTPXFER)
        if kind == 'session':
            return paramiko.OPEN_SUCCEEDED
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_auth_publickey(self, username, key):
        """\
        Ensure proper authentication.

        @param username: username of incoming authentication request
        @type username: C{str}
        @param key: incoming SSH key to be used for authentication
        @type key: C{paramiko.RSAKey} instance

        @return: returns a Paramiko/SSH return code
        @rtype: C{int}

        """
        self.logger('sFTP server %s: username is %s' % (self, self.current_local_user), loglevel=log.loglevel_DEBUG)
        if username == self.current_local_user:
            if type(key) == paramiko.RSAKey and key == self.auth_key:
                self.logger('sFTP server %s: publickey auth (type: %s) has been successful' % (self, key.get_name()), loglevel=log.loglevel_INFO)
                return paramiko.AUTH_SUCCESSFUL
        self.logger('sFTP server %s: publickey (type: %s) auth failed' % (self, key.get_name()), loglevel=log.loglevel_WARN)
        return paramiko.AUTH_FAILED

    def get_allowed_auths(self, username):
        """\
        Only allow public key authentication.

        @param username: username of incoming authentication request
        @type username: C{str}

        @return: statically returns C{publickey} as auth mechanism
        @rtype: C{str}

        """
        self.logger('sFTP client asked for support auth methods, answering: publickey', loglevel=log.loglevel_DEBUG_SFTPXFER)
        return 'publickey'


class _SFTPHandle(paramiko.SFTPHandle):
    """\
    Represents a handle to an open file.

    """
    def stat(self):
        """\
        Create an SFTPAttributes object from an existing stat object (an object returned by os.stat).

        return: new C{SFTPAttributes} object with the same attribute fields.
        rtype: C{obj}

        """
        try:
            return paramiko.SFTPAttributes.from_stat(os.fstat(self.readfile.fileno()))
        except OSError, e:
            return paramiko.SFTPServer.convert_errno(e.errno)


class _SFTPServerInterface(paramiko.SFTPServerInterface):
    """\
    sFTP server implementation.

    """
    def __init__(self, server, chroot=None, logger=None, loglevel=log.loglevel_DEFAULT, server_event=None, *args, **kwargs):
        """\
        Make user information accessible as well as set chroot jail directory.

        @param server: a C{paramiko.ServerInterface} instance to use with this SFTP server interface
        @type server: C{paramiko.ServerInterface} instance
        @param chroot: chroot environment for this SFTP interface
        @type chroot: C{str}
        @param logger: you can pass an L{X2GoLogger} object to the L{X2GoClientXConfig} constructor
        @type logger: C{obj}
        @param loglevel: if no L{X2GoLogger} object has been supplied a new one will be
            constructed with the given loglevel
        @type loglevel: C{int}
        @param server_event: a C{threading.Event} instance that can signal SFTP session termination
        @type server_event: C{threading.Event} instance

        """
        if logger is None:
            self.logger = log.X2GoLogger(loglevel=loglevel)
        else:
            self.logger = copy.deepcopy(logger)
        self.logger.tag = __NAME__
        self.server_event = server_event

        self.logger('sFTP server: initializing new channel...', loglevel=log.loglevel_DEBUG)
        self.CHROOT = chroot or '/tmp'

    def _realpath(self, path):
        """\
        Enforce the chroot jail. On Windows systems the drive letter is incorporated in the
        chroot path name (/windrive/<drive_letter>/path/to/file/or/folder).

        @param path: path name within chroot
        @type path: C{str}

        @return: real path name (including drive letter on Windows systems)
        @rtype: C{str}

        """
        if defaults.X2GOCLIENT_OS == 'Windows' and path.startswith('/windrive'):
            _path_components = path.split('/')
            _drive = _path_components[2]
            _tail_components = (len(_path_components) > 3) and _path_components[3:] or ''
            _tail = os.path.normpath('/'.join(_tail_components))
            path = os.path.join('%s:' % _drive, '/', _tail)
        else:
            path = self.CHROOT + self.canonicalize(path)
            path = path.replace('//', '/')
        return path

    def list_folder(self, path):
        """\
        List the contents of a folder.

        @param path: path to folder
        @type path: C{str}

        @return: returns the folder contents, on failure returns a Paramiko/SSH return code
        @rtype: C{dict} or C{int}

        """
        path = self._realpath(path)
        self.logger('sFTP server: listing files in folder: %s' % path, loglevel=log.loglevel_DEBUG_SFTPXFER)

        try:
            out = []
            flist = os.listdir(path)
            for fname in flist:

                try:
                    attr = paramiko.SFTPAttributes.from_stat(os.lstat(os.path.join(path, fname)))
                    attr.filename = fname
                    self.logger('sFTP server %s: file attributes ok: %s' % (self, fname), loglevel=log.loglevel_DEBUG_SFTPXFER)
                    out.append(attr)
                except OSError, e:
                    self.logger('sFTP server %s: encountered error processing attributes of file %s: %s' % (self, fname, str(e)), loglevel=log.loglevel_DEBUG_SFTPXFER)

            self.logger('sFTP server: folder list is : %s' % str([ a.filename for a in out ]), loglevel=log.loglevel_DEBUG_SFTPXFER)
            return out
        except OSError, e:
            self.logger('sFTP server %s: encountered error: %s' % (self, str(e)), loglevel=log.loglevel_DEBUG_SFTPXFER)
            return paramiko.SFTPServer.convert_errno(e.errno)

    def stat(self, path):
        """\
        Stat on a file.

        @param path: path to file/folder
        @type path: C{str}

        @return: returns the file's stat output, on failure: returns a Paramiko/SSH return code
        @rtype: C{class} or C{int}

        """
        path = self._realpath(path)
        self.logger('sFTP server %s: calling stat on path: %s' % (self, path), loglevel=log.loglevel_DEBUG_SFTPXFER)
        try:
            return paramiko.SFTPAttributes.from_stat(os.stat(path))
        except OSError, e:
            self.logger('sFTP server %s: encountered error: %s' % (self, str(e)), loglevel=log.loglevel_DEBUG_SFTPXFER)
            return paramiko.SFTPServer.convert_errno(e.errno)

    def lstat(self, path):
        """\
        LStat on a file.

        @param path: path to folder
        @type path: C{str}

        @return: returns the file's lstat output, on failure: returns a Paramiko/SSH return code
        @rtype: C{class} or C{int}

        """
        path = self._realpath(path)
        self.logger('sFTP server: calling lstat on path: %s' % path, loglevel=log.loglevel_DEBUG_SFTPXFER)
        try:
            return paramiko.SFTPAttributes.from_stat(os.lstat(path))
        except OSError, e:
            self.logger('sFTP server %s: encountered error: %s' % (self, str(e)), loglevel=log.loglevel_DEBUG_SFTPXFER)
            return paramiko.SFTPServer.convert_errno(e.errno)

    def open(self, path, flags, attr):
        """\
        Open a file for reading, writing, appending etc.

        @param path: path to file
        @type path: C{str}
        @param flags: file flags
        @type flags: C{str}
        @param attr: file attributes
        @type attr: C{class}

        @return: file handle/object for remote file, on failure: returns a Paramiko/SSH return code
        @rtype: L{_SFTPHandle} instance or C{int}

        """
        path = self._realpath(path)
        self.logger('sFTP server %s: opening file: %s' % (self, path), loglevel=log.loglevel_DEBUG_SFTPXFER)
        try:
            binary_flag = getattr(os, 'O_BINARY',  0)
            flags |= binary_flag
            mode = getattr(attr, 'st_mode', None)
            if mode is not None:
                fd = os.open(path, flags, mode)
            else:
                # os.open() defaults to 0777 which is
                # an odd default mode for files
                fd = os.open(path, flags, 0666)
        except OSError, e:
            self.logger('sFTP server %s: encountered error: %s' % (self, str(e)), loglevel=log.loglevel_DEBUG_SFTPXFER)
            return paramiko.SFTPServer.convert_errno(e.errno)
        if (flags & os.O_CREAT) and (attr is not None):
            attr._flags &= ~attr.FLAG_PERMISSIONS
            paramiko.SFTPServer.set_file_attr(path, attr)
        if flags & os.O_WRONLY:
            if flags & os.O_APPEND:
                fstr = 'ab'
            else:
                fstr = 'wb'
        elif flags & os.O_RDWR:
            if flags & os.O_APPEND:
                fstr = 'a+b'
            else:
                fstr = 'r+b'
        else:
            # O_RDONLY (== 0)
            fstr = 'rb'
        try:
            f = os.fdopen(fd, fstr)
        except OSError, e:
            self.logger('sFTP server %s: encountered error: %s' % (self, str(e)), loglevel=log.loglevel_DEBUG_SFTPXFER)
            return paramiko.SFTPServer.convert_errno(e.errno)
        fobj = _SFTPHandle(flags)
        fobj.filename = path
        fobj.readfile = f
        fobj.writefile = f
        return fobj

    def remove(self, path):
        """\
        Remove a file.

        @param path: path to file
        @type path: C{str}

        @return: returns Paramiko/SSH return code
        @rtype: C{int}

        """
        path = self._realpath(path)
        os.remove(path)
        self.logger('sFTP server %s: removing file: %s' % (self, path), loglevel=log.loglevel_DEBUG_SFTPXFER)
        return paramiko.SFTP_OK

    def rename(self, oldpath, newpath):
        """\
        Rename/move a file.

        @param oldpath: old path/location/file name
        @type oldpath: C{str}
        @param newpath: new path/location/file name
        @type newpath: C{str}

        @return: returns Paramiko/SSH return code
        @rtype: C{int}

        """
        self.logger('sFTP server %s: renaming path from %s to %s' % (self, oldpath, newpath), loglevel=log.loglevel_DEBUG_SFTPXFER)
        oldpath = self._realpath(oldpath)
        newpath = self._realpath(newpath)
        try:
            shutil.move(oldpath, newpath)
        except OSError, e:
            self.logger('sFTP server %s: encountered error: %s' % (self, str(e)), loglevel=log.loglevel_DEBUG_SFTPXFER)
            return paramiko.SFTPServer.convert_errno(e.errno)
        return paramiko.SFTP_OK

    def mkdir(self, path, attr):
        """\
        Make a directory.

        @param path: path to new folder
        @type path: C{str}
        @param attr: file attributes
        @type attr: C{class}

        @return: returns Paramiko/SSH return code
        @rtype: C{int}

        """
        self.logger('sFTP server: creating new dir (perms: %s): %s' % (attr.st_mode, path), loglevel=log.loglevel_DEBUG_SFTPXFER)
        path = self._realpath(path)
        try:
            os.mkdir(path, attr.st_mode)
        except OSError, e:
            self.logger('sFTP server %s: encountered error: %s' % (self, str(e)), loglevel=log.loglevel_DEBUG_SFTPXFER)
            return paramiko.SFTPServer.convert_errno(e.errno)
        return paramiko.SFTP_OK

    def rmdir(self, path):
        """\
        Remove a directory (if needed recursively).

        @param path: folder to be removed
        @type path: C{str}

        @return: returns Paramiko/SSH return code
        @rtype: C{int}

        """
        self.logger('sFTP server %s: removing dir: %s' % (self, path), loglevel=log.loglevel_DEBUG_SFTPXFER)
        path = self._realpath(path)
        try:
            shutil.rmtree(path)
        except OSError, e:
            self.logger('sFTP server %s: encountered error: %s' % (self, str(e)), loglevel=log.loglevel_DEBUG_SFTPXFER)
            return paramiko.SFTPServer.convert_errno(e.errno)
        return paramiko.SFTP_OK

    def chattr(self, path, attr):
        """\
        Change file attributes.

        @param path: path of file/folder
        @type path: C{str}
        @param attr: new file attributes
        @type attr: C{class}

        @return: returns Paramiko/SSH return code
        @rtype: C{int}

        """
        self.logger('sFTP server %s: modifying attributes of path: %s' % (self, path), loglevel=log.loglevel_DEBUG_SFTPXFER)
        path = self._realpath(path)
        try:
            if attr.st_mode is not None:
                os.chmod(path, attr.st_mode)
            if attr.st_uid is not None:
                os.chown(path, attr.st_uid, attr.st_gid)
        except OSError, e:
            self.logger('sFTP server %s: encountered error: %s' % (self, str(e)), loglevel=log.loglevel_DEBUG_SFTPXFER)
            return paramiko.SFTPServer.convert_errno(e.errno)
        return paramiko.SFTP_OK

    def symlink(self, target_path, path):
        """\
        Create a symbolic link.

        @param target_path: link shall point to this path
        @type target_path: C{str}
        @param path: link location
        @type path: C{str}

        @return: returns Paramiko/SSH return code
        @rtype: C{int}

        """
        self.logger('sFTP server %s: creating symlink from: %s to target: %s' % (self, path, target_path), loglevel=log.loglevel_DEBUG_SFTPXFER)
        path = self._realpath(path)
        if target_path.startswith('/'):
            target_path = self._realpath(target_path)
        try:
            os.symlink(target_path, path)
        except OSError, e:
            self.logger('sFTP server %s: encountered error: %s' % (self, str(e)), loglevel=log.loglevel_DEBUG_SFTPXFER)
            return paramiko.SFTPServer.convert_errno(e.errno)
        return paramiko.SFTP_OK

    def readlink(self, path):
        """\
        Read the target of a symbolic link.

        @param path: path of symbolic link
        @type path: C{str}

        @return: target location of the symbolic link, on failure: returns a Paramiko/SSH return code
        @rtype: C{str} or C{int}

        """
        path = self._realpath(path)
        try:
            return os.readlink(path)
        except OSError, e:
            self.logger('sFTP server %s: encountered error: %s' % (self, str(e)), loglevel=log.loglevel_DEBUG_SFTPXFER)
            return paramiko.SFTPServer.convert_errno(e.errno)

    def session_ended(self):
        """\
        Tidy up when the sFTP session has ended.

        """
        if self.server_event is not None:
            self.logger('sFTP server %s: session has ended' % self, loglevel=log.loglevel_DEBUG_SFTPXFER)
            self.server_event.set()


class X2GoRevFwTunnelToSFTP(rforward.X2GoRevFwTunnel):
    """\
    A reverse fowarding tunnel with an sFTP server at its endpoint. This blend of a Paramiko/SSH
    reverse forwarding tunnel is used to provide access to local X2Go client folders
    from within the the remote X2Go server session.

    """
    def __init__(self, server_port, ssh_transport, auth_key=None, session_instance=None, logger=None, loglevel=log.loglevel_DEFAULT):
        """\
        Start a Paramiko/SSH reverse forwarding tunnel, that has an sFTP server listening at
        the endpoint of the tunnel.

        @param server_port: the TCP/IP port on the X2Go server (starting point of the tunnel), 
            normally some number above 30000
        @type server_port: C{int}
        @param ssh_transport: the L{X2GoSession}'s Paramiko/SSH transport instance
        @type ssh_transport: C{paramiko.Transport} instance
        @param auth_key: Paramiko/SSH RSAkey object that has to be authenticated against by
            the remote sFTP client
        @type auth_key: C{paramiko.RSAKey} instance
        @param logger: you can pass an L{X2GoLogger} object to the
            L{X2GoRevFwTunnelToSFTP} constructor
        @type logger: L{X2GoLogger} instance
        @param loglevel: if no L{X2GoLogger} object has been supplied a new one will be
            constructed with the given loglevel
        @type loglevel: C{int}

        """
        self.ready = False
        if logger is None:
            self.logger = log.X2GoLogger(loglevel=loglevel)
        else:
            self.logger = copy.deepcopy(logger)
        self.logger.tag = __NAME__

        self.server_port = server_port
        self.ssh_transport = ssh_transport
        self.session_instance = session_instance
        if type(auth_key) is not paramiko.RSAKey:
            auth_key = None
        self.auth_key = auth_key

        self.open_channels = {}
        self.incoming_channel = threading.Condition()

        threading.Thread.__init__(self)
        self.daemon = True
        self._accept_channels = True

    def run(self):
        """\
        This method gets run once an L{X2GoRevFwTunnelToSFTP} has been started with its
        L{start()} method. Use L{X2GoRevFwTunnelToSFTP}.stop_thread() to stop the
        reverse forwarding tunnel again (refer also to its pause() and resume() method).

        L{X2GoRevFwTunnelToSFTP.run()} waits for notifications of an appropriate incoming
        Paramiko/SSH channel (issued by L{X2GoRevFwTunnelToSFTP.notify()}). Appropriate in
        this context means, that its starting point on the X2Go server matches the class's
        property C{server_port}.

        Once a new incoming channel gets announced by the L{notify()} method, a new 
        L{X2GoRevFwSFTPChannelThread} instance will be initialized. As a data stream handler,
        the function L{x2go_rev_forward_sftpchannel_handler()} will be used.

        The channel will last till the connection gets dropped on the X2Go server side or 
        until the tunnel gets paused by an L{X2GoRevFwTunnelToSFTP.pause()} call or 
        stopped via the C{X2GoRevFwTunnelToSFTP.stop_thread()} method.

        """
        self._request_port_forwarding()
        self._keepalive = True
        self.ready = True
        while self._keepalive:

            self.incoming_channel.acquire()

            self.logger('waiting for incoming sFTP channel on X2Go server port: [localhost]:%s' % self.server_port, loglevel=log.loglevel_DEBUG)
            self.incoming_channel.wait()
            if self._keepalive:
                self.logger('Detected incoming sFTP channel on X2Go server port: [localhost]:%s' % self.server_port, loglevel=log.loglevel_DEBUG)
                _chan = self.ssh_transport.accept()
                self.logger('sFTP channel %s for server port [localhost]:%s is up' % (_chan, self.server_port), loglevel=log.loglevel_DEBUG)
            else:
                self.logger('closing down rev forwarding sFTP tunnel on remote end [localhost]:%s' % self.server_port, loglevel=log.loglevel_DEBUG)

            self.incoming_channel.release()
            if self._accept_channels and self._keepalive:
                _new_chan_thread = X2GoRevFwSFTPChannelThread(_chan,
                                                              target=x2go_rev_forward_sftpchannel_handler, 
                                                              kwargs={ 
                                                               'chan': _chan,
                                                               'auth_key': self.auth_key,
                                                               'logger': self.logger, 
                                                              }
                                                             )
                _new_chan_thread.start()
                self.open_channels['[%s]:%s' % _chan.origin_addr] = _new_chan_thread
        self.ready = False


def x2go_rev_forward_sftpchannel_handler(chan=None, auth_key=None, logger=None):
    """\
    Handle incoming sFTP channels that got setup by an L{X2GoRevFwTunnelToSFTP} instance.

    The channel (and the corresponding connections) close either ...

        - ... if the connecting application closes the connection and thus, drops 
        the sFTP channel, or
        - ... if the L{X2GoRevFwTunnelToSFTP} parent thread gets paused. The call
        of L{X2GoRevFwTunnelToSFTP.pause()} on the instance can be used to shut down all incoming 
        tunneled SSH connections associated to this L{X2GoRevFwTunnelToSFTP} instance
        from within a Python X2Go application.

    @param chan: an incoming sFTP channel
    @type chan: paramiko.Channel instance
    @param auth_key: Paramiko/SSH RSAkey object that has to be authenticated against by
        the remote sFTP client
    @type auth_key: C{paramiko.RSAKey} instance
    @param logger: you must pass an L{X2GoLogger} object to this handler method
    @type logger: C{X2GoLogger} instance

    """
    if logger is None:
        def _dummy_logger(msg, l):
            pass
        logger = _dummy_logger

    if auth_key is None:
        logger('sFTP channel %s closed because of missing authentication key' % chan, loglevel=log.loglevel_DEBUG)
        return

    # set up server
    t = paramiko.Transport(chan)
    t.daemon = True
    t.load_server_moduli()
    t.add_server_key(defaults.RSAHostKey)

    # set up sftp handler, server and event
    event = threading.Event()
    t.set_subsystem_handler('sftp', paramiko.SFTPServer, sftp_si=_SFTPServerInterface, chroot='/', logger=logger, server_event=event)
    logger('registered sFTP subsystem handler', loglevel=log.loglevel_DEBUG_SFTPXFER)
    server = _SSHServer(auth_key=auth_key, logger=logger)

    # start ssh server session
    t.start_server(server=server, event=event)

    while t.is_active():
        gevent.sleep(1)

    t.stop_thread()
    logger('sFTP channel %s closed down' % chan, loglevel=log.loglevel_DEBUG)


class X2GoRevFwSFTPChannelThread(rforward.X2GoRevFwChannelThread): pass
"""A clone of L{rforward.X2GoRevFwChannelThread}."""
