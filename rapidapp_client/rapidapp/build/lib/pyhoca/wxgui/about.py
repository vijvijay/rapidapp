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

import os

# Python X2Go
import x2go

# wxPython
import wx

# PyHoca-GUI modules
import basepath

class PyHocaGUI_AboutFrame(wx.Frame):
    """\
    wxWidget displaying an ,,About'' window for this application.

    """
    def __init__(self, _PyHocaGUI, caller=None, about_image=None, icon_name=None, about_what=None, ):
        """\
        About window (constructor).

        @param _PyHocaGUI: main application instance
        @type _PyHocaGUI: C{obj}
        @param caller: unused
        @type caller: C{None}
        @param about_image: full image path for background image of About window
        @type about_image: C{str}
        @param icon_name: icon name for window icon
        @type icon_name: C{str}
        @param about_what: about what is this about window?
        @type about_what: C{str}

        """
        self._PyHocaGUI = _PyHocaGUI
        self._pyhoca_logger = self._PyHocaGUI._pyhoca_logger

        fallback_about_image = 'PyHoca-GUI_about-logo.png'

        if about_image is None:
            about_image = '{appname}_about-logo.png'.format(appname=_PyHocaGUI.appname)

        if not about_image.lower().endswith('.png'):
            about_image = '%s.png' % about_image

        about_image = os.path.expanduser(about_image)

        if os.path.basename(about_image) == about_image:
            about_image = os.path.join(basepath.images_basepath, about_image)

        if not os.path.isfile(about_image):
            about_image = os.path.join(basepath.images_basepath, fallback_about_image)

        if about_what is None:
            about_what = self._PyHocaGUI.appname

        if x2go.X2GOCLIENT_OS == 'Windows':
            wx.Frame.__init__(self, None, -1, _(u'About %s ...') % about_what, size=(403,340))
        else:
            wx.Frame.__init__(self, None, -1, _(u'About %s ...') % about_what, size=(400,298))
        self.Bind(wx.EVT_CLOSE, self.OnHide)

        panel = wx.Panel(self, -1, pos=(0,0), size=(0,0), )
        panel.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)
        panel.SetFocus()

        about_wximage = wx.Image(about_image, wx.BITMAP_TYPE_PNG, )
        about_wximage.Rescale(400, int(float(400)/about_wximage.Width*about_wximage.Height))
        about_wxbitmap = about_wximage.ConvertToBitmap()

        _logo_bitmap = wx.StaticBitmap(self, wx.ID_ANY, about_wxbitmap, (0, 0))
        self.bitmap = _logo_bitmap

        if "wxMSW" in wx.PlatformInfo:
            icon_size = '16x16'
        elif "wxGTK" in wx.PlatformInfo:
            icon_size = '22x22'
        elif "wxMAC" in wx.PlatformInfo:
            icon_size = '128x128'

        if icon_name is None:
            icon_name = '{appname}_winicon.png'.format(appname=_PyHocaGUI.appname)

        icon_name = os.path.expanduser(icon_name)
        if not icon_name.lower().endswith('.png'):
            icon_name = '%s.png' % icon_name

        icon_file = icon_name
        if not (os.path.isfile(str(icon_file)) or os.path.islink(str(icon_file))):
            icon_folder = 'PyHoca'
            if os.path.isdir(os.path.join(basepath.icons_basepath, _PyHocaGUI.appname)):
                icon_folder = _PyHocaGUI.appname
            icon_file = '%s/%s/%s/%s' % (basepath.icons_basepath, icon_folder, icon_size, icon_name)

        img = wx.Image(icon_file)
        icon = wx.IconFromBitmap(img.ConvertToBitmap())
        self.icon = self.SetIcon(icon)

        self.CenterOnScreen()

    def OnHide(self, evt):
        """\
        Hide the About window (never close it as it is the main window of the application.

        """
        self.Show(False)

    def OnKeyDown(self, evt):
        """\
        Handle keyboard requests, so that pressing ESC can hide the About window.

        """
        keycode = evt.GetKeyCode()
        if keycode == wx.WXK_ESCAPE:
            self.Show(False)
        evt.Skip()

