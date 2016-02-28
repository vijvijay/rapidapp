#!/usr/bin/env python
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

import os

from setuptools import setup, find_packages

# silence pyflakes, the correct __VERSION__ will be detected below...
__VERSION__ = "0.0.0.0"
try:
    # for python3.x
    for line in open(os.path.join('x2go', '__init__.py'),encoding='utf-8').readlines():
        if (line.startswith('__VERSION__')):
            exec(line.strip())
except TypeError:
    # for older python2.x versions
    for line in file(os.path.join('x2go', '__init__.py')).readlines():
        if (line.startswith('__VERSION__')):
            exec(line.strip())
MODULE_VERSION = __VERSION__

setup(
    name = "x2go",
    version = MODULE_VERSION,
    description = "Python X2Go implements an X2Go client/session library in Python based on the Python Paramiko SSH module.",
    license = 'AGPLv3+',
    author = 'Mike Gabriel',
    url = 'http://www.x2go.org',
    packages = find_packages('.'),
    package_dir = {'': '.'},
    install_requires = ['gevent', 'paramiko', ]
)
