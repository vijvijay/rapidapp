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
Python X2Go exceptions.

"""
__NAME__ = 'x2goexceptions-pylib'

# modules
import paramiko
import exceptions

from defaults import X2GOCLIENT_OS as _X2GOCLIENT_OS

# Python X2Go Exceptions
AuthenticationException = paramiko.AuthenticationException
"""inherited from Python Paramiko library"""
PasswordRequiredException = paramiko.PasswordRequiredException
"""inherited from Python Paramiko library"""
BadHostKeyException = paramiko.BadHostKeyException
"""inherited from Python Paramiko library"""
SSHException = paramiko.SSHException
"""inherited from Python Paramiko library"""

class _X2GoException(exceptions.BaseException): pass
class X2GoClientException(_X2GoException): pass
class X2GoClientPrintingException(_X2GoException): pass
class X2GoClientSettingsException(_X2GoException): pass
class X2GoSessionException(_X2GoException): pass
class X2GoControlSessionException(_X2GoException): pass
class X2GoSFTPClientException(_X2GoException): pass
class X2GoRemoteHomeException(_X2GoException): pass
class X2GoHostKeyException(_X2GoException): pass
class X2GoSSHProxyPasswordRequiredException(_X2GoException): pass
class X2GoSSHProxyHostKeyException(_X2GoException): pass
class X2GoTerminalSessionException(_X2GoException): pass
class X2GoSessionCacheException(_X2GoException): pass
class X2GoUserException(_X2GoException): pass
class X2GoProfileException(_X2GoException): pass
class X2GoSessionRegistryException(_X2GoException): pass
class X2GoFwTunnelException(_X2GoException): pass
class X2GoRevFwTunnelException(_X2GoException): pass
class X2GoPrintException(_X2GoException): pass
class X2GoPrintQueueException(_X2GoException): pass
class X2GoPrintActionException(_X2GoException): pass
class X2GoProxyException(_X2GoException): pass
class X2GoMIMEboxActionException(_X2GoException): pass
class X2GoMIMEboxQueueException(_X2GoException): pass
class X2GoSSHProxyException(_X2GoException): pass
class X2GoSSHProxyAuthenticationException(_X2GoException): pass
class X2GoNotImplementedYetException(_X2GoException): pass
class X2GoDesktopSharingDenied(_X2GoException): pass
class X2GoTimeOutException(_X2GoException): pass
class X2GoBrokerConnectionException(_X2GoException): pass
class X2GoTelekinesisClientException(_X2GoException): pass
if _X2GOCLIENT_OS != 'Windows':
    # faking Windows errors on non-Windows systems...
    class WindowsError(_X2GoException): pass

# compat section
class X2goClientException(_X2GoException): pass
class X2goClientPrintingException(_X2GoException): pass
class X2goClientSettingsException(_X2GoException): pass
class X2goSessionException(_X2GoException): pass
class X2goControlSessionException(_X2GoException): pass
class X2goRemoteHomeException(_X2GoException): pass
class X2goHostKeyException(_X2GoException): pass
class X2goSSHProxyHostKeyException(_X2GoException): pass
class X2goTerminalSessionException(_X2GoException): pass
class X2goSessionCacheException(_X2GoException): pass
class X2goUserException(_X2GoException): pass
class X2goProfileException(_X2GoException): pass
class X2goSessionRegistryException(_X2GoException): pass
class X2goFwTunnelException(_X2GoException): pass
class X2goRevFwTunnelException(_X2GoException): pass
class X2goPrintException(_X2GoException): pass
class X2goPrintQueueException(_X2GoException): pass
class X2goPrintActionException(_X2GoException): pass
class X2goProxyException(_X2GoException): pass
class X2goMIMEboxActionException(_X2GoException): pass
class X2goMIMEboxQueueException(_X2GoException): pass
class X2goSSHProxyException(_X2GoException): pass
class X2goSSHProxyAuthenticationException(_X2GoException): pass
class X2goNotImplementedYetException(_X2GoException): pass
class X2goDesktopSharingException(_X2GoException): pass
class X2goTimeOutException(_X2GoException): pass

