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

# gevent
import gevent
import gevent.monkey
gevent.monkey.patch_all()

import wx
import os
import base64

# PyHoca-GUI modules
import logon

if os.environ.has_key('DESKTOP_SESSION'):
    WINDOW_MANAGER = os.environ['DESKTOP_SESSION']
else:
    WINDOW_MANAGER = 'generic'

class PyHocaGUI_DialogBoxPassphrase(wx.Dialog):
    """\
    SSH key passphrase window for L{PyHocaGUI}.

    """
    def __init__(self, _PyHocaGUI, profile_name, caller=None, password=None, sshproxy_auth=False, sshproxy_passphrase=None, key_filename=None):
        """\
        Passphrase window (constructor)

        @param _PyHocaGUI: main application instance
        @type _PyHocaGUI: C{obj}
        @param profile_name: name of session profile that defines the server we authenticate against
        @type profile_name: C{str}
        @param caller: unused
        @type caller: C{None}

        """
        self._PyHocaGUI = _PyHocaGUI
        self._PyHocaGUI.gevent_sleep_when_idle = 0.1
        self._pyhoca_logger = self._PyHocaGUI._pyhoca_logger
        self._pyhoca_logger('SSH key passphrase dialog box started', loglevel=x2go.loglevel_INFO, )

        self.current_profile_name = profile_name
        self.current_profile_config = self._PyHocaGUI.session_profiles.get_profile_config(profile_name)

        if sshproxy_auth:
            wx.Dialog.__init__(self, None, id=-1, title=_(u'%s (SSH proxy)') % profile_name, style=wx.DEFAULT_FRAME_STYLE, )
        else:
            wx.Dialog.__init__(self, None, id=-1, title=_(u'%s (X2Go Server)') % profile_name, style=wx.DEFAULT_FRAME_STYLE, )

        self._PyHocaGUI._sub_windows.append(self)

        self.password = password
        self.key_filename = key_filename
        self.sshproxy_auth = sshproxy_auth
        self.sshproxy_passphrase = sshproxy_passphrase

        if self.key_filename:
            keyfilenameLbl = wx.StaticText(self, wx.ID_ANY, _(u'Unlock SSH private key (%s)...') % key_filename)
        else:
            keyfilenameLbl = wx.StaticText(self, wx.ID_ANY, _(u'Unlock auto-discovered SSH private key...'))

        self.passphraseLbl = wx.StaticText(self, wx.ID_ANY, _(u'Passphrase')+':', size=(-1, -1))
        self.passphraseTxt = wx.TextCtrl(self, wx.ID_ANY, '', style=wx.TE_PROCESS_ENTER|wx.TE_PASSWORD, size=(120, -1))
        self.passphraseTxt.SetFocus()
        self.unlockBtn = wx.Button(self, wx.ID_OK, _(u'Unlock SSH key'), )
        self.unlockBtn.SetDefault()

        _tab_order = []

        self.cancelBtn = wx.Button(self, wx.ID_CANCEL, _(u'Cancel'), )

        _tab_order.extend([self.passphraseTxt, self.unlockBtn, self.cancelBtn, ])

        self.Bind(wx.EVT_BUTTON, self.OnPassphrase, self.unlockBtn)
        self.Bind(wx.EVT_TEXT_ENTER, self.OnPassphrase, self.passphraseTxt)
        self.Bind(wx.EVT_BUTTON, self.OnCancel, self.cancelBtn)

        btnSizer = wx.BoxSizer(wx.HORIZONTAL)
        credSizer = wx.GridBagSizer(hgap=1, vgap=1)
        mainSizer = wx.BoxSizer(wx.VERTICAL)

        credSizer.Add(self.passphraseLbl, pos=(0,0), flag=wx.LEFT|wx.ALIGN_CENTER_VERTICAL, border=5)
        credSizer.Add(self.passphraseTxt, pos=(0,1), flag=wx.ALL, border=5)

        btnSizer.Add(self.unlockBtn, 0, wx.ALL, 5)
        btnSizer.Add(self.cancelBtn, 0, wx.ALL, 5)

        mainSizer.Add(keyfilenameLbl, 0, wx.ALL|wx.ALIGN_LEFT, 5)
        mainSizer.Add(credSizer, 0, wx.ALL|wx.ALIGN_CENTER, 5)
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

    def OnPassphrase(self, evt):
        """\
        If the user clicks ,,Ok'' in the passphrase window.

        @param evt: event
        @type evt: C{obj}

        """
        password = None
        passphrase = None
        force_password_auth = False
        sshproxy_force_password_auth = False
        if self.sshproxy_auth and self.password:
            password = self.password
            sshproxy_passphrase = self.passphraseTxt.GetValue()
            force_password_auth = True
        elif self.sshproxy_auth:
            passphrase = sshproxy_passphrase = self.passphraseTxt.GetValue()
        else:
            passphrase = self.passphraseTxt.GetValue()
            try:
                sshproxy_passphrase = base64.b64decode(self.sshproxy_passphrase)
            except TypeError:
                sshproxy_passphrase = None

        try:
            b64_passphrase = base64.b64encode(passphrase)
        except TypeError:
            b64_passphrase = None

        connect_failed = False

        wx.BeginBusyCursor()
        session_uuid = self._PyHocaGUI._X2GoClient__client_registered_sessions_of_profile_name(self.current_profile_name)[0]

        try:
            self._PyHocaGUI._X2GoClient__connect_session(session_uuid,
                                                         password=password,
                                                         passphrase=passphrase,
                                                         sshproxy_passphrase=sshproxy_passphrase,
                                                         force_password_auth=force_password_auth,
                                                         sshproxy_force_password_auth=sshproxy_force_password_auth,
                                                         add_to_known_hosts=self._PyHocaGUI.add_to_known_hosts,
                                                        )
            self._PyHocaGUI.notifier.prepare('AUTH_%s' % self.current_profile_name,
                                             title=_(u'%s - connect') % self.current_profile_name,
                                             text=_(u'Authentication has been successful.'),
                                             icon='auth_success')

        except x2go.PasswordRequiredException:
            if self.sshproxy_auth:
                key_filename = ''
                try:
                    if not self._PyHocaGUI._X2GoClient__get_session(session_uuid).control_params['look_for_keys']:
                        key_filename = self._PyHocaGUI._X2GoClient__get_session(session_uuid).control_params['key_filename']
                except KeyError:
                    pass
                self._pyhoca_logger('SSH private key file is encrypted and requires a passphrase', loglevel=x2go.log.loglevel_INFO, )
                _passphrase_window = PyHocaGUI_DialogBoxPassphrase(self._PyHocaGUI, self.current_profile_name, caller=self, sshproxy_passphrase=b64_passphrase, key_filename=key_filename)
                self._PyHocaGUI._logon_windows[self.current_profile_name] = _passphrase_window

            else:
                self._PyHocaGUI.notifier.prepare('AUTH_%s' % self.current_profile_name,
                                                 title=_(u'%s - connect failure') % self.current_profile_name,
                                                 text=_(u'SSH key file (for X2Go server) could not be unlocked!'),
                                                 icon='auth_failed')
                connect_failed = True

        except x2go.X2GoSSHProxyPasswordRequiredException:
            self._PyHocaGUI.notifier.prepare('AUTH_%s' % self.current_profile_name,
                                             title=_(u'%s - connect failure') % self.current_profile_name,
                                             text=_(u'SSH key file (for SSH proxy) could not be unlocked!'),
                                             icon='auth_failed')
            connect_failed = True

        except x2go.AuthenticationException:
            self._PyHocaGUI.notifier.prepare('AUTH_%s' % self.current_profile_name,
                                             title=_(u'%s - connect failure') % self.current_profile_name,
                                             text=_(u'Authentication failed!'),
                                             icon='auth_failed')
            connect_failed = True

        except x2go.X2GoSSHProxyAuthenticationException:
            self._PyHocaGUI.notifier.prepare('AUTH_%s' % self.current_profile_name,
                                             title=_(u'%s - connect failure') % self.current_profile_name,
                                             text=_(u'Authentication to the SSH proxy server failed!'),
                                             icon='auth_failed')
            connect_failed = True

        except gevent.socket.error, e:
            self._PyHocaGUI.notifier.prepare('AUTH_%s' % self.current_profile_name,
                                             title=_(u'%s - socket error') % self.current_profile_name,
                                             text=e.strerror + '!',
                                             icon='auth_error')
            connect_failed = True

        except x2go.X2GoHostKeyException, e:
            self._PyHocaGUI.notifier.prepare('AUTH_%s' % self.current_profile_name,
                                             title=_(u'%s - host key error') % self.current_profile_name,
                                             text=_(u'The remote server\'s host key is invalid or has not been accepted by the user') + '!',
                                             icon='auth_error',
                                             timeout=4000)
            connect_failed = True

        except x2go.X2GoRemoteHomeException, e:
            self._PyHocaGUI.notifier.prepare('AUTH_%s' % self.current_profile_name,
                                             title=_(u'%s - missing home directory') % self.current_profile_name,
                                             text=_("The remote user's home directory does not exist."),
                                             icon='auth_error',
                                             timeout=4000)
            connect_failed = True

        except x2go.X2GoSSHProxyException, e:
            if str(e).startswith('Two-factor authentication requires a password'):
                self._pyhoca_logger('SSH proxy host requests two-factor authentication', loglevel=x2go.loglevel_NOTICE)
                _logon_window = logon.PyHocaGUI_DialogBoxPassword(self._PyHocaGUI, self.current_profile_name,
                                                                  caller=self,
                                                                  passphrase=passphrase,
                                                                  sshproxy_passphrase=sshproxy_passphrase,
                                                                  sshproxy_auth=True,
                                                                  sshproxy_twofactor_auth=True,
                                                                 )
                self._PyHocaGUI._logon_windows[self.current_profile_name] = _logon_window
            else:
                if str(e).startswith('Host key for server ') and str(e).endswith(' does not match!'):
                    errmsg = _('Host key verification failed. The X2Go server may have been compromised.\n\nIt is also possible that the host key has just been changed.\n\nHowever, for security reasons the connection will not be established!!!')
                else:
                    errmsg = str(e)
                self._PyHocaGUI.notifier.prepare('AUTH_%s' % self.current_profile_name,
                                                 title=_(u'%s - key error') % self.current_profile_name,
                                                 text='%s!' % errmsg,
                                                 icon='auth_error',
                                                 timeout=4000)
                connect_failed = True

        except x2go.X2GoSessionException, e:
            self._PyHocaGUI.notifier.prepare('AUTH_%s' % self.current_profile_name,
                                             title=_(u'%s - auth error') % self.current_profile_name,
                                             text='%s!' % str(e),
                                             icon='auth_error',
                                             timeout=4000)
            connect_failed = True

        except x2go.SSHException, e:
            if str(e).startswith('Two-factor authentication requires a password'):
                self._pyhoca_logger('X2Go Server requests two-factor authentication', loglevel=x2go.loglevel_NOTICE)
                _logon_window = logon.PyHocaGUI_DialogBoxPassword(self._PyHocaGUI, self.current_profile_name,
                                                                  caller=self,
                                                                  passphrase=passphrase,
                                                                  sshproxy_passphrase=sshproxy_passphrase,
                                                                  sshproxy_auth=False,
                                                                  twofactor_auth=True,
                                                                 )
                self._PyHocaGUI._logon_windows[self.current_profile_name] = _logon_window
            else:
                if str(e).startswith('Host key for server ') and str(e).endswith(' does not match!'):
                    errmsg = _('Host key verification failed. The X2Go server may have been compromised.\n\nIt is also possible that the host key has just been changed.\n\nHowever, for security reasons the connection will not be established!!!')
                else:
                    errmsg = str(e)

                self._PyHocaGUI.notifier.prepare('AUTH_%s' % self.current_profile_name,
                                                 title=_(u'%s - SSH error') % self.current_profile_name,
                                                 text='%s' % errmsg,
                                                 icon='auth_error',
                                                 timeout=10000)
                connect_failed = True

        except:
            self._PyHocaGUI.notifier.prepare('AUTH_%s' % self.current_profile_name,
                                             title=_(u'%s - unknown error') % self.current_profile_name,
                                             text=_(u'An unknown error occured during authentication!'),
                                             icon='auth_error')
            connect_failed = True
            if self._PyHocaGUI.args.debug or self._PyHocaGUI.args.libdebug or (os.environ.has_key('PYHOCAGUI_DEVELOPMENT') and os.environ['PYHOCAGUI_DEVELOPMENT'] == '1'):
                raise

        self._PyHocaGUI.notifier.send(self.current_profile_name, context='AUTH_%s' % self.current_profile_name, timeout=4000)

        wx.SetCursor(wx.StockCursor(wx.CURSOR_ARROW))
        # Windows's GUI is more picky then Linux's GTK GUI about EndBusyCursor if cursor is not busy...
        try: wx.EndBusyCursor()
        except: pass

        if connect_failed and self._PyHocaGUI.exit_on_disconnect:
            self._PyHocaGUI.WakeUpIdle()
            self._PyHocaGUI.ExitMainLoop()

        if self._PyHocaGUI._X2GoClient__is_session_connected(session_uuid):
            self._PyHocaGUI._post_authenticate(evt, session_uuid)
        self.sshproxy_started = False
        try: del self._PyHocaGUI._logon_windows[self.current_profile_name]
        except KeyError: pass

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
        try:
            self._PyHocaGUI._temp_disabled_profile_names.remove(self.current_profile_name)
        except ValueError:
            pass
        wx.Dialog.Destroy(self)
