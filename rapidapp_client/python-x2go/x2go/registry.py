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
X2GoSessionRegistry class - the X2GoClient's session registry backend

"""
__NAME__ = 'x2gosessregistry-pylib'

import os
import copy
import types
import time
import threading
import re

# Python X2Go modules
import log
import utils
import session
import x2go_exceptions

from defaults import LOCAL_HOME as _LOCAL_HOME
from defaults import X2GO_CLIENT_ROOTDIR as _X2GO_CLIENT_ROOTDIR
from defaults import X2GO_SESSIONS_ROOTDIR as _X2GO_SESSIONS_ROOTDIR
from defaults import X2GO_SESSIONPROFILE_DEFAULTS as _X2GO_SESSIONPROFILE_DEFAULTS
from defaults import X2GO_SSH_ROOTDIR as _X2GO_SSH_ROOTDIR

from defaults import BACKENDS as _BACKENDS


class X2GoSessionRegistry(object):
    """\
    This class is utilized by L{X2GoClient} instances to maintain a good overview on
    session status of all associated L{X2GoSession} instances.

    """
    def __init__(self, client_instance,
                 logger=None, loglevel=log.loglevel_DEFAULT):
        """\
        @param client_instance: the L{X2GoClient} instance that instantiated this L{X2GoSessionRegistry} instance.
        @type client_instance: L{X2GoClient} instance
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

        self.client_instance = client_instance

        self.registry = {}
        self.control_sessions = {}
        self.master_sessions = {}

        self._last_available_session_registration = None
        self._skip_auto_registration = False
        self._profile_locks = {}

    def keys(self):
        """\
        A list of session registry keys.

        @return: session registry key list
        @rtype: C{list}

        """
        return self.registry.keys()

    def __repr__(self):
        result = 'X2GoSessionRegistry('
        for p in dir(self):
            if '__' in p or not p in self.__dict__ or type(p) is types.InstanceType: continue
            result += p + '=' + str(self.__dict__[p]) + ','
        result = result.strip(',')
        return result + ')'

    def __call__(self, session_uuid):
        """\
        Returns the L{X2GoSession} instance for a given session UUID hash.

        @param session_uuid: the X2Go session's UUID registry hash
        @type session_uuid: C{str}

        @return: the corresponding L{X2GoSession} instance
        @rtype: L{X2GoSession} instance

        @raise X2GoSessionRegistryException: if the given session UUID could not be found

        """
        try:
            return self.registry[session_uuid]
        except KeyError:
            raise x2go_exceptions.X2GoSessionRegistryException('No session found for UUID %s' % session_uuid)

    def disable_session_auto_registration(self):
        """\
        This method is used to temporarily skip auto-registration of newly appearing
        X2Go session on the server side. This is necessary during session startups to
        assure that the session registry does not get filled with session UUID 
        duplicates.

        """
        self._skip_auto_registration = True

    def enable_session_auto_registration(self):
        """\
        This method is used to temporarily (re-)enable auto-registration of newly appearing
        X2Go session on the server side.

        """
        self._skip_auto_registration = False

    def forget(self, session_uuid):
        """\
        Forget the complete record for session UUID C{session_uuid}.

        @param session_uuid: the X2Go session's UUID registry hash
        @type session_uuid: C{str}

        """
        try:
            del self.registry[session_uuid]
            self.logger('Forgetting session UUID %s' % session_uuid, loglevel=log.loglevel_DEBUG)
        except KeyError:
            pass

    def get_profile_id(self, session_uuid):
        """\
        Retrieve the profile ID of a given session UUID hash.

        @param session_uuid: the X2Go session's UUID registry hash
        @type session_uuid: C{str}

        @return: profile ID
        @rtype: C{str}

        """
        return self(session_uuid).get_profile_id()

    def get_profile_name(self, session_uuid):
        """\
        Retrieve the profile name of a given session UUID hash.

        @param session_uuid: the X2Go session's UUID registry hash
        @type session_uuid: C{str}

        @return: profile name
        @rtype: C{str}

        """
        return self(session_uuid).get_profile_name()

    def session_summary(self, session_uuid, status_only=False):
        """\
        Compose a session summary (as Python dictionary).

        @param session_uuid: the X2Go session's UUID registry hash
        @type session_uuid: C{str}

        @return: session summary dictionary
        @rtype: C{dict}

        """
        _session_summary = {}
        _r = False
        if session_uuid in [ s() for s in self.registered_sessions() ]:
            _r = True

        if not status_only:
            _session_summary['uuid'] = _r and session_uuid or None
            _session_summary['profile_id'] = _r and self.get_profile_id(session_uuid) or ''
            _session_summary['profile_name'] = _r and self.get_profile_name(session_uuid) or ''
            _session_summary['session_name'] = _r and self(session_uuid).get_session_name() or ''
            _session_summary['control_session'] = _r and self(session_uuid).get_control_session() or None
            _session_summary['control_params'] = _r and self(session_uuid).control_params or {}
            _session_summary['terminal_session'] = _r and self(session_uuid).get_terminal_session() or None
            _session_summary['terminal_params'] = _r and self(session_uuid).terminal_params or {}
            _session_summary['active_threads'] = _r and bool(self(session_uuid).get_terminal_session()) and self(session_uuid).get_terminal_session().active_threads or []
            _session_summary['backends'] = {
                'control': _r and self(session_uuid).control_backend or None,
                'terminal': _r and self(session_uuid).terminal_backend or None,
                'info': _r and self(session_uuid).info_backend or None,
                'list': _r and self(session_uuid).list_backend or None,
                'proxy': _r and self(session_uuid).proxy_backend or None,
            }

        if _r:
            _session_summary['virgin'] = self(session_uuid).virgin
            _session_summary['connected'] = self(session_uuid).connected
            _session_summary['running'] = self(session_uuid).running
            _session_summary['suspended'] = self(session_uuid).suspended
            _session_summary['terminated'] = self(session_uuid).terminated
        else:
            _session_summary['virgin'] = None
            _session_summary['connected'] = None
            _session_summary['running'] = None
            _session_summary['suspended'] = None
            _session_summary['terminated'] = None
        return _session_summary

    def update_status(self, session_uuid=None, profile_name=None, profile_id=None, session_list=None, force_update=False, newly_connected=False):
        """\
        Update the session status for L{X2GoSession} that is represented by a given session UUID hash,
        profile name or profile ID.

        @param session_uuid: the X2Go session's UUID registry hash
        @type session_uuid: C{str}
        @param profile_name: alternatively, a profile name can be specified (the stati of all registered sessions for this session
            profile will be updated)
        @type profile_name: C{str}
        @param profile_id: alternatively, a profile ID can be given (the stati of all registered sessions for this session 
            profile will be updated)
        @type profile_id: C{str}
        @param session_list: an optional C{X2GoServerSessionList*} instance (as returned by the L{X2GoClient.list_sessions()} command can
            be passed to this method.
        @type session_list: C{X2GoServerSessionList*} instance
        @param force_update: make sure the session status gets really updated
        @type force_update: C{bool}

        @return: C{True} if this method has been successful
        @rtype: C{bool}

        @raise X2GoSessionRegistryException: if the combination of C{session_uuid}, C{profile_name} and C{profile_id} does not match the requirement: 
            only one of them

        """
        if session_uuid and profile_name or session_uuid and profile_id or profile_name and profile_id:
            raise x2go_exceptions.X2GoSessionRegistryException('only one of the possible method parameters is allowed (session_uuid, profile_name or profile_id)')
        elif session_uuid is None and profile_name is None and profile_id is None:
            raise x2go_exceptions.X2GoSessionRegistryException('at least one of the method parameters session_uuid, profile_name or profile_id must be given')

        if session_uuid:
            session_uuids = [ session_uuid ]
        elif profile_name:
            session_uuids = [ s() for s in self.registered_sessions_of_profile_name(profile_name, return_objects=True) ]
        elif profile_id:
            session_uuids = [ s() for s in self.registered_sessions_of_profile_name(self.client_instance.to_profile_name(profile_id), return_objects=True) ]

        for _session_uuid in session_uuids:

            # only operate on instantiated X2GoSession objects
            if type(self(_session_uuid)) != session.X2GoSession:
                continue

            if self(_session_uuid).is_locked():
                continue

            if not self(_session_uuid).update_status(session_list=session_list, force_update=force_update):
                # skip this run, as nothing has changed since the last time...
                continue

            _last_status = copy.deepcopy(self(_session_uuid)._last_status)
            _current_status = copy.deepcopy(self(_session_uuid)._current_status)

            # at this point we hook into the X2GoClient instance and call notification methods
            # that can be used to inform an application that something has happened

            _profile_name = self(_session_uuid).get_profile_name()
            _session_name = self(_session_uuid).get_session_name()

            if self(_session_uuid).get_server_hostname() != _current_status['server']:

                # if the server (hostname) has changed due to a configuration change we skip all notifications
                self(_session_uuid).session_cleanup()
                self(_session_uuid).__del__()
                if len(self.virgin_sessions_of_profile_name(profile_name)) > 1:
                    del self.registry[_session_uuid]

            elif not _last_status['running'] and _current_status['running'] and not _current_status['faulty']:
                # session has started
                if newly_connected:
                    # from a suspended state
                    self.client_instance.HOOK_on_found_session_running_after_connect(session_uuid=_session_uuid, profile_name=_profile_name, session_name=_session_name)
                else:
                    # explicitly ask for the terminal_session object directly here, so we also get 'PENDING' terminal sessions here...
                    if self(_session_uuid).terminal_session:

                        # declare as master session if appropriate
                        if _profile_name not in self.master_sessions.keys():
                            self.master_sessions[_profile_name] = self(_session_uuid)
                            self(_session_uuid).set_master_session()

                        elif (not self.master_sessions[_profile_name].is_desktop_session() and self(_session_uuid).is_desktop_session()) or \
                             (not self.master_sessions[_profile_name].is_desktop_session() and self(_session_uuid).is_published_applications_provider()):
                                self(self.master_sessions[_profile_name]()).unset_master_session()
                                self.master_sessions[_profile_name] = self(_session_uuid)
                                self(_session_uuid).set_master_session()

                        if _last_status['suspended']:
                            # from a suspended state
                            self.client_instance.HOOK_on_session_has_resumed_by_me(session_uuid=_session_uuid, profile_name=_profile_name, session_name=_session_name)
                        elif _last_status['virgin']:
                            # as a new session
                            self.client_instance.HOOK_on_session_has_started_by_me(session_uuid=_session_uuid, profile_name=_profile_name, session_name=_session_name)

                    else:
                        if _last_status['suspended']:
                            # from a suspended state
                            self.client_instance.HOOK_on_session_has_resumed_by_other(session_uuid=_session_uuid, profile_name=_profile_name, session_name=_session_name)
                        elif _last_status['connected'] and _last_status['virgin']:
                            # as a new session, do not report directly after connect due to many false positives then...
                            self.client_instance.HOOK_on_session_has_started_by_other(session_uuid=_session_uuid, profile_name=_profile_name, session_name=_session_name)

            elif _last_status['connected'] and (not _last_status['suspended'] and _current_status['suspended']) and not _current_status['faulty'] and _session_name:

                # unregister as master session
                if _profile_name in self.master_sessions.keys():
                    if self.master_sessions[_profile_name] == self(_session_uuid):

                        self(_session_uuid).unset_master_session()
                        del self.master_sessions[_profile_name]

                # session has been suspended
                self(_session_uuid).session_cleanup()
                self.client_instance.HOOK_on_session_has_been_suspended(session_uuid=_session_uuid, profile_name=_profile_name, session_name=_session_name)

            elif _last_status['connected'] and (not _last_status['terminated'] and _current_status['terminated']) and not _current_status['faulty'] and _session_name:

                # unregister as master session
                if _profile_name in self.master_sessions.keys():
                    if self.master_sessions[_profile_name] == self(_session_uuid):

                        self(_session_uuid).unset_master_session()
                        del self.master_sessions[_profile_name]

                # session has terminated
                self.client_instance.HOOK_on_session_has_terminated(session_uuid=_session_uuid, profile_name=_profile_name, session_name=_session_name)
                try: self(_session_uuid).session_cleanup()
                except x2go_exceptions.X2GoSessionException: pass
                try: self(_session_uuid).__del__()
                except x2go_exceptions.X2GoSessionException: pass
                if len(self.virgin_sessions_of_profile_name(profile_name)) > 1:
                    self.forget(_session_uuid)

        # detect master sessions for connected profiles that have lost (suspend/terminate) their master session or never had a master session
        for _profile_name in [ p for p in self.connected_profiles(return_profile_names=True) if p not in self.master_sessions.keys() ]:
            _running_associated_sessions = [ _s for _s in self.running_sessions_of_profile_name(_profile_name, return_objects=True) if _s.is_associated() ]
            if _running_associated_sessions:
                for _r_a_s in _running_associated_sessions:
                    if _r_a_s.is_desktop_session():
                        self.master_sessions[_profile_name] = _r_a_s
                        _r_a_s.set_master_session(wait=1)
                        break
                if not self.master_sessions.has_key(_profile_name):
                    _pubapp_associated_sessions = self.pubapp_sessions_of_profile_name(_profile_name, return_objects=True)
                    if _pubapp_associated_sessions:
                        self.master_sessions[_profile_name] = _pubapp_associated_sessions[0]
                        _pubapp_associated_sessions[0].set_master_session(wait=2)
                    else:
                        self.master_sessions[_profile_name] = _running_associated_sessions[0]
                        _running_associated_sessions[0].set_master_session(wait=2)

        return True

    def register_available_server_sessions(self, profile_name, session_list=None, newly_connected=False, re_register=False, skip_pubapp_sessions=False):
        """\
        Register server-side available X2Go sessions with this L{X2GoSessionRegistry} instance for a given profile name.

        @param profile_name: session profile name to register available X2Go sessions for
        @type profile_name: C{str}
        @param session_list: an optional C{X2GoServerSessionList*} instance (as returned by the L{X2GoClient.list_sessions()} command can
            be passed to this method.
        @type session_list: C{X2GoServerSessionList*} instance
        @param newly_connected: give a hint that the session profile got newly connected
        @type newly_connected: C{bool}
        @param re_register: re-register available sessions, needs to be done after changes to the session profile
        @type re_register: C{bool}
        @param skip_pubapp_sessions: Do not register published applications sessions
        @type skip_pubapp_sessions: C{bool}

        """
        if self._last_available_session_registration is not None:
            _now = time.time()
            _time_delta = _now - self._last_available_session_registration
            if _time_delta < 2 and not re_register:
                self.logger('registration interval too short (%s), skipping automatic session registration...' % _time_delta, loglevel=log.loglevel_DEBUG)
                return
            self._last_available_session_registration = _now

        _connected_sessions = self.connected_sessions_of_profile_name(profile_name=profile_name, return_objects=False)
        _registered_sessions = self.registered_sessions_of_profile_name(profile_name=profile_name, return_objects=False)
        _session_names = [ self(s_uuid).session_name for s_uuid in _registered_sessions if self(s_uuid).session_name is not None ]

        if _connected_sessions:
            # any of the connected sessions is valuable for accessing the profile's control 
            # session commands, so we simply take the first that comes in...
            _ctrl_session = self(_connected_sessions[0])

            if session_list is None:
                session_list = _ctrl_session.list_sessions()

            # make sure the session registry gets updated before registering new session
            # (if the server name has changed, this will kick out obsolete X2GoSessions)
            self.update_status(profile_name=profile_name, session_list=session_list, force_update=True)
            for session_name in session_list.keys():
                if (session_name not in _session_names and not self._skip_auto_registration) or re_register:
                    server = _ctrl_session.get_server_hostname()
                    profile_id = _ctrl_session.get_profile_id()

                    # reconstruct all session options of _ctrl_session to auto-register a suspended session
                    # found on the _ctrl_session's connected server
                    _clone_kwargs = _ctrl_session.__dict__
                    kwargs = {}
                    kwargs.update(self.client_instance.session_profiles.to_session_params(profile_id))
                    kwargs['client_instance'] = self.client_instance
                    kwargs['control_backend'] = _clone_kwargs['control_backend']
                    kwargs['terminal_backend'] = _clone_kwargs['terminal_backend']
                    kwargs['proxy_backend'] = _clone_kwargs['proxy_backend']
                    kwargs['info_backend'] = _clone_kwargs['info_backend']
                    kwargs['list_backend'] = _clone_kwargs['list_backend']
                    kwargs['settings_backend'] = _clone_kwargs['settings_backend']
                    kwargs['printing_backend'] = _clone_kwargs['printing_backend']
                    kwargs['keep_controlsession_alive'] = _clone_kwargs['keep_controlsession_alive']
                    kwargs['client_rootdir'] = _clone_kwargs['client_rootdir']
                    kwargs['sessions_rootdir'] = _clone_kwargs['sessions_rootdir']

                    try: del kwargs['server'] 
                    except: pass
                    try: del kwargs['profile_name']
                    except: pass
                    try: del kwargs['profile_id'] 
                    except: pass

                    # this if clause catches problems when x2golistsessions commands give weird results
                    if not self.has_session_of_session_name(session_name) or re_register:
                        if not (skip_pubapp_sessions and re.match('.*_stRPUBLISHED_.*', session_name)):
                            session_uuid = self.register(server, profile_id, profile_name,
                                                         session_name=session_name, virgin=False,
                                                         **kwargs
                                                        )
                            self(session_uuid).connected = True
                            self.update_status(session_uuid=session_uuid, force_update=True, newly_connected=newly_connected)

    def register(self, server, profile_id, profile_name,
                 session_name=None,
                 control_backend=_BACKENDS['X2GoControlSession']['default'],
                 terminal_backend=_BACKENDS['X2GoTerminalSession']['default'],
                 info_backend=_BACKENDS['X2GoServerSessionInfo']['default'],
                 list_backend=_BACKENDS['X2GoServerSessionList']['default'],
                 proxy_backend=_BACKENDS['X2GoProxy']['default'],
                 settings_backend=_BACKENDS['X2GoClientSettings']['default'],
                 printing_backend=_BACKENDS['X2GoClientPrinting']['default'],
                 client_rootdir=os.path.join(_LOCAL_HOME,_X2GO_CLIENT_ROOTDIR),
                 sessions_rootdir=os.path.join(_LOCAL_HOME,_X2GO_SESSIONS_ROOTDIR),
                 ssh_rootdir=os.path.join(_LOCAL_HOME,_X2GO_SSH_ROOTDIR),
                 keep_controlsession_alive=True,
                 add_to_known_hosts=False,
                 known_hosts=None,
                 **kwargs):
        """\
        Register a new L{X2GoSession} instance with this L{X2GoSessionRegistry}.

        @param server: hostname of X2Go server
        @type server: C{str}
        @param profile_id: profile ID
        @type profile_id: C{str}
        @param profile_name: profile name
        @type profile_name: C{str}
        @param session_name: session name (if available)
        @type session_name: C{str}
        @param control_backend: X2Go control session backend to use
        @type control_backend: C{str}
        @param terminal_backend: X2Go terminal session backend to use
        @type terminal_backend: C{str}
        @param info_backend: X2Go session info backend to use
        @type info_backend: C{str}
        @param list_backend: X2Go session list backend to use
        @type list_backend: C{str}
        @param proxy_backend: X2Go proxy backend to use
        @type proxy_backend: C{str}
        @param settings_backend: X2Go client settings backend to use
        @type settings_backend: C{str}
        @param printing_backend: X2Go client printing backend to use
        @type printing_backend: C{str}
        @param client_rootdir: client base dir (default: ~/.x2goclient)
        @type client_rootdir: C{str}
        @param sessions_rootdir: sessions base dir (default: ~/.x2go)
        @type sessions_rootdir: C{str}
        @param ssh_rootdir: ssh base dir (default: ~/.ssh)
        @type ssh_rootdir: C{str}
        @param keep_controlsession_alive: On last L{X2GoSession.disconnect()} keep the associated C{X2GoControlSession} instance alive?
        @ŧype keep_controlsession_alive: C{bool}
        @param add_to_known_hosts: Auto-accept server host validity?
        @type add_to_known_hosts: C{bool}
        @param known_hosts: the underlying Paramiko/SSH systems C{known_hosts} file
        @type known_hosts: C{str}
        @param kwargs: all other options will be passed on to the constructor of the to-be-instantiated L{X2GoSession} instance
        @type C{dict}

        @return: the session UUID of the newly registered (or re-registered) session
        @rtype: C{str}

        """
        if profile_id not in self._profile_locks.keys():
            self._profile_locks[profile_id] = threading.Lock()

        self._profile_locks[profile_id].acquire()

        control_session = None
        if profile_id in self.control_sessions.keys():
            control_session = self.control_sessions[profile_id]

        try:
            _params = self.client_instance.session_profiles.to_session_params(profile_id)

        except x2go_exceptions.X2GoProfileException:
            _params = utils._convert_SessionProfileOptions_2_SessionParams(_X2GO_SESSIONPROFILE_DEFAULTS)

        for _k in _params.keys():
            if _k in kwargs.keys():
                _params[_k] = kwargs[_k]

        # allow injection of PKey objects (Paramiko's private SSH keys)
        if kwargs.has_key('pkey'):
            _params['pkey'] = kwargs['pkey']
        if kwargs.has_key('sshproxy_pkey'):
            _params['sshproxy_pkey'] = kwargs['sshproxy_pkey']

        # when starting a new session, we will try to use unused registered virgin sessions
        # depending on your application layout, there should either be one or no such virgin session at all
        _virgin_sessions = [ s for s in self.virgin_sessions_of_profile_name(profile_name, return_objects=True) if not s.activated ]
        if _virgin_sessions and not session_name:
            session_uuid = _virgin_sessions[0].get_uuid()
            self(session_uuid).activated = True
            self.logger('using already initially-registered yet-unused session %s' % session_uuid, loglevel=log.loglevel_NOTICE)

        else:
            session_uuid = self.get_session_of_session_name(session_name, match_profile_name=profile_name)
            if session_uuid is not None: self.logger('using already registered-by-session-name session %s' % session_uuid, loglevel=log.loglevel_NOTICE)

        if session_uuid is not None:
            self(session_uuid).activated = True
            self(session_uuid).update_params(_params)
            self(session_uuid).set_server(server)
            self(session_uuid).set_profile_name(profile_name)
            self._profile_locks[profile_id].release()
            return session_uuid

        try: del _params['server'] 
        except: pass
        try: del _params['profile_name']
        except: pass
        try: del _params['profile_id'] 
        except: pass

        s = session.X2GoSession(server=server, control_session=control_session,
                                profile_id=profile_id, profile_name=profile_name,
                                session_name=session_name,
                                control_backend=control_backend,
                                terminal_backend=terminal_backend,
                                info_backend=info_backend,
                                list_backend=list_backend,
                                proxy_backend=proxy_backend,
                                settings_backend=settings_backend,
                                printing_backend=printing_backend,
                                client_rootdir=client_rootdir,
                                sessions_rootdir=sessions_rootdir,
                                ssh_rootdir=ssh_rootdir,
                                keep_controlsession_alive=keep_controlsession_alive,
                                add_to_known_hosts=add_to_known_hosts,
                                known_hosts=known_hosts,
                                client_instance=self.client_instance,
                                logger=self.logger, **_params)

        session_uuid = s._X2GoSession__get_uuid()
        self.logger('registering X2Go session %s...' % profile_name, log.loglevel_NOTICE)
        self.logger('registering X2Go session with UUID %s' % session_uuid, log.loglevel_DEBUG)

        self.registry[session_uuid] = s
        if profile_id not in self.control_sessions.keys():
            self.control_sessions[profile_id] = s.get_control_session()

        # make sure a new session is a non-master session unless promoted in update_status method
        self(session_uuid).unset_master_session()
        if control_session is None:
            self(session_uuid).do_auto_connect()

        self._profile_locks[profile_id].release()
        return session_uuid

    def has_session_of_session_name(self, session_name, match_profile_name=None):
        """\
        Detect if we know about an L{X2GoSession} of name C{<session_name>}.

        @param session_name: name of session to be searched for
        @type session_name: C{str}
        @param match_profile_name: a session's profile_name must match this profile name
        @type match_profile_name: C{str}

        @return: C{True} if a session of C{<session_name>} has been found
        @rtype: C{bool}

        """
        return bool(self.get_session_of_session_name(session_name, match_profile_name=match_profile_name))

    def get_session_of_session_name(self, session_name, return_object=False, match_profile_name=None):
        """\
        Retrieve the L{X2GoSession} instance with session name C{<session_name>}.

        @param session_name: name of session to be retrieved
        @type session_name: C{str}
        @param return_object: if C{False} the session UUID hash will be returned, if C{True} the L{X2GoSession} instance will be returned
        @type return_object: C{bool}
        @param match_profile_name: returned sessions must match this profile name
        @type match_profile_name: C{str}

        @return: L{X2GoSession} object or its representing session UUID hash
        @rtype: L{X2GoSession} instance or C{str}

        @raise X2GoSessionRegistryException: if there is more than one L{X2GoSession} registered for C{<session_name>} within
            the same L{X2GoClient} instance. This should never happen!

        """
        if match_profile_name is None:
            reg_sessions = self.registered_sessions()
        else:
            reg_sessions = self.registered_sessions_of_profile_name(match_profile_name)
        found_sessions = [ s for s in reg_sessions if s.session_name == session_name and s.session_name is not None ]
        if len(found_sessions) == 1:
            session = found_sessions[0]
            if return_object:
                return session
            else:
                return session.get_uuid()
        elif len(found_sessions) > 1:
            raise x2go_exceptions.X2GoSessionRegistryException('there should only be one registered session of name ,,%s\'\'' % session_name)
        else:
            return None

    def _sessionsWithState(self, state, return_objects=True, return_profile_names=False, return_profile_ids=False, return_session_names=False):
        if state == 'associated':
            sessions = [ ts for ts in self.registry.values() if ts.has_terminal_session() ]
        elif state == 'registered':
            sessions = [ ts for ts in self.registry.values() ]
        else:
            sessions = [ ts for ts in self.registry.values() if eval('ts.%s' % state) ]
        if return_profile_names:
            profile_names = []
            for this_session in sessions:
                if this_session.profile_name and this_session.profile_name not in profile_names:
                    profile_names.append(this_session.profile_name)
            return profile_names
        elif return_profile_ids:
            profile_ids = []
            for this_session in sessions:
                if this_session.profile_id and this_session.profile_id not in profile_ids:
                    profile_ids.append(this_session.profile_id)
            return profile_ids
        elif return_session_names:
            session_names = []
            for this_session in sessions:
                if this_session.session_name and this_session.session_name not in session_names:
                    session_names.append(this_session.session_name)
            return session_names
        elif return_objects:
            return sessions
        else:
            return [s.get_uuid() for s in sessions ]

    def connected_sessions(self, return_objects=True, return_profile_names=False, return_profile_ids=False, return_session_names=False):
        """\
        Retrieve a list of sessions that the underlying L{X2GoClient} instances is currently connected to.
        If none of the C{return_*} options is specified a list of session UUID hashes will be returned.

        @param return_objects: return as list of L{X2GoSession} instances
        @type return_objects: C{bool}
        @param return_profile_names: return as list of profile names
        @type return_profile_names: C{bool}
        @param return_profile_ids: return as list of profile IDs
        @type return_profile_ids: C{bool}
        @param return_session_names: return as list of X2Go session names
        @type return_session_names: C{bool}

        @return: a session list (as UUID hashes, objects, profile names/IDs or session names)
        @rtype: C{list}

        """
        return self._sessionsWithState('connected', return_objects=return_objects, return_profile_names=return_profile_names, return_profile_ids=return_profile_ids, return_session_names=return_session_names)

    def associated_sessions(self, return_objects=True, return_profile_names=False, return_profile_ids=False, return_session_names=False):
        """\
        Retrieve a list of sessions that are currently associated by an C{X2GoTerminalSession*} to the underlying L{X2GoClient} instance.
        If none of the C{return_*} options is specified a list of session UUID hashes will be returned.

        @param return_objects: return as list of L{X2GoSession} instances
        @type return_objects: C{bool}
        @param return_profile_names: return as list of profile names
        @type return_profile_names: C{bool}
        @param return_profile_ids: return as list of profile IDs
        @type return_profile_ids: C{bool}
        @param return_session_names: return as list of X2Go session names
        @type return_session_names: C{bool}

        @return: a session list (as UUID hashes, objects, profile names/IDs or session names)
        @rtype: C{list}

        """
        return self._sessionsWithState('associated', return_objects=return_objects, return_profile_names=return_profile_names, return_profile_ids=return_profile_ids, return_session_names=return_session_names)

    def virgin_sessions(self, return_objects=True, return_profile_names=False, return_profile_ids=False, return_session_names=False):
        """\
        Retrieve a list of sessions that are currently still in virgin state (not yet connected, associated etc.).
        If none of the C{return_*} options is specified a list of session UUID hashes will be returned.

        @param return_objects: return as list of L{X2GoSession} instances
        @type return_objects: C{bool}
        @param return_profile_names: return as list of profile names
        @type return_profile_names: C{bool}
        @param return_profile_ids: return as list of profile IDs
        @type return_profile_ids: C{bool}
        @param return_session_names: return as list of X2Go session names
        @type return_session_names: C{bool}

        @return: a session list (as UUID hashes, objects, profile names/IDs or session names)
        @rtype: C{list}

        """
        return self._sessionsWithState('virgin', return_objects=return_objects, return_profile_names=return_profile_names, return_profile_ids=return_profile_ids, return_session_names=return_session_names)

    def running_sessions(self, return_objects=True, return_profile_names=False, return_profile_ids=False, return_session_names=False):
        """\
        Retrieve a list of sessions that are currently in running state.
        If none of the C{return_*} options is specified a list of session UUID hashes will be returned.

        @param return_objects: return as list of L{X2GoSession} instances
        @type return_objects: C{bool}
        @param return_profile_names: return as list of profile names
        @type return_profile_names: C{bool}
        @param return_profile_ids: return as list of profile IDs
        @type return_profile_ids: C{bool}
        @param return_session_names: return as list of X2Go session names
        @type return_session_names: C{bool}

        @return: a session list (as UUID hashes, objects, profile names/IDs or session names)
        @rtype: C{list}

        """
        return self._sessionsWithState('running', return_objects=return_objects, return_profile_names=return_profile_names, return_profile_ids=return_profile_ids, return_session_names=return_session_names)

    def suspended_sessions(self, return_objects=True, return_profile_names=False, return_profile_ids=False, return_session_names=False):
        """\
        Retrieve a list of sessions that are currently in suspended state.
        If none of the C{return_*} options is specified a list of session UUID hashes will be returned.

        @param return_objects: return as list of L{X2GoSession} instances
        @type return_objects: C{bool}
        @param return_profile_names: return as list of profile names
        @type return_profile_names: C{bool}
        @param return_profile_ids: return as list of profile IDs
        @type return_profile_ids: C{bool}
        @param return_session_names: return as list of X2Go session names
        @type return_session_names: C{bool}

        @return: a session list (as UUID hashes, objects, profile names/IDs or session names)
        @rtype: C{list}

        """
        return self._sessionsWithState('suspended', return_objects=return_objects, return_profile_names=return_profile_names, return_profile_ids=return_profile_ids, return_session_names=return_session_names)

    def terminated_sessions(self, return_objects=True, return_profile_names=False, return_profile_ids=False, return_session_names=False):
        """\
        Retrieve a list of sessions that have terminated recently.
        If none of the C{return_*} options is specified a list of session UUID hashes will be returned.

        @param return_objects: return as list of L{X2GoSession} instances
        @type return_objects: C{bool}
        @param return_profile_names: return as list of profile names
        @type return_profile_names: C{bool}
        @param return_profile_ids: return as list of profile IDs
        @type return_profile_ids: C{bool}
        @param return_session_names: return as list of X2Go session names
        @type return_session_names: C{bool}

        @return: a session list (as UUID hashes, objects, profile names/IDs or session names)
        @rtype: C{list}

        """
        return self._sessionsWithState('terminated', return_objects=return_objects, return_profile_names=return_profile_names, return_profile_ids=return_profile_ids, return_session_names=return_session_names)

    @property
    def has_running_sessions(self):
        """\
        Equals C{True} if the underlying L{X2GoClient} instance has any running sessions at hand.

        """
        return self.running_sessions() and len(self.running_sessions()) > 0

    @property
    def has_suspended_sessions(self):
        """\
        Equals C{True} if the underlying L{X2GoClient} instance has any suspended sessions at hand.

        """
        return self.suspended_sessions and len(self.suspended_sessions) > 0

    def registered_sessions(self, return_objects=True, return_profile_names=False, return_profile_ids=False, return_session_names=False):
        """\
        Retrieve a list of all registered sessions.
        If none of the C{return_*} options is specified a list of session UUID hashes will be returned.

        @param return_objects: return as list of L{X2GoSession} instances
        @type return_objects: C{bool}
        @param return_profile_names: return as list of profile names
        @type return_profile_names: C{bool}
        @param return_profile_ids: return as list of profile IDs
        @type return_profile_ids: C{bool}
        @param return_session_names: return as list of X2Go session names
        @type return_session_names: C{bool}

        @return: a session list (as UUID hashes, objects, profile names/IDs or session names)
        @rtype: C{list}

        """
        return self._sessionsWithState('registered', return_objects=return_objects, return_profile_names=return_profile_names, return_profile_ids=return_profile_ids, return_session_names=return_session_names)

    def non_running_sessions(self, return_objects=True, return_profile_names=False, return_profile_ids=False, return_session_names=False):
        """\
        Retrieve a list of sessions that are currently _NOT_ in running state.
        If none of the C{return_*} options is specified a list of session UUID hashes will be returned.

        @param return_objects: return as list of L{X2GoSession} instances
        @type return_objects: C{bool}
        @param return_profile_names: return as list of profile names
        @type return_profile_names: C{bool}
        @param return_profile_ids: return as list of profile IDs
        @type return_profile_ids: C{bool}
        @param return_session_names: return as list of X2Go session names
        @type return_session_names: C{bool}

        @return: a session list (as UUID hashes, objects, profile names/IDs or session names)
        @rtype: C{list}

        """
        return [ s for s in self.registered_sessions(return_objects=return_objects, return_profile_names=return_profile_names, return_profile_ids=return_profile_ids, return_session_names=return_session_names) if s not in self.running_sessions(return_objects=return_objects, return_profile_names=return_profile_names, return_profile_ids=return_profile_ids, return_session_names=return_session_names) ]

    def connected_sessions_of_profile_name(self, profile_name, return_objects=True, return_session_names=False):
        """\
        For a given session profile name retrieve a list of sessions that are currently connected to the profile's X2Go server.
        If none of the C{return_*} options is specified a list of session UUID hashes will be returned.

        @param profile_name: session profile name
        @type profile_name: C{str}
        @param return_objects: return as list of L{X2GoSession} instances
        @type return_objects: C{bool}
        @param return_session_names: return as list of X2Go session names
        @type return_session_names: C{bool}

        @return: a session list (as UUID hashes, objects or session names)
        @rtype: C{list}

        """
        if return_objects:
            return self.connected_sessions() and [ s for s in self.connected_sessions() if s.get_profile_name() == profile_name ]
        elif return_session_names:
            return self.connected_sessions() and [ s.session_name for s in self.connected_sessions() if s.get_profile_name() == profile_name ]
        else:
            return self.connected_sessions() and [ s.get_uuid() for s in self.connected_sessions() if s.get_profile_name() == profile_name ]

    def associated_sessions_of_profile_name(self, profile_name, return_objects=True, return_session_names=False):
        """\
        For a given session profile name retrieve a list of sessions that are currently associated by an C{X2GoTerminalSession*} to this L{X2GoClient} instance.
        If none of the C{return_*} options is specified a list of session UUID hashes will be returned.

        @param profile_name: session profile name
        @type profile_name: C{str}
        @param return_objects: return as list of L{X2GoSession} instances
        @type return_objects: C{bool}
        @param return_session_names: return as list of X2Go session names
        @type return_session_names: C{bool}

        @return: a session list (as UUID hashes, objects or session names)
        @rtype: C{list}

        """
        if return_objects:
            return self.associated_sessions() and [ s for s in self.associated_sessions() if s.get_profile_name() == profile_name ]
        elif return_session_names:
            return self.associated_sessions() and [ s.session_name for s in self.associated_sessions() if s.get_profile_name() == profile_name ]
        else:
            return self.associated_sessions() and [ s.get_uuid() for s in self.associated_sessions() if s.get_profile_name() == profile_name ]

    def pubapp_sessions_of_profile_name(self, profile_name, return_objects=True, return_session_names=False):
        """\
        For a given session profile name retrieve a list of sessions that can be providers for published application list.
        If none of the C{return_*} options is specified a list of session UUID hashes will be returned.

        @param profile_name: session profile name
        @type profile_name: C{str}
        @param return_objects: return as list of L{X2GoSession} instances
        @type return_objects: C{bool}
        @param return_session_names: return as list of X2Go session names
        @type return_session_names: C{bool}

        @return: a session list (as UUID hashes, objects or session names)
        @rtype: C{list}

        """
        if return_objects:
            return self.associated_sessions_of_profile_name(profile_name) and [ s for s in self.associated_sessions_of_profile_name(profile_name) if s.is_published_applications_provider() ]
        elif return_session_names:
            return self.associated_sessions_of_profile_name(profile_name) and [ s.session_name for s in self.associated_sessions_of_profile_name(profile_name) if s.is_published_applications_provider() ]
        else:
            return self.associated_sessions_of_profile_name(profile_name) and [ s.get_uuid() for s in self.associated_sessions_of_profile_name(profile_name) if s.is_published_applications_provider() ]

    def registered_sessions_of_profile_name(self, profile_name, return_objects=True, return_session_names=False):
        """\
        For a given session profile name retrieve a list of sessions that are currently registered with this L{X2GoClient} instance.
        If none of the C{return_*} options is specified a list of session UUID hashes will be returned.

        @param profile_name: session profile name
        @type profile_name: C{str}
        @param return_objects: return as list of L{X2GoSession} instances
        @type return_objects: C{bool}
        @param return_session_names: return as list of X2Go session names
        @type return_session_names: C{bool}

        @return: a session list (as UUID hashes, objects or session names)
        @rtype: C{list}

        """
        if return_objects:
            return self.registered_sessions() and [ s for s in self.registered_sessions() if s.get_profile_name() == profile_name ]
        elif return_session_names:
            return self.registered_sessions() and [ s.session_name for s in self.registered_sessions() if s.get_profile_name() == profile_name ]
        else:
            return self.registered_sessions() and [ s.get_uuid() for s in self.registered_sessions() if s.get_profile_name() == profile_name ]

    def virgin_sessions_of_profile_name(self, profile_name, return_objects=True, return_session_names=False):
        """\
        For a given session profile name retrieve a list of sessions that are registered with this L{X2GoClient} instance but have not
        yet been started (i.e. sessions that are in virgin state). If none of the C{return_*} options is specified a list of 
        session UUID hashes will be returned.

        @param profile_name: session profile name
        @type profile_name: C{str}
        @param return_objects: return as list of L{X2GoSession} instances
        @type return_objects: C{bool}
        @param return_session_names: return as list of X2Go session names
        @type return_session_names: C{bool}

        @return: a session list (as UUID hashes, objects or session names)
        @rtype: C{list}

        """
        if return_objects:
            return self.virgin_sessions() and [ s for s in self.virgin_sessions() if s.get_profile_name() == profile_name ]
        elif return_session_names:
            return self.virgin_sessions() and [ s.session_name for s in self.virgin_sessions() if s.get_profile_name() == profile_name ]
        else:
            return self.virgin_sessions() and [ s.get_uuid() for s in self.virgin_sessions() if s.get_profile_name() == profile_name ]

    def running_sessions_of_profile_name(self, profile_name, return_objects=True, return_session_names=False):
        """\
        For a given session profile name retrieve a list of sessions that are currently running.
        If none of the C{return_*} options is specified a list of session UUID hashes will be returned.

        @param profile_name: session profile name
        @type profile_name: C{str}
        @param return_objects: return as list of L{X2GoSession} instances
        @type return_objects: C{bool}
        @param return_session_names: return as list of X2Go session names
        @type return_session_names: C{bool}

        @return: a session list (as UUID hashes, objects or session names)
        @rtype: C{list}

        """
        if return_objects:
            return self.running_sessions() and [ s for s in self.running_sessions() if s.get_profile_name() == profile_name ]
        elif return_session_names:
            return self.running_sessions() and [ s.session_name for s in self.running_sessions() if s.get_profile_name() == profile_name ]
        else:
            return self.running_sessions() and [ s.get_uuid() for s in self.running_sessions() if s.get_profile_name() == profile_name ]

    def suspended_sessions_of_profile_name(self, profile_name, return_objects=True, return_session_names=False):
        """\
        For a given session profile name retrieve a list of sessions that are currently in suspended state.
        If none of the C{return_*} options is specified a list of session UUID hashes will be returned.

        @param profile_name: session profile name
        @type profile_name: C{str}
        @param return_objects: return as list of L{X2GoSession} instances
        @type return_objects: C{bool}
        @param return_session_names: return as list of X2Go session names
        @type return_session_names: C{bool}

        @return: a session list (as UUID hashes, objects or session names)
        @rtype: C{list}

        """
        if return_objects:
            return self.suspended_sessions() and [ s for s in self.suspended_sessions() if s.get_profile_name() == profile_name ]
        elif return_session_names:
            return self.suspended_sessions() and [ s.session_name for s in self.suspended_sessions() if s.get_profile_name() == profile_name ]
        else:
            return self.suspended_sessions() and [ s.get_uuid() for s in self.suspended_sessions() if s.get_profile_name() == profile_name ]

    def control_session_of_profile_name(self, profile_name):
        """\
        For a given session profile name retrieve a the corresponding C{X2GoControlSession*} instance.

        @param profile_name: session profile name
        @type profile_name: C{str}

        @return: contol session instance
        @rtype: C{X2GoControlSession*} instance

        """
        _sessions = self.registered_sessions_of_profile_name(profile_name, return_objects=True)
        if _sessions:
            session = _sessions[0]
            return session.control_session
        return None

    @property
    def connected_control_sessions(self):
        """\
        Equals a list of all currently connected control sessions.

        """
        return [ c for c in self.control_sessions.values() if c.is_connected() ]

    def connected_profiles(self, use_paramiko=False, return_profile_ids=True, return_profile_names=False):
        """\
        Retrieve a list of all currently connected session profiles.

        @param use_paramiko: send query directly to the Paramiko/SSH layer
        @type use_paramiko: C{bool}

        @return: list of connected session profiles
        @rtype: C{list}

        """
        if use_paramiko:
            return [ p for p in self.control_sessions.keys() if self.control_sessions[p].is_connected() ]
        else:
            return self.connected_sessions(return_profile_ids=return_profile_ids, return_profile_names=return_profile_names)

    def get_master_session(self, profile_name, return_object=True, return_session_name=False):
        """\
        Retrieve the master session of a specific profile.

        @param profile_name: the profile name that we query the master session of
        @type profile_name: C{str}
        @param return_object: return L{X2GoSession} instance
        @type return_object: C{bool}
        @param return_session_name: return X2Go session name
        @type return_session_name: C{bool}

        @return: a session list (as UUID hashes, objects, profile names/IDs or session names)
        @rtype: C{list}

        """
        if profile_name not in self.connected_profiles(return_profile_names=True):
            return None

        if profile_name not in self.master_sessions.keys() or self.master_sessions[profile_name] is None:
            return None

        _session = self.master_sessions[profile_name]

        if not _session.is_master_session():
            del self.master_sessions[profile_name]
            return None

        if return_object:
            return _session
        elif return_session_name:
            return _session.get_session_name()
        else:
            return _session.get_uuid()
