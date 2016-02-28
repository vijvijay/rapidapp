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
L{X2GoSessionProfiles} class - managing x2goclient session profiles.

L{X2GoSessionProfiles} is a public API class. Use this class in your Python X2Go based 
applications.

"""
__NAME__ = 'x2gosessionprofiles-pylib'

import re
import requests
import urllib3.exceptions
import copy
import types
import time
try: import simplejson as json
except ImportError: import json

# Python X2Go modules
from x2go.defaults import X2GO_SESSIONPROFILE_DEFAULTS as _X2GO_SESSIONPROFILE_DEFAULTS
from x2go.defaults import CURRENT_LOCAL_USER as _CURRENT_LOCAL_USER
import x2go.backends.profiles.base as base
import x2go.log as log
from x2go.utils import genkeypair
import x2go.x2go_exceptions

class X2GoSessionProfiles(base.X2GoSessionProfiles):

    defaultSessionProfile = copy.deepcopy(_X2GO_SESSIONPROFILE_DEFAULTS)

    def __init__(self, session_profile_defaults=None,
                 broker_url="http://localhost:8080/json/",
                 broker_username=None,
                 broker_password=None,
                 logger=None, loglevel=log.loglevel_DEFAULT,
                 **kwargs):
        """\
        Retrieve X2Go session profiles from a HTTP(S) session broker.

        @param session_profile_defaults: a default session profile
        @type session_profile_defaults: C{dict}
        @param broker_url: URL for accessing the X2Go Session Broker
        @type broker_url: C{str}
        @param broker_password: use this password for authentication against the X2Go Session Broker (avoid
            password string in the C{broker_URL} parameter is highly recommended)
        @type broker_password: C{str}
        @param logger: you can pass an L{X2GoLogger} object to the
            L{x2go.backends.profiles.httpbroker.X2GoSessionProfiles} constructor
        @type logger: L{X2GoLogger} instance
        @param loglevel: if no L{X2GoLogger} object has been supplied a new one will be
            constructed with the given loglevel
        @type loglevel: C{int}

        """
        if broker_url.upper() != "HTTP":
            match = re.match('^(?P<protocol>(http(|s)))://(|(?P<user>[a-zA-Z0-9_\.-]+)(|:(?P<password>.*))@)(?P<hostname>[a-zA-Z0-9\.-]+)(|:(?P<port>[0-9]+))($|/(?P<path>.*)$)', broker_url)
            p = match.groupdict()
            if p['user']:
                self.broker_username = p['user']
            else:
                self.broker_username = broker_username
            if p['password']:
                self.broker_password = p['password']
            elif broker_password:
                self.broker_password = broker_password
            else:
                self.broker_password = None

            # fine-tune the URL
            p['path'] = "/{path}".format(**p)
            if p['port'] is not None:
                p['port'] = ":{port}".format(**p)

            self.broker_url = "{protocol}://{hostname}{port}{path}".format(**p)

        else:
            self.broker_username = broker_username
            self.broker_password = broker_password
            self.broker_url = broker_url

        self.broker_noauth = False
        self.broker_authid = None
        self._broker_profile_cache = {}
        self._mutable_profile_ids = None
        self._broker_auth_successful = None

        self._broker_type = "http"

        base.X2GoSessionProfiles.__init__(self, session_profile_defaults=session_profile_defaults, logger=logger, loglevel=loglevel)
        if self.broker_url != "HTTP":
            self.logger("Using session broker at URL: %s" % self.broker_url, log.loglevel_NOTICE)

        # for broker based autologin, we have to be able to provide public/private key pair
        self.broker_my_pubkey, self.broker_my_privkey = genkeypair(local_username=_CURRENT_LOCAL_USER, client_address='127.0.0.1')

    def get_broker_noauth(self):
        """\
        Accessor for the class's C{broker_noauth} property.

        @return: C{True} if the broker probably does not expect authentication.
        @rtype: C{bool}

        """
        return self.broker_noauth

    def get_broker_username(self):
        """\
        Accessor for the class's C{broker_username} property.

        @return: the username used for authentication against the session broker URL
        @rtype: C{str}

        """
        return self.broker_username

    def get_broker_url(self):
        """\
        Accessor for the class's C{broker_url} property.

        @return: the session broker URL that was used at broker session instantiation
        @rtype: C{str}

        """
        return self.broker_url

    def set_broker_url(self, broker_url):
        """\
        Mutator for the class's C{broker_url} property.

        @param broker_url: A new broker URL to use with this instance. Format is
            C{<protocol>://<hostname>:<port>/<path>} (where protocol has to be C{http}
            or C{https}.
        @type broker_url: C{str}

        @return: the session broker URL that was used at broker session instantiation
        @rtype: C{str}

        """
        self.broker_url = broker_url

    def get_broker_type(self):
        """\
        Accessor of the class's {_broker_type} property.

        @return: either C{http} or C{https}.
        @rtype: C{str}

        """
        return self._broker_type

    def broker_simpleauth(self, broker_username, broker_password):
        """\
        Attempt a username / password authentication against the instance's
        broker URL.

        @param broker_username: username to use for authentication
        @type broker_username: C{str}
        @param broker_password: password to use for authentication
        @type broker_password: C{str}

        @return: C{True} if authentication has been successful
        @rtype: C{bool}

        @raise X2GoBrokerConnectionException: Raised on any kind of connection /
            authentication failure.

        """
        if self.broker_url is not None:
            request_data = {
                'user': broker_username or '',
            }
            if self.broker_authid is not None:
                request_data['authid'] = self.broker_authid
                self.logger("Sending request to broker: user: {user}, authid: {authid}".format(**request_data), log.loglevel_DEBUG)
            else:
                if broker_password:
                    request_data['password'] = "<hidden>"
                else:
                    request_data['password'] = "<EMPTY>"
                self.logger("Sending request to broker: user: {user}, password: {password}".format(**request_data), log.loglevel_DEBUG)
                request_data['password'] = broker_password or ''
            try:
                r = requests.post(self.broker_url, data=request_data)
            except (requests.exceptions.ConnectionError, requests.exceptions.MissingSchema, urllib3.exceptions.LocationParseError):
                raise x2go.x2go_exceptions.X2GoBrokerConnectionException('Failed to connect to URL %s' % self.broker_url)
            if r.status_code == 200:
                payload = json.loads(r.text)
                if not self.broker_authid and not self.broker_password:
                    self.broker_noauth = True
                elif payload.has_key('next-authid'):
                    self.broker_authid = payload['next-authid']
                self.broker_username = broker_username or ''
                self.broker_password = broker_password or ''
                self._broker_auth_successful = True
                self.populate_session_profiles()
                return True
        self._broker_auth_successful = False
        self.broker_authid = None
        return False

    def broker_disconnect(self):
        """\
        Disconnect from an (already) authenticated broker session.

        All authentication parameters will be dropped (forgotten) and
        this instance has to re-authenticate against / re-connect to the
        session broker before any new interaction with the broker is possible.

        """
        _profile_ids = copy.deepcopy(self.profile_ids)

        # forget nearly everything...
        for profile_id in _profile_ids:
            self.init_profile_cache(profile_id)
            try: del self._profile_metatypes[profile_id]
            except KeyError: pass
            try: self._profiles_need_profile_id_renewal.remove(profile_id)
            except ValueError: pass
            try: del self._cached_profile_ids[profile_id]
            except KeyError: pass
            del self.session_profiles[profile_id]
        self._mutable_profile_ids = None
        self._broker_auth_successful = False
        self.broker_authid = None
        self.broker_password = None
        self.broker_noauth = False

    def is_broker_authenticated(self):
        """\
        Detect if an authenticated broker session has already been
        initiated. Todo so, a simple re-authentication (username, password)
        will be attempted. If that fails, user credentials are not provided /
        valid.

        @return: C{True} if the broker session has already been authenticated
            and user credentials are known / valid
        @rtype: C{bool}

        """
        if self._broker_auth_successful is None:
            # do a test auth against the given broker URL
            try:
                self.broker_simpleauth(self.broker_username, self.broker_password)
            except x2go.x2go_exceptions.X2GoBrokerConnectionException:
                self._broker_auth_successful = False
        return self._broker_auth_successful

    def broker_listprofiles(self):
        """\
        Obtain a session profile list from the X2Go Session Broker.

        @return: session profiles as a Python dictionary.
        @rtype: C{dict}

        """
        if self.broker_url is not None:
            request_data = {
                'task': 'listprofiles',
                'user': self.broker_username,
            }
            if self.broker_authid is not None:
                request_data['authid'] = self.broker_authid
                self.logger("Sending request to broker: user: {user}, authid: {authid}, task: {task}".format(**request_data), log.loglevel_DEBUG)
            else:
                if self.broker_password:
                    request_data['password'] = "<hidden>"
                else:
                    request_data['password'] = "<EMPTY>"
                self.logger("Sending request to broker: user: {user}, password: {password}, task: {task}".format(**request_data), log.loglevel_DEBUG)
                request_data['password'] = self.broker_password or ''
            try:
                r = requests.post(self.broker_url, data=request_data)
            except requests.exceptions.ConnectionError:
                raise x2go.x2go_exceptions.X2GoBrokerConnectionException('Failed to connect to URL %s' % self.broker_url)
            if r.status_code == 200 and r.headers['content-type'].startswith("text/json"):
                payload = json.loads(r.text)
                if payload.has_key('next-authid'):
                    self.broker_authid = payload['next-authid']
                if payload.has_key('mutable_profile_ids'):
                    self._mutable_profile_ids = payload['mutable_profile_ids']
                self._broker_auth_successful = True
                return payload['profiles'] if payload['task'] == 'listprofiles' else {}
        self._broker_auth_successful = False
        self.broker_authid = None
        return {}

    def broker_selectsession(self, profile_id):
        """\
        Select a session from the list of available session profiles (presented by
        L{broker_listprofiles}). This method requests a session information dictionary
        (server, port, SSH keys, already running / suspended sessions, etc.) from the
        session broker for the provided C{profile_id}.

        @param profile_id: profile ID of the selected session profile
        @type profile_id: C{str}

        @return: session information (server, port, SSH keys, etc.) for a selected
            session profile (i.e. C{profile_id})
        @rtype: C{dict}

        """
        if self.broker_url is not None:
            if not self._broker_profile_cache.has_key(profile_id) or not self._broker_profile_cache[profile_id]:
                request_data = {
                    'task': 'selectsession',
                    'profile-id': profile_id,
                    'user': self.broker_username,
                    'pubkey': self.broker_my_pubkey,
                }
                if self.broker_authid is not None:
                    request_data['authid'] = self.broker_authid
                    self.logger("Sending request to broker: user: {user}, authid: {authid}, task: {task}".format(**request_data), log.loglevel_DEBUG)
                else:
                    if self.broker_password:
                        request_data['password'] = "<hidden>"
                    else:
                        request_data['password'] = "<EMPTY>"
                    self.logger("Sending request to broker: user: {user}, password: {password}, task: {task}".format(**request_data), log.loglevel_DEBUG)
                    request_data['password'] = self.broker_password or ''
                try:
                    r = requests.post(self.broker_url, data=request_data)
                except requests.exceptions.ConnectionError:
                    raise x2go.x2go_exceptions.X2GoBrokerConnectionException('Failed to connect to URL %s' % self.broker_url)
                if r.status_code == 200 and r.headers['content-type'].startswith("text/json"):
                    payload = json.loads(r.text)
                    if payload.has_key('next-authid'):
                        self.broker_authid = payload['next-authid']
                    self._broker_profile_cache[profile_id] = payload['selected_session'] if payload['task'] == 'selectsession' else {}
                    self._broker_auth_successful = True
                else:
                    self.broker_authid = None
                    self._broker_auth_successful = False
            self._broker_profile_cache[profile_id]
            return self._broker_profile_cache[profile_id]
        return {}

    def _init_profile_cache(self, profile_id):
        if self._broker_profile_cache.has_key(unicode(profile_id)):
            del self._broker_profile_cache[unicode(profile_id)]

    def _populate_session_profiles(self):
        """\
        Populate the set of session profiles by loading the session
        profile configuration from a file in INI format.

        @return: a set of session profiles
        @rtype: C{dict}

        """
        if self.is_broker_authenticated() and \
           self.broker_noauth or \
           self.broker_username and self.broker_password:

            session_profiles = self.broker_listprofiles()
            _session_profiles = copy.deepcopy(session_profiles)

            for session_profile in _session_profiles:
                session_profile = unicode(session_profile)
                for key, default_value in self.defaultSessionProfile.iteritems():
                    key = unicode(key)
                    if type(default_value) is types.StringType:
                        default_value = unicode(default_value)
                    if not session_profiles[session_profile].has_key(key):
                        session_profiles[session_profile][key] = default_value

        else:
            session_profiles = {}

        return session_profiles

    def _is_mutable(self, profile_id):
        if type(self._mutable_profile_ids) is types.ListType and profile_id in self._mutable_profile_ids:
            return True
        return False

    def _supports_mutable_profiles(self):
        if type(self._mutable_profile_ids) is types.ListType:
            return True
        return False

    def _write(self):
        print "not suported, yet"

    def _delete_profile(self, profile_id):
        del self.session_profiles[unicode(profile_id)]

    def _update_value(self, profile_id, option, value):
        if type(value) is types.StringType:
            value = unicode(value)
        self.session_profiles[unicode(profile_id)][unicode(option)] = value

    def _get_profile_parameter(self, profile_id, option, key_type):
        return key_type(self.session_profiles[unicode(profile_id)][unicode(option)])

    def _get_profile_options(self, profile_id):
        return self.session_profiles[unicode(profile_id)].keys()

    def _get_profile_ids(self):
        self.session_profiles.keys()
        return self.session_profiles.keys()

    def _get_server_hostname(self, profile_id):
        selected_session = self.broker_selectsession(profile_id)
        return selected_session['server']

    def _get_server_port(self, profile_id):
        selected_session = self.broker_selectsession(profile_id)
        return int(selected_session['port'])

    def _get_pkey_object(self, profile_id):
        selected_session = self.broker_selectsession(profile_id)
        if selected_session.has_key('authentication_pubkey') and selected_session['authentication_pubkey'] == 'ACCEPTED':
            time.sleep(2)
            return self.broker_my_privkey
        return None
