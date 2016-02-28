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

import messages

if os.environ.has_key('DESKTOP_SESSION'):
    WINDOW_MANAGER = os.environ['DESKTOP_SESSION']
else:
    WINDOW_MANAGER = 'generic'

class PyHocaGUI_BrokerDialogBoxPassword(wx.Dialog):
    """\
    Broker logon window for L{PyHocaGUI}.

    """
    def __init__(self, _PyHocaGUI, caller=None):
        """\
        Broker logon window (constructor)

        @param _PyHocaGUI: main application instance
        @type _PyHocaGUI: C{obj}

        """
        self._PyHocaGUI = _PyHocaGUI
        self._PyHocaGUI.gevent_sleep_when_idle = 0.1
        self._pyhoca_logger = self._PyHocaGUI._pyhoca_logger
        self._pyhoca_logger('password dialog box started', loglevel=x2go.loglevel_INFO, )

        wx.Dialog.__init__(self, None, id=-1, title=self._PyHocaGUI.broker_name + ' ' + _(u'Logon'), style=wx.DEFAULT_FRAME_STYLE, )
        self._PyHocaGUI._sub_windows.append(self)

        self.brokerLbl = wx.StaticText(self, wx.ID_ANY, _(u'Broker URL')+':', size=(-1, -1))
        self.brokerTxt = wx.TextCtrl(self, wx.ID_ANY, '', style=wx.TE_PROCESS_ENTER, size=(240, -1))

        self.userLbl = wx.StaticText(self, wx.ID_ANY, _(u'Username')+':', size=(-1, -1))
        self.userTxt = wx.TextCtrl(self, wx.ID_ANY, '', style=wx.TE_PROCESS_ENTER, size=(240, -1))

        self.passwordLbl = wx.StaticText(self, wx.ID_ANY, _(u'Password')+':', size=(-1, -1))
        self.passwordTxt = wx.TextCtrl(self, wx.ID_ANY, '', style=wx.TE_PROCESS_ENTER|wx.TE_PASSWORD, size=(240, -1))
        self.passwordTxt.SetFocus()

        if self._PyHocaGUI.session_profiles.get_broker_username():
            self.userTxt.SetValue(self._PyHocaGUI.session_profiles.get_broker_username())
        else:
            self.userTxt.SetFocus()

        if self._PyHocaGUI.session_profiles.get_broker_url():
            if self._PyHocaGUI.session_profiles.get_broker_url().upper() in ('HTTP', 'SSH'):
                self.brokerTxt.SetFocus()
                if self._PyHocaGUI.session_profiles.get_broker_type() == 'http':
                    self.brokerTxt.SetValue('http://<host>[:<port>]/json/')
                    self.userTxt.SetValue('<user>')
                elif self._PyHocaGUI.session_profiles.get_broker_type() == 'ssh':
                    self.brokerTxt.SetValue('ssh://<host>[:<port>]/usr/bin/x2gobroker')
                    self.userTxt.SetValue('<user>')
            else:
                self.brokerTxt.SetValue(self._PyHocaGUI.session_profiles.get_broker_url())

        self.loginBtn = wx.Button(self, wx.ID_OK, _(u'Authenticate'), )
        self.loginBtn.SetDefault()
        self.cancelBtn = wx.Button(self, wx.ID_CANCEL, _(u'Cancel'), )
        _tab_order = [self.userTxt, self.passwordTxt, self.loginBtn, self.cancelBtn, ]

        self.Bind(wx.EVT_BUTTON, self.OnLogin, self.loginBtn)
        self.Bind(wx.EVT_TEXT_ENTER, self.OnLogin, self.brokerTxt)
        self.Bind(wx.EVT_TEXT_ENTER, self.OnLogin, self.userTxt)
        self.Bind(wx.EVT_TEXT_ENTER, self.OnLogin, self.passwordTxt)
        self.Bind(wx.EVT_BUTTON, self.OnCancel, self.cancelBtn)

        btnSizer = wx.BoxSizer(wx.HORIZONTAL)
        mainSizer = wx.BoxSizer(wx.VERTICAL)

        credSizer = wx.GridBagSizer(hgap=2, vgap=3)
        credSizer.Add(self.brokerLbl, pos=(0,0), flag=wx.LEFT|wx.ALIGN_CENTER_VERTICAL, border=5)
        credSizer.Add(self.brokerTxt, pos=(0,1), flag=wx.ALL, border=5)
        credSizer.Add(self.userLbl, pos=(1,0), flag=wx.LEFT|wx.ALIGN_CENTER_VERTICAL, border=5)
        credSizer.Add(self.userTxt, pos=(1,1), flag=wx.ALL, border=5)
        credSizer.Add(self.passwordLbl, pos=(2,0), flag=wx.LEFT|wx.ALIGN_CENTER_VERTICAL, border=5)
        credSizer.Add(self.passwordTxt, pos=(2,1), flag=wx.ALL, border=5)

        btnSizer.Add(self.loginBtn, 0, wx.ALL, 5)
        btnSizer.Add(self.cancelBtn, 0, wx.ALL, 5)

        mainSizer.Add(credSizer, 0, wx.ALL, 5)
        mainSizer.Add(btnSizer, 0, wx.ALL|wx.ALIGN_RIGHT, 5)

        # Logged in variable
        self.loggedIn = False

        self.SetSizerAndFit(mainSizer)
        self.Layout()

        for i in xrange(len(_tab_order) - 1):
            _tab_order[i+1].MoveAfterInTabOrder(_tab_order[i])

        maxX, maxY = wx.GetDisplaySize()

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

    def OnLogin(self, evt):
        """\
        If the user clicks ,,Ok'' in the logon window.

        @param evt: event
        @type evt: C{obj}

        """
        broker_url = self.brokerTxt.GetValue()
        username = self.userTxt.GetValue()
        password = self.passwordTxt.GetValue()

        self._PyHocaGUI.session_profiles.set_broker_url(broker_url)
        try:
            if self._PyHocaGUI.session_profiles.broker_simpleauth(username, password):
                self._PyHocaGUI.notifier.send(_(u"%s - success") % self._PyHocaGUI.broker_name, _(u"Authentication to session broker has been\nsuccessful."), icon='auth_success', timeout=10000)
            else:
                self._PyHocaGUI.notifier.send(_(u"%s - failure") % self._PyHocaGUI.broker_name, _(u"Authentication to session broker failed."), icon='auth_failed', timeout=10000)
            self.Close()
            self.Destroy()
        except x2go.x2go_exceptions.X2GoBrokerConnectionException:
            m = messages.PyHoca_MessageWindow_YesNo(self._PyHocaGUI, title=_(u'%s: Connection refused error') % self._PyHocaGUI.appname, msg=_(u'Connection to %s failed. Retry?') % self._PyHocaGUI.broker_name, icon='connect_error')
            m.ShowModal()
            if m.No():
                self.Close()
                self.Destroy()

    def OnCancel(self, evt):
        """
        If the user clicks ,,Cancel'' in the logon window.

        @param evt: event
        @type evt: C{obj}

        """
        self.Close()
        self.Destroy()

    def Destroy(self):
        """
        Tidy up some stuff in the main application instance when the logon window gets destroyed.

        """
        self._PyHocaGUI.gevent_sleep_when_idle = 0.25
        try:
            self._PyHocaGUI._sub_windows.remove(self)
        except ValueError:
            pass
        wx.Dialog.Destroy(self)
