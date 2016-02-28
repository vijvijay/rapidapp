# -*- coding: utf-8 -*-

modules ={}

# Python X2Go
import x2go

import wx
import os
import datetime
import socket

# PyHoca-GUI modules
# ... NONE ...

if os.environ.has_key('DESKTOP_SESSION'):
    WINDOW_MANAGER = os.environ['DESKTOP_SESSION']
else:
    WINDOW_MANAGER = 'generic'

class PyHocaGUI_DialogBoxServerInfo(wx.Dialog):
    """\
    Simple dialog box for showing server information.

    """
    def __init__(self, _PyHocaGUI, profile_name):
        """\
        Server information dialog box (constructor).

        @param _PyHocaGUI: the master/parent object of the application
        @type _PyHocaGUI: C{obj}
        @param profile_name: session profile name
        @type profile_name: C{str}

        """
        self._PyHocaGUI = _PyHocaGUI
        self._pyhoca_logger = self._PyHocaGUI._pyhoca_logger
        self._pyhoca_logger('server info box started', loglevel=x2go.loglevel_INFO, )

        self.current_profile_name = profile_name

        wx.Dialog.__init__(self, None, id=-1, title=profile_name, style=wx.DEFAULT_FRAME_STYLE, )
        self._PyHocaGUI._sub_windows.append(self)

        self.SetTitle(_(u'Connection status - %s') % profile_name)

        self.titleLbl = wx.StaticText(self, wx.ID_ANY, _(u'Connection status: %s\n\nServer performance, network delay, ...') % self.current_profile_name, size=(-1, -1))

        self.infoArea = wx.TextCtrl(self, id=-1, value="", size=(520,300), style=wx.TE_READONLY|wx.TE_MULTILINE|wx.SUNKEN_BORDER)

        ID_REFRESH = wx.NewId()
        self.refreshBtn = wx.Button(self, ID_REFRESH, _(u'Refresh'), )
        self.cancelBtn = wx.Button(self, wx.ID_CANCEL, _(u'Close'), )

        self.Bind(wx.EVT_BUTTON, self.OnRefreshServerInfo, self.refreshBtn)
        self.Bind(wx.EVT_BUTTON, self.OnCancel, self.cancelBtn)

        titleSizer = wx.BoxSizer(wx.HORIZONTAL)
        infoSizer = wx.BoxSizer(wx.HORIZONTAL)
        btnSizer = wx.BoxSizer(wx.HORIZONTAL)
        mainSizer = wx.BoxSizer(wx.VERTICAL)

        titleSizer.Add(self.titleLbl, 0, wx.ALL, 5)

        infoSizer.Add(self.infoArea, 0, wx.ALL, 5)

        btnSizer.Add(self.refreshBtn, 0, wx.ALL, 5)
        btnSizer.Add(self.cancelBtn, 0, wx.ALL, 5)

        mainSizer.Add(titleSizer, 0, wx.ALL, 5)
        mainSizer.Add(infoSizer, 0, wx.ALL, 5)
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
        self._refreshServerInfo()

    def ShowModal(self, **kwargs):
        self._PyHocaGUI._sub_windows.append(self)
        wx.Dialog.ShowModal(self, **kwargs)

    def _refreshServerInfo_orig_x2go(self):

        server_components = self._PyHocaGUI.get_server_components(self.current_profile_name, force=True)
        server_extensions = [ k for k in server_components.keys() if k.startswith('x2goserver-') and k != 'x2goserver-common' ]
        server_extensions.sort()
        server_addons = [ k for k in server_components.keys() if not k.startswith('x2goserver') and k != 'x2goagent' ]
        server_addons.sort()
        server_features = self._PyHocaGUI.get_server_features(self.current_profile_name, force=True)
        halftab = '    '
        newline = '\n'

        self.infoArea.AppendText(_(u'X2Go Server')+':'+2*newline)
        self.infoArea.AppendText(halftab+_(u'Server Core')+':'+newline)
        self.infoArea.AppendText(newline)
        #self.infoArea.AppendText("Server latency = %d ms\n" % self._PyHocaGUI.getServerLatency())
        self.infoArea.AppendText(2*halftab+'%s (%s)\n' % ('x2goserver', server_components['x2goserver']))
        if 'x2goserver-common' in server_components.keys():
            self.infoArea.AppendText(2*halftab+'%s (%s)\n' % ('x2goserver-common', server_components['x2goserver-common']))
        self.infoArea.AppendText(2*halftab+'%s (%s)\n' % ('x2goagent', server_components['x2goagent']))
        self.infoArea.AppendText('\n')
        if server_extensions:
            self.infoArea.AppendText(halftab+_(u'Server Extensions')+':'+newline)
            self.infoArea.AppendText(newline)
            for comp in server_extensions:
                self.infoArea.AppendText(2*halftab+'%s (%s)\n' % (comp, server_components[comp]))
        self.infoArea.AppendText('\n')
        if server_addons:
            self.infoArea.AppendText(_(u'X2Go Server Add-ons')+':'+2*newline)
            for comp in server_addons:
                self.infoArea.AppendText(2*halftab+'%s (%s)\n' % (comp, server_components[comp]))
        self.infoArea.AppendText('\n')
        self.infoArea.AppendText(_(u'X2Go Server Features')+':'+2*newline)
        for feature in server_features:
            self.infoArea.AppendText(2*halftab+'%s\n' % (feature))
        self.infoArea.ShowPosition(0)

    def _refreshServerInfo(self):
        halftab = '    '
        newline = '\n'

        self.infoArea.AppendText(newline)
        self.infoArea.AppendText("Network latency \t= %d ms ( <75 is good )\n" % self._PyHocaGUI.getServerLatency())
        cmdlatency = "failed"
        starttime = datetime.datetime.now()
        #run status cmd on server and get as string
        server_info = self._PyHocaGUI.get_apprime_server_info(self.current_profile_name)
        endtime = datetime.datetime.now()
        diff = endtime - starttime
        cmdlatency = (int)(diff.seconds*1000 + diff.microseconds/1000)
        self.infoArea.AppendText(newline)
        self.infoArea.AppendText("Command RTT \t= %d ms ( <250 is good )\n" % cmdlatency)
        self.infoArea.AppendText(newline)
        self.infoArea.AppendText(newline)
        self.infoArea.AppendText(server_info)
        self.infoArea.ShowPosition(0)

    def OnRefreshServerInfo(self, evt):
        """\
        Gets called if the Refresh button gets pressed.

        @param evt: event
        @type evt: C{obj}

        """
        self.infoArea.Clear()
        self._refreshServerInfo()

    def OnCancel(self, evt):
        """\
        Continue here, if the user clicks the Cancel button in the dialog box.

        @param evt: event
        @type evt: C{obj}

        """
        self.Hide()
        self.cancel = True

    def Hide(self):
        """\
        When hiding the server info box, remove it from the list of open windows in the main application instance.

        """
        try:
            self._PyHocaGUI._sub_windows.remove(self)
        except (AttributeError, ValueError):
            pass
        self.Show(False)

    def Close(self):
        """\
        Do some PyHocaGUI specific cleanup if this window gets destroyed.

        """
        try:
            self._PyHocaGUI._sub_windows.remove(self)
        except ValueError:
            pass
        try:
            self._PyHocaGUI._temp_disabled_profile_names.remove(self.current_profile_name)
        except ValueError:
            pass
        wx.Dialog.Close(self)
        wx.Dialog.Destroy(self)
