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
from x2go import X2GOCLIENT_OS
from x2go import log
if X2GOCLIENT_OS in ('Linux', 'Mac'):
    import pynotify
import exceptions
import basepath

import x2go.utils as utils

class NotSupportedException(exceptions.StandardError): pass
class PyHocaNotificationException(exceptions.StandardError): pass

class libnotify_NotifierPopup(object):
    """\
    L{PyHocaGUI} notification utilizing C{libnotify}, used on Linux/Unix OS.

    """
    title = {}
    text = {}
    icon = {}
    timeout = {}

    def __init__(self, _PyHocaGUI):
        """\
        Notifier popup (constructor).

        @param _PyHocaGUI: main application instance
        @type _PyHocaGUI: C{obj}

        """
        self._PyHocaGUI = _PyHocaGUI
        self._pyhoca_logger = self._PyHocaGUI._pyhoca_logger

        if not pynotify.init("PyHocaGUI"):
            raise NotSupportedException

    def prepare(self, context, title=None, text=None, icon=None, timeout=None):
        """\
        Prepare a notification that gets sent to C{libnotify} later (by the L{send()} method).

        Use C{context} as a unique identifier. When sending the notification later, C{context}
        will unequivocally map to the notification content that shall get sent.

        @param context: a unique identifier for this notification preparation
        @type context: C{str}
        @param title: notification title
        @type title: C{str}
        @param text: notification text
        @type text: C{str}
        @param icon: icon name for an icon that appears with the notification
        @type icon: C{str}
        @param timeout: let notification disappear after C{<timeout>} milliseconds
        @type timeout: C{int}

        """
        if title is not None:
            self.title[context] = title
        if text is not None:
            self.text[context] = text
        if icon is not None:
            self.icon[context] = icon
        if timeout is not None:
            self.timeout[context] = timeout

    def send(self, title=None, text=None, context=None, icon=None, timeout=8000):
        """\
        Send notifications directly (or use a prepared notification).

        @param title: notification title
        @type title: C{str}
        @param text: notification text
        @type text: C{str}
        @param context: an identifier that refers to a prepared notification
        @type context: C{str}
        @param icon: icon name for an icon that appears with the notification
        @type icon: C{str}
        @param timeout: let notification disappear after C{<timeout>} milliseconds
        @type timeout: C{int}

        @raise PyHocaNotificationException: if notification failed

        """
        if context is not None:
            try:
                title = self.title[context]
                del self.title[context]
            except KeyError:
                pass
            try:
                text = self.text[context]
                del self.text[context]
            except KeyError:
                pass
            try:
                icon = self.icon[context]
                del self.icon[context]
            except KeyError:
                pass
            try:
                timeout = self.timeout[context]
                del self.timeout[context]
            except KeyError:
                pass

        _icons_location = basepath.icons_basepath
        if icon:
            icon = 'file://%s/PyHoca/32x32/%s.png' % (_icons_location, icon)

        if title and text:
            self._pyhoca_logger('[%s] %s' % (title.encode(utils.get_encoding()), text.encode(utils.get_encoding())), loglevel=log.loglevel_NOTICE)

        try:
            if not self._PyHocaGUI.disable_notifications and title and text:
                n = pynotify.Notification(title, text, icon)
                n.set_urgency(pynotify.URGENCY_NORMAL)
                n.set_timeout(timeout)
                n.show()
        except:
            pass

    def Close(self):
        """\
        Provide a C{Close()} method which does nothing.

        """
        pass

    def Destroy(self):
        """\
        Provide a C{Destroy()} method which does nothing.

        """
        pass


