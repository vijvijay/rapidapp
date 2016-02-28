#!/usr/bin/env python
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

from x2go import X2GOCLIENT_OS
from x2go import BACKENDS

_profiles_backend_default = BACKENDS['X2GoSessionProfiles']['default']
_settings_backend_default = BACKENDS['X2GoClientSettings']['default']
_printing_backend_default = BACKENDS['X2GoClientPrinting']['default']

if X2GOCLIENT_OS == 'Windows':
    from x2go import X2GoClientXConfig
    _x = X2GoClientXConfig()
    _known_xservers = _x.known_xservers
    _installed_xservers = _x.installed_xservers

if X2GOCLIENT_OS == 'Windows':
    _config_backends = ('FILE', 'WINREG')
elif X2GOCLIENT_OS == 'Linux':
    _config_backends = ('FILE', 'GCONF')
else:
    _config_backends = ('FILE')

default_options = {

  # common
  'debug': False,
  'quiet': False,
  'libdebug': False,
  'libdebug_sftpxfer': False,
  'version': False,

  # session related options
  'session_profile': '',
  'remember_username': False,
  'non_interactive': False,
  'auto_connect': False,
  'show_profile_metatypes': False,
  'single_session_profile': False,
  'tray_icon': '',
  'tray_icon_connecting': '',
  'restricted_trayicon': False,
  'add_to_known_hosts': False,
  'start_on_connect': False,
  'exit_on_disconnect': False,
  'resume_newest_on_connect': False,
  'resume_oldest_on_connect': False,
  'resume_all_on_connect': False,
  'disconnect_on_suspend': False,
  'disconnect_on_terminate': False,
  'display': '',

  # brokerage
  'broker_url': '',
  'broker_password': '',
  'broker_name': 'X2Go Session Broker',
  'broker_cacertfile': '',
  'broker_autoconnect': False,

  # branding
  'splash_image': '',
  'about_image': '',
  'disable_splash': False,
  'disable_options': False,
  'disable_printingprefs': False,
  'disable_profilemanager': False,
  'disable_notifications': False,
  'logon_window_position': False,
  'published_applications_no_submenus': 10,

  # backends
  'backend_controlsession': '',
  'backend_terminalsession': '',
  'backend_serversessioninfo': '',
  'backend_serversessionlist': '',
  'backend_proxy': '',
  'backend_sessionprofiles': '',
  'backend_clientsettings': '',
  'backend_clientprinting': '',

  # file locations
  'client_rootdir': '',
  'sessions_rootdir': '',
  'ssh_rootdir': '',
}

if X2GOCLIENT_OS == 'Windows':
    default_options.update(
        { 'lang': 'en',
          'start_xserver': False,
          'preferred_xserver': '',
          'start_pulseaudio': False,
        }
    )
