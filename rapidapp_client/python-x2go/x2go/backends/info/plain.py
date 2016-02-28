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
X2GoServerSessionList and X2GoServerSessionInfo classes - data handling for 
X2Go server sessions.

This backend handles X2Go server implementations that respond with session infos 
via server-side PLAIN text output.

"""
__NAME__ = 'x2goserversessioninfo-pylib'


# modules
import types
import re

class X2GoServerSessionInfo(object):
    """\
    L{X2GoServerSessionInfo} is used to store all information
    that is retrieved from the connected X2Go server on 
    C{X2GoTerminalSession.start()} resp. C{X2GoTerminalSession.resume()}.

    """
    def __str__(self):
        return self.name
    def __repr__(self):
        result = 'X2GoServerSessionInfo('
        for p in dir(self):
            if '__' in p or not p in self.__dict__ or type(p) is types.InstanceType: continue
            result += p + '=' + str(self.__dict__[p]) +','
        return result.strip(',') + ')'

    def _parse_x2golistsessions_line(self, x2go_output):
        """\
        Parse a single line of X2Go's listsessions output.

        @param x2go_output: output from ,,x2golistsessions'' command (as list of strings/lines)
        @type x2go_output: C{list}

        """
        try:
            l = x2go_output.split("|")
            self.agent_pid = int(l[0])
            self.name = l[1]
            self.display = int(l[2])
            self.hostname = l[3]
            self.status = l[4]
            # TODO: turn into datetime object
            self.date_created = l[5]
            self.cookie = l[6]
            self.graphics_port = int(l[8])
            self.snd_port = int(l[9])
            # TODO: turn into datetime object
            self.date_suspended = l[10]
            self.username = l[11]
            self.sshfs_port = int(l[13])
            self.local_container = ''
        except IndexError, e:
            # DEBUGGING CODE
            raise e
        except ValueError, e:
            # DEBUGGING CODE
            raise e

        # retrieve Telekinesis ports from list of sessions...
        try:
            self.tekictrl_port = int(l[14])
        except (IndexError, ValueError), e:
            self.tekictrl_port = -1
        try:
            self.tekidata_port = int(l[15])
        except (IndexError, ValueError), e:
            self.tekidata_port = -1

    def is_published_applications_provider(self):
        """\
        Detect from session info if this session is a published applications provider.

        @return: returns C{True} if this session is a published applications provider
        @rtype: C{bool}

        """
        return bool(re.match('.*_stRPUBLISHED_.*', self.name))

    def is_running(self):
        """\
        Is this session running?

        @return: C{True} if the session is running, C{False} otherwise
        @rtype: C{bool}

        """
        return self.status == 'R'

    def get_session_type(self):
        """\
        Get the session type (i.e. 'D', 'R', 'S' or 'P').

        @return: session type
        @rtype: C{str}
        """
        try:
            cmd = self.name.split('_')[1]
            session_type = cmd[2]
            if session_type == 'R' and self.is_published_applications_provider():
                session_type = 'P'
            return session_type
        except:
            return 'P'

    def get_share_mode(self):
        """\
        Get the share mode of a shadow session.

        @return: share mode (0: view-only, 1: full access), C{None} when used for non-desktop-sharing sessions
        @rtype: C{str}

        """
        share_mode = None
        cmd = self.name.split('_')[1]
        session_type = cmd[2]
        if session_type == 'S':
            share_mode = cmd[3]
        return share_mode

    def is_suspended(self):
        """\
        Is this session suspended?

        @return: C{True} if the session is suspended, C{False} otherwise
        @rtype: C{bool}

        """
        return self.status == 'S'

    def is_desktop_session(self):
        """\
        Is this session a desktop session?

        @return: C{True} if this session is a desktop session, C{False} otherwise
        @rtype: C{bool}

        """
        return self.get_session_type() == 'D'

    def _parse_x2gostartagent_output(self, x2go_output):
        """\
        Parse x2gostartagent output.

        @param x2go_output: output from ,,x2gostartagent'' command (as list of strings/lines)
        @type x2go_output: C{list}

        """
        try:
            l = x2go_output.split("\n")
            self.name = l[3]
            self.cookie = l[1]
            self.agent_pid = int(l[2])
            self.display = int(l[0])
            self.graphics_port = int(l[4])
            self.snd_port = int(l[5])
            self.sshfs_port = int(l[6])
            self.username = ''
            self.hostname = ''
            # TODO: we have to see how we fill these fields here...
            self.date_created = ''
            self.date_suspended = ''
            # TODO: presume session is running after x2gostartagent, this could be better
            self.status = 'R'
            self.local_container = ''
            self.remote_container = ''
        except IndexError, e:
            # DEBUGGING CODE
            raise e
        except ValueError, e:
            # DEBUGGING CODE
            raise e

        # retrieve Telekinesis ports from x2gostartagent output
        try:
            self.tekictrl_port = int(l[7])
        except (IndexError, ValueError), e:
            self.tekictrl_port = -1
        try:
            self.tekidata_port = int(l[8])
        except (IndexError, ValueError), e:
            self.tekidata_port = -1

    def initialize(self, x2go_output, username='', hostname='', local_container='', remote_container=''):
        """\
        Setup a a session info data block, includes parsing of X2Go server's C{x2gostartagent} stdout values.

        @param x2go_output: X2Go server's C{x2gostartagent} command output, each value 
            separated by a newline character.
        @type x2go_output: str
        @param username: session user name
        @type username: str
        @param hostname: hostname of X2Go server
        @type hostname: str
        @param local_container: X2Go client session directory for config files, cache and session logs
        @type local_container: str
        @param remote_container: X2Go server session directory for config files, cache and session logs
        @type remote_container: str

        """
        self.protect()
        self._parse_x2gostartagent_output(x2go_output)
        self.username = username
        self.hostname = hostname
        self.local_container = local_container
        self.remote_container = remote_container

    def protect(self):
        """\
        Write-protect this session info data structure.

        """
        self.protected = True

    def unprotect(self):
        """\
        Remove write-protection from this session info data structure.

        """
        self.protected = False

    def is_protected(self):
        """\

        """
        return self.protected

    def get_status(self):
        """\
        Retrieve the session's status from this session info data structure.

        @return: session status
        @rtype: C{str}

        """
        return self.status

    def clear(self):
        """\
        Clear all properties of a L{X2GoServerSessionInfo} object.

        """
        self.name = ''
        self.cookie = ''
        self.agent_pid = ''
        self.display = ''
        self.graphics_port = ''
        self.snd_port = ''
        self.sshfs_port = ''
        self.tekictrl_port = ''
        self.tekidata_port = ''
        self.username = ''
        self.hostname = ''
        self.date_created = ''
        self.date_suspended = ''
        self.status = ''
        self.local_container = ''
        self.remote_container = ''
        self.protected = False

    def update(self, session_info):
        """\
        Update all properties of a L{X2GoServerSessionInfo} object.

        @param session_info: a provided session info data structure
        @type session_info: C{X2GoServerSessionInfo*}

        """
        if type(session_info) == type(self):
            for prop in ('graphics_port', 'snd_port', 'sshfs_port', 'tekictrl_port', 'tekidata_port', 'date_suspended', 'status', ):
                if hasattr(session_info, prop):
                    _new = getattr(session_info, prop)
                    _current = getattr(self, prop)
                    if _new != _current:
                        setattr(self, prop, _new)

    def __init__(self):
        """\
        Class constructor, identical to L{clear()} method. 

        """
        self.clear()


class X2GoServerSessionList(object):
    """\
    L{X2GoServerSessionList} is used to store all information
    that is retrieved from a connected X2Go server on a
    C{X2GoControlSession.list_sessions()} call.

    """
    def __init__(self, x2go_output=None, info_backend=X2GoServerSessionInfo):
        """\
        @param x2go_output: X2Go server's C{x2golistsessions} command output, each 
            session separated by a newline character. Session values are separated 
            by Unix Pipe Symbols ('|')
        @type x2go_output: str
        @param info_backend: the session info backend to use
        @type info_backend: C{X2GoServerSessionInfo*}

        """
        self.sessions = {}
        if x2go_output is not None:
            lines = x2go_output.split("\n")
            for line in lines:
                if not line:
                    continue
                s_info = info_backend()
                s_info._parse_x2golistsessions_line(line)
                self.sessions[s_info.name] = s_info

    def __call__(self):
        return self.sessions

    def set_sessions(self, sessions):
        """\
        Set the sessions property directly by parsing a complete data structure.

        """
        self.sessions = sessions

    def get_session_info(self, session_name):
        """\
        Retrieve the session information for C{<session_name>}.

        @param session_name: the queried session name
        @type session_name: C{str}

        @return: the session info of C{<session_name>}
        @rtype: C{X2GoServerSessionInfo*} or C{None}

        """
        try:
            return self.sessions[session_name]
        except KeyError:
            return None

    def get_session_with(self, property_name, value, hostname=None):
        """\
        Find session with a given display number on a given host.

        @param property_name: match a session based on this property name
        @type property_name: C{str}
        @param value: the resulting session has to match this value for C{<property_name>}
        @type value: C{str}
        @param hostname: the result has to match this hostname
        @type hostname: C{str}

        """
        if property_name == 'display':
            value = value.lstrip(':')
            if '.' in value: value = value.split('.')[0]

        for session in self.sessions.values():
            try:
                if str(getattr(session, property_name)) == str(value):
                    if hostname is None or session.hostname == hostname:
                        return session
            except AttributeError:
                pass