class showballoon_NotifierPopup(object):
    """\
    L{PyHocaGUI} notification utilizing C{wx.TaskBarIcon.ShowBalloon()}, used on Windows OS.

    """
    title = {}
    text = {}
    icon = {}
    timeout = {}

    def __init__(self, _about):
        """\
        Notifier popup (constructor).

        @param _about: main application window
        @type _about: C{obj}

        """
        self._PyHocaGUI = _about._PyHocaGUI
        self._pyhoca_logger = self._PyHocaGUI._pyhoca_logger

    def prepare(self, context, title=None, text=None, icon=None, timeout=None):
        """\
        Prepare a notification that gets sent to C{libnotify} later (by the L{send()} method).

        Use C{context} as a unique identifier. When sending the notification later, C{context}
        will unequivocally map to the notification content that shall get sent.

        @param context: a unique identifier for this notification preparation
        @type context: C{str}
        @param title: notification title
        @type title: C{str}
        @param text: notification text
        @type text: C{str}
        @param icon: icon name for an icon that appears with the notification
        @type icon: C{str}
        @param timeout: let notification disappear after C{<timeout>} milliseconds
        @type timeout: C{int}

        """
        if title is not None:
            self.title[context] = title
        if text is not None:
            self.text[context] = text
        if icon is not None:
            self.icon[context] = icon
        if timeout is not None:
            self.timeout[context] = timeout

    def send(self, title=None, text=None, context=None, icon=None, timeout=8000):
        """\
        Send notifications directly (or use a prepared notification).

        @param title: notification title
        @type title: C{str}
        @param text: notification text
        @type text: C{str}
        @param context: an identifier that refers to a prepared notification
        @type context: C{str}
        @param icon: icon name for an icon that appears with the notification
        @type icon: C{str}
        @param timeout: let notification disappear after C{<timeout>} milliseconds
        @type timeout: C{int}

        """
        if context is not None:
            try:
                title = self.title[context]
                del self.title[context]
            except KeyError:
                pass
            try:
                text = self.text[context]
                del self.text[context]
            except KeyError:
                pass
            try:
                icon = self.icon[context]
                del self.icon[context]
            except KeyError:
                pass
            try:
                timeout = self.timeout[context]
                del self.timeout[context]
            except KeyError:
                pass

        # libnotify timeouts are given in millisecs, on Windows we use seconds...
        timeout = timeout / 1000

        _icon_map_wx = {
            'audio_error': wx.ICON_ERROR,
            'auth_success': wx.ICON_INFORMATION,
            'auth_failed': wx.ICON_WARNING,
            'auth_error': wx.ICON_ERROR,
            'auth_disconnect': wx.ICON_INFORMATION,
            'profile_add': wx.ICON_INFORMATION,
            'profile_delete': wx.ICON_INFORMATION,
            'profile_edit': wx.ICON_INFORMATION,
            'profile_save': wx.ICON_INFORMATION,
            'profile_error': wx.ICON_ERROR,
            'session_cleanall': wx.ICON_INFORMATION,
            'session_error': wx.ICON_ERROR,
            'session_pause': wx.ICON_INFORMATION,
            'session_printing': wx.ICON_INFORMATION,
            'session_resume': wx.ICON_INFORMATION,
            'session_start': wx.ICON_INFORMATION,
            'session_terminate': wx.ICON_INFORMATION,
            'session_warning': wx.ICON_WARNING,
        }
        if icon in _icon_map_wx.keys():
           icon = _icon_map_wx[icon]
        else:
           icon = wx.ICON_INFORMATION

        try:
            if not self._PyHocaGUI.disable_notifications and title and text:
                # you will need wxPython >= 2.9 for this
                self._PyHocaGUI.taskbar.ShowBalloon(
                    title,
                    text,
                    timeout*1000,
                    icon,
                )
        except:
            pass

        if title and text:
            # on Windows some error messages are already encoded, some are not, depending from which module they come
            try: _title = title.encode(utils.get_encoding())
            except: _title = title
            try: _text = text.encode(utils.get_encoding())
            except: _text = text

            try: self._pyhoca_logger('['+_title+'] '+_text, loglevel=log.loglevel_NOTICE)
            except UnicodeDecodeError: self._pyhoca_logger('Unicode error occurred while rendering a log message...', loglevel=log.loglevel_WARN)

    def Close(self):
        """\
        Provide a C{Close()} method which does nothing.

        """
        pass

    def Destroy(self):
        """\
        Provide a C{Destroy()} method which does nothing.

        """
        pass


