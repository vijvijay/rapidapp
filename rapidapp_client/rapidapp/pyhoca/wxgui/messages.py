# -*- coding: utf-8 -*-

# Copyright (C) 2010 by Mike Gabriel <mike.gabriel@das-netzwerkteam.de>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program; if not, write to the
# Free Software Foundation, Inc.,
# 51 Franklin St, Fifth Floor, Boston, MA 02110-1301, USA.

# Contributors to the code of this programme:
#     Dick Kniep <dick.kniep@lindix.nl>


import wx
import os

# PyHoca-GUI modules
import basepath

# X2Go modules
from x2go.defaults import CURRENT_LOCAL_USER as _CURRENT_LOCAL_USER

class PyHoca_MessageWindow(wx.Dialog):
    """\
    A simple message window for L{PyHocaGUI}.

    """
    def __init__(self, _PyHocaGUI, parent=None, title=None, shortmsg=None, msg=None, icon=None, buttontype='ok',
                 profile_name=None,
                 session_name=None):
        """\
        L{PyHocaGUI} message window.

        @param _PyHocaGUI: main application instance
        @type _PyHocaGUI: C{obj}
        @param parent: the parent (calling) object
        @type parent: C{obj}
        @param title: window title
        @type title: C{str}
        @param shortmsg: a short string that refers to a pre-defined message (hard-coded in this class)
        @type shortmsg: C{str}
        @param msg: the message to be shown in this message box (alternative to C{shortmsg})
        @type msg: C{str}
        @param icon: icon name for an icon to be shown left of the text in this message box
        @type icon: C{str}
        @param buttontype: button types can be: C{ok}, C{okcancel}, C{cancelok}, C{yesno}, and C{noyes}
        @type buttontype: C{str}
        @param profile_name: session profile name of the profile this message box refers to
        @type profile_name: C{str}
        @param session_name: X2Go session name of the session this message box refers to
        @type session_name: C{str}

        """
        self._PyHocaGUI = _PyHocaGUI

        try: wx.EndBusyCursor()
        except: pass

        self._pyhoca_messages = {
            'REALLY_DELETE_PROFILE': _(u'Are you really sure you want to\ndelete the session profile ,,%s\'\'?') % profile_name,
            'ALREADY_RUNNING': _(u'{appname} is already running for user ,,{username}\'\'!\n\nOnly one instance of {appname} can be started per\nuser. The {appname} icon can be found in your desktop\'s\nnotification area/systray.').format(appname=self._PyHocaGUI.appname, username=_CURRENT_LOCAL_USER)
        }


        if shortmsg is None:
            show_message = msg
        elif shortmsg in self._pyhoca_messages.keys():
            show_message = self._pyhoca_messages[shortmsg]
        else:
            show_message = 'No message has been given...'

        self.show_message = show_message
        self.result = None

        try:
            if parent is None:
                parent = self._PyHocaGUI.about
        except AttributeError:
            pass

        wx.Dialog.__init__(self, parent, wx.ID_ANY, )
        self.SetTitle('%s' % title)

        _icons_location = basepath.icons_basepath
        icon_folder = 'PyHoca'
        if os.path.isdir(os.path.join(_icons_location, _PyHocaGUI.appname)):
            icon_folder = _PyHocaGUI.appname

        if icon:
            path_to_icon = os.path.normpath('%s/%s/64x64/%s.png' % (_icons_location, icon_folder, icon))
            self.icon = wx.StaticBitmap(self, wx.ID_ANY, wx.Bitmap(path_to_icon, wx.BITMAP_TYPE_ANY))
        self.message = wx.StaticText(self, wx.ID_ANY, self.show_message, size=(-1, -1), style=wx.ALIGN_LEFT)

        btnSizer = wx.BoxSizer(wx.HORIZONTAL)
        msgSizer = wx.BoxSizer(wx.HORIZONTAL)
        mainSizer = wx.BoxSizer(wx.VERTICAL)

        if buttontype in ('yesno', 'noyes'):
            self.yesBtn = wx.Button(self, wx.ID_ANY, _(u'Yes'),)
            self.noBtn = wx.Button(self, wx.ID_ANY, _(u'No'))

            self.Bind(wx.EVT_BUTTON, self.OnTrue, self.yesBtn)
            self.Bind(wx.EVT_BUTTON, self.OnFalse, self.noBtn)

            btnSizer.Add(self.yesBtn, flag=wx.ALL, border=5)
            btnSizer.Add(self.noBtn, flag=wx.ALL, border=5)

            if buttontype == 'yesno':
                self.yesBtn.SetDefault()
                self.yesBtn.SetFocus()
            elif buttontype == 'noyes':
                self.noBtn.SetDefault()
                self.noBtn.SetFocus()

        if buttontype in ('ok', 'okcancel', 'cancelok'):

            self.okBtn = wx.Button(self, wx.ID_ANY, _(u'Ok'),)
            self.Bind(wx.EVT_BUTTON, self.OnTrue, self.okBtn)
            btnSizer.Add(self.okBtn, flag=wx.ALL, border=5)

        if buttontype in ('okcancel', 'cancelok'):

            self.cancelBtn = wx.Button(self, wx.ID_ANY, _(u'Cancel'))
            self.Bind(wx.EVT_BUTTON, self.OnFalse, self.cancelBtn)
            btnSizer.Add(self.cancelBtn, flag=wx.ALL, border=5)

        if buttontype in ('ok', 'okcancel'):
            self.okBtn.SetDefault()
            self.okBtn.SetFocus()

        if buttontype == 'cancelok':
            self.cancelBtn.SetDefault()
            self.cancelBtn.SetFocus()

        if icon:
            msgSizer.Add(self.icon, flag=wx.RIGHT, border=15)
        msgSizer.Add(self.message, flag=wx.ALL, border=0)
        mainSizer.Add(msgSizer, flag=wx.ALL, border=10)
        mainSizer.Add(btnSizer, flag=wx.ALL|wx.ALIGN_RIGHT, border=5)

        self.SetSizerAndFit(mainSizer)
        self.Layout()

        maxX, maxY = wx.GetDisplaySize()

        self.Move((maxX/2 - self.GetSize().GetWidth()/2, maxY/2 - self.GetSize().GetHeight()/2))
        try:
            self._PyHocaGUI._sub_windows.append(self)
        except AttributeError:
            pass

    def OnTrue(self, evt):
        """\
        Gets called if the user clicks on ,,Yes'' or ,,Ok''.

        @param evt: event
        @type evt: C{obj}

        """
        self.result = True
        self.Hide()

    def OnFalse(self, evt):
        """\
        Gets called if the user clicks on ,,No'' or ,,Cancel''.

        @param evt: event
        @type evt: C{obj}

        """
        self.result = False
        self.Hide()

    def Ok(self):
        """\
        Evaluate the result what the user chose in the message window.

        @return: C{True}, if ,,Ok'' had been chosen
        @rtype: C{bool}

        """
        return self.Yes()

    def Cancel(self):
        """\
        Evaluate the result what the user chose in the message window.

        @return: C{True}, if ,,Cancel'' had been chosen
        @rtype: C{bool}

        """
        return not self.No()

    def Yes(self):
        """\
        Evaluate the result what the user chose in the message window.

        @return: C{True}, if ,,Yes'' had been chosen
        @rtype: C{bool}

        """
        return self.result

    def No(self):
        """\
        Evaluate the result what the user chose in the message window.

        @return: C{True}, if ,,No'' had been chosen
        @rtype: C{bool}

        """
        return not self.Yes()

    def Hide(self):
        """\
        When hiding the message box, remove it from the list of open windows in the main application instance.

        """
        try:
            self._PyHocaGUI._sub_windows.remove(self)
        except AttributeError:
            pass
        self.Show(False)


