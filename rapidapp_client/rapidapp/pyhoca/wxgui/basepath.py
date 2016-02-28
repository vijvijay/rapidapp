# -*- coding: utf-8 -*-

# Copyright (C) 2010-2014 by Mike Gabriel <mike.gabriel@das-netzwerkteam.de>
# Copyright (C) 2010-2014 by Dick Kniep <dick.kniep@lindix.nl>
#
# PyHoca GUI is free software; you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# PyHoca GUI is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program; if not, write to the
# Free Software Foundation, Inc.,
# 51 Franklin St, Fifth Floor, Boston, MA 02110-1301, USA.

import os
from x2go import X2GOCLIENT_OS as _X2GOCLIENT_OS

def reload_base_paths():
    if os.environ.has_key('PYHOCAGUI_DEVELOPMENT') and os.environ['PYHOCAGUI_DEVELOPMENT'] == '1':
        _base_location = os.path.abspath(os.path.curdir)
        _icons_location = os.path.join(_base_location, 'icons')
        _images_location = os.path.join(_base_location, 'img')
        if _X2GOCLIENT_OS != 'Windows':
            _locale_location = os.path.join(_base_location, 'locale')
        else:
            _locale_location = os.path.join(_base_location, 'build', 'mo')
            _nxproxy_location = os.path.join(_base_location, '..', 'pyhoca-contrib', 'mswin', 'nxproxy-mswin', 'nxproxy.exe')
            _pulseaudio_location = os.path.join(_base_location, '..', 'pyhoca-contrib', 'mswin', 'pulseaudio-mswin', 'pulseaudio-5.0-rev18', 'pulseaudio.exe')
    else:
        if _X2GOCLIENT_OS == 'Windows':
            _base_location = os.path.abspath(os.path.curdir)
            _icons_location = os.path.join(_base_location, 'icons')
            _images_location = os.path.join(_base_location, 'img')
            _locale_location = os.path.join(_base_location, 'mo')
            _nxproxy_location = os.path.join(_base_location, 'nxproxy', 'nxproxy.exe')
            _pulseaudio_location = os.path.join(_base_location, 'pulseaudio', 'pulseaudio.exe')
        else:
            _icons_location = '/usr/share/icons'
            _images_location = '/usr/share/pyhoca/img'
            _locale_location = '/usr/share/locale'

    global icons_basepath
    global images_basepath
    icons_basepath = _icons_location
    images_basepath = _images_location
    if _X2GOCLIENT_OS == 'Windows':
        global nxproxy_binary
        nxproxy_binary = _nxproxy_location
        global pulseaudio_binary
        pulseaudio_binary = _pulseaudio_location
    global locale_basepath
    locale_basepath = _locale_location

reload_base_paths()
