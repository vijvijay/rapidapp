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
X2GoSessionGuardian class - a guardian thread that controls X2Go session threads
and their sub-threads (like reverse forwarding tunnels, Paramiko transport threads,
etc.).

"""
__NAME__ = 'x2goguardian-pylib'

# modules
import gevent
import threading
import copy

# Python X2Go modules
from cleanup import x2go_cleanup
import log

class X2GoSessionGuardian(threading.Thread):
    """\
    L{X2GoSessionGuardian} thread controls X2Go session threads and their sub-threads (like 
    reverse forwarding tunnels, Paramiko transport threads, etc.). Its main function is
    to tidy up once a session gets interrupted (SIGTERM, SIGINT). 

    There is one L{X2GoSessionGuardian} for each L{X2GoClient} instance (thus: for normal
    setups there should be _one_ L{X2GoClient} and _one_ L{X2GoSessionGuardian} in use).

    """
    seconds = 0
    
    def __init__(self, client_instance, 
                 auto_update_listsessions_cache=False, 
                 auto_update_listdesktops_cache=False, 
                 auto_update_listmounts_cache=False, 
                 auto_update_sessionregistry=False,
                 auto_register_sessions=False,
                 no_auto_reg_pubapp_sessions=False,
                 refresh_interval=60,
                 logger=None, loglevel=log.loglevel_DEFAULT):
        """\
        @param auto_update_listsessions_cache: let L{X2GoSessionGuardian} refresh the session list cache for all L{X2GoSession} objects
        @type auto_update_listsessions_cache: C{bool}
        @param auto_update_listdesktops_cache: let L{X2GoSessionGuardian} refresh desktop lists in the session list cache for all L{X2GoSession} objects
        @type auto_update_listdesktops_cache: C{bool}
        @param auto_update_listmounts_cache: let L{X2GoSessionGuardian} refresh mount lists in the session list cache for all L{X2GoSession} objects
        @type auto_update_listmounts_cache: C{bool}
        @param auto_update_sessionregistry: if set to C{True} the session status will be updated in regular intervals
        @type auto_update_sessionregistry: C{bool}
        @param auto_register_sessions: register new sessions automatically once they appear in the X2Go session (e.g. 
            instantiated by another client that is connected to the same X2Go server under same user ID)
        @type auto_register_sessions: C{bool}
        @param no_auto_reg_pubapp_sessions: do not auto-register published applications sessions
        @type no_auto_reg_pubapp_sessions: C{bool}
        @param refresh_interval: refresh cache and session registry every <refresh_interval> seconds
        @type refresh_interval: C{int}
        @param logger: you can pass an L{X2GoLogger} object to the L{X2GoSessionGuardian} constructor
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
        self.auto_update_listsessions_cache = auto_update_listsessions_cache
        self.auto_update_listdesktops_cache = auto_update_listdesktops_cache
        self.auto_update_listmounts_cache = auto_update_listmounts_cache
        self.auto_update_sessionregistry = auto_update_sessionregistry
        self.auto_register_sessions = auto_register_sessions
        self.no_auto_reg_pubapp_sessions = no_auto_reg_pubapp_sessions
        self.refresh_interval = refresh_interval

        threading.Thread.__init__(self, target=self.guardian)
        self.daemon = True
        self.start()

    def guardian(self):
        """\
        The handler of this L{X2GoSessionGuardian} thread.

        """
        #seconds = 0
        self._keepalive = True
        while self._keepalive:
            gevent.sleep(1)
            X2GoSessionGuardian.seconds += 1
            small_refresh   = X2GoSessionGuardian.seconds<61 and X2GoSessionGuardian.seconds % 15 == 0
            big_refresh     = X2GoSessionGuardian.seconds>60 and X2GoSessionGuardian.seconds % self.refresh_interval == 0
            #if seconds % self.refresh_interval == 0:
            if small_refresh or big_refresh:
                self.logger('Entering X2Go Guardian client management loop...', loglevel=log.loglevel_DEBUG)

                if self.auto_update_listsessions_cache:
                    self.logger('====>>>update_cache_all_profiles', loglevel=log.loglevel_DEBUG)
                    self.client_instance.update_cache_all_profiles(update_sessions=self.auto_update_listsessions_cache, 
                                                                   update_desktops=self.auto_update_listdesktops_cache,
                                                                   update_mounts=self.auto_update_listmounts_cache,
                                                                  )

                if self.auto_update_sessionregistry and not self.auto_register_sessions:
                    self.logger('====>>>update_sessionregistry_status_all_profiles', loglevel=log.loglevel_DEBUG)
                    self.client_instance.update_sessionregistry_status_all_profiles()

                # session auto-registration will automatically trigger an update of the session registry status
                if self.auto_register_sessions:
                    self.logger('====>>>register_available_server_sessions_all_profiles', loglevel=log.loglevel_DEBUG)
                    self.client_instance.register_available_server_sessions_all_profiles(skip_pubapp_sessions=self.no_auto_reg_pubapp_sessions)

        self.logger('X2Go session guardian thread waking up after %s seconds' % X2GoSessionGuardian.seconds, loglevel=log.loglevel_DEBUG)

        for session_uuid in self.client_instance.session_registry.keys():
            session_summary = self.client_instance.get_session_summary(session_uuid)
            self.logger('calling session cleanup on profile %s for terminal session: %s' % (session_summary['profile_name'], session_summary['session_name']), loglevel=log.loglevel_DEBUG)
            x2go_cleanup(threads=session_summary['active_threads'])

    def stop_thread(self):
        """\
        Stop this L{X2GoSessionGuardian} thread.

        """
        self._keepalive = False


