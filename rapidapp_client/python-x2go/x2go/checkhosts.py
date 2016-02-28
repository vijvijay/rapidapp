# -*- coding: utf-8 -*-

"""\
Providing mechanisms to C{X2GoControlSession*} backends for checking host validity.

"""
__NAME__ = 'x2gocheckhosts-pylib'

# modules
import paramiko
import binascii

# Python X2Go modules
import sshproxy
import log
import x2go_exceptions
import random
import string

class X2GoMissingHostKeyPolicy(paramiko.MissingHostKeyPolicy):
    """\
    Skeleton class for Python X2Go's missing host key policies.

    """
    def __init__(self, caller=None, session_instance=None, fake_hostname=None):
        """\
        @param caller: calling instance
        @type caller: C{class}
        @param session_instance: an X2Go session instance
        @type session_instance: L{X2GoSession} instance

        """
        self.caller = caller
        self.session_instance = session_instance
        self.fake_hostname = fake_hostname

    def get_client(self):
        """\
        Retrieve the Paramiko SSH/Client.

        @return: the associated X2Go control session instance.
        @rtype: C{X2GoControlSession*} instance

        """
        return self.client

    def get_hostname(self):
        """\
        Retrieve the server hostname:port expression of the server to be validated.

        @return: hostname:port
        @rtype: C{str}

        """
        return self.fake_hostname or self.hostname

    def get_hostname_name(self):
        """\
        Retrieve the server hostname string of the server to be validated.

        @return: hostname
        @rtype: C{str}

        """
        if ":" in self.get_hostname():
            return self.get_hostname().split(':')[0].lstrip('[').rstrip(']')
        else:
            return self.get_hostname().lstrip('[').rstrip(']')

    def get_hostname_port(self):
        """\
        Retrieve the server port of the server to be validated.

        @return: port
        @rtype: C{str}

        """
        if ":" in self.get_hostname():
            return int(self.get_hostname().split(':')[1])
        else:
            return 22

    def get_key(self):
        """\
        Retrieve the host key of the server to be validated.

        @return: host key
        @rtype: Paramiko/SSH key instance

        """
        return self.key

    def get_key_name(self):
        """\
        Retrieve the host key name of the server to be validated.

        @return: host key name (RSA, DSA, ECDSA...)
        @rtype: C{str}

        """
        return self.key.get_name().upper()

    def get_key_fingerprint(self):
        """\
        Retrieve the host key fingerprint of the server to be validated.

        @return: host key fingerprint
        @rtype: C{str}

        """
        return binascii.hexlify(self.key.get_fingerprint())

    def get_key_fingerprint_with_colons(self):
        """\
        Retrieve the (colonized) host key fingerprint of the server
        to be validated.

        @return: host key fingerprint (with colons)
        @rtype: C{str}

        """
        _fingerprint = self.get_key_fingerprint()
        _colon_fingerprint = ''
        idx = 0
        for char in _fingerprint:
            idx += 1
            _colon_fingerprint += char
            if idx % 2 == 0:
                _colon_fingerprint += ':'
        return _colon_fingerprint.rstrip(':')


class X2GoAutoAddPolicy(X2GoMissingHostKeyPolicy):

    def missing_host_key(self, client, hostname, key):
        self.client = client
        self.hostname = hostname
        self.key = key
        if self.session_instance and self.session_instance.control_session.unique_hostkey_aliases:
            self.client._host_keys.add(self.session_instance.get_profile_id(), self.key.get_name(), self.key)
        else:
            self.client._host_keys.add(self.get_hostname(), self.key.get_name(), self.key)
        if self.client._host_keys_filename is not None:
            self.client.save_host_keys(self.client._host_keys_filename)
        self.client._log(paramiko.common.DEBUG, 'Adding %s host key for %s: %s' %
                         (self.key.get_name(), self.get_hostname(), binascii.hexlify(self.key.get_fingerprint())))


