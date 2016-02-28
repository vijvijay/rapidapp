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
Monkey Patch and feature map for Python Paramiko

"""

import paramiko
import re
try:
    from paramiko.config import SSH_PORT
except ImportError:
    SSH_PORT=22
import platform
from utils import compare_versions

PARAMIKO_VERSION = paramiko.__version__.split()[0]
PARAMIKO_FEATURE = {
    'forward-ssh-agent': compare_versions(PARAMIKO_VERSION, ">=", '1.8.0') and (platform.system() != "Windows"),
    'use-compression': compare_versions(PARAMIKO_VERSION, ">=", '1.7.7.1'),
    'hash-host-entries': compare_versions(PARAMIKO_VERSION, ">=", '99'),
    'host-entries-reloadable': compare_versions(PARAMIKO_VERSION, ">=", '1.11.0'),
    'preserve-known-hosts': compare_versions(PARAMIKO_VERSION, ">=", '1.11.0'),
    'ecdsa-hostkeys': compare_versions(PARAMIKO_VERSION, ">=", '1.11.6'),
}

def _SSHClient_save_host_keys(self, filename):
    """\
    Available since paramiko 1.11.0...

    This method has been taken from SSHClient class in Paramiko and
    has been improved and adapted to latest SSH implementations.

    Save the host keys back to a file.
    Only the host keys loaded with
    L{load_host_keys} (plus any added directly) will be saved -- not any
    host keys loaded with L{load_system_host_keys}.

    @param filename: the filename to save to
    @type filename: str

    @raise IOError: if the file could not be written 

    """
    # update local host keys from file (in case other SSH clients
    # have written to the known_hosts file meanwhile.
    if self.known_hosts is not None:
        self.load_host_keys(self.known_hosts)

    f = open(filename, 'w')
    #f.write('# SSH host keys collected by paramiko\n')
    _host_keys = self.get_host_keys()
    for hostname, keys in _host_keys.iteritems():

        for keytype, key in keys.iteritems():
            f.write('%s %s %s\n' % (hostname, keytype, key.get_base64()))

    f.close()


def _HostKeys_load(self, filename):
    """\
    Available since paramiko 1.11.0...

    Read a file of known SSH host keys, in the format used by openssh.
    This type of file unfortunately doesn't exist on Windows, but on
    posix, it will usually be stored in
    C{os.path.expanduser("~/.ssh/known_hosts")}.

    If this method is called multiple times, the host keys are merged,
    not cleared. So multiple calls to C{load} will just call L{add},
    replacing any existing entries and adding new ones.

    @param filename: name of the file to read host keys from
    @type filename: str

    @raise IOError: if there was an error reading the file

    """
    f = open(filename, 'r')
    for line in f:
        line = line.strip()
        if (len(line) == 0) or (line[0] == '#'):
            continue
        e = paramiko.hostkeys.HostKeyEntry.from_line(line)
        if e is not None:
            _hostnames = e.hostnames
            for h in _hostnames:
                if self.check(h, e.key):
                    e.hostnames.remove(h)
            if len(e.hostnames):
                self._entries.append(e)
    f.close() 


def _HostKeys_add(self, hostname, keytype, key, hash_hostname=True):
    """\
    Add a host key entry to the table. Any existing entry for a
    C{(hostname, keytype)} pair will be replaced.

    @param hostname: the hostname (or IP) to add
    @type hostname: str
    @param keytype: key type (C{"ssh-rsa"}, C{"ssh-dss"} or C{"ecdsa-sha2-nistp256"})
    @type keytype: str
    @param key: the key to add
    @type key: L{PKey}

    """
    # IPv4 and IPv6 addresses using the SSH default port need to be stripped off the port number
    if re.match('^\[.*\]\:'+str(SSH_PORT)+'$', hostname):
        # so stripping off the port and the square brackets here...
        hostname = hostname.split(':')[-2].lstrip('[').rstrip(']')

    for e in self._entries:
        if (hostname in e.hostnames) and (e.key.get_name() == keytype):
            e.key = key
            return
    if not hostname.startswith('|1|') and hash_hostname:
        hostname = self.hash_host(hostname)
    self._entries.append(paramiko.hostkeys.HostKeyEntry([hostname], key))


def monkey_patch_paramiko():
    if not PARAMIKO_FEATURE['preserve-known-hosts']:
        paramiko.SSHClient.save_host_keys = _SSHClient_save_host_keys
    if not PARAMIKO_FEATURE['host-entries-reloadable']:
        paramiko.hostkeys.HostKeys.load = _HostKeys_load
    if not PARAMIKO_FEATURE['hash-host-entries']:
        paramiko.hostkeys.HostKeys.add = _HostKeys_add