class notificationmessage_NotifierPopup(object):
    """\
    L{PyHocaGUI} notification utilizing C{wx.NotificationMessage()}, used on Windows OS.

    Note: C{wx.NotificationMessage()} has only been added to wxPython in version 2.9.x.

    """
    title = {}
    text = {}
    icon = {}
    timeout = {}

    def __init__(self, _about):
        """\
        Notifier popup (constructor).

        @param _about: main application window
        @type _about: C{obj}

        """
        self._PyHocaGUI = _about._PyHocaGUI
        self._pyhoca_logger = self._PyHocaGUI._pyhoca_logger

    def prepare(self, context, title=None, text=None, icon=None, timeout=None):
        """\
        Prepare a notification that gets sent to C{libnotify} later (by the L{send()} method).

        Use C{context} as a unique identifier. When sending the notification later, C{context}
        will unequivocally map to the notification content that shall get sent.

        @param context: a unique identifier for this notification preparation
        @type context: C{str}
        @param title: notification title
        @type title: C{str}
        @param text: notification text
        @type text: C{str}
        @param icon: icon name for an icon that appears with the notification
        @type icon: C{str}
        @param timeout: let notification disappear after C{<timeout>} milliseconds
        @type timeout: C{int}

        """
        if title is not None:
            self.title[context] = title
        if text is not None:
            self.text[context] = text
        if icon is not None:
            self.icon[context] = icon
        if timeout is not None:
            self.timeout[context] = timeout

    def send(self, title=None, text=None, context=None, icon=None, timeout=8000):
        """\
        Send notifications directly (or use a prepared notification).

        @param title: notification title
        @type title: C{str}
        @param text: notification text
        @type text: C{str}
        @param context: an identifier that refers to a prepared notification
        @type context: C{str}
        @param icon: icon name for an icon that appears with the notification
        @type icon: C{str}
        @param timeout: let notification disappear after C{<timeout>} milliseconds
        @type timeout: C{int}

        """
        if context is not None:
            try:
                title = self.title[context]
                del self.title[context]
            except KeyError:
                pass
            try:
                text = self.text[context]
                del self.text[context]
            except KeyError:
                pass
            try:
                icon = self.icon[context]
                del self.icon[context]
            except KeyError:
                pass
            try:
                timeout = self.timeout[context]
                del self.timeout[context]
            except KeyError:
                pass

        # libnotify timeouts are given in millisecs, on Windows we use seconds...
        timeout = timeout / 1000

        _icon_map_wx = {
            'audio_error': wx.ICON_ERROR,
            'auth_success': wx.ICON_INFORMATION,
            'auth_failed': wx.ICON_WARNING,
            'auth_error': wx.ICON_ERROR,
            'auth_disconnect': wx.ICON_INFORMATION,
            'profile_add': wx.ICON_INFORMATION,
            'profile_delete': wx.ICON_INFORMATION,
            'profile_edit': wx.ICON_INFORMATION,
            'profile_save': wx.ICON_INFORMATION,
            'profile_error': wx.ICON_ERROR,
            'session_cleanall': wx.ICON_INFORMATION,
            'session_error': wx.ICON_ERROR,
            'session_pause': wx.ICON_INFORMATION,
            'session_printing': wx.ICON_INFORMATION,
            'session_resume': wx.ICON_INFORMATION,
            'session_start': wx.ICON_INFORMATION,
            'session_terminate': wx.ICON_INFORMATION,
            'session_warning': wx.ICON_WARNING,
        }
        if icon in _icon_map_wx.keys():
           icon = _icon_map_wx[icon]
        else:
           icon = wx.ICON_INFORMATION

        try:
            if not self._PyHocaGUI.disable_notifications and title and text:
                # you will need wxPython >= 2.9 for this
                _notification_msg = wx.NotificationMessage()
                _notification_msg.SetTitle(title)
                _notification_msg.SetMessage(text)
                _notification_msg.SetParent(self._PyHocaGUI.about)
                _notification_msg.SetFlags(icon)
                _notification_msg.Show(timeout=timeout)
        except:
            # if we are running wxPython 2.8, we ignore missing
            # wx.NotificationMessage class
            pass

        if title and text:
            # on Windows some error messages are already encoded, some are not, depending from which module they come
            try: _title = title.encode(utils.get_encoding())
            except: _title = title
            try: _text = text.encode(utils.get_encoding())
            except: _text = text

            try: self._pyhoca_logger('['+_title+'] '+_text, loglevel=log.loglevel_NOTICE)
            except UnicodeDecodeError: self._pyhoca_logger('Unicode error occurred while rendering a log message...', loglevel=log.loglevel_WARN)

    def Close(self):
        """\
        Provide a C{Close()} method which does nothing.

        """
        pass

    def Destroy(self):
        """\
        Provide a C{Destroy()} method which does nothing.

        """
        pass