class PyHoca_MessageWindow_Ok(PyHoca_MessageWindow):
    """\
    A simple ,,Ok'' message window for L{PyHocaGUI}.

    """
    def __init__(self, _PyHocaGUI, parent=None, title=None, shortmsg=None, msg=None, icon='session_warning', **kwargs):
        """\
        @param _PyHocaGUI: main application instance
        @type _PyHocaGUI: C{obj}
        @param parent: the parent (calling) object
        @type parent: C{obj}
        @param title: window title
        @type title: C{str}
        @param shortmsg: a short string that refers to a pre-defined message (hard-coded in this class)
        @type shortmsg: C{str}
        @param msg: the message to be shown in this message box (alternative to C{shortmsg})
        @type msg: C{str}
        @param icon: icon name for an icon to be shown left of the text in this message box
        @type icon: C{str}
        @param kwargs: any other optional argument (will be ignored)
        @type kwargs: C{dict}

        """
        PyHoca_MessageWindow.__init__(self, _PyHocaGUI, parent=parent, title=title, shortmsg=shortmsg, msg=msg, icon=icon, buttontype='ok', **kwargs)


class PyHoca_MessageWindow_OkCancel(PyHoca_MessageWindow):
    """\
    A simple ,,Ok+Cancel'' (default: Ok) message window for L{PyHocaGUI}.

    """
    def __init__(self, _PyHocaGUI, parent=None, title=None, shortmsg=None, msg=None, icon='session_warning', **kwargs):
        """\
        @param _PyHocaGUI: main application instance
        @type _PyHocaGUI: C{obj}
        @param parent: the parent (calling) object
        @type parent: C{obj}
        @param title: window title
        @type title: C{str}
        @param shortmsg: a short string that refers to a pre-defined message (hard-coded in this class)
        @type shortmsg: C{str}
        @param msg: the message to be shown in this message box (alternative to C{shortmsg})
        @type msg: C{str}
        @param icon: icon name for an icon to be shown left of the text in this message box
        @type icon: C{str}
        @param kwargs: any other optional argument (will be ignored)
        @type kwargs: C{dict}

        """
        PyHoca_MessageWindow.__init__(self, _PyHocaGUI, parent=parent, title=title, shortmsg=shortmsg, msg=msg,  icon=icon, buttontype='okcancel', **kwargs)


