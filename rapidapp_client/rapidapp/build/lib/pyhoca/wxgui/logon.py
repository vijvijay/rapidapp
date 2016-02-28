modules ={}

# Python X2Go
import x2go

# gevent
import gevent

import wx
import os

# PyHoca-GUI modules
import passphrase

if os.environ.has_key('DESKTOP_SESSION'):
    WINDOW_MANAGER = os.environ['DESKTOP_SESSION']
else:
    WINDOW_MANAGER = 'generic'

class PyHocaGUI_DialogBoxPassword(wx.Dialog):
    """\
    Logon window for L{PyHocaGUI}.

    """
    def __init__(self, _PyHocaGUI, profile_name, caller=None, passphrase=None, sshproxy_passphrase=None, sshproxy_auth=False, twofactor_auth=False, sshproxy_twofactor_auth=False):
        """\
        Logon window (constructor)

        @param _PyHocaGUI: main application instance
        @type _PyHocaGUI: C{obj}
        @param profile_name: name of session profile that defines the server we authenticate against
        @type profile_name: C{str}
        @param caller: unused
        @type caller: C{None}
        @param sshproxy_auth: use (dual) SSH proxy authentication
        @type sshproxy_auth: C{bool}
        @param twofactor_auth: use two-factor authentication for X2Go Server
        @type twofactor_auth: C{bool}
        @param sshproxy_twofactor_auth: use two-factor authentication for SSH proxy
        @type sshproxy_twofactor_auth: C{bool}

        """
        self._PyHocaGUI = _PyHocaGUI
        self._PyHocaGUI.gevent_sleep_when_idle = 0.1
        self._pyhoca_logger = self._PyHocaGUI._pyhoca_logger
        self._pyhoca_logger('password dialog box started', loglevel=x2go.loglevel_INFO, )

        self.sshproxy_auth = sshproxy_auth
        self.twofactor_auth = twofactor_auth
        self.sshproxy_twofactor_auth = sshproxy_twofactor_auth

        self.current_profile_name = profile_name
        self.current_profile_config = self._PyHocaGUI.session_profiles.get_profile_config(profile_name)

        wx.Dialog.__init__(self, None, id=-1, title=profile_name, style=wx.DEFAULT_FRAME_STYLE, )
        self._PyHocaGUI._sub_windows.append(self)

        if self.sshproxy_auth:
            self.sshproxy_started = False
            self.sshproxy_password = None
            self.SetTitle(_(u'%s (via %s)') % (profile_name, self.current_profile_config['sshproxyhost']))

        self.password = None
        self.passphrase = passphrase
        self.sshproxy_passphrase = sshproxy_passphrase

        self.userLbl = wx.StaticText(self, wx.ID_ANY, _(u'Username')+':', size=(-1, -1))
        self.userTxt = wx.TextCtrl(self, wx.ID_ANY, '', style=wx.TE_PROCESS_ENTER, size=(120, -1))
        self.passwordLbl = wx.StaticText(self, wx.ID_ANY, _(u'Password')+':', size=(-1, -1))
        self.passwordTxt = wx.TextCtrl(self, wx.ID_ANY, '', style=wx.TE_PROCESS_ENTER|wx.TE_PASSWORD, size=(120, -1))
        self.passwordTxt.SetFocus()
        self.loginBtn = wx.Button(self, wx.ID_OK, _(u'Authenticate'), )
        self.loginBtn.SetDefault()

        _tab_order = []

        # widgets
        if self.sshproxy_auth:
            self.sshProxyUserLbl = wx.StaticText(self, wx.ID_ANY, _(u'Username')+':', size=(-1, -1))
            self.sshProxyUserTxt = wx.TextCtrl(self, wx.ID_ANY, '', style=wx.TE_PROCESS_ENTER, size=(120, -1))
            self.sshProxyPasswordLbl = wx.StaticText(self, wx.ID_ANY, _(u'Password')+':', size=(-1, -1))
            self.sshProxyPasswordTxt = wx.TextCtrl(self, wx.ID_ANY, '', style=wx.TE_PROCESS_ENTER|wx.TE_PASSWORD, size=(120, -1))
            self.sshProxyPasswordTxt.SetFocus()
            self.sshProxyLoginBtn = wx.Button(self, wx.ID_OK, '  '+_(u'Start SSH tunnel')+'  ')
            self.sshProxyLoginBtn.SetDefault()

            _tab_order.extend([self.sshProxyUserTxt, self.sshProxyPasswordTxt, self.sshProxyLoginBtn, ])

            headerWidth = max(self.userLbl.GetSize().GetWidth(), self.passwordLbl.GetSize().GetWidth()) + 150
            sshProxyHeaderWidth = max(self.sshProxyUserLbl.GetSize().GetWidth(), self.sshProxyPasswordLbl.GetSize().GetWidth()) + 150

            self.headerLbl = wx.StaticText(self, wx.ID_ANY, _(u'Session login')+':', size=(headerWidth, -1))
            self.sshProxyHeaderLbl = wx.StaticText(self, wx.ID_ANY, _(u'SSH proxy server login')+':', size=(sshProxyHeaderWidth, -1))
            self.headerLbl.SetFont(wx.Font(-1, wx.DEFAULT, wx.NORMAL, wx.FONTWEIGHT_BOLD, 0, ""))
            self.sshProxyHeaderLbl.SetFont(wx.Font(-1, wx.DEFAULT, wx.NORMAL, wx.FONTWEIGHT_BOLD, 0, ""))

            self.headerLbl.Enable(False)
            self.userLbl.Enable(False)
            self.userTxt.Enable(False)
            self.passwordLbl.Enable(False)
            self.passwordTxt.Enable(False)
            self.loginBtn.Enable(False)

        self.cancelBtn = wx.Button(self, wx.ID_CANCEL, _(u'Cancel'), )

        _tab_order.extend([self.userTxt, self.passwordTxt, self.loginBtn, self.cancelBtn, ])

        if self.sshproxy_auth:
            self.Bind(wx.EVT_BUTTON, self.OnLogin, self.sshProxyLoginBtn)
            self.Bind(wx.EVT_TEXT_ENTER, self.OnLogin, self.sshProxyUserTxt)
            self.Bind(wx.EVT_TEXT_ENTER, self.OnLogin, self.sshProxyPasswordTxt)

        self.Bind(wx.EVT_BUTTON, self.OnLogin, self.loginBtn)
        self.Bind(wx.EVT_TEXT_ENTER, self.OnLogin, self.userTxt)
        self.Bind(wx.EVT_TEXT_ENTER, self.OnLogin, self.passwordTxt)
        self.Bind(wx.EVT_BUTTON, self.OnCancel, self.cancelBtn)

        btnSizer = wx.BoxSizer(wx.HORIZONTAL)
        if not self.sshproxy_auth:
            credSizer = wx.GridBagSizer(hgap=2, vgap=2)
        mainSizer = wx.BoxSizer(wx.VERTICAL)

        # sizer / layout
        if self.sshproxy_auth:

            credSizer = wx.GridBagSizer(hgap=4, vgap=2)

            credSizer.Add(self.sshProxyHeaderLbl, pos=(0,0), span=(1,2), flag=wx.ALL|wx.EXPAND, border=5)
            credSizer.Add(self.headerLbl, pos=(0,2), span=(1,2), flag=wx.ALL|wx.EXPAND, border=5)

            credSizer.Add(self.sshProxyUserLbl, pos=(1,0), flag=wx.LEFT|wx.ALIGN_CENTER_VERTICAL, border=5)
            credSizer.Add(self.sshProxyUserTxt, pos=(1,1), flag=wx.ALL, border=5)

            credSizer.Add(self.userLbl, pos=(1,2), flag=wx.LEFT|wx.ALIGN_CENTER_VERTICAL, border=5)
            credSizer.Add(self.userTxt, pos=(1,3), flag=wx.ALL, border=5)

        else:
            credSizer.Add(self.userLbl, pos=(0,0), flag=wx.LEFT|wx.ALIGN_CENTER_VERTICAL, border=5)
            credSizer.Add(self.userTxt, pos=(0,1), flag=wx.ALL, border=5)

        if self.sshproxy_auth:

            credSizer.Add(self.sshProxyPasswordLbl, pos=(2,0), flag=wx.LEFT|wx.ALIGN_CENTER_VERTICAL, border=5)
            credSizer.Add(self.sshProxyPasswordTxt, pos=(2,1), flag=wx.ALL, border=5)

            credSizer.Add(self.passwordLbl, pos=(2,2), flag=wx.LEFT|wx.ALIGN_CENTER_VERTICAL, border=5)
            credSizer.Add(self.passwordTxt, pos=(2,3), flag=wx.ALL, border=5)

        else:
            credSizer.Add(self.passwordLbl, pos=(1,0), flag=wx.LEFT|wx.ALIGN_CENTER_VERTICAL, border=5)
            credSizer.Add(self.passwordTxt, pos=(1,1), flag=wx.ALL, border=5)

        if self.sshproxy_auth:
            btnSizer.Add(self.sshProxyLoginBtn, 0, wx.ALL, 5)
        btnSizer.Add(self.loginBtn, 0, wx.ALL, 5)
        btnSizer.Add(self.cancelBtn, 0, wx.ALL, 5)

        mainSizer.Add(credSizer, 0, wx.ALL, 5)
        mainSizer.Add(btnSizer, 0, wx.ALL|wx.ALIGN_RIGHT, 5)

        if self.current_profile_config.has_key('user'):
            self.userTxt.SetValue(self.current_profile_config['user'])
            if not self.current_profile_config['user'] and not self.sshproxy_auth:
                self.userTxt.SetFocus()

        if self.sshproxy_auth:

            if self.current_profile_config.has_key('sshproxyuser'):
                if self.current_profile_config.has_key('sshproxysameuser') and not self.current_profile_config['sshproxysameuser']:
                    self.sshProxyUserTxt.SetValue(self.current_profile_config['sshproxyuser'])
            if self.current_profile_config.has_key('user'):
                if self.current_profile_config.has_key('sshproxysameuser') and self.current_profile_config['sshproxysameuser']:
                    self.sshProxyUserTxt.SetValue(self.current_profile_config['user'])

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
        username = self.userTxt.GetValue()
        password = self.passwordTxt.GetValue()
        connect_failed = False
        if self.sshproxy_auth:
            sshproxy_user = self.sshProxyUserTxt.GetValue()
            sshproxy_password = self.sshProxyPasswordTxt.GetValue()
            if len(sshproxy_user) == 0:
                return
            if len(sshproxy_password) == 0:
                return
            # in case of a host key validity check, we will disable all widgets in the window
            self.sshProxyHeaderLbl.Enable(False)
            self.sshProxyUserLbl.Enable(False)
            self.sshProxyUserTxt.Enable(False)
            self.sshProxyPasswordLbl.Enable(False)
            self.sshProxyPasswordTxt.Enable(False)
            self.sshProxyLoginBtn.Enable(False)
            self.cancelBtn.Enable(False)

        elif self.current_profile_config['sshproxysamepass']:
            sshproxy_user = None
            sshproxy_password = self.passwordTxt.GetValue()

        else:
            sshproxy_user = sshproxy_password = None

        if (not self.sshproxy_auth) or self.sshproxy_started:
            if len(username) == 0:
                self._PyHocaGUI.notifier.prepare('Pls enter user name',
                                                 title=_('Enter user name'),
                                                 text=_('Enter user name'),
                                                 icon='auth_error')
                self._PyHocaGUI.notifier.send(self.current_profile_name, context='Pls enter user name', timeout=4000)
                self._pyhoca_logger('popping up username required baloon', loglevel=x2go.log.loglevel_INFO, )
                return
            if len(password) == 0:
                self._PyHocaGUI.notifier.prepare('Pls enter password',
                                                 title=_('Enter password'),
                                                 text=_('Enter password'),
                                                 icon='auth_error')
                self._PyHocaGUI.notifier.send(self.current_profile_name, context='Pls enter password', timeout=4000)
                self._pyhoca_logger('popping up username required baloon', loglevel=x2go.log.loglevel_INFO, )
                return

        if self.sshproxy_auth and (not self.sshproxy_started):
            force_password_auth = False
            sshproxy_force_password_auth = True
        else:
            force_password_auth = True
            sshproxy_force_password_auth = True

        wx.BeginBusyCursor()
        session_uuid = self._PyHocaGUI._X2GoClient__client_registered_sessions_of_profile_name(self.current_profile_name)[0]
        
        try:
            self._PyHocaGUI._X2GoClient__connect_session(session_uuid,
                                                         username=username,
                                                         password=password,
                                                         passphrase=self.passphrase,
                                                         force_password_auth=(force_password_auth and not self.twofactor_auth),
                                                         add_to_known_hosts=self._PyHocaGUI.add_to_known_hosts,
                                                         sshproxy_user=sshproxy_user,
                                                         sshproxy_password=sshproxy_password,
                                                         sshproxy_passphrase=self.sshproxy_passphrase,
                                                         sshproxy_force_password_auth=(sshproxy_force_password_auth and not self.sshproxy_twofactor_auth),
                                                        )
            if not self._PyHocaGUI._X2GoClient__server_valid_x2gouser(session_uuid):
                self._PyHocaGUI.notifier.prepare('AUTH_%s' % self.current_profile_name,
                                                 title=_(u'%s - connect failure') % self.current_profile_name,
                                                 text=_(u'User is not allowed to start X2Go sessions!'),
                                                 icon='auth_error')
                self._PyHocaGUI.OnServerDisconnect(evt)
            else:
                self._PyHocaGUI.notifier.prepare('AUTH_%s' % self.current_profile_name,
                                                 title=_(u'%s - connect') % self.current_profile_name,
                                                 text=_(u'Authentication has been successful.'),
                                                 icon='auth_success')
                if self._PyHocaGUI.remember_username:
                    _sp = self._PyHocaGUI.session_profiles
                    if username:
                        _sp.update_value(_sp.to_profile_id(self.current_profile_name), 'user', username)
                    if sshproxy_user:
                        _sp.update_value(_sp.to_profile_id(self.current_profile_name), 'sshproxyuser', sshproxy_user)
                    _sp.write_user_config = True
                    _sp.write()

        except x2go.X2GoSSHProxyPasswordRequiredException:
            key_filename = None
            try:
                if not self._PyHocaGUI._X2GoClient__get_session(session_uuid).sshproxy_params['sshproxy_look_for_keys']:
                    key_filename = self._PyHocaGUI._X2GoClient__get_session(session_uuid).sshproxy_params['sshproxy_key_filename']
            except KeyError:
                pass
            self._pyhoca_logger('SSH private key file (for SSH proxy) is encrypted and requires a passphrase', loglevel=x2go.log.loglevel_INFO, )
            _passphrase_window = passphrase.PyHocaGUI_DialogBoxPassphrase(self._PyHocaGUI, self.current_profile_name, caller=self, password=password, sshproxy_auth=True, key_filename=key_filename)
            self._PyHocaGUI._logon_windows[self.current_profile_name] = _passphrase_window

        except x2go.AuthenticationException:
            if self.sshproxy_auth and (not self.sshproxy_started):
                try: wx.EndBusyCursor()
                except: pass
                self.sshproxy_started = True
                self.headerLbl.Enable(True)
                self.userLbl.Enable(True)
                self.userTxt.Enable(True)
                self.passwordLbl.Enable(True)
                self.passwordTxt.Enable(True)
                self.passwordTxt.SetFocus()
                self.loginBtn.Enable(True)
                self.loginBtn.SetDefault()
                self.cancelBtn.Enable(True)
                self.sshProxyHeaderLbl.Enable(False)
                self.sshProxyUserLbl.Enable(False)
                self.sshProxyUserTxt.Enable(False)
                self.sshProxyPasswordLbl.Enable(False)
                self.sshProxyPasswordTxt.Enable(False)
                self.sshProxyLoginBtn.Enable(False)
                self.sshProxyLoginBtn.SetLabel(_(u'SSH tunnel started'))
                return
            else:
                self._PyHocaGUI.notifier.prepare('AUTH_%s' % self.current_profile_name,
                                                 title=_(u'%s - connect failure') % self.current_profile_name,
                                                 text=_(u'Authentication failed!'),
                                                 icon='auth_failed')
                connect_failed = True

        except x2go.X2GoSSHProxyAuthenticationException:
            try: wx.EndBusyCursor()
            except: pass
            self._PyHocaGUI.notifier.prepare('AUTH_%s' % self.current_profile_name,
                                             title=_(u'%s - SSH proxy') % self.current_profile_name,
                                             text=_(u'Authentication to the SSH proxy server failed!'),
                                             icon='auth_failed')

            if not self.current_profile_config['sshproxysamepass']:
                self._PyHocaGUI.notifier.send(self.current_profile_name, context='AUTH_%s' % self.current_profile_name, timeout=4000)
                if self.sshproxy_auth:
                    self.sshProxyPasswordTxt.SetValue('')
                    self.sshProxyHeaderLbl.Enable(True)
                    self.sshProxyUserLbl.Enable(True)
                    self.sshProxyUserTxt.Enable(True)
                    self.sshProxyPasswordLbl.Enable(True)
                    self.sshProxyPasswordTxt.Enable(True)
                    self.sshProxyLoginBtn.Enable(True)
                self.cancelBtn.Enable(True)
                return
            else:
                connect_failed = True

        #except gevent.dns.DNSError, e:
        #    self._PyHocaGUI.notifier.prepare('AUTH_%s' % self.current_profile_name,
        #                                     title=_(u'%s - DNS error') % self.current_profile_name,
        #                                     text=e.strerror + '!',
        #                                     icon='auth_error')
        #    connect_failed = True

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
            self._PyHocaGUI.notifier.prepare('AUTH_%s' % self.current_profile_name,
                                             title=_(u'%s - key error') % self.current_profile_name,
                                             text='%s!' % str(e),
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
                if self.sshproxy_auth and (not self.sshproxy_started):
                    try: wx.EndBusyCursor()
                    except: pass
                    self.sshproxy_started = True
                    self.headerLbl.Enable(True)
                    self.userLbl.Enable(True)
                    self.userTxt.Enable(True)
                    self.passwordLbl.Enable(True)
                    self.passwordTxt.Enable(True)
                    self.passwordTxt.SetFocus()
                    self.loginBtn.Enable(True)
                    self.loginBtn.SetDefault()
                    self.cancelBtn.Enable(True)
                    self.sshProxyHeaderLbl.Enable(False)
                    self.sshProxyUserLbl.Enable(False)
                    self.sshProxyUserTxt.Enable(False)
                    self.sshProxyPasswordLbl.Enable(False)
                    self.sshProxyPasswordTxt.Enable(False)
                    self.sshProxyLoginBtn.Enable(False)
                    self.sshProxyLoginBtn.SetLabel(_(u'SSH tunnel started'))
                    return

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

        except ValueError as verr:
            self._PyHocaGUI.notifier.prepare('AUTH_%s' % self.current_profile_name,
                                             title=_(u'%s - LoadBalancer error') % self.current_profile_name,
                                             text=_(u'%s !' % verr.args[0]),
                                             icon='auth_error')
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
