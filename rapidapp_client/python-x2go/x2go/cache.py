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
X2GoListSessionCache class - caching X2Go session information.

"""
__NAME__ = 'x2gocache-pylib'

# modules
import copy
import gevent

# Python X2Go modules
import log
import x2go_exceptions

class X2GoListSessionsCache(object):
    """\
    For non-blocking operations in client applications using Python X2Go, it is
    recommended to enable the L{X2GoListSessionsCache}. This can be done by calling
    the constructor of the L{X2GoClient} class.

    The session list and desktop cache gets updated in regular intervals by a threaded
    L{X2GoSessionGuardian} instance. For the session list and desktop list update, the
    X2Go server commands C{x2golistsessions} and C{x2godesktopsessions} are called and
    the command's stdout is cached in the session list cache.

    Whenever your client application needs access to either the server's session list
    or the server's desktop list the session cache is queried instead. This assures that
    the server's session/desktop list is available without delay, even on slow internet
    connections.

    """
    x2go_listsessions_cache = {}

    def __init__(self, client_instance, logger=None, loglevel=log.loglevel_DEFAULT):
        """\
        @param client_instance: the L{X2GoClient} instance that uses this L{X2GoListSessionsCache}
        @type client_instance: C{obj}
        @param logger: you can pass an L{X2GoLogger} object to the L{X2GoListSessionsCache} constructor
        @type logger: C{obj}
        @param loglevel: if no L{X2GoLogger} object has been supplied a new one will be
            constructed with the given loglevel
        @type loglevel: C{int}

        """
        self.x2go_listsessions_cache = {}
        self.last_listsessions_cache = {}
        self.protected = False

        if logger is None:
            self.logger = log.X2GoLogger(loglevel=loglevel)
        else:
            self.logger = copy.deepcopy(logger)
        self.logger.tag = __NAME__

        self.client_instance = client_instance

    def delete(self, profile_name):
        """\
        Remove session list from cache for a given profile.

        @param profile_name: name of profile to operate on
        @type profile_name: C{str}

        """
        while self.protected:
            gevent.sleep(.1)
        try: del self.x2go_listsessions_cache[profile_name]
        except KeyError: pass

    def check_cache(self):
        """\
        Check if session list cache elements are still valid (i.e. if all corresponding
        session profiles are still connected). If not so, remove invalid cache entries from
        the session list cache.

        """
        for profile_name in self.x2go_listsessions_cache.keys():
            if profile_name not in self.client_instance.client_connected_profiles(return_profile_names=True):
                del self.x2go_listsessions_cache[profile_name]

    def update_all(self, update_sessions=True, update_desktops=False):
        """\
        Update L{X2GoListSessionsCache} for all connected session profiles.

        @param update_sessions: cache recent session lists from all connected servers
        @type update_sessions: C{bool}
        @param update_desktops: cache recent desktop lists from all connected servers
        @type update_desktops: C{bool}

        """
        for profile_name in self.client_instance.client_connected_profiles(return_profile_names=True):
            self.update(profile_name, update_sessions=update_sessions, update_desktops=update_desktops)

        self.check_cache()

    def update(self, profile_name, update_sessions=True, update_desktops=False, update_mounts=False):
        """\
        Update L{X2GoListSessionsCache} (i.e. session/desktops) for session profile C{profile_name}.

        @param profile_name: name of profile to update
        @type profile_name: C{str}
        @param update_sessions: cache recent session list from server
        @type update_sessions: C{bool}
        @param update_desktops: cache recent desktop list from server
        @type update_desktops: C{bool}
        @param update_mounts: cache list of client-side mounts on server
        @type update_mounts: C{bool}

        """
        self.protected = True
        self.last_listsessions_cache = copy.deepcopy(self.x2go_listsessions_cache)
        control_session = self.client_instance.client_control_session_of_profile_name(profile_name)
        if not self.x2go_listsessions_cache.has_key(profile_name):
            self.x2go_listsessions_cache[profile_name] = {'sessions': None, 'desktops': None, 'mounts': {}, }
        if update_sessions:
            self._update_sessions(profile_name, control_session)
        if update_desktops:
            self._update_desktops(profile_name, control_session)
        if update_mounts:
            self._update_mounts(profile_name, control_session)
        self.protected = False

    def _update_mounts(self, profile_name, control_session):
        """\
        Update mounts list of L{X2GoListSessionsCache} for session profile C{profile_name}.

        @param profile_name: name of profile to update
        @type profile_name: C{str}

        @raise X2GoControlSessionException: if the control session's C{list_mounts} method fails
        """
        try:
            self.x2go_listsessions_cache[profile_name]['mounts'] = {}
            if self.x2go_listsessions_cache[profile_name]['sessions']:
                for session_name in self.x2go_listsessions_cache[profile_name]['sessions']:
                    session = self.client_instance.get_session_of_session_name(session_name, return_object=True, match_profile_name=profile_name)
                    if session is not None and session.is_running():
                        if control_session is not None and not control_session.has_session_died():
                            self.x2go_listsessions_cache[profile_name]['mounts'].update(control_session.list_mounts(session_name))
        except (x2go_exceptions.X2GoControlSessionException, AttributeError), e:
            if profile_name in self.x2go_listsessions_cache.keys():
                del self.x2go_listsessions_cache[profile_name]
            self.protected = False
            raise x2go_exceptions.X2GoControlSessionException(str(e))
        except x2go_exceptions.X2GoTimeOutException:
            pass
        except KeyError:
            pass

    def _update_desktops(self, profile_name, control_session):
        """\
        Update session lists of L{X2GoListSessionsCache} for session profile C{profile_name}.

        @param profile_name: name of profile to update
        @type profile_name: C{str}
        @param control_session: X2Go control session instance
        @type control_session: C{obj}

        @raise X2GoControlSessionException: if the control session's C{list_desktop} method fails
        """
        try:
            if control_session is not None and not control_session.has_session_died():
                self.x2go_listsessions_cache[profile_name]['desktops'] = control_session.list_desktops()
        except (x2go_exceptions.X2GoControlSessionException, AttributeError), e:
            if profile_name in self.x2go_listsessions_cache.keys():
                del self.x2go_listsessions_cache[profile_name]
            self.protected = False
            raise x2go_exceptions.X2GoControlSessionException(str(e))
        except x2go_exceptions.X2GoTimeOutException:
            pass
        except KeyError:
            pass

    def _update_sessions(self, profile_name, control_session):
        """\
        Update desktop list of L{X2GoListSessionsCache} for session profile C{profile_name}.

        @param profile_name: name of profile to update
        @type profile_name: C{str}

        @raise X2GoControlSessionException: if the control session's C{list_sessions} method fails
        """
        try:
            if control_session is not None and not control_session.has_session_died():
                self.x2go_listsessions_cache[profile_name]['sessions'] = control_session.list_sessions()
        except (x2go_exceptions.X2GoControlSessionException, AttributeError), e:
            if profile_name in self.x2go_listsessions_cache.keys():
                del self.x2go_listsessions_cache[profile_name]
            self.protected = False
            raise x2go_exceptions.X2GoControlSessionException(str(e))
        except KeyError:
            pass

    def list_sessions(self, session_uuid):
        """\
        Retrieve a session list from the current cache content of L{X2GoListSessionsCache}
        for a given L{X2GoSession} instance (specified by its unique session UUID).

        @param session_uuid: unique identifier of session to query cache for
        @type session_uuid: C{str}

        @return: a data object containing available session information
        @rtype: C{X2GoServerSessionList*} instance (or C{None})

        """
        profile_name = self.client_instance.get_session_profile_name(session_uuid)
        if self.is_cached(session_uuid=session_uuid):
            return self.x2go_listsessions_cache[profile_name]['sessions']
        else:
            return None

    def list_desktops(self, session_uuid):
        """\
        Retrieve a list of available desktop sessions from the current cache content of
        L{X2GoListSessionsCache} for a given L{X2GoSession} instance (specified by its 
        unique session UUID).

        @param session_uuid: unique identifier of session to query cache for
        @type session_uuid: C{str}

        @return: a list of strings representing X2Go desktop sessions available for sharing
        @rtype: C{list} (or C{None})

        """
        profile_name = self.client_instance.get_session_profile_name(session_uuid)
        if self.is_cached(session_uuid=session_uuid):
            return self.x2go_listsessions_cache[profile_name]['desktops']
        else:
            return None

    def list_mounts(self, session_uuid):
        """\
        Retrieve a list of mounted client shares from the current cache content of
        L{X2GoListSessionsCache} for a given L{X2GoSession} instance (specified by its 
        unique session UUID).

        @param session_uuid: unique identifier of session to query cache for
        @type session_uuid: C{str}

        @return: a list of strings representing mounted client shares
        @rtype: C{list} (or C{None})

        """
        profile_name = self.client_instance.get_session_profile_name(session_uuid)
        if self.is_cached(session_uuid=session_uuid):
            return self.x2go_listsessions_cache[profile_name]['mounts']
        else:
            return None

    def is_cached(self, profile_name=None, session_uuid=None, cache_type=None):
        """\
        Check if session information is cached.

        @param profile_name: name of profile to update
        @type profile_name: C{str}
        @param session_uuid: unique identifier of session to query cache for
        @type session_uuid: C{str}

        @return: C{True} if session information is cached
        @rtype: C{bool}

        """
        if profile_name is None and session_uuid and self.client_instance:
            try:
                profile_name = self.client_instance.get_session_profile_name(session_uuid)
            except x2go_exceptions.X2GoSessionRegistryException:
                raise x2go_exceptions.X2GoSessionCacheException("requested session UUID is not valid anymore")
        _is_profile_cached = self.x2go_listsessions_cache.has_key(profile_name)
        _is_cache_type_cached = _is_profile_cached and self.x2go_listsessions_cache[profile_name].has_key(cache_type)
        if cache_type is None:
            return _is_profile_cached
        else:
            return _is_cache_type_cached
