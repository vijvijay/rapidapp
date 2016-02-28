# -*- coding: utf-8 -*-

"""\
X2GoClientSettings class - managing x2goclient settings file.

The L{X2GoClientSettings} class one of Python X2Go's a public API classes.
Use this class (indirectly by retrieving it from an L{X2GoClient} instance)
in your Python X2Go based applications to access the
»settings« configuration file of your X2Go client application.

"""
__NAME__ = 'x2gosettings-pylib'

# Python X2Go modules
import x2go.log as log
from x2go.defaults import X2GO_SETTINGS_CONFIGFILES as _X2GO_SETTINGS_CONFIGFILES
from x2go.defaults import X2GO_CLIENTSETTINGS_DEFAULTS as _X2GO_CLIENTSETTINGS_DEFAULTS
import x2go.inistring as inistring


class X2GoClientSettings(inistring.X2GoIniString):
    """\
    Configuration file based settings for L{X2GoClient} instances.

    """
    def __init__(self, config_files=_X2GO_SETTINGS_CONFIGFILES, defaults=_X2GO_CLIENTSETTINGS_DEFAULTS, logger=None, loglevel=log.loglevel_DEFAULT):
        """\
        Constructs an L{X2GoClientSettings} instance. This is normally done from within an L{X2GoClient} instance.
        You can retrieve this L{X2GoClientSettings} instance with the L{X2GoClient.get_client_settings()} 
        method.

        On construction the L{X2GoClientSettings} object is filled with values from the configuration files::

            /etc/x2goclient/settings
            ~/.x2goclient/settings

        The files are read in the specified order and config options of both files are merged. Options 
        set in the user configuration file (C{~/.x2goclient/settings}) override global options set in
        C{/etc/x2goclient/settings}.

        """
        self.config_string = """\
[General]
clientport = 22
autoresume = 1

[trayicon]
noclose = 1
maxdiscon = 1
enabled = 1
mincon = 1
mintotray = 1

[Authorization]
suspend = 1
editprofile = 1
newprofile = 1
resume = 1

[LDAP]
useldap = 0
port1 = 0
port2 = 0
port = 389
server = localhost

"""
        inistring.X2GoIniString.__init__(self, self.config_string, defaults=defaults, logger=logger, loglevel=loglevel)
