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
# ... NONE ...

if os.environ.has_key('DESKTOP_SESSION'):
    WINDOW_MANAGER = os.environ['DESKTOP_SESSION']
else:
    WINDOW_MANAGER = 'generic'

class PyHocaGUI_DialogBoxListDesktops(wx.Dialog):
    """\
    Dialog box for selection from a list of sharable desktops.

    """
    def __init__(self, _PyHocaGUI, profile_name):
        """\
        Desktop list and selection dialog box (constructor).

        @param _PyHocaGUI: the master/parent object of the application
        @type _PyHocaGUI: C{obj}
        @param profile_name: session profile name
        @type profile_name: C{str}

        """
        self._PyHocaGUI = _PyHocaGUI
        self._pyhoca_logger = self._PyHocaGUI._pyhoca_logger
        self._pyhoca_logger('desktop list selection box started', loglevel=x2go.loglevel_INFO, )

        self.connect = False
        self.cancel = False

        self.current_profile_name = profile_name
        self.list_index = 0
        self.listed_desktops = {}

        wx.Dialog.__init__(self, None, id=-1, title=profile_name, style=wx.DEFAULT_FRAME_STYLE, )
        self._PyHocaGUI._sub_windows.append(self)

        self.SetTitle(_(u'Share Desktop Session - %s') % profile_name)

        self.titleLbl = wx.StaticText(self, wx.ID_ANY, _(u'Select one of the available desktop sessions on this server')+':', size=(-1, -1))
        self.desktopList = wx.ListCtrl(self, size=(420,140),
                                       style=wx.LC_REPORT|wx.BORDER_SUNKEN|wx.LC_SINGLE_SEL)
        self.desktopList.InsertColumn(0, 'Display')
        self.desktopList.InsertColumn(1, 'User')

        self.shareMode0 = wx.RadioButton(self, -1, _(u"View session only"), style=wx.RB_GROUP)
        self.shareMode1 = wx.RadioButton(self, -1, _(u"Gain full access"))
        self.share_mode = 0

        ID_REFRESH = wx.NewId()
        self.okBtn = wx.Button(self, wx.ID_OK, _(u'Share Desktop'), )
        self.okBtn.SetDefault()
        self.okBtn.Enable(False)
        self.refreshBtn = wx.Button(self, ID_REFRESH, _(u'Refresh list'), )
        self.cancelBtn = wx.Button(self, wx.ID_CANCEL, _(u'Cancel'), )

        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.OnListClick, self.desktopList)
        self.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.OnListDoubleClick, self.desktopList)
        self.Bind(wx.EVT_BUTTON, self.OnOk, self.okBtn)
        self.Bind(wx.EVT_BUTTON, self.OnRefreshDesktopList, self.refreshBtn)
        self.Bind(wx.EVT_BUTTON, self.OnCancel, self.cancelBtn)

        titleSizer = wx.BoxSizer(wx.HORIZONTAL)
        listSizer = wx.BoxSizer(wx.HORIZONTAL)
        modeSizer = wx.BoxSizer(wx.HORIZONTAL)
        btnSizer = wx.BoxSizer(wx.HORIZONTAL)
        mainSizer = wx.BoxSizer(wx.VERTICAL)

        titleSizer.Add(self.titleLbl, 0, wx.ALL, 5)

        listSizer.Add(self.desktopList, 0, wx.ALL|wx.EXPAND, 5)

        modeSizer.Add(self.shareMode0, 0, wx.ALL, 5)
        modeSizer.Add(self.shareMode1, 0, wx.ALL, 5)

        btnSizer.Add(self.okBtn, 0, wx.ALL, 5)
        btnSizer.Add(self.refreshBtn, 0, wx.ALL, 5)
        btnSizer.Add(self.cancelBtn, 0, wx.ALL, 5)

        mainSizer.Add(titleSizer, 0, wx.ALL, 5)
        mainSizer.Add(listSizer, 0, wx.ALL|wx.EXPAND, 5)
        mainSizer.Add(modeSizer, 0, wx.ALL, 5)
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
        self._refreshDesktopList()

    def ShowModal(self, **kwargs):
        self._PyHocaGUI._sub_windows.append(self)
        wx.Dialog.ShowModal(self, **kwargs)

    def add_item(self, display, user):
        self.listed_desktops.update({ self.list_index: '%s@%s' % (user, display) })
        self.desktopList.InsertStringItem(self.list_index, display)
        self.desktopList.SetStringItem(self.list_index, 1, user)
        self.list_index += 1

    def _refreshDesktopList(self):
        self.desktopList.DeleteAllItems()
        self.listed_desktops = {}
        self.list_index = 0
        desktops = self._PyHocaGUI._X2GoClient__list_desktops(profile_name=self.current_profile_name, exclude_session_types=['R', 'S', 'P'])
        for desktop in desktops:
            if len(desktop.split('@')) >= 2:
                display = desktop.split('@')[0]
                user = desktop.split('@')[1]
                self.add_item(user, display)

    def OnListDoubleClick(self, evt):
        """\
        On double click select item and auto-click Ok button.

        @param evt: event
        @type evt: C{obj}

        """
        self.OnListClick(evt)
        self.OnOk(evt)

    def OnListClick(self, evt):
        """\
        Enable the Connect button only if a list item got clicked.

        @param evt: event
        @type evt: C{obj}

        """
        self.okBtn.Enable(True)

    def OnRefreshDesktopList(self, evt):
        """\
        Gets called if the Refresh button gets pressed.

        @param evt: event
        @type evt: C{obj}

        """
        self._refreshDesktopList()

    def OnOk(self, evt):
        """\
        Continue here, if the user clicks the Ok button in the dialog box.

        @param evt: event
        @type evt: C{obj}

        """
        self.Hide()
        self.connect = True
        self.share_mode = self.shareMode1.GetValue() and 1 or 0

    def GetResult(self):
        """\
        Retrieve the result of the selection in the list box.

        """
        return self.desktopList.GetValue()

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
        When hiding the list desktops box, remove it from the list of open windows in the main application instance.

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

    def GetSelectedItems(self):
        """\
        Gets the selected items for the list control.
        Selection is returned as a list of selected indices,
        low to high.

        """
        selection = []
        idx = self.desktopList.GetFirstSelected()
        selection.append(idx)
        while len(selection) != self.desktopList.GetSelectedItemCount():
            idx = self.desktopList.GetNextSelected(idx)
            selection.append(idx)

        return selection

    def GetSelectedDesktop(self):
        idx = self.GetSelectedItems()[0]
        return self.listed_desktops[idx]
