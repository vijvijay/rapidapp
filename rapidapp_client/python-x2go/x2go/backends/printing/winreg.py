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
L{X2GoClientPrinting} class is one of Python X2Go's public API classes. 

Retrieve an instance of this class from your L{X2GoClient} instance.
Use this class in your Python X2Go based applications to access the »printing« 
configuration of your X2Go client application.

"""
__NAME__ = 'x2goprint-pylib'

# modules
import copy

# Python X2Go modules
import x2go.log as log

# we hide the default values from epydoc (that's why we transform them to _UNDERSCORE variables)
from x2go.defaults import X2GO_CLIENTPRINTING_DEFAULTS as _X2GO_CLIENTPRINTING_DEFAULTS

from x2go.x2go_exceptions import X2GoNotImplementedYetException

class X2GoClientPrinting(object):
    """\
    L{x2go.backends.printing.winreg.X2GoClientPrinting} provides access to the Windows registry
    based configuration of the X2Go client printing setup.

    An instance of L{x2go.backends.printing.winreg.X2GoClientPrinting} is created on each incoming
    print job. This facilitates that on every print job the print action for this job is derived from the
    »printing« configuration file.

    Thus, changes on the file are active for the next incoming print job.

    """
    _print_action = None
    defaultValues = copy.deepcopy(_X2GO_CLIENTPRINTING_DEFAULTS)

    def __init__(self, defaults=None, logger=None, loglevel=log.loglevel_DEFAULT):
        """\
        @param defaults: a cascaded Python dicitionary structure with ini file defaults (to override 
            Python X2Go's hard coded defaults in L{defaults}
        @type defaults: C{dict}
        @param logger: you can pass an L{X2GoLogger} object to the
            L{X2GoPrintAction} constructor
        @type logger: C{obj}
        @param loglevel: if no L{X2GoLogger} object has been supplied a new one will be
            constructed with the given loglevel
        @type loglevel: C{int}

        """
        raise X2GoNotImplementedYetException('WINREG backend support is not implemented yet')
