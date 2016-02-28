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
L{X2GoSSHProxy} class - providing a forwarding tunnel for connecting to servers behind firewalls.

"""
__NAME__ = 'x2gosshproxy-pylib'

# modules
import gevent
import os
import copy
import paramiko
import threading
import types

import string
import random

# Python X2Go modules
import forward
import checkhosts
import log
import utils
import x2go_exceptions

from x2go.defaults import CURRENT_LOCAL_USER as _CURRENT_LOCAL_USER
from x2go.defaults import LOCAL_HOME as _LOCAL_HOME
from x2go.defaults import X2GO_SSH_ROOTDIR as _X2GO_SSH_ROOTDIR

import x2go._paramiko
x2go._paramiko.monkey_patch_paramiko()

class X2GoSSHProxy(paramiko.SSHClient, threading.Thread):
    """\
    X2GoSSHProxy can be used to proxy X2Go connections through a firewall via SSH.

    """
    fw_tunnel = None

    def __init__(self, hostname=None, port=22, username=None, password=None, passphrase=None, force_password_auth=False, key_filename=None,
                 local_host='localhost', local_port=22022, remote_host='localhost', remote_port=22,
                 known_hosts=None, add_to_known_hosts=False, pkey=None, look_for_keys=False, allow_agent=False,
                 sshproxy_host=None, sshproxy_port=22, sshproxy_user=None,
                 sshproxy_password=None, sshproxy_force_password_auth=False, sshproxy_key_filename=None, sshproxy_pkey=None, sshproxy_passphrase=None,
                 sshproxy_look_for_keys=False, sshproxy_allow_agent=False,
                 sshproxy_tunnel=None,
                 ssh_rootdir=os.path.join(_LOCAL_HOME, _X2GO_SSH_ROOTDIR), 
                 session_instance=None,
                 logger=None, loglevel=log.loglevel_DEFAULT, ):
        """\
        Initialize an X2GoSSHProxy instance. Use an instance of this class to tunnel X2Go requests through
        a proxying SSH server (i.e. to subLANs that are separated by firewalls or to private IP subLANs that
        are NATted behind routers).

        @param username: login user name to be used on the SSH proxy host
        @type username: C{str}
        @param password: user's password on the SSH proxy host, with private key authentication it will be
            used to unlock the key (if needed)
        @type password: C{str}
        @param passphrase: a passphrase to use for unlocking
            a private key in case the password is already needed for two-factor
            authentication
        @type passphrase: {str}
        @param key_filename: name of a SSH private key file
        @type key_filename: C{str}
        @param pkey: a private DSA/RSA key object (as provided by Paramiko/SSH)
        @type pkey: C{RSA/DSA key instance}
        @param force_password_auth: enforce password authentication even if a key(file) is present
        @type force_password_auth: C{bool}
        @param look_for_keys: look for key files with standard names and try those if any can be found
        @type look_for_keys: C{bool}
        @param allow_agent: try authentication via a locally available SSH agent
        @type allow_agent: C{bool}
        @param local_host: bind SSH tunnel to the C{local_host} IP socket address (default: localhost)
        @type local_host: C{str}
        @param local_port: IP socket port to bind the SSH tunnel to (default; 22022)
        @type local_port: C{int}
        @param remote_host: remote endpoint of the SSH proxying/forwarding tunnel (default: localhost)
        @type remote_host: C{str}
        @param remote_port: remote endpoint's IP socket port for listening SSH daemon (default: 22)
        @type remote_port: C{int}
        @param known_hosts: full path to a custom C{known_hosts} file
        @type known_hosts: C{str}
        @param add_to_known_hosts: automatically add host keys of unknown SSH hosts to the C{known_hosts} file
        @type add_to_known_hosts: C{bool}
        @param hostname: alias for C{local_host}
        @type hostname: C{str}
        @param port: alias for C{local_port}
        @type port: C{int}
        @param sshproxy_host: alias for C{hostname}
        @type sshproxy_host: C{str}
        @param sshproxy_port: alias for C{post}
        @type sshproxy_port: C{int}
        @param sshproxy_user: alias for C{username}
        @type sshproxy_user: C{str}
        @param sshproxy_password: alias for C{password}
        @type sshproxy_password: C{str}
        @param sshproxy_passphrase: alias for C{passphrase}
        @type sshproxy_passphrase: C{str}
        @param sshproxy_key_filename: alias for C{key_filename}
        @type sshproxy_key_filename: C{str}
        @param sshproxy_pkey: alias for C{pkey}
        @type sshproxy_pkey: C{RSA/DSA key instance} (Paramiko)
        @param sshproxy_force_password_auth: alias for C{force_password_auth}
        @type sshproxy_force_password_auth: C{bool}
        @param sshproxy_look_for_keys: alias for C{look_for_keys}
        @type sshproxy_look_for_keys: C{bool}
        @param sshproxy_allow_agent: alias for C{allow_agent}
        @type sshproxy_allow_agent: C{bool}

        @param sshproxy_tunnel: a string of the format <local_host>:<local_port>:<remote_host>:<remote_port> 
            which will override---if used---the options: C{local_host}, C{local_port}, C{remote_host} and C{remote_port}
        @type sshproxy_tunnel: C{str}

        @param ssh_rootdir: local user's SSH base directory (default: ~/.ssh)
        @type ssh_rootdir: C{str}
        @param session_instance: the L{X2GoSession} instance that builds up this SSH proxying tunnel
        @type session_instance: L{X2GoSession} instance
        @param logger: you can pass an L{X2GoLogger} object to the
            L{X2GoSSHProxy} constructor
        @type logger: L{X2GoLogger} instance
        @param loglevel: if no L{X2GoLogger} object has been supplied a new one will be
            constructed with the given loglevel
        @type loglevel: int

        @raise X2GoSSHProxyAuthenticationException: if the SSH proxy caused a C{paramiko.AuthenticationException}
        @raise X2GoSSHProxyException: if the SSH proxy caused a C{paramiko.SSHException}
        """
        if logger is None:
            self.logger = log.X2GoLogger(loglevel=loglevel)
        else:
            self.logger = copy.deepcopy(logger)
        self.logger.tag = __NAME__

        if hostname and hostname in (types.UnicodeType, types.StringType):
            hostname = [hostname]
        if hostname and hostname in (types.ListType, types.TupleType):
            hostname = random.choice(list(hostname))
        self.hostname, self.port, self.username = hostname, port, username

        if sshproxy_port: self.port = sshproxy_port

        # translate between X2GoSession options and paramiko.SSHCLient.connect() options
        # if <hostname>:<port> is used for sshproxy_host, then this <port> is used
        if sshproxy_host:
            if sshproxy_host and type(sshproxy_host) in (types.UnicodeType, types.StringType):
                sshproxy_host = [sshproxy_host]
            if type(sshproxy_host) in (types.ListType, types.TupleType):
                sshproxy_host = random.choice(list(sshproxy_host))
            if sshproxy_host.find(':'):
                self.hostname = sshproxy_host.split(':')[0]
                try: self.port = int(sshproxy_host.split(':')[1])
                except IndexError: pass
            else:
                self.hostname = sshproxy_host

        if sshproxy_user: self.username = sshproxy_user
        if sshproxy_password: password = sshproxy_password
        if sshproxy_passphrase: passphrase = sshproxy_passphrase
        if sshproxy_force_password_auth: force_password_auth = sshproxy_force_password_auth
        if sshproxy_key_filename: key_filename = sshproxy_key_filename
        if sshproxy_pkey: pkey = sshproxy_pkey
        if sshproxy_look_for_keys: look_for_keys = sshproxy_look_for_keys
        if sshproxy_allow_agent: allow_agent = sshproxy_allow_agent
        if sshproxy_tunnel:
            self.local_host, self.local_port, self.remote_host, self.remote_port = sshproxy_tunnel.split(':')
            self.local_port = int(self.local_port)
            self.remote_port = int(self.remote_port)
        else:
            if local_host and type(local_host) in (types.UnicodeType, types.StringType):
                local_host = [local_host]
            if local_host and type(local_host) in (types.ListType, types.TupleType):
                local_host = random.choice(list(local_host))
            if remote_host and type(remote_host) in (types.UnicodeType, types.StringType):
                remote_host = [remote_host]
            if remote_host and type(remote_host) in (types.ListType, types.TupleType):
                remote_host = random.choice(remote_host)
            print "LOCAL_HOST: ", local_host
            self.local_host = local_host
            self.local_port = int(local_port)
            self.remote_host =  remote_host
            self.remote_port = int(remote_port)

        # allow more trailing whitespace tolerance in hostnames
        self.hostname = self.hostname.strip()
        self.local_host = self.local_host.strip()
        self.remote_host = self.remote_host.strip()

        # do not use explicitly given keys if look_for_keys has got activated
        if look_for_keys:
            key_filename = None
            pkey = None

        if key_filename and "~" in key_filename:
            key_filename = os.path.expanduser(key_filename)

        if password and (passphrase is None): passphrase = password

        # enforce IPv4 for localhost addresses!!!
        _hostname = self.hostname
        if _hostname in ('localhost', 'localhost.localdomain'):
            _hostname = '127.0.0.1'
        if self.local_host in ('localhost', 'localhost.localdomain'):
            self.local_host = '127.0.0.1'
        if self.remote_host in ('localhost', 'localhost.localdomain'):
            self.remote_host = '127.0.0.1'

        if username is None:
            username = _CURRENT_LOCAL_USER

        if type(password) not in (types.StringType, types.UnicodeType):
            password = ''

        self._keepalive = True
        self.session_instance = session_instance

        self.client_instance = None
        if self.session_instance is not None:
            self.client_instance = self.session_instance.get_client_instance()

        self.ssh_rootdir = ssh_rootdir
        paramiko.SSHClient.__init__(self)

        self.known_hosts = known_hosts
        if self.known_hosts:
            utils.touch_file(self.known_hosts)
            self.load_host_keys(self.known_hosts)

        if not add_to_known_hosts and session_instance:
            self.set_missing_host_key_policy(checkhosts.X2GoInteractiveAddPolicy(caller=self, session_instance=session_instance))

        if add_to_known_hosts:
            self.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            if key_filename or pkey or look_for_keys or allow_agent or (password and force_password_auth):
                try:
                    if password and force_password_auth:
                        self.connect(_hostname, port=self.port,
                                     username=self.username,
                                     password=password,
                                     key_filename=None,
                                     pkey=None,
                                     look_for_keys=False,
                                     allow_agent=False,
                                    )
                    elif (key_filename and os.path.exists(os.path.normpath(key_filename))) or pkey:
                        self.connect(_hostname, port=self.port,
                                     username=self.username,
                                     key_filename=key_filename,
                                     pkey=pkey,
                                     allow_agent=False,
                                     look_for_keys=False,
                                    )
                    else:
                        self.connect(_hostname, port=self.port,
                                     username=self.username,
                                     key_filename=None,
                                     pkey=None,
                                     look_for_keys=look_for_keys,
                                     allow_agent=allow_agent,
                                    )

                except (paramiko.PasswordRequiredException, paramiko.SSHException), e:
                    self.close()
                    if type(e) == paramiko.SSHException and str(e).startswith('Two-factor authentication requires a password'):
                        self.logger('SSH proxy host requests two-factor authentication', loglevel=log.loglevel_NOTICE)
                        raise x2go_exceptions.X2GoSSHProxyException(str(e))

                    if passphrase is None:
                        try:
                            if not password: password = None
                            if (key_filename and os.path.exists(os.path.normpath(key_filename))) or pkey:
                                try:
                                    self.connect(_hostname, port=self.port,
                                                 username=self.username,
                                                 password=password,
                                                 passphrase=passphrase,
                                                 key_filename=key_filename,
                                                 pkey=pkey,
                                                 allow_agent=False,
                                                 look_for_keys=False,
                                                )
                                except TypeError:
                                    self.connect(_hostname, port=self.port,
                                                 username=self.username,
                                                 password=passphrase,
                                                 key_filename=key_filename,
                                                 pkey=pkey,
                                                 allow_agent=False,
                                                 look_for_keys=False,
                                                )
                            else:
                                try:
                                    self.connect(_hostname, port=self.port,
                                                 username=self.username,
                                                 password=password,
                                                 passphrase=passphrase,
                                                 key_filename=None,
                                                 pkey=None,
                                                 look_for_keys=look_for_keys,
                                                 allow_agent=allow_agent,
                                                )
                                except TypeError:
                                    self.connect(_hostname, port=self.port,
                                                 username=self.username,
                                                 password=passphrase,
                                                 key_filename=None,
                                                 pkey=None,
                                                 look_for_keys=look_for_keys,
                                                 allow_agent=allow_agent,
                                                )
                        except x2go_exceptions.AuthenticationException, auth_e:
                            raise x2go_exceptions.X2GoSSHProxyAuthenticationException(str(auth_e))

                    else:
                        if type(e) == paramiko.SSHException:
                            raise x2go_exceptions.X2GoSSHProxyException(str(e))
                        elif type(e) == paramiko.PasswordRequiredException:
                            raise x2go_exceptions.X2GoSSHProxyPasswordRequiredException(str(e))
                except x2go_exceptions.AuthenticationException:
                    self.close()
                    raise x2go_exceptions.X2GoSSHProxyAuthenticationException('all authentication mechanisms with SSH proxy host failed')
                except x2go_exceptions.SSHException:
                    self.close()
                    raise x2go_exceptions.X2GoSSHProxyAuthenticationException('with SSH proxy host password authentication is required')
                except:
                    raise

                # since Paramiko 1.7.7.1 there is compression available, let's use it if present...
                t = self.get_transport()
                if x2go._paramiko.PARAMIKO_FEATURE['use-compression']:
                    t.use_compression(compress=False)
                t.set_keepalive(5)

            # if there is no private key, we will use the given password, if any
            else:
                # create a random password if password is empty to trigger host key validity check
                if not password:
                    password = "".join([random.choice(string.letters+string.digits) for x in range(1, 20)])
                try:
                    self.connect(_hostname, port=self.port,
                                 username=self.username,
                                 password=password,
                                 look_for_keys=False,
                                 allow_agent=False,
                                )
                except x2go_exceptions.AuthenticationException:
                    self.close()
                    raise x2go_exceptions.X2GoSSHProxyAuthenticationException('interactive auth mechanisms failed')
                except:
                    self.close()
                    raise

        except (x2go_exceptions.SSHException, IOError), e:
            self.close()
            raise x2go_exceptions.X2GoSSHProxyException(str(e))
        except:
            self.close()
            raise


        self.set_missing_host_key_policy(paramiko.RejectPolicy())
        threading.Thread.__init__(self)
        self.daemon = True

    def check_host(self):
        """\
        Wraps around a Paramiko/SSH host key check.

        """
        _hostname = self.hostname

        # force into IPv4 for localhost connections
        if _hostname in ('localhost', 'localhost.localdomain'):
            _hostname = '127.0.0.1'

        _valid = False
        (_valid, _hostname, _port, _fingerprint, _fingerprint_type) = checkhosts.check_ssh_host_key(self, _hostname, port=self.port)
        if not _valid and self.session_instance:
            _valid = self.session_instance.HOOK_check_host_dialog(self.remote_host, self.remote_port, fingerprint=_fingerprint, fingerprint_type=_fingerprint_type)
        return _valid

    def run(self):
        """\
        Start the SSH proxying tunnel...

        @raise X2GoSSHProxyException: if the SSH proxy could not retrieve an SSH transport for proxying a X2Go server-client connection

        """
        if self.get_transport() is not None and self.get_transport().is_authenticated():
            self.local_port = utils.detect_unused_port(bind_address=self.local_host, preferred_port=self.local_port)
            self.fw_tunnel = forward.start_forward_tunnel(local_host=self.local_host,
                                                          local_port=self.local_port,
                                                          remote_host=self.remote_host,
                                                          remote_port=self.remote_port,
                                                          ssh_transport=self.get_transport(),
                                                          logger=self.logger, )
            self.logger('SSH proxy tunnel via [%s]:%s has been set up' % (self.hostname, self.port), loglevel=log.loglevel_NOTICE)
            self.logger('SSH proxy tunnel startpoint is [%s]:%s, endpoint is [%s]:%s' % (self.local_host, self.local_port, self.remote_host, self.remote_port), loglevel=log.loglevel_NOTICE)

            while self._keepalive:
                gevent.sleep(.1)

        else:
            raise x2go_exceptions.X2GoSSHProxyException('SSH proxy connection could not retrieve an SSH transport')

    def get_local_proxy_host(self):
        """\
        Retrieve the local IP socket address this SSH proxying tunnel is (about to) bind/bound to.

        @return: local IP socket address
        @rtype: C{str}

        """
        return self.local_host

    def get_local_proxy_port(self):
        """\
        Retrieve the local IP socket port this SSH proxying tunnel is (about to) bind/bound to.

        @return: local IP socket port
        @rtype: C{int}

        """
        return self.local_port

    def get_remote_host(self):
        """\
        Retrieve the remote IP socket address at the remote end of the SSH proxying tunnel.

        @return: remote IP socket address
        @rtype: C{str}

        """
        return self.remote_host

    def get_remote_port(self):
        """\
        Retrieve the remote IP socket port of the target system's SSH daemon.

        @return: remote SSH port
        @rtype: C{int}

        """
        return self.remote_port

    def stop_thread(self):
        """\
        Tear down the SSH proxying tunnel.

        """
        if self.fw_tunnel is not None and self.fw_tunnel.is_active:
            self.logger('taking down SSH proxy tunnel via [%s]:%s' % (self.hostname, self.port), loglevel=log.loglevel_NOTICE)
        try: forward.stop_forward_tunnel(self.fw_tunnel)
        except: pass
        self.fw_tunnel = None
        self._keepalive = False
        if self.get_transport() is not None:
            self.logger('closing SSH proxy connection to [%s]:%s' % (self.hostname, self.port), loglevel=log.loglevel_NOTICE)
        self.close()
        self.password = self.sshproxy_password = None

    def __del__(self):
        """\
        Class desctructor.

        """
        self.stop_thread()
