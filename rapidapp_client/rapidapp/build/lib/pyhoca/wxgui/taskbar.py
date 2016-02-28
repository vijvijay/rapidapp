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

modules ={}

# Python X2Go
import x2go

import wx
import os

# PyHoca-GUI modules
import menus_taskbar
import basepath


def MakeIcon(icon_name, fallback_name='PyHoca-GUI_trayicon.png', appname="PyHoca-GUI"):
    """\
    The various platforms have different requirements for the
    icon size...

    @param icon_name: rel. file name of the icon image
    @type icon_name: C{str}
    @param fallback_name: a fallback icon file name in case C{icon_name} cannot be found
    @type fallback_name: C{str}
    @param appname: name of this application, used to detect icon file
    @type appname: C{str}

    """
    if "wxMSW" in wx.PlatformInfo:
        icon_size = '16x16'
    elif "wxGTK" in wx.PlatformInfo:
        icon_size = '22x22'
    elif "wxMAC" in wx.PlatformInfo:
        icon_size = '128x128'

    if icon_name is None:
        icon_name = '{appname}_trayicon'.format(appname=appname)

    _icons_location = basepath.icons_basepath

    icon_name = os.path.expanduser(icon_name)
    if not icon_name.lower().endswith('.png'):
        icon_name = '%s.png' % icon_name

    icon_folder = 'PyHoca'
    if os.path.isdir(os.path.join(_icons_location, appname)):
        icon_folder = appname

    icon_file = '%s/%s/%s/%s' % (_icons_location, icon_folder, icon_size, icon_name)
    if not (os.path.isfile(str(icon_file)) or os.path.islink(str(icon_file))):
        icon_file = '%s/%s/%s/%s' % (_icons_location, icon_folder, icon_size, fallback_name)

    img = wx.Image(icon_file)
    icon = wx.IconFromBitmap(img.ConvertToBitmap())
    return icon


class PyHocaGUI_TaskBarIcon(wx.TaskBarIcon):
    """\
    Class for the L{PyHocaGUI} taskbar icon.

    """
    def __init__(self, about):
        """\
        Initialize the systray icon. The main application window is
        the about window, so this one has to be passed in as mandatory
        argument.

        @param about: instance of the About wx.Frame
        @type about: C{obj}

        """
        wx.TaskBarIcon.__init__(self)
        self._PyHocaGUI = about._PyHocaGUI
        self._pyhoca_logger = self._PyHocaGUI._pyhoca_logger
        self._pyhoca_logger('start TaskBarIcon of type: %s' % (wx.PlatformInfo, ), loglevel=x2go.loglevel_INFO)
        self.SetIconIdle()
        self.imgidx = 1
        self.tooltip = ""

    def SetIconConnecting(self, profile_name):
        """\
        When connecting show the default icon and some informational text on mouse hover events
        that gives some information what remote X2Go server the client is connecting to.

        @param profile_name: the name of the session profile the application currently is connecting to
        @type profile_name: C{str}

        """
        if x2go.X2GOCLIENT_OS == 'Windows':
            icon_name = self._PyHocaGUI.tray_icon_connecting or self._PyHocaGUI.tray_icon
            self.icon = MakeIcon(icon_name=icon_name, appname=self._PyHocaGUI.appname)
            self.SetIcon(self.icon, _(u"%s (%s)\nConnecting you to ,,%s\'\'") % (self._PyHocaGUI.appname, self._PyHocaGUI.version, profile_name))
        else:
            icon_name = self._PyHocaGUI.tray_icon_connecting or self._PyHocaGUI.tray_icon
            self.icon = MakeIcon(icon_name=icon_name, appname=self._PyHocaGUI.appname)
            self.SetIcon(self.icon, _(u"%s\nCurrently connecting you to remote X2Go server ,,%s\'\'") % (self._PyHocaGUI.appname, profile_name))

    def SetIconIdle(self):
        """\
        When idle show the default icon and some default informational text on mouse hover events.

        """
        if x2go.X2GOCLIENT_OS == 'Windows':
            icon_name = self._PyHocaGUI.tray_icon
            self.icon = MakeIcon(icon_name=icon_name, appname=self._PyHocaGUI.appname)
            self.SetIcon(self.icon, _(u"%s (%s)\nConnecting you to Appri.me Cloud Apps") % (self._PyHocaGUI.appname, self._PyHocaGUI.version))
        else:
            icon_name = self._PyHocaGUI.tray_icon
            self.icon = MakeIcon(icon_name=icon_name, appname=self._PyHocaGUI.appname)
            self.SetIcon(self.icon, _(u"%s\nClient for connecting you to a remote X2Go server") % self._PyHocaGUI.appname)

    def CreateSessionManagerPopupMenu(self, evt):
        """\
        This method is called by the L{PyHocaGUI} base class when it needs to popup
        the menu for the default EVT_LEFT_DOWN event.

        @param evt: event
        @type evt: C{obj}

        @return: a wx-based popup menu object (containing the session and connection manager)
        @rtype: C{obj}

        """
        if self._PyHocaGUI.args.single_session_profile:
            self.menu_sessionmanager = self.PopupMenu(menus_taskbar.PyHocaGUI_Menu_TaskbarSessionProfile(self._PyHocaGUI, caller=self, profile_name=self._PyHocaGUI.args.session_profile))
        else:
            self.menu_sessionmanager = self.PopupMenu(menus_taskbar.PyHocaGUI_Menu_TaskbarSessionManager(self._PyHocaGUI, caller=self,))
        return self.menu_sessionmanager

    def CreatePopupMenu(self):
        """\
        This method is called by the L{PyHocaGUI} base class when it needs to popup
        the menu for the default EVT_RIGHT_DOWN event.

        This method wraps around L{CreateProfileManagerPopupMenu()}.

        @return: a wx-based popup menu object (containing the session profile manager, amongst others)
        @rtype: C{obj}

        """
        return self.CreateProfileManagerPopupMenu()

    def CreateProfileManagerPopupMenu(self):
        """\
        Create the profile manager / client mangager popup menu (i.e. on right-click of the mouse).

        @return: a wx-based popup menu object (containing the session profile manager, amongst others)
        @rtype: C{obj}

        """
        self.menu_optionsmanager = self.PopupMenu(menus_taskbar.PyHocaGUI_Menu_TaskbarOptionsManager(self._PyHocaGUI, caller=self,))
        return self.menu_optionsmanager

    def Close(self):
        """\
        Remove the applet icon from the system tray.

        """
        self.RemoveIcon()

