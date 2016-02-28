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

# modules
import copy

# Python X2Go modules
import x2go.backends.profiles.base as base
import x2go.log as log

from x2go.defaults import X2GO_SESSIONPROFILE_DEFAULTS as _X2GO_SESSIONPROFILE_DEFAULTS

from x2go.x2go_exceptions import X2GoNotImplementedYetException

class X2GoSessionProfiles(base.X2GoSessionProfiles):

    defaultSessionProfile = copy.deepcopy(_X2GO_SESSIONPROFILE_DEFAULTS)
    _non_profile_sections = ('embedded')

    def __init__(self, session_profile_defaults=_X2GO_SESSIONPROFILE_DEFAULTS, logger=None, loglevel=log.loglevel_DEFAULT):
        """\
        Retrieve X2Go session profiles from a SSH session broker.

        @param session_profile_defaults: a default session profile
        @type session_profile_defaults: C{dict}
        @param logger: you can pass an L{X2GoLogger} object to the
            L{x2go.backends.profiles.httpbroker.X2GoSessionProfiles} constructor
        @type logger: L{X2GoLogger} instance
        @param loglevel: if no L{X2GoLogger} object has been supplied a new one will be
            constructed with the given loglevel
        @type loglevel: C{int}

        """
        raise X2GoNotImplementedYetException('HTTPSBROKER backend support is not implemented yet')
