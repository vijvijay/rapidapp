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

import copy
import types
import re

# Python X2Go modules
from x2go.defaults import X2GO_SESSIONPROFILE_DEFAULTS as _X2GO_SESSIONPROFILE_DEFAULTS
from x2go.defaults import X2GO_DESKTOPSESSIONS as _X2GO_DESKTOPSESSIONS
import x2go.log as log
import x2go.utils as utils

from x2go.x2go_exceptions import X2GoProfileException

class X2GoSessionProfiles():

    defaultSessionProfile = copy.deepcopy(_X2GO_SESSIONPROFILE_DEFAULTS)
    _non_profile_sections = ('embedded')

    def __init__(self, session_profile_defaults=None, logger=None, loglevel=log.loglevel_DEFAULT, **kwargs):
        """\
        Retrieve X2Go session profiles. Base class for the different specific session profile
        configuration backends.

        @param session_profile_defaults: a default session profile
        @type session_profile_defaults: C{dict}
        @param logger: you can pass an L{X2GoLogger} object to the
            L{x2go.backends.profiles.httpbroker.X2GoSessionProfiles} constructor
        @type logger: L{X2GoLogger} instance
        @param loglevel: if no L{X2GoLogger} object has been supplied a new one will be
            constructed with the given loglevel
        @type loglevel: C{int}

        """
        self.defaultValues = {}
        self._profile_metatypes = {}
        self._cached_profile_ids = {}
        self.__useexports = {}
        self._profiles_need_profile_id_renewal = []
        self.write_user_config = False

        if logger is None:
            self.logger = log.X2GoLogger(loglevel=loglevel)
        else:
            self.logger = copy.deepcopy(logger)
        self.logger.tag = __NAME__

        if utils._checkSessionProfileDefaults(session_profile_defaults):
            self.defaultSessionProfile = session_profile_defaults

        self.populate_session_profiles()

    def __call__(self, profile_id_or_name):
        """\
        Retrieve the session profile configuration for a given session profile ID (or name)

        @param profile_id_or_name: profile ID or profile name
        @type profile_id_or_name: C{str}

        @return: the profile ID's / name's profile configuration
        @rtype: C{dict}

        """
        _profile_id = self.check_profile_id_or_name(self, profile_id_or_name)
        return self.get_profile_config(profile_id=_profile_id)

    def init_profile_cache(self, profile_id_or_name):
        """\
        Some session profile backends (e.g. the broker backends cache
        dynamic session profile data). On new connections, it is
        recommented to (re-)initialize these caches.

        @param profile_id_or_name: profile ID or profile name
        @type profile_id_or_name: C{str}

        """
        profile_id = self.check_profile_id_or_name(profile_id_or_name)

        # allow backend specific clean-up
        self._init_profile_cache(profile_id)

    def _init_profile_cache(self, profile_id):
        """\
        Inherit from this class to (re-)initialize profile ID based
        cache storage.

        """
        pass

    def populate_session_profiles(self):
        """\
        Load a session profile set from the configuration storage
        backend and make it available for this class.

        @return: a set of session profiles
        @rtype: C{dict}

        """
        self.session_profiles = self. _populate_session_profiles()

        # scan for duplicate profile names and handle them...
        scan_profile_names = {}
        for profile_id in self.session_profiles.keys():
            profile_name = self.to_profile_name(profile_id)
            if profile_name not in scan_profile_names.keys():
                scan_profile_names[profile_name] = [profile_id]
            else:
                scan_profile_names[profile_name].append(profile_id)
        _duplicates = {}
        for profile_name in scan_profile_names.keys():
            if len(scan_profile_names[profile_name]) > 1:
                _duplicates[profile_name] = scan_profile_names[profile_name]
        for profile_name in _duplicates.keys():
            i = 1
            for profile_id in _duplicates[profile_name]:
                self.update_value(None, 'name', '{name} ({i})'.format(name=profile_name, i=i), profile_id=profile_id)
                i += 1

    def _populate_session_profiles(self):
        """\
        Inherit from this class and provide the backend specific way of loading /
        populating a set of session profile via this method.

        @return: a set of session profiles
        @rtype: C{dict}

        """
        return {}

    def get_profile_metatype(self, profile_id_or_name, force=False):
        """\
        Detect a human readable session profile type from the session profile configuration.

        @param profile_id_or_name: profile ID or profile name
        @type profile_id_or_name: C{str}
        @param force: re-detect the meta type, otherwise use a cached result
        @type force: C{bool}

        @return: the profile ID's / name's meta type
        @rtype: C{str}

        """
        _profile_id = self.check_profile_id_or_name(profile_id_or_name)

        if not self._profile_metatypes.has_key(_profile_id) or force:
            _config = self.get_profile_config(_profile_id)
            if _config['host']:
                if _config['rdpserver'] and _config['command'] == 'RDP':
                    _metatype = 'RDP/proxy'
                elif _config['published']:

                    if _config['command'] in _X2GO_DESKTOPSESSIONS.keys():
                        _metatype = '%s + Published Applications' % _config['command']
                    else:
                        _metatype = 'Published Applications'

                elif _config['rootless']:
                    _metatype = 'Single Applications'
                elif _config['command'] in _X2GO_DESKTOPSESSIONS.keys():
                    _metatype = '%s Desktop' % _config['command']
                elif _config['command'] in _X2GO_DESKTOPSESSIONS.values():
                    _metatype = '%s Desktop' % [ s for s in _X2GO_DESKTOPSESSIONS.keys() if _config['command'] == _X2GO_DESKTOPSESSIONS[s] ][0]
                else:
                    _metatype = 'CUSTOM Desktop'
            else:
                if _config['rdpserver'] and _config['command'] == 'RDP':
                    _metatype = 'RDP/direct'
                else:
                    _metatype = 'not supported'
            self._profile_metatypes[_profile_id] = unicode(_metatype)
        else:
            return self._profile_metatypes[_profile_id]

    def is_mutable(self, profile_id_or_name=None, profile_id=None):
        """\
        Check if a given profile name (or ID) is mutable or not.

        @param profile_id_or_name: profile name or profile ID
        @type profile_id_or_name: C{str}
        @param profile_id: if the profile ID is known, pass it in directly and skip
            the L{check_profile_id_or_name()} call
        @type profile_id: C{str}

        @return: C{True} if the session profile of the specified name/ID is mutable
        @rtype: C{bool}

        @raise X2GoProfileException: if no such session profile exists

        """
        try:
            profile_id = profile_id or self.check_profile_id_or_name(profile_id_or_name)
            return self._is_mutable(profile_id)
        except X2GoProfileException:
            return None

    def _is_mutable(self, profile_id):
        """\
        Inherit from this base class and provide your own decision making
        code here if a given profile ID is mutable or not.

        @param profile_id: profile ID
        @type profile_id: C{str}

        @return: C{True} if the session profile of the specified ID is mutable
        @rtype: C{bool}

        """
        return False

    def supports_mutable_profiles(self):
        """\
        Check if the current session profile backend supports
        mutable session profiles.

        @return: list of mutable profiles
        @rtype: C{list}

        """
        return self._supports_mutable_profiles()

    def _supports_mutable_profiles(self):
        """\
        Inherit from this base class and provide your own decision making
        code here if a your session profile backend supports mutable
        session profiles or not.

        @return: list of mutable profiles
        @rtype: C{list}

        """
        return False

    def mutable_profile_ids(self):
        """\
        List all mutable session profiles.

        @return: List up all session profile IDs of mutable session profiles.
        @rtype: C{bool}

        """
        return [ p for p in self.profile_ids if self._is_mutable(p) ]

    def write(self):
        """\
        Store session profile data to the storage backend.

        @return: C{True} if the write process has been successfull, C{False} otherwise
        @rtype: C{bool}

        """
        # then update profile IDs for profiles that have a renamed host attribute...
        for profile_id in self._profiles_need_profile_id_renewal:
            _config = self.get_profile_config(profile_id=profile_id)

            self._delete_profile(profile_id)

            try: del self._cached_profile_ids[profile_id]
            except KeyError: pass
            self.add_profile(profile_id=None, force_add=True, **_config)

        self._profiles_need_profile_id_renewal = []
        self._cached_profile_ids = {}

        return self._write()

    def _write(self):
        """\
        Write session profiles back to session profile storage backend. Inherit from this
        class and adapt to the session profile backend via this method.

        """
        return True

    def get_profile_option_type(self, option):
        """\
        Get the data type for a specific session profile option.

        @param option: the option to get the data type for
        @type option: will be detected by this method

        @return: the data type of C{option}
        @rtype: C{type}

        """
        try:
            return type(self.defaultSessionProfile[option])
        except KeyError:
            return types.StringType

    def get_profile_config(self, profile_id_or_name=None, parameter=None, profile_id=None):
        """\
        The configuration options for a single session profile.

        @param profile_id_or_name: either profile ID or profile name is accepted
        @type profile_id_or_name: C{str}
        @param parameter: if specified, only the value for the given parameter is returned
        @type parameter: C{str}
        @param profile_id: profile ID (faster than specifying C{profile_id_or_name})
        @type profile_id: C{str}

        @return: the session profile configuration for the given profile ID (or name)
        @rtype: C{dict}

        """
        _profile_id = profile_id or self.check_profile_id_or_name(profile_id_or_name)
        _profile_config = {}
        if parameter is None:
            parameters = self._get_profile_options(_profile_id)
        else:
            parameters = [parameter]
        for option in parameters:
            value = self._get_profile_parameter(_profile_id, option, key_type=self.get_profile_option_type(option))

            if type(value) is types.StringType:
                value = unicode(value)

            if option == 'export' and type(value) is types.UnicodeType:

                _value = value.replace(',', ';').strip().strip('"').strip().strip(';').strip()
                value = {}
                if _value:
                    _export_paths = _value.split(';')
                    for _path in _export_paths:
                        if not re.match('.*:(0|1)$', _path): _path = '%s:1' % _path
                        _auto_export_path = re.match('.*:1$', _path) and True or False
                        _export_path = ':'.join(_path.split(':')[:-1])
                        value[_export_path] = _auto_export_path

            _profile_config[option] = value

        if parameter is not None:
            if parameter in _profile_config.keys():
                value = _profile_config[parameter]
                return value
            else:
                raise X2GoProfileException('no such session profile parameter: %s' % parameter)

        return _profile_config

    def default_profile_config(self):
        """\
        Return a default session profile.

        @return: default session profile
        @rtype: C{dict}

        """
        return copy.deepcopy(self.defaultSessionProfile)

    def has_profile(self, profile_id_or_name):
        """\
        Does a session profile of a given profile ID or profile name exist?

        @param profile_id_or_name: profile ID or profile name
        @type profile_id_or_name: C{str}

        @return: C{True} if there is such a session profile, C{False} otherwise
        @rtype: C{bool}

        """
        try:
            self.check_profile_id_or_name(profile_id_or_name)
            return True
        except X2GoProfileException:
            return False

    def _update_profile_ids_cache(self):
        for p in self._get_profile_ids():
            if p not in self._non_profile_sections:
                self._cached_profile_ids[p] = self.to_profile_name(p)

    @property
    def profile_ids(self):
        """\
        Render a list of all profile IDs found in the session profiles configuration.

        """
        if not self._cached_profile_ids:
            self._update_profile_ids_cache()
        return self._cached_profile_ids.keys()

    def _get_profile_ids(self):
        """\
        Inherit from this class and provide a way for actually getting
        a list of session profile IDs from the storage backend via this method.

        @return: list of available session profile IDs
        @rtype: C{list}

        """
        return []

    def has_profile_id(self, profile_id):
        """\
        Does a session profile of a given profile ID exist? (Faster than L{has_profile()}.)

        @param profile_id: profile ID
        @type profile_id: C{str}

        @return: C{True} if there is such a session profile, C{False} otherwise
        @rtype: C{bool}

        """
        return unicode(profile_id) in self.profile_ids

    @property
    def profile_names(self):
        """\
        Render a list of all profile names found in the session profiles configuration.

        """
        if not self._cached_profile_ids:
            self._update_profile_ids_cache()
        return  self._cached_profile_ids.values()

    def has_profile_name(self, profile_name):
        """\
        Does a session profile of a given profile name exist? (Faster than L{has_profile()}.)

        @param profile_name: profile name
        @type profile_name: C{str}

        @return: C{True} if there is such a session profile, C{False} otherwise
        @rtype: C{bool}

        """
        return unicode(profile_name) in self.profile_names

    def to_profile_id(self, profile_name):
        """\
        Convert profile name to profile ID.

        @param profile_name: profile name
        @type profile_name: C{str}

        @return: profile ID
        @rtype: C{str}

        """
        _profile_ids = [ p for p in self.profile_ids if self._cached_profile_ids[p] == profile_name ]
        if len(_profile_ids) == 1:
            return unicode(_profile_ids[0])
        elif len(_profile_ids) == 0:
            return None
        else:
            raise X2GoProfileException('The sessions config file contains multiple session profiles with name: %s' % profile_name)

    def to_profile_name(self, profile_id):
        """\
        Convert profile ID to profile name.

        @param profile_id: profile ID
        @type profile_id: C{str}

        @return: profile name
        @rtype: C{str}

        """
        try:
            _profile_name = self.get_profile_config(profile_id=profile_id, parameter='name')
            return unicode(_profile_name)
        except:
            return u''

    def add_profile(self, profile_id=None, force_add=False, **kwargs):
        """\
        Add a new session profile.

        @param profile_id: a custom profile ID--if left empty a profile ID will be auto-generated
        @type profile_id: C{str}
        @param kwargs: session profile options for this new session profile
        @type kwargs: C{dict}

        @return: the (auto-generated) profile ID of the new session profile
        @rtype: C{str}

        """
        if profile_id is None or profile_id in self.profile_ids:
            profile_id = utils._genSessionProfileId()
            self.session_profiles[profile_id] = self.default_profile_config()

        if 'name' not in kwargs.keys():
            raise X2GoProfileException('session profile parameter ,,name\'\' is missing in method parameters')

        if kwargs['name'] in self.profile_names and not force_add:
            raise X2GoProfileException('a profile of name ,,%s\'\' already exists' % kwargs['name'])

        self._cached_profile_ids[profile_id] = kwargs['name']

        for key, value in kwargs.items():
            self.update_value(None, key, value, profile_id=profile_id)

        _default_session_profile = self.default_profile_config()
        for key, value in _default_session_profile.items():
            if key in kwargs: continue
            self.update_value(None, key, value, profile_id=profile_id)

        self._cached_profile_ids = {}

        return unicode(profile_id)

    def delete_profile(self, profile_id_or_name):
        """\
        Delete a session profile from the configuration file.

        @param profile_id_or_name: profile ID or profile name
        @type profile_id_or_name: C{str}

        """
        _profile_id = self.check_profile_id_or_name(profile_id_or_name)

        self._delete_profile(_profile_id)

        self.write_user_config = True
        self.write()
        self._cached_profile_ids = {}

    def _delete_profile(self, profile_id):
        """\
        Inherit from this class and provide a way for actually deleting
        a complete session profile from the storage backend via this method.

        """
        pass

    def update_value(self, profile_id_or_name, option, value, profile_id=None):
        """\
        Update a value in a session profile.

        @param profile_id_or_name: the profile ID
        @type profile_id_or_name: C{str}
        @param option: the session profile option of the given profile ID
        @type option: C{str}
        @param value: the value to update the session profile option with
        @type value: any type, depends on the session profile option
        @param profile_id: if the profile ID is known, pass it in directly and skip
            the L{check_profile_id_or_name()} call
        @type profile_id: C{str}

        """
        try:
            profile_id = profile_id or self.check_profile_id_or_name(profile_id_or_name)
        except X2GoProfileException:
            profile_id = profile_id_or_name

        if not self.is_mutable(profile_id=profile_id):
            raise X2GoProfileException("session profile cannot be modified, it is marked as immutable")

        if option == 'name':
            profile_name = value
            current_profile_name = self.get_value(profile_id, option)
            if not profile_name:
                raise X2GoProfileException('profile name for profile id %s must not be empty' % profile_id)
            else:
                if profile_name != current_profile_name:
                    try: del self._cached_profile_ids[profile_id]
                    except KeyError: pass
                    if profile_name in self.profile_names:
                        raise X2GoProfileException('a profile of name ,,%s\'\' already exists' % profile_name)
                    self._cached_profile_ids[profile_id] = profile_name

        if option == 'export' and type(value) == types.DictType:
            _strvalue = '"'
            for folder in value.keys():
                _strvalue += "%s:%s;" % (folder, int(value[folder]))
            _strvalue += '"'
            _strvalue = _strvalue.replace('""', '')
            value = _strvalue

        if option == 'host':
            _host = self.get_profile_config(profile_id=profile_id, parameter='host')
            if _host != value and _host is not None:
                self._profiles_need_profile_id_renewal.append(profile_id)
            if type(value) is types.TupleType:
                value = list(value)
            if type(value) is not types.ListType:
                value = value.split(',')

        self._update_value(profile_id, option, value)

    def _update_value(self, profile_id, option, value):
        """\
        Inherit from this class and provide for actually updating
        a session profile's value in the storage backend via this method.

        """
        pass

    def check_profile_id_or_name(self, profile_id_or_name):
        """\
        Detect the profile ID from a given string which maybe profile ID or profile name.

        @param profile_id_or_name: profile ID or profile name
        @type profile_id_or_name: C{str}

        @return: profile ID
        @rtype: C{str}

        @raise X2GoProfileException: if no such session profile exists

        """
        _profile_id = None
        if self.has_profile_name(profile_id_or_name):
            # we were given a sesion profile name...
            _profile_id = self.to_profile_id(profile_id_or_name)
        elif self.has_profile_id(profile_id_or_name):
            # we were given a session profile id...
            _profile_id = profile_id_or_name
        else:
            raise X2GoProfileException('No session profile with id or name ,,%s\'\' exists.' % profile_id_or_name)
        if _profile_id is not None:
            _profile_id = unicode(_profile_id)
        return _profile_id

    def to_session_params(self, profile_id_or_name=None, profile_id=None):
        """\
        Convert session profile options to L{X2GoSession} constructor method parameters.

        @param profile_id_or_name: either profile ID or profile name is accepted
        @type profile_id_or_name: C{str}
        @param profile_id: profile ID (fast than specifying C{profile_id_or_name})
        @type profile_id: C{str}

        @return: a dictionary of L{X2GoSession} constructor method parameters
        @rtype: C{dict}

        """
        _profile_id = profile_id or self.check_profile_id_or_name(profile_id_or_name)
        return utils._convert_SessionProfileOptions_2_SessionParams(self.get_profile_config(_profile_id))

    def get_session_param(self, profile_id_or_name, param):
        """\
        Get a single L{X2GoSession} parameter from a specific session profile.

        @param profile_id_or_name: either profile ID or profile name is accepted
        @type profile_id_or_name: C{str}
        @param param: the parameter name in the L{X2GoSession} constructor method
        @type param: C{str}

        @return: the value of the session profile option represented by C{param}
        @rtype: depends on the session profile option requested

        """
        return self.to_session_params(profile_id_or_name)[param]

    def _get_profile_parameter(self, profile_id, option, key_type):
        """\
        Inherit from this class and provide a way for actually obtaining
        the value of a specific profile parameter.

        @param profile_id: the profile's unique ID
        @type profile_id: C{str}
        @param option: the session profile option for which to retrieve its value
        @type option: C{str}
        @param key_type: type of the value to return
        @type key_type: C{typeobject}

        @return: value of a session profile parameter
        @rtype: C{various types}

        """
        return None

    def _get_profile_options(self, profile_id):
        """\
        Inherit from this class and provide a way for actually obtaining
        a list of available profile options of a given session profile.

        @return: list of available option is the given session profile
        @rtype: C{list}

        """
        return []

    def get_server_hostname(self, profile_id):
        """\
        Retrieve host name of the X2Go Server configured in a session profile.

        @param profile_id: the profile's unique ID
        @type profile_id: C{str}

        @return: the host name of the X2Go Server configured by the session profile
            of the given profile ID
        @rtype: C{list}

        """
        return unicode(self._get_server_hostname(profile_id))

    def _get_server_hostname(self, profile_id):
        """\
        Inherit from this class and provide a way for actually obtaining
        a the server host name for a given profile ID.

        @param profile_id: the profile's unique ID
        @type profile_id: C{str}

        @return: the host name of the X2Go Server configured by the session profile
            of the given profile ID
        @rtype: C{list}

        """
        return u'localhost'

    def get_server_port(self, profile_id):
        """\
        Retrieve SSH port of the X2Go Server configured in a session profile.

        @param profile_id: the profile's unique ID
        @type profile_id: C{str}

        @return: the SSH port of the X2Go Server configured by the session profile
            of the given profile ID
        @rtype: C{list}

        """
        return self._get_server_port(profile_id)

    def _get_server_port(self, profile_id):
        """\
        Inherit from this class and provide a way for actually obtaining
        a the server SSH port for a given profile ID.

        @param profile_id: the profile's unique ID
        @type profile_id: C{str}

        @return: the SSH port of the X2Go Server configured by the session profile
            of the given profile ID
        @rtype: C{list}

        """
        return 22

    def get_pkey_object(self, profile_id):
        """\
        If available, return a PKey (Paramiko/SSH private key) object.

        @param profile_id: the profile's unique ID
        @type profile_id: C{str}

        @return: a Paramiko/SSH PKey object
        @rtype: C{obj}

        """
        return self._get_pkey_object(profile_id)

    def _get_pkey_object(self, profile_id):
        """\
        Inherit from this class and provide a way for actually
        providing such a PKey object.

        """
        return None
