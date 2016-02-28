# -*- coding: utf-8 -*-

modules ={}

# Python X2Go
import x2go

import wx
import os

# PyHoca-GUI modules
# ... NONE ...

if os.environ.has_key('DESKTOP_SESSION'):
    WINDOW_MANAGER = os.environ['DESKTOP_SESSION']
else:
    WINDOW_MANAGER = 'generic'

class PyHocaGUI_DialogBoxSessionTitle(wx.Dialog):
    """\
    Simple dialog box for selecting a session title string.

    """
    def __init__(self, _PyHocaGUI, profile_name, session_name):
        """\
        Session title renaming dialog box (constructor).

        @param _PyHocaGUI: the master/parent object of the application
        @type _PyHocaGUI: C{obj}
        @param profile_name: session profile name
        @type profile_name: C{str}
        @param session_name: the X2Go session name of the Window that we intend to modify the name of
        @type session_name C{str}

        """
        self._PyHocaGUI = _PyHocaGUI
        self._PyHocaGUI.gevent_sleep_when_idle = 0.1
        self._pyhoca_logger = self._PyHocaGUI._pyhoca_logger
        self._pyhoca_logger('session title query box started', loglevel=x2go.loglevel_INFO, )

        self.current_profile_name = profile_name
        self.current_session_name = session_name

        wx.Dialog.__init__(self, None, id=-1, title=profile_name, style=wx.DEFAULT_FRAME_STYLE, )
        self._PyHocaGUI._sub_windows.append(self)

        self.SetTitle(_(u'Session Title - %s') % profile_name)

        self.titleLbl = wx.StaticText(self, wx.ID_ANY, _(u'Change session title to')+':', size=(-1, -1))
        self.titleTxt = wx.TextCtrl(self, wx.ID_ANY, '', style=wx.TE_PROCESS_ENTER, size=(120, -1))
        self.okBtn = wx.Button(self, wx.ID_OK, _(u'OK'), )
        self.okBtn.SetDefault()
        self.cancelBtn = wx.Button(self, wx.ID_CANCEL, _(u'Cancel'), )

        self.Bind(wx.EVT_BUTTON, self.OnOk, self.okBtn)
        self.Bind(wx.EVT_TEXT_ENTER, self.OnOk, self.titleTxt)
        self.Bind(wx.EVT_BUTTON, self.OnCancel, self.cancelBtn)

        titleSizer = wx.BoxSizer(wx.HORIZONTAL)
        btnSizer = wx.BoxSizer(wx.HORIZONTAL)
        mainSizer = wx.BoxSizer(wx.VERTICAL)

        titleSizer.Add(self.titleLbl, 0, wx.ALL, 5)
        titleSizer.Add(self.titleTxt, 0, wx.ALL, 5)

        btnSizer.Add(self.okBtn, 0, wx.ALL, 5)
        btnSizer.Add(self.cancelBtn, 0, wx.ALL, 5)

        mainSizer.Add(titleSizer, 0, wx.ALL, 5)
        mainSizer.Add(btnSizer, 0, wx.ALL|wx.ALIGN_RIGHT, 5)

        self.SetSizerAndFit(mainSizer)
        self.Layout()

        maxX, maxY = wx.GetDisplaySize()

        # we will use the logon window position for this session re-titling windows, as well
        if self._PyHocaGUI.logon_window_position_x and self._PyHocaGUI.logon_window_position_y:

            # allow positioning of logon window via command line option
            if self._PyHocaGUI.logon_window_position_x < 0:
                move_x = maxX - (self.GetSize().GetWidth() + self._PyHocaGUI.logon_window_position_x)
            else:
                move_x = self._PyHocaGUI.logon_window_position_x
            if self._PyHocaGUI.logon_window_position_y < 0:
                move_y = maxX - (self.GetSize().GetHeight() + self._PyHocaGUI.logon_window_position_y)
            else:
                move_y = self._PyHocaGUI.logon_window_position_y

        elif (x2go.X2GOCLIENT_OS == 'Linux') and (WINDOW_MANAGER in ('gnome', 'gnome-fallback', 'awesome', 'mate', 'ubuntu', 'ubuntu-2d', 'openbox-gnome', )):

            # automatically place logon Window for GNOME, awesome
            move_x = maxX - (self.GetSize().GetWidth() + 20)
            move_y = 35

        else:

            # automatically place logon Window for KDE4, LXDE, etc.
            move_x = maxX - (self.GetSize().GetWidth() + 20)
            move_y = maxY - (self.GetSize().GetHeight() + 70)

        self.Move((move_x, move_y))
        self.Show()

    def OnOk(self, evt):
        """\
        Continue here, if the user clicks the Ok button in the dialog box.

        @param evt: event
        @type evt: C{obj}

        """
        title = self.titleTxt.GetValue()

        _session = self._PyHocaGUI._X2GoClient__get_session_of_session_name(session_name=self.current_session_name, return_object=True)
        _session.set_session_window_title(title=title)

        self.Close()
        self.Destroy()

    def OnCancel(self, evt):
        """\
        Continue here, if the user clicks the Cancel button in the dialog box.

        @param evt: event
        @type evt: C{obj}

        """
        self.Close()
        self.Destroy()

    def Destroy(self):
        """\
        Do some PyHocaGUI specific cleanup if this window gets destroyed.

        """
        self._PyHocaGUI.gevent_sleep_when_idle = 0.25
        try:
            self._PyHocaGUI._sub_windows.remove(self)
        except ValueError:
            pass
        try:
            self._PyHocaGUI._temp_disabled_profile_names.remove(self.current_profile_name)
        except ValueError:
            pass
        wx.Dialog.Destroy(self)