class PyHoca_MessageWindow_CancelOk(PyHoca_MessageWindow):
    """\
    A simple ,,Ok+Cancel'' (default: Cancel) message window for L{PyHocaGUI}.

    """
    def __init__(self, _PyHocaGUI, parent=None, title=None, shortmsg=None, msg=None, icon='session_warning', **kwargs):
        """\
        @param _PyHocaGUI: main application instance
        @type _PyHocaGUI: C{obj}
        @param parent: the parent (calling) object
        @type parent: C{obj}
        @param title: window title
        @type title: C{str}
        @param shortmsg: a short string that refers to a pre-defined message (hard-coded in this class)
        @type shortmsg: C{str}
        @param msg: the message to be shown in this message box (alternative to C{shortmsg})
        @type msg: C{str}
        @param icon: icon name for an icon to be shown left of the text in this message box
        @type icon: C{str}
        @param kwargs: any other optional argument (will be ignored)
        @type kwargs: C{dict}

        """
        PyHoca_MessageWindow.__init__(self, _PyHocaGUI, parent=parent, title=title, shortmsg=shortmsg, msg=msg, icon=icon, buttontype='cancelok', **kwargs)


class PyHoca_MessageWindow_YesNo(PyHoca_MessageWindow):
    """\
    A simple ,,Yes+No'' (default: Yes) message window for L{PyHocaGUI}.

    """
    def __init__(self, _PyHocaGUI, parent=None, title=None, shortmsg=None, msg=None, icon='session_warning', **kwargs):
        """\
        @param _PyHocaGUI: main application instance
        @type _PyHocaGUI: C{obj}
        @param parent: the parent (calling) object
        @type parent: C{obj}
        @param title: window title
        @type title: C{str}
        @param shortmsg: a short string that refers to a pre-defined message (hard-coded in this class)
        @type shortmsg: C{str}
        @param msg: the message to be shown in this message box (alternative to C{shortmsg})
        @type msg: C{str}
        @param icon: icon name for an icon to be shown left of the text in this message box
        @type icon: C{str}
        @param kwargs: any other optional argument (will be ignored)
        @type kwargs: C{dict}

        """
        PyHoca_MessageWindow.__init__(self, _PyHocaGUI, parent=parent, title=title, shortmsg=shortmsg, msg=msg, icon=icon, buttontype='yesno', **kwargs)

class PyHoca_MessageWindow_NoYes(PyHoca_MessageWindow):
    """\
    A simple ,,Yes+No'' (default: No) message window for L{PyHocaGUI}.

    """
    def __init__(self, _PyHocaGUI, parent=None, title=None, shortmsg=None, msg=None, icon='session_warning', **kwargs):
        """\
        @param _PyHocaGUI: main application instance
        @type _PyHocaGUI: C{obj}
        @param parent: the parent (calling) object
        @type parent: C{obj}
        @param title: window title
        @type title: C{str}
        @param shortmsg: a short string that refers to a pre-defined message (hard-coded in this class)
        @type shortmsg: C{str}
        @param msg: the message to be shown in this message box (alternative to C{shortmsg})
        @type msg: C{str}
        @param icon: icon name for an icon to be shown left of the text in this message box
        @type icon: C{str}
        @param kwargs: any other optional argument (will be ignored)
        @type kwargs: C{dict}

        """
        PyHoca_MessageWindow.__init__(self, _PyHocaGUI, parent=parent, title=title, shortmsg=shortmsg, msg=msg, icon=icon, buttontype='noyes', **kwargs)

