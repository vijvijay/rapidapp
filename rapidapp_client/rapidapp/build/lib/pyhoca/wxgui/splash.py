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

import wx
import os

# PyHoca-GUI modules
import basepath

class PyHocaGUI_SplashScreen(wx.SplashScreen):
    """\
    L{PyHocaGUI} splash screen that gets shown an application startup.

    """
    def __init__(self, _PyHocaGUI, splash_image=None):
        """
        Splash screen (constructor).

        @param splash_image: file name of a splash image file (currently, only PNGs are supported)
        @type splash_image: C{str}

        """
        if splash_image:
            splash_image = os.path.expanduser(splash_image)

        if splash_image and os.path.basename(splash_image) == splash_image:
            splash_image = os.path.join(basepath.images_basepath, splash_image)

        if not os.path.isfile(str(splash_image)):
            splash_image = None

        if splash_image is None:
            splash_image = os.path.join(basepath.images_basepath, '{appname}_splash.png'.format(appname=_PyHocaGUI.appname))
            if not os.path.exists(splash_image):
                splash_image = os.path.join(basepath.images_basepath, 'PyHoca-GUI_splash.png')

        if os.path.isfile(str(splash_image)):
            splash_wximage = wx.Image(splash_image, wx.BITMAP_TYPE_PNG, )
            splash_wximage.Rescale(400, int(float(400)/splash_wximage.Width*splash_wximage.Height))

            splash_wxbitmap = splash_wximage.ConvertToBitmap()
            wx.SplashScreen.__init__(self,
                                     splash_wxbitmap,
                                     splashStyle=wx.SPLASH_CENTRE_ON_SCREEN|wx.SPLASH_TIMEOUT,
                                     milliseconds=5000,
                                     parent=None,
                                     style=wx.SIMPLE_BORDER|wx.STAY_ON_TOP|wx.FRAME_NO_TASKBAR
                                    )
            self.Bind(wx.EVT_CLOSE, self.OnClose)

    def OnClose(self, evt):
        """\
        Hide the splash screen.

        """
        # Make sure the default handler runs too so this window gets
        # destroyed
        evt.Skip()
        self.Hide()
