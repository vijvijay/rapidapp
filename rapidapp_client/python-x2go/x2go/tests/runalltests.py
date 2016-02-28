# -*- coding: utf-8 -*-

# Copyright (C) 2010 by Mike Gabriel <mike.gabriel@das-netzwerkteam.de>
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
This file is a default test runner as found in ZOPE/Plone products. It works 
fine for any kind of Python unit testing---as we do here for Python X2Go.
"""

import os
import sys

base = os.path.join(os.path.split(os.path.split(os.getcwd())[0])[0])

# prepend the X2Go path (useful for building new packages)
sys.path = [os.path.normpath(base)] + sys.path

import unittest
TestRunner = unittest.TextTestRunner
suite = unittest.TestSuite()

tests = os.listdir(os.curdir)
tests = [n[:-3] for n in tests if n.startswith('test') and n.endswith('.py')]

for test in tests:
    m = __import__(test)
    if hasattr(m, 'test_suite'):
        suite.addTest(m.test_suite())

if __name__ == '__main__':
    TestRunner().run(suite)
