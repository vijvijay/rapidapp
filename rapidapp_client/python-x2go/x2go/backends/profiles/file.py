# -*- coding: utf-8 -*-

"""\
L{X2GoSessionProfiles} class - managing x2goclient session profiles.

L{X2GoSessionProfiles} is a public API class. Use this class in your Python X2Go based 
applications.

"""
__NAME__ = 'x2gosessionprofiles-pylib'

import random

# Python X2Go modules
from x2go.defaults import X2GO_SESSIONPROFILES_CONFIGFILES as _X2GO_SESSIONPROFILES_CONFIGFILES
import x2go.backends.profiles.base as base
import x2go.inistring as inistring
import x2go.log as log
import x2go.client as x2client

class X2GoSessionProfiles(base.X2GoSessionProfiles, inistring.X2GoIniString):

    def __init__(self, config_files=_X2GO_SESSIONPROFILES_CONFIGFILES, session_profile_defaults=None, logger=None, loglevel=log.loglevel_DEFAULT, **kwargs):
        """\
        Retrieve X2Go session profiles from a file, typically C{~/.x2goclient/sessions}.

        @param config_files: a list of config file locations, the first file name in this list the user has write access to will be the user configuration file
        @type config_files: C{list}
        @param session_profile_defaults: a default session profile
        @type session_profile_defaults: C{dict}
        @param logger: you can pass an L{X2GoLogger} object to the
            L{x2go.backends.profiles.file.X2GoSessionProfiles} constructor
        @type logger: L{X2GoLogger} instance
        @param loglevel: if no L{X2GoLogger} object has been supplied a new one will be
            constructed with the given loglevel
        @type loglevel: C{int}

        """
        self.config_string = """\
[20150709040728796000]
defsndport = 1
sshproxyautologin = 1
forwardsshagent = 0
useiconv = 0
iconvfrom = UTF-8
height = 600
xdmcpserver = localhost
pack = 4k-tight
uniquehostkeyaliases = 0
rdpserver = 
directrdpsettings = 
sshproxysamepass = 0
speed = 2
setsessiontitle = 0
sessiontitle = 
layout = 
sshproxytype = SSH
width = 800
quality = 0
krblogin = 0
sshproxyuser = 
soundtunnel = 1
rdpoptions = -u X2GO_USER -p X2GO_PASSWORD
soundsystem = pulse
clipboard = both
autostart = 1
fullscreen = 0
print = 1
type = auto
sndport = 4713
usesshproxy = 0
usemimebox = 1
xinerama = 0
variant = 
usekbd = 1
autologin = 1
sshproxykeyfile = 
fstunnel = 1
applications = TERMINAL, WWWBROWSER, MAILCLIENT, OFFICE
host = lb.rapidapp.online
mimeboxextensions = 
multidisp = 0
key = 
sshproxysameuser = 0
sshproxyport = 22
startsoundsystem = 0
icon = :icons/128x128/x2gosession.png
sound = 0
autoconnect = 0
rootless = 1
mimeboxaction = OPEN
name = Appri.me
rdpport = 3389
iconvto = UTF-8
directrdp = 0
restoreexports = 0
useexports = 0
sshproxyhost = proxyhost.mydomain
rdpclient = rdesktop
command = 
dpi = 64
published = 1
sshport = 22
setdpi = 0
display = 1
maxdim = 0
user =
        """
        # providing defaults for an X2GoSessionProfiles instance will---in the worst case---override your
        # existing sessions file in your home directory once you write the sessions back to file...
        inistring.X2GoIniString.__init__(self, config_file_string=self.config_string, logger=logger, loglevel=loglevel)
        base.X2GoSessionProfiles.__init__(self, session_profile_defaults=session_profile_defaults, logger=logger, loglevel=loglevel)


    def get_type(self, section, key):
        """\
        Override the inifile class's get_type method due to the special layout of the session profile
        class.

        @param section: INI file section
        @type section: C{str}
        @param key: key in INI file section
        @type key: C{str}

        @return: the data type of C{key} in C{section}
        @rtype: C{type}

        """
        # we have to handle the get_type method separately...
        return self.get_profile_option_type(key)

    def _populate_session_profiles(self):
        """\
        Populate the set of session profiles by loading the session
        profile configuration from a file in INI format.

        @return: a set of session profiles
        @rtype: C{dict}

        """
        session_profiles = [ p for p in self.iniConfig.sections() if p not in self._non_profile_sections and p != 'none' ]
        _session_profiles_dict = {}
        for session_profile in session_profiles:
            for key, default_value in self.defaultSessionProfile.iteritems():
                if not self.iniConfig.has_option(session_profile, key):
                    self._storeValue(session_profile, key, default_value)
            # update cached meta type session profile information
            self.get_profile_metatype(session_profile)
            _session_profiles_dict[session_profile] = self.get_profile_config(session_profile)

        return _session_profiles_dict

    def _is_mutable(self, profile_id):
        return True

    def _supports_mutable_profiles(self):
        return True

    def _write(self):
        self._write_user_config = self.write_user_config
        return inistring.X2GoIniString.write(self)

    def _delete_profile(self, profile_id):
        self.iniConfig.remove_section(profile_id)
        try: del self.session_profiles[profile_id]
        except KeyError: pass

    def _update_value(self, profile_id, option, value):
        self.session_profiles[profile_id][option] = value
        if option == 'host':
            value = ','.join(value)
        self._X2GoIniFile__update_value(profile_id, option, value)

    def _get_profile_parameter(self, profile_id, option, key_type):
        return self.get(profile_id, option, key_type)

    def _get_profile_options(self, profile_id):
        return [ o for o in self.iniConfig.options(profile_id) if o != "none" ]

    def _get_profile_ids(self):
        return [ s for s in self.iniConfig.sections() if s != "none" ]

    def _get_server_hostname(self, profile_id):
        if x2client.X2GoClient.apprime_server is not None:
            return x2client.X2GoClient.apprime_server
        return random.choice(self.get_profile_config(profile_id, 'host'))

    def _get_server_port(self, profile_id):
        if x2client.X2GoClient.apprime_port is not None:
            return x2client.X2GoClient.apprime_port
        return self.get_profile_config(profile_id, 'sshport')
