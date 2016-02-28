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
X2GoClientSettings class - managing x2goclient settings file.

The L{X2GoClientSettings} class one of Python X2Go's a public API classes.
Use this class (indirectly by retrieving it from an L{X2GoClient} instance)
in your Python X2Go based applications to access the
»settings« configuration file of your X2Go client application.

"""
__NAME__ = 'x2gosettings-pylib'

# modules
import copy

# Python X2Go modules
import x2go.log as log
from x2go.defaults import X2GO_CLIENTSETTINGS_DEFAULTS as _X2GO_CLIENTSETTINGS_DEFAULTS

from x2go.x2go_exceptions import X2GoNotImplementedYetException

class X2GoClientSettings(object):
    """\
    Configure settings for L{X2GoClient} instances with the GConf daemon.

    """
    defaultValues = copy.deepcopy(_X2GO_CLIENTSETTINGS_DEFAULTS)

    def __init__(self, defaults=_X2GO_CLIENTSETTINGS_DEFAULTS, logger=None, loglevel=log.loglevel_DEFAULT):
        """\
        Constructs an L{X2GoClientSettings} instance. This is normally done from within an L{X2GoClient} instance.
        You can retrieve this L{X2GoClientSettings} instance with the L{X2GoClient.get_client_settings()} 
        method.

        On construction the L{X2GoClientSettings} object is filled with values as found in GConf::

            <GConf paths, FIXME: give proper locations here>

        """
        raise X2GoNotImplementedYetException('GCONF backend support is not implemented yet')