class X2GoInteractiveAddPolicy(X2GoMissingHostKeyPolicy):
    """\
    Policy for making host key information available to Python X2Go after a
    Paramiko/SSH connect has been attempted. This class needs information
    about the associated L{X2GoSession} instance.

    Once called, the L{missing_host_key} method of this class will try to call
    L{X2GoSession.HOOK_check_host_dialog()}. This hook method---if not re-defined
    in your application---will then try to call the L{X2GoClient.HOOK_check_host_dialog()},
    which then will return C{True} by default if not customized in your application.

    To accept host key checks, make sure to either customize the 
    L{X2GoClient.HOOK_check_host_dialog()} method or the L{X2GoSession.HOOK_check_host_dialog()}
    method and hook some interactive user dialog to either of them.

    """
    def missing_host_key(self, client, hostname, key):
        """\
        Handle a missing host key situation. This method calls

        Once called, the L{missing_host_key} method will try to call
        L{X2GoSession.HOOK_check_host_dialog()}. This hook method---if not re-defined
        in your application---will then try to call the L{X2GoClient.HOOK_check_host_dialog()},
        which then will return C{True} by default if not customized in your application.

        To accept host key checks, make sure to either customize the 
        L{X2GoClient.HOOK_check_host_dialog()} method or the L{X2GoSession.HOOK_check_host_dialog()}
        method and hook some interactive user dialog to either of them.

        @param client: SSH client (C{X2GoControlSession*}) instance
        @type client: C{X2GoControlSession*} instance
        @param hostname: remote hostname
        @type hostname: C{str}
        @param key: host key to validate
        @type key: Paramiko/SSH key instance

        @raise X2GoHostKeyException: if the X2Go server host key is not in the C{known_hosts} file
        @raise X2GoSSHProxyHostKeyException: if the SSH proxy host key is not in the C{known_hosts} file
        @raise SSHException: if this instance does not know its {self.session_instance}

        """
        self.client = client
        self.hostname = hostname
        if (self.hostname.find(']') == -1) and (self.hostname.find(':') == -1):
            # if hostname is an IPv4 quadruple with standard SSH port...
            self.hostname = '[%s]:22' % self.hostname
        self.key = key
        self.client._log(paramiko.common.DEBUG, 'Interactively Checking %s host key for %s: %s' %
                         (self.key.get_name(), self.get_hostname(), binascii.hexlify(self.key.get_fingerprint())))
        if self.session_instance:

            if self.fake_hostname is not None:
                server_key = client.get_transport().get_remote_server_key()
                keytype = server_key.get_name()
                our_server_key = client._system_host_keys.get(self.fake_hostname, {}).get(keytype, None)
                if our_server_key is None:
                    if self.session_instance.control_session.unique_hostkey_aliases:
                        our_server_key = client._host_keys.get(self.session_instance.get_profile_id(), {}).get(keytype, None)
                        if our_server_key is not None:
                            self.session_instance.logger('SSH host key verification for SSH-proxied host %s with %s fingerprint ,,%s\'\' succeeded. This host is known by the X2Go session profile ID of profile ,,%s\'\'.' % (self.fake_hostname, self.get_key_name(), self.get_key_fingerprint_with_colons(), self.session_instance.profile_name), loglevel=log.loglevel_NOTICE)
                            return
                    else:
                        our_server_key = client._host_keys.get(self.fake_hostname, {}).get(keytype, None)
                        if our_server_key is not None:
                            self.session_instance.logger('SSH host key verification for SSH-proxied host %s with %s fingerprint ,,%s\'\' succeeded. This host is known by the address it has behind the SSH proxy host.' % (self.fake_hostname, self.get_key_name(), self.get_key_fingerprint_with_colons()), loglevel=log.loglevel_NOTICE)
                            return

            self.session_instance.logger('SSH host key verification for host %s with %s fingerprint ,,%s\'\' initiated. We are seeing this X2Go server for the first time.' % (self.get_hostname(), self.get_key_name(), self.get_key_fingerprint_with_colons()), loglevel=log.loglevel_NOTICE)
            _valid = self.session_instance.HOOK_check_host_dialog(self.get_hostname_name(),
                                                                  port=self.get_hostname_port(),
                                                                  fingerprint=self.get_key_fingerprint_with_colons(),
                                                                  fingerprint_type=self.get_key_name(),
                                                                 )
            if _valid:
                if self.session_instance.control_session.unique_hostkey_aliases and type(self.caller) not in (sshproxy.X2GoSSHProxy, ):
                    paramiko.AutoAddPolicy().missing_host_key(client, self.session_instance.get_profile_id(), key)
                else:
                    paramiko.AutoAddPolicy().missing_host_key(client, self.get_hostname(), key)

            else:
                if type(self.caller) in (sshproxy.X2GoSSHProxy, ):
                    raise x2go_exceptions.X2GoSSHProxyHostKeyException('Invalid host %s is not authorized for access. Add the host to Paramiko/SSH\'s known_hosts file.' % self.get_hostname())
                else:
                    raise x2go_exceptions.X2GoHostKeyException('Invalid host %s is not authorized for access. Add the host to Paramiko/SSH\'s known_hosts file.' % self.get_hostname())
        else:
            raise x2go_exceptions.SSHException('Policy has collected host key information on %s for further introspection' % self.get_hostname())


def check_ssh_host_key(x2go_sshclient_instance, hostname, port=22):
    """\
    Perform a Paramiko/SSH host key check by connecting to the host and
    validating the results (i.e. by validating raised exceptions during the
    connect process).

    @param x2go_sshclient_instance: a Paramiko/SSH client instance to be used for testing host key validity.
    @type x2go_sshclient_instance: C{X2GoControlSession*} instance
    @param hostname: hostname of server to validate
    @type hostname: C{str}
    @param port: port of server to validate
    @type port: C{int}

    @return: returns a tuple with the following components (<host_ok>, <hostname>, <port>, <fingerprint>, <fingerprint_type>)
    @rtype: C{tuple}

    @raise SSHException: if an SSH exception occurred, that we did not provocate in L{X2GoInteractiveAddPolicy.missing_host_key()}

    """
    _hostname = hostname
    _port = port
    _fingerprint = 'NO-FINGERPRINT'
    _fingerprint_type = 'SOME-KEY-TYPE'

    _check_policy = X2GoInteractiveAddPolicy()
    x2go_sshclient_instance.set_missing_host_key_policy(_check_policy)

    host_ok = False
    try:
        paramiko.SSHClient.connect(x2go_sshclient_instance, hostname=hostname, port=port, username='foo', password="".join([random.choice(string.letters+string.digits) for x in range(1, 20)]))
    except x2go_exceptions.AuthenticationException:
        host_ok = True
        x2go_sshclient_instance.logger('SSH host key verification for host [%s]:%s succeeded. Host is already known to the client\'s Paramiko/SSH sub-system.' % (_hostname, _port), loglevel=log.loglevel_NOTICE)
    except x2go_exceptions.SSHException, e:
        msg = str(e)
        if msg.startswith('Policy has collected host key information on '):
            _hostname = _check_policy.get_hostname().split(':')[0].lstrip('[').rstrip(']')
            _port = _check_policy.get_hostname().split(':')[1]
            _fingerprint = _check_policy.get_key_fingerprint_with_colons()
            _fingerprint_type = _check_policy.get_key_name()
        else:
            raise(e)
        x2go_sshclient_instance.set_missing_host_key_policy(paramiko.RejectPolicy())
    except:
        # let any other error be handled by subsequent algorithms
        pass

    return (host_ok, _hostname, _port, _fingerprint, _fingerprint_type)
