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
import copy
import types

import x2go.log as log
import x2go.utils as utils
import x2go.defaults as defaults
from x2go import X2GOCLIENT_OS

from x2go._paramiko import PARAMIKO_FEATURE
import basepath

_known_encodings = utils.known_encodings()

from wx.lib.mixins.listctrl import CheckListCtrlMixin


class CheckListCtrl(wx.ListCtrl, CheckListCtrlMixin):
    def __init__(self, parent):
        wx.ListCtrl.__init__(self, parent, -1, style=wx.LC_REPORT | wx.SUNKEN_BORDER|wx.LC_SINGLE_SEL|wx.LC_VRULES)
        CheckListCtrlMixin.__init__(self)


class PyHocaGUI_ProfileManager(wx.Dialog):
    """\
    L{PyHocaGUI}'s profile manager window that allows to tweak all session related settings.

    """
    def __init__(self, _PyHocaGUI, action, profile_id=None, profile_name=None):
        """\
        Profile manager window (constructor).

        @param _PyHocaGUI: main application instance
        @type _PyHocaGUI: C{obj}
        @param action: profile manager action (use either of C{ADD}, C{ADD_EXPLICITLY}, C{EDIT}, C{EDIT_CONNECTED}, (C{EDIT_EXPLICITLY})
        @type action: C{str}
        @param profile_id: X2Go session profile ID
        @type profile_id: C{str}
        @param profile_name: X2Go session profile name
        @type profile_name: C{str}

        """
        self._icons_location = basepath.icons_basepath

        self._PyHocaGUI = _PyHocaGUI
        self._PyHocaGUI.gevent_sleep_when_idle = 0.1

        self._pyhoca_logger = self._PyHocaGUI._pyhoca_logger

        self._pyhoca_logger('starting profile manager, action is: %s' % action, loglevel=log.loglevel_INFO)

        wx.Dialog.__init__(self, None, -1, style=wx.DEFAULT_DIALOG_STYLE, size=wx.Size(550,450))
        self._PyHocaGUI._sub_windows.append(self)

        self.profileManagerDefaults = defaults.X2GO_SESSIONPROFILE_DEFAULTS
        self.success = False

        self.action = action
        self.sessionChoices = {
            'CINNAMON': _(u'Cinnamon Desktop (CINNAMON)'),
            'GNOME': _(u'GNOME Desktop (GNOME)'),
            'MATE': _(u'MATE Desktop (MATE)'),
            'KDE': _(u'K Desktop Environment (KDE)'),
            'LXDE': _(u'Lightweight X Desktop (LXDE)'),
            'TRINITY': _(u'Trinity X Desktop (KDE3-like)'),
            'UNITY': _(u'Unity X Desktop Shell (UNITY)'),
            'XFCE': _(u'XFCE Desktop (XFCE)'),
            'PUBLISHEDAPPLICATIONS': _(u'Published Applications'),
            'APPLICATION': _(u'Single Application'),
            'SHADOW': _(u'Share desktop session (SHADOW)'),
            'XDMCP': _(u'XDMCP Query'),
            'RDP': _(u'Windows Terminal Server (X2Go-proxied RDP)'),
            'DirectRDP': _(u'Windows Terminal Server (Direct RDP)'),
            'CUSTOM': _(u'Custom command'),
            }
        if self.action == 'EDIT_CONNECTED':
            del self.sessionChoices['DirectRDP']
        self.applicationChoices = {
            'WWWBROWSER': _(u'Internet Browser'),
            'MAILCLIENT': _(u'Email Client'),
            'OFFICE': _(u'Office'), 
            'TERMINAL': _(u'Terminal'), 
            }
        self.clipboardModeChoices = {
            'both': _(u'between client and server'),
            'server': _(u'from server to client only'),
            'client': _(u'from client to server only'),
            'none': _(u'not at all')
            }
        self.rdpclientChoices = {
            'rdesktop': u'rdesktop',
            'xfreerdp': u'xfreerdp',
            }
        self.linkChoices = {
            0: 'MODEM',
            1: 'ISDN',
            2: 'ADSL',
            3: 'WAN',
            4: 'LAN',
        }
        self.audioPorts = {
            'esd': 16001,
            'pulse': 4713,
        }
        self.mimeboxactionChoices = {
            'OPEN': _(u'Open file with system\'s default application'),
            'OPENWITH': _(u'Open application chooser dialog'),
            'SAVEAS': _(u'Save incoming file as ...'),
        }

        self._compressions = defaults.pack_methods_nx3_noqual
        self.compressionChoices = {}
        for _comp in self._compressions:
            self.compressionChoices[_comp] = _comp

        self.session_profiles = self._PyHocaGUI.session_profiles

        if X2GOCLIENT_OS == 'Windows':
            self._textfield_height = 24
        else:
            self._textfield_height = 30

        if profile_id is not None:
            self.profile_id = profile_id
        elif profile_name is not None and self.action in ('EDIT', 'EDIT_CONNECTED', 'EDIT_EXPLICITLY', 'COPY'):
            self.profile_id = self.session_profiles.to_profile_id(profile_name)
        else:
            self.profile_id = None

        if self.action in ('EDIT', 'EDIT_CONNECTED', 'EDIT_EXPLICITLY') and self.profile_id:
            self.profile_name = self.session_profiles.to_profile_name(self.profile_id)
            self.profile_config = self.session_profiles.get_profile_config(self.profile_id)
        elif self.action == 'COPY' and self.profile_id:
            self.profile_name = self.session_profiles.to_profile_name(self.profile_id)
            self.profile_config = self.session_profiles.get_profile_config(self.profile_id)
            self.profile_name = self.profile_config['name'] = '%s %s' % (_('settings derived from '), self.profile_name)
        elif self.action in ("ADD", "ADD_EXPLICITLY"):
            self.profile_config = self.session_profiles.default_profile_config()
            # allow localization of the default keyboard settings
            self.profile_name = self.profile_config['name'] = profile_name

        # this code block is for compatibility of session profiles prior to 0.2.2.0:
        _from_host = _from_port = _to_host = _to_port = None
        if self.profile_config.has_key('sshproxytunnel'):
            if self.profile_config['sshproxytunnel'].count(':') == 2:
                _from_port, _to_host, _to_port = self.profile_config['sshproxytunnel'].split(':')
                _from_host = 'localhost'
            elif self.profile_config['sshproxytunnel'].count(':') == 3:
                _from_host, _from_port, _to_host, _to_port = self.profile_config['sshproxytunnel'].split(':')

            if _to_host: self.profile_config['host'] = [_to_host]
            if _to_port: self.profile_config['sshport'] = int(_to_port)

            self.profile_config['sshproxytunnel'] = 'DEPRECATED_CAN_BE_SAFELY_REMOVED'

        # we create a backup dict of our profile_config immediately (for being able to reset erroneously made changes)
        self.profile_config_orig = copy.deepcopy(self.profile_config)
        self.profile_config_bak = copy.deepcopy(self.profile_config)

        self._last_rdpclient = self.profile_config['rdpclient']
        self._last_application = self.applicationChoices['TERMINAL']

        self.config_saved = False

        self.X2GoTabs = wx.Notebook(self, -1, style=0)
        self.tab_Profile = wx.Panel(self.X2GoTabs, -1)
        self.tab_Session = wx.Panel(self.X2GoTabs, -1)
        self.tab_Connection = wx.Panel(self.X2GoTabs, -1)
        self.tab_LinkQuality = wx.Panel(self.X2GoTabs, -1)
        self.tab_IO = wx.Panel(self.X2GoTabs, -1)
        self.tab_MediaResources = wx.Panel(self.X2GoTabs, -1)
        self.tab_SharedResources = wx.Panel(self.X2GoTabs, -1)

        if not self.session_profiles.is_mutable(self.profile_id) and not self.action.startswith('ADD'):
            self.tab_Profile.Enable(False)
            self.tab_Session.Enable(False)
            self.tab_Connection.Enable(False)
            self.tab_LinkQuality.Enable(False)
            self.tab_IO.Enable(False)
            self.tab_MediaResources.Enable(False)
            self.tab_SharedResources.Enable(False)

        # boxes for all tabs
        self.staticbox_Profile = wx.StaticBox(self.tab_Profile, -1, ' %s ' % _(u'Session Title'))
        self.staticbox_Window = wx.StaticBox(self.tab_Profile, -1, ' %s ' % _(u'Session Window'))
        self.staticbox_SessionType = wx.StaticBox(self.tab_Session, -1, ' %s ' % _(u'Session Startup'))
        self.staticbox_Server = wx.StaticBox(self.tab_Connection, -1, ' %s ' % _(u"Server"))
        self.staticbox_Proxy = wx.StaticBox(self.tab_Connection, -1, ' %s ' % _(u"Proxy"))
        self.staticbox_LinkSpeed = wx.StaticBox(self.tab_LinkQuality, -1, ' %s ' % _(u"Connection Link Speed"))
        self.staticbox_Compression = wx.StaticBox(self.tab_LinkQuality, -1, ' %s ' % _(u"Compression"))
        self.staticbox_Display = wx.StaticBox(self.tab_IO, -1, ' %s ' % _(u"Display"))
        self.staticbox_Clipboard = wx.StaticBox(self.tab_IO, -1, ' %s ' % _(u"Clipboard"))
        self.staticbox_Keyboard = wx.StaticBox(self.tab_IO, -1, ' %s ' % _(u"Keyboard"))
        self.staticbox_Sound = wx.StaticBox(self.tab_MediaResources, -1, ' %s ' % _(u"Sound"))
        self.staticbox_Printing = wx.StaticBox(self.tab_MediaResources, -1, ' %s ' % _(u"Printing"))
        self.staticbox_FolderSharing = wx.StaticBox(self.tab_SharedResources, -1, ' %s ' % _(u"Folder Exports"))
        self.staticbox_FileMIMEbox = wx.StaticBox(self.tab_SharedResources, -1, ' %s ' % _(u"File Import"))

        ###
        ### widgets for the PROFILE tab
        ###
        self.ProfileNameLabel = wx.StaticText(self.tab_Profile, -1, _(u"Name")+": ")
        self.ProfileName = wx.TextCtrl(self.tab_Profile, -1, "")

        if self.action in ("ADD_EXPLICITLY", "EDIT_EXPLICITLY"):
            self.ProfileNameLabel.Enable(False)
            self.ProfileName.Enable(False)

        self.SetSessionWindowTitle = wx.CheckBox(self.tab_Profile, -1, _(u"Set session window title"))
        self.UseDefaultSessionWindowTitle = wx.CheckBox(self.tab_Profile, -1, _(u"Use a default session window title"))
        self.CustomSessionWindowTitleLabel = wx.StaticText(self.tab_Profile, -1, _(u"Custom session window title") + ": ")
        self.CustomSessionWindowTitle = wx.TextCtrl(self.tab_Profile, -1, "")
        path_to_icon = os.path.normpath('%s/%s/128x128/%s_sessionicon.png' % (self._icons_location, self._PyHocaGUI.appname, self._PyHocaGUI.appname))
        self.default_icon = True
        if 'icon' in self.profile_config and self.profile_config['icon'] == ':icons/128x128/x2gosession.png':
            # interpret the default x2gosession.png icon entry in session profile config as the PyHoca icon...
            pass
        elif 'icon' in self.profile_config and self.profile_config['icon'] == path_to_icon:
            # rewrite absolute path to PyHoca icon in session profile config back to the default icon path used
            # by X2Go Client, fixes behaviour of PyHoca-GUI <= 0.2.0.4.
            pass
        elif 'icon' in self.profile_config:
            path_to_icon = self.profile_config['icon'].strip()
            path_to_icon = os.path.normpath(path_to_icon)
            self.default_icon = False
        if not os.path.exists(os.path.expanduser(path_to_icon)):
            path_to_icon = os.path.normpath('%s/App-O-Cloud/128x128/App-O-Cloud_sessionicon.png' % self._icons_location)
            self.default_icon = True
        self.IconPath = path_to_icon
        self.IconButtonLabel = wx.StaticText(self.tab_Profile, -1, _(u"Window Icon")+": ")
        self.IconButton = wx.BitmapButton(self.tab_Profile, -1, wx.Bitmap(os.path.expanduser(path_to_icon), wx.BITMAP_TYPE_ANY), size=wx.Size(136,136), )

        ###
        ### widgets for the SESSION tab
        ###
        self.AutoStartSession = wx.CheckBox(self.tab_Session, -1, _(u"Start session automatically after login"))
        self.AutoConnectSessionProfile = wx.CheckBox(self.tab_Session, -1, _(u"Login automatically after %s has started (needs --auto-connect)") % self._PyHocaGUI.appname)
        self.SessionTypeLabel = wx.StaticText(self.tab_Session, -1, _(u"Type")+": ")
        self.SessionType = wx.ComboBox(self.tab_Session, -1, choices=self.sessionChoices.values(), style=wx.CB_DROPDOWN|wx.CB_READONLY)
        self.ApplicationLabel = wx.StaticText(self.tab_Session, -1, _(u"Application")+": ")
        self.Application = wx.ComboBox(self.tab_Session, -1, choices=self.applicationChoices.values(), style=wx.CB_DROPDOWN|wx.CB_READONLY)
        self.CommandLabel = wx.StaticText(self.tab_Session, -1, _(u"Custom command")+": ")
        self.Command = wx.TextCtrl(self.tab_Session, -1, "", )
        self.XDMCPServerLabel = wx.StaticText(self.tab_Session, -1, _(u"XDMCP server")+": ")
        self.XDMCPServer = wx.TextCtrl(self.tab_Session, -1, "", )
        self.RDPServerLabel = wx.StaticText(self.tab_Session, -1, _(u"RDP server")+": ")
        self.RDPServer = wx.TextCtrl(self.tab_Session, -1, "", )
        self.RDPOptionsLabel = wx.StaticText(self.tab_Session, -1, _(u"RDP options")+": ")
        self.RDPOptions = wx.TextCtrl(self.tab_Session, -1, "", )
        self.RootlessSession = wx.CheckBox(self.tab_Session, -1, _(u"Integrate remote application(s) into local desktop (rootless mode)"))
        self.UsePublishedApplications = wx.CheckBox(self.tab_Session, -1, _(u"Menu of published applications"))
        self._last_pubapp_value = None
        self._last_auto_start_value = None

        ###
        ### widgets for the CONNECTION tab
        ###
        self.UserNameLabel = wx.StaticText(self.tab_Connection, -1, _(u"User")+": ")
        self.UserName = wx.TextCtrl(self.tab_Connection, -1, "", size=wx.Size(200,20))
        self.HostLabel = wx.StaticText(self.tab_Connection, -1, _(u"Host")+": ")
        self.Host = wx.TextCtrl(self.tab_Connection, -1, "", size=wx.Size(200,20))
        self.SSHPortLabel = wx.StaticText(self.tab_Connection, -1, _(u"Port")+": ")
        self.SSHPort = wx.SpinCtrl(self.tab_Connection, -1, "22", min=1, max=65534)
        self.SSHKeyFileLabel = wx.StaticText(self.tab_Connection, -1, _(u"Key")+": ")
        self.SSHKeyFile = wx.TextCtrl(self.tab_Connection, -1, style=wx.TE_PROCESS_ENTER)
        self.SSHKeyFileBrowseButton = wx.BitmapButton(self.tab_Connection, -1, wx.Bitmap('%s/PyHoca/16x16/system-search.png' % self._icons_location, wx.BITMAP_TYPE_ANY), size=wx.Size(self._textfield_height,self._textfield_height), )
        self.SSHAutoLogin = wx.CheckBox(self.tab_Connection, -1, _(u"Discover SSH keys or use SSH agent for X2Go authentication"))
        if PARAMIKO_FEATURE['forward-ssh-agent']:
            self.SSHForwardAuthAgent = wx.CheckBox(self.tab_Connection, -1, _(u"Enable forwarding of SSH authentication agent connections"))
        self.UniqueHostKeyAliases = wx.CheckBox(self.tab_Connection, -1, _(u"Store SSH host keys under (unique) X2Go session profile ID"))
        self.UseSSHProxy = wx.CheckBox(self.tab_Connection, -1, _(u"Server behind SSH proxy"))
        self.SSHProxyUserLabel = wx.StaticText(self.tab_Connection, -1, _(u"User")+": ")
        self.SSHProxyUser = wx.TextCtrl(self.tab_Connection, -1, "", size=wx.Size(80,20))
        self.SSHProxySameUser = wx.CheckBox(self.tab_Connection, -1, _(u"Use same username for X2Go and proxy host"))
        self.SSHProxySamePassword = wx.CheckBox(self.tab_Connection, -1, _(u"Use same authentication for X2Go and proxy host"))
        self.SSHProxyKeyFileLabel = wx.StaticText(self.tab_Connection, -1, _(u"Key file")+": ")
        self.SSHProxyKeyFile = wx.TextCtrl(self.tab_Connection, -1, style=wx.TE_PROCESS_ENTER)
        self.SSHProxyKeyFileBrowseButton = wx.BitmapButton(self.tab_Connection, -1, wx.Bitmap('%s/PyHoca/16x16/system-search.png' % self._icons_location, wx.BITMAP_TYPE_ANY), size=wx.Size(self._textfield_height,self._textfield_height), )
        self.SSHProxyHostLabel = wx.StaticText(self.tab_Connection, -1, _(u"Host")+": ")
        self.SSHProxyHost = wx.TextCtrl(self.tab_Connection, -1, "", size=wx.Size(80,20))
        self.SSHProxyPortLabel = wx.StaticText(self.tab_Connection, -1, _(u"Port")+": ")
        self.SSHProxyPort = wx.SpinCtrl(self.tab_Connection, -1, "22", min=1, max=65534)
        self.SSHProxyAutoLogin = wx.CheckBox(self.tab_Connection, -1, _(u"Discover SSH keys or use SSH agent for proxy authentication"))

        self.LinkSpeed = wx.Slider(self.tab_LinkQuality, -1, 0, 0, 4)
        self.ModemLabel = wx.StaticText(self.tab_LinkQuality, -1, "|\n "+_(u"Modem"), style=wx.ALIGN_CENTRE)
        self.ISDNLabel = wx.StaticText(self.tab_LinkQuality, -1, "|\n "+_(u"ISDN"), style=wx.ALIGN_CENTRE)
        self.ADSLLabel = wx.StaticText(self.tab_LinkQuality, -1, "|\n"+_(u"ADSL"), style=wx.ALIGN_CENTRE)
        self.WANLabel = wx.StaticText(self.tab_LinkQuality, -1, "|\n"+_(u"WAN"), style=wx.ALIGN_CENTRE)
        self.LANLabel = wx.StaticText(self.tab_LinkQuality, -1, "|\n"+_(u"LAN"), style=wx.ALIGN_CENTRE)

        self.CompressionLabel = wx.StaticText(self.tab_LinkQuality, -1, _(u"Method")+": ")
        self.Compression = wx.ComboBox(self.tab_LinkQuality, -1, choices=self.compressionChoices.values(), style=wx.CB_DROPDOWN)
        self.ImageQualityLabel = wx.StaticText(self.tab_LinkQuality, -1, _(u"Image quality")+": ")
        self.ImageQuality = wx.SpinCtrl(self.tab_LinkQuality, -1, "9", min=0, max=9)

        ###
        ### wigdets for the IO tab
        ###
        self.DisplayTypeFullscreen = wx.RadioButton(self.tab_IO, -1, _(u"Fullscreen"), style=wx.RB_GROUP)
        self.DisplayTypeMaximize = wx.RadioButton(self.tab_IO, -1, _(u"Maximized"))
        self.DisplayTypeCustom = wx.RadioButton(self.tab_IO, -1, _(u"Custom Size")+": ")
        self.ScreenWidthLabel = wx.StaticText(self.tab_IO, -1, '')
        self.ScreenWidth = wx.SpinCtrl(self.tab_IO, -1, "800", min=400, max=3000)
        self.ScreenHeightLabel = wx.StaticText(self.tab_IO, -1, "x")
        self.ScreenHeight = wx.SpinCtrl(self.tab_IO, -1, "600", min=500, max=3000)
        self.SetDisplayDPI = wx.CheckBox(self.tab_IO, -1, _(u"Set display DPI")+": ")
        self.DisplayDPI = wx.SpinCtrl(self.tab_IO, -1, "96", min=32, max=512)
        self.ClipboardModeLabel = wx.StaticText(self.tab_IO, -1, _(u"Allow copy'n'paste")+": ")
        self.ClipboardMode = wx.ComboBox(self.tab_IO, -1, choices=self.clipboardModeChoices.values(), style=wx.CB_DROPDOWN|wx.CB_READONLY)
        self.DontSetKeyboard = wx.RadioButton(self.tab_IO, -1, label=_(u"Do not set (use server-side tools to configure the keyboard)"), style=wx.RB_GROUP)
        self.AutoSetKeyboard = wx.RadioButton(self.tab_IO, -1, label=_(u"Automatically detect and use client-side keyboard configuration inside the session"))
        self.CustomSetKeyboard = wx.RadioButton(self.tab_IO, -1, label=_(u"Use custom keyboard settings as provided below") + ": ")
        self.KeyboardModelLabel = wx.StaticText(self.tab_IO, -1, _(u"Keyboard model")+": ")
        self.KeyboardModel = wx.TextCtrl(self.tab_IO, -1, "")
        self.KeyboardLayoutLabel = wx.StaticText(self.tab_IO, -1, _(u"Layout")+": ")
        self.KeyboardLayout = wx.TextCtrl(self.tab_IO, -1, "")
        self.KeyboardVariantLabel = wx.StaticText(self.tab_IO, -1, _(u"Layout variant")+": ")
        self.KeyboardVariant = wx.TextCtrl(self.tab_IO, -1, "")
        ###
        ### wigdets for the MEDIA tab
        ###
        self.EnableSound = wx.CheckBox(self.tab_MediaResources, -1, _(u"Enable sound support"))
        self.PulseAudio = wx.RadioButton(self.tab_MediaResources, -1, _(u"Pulse Audio"), style=wx.RB_GROUP)

        # Arts daemon is not supported by PyHoca-GUI / Python X2Go as it is outdated.
        # However, config files can contain an Arts configuration, so we will honour this
        self.Arts = wx.RadioButton(self.tab_MediaResources, -1, _(u"Arts (not supported)"))
        self.Arts.Enable(False)

        self.Esd = wx.RadioButton(self.tab_MediaResources, -1, _(u"esd"))
        self.DefaultSoundPort = wx.CheckBox(self.tab_MediaResources, -1, _(u"Use default sound port"))
        self.SoundPortLabel = wx.StaticText(self.tab_MediaResources, -1, _(u"Custom sound port")+": ")
        self.SoundPort = wx.SpinCtrl(self.tab_MediaResources, -1, "4713", min=23, max=64889)

        self.ClientSidePrinting = wx.CheckBox(self.tab_MediaResources, -1, _(u"Client Side printing"))

        ###
        ### wigdets for the SHARING tab
        ###

        self.UseLocalFolderSharing = wx.CheckBox(self.tab_SharedResources, -1, _(u"Use local folder sharing"))
        self.RestoreSharedLocalFolders = wx.CheckBox(self.tab_SharedResources, -1, _(u"Store share list at end of session"))
        self.SharedFolderPathLabel = wx.StaticText(self.tab_SharedResources, -1, _(u"Path")+": ")
        self.SharedFolderPath = wx.TextCtrl(self.tab_SharedResources, -1, "", style=wx.TE_PROCESS_ENTER)
        self.SharedFolderPathBrowseButton = wx.BitmapButton(self.tab_SharedResources, -1, wx.Bitmap('%s/PyHoca/16x16/system-search.png' % self._icons_location, wx.BITMAP_TYPE_ANY), size=wx.Size(self._textfield_height,self._textfield_height), )
        self.AddSharedFolderPathButton = wx.Button(self.tab_SharedResources, -1, _(u"Add"))
        self.SharedFoldersList = CheckListCtrl(self.tab_SharedResources)
        self.SharedFoldersList.InsertColumn(0, _("Local Path"), wx.LIST_FORMAT_LEFT)
        self.SharedFoldersList.InsertColumn(1, _("Connect Method"), wx.LIST_FORMAT_CENTER)
        self.DeleteSharedFolderPathButton = wx.Button(self.tab_SharedResources, -1, _(u"Delete"))

        self.UseEncodingConverter = wx.CheckBox(self.tab_SharedResources, -1, _(u"Convert between client and server encodings"))
        self.ClientEncodingLabel = wx.StaticText(self.tab_SharedResources, -1, _(u"Client encoding")+": ")
        self.ClientEncoding = wx.ComboBox(self.tab_SharedResources, -1, choices=_known_encodings, style=wx.CB_DROPDOWN|wx.CB_READONLY)
        self.ServerEncodingLabel = wx.StaticText(self.tab_SharedResources, -1, _(u"Server encoding")+": ")
        self.ServerEncoding = wx.ComboBox(self.tab_SharedResources, -1, choices=_known_encodings, style=wx.CB_DROPDOWN|wx.CB_READONLY)

        self.UseFileMIMEbox = wx.CheckBox(self.tab_SharedResources, -1, _(u"Use file MIME box for local file import"))
        self.FileMIMEboxExtensionsLabel = wx.StaticText(self.tab_SharedResources, -1, _(u"Extensions")+": ")
        self.FileMIMEboxExtensions = wx.TextCtrl(self.tab_SharedResources, -1, "", style=wx.TE_PROCESS_ENTER)
        self.FileMIMEboxActionLabel = wx.StaticText(self.tab_SharedResources, -1, _(u"Action")+": ")
        self.FileMIMEboxAction = wx.ComboBox(self.tab_SharedResources, -1, choices=self.mimeboxactionChoices.values(), style=wx.CB_DROPDOWN|wx.CB_READONLY)

        if self.action == 'ADD':
            self.OKButton = wx.Button(self, -1, _(u"Add"))
            self.DefaultButton = wx.Button(self, -1, _(u'Defaults'))
        else:
            self.OKButton = wx.Button(self, -1, _(u"Save"))
            self.DefaultButton = wx.Button(self, -1, _(u'Reset'))
        self.ApplyButton = wx.Button(self, -1, _(u"Apply"))
        self.CancelButton = wx.Button(self, -1, _(u"Cancel"))
        if self.session_profiles.is_mutable(self.profile_id):
            self.OKButton.SetDefault()
        elif self.action.startswith('ADD'):
            self.OKButton.SetDefault()
            self.ApplyButton.Enable(False)
        else:
            self.OKButton.Enable(False)
            self.ApplyButton.Enable(False)
            self.DefaultButton.Enable(False)
            self.CancelButton.SetDefault()

        self.__set_properties()
        self.__do_layout()
        self.__update_fields()

        self.Bind(wx.EVT_BUTTON, self.OnIconChange, self.IconButton)
        self.Bind(wx.EVT_COMBOBOX, self.OnSessionTypeSelected, self.SessionType)
        self.Bind(wx.EVT_CHECKBOX, self.OnUseDefaultSessionWindowTitle, self.UseDefaultSessionWindowTitle)
        self.Bind(wx.EVT_CHECKBOX, self.OnSetSessionWindowTitle, self.SetSessionWindowTitle)
        self.Bind(wx.EVT_TEXT, self.OnUserNameKeyPressed, self.UserName)
        self.Bind(wx.EVT_TEXT, self.OnHostKeyPressed, self.Host)
        self.Bind(wx.EVT_TEXT, self.OnSSHKeyFileKeyPressed, self.SSHKeyFile)
        self.Bind(wx.EVT_BUTTON, self.OnSSHKeyFileBrowse, self.SSHKeyFileBrowseButton)
        self.Bind(wx.EVT_BUTTON, self.OnSSHProxyKeyFileBrowse, self.SSHProxyKeyFileBrowseButton)
        self.Bind(wx.EVT_CHECKBOX, self.OnSSHAutoLogin, self.SSHAutoLogin)
        self.Bind(wx.EVT_CHECKBOX, self.OnUseSSHProxy, self.UseSSHProxy)
        self.Bind(wx.EVT_CHECKBOX, self.OnSSHProxySameUser, self.SSHProxySameUser)
        self.Bind(wx.EVT_CHECKBOX, self.OnSSHProxySamePassword, self.SSHProxySamePassword)
        self.Bind(wx.EVT_CHECKBOX, self.OnSSHProxyAutoLogin, self.SSHProxyAutoLogin)
        self.Bind(wx.EVT_COMBOBOX, self.OnCompressionSelected, self.Compression)
        self.Bind(wx.EVT_RADIOBUTTON, self.OnSetDisplayFullscreen, self.DisplayTypeFullscreen)
        self.Bind(wx.EVT_RADIOBUTTON, self.OnSetDisplayMaximize, self.DisplayTypeMaximize)
        self.Bind(wx.EVT_RADIOBUTTON, self.OnSetDisplayCustom, self.DisplayTypeCustom)
        self.Bind(wx.EVT_CHECKBOX, self.OnSetDisplayDPI, self.SetDisplayDPI)
        self.Bind(wx.EVT_RADIOBUTTON, self.OnSetKeyboard, self.DontSetKeyboard)
        self.Bind(wx.EVT_RADIOBUTTON, self.OnSetKeyboard, self.AutoSetKeyboard)
        self.Bind(wx.EVT_RADIOBUTTON, self.OnSetKeyboard, self.CustomSetKeyboard)
        self.Bind(wx.EVT_CHECKBOX, self.OnSoundEnable, self.EnableSound)
        self.Bind(wx.EVT_CHECKBOX, self.OnDefaultSoundPort, self.DefaultSoundPort)
        self.Bind(wx.EVT_RADIOBUTTON, self.OnPulseAudio, self.PulseAudio)
        self.Bind(wx.EVT_RADIOBUTTON, self.OnEsd, self.Esd)
        self.Bind(wx.EVT_BUTTON, self.OnSelectSharedFolderPath, self.SharedFolderPathBrowseButton)
        self.Bind(wx.EVT_BUTTON, self.OnAddSharedFolderPath, self.AddSharedFolderPathButton)
        self.Bind(wx.EVT_BUTTON, self.OnDeleteSharedFolderPath, self.DeleteSharedFolderPathButton)
        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.OnSharedFolderListItemSelected, self.SharedFoldersList)
        self.Bind(wx.EVT_LIST_ITEM_DESELECTED, self.OnSharedFolderListItemDeselected, self.SharedFoldersList)
        self.Bind(wx.EVT_TEXT, self.OnSharedFolderPathKeyPressed, self.SharedFolderPath)
        self.Bind(wx.EVT_TEXT_ENTER, self.OnAddSharedFolderPath, self.SharedFolderPath)
        self.Bind(wx.EVT_CHECKBOX, self.OnToggleEncodingConverter, self.UseEncodingConverter)
        self.Bind(wx.EVT_CHECKBOX, self.OnToggleLocalFolderSharing, self.UseLocalFolderSharing)
        self.Bind(wx.EVT_CHECKBOX, self.OnToggleFileMIMEbox, self.UseFileMIMEbox)
        self.Bind(wx.EVT_BUTTON, self.OnOKButton, self.OKButton)
        self.Bind(wx.EVT_BUTTON, self.OnApplyButton, self.ApplyButton)
        self.Bind(wx.EVT_BUTTON, self.OnCancel, self.CancelButton)
        self.Bind(wx.EVT_BUTTON, self.OnDefault, self.DefaultButton)

        # handle check/uncheck events on SharedFoldersList items
        def _SharedFoldersList_OnCheckItem(index, flag):
            if flag:
                self.SharedFoldersList.SetStringItem(index, 1, _("automatically"))
            else:
                self.SharedFoldersList.SetStringItem(index, 1, _("manually"))
        self.SharedFoldersList.OnCheckItem = _SharedFoldersList_OnCheckItem

    def __set_properties(self):
        """\
        Set hard-coded widget properties.

        """
        if self.action == 'ADD':
            self.SetTitle(_(u"%s Profile Manager - new profile") % self._PyHocaGUI.appname)
        elif self.action == 'EDIT_CONNECTED':
            if self._PyHocaGUI.session_profiles.is_mutable(profile_id=self.profile_id):
                self.SetTitle(_(u"%s Profile Manager - %s (connected)") % (self._PyHocaGUI.appname, self.profile_config['name']))
            else:
                self.SetTitle(_(u"%s Profile Manager - %s (connected, immutable)") % (self._PyHocaGUI.appname, self.profile_config['name']))
        else:
            if self._PyHocaGUI.session_profiles.is_mutable(profile_id=self.profile_id):
                self.SetTitle(_(u"%s Profile Manager - %s") % (self._PyHocaGUI.appname, self.profile_config['name']))
            else:
                self.SetTitle(_(u"%s Profile Manager - %s (immutable)") % (self._PyHocaGUI.appname, self.profile_config['name']))
        self.SetFont(wx.Font(9, wx.DEFAULT, wx.NORMAL, wx.NORMAL, 0, ""))
        self._textfield_height = 30

        self.ProfileNameLabel.SetMinSize((160, 16))
        self.ProfileName.SetMinSize((320, self._textfield_height))
        self.SetSessionWindowTitle.SetMinSize((-1, self._textfield_height))
        self.UseDefaultSessionWindowTitle.SetMinSize((-1, self._textfield_height))
        self.CustomSessionWindowTitleLabel.SetMinSize((160, 16))
        self.CustomSessionWindowTitle.SetMinSize((320, self._textfield_height))
        self.IconButtonLabel.SetMinSize((168, 16))

        self.AutoStartSession.SetMinSize((-1, self._textfield_height))
        self.AutoConnectSessionProfile.SetMinSize((-1, self._textfield_height))
        self.SessionTypeLabel.SetMinSize((120, 16))
        self.SessionType.SetMinSize((420, self._textfield_height))
        self.SessionType.SetSelection(5)
        self.ApplicationLabel.SetMinSize((120, 16))
        self.Application.SetMinSize((-1, self._textfield_height))
        self.Application.SetSelection(0)
        self.Command.SetMinSize((-1, self._textfield_height))
        self.XDMCPServerLabel.SetMinSize((120, 16))
        self.XDMCPServer.SetMinSize((-1, self._textfield_height))
        self.RDPServerLabel.SetMinSize((180, 16))
        self.RDPServer.SetMinSize((-1, self._textfield_height))
        self.RDPOptionsLabel.SetMinSize((180, 16))
        self.RDPOptions.SetMinSize((-1, self._textfield_height))
        self.RootlessSession.SetMinSize((-1, self._textfield_height))
        self.UsePublishedApplications.SetMinSize((-1, self._textfield_height))

        self.UserNameLabel.SetMinSize((-1, 16))
        self.UserName.SetMinSize((220, self._textfield_height))
        self.HostLabel.SetMinSize((-1, 16))
        self.Host.SetMinSize((220, self._textfield_height))
        self.SSHPortLabel.SetMinSize((-1, 16))
        self.SSHPort.SetMinSize((65, self._textfield_height))
        self.SSHKeyFileLabel.SetMinSize((-1, 16))
        self.SSHKeyFile.SetMinSize((220, self._textfield_height))
        self.SSHProxyUserLabel.SetMinSize((-1, 16))
        self.SSHProxyUser.SetMinSize((220, self._textfield_height))
        self.SSHProxyHostLabel.SetMinSize((-1, 16))
        self.SSHProxyHost.SetMinSize((220, self._textfield_height))
        self.SSHProxyPortLabel.SetMinSize((-1, 16))
        self.SSHProxyPort.SetMinSize((65, self._textfield_height))
        self.SSHProxyKeyFile.SetMinSize((220, self._textfield_height))
        if X2GOCLIENT_OS == 'Windows':
            self.LinkSpeed.SetMinSize((425, self._textfield_height))
        else:
            self.LinkSpeed.SetMinSize((440, self._textfield_height))
        self.ModemLabel.SetFont(wx.Font(8, wx.DEFAULT, wx.NORMAL, wx.NORMAL, 0, ""))
        self.ISDNLabel.SetFont(wx.Font(8, wx.DEFAULT, wx.NORMAL, wx.NORMAL, 0, ""))
        self.ADSLLabel.SetFont(wx.Font(8, wx.DEFAULT, wx.NORMAL, wx.NORMAL, 0, ""))
        self.WANLabel.SetFont(wx.Font(8, wx.DEFAULT, wx.NORMAL, wx.NORMAL, 0, ""))
        self.LANLabel.SetFont(wx.Font(8, wx.DEFAULT, wx.NORMAL, wx.NORMAL, 0, ""))
        self.CompressionLabel.SetMinSize((120, 16))
        self.Compression.SetMinSize((180, self._textfield_height))
        self.Compression.SetSelection(0)
        self.ImageQualityLabel.SetMinSize((120, 16))
        self.ImageQuality.SetMinSize((180, self._textfield_height))
        self.DisplayTypeFullscreen.SetMinSize((-1, self._textfield_height))
        self.DisplayTypeMaximize.SetMinSize((-1, self._textfield_height))
        self.ScreenWidth.SetMinSize((60, self._textfield_height))
        self.ScreenHeight.SetMinSize((60, self._textfield_height))
        self.SetDisplayDPI.SetMinSize((-1, self._textfield_height))
        self.DisplayDPI.SetMinSize((60, self._textfield_height))
        self.DontSetKeyboard.SetMinSize((-1, self._textfield_height))
        self.AutoSetKeyboard.SetMinSize((-1, self._textfield_height))
        self.CustomSetKeyboard.SetMinSize((-1, self._textfield_height))
        self.ClipboardMode.SetMinSize((220, -1))
        self.KeyboardModelLabel.SetMinSize((-1, 16))
        self.KeyboardModel.SetMinSize((-1, self._textfield_height))
        self.KeyboardLayoutLabel.SetMinSize((-1, 16))
        self.KeyboardLayout.SetMinSize((-1, self._textfield_height))
        self.KeyboardVariantLabel.SetMinSize((-1, 16))
        self.KeyboardVariant.SetMinSize((-1, self._textfield_height))
        self.PulseAudio.SetMinSize((-1, self._textfield_height))
        self.Arts.SetMinSize((-1, self._textfield_height))
        self.Esd.SetMinSize((-1, self._textfield_height))
        self.DefaultSoundPort.SetMinSize((-1, self._textfield_height))
        self.SoundPort.SetMinSize((-1, self._textfield_height))
        self.ClientSidePrinting.SetMinSize((-1, self._textfield_height))
        self.SharedFolderPath.SetMinSize((220, self._textfield_height))
        self.SharedFoldersList.SetMinSize((-1, 90))

        self.ClientEncoding.SetMinSize((140, self._textfield_height))
        self.ServerEncoding.SetMinSize((140, self._textfield_height))

        self.FileMIMEboxAction.SetMinSize((-1, self._textfield_height))
        _field_width = self.FileMIMEboxAction.GetBestSize().GetWidth()
        self.FileMIMEboxExtensions.SetMinSize((_field_width, self._textfield_height))

        self.OKButton.SetMinSize((-1, 30))
        self.ApplyButton.SetMinSize((-1, 30))
        self.CancelButton.SetMinSize((-1, 30))
        self.DefaultButton.SetMinSize((-1, 30))

    def __do_layout(self):
        """\
        Arrange/layout widgets on screen.

        """
        # PROFILE TAB
        sizer_1 = wx.BoxSizer(wx.VERTICAL)
        sizer_1_1 = wx.StaticBoxSizer(self.staticbox_Profile, wx.VERTICAL)
        sizer_1_1_1 = wx.FlexGridSizer(1, 2, 7, 9)
        sizer_1_1_1.Add(self.ProfileNameLabel, flag=wx.ALIGN_CENTRE_VERTICAL)
        sizer_1_1_1.Add(self.ProfileName)
        sizer_1_1.Add(sizer_1_1_1, flag=wx.EXPAND|wx.ALL, border=7)

        sizer_1_2 = wx.StaticBoxSizer(self.staticbox_Window, wx.VERTICAL)
        sizer_1_2_1 = wx.GridBagSizer(hgap=2,vgap=4)
        sizer_1_2_1.Add(self.SetSessionWindowTitle, pos=(0,0), span=(1,2))
        sizer_1_2_1.Add(self.UseDefaultSessionWindowTitle, pos=(1,0), span=(1,2))
        sizer_1_2_1.Add(self.CustomSessionWindowTitleLabel, pos=(2,0), )
        sizer_1_2_1.Add(self.CustomSessionWindowTitle, pos=(2,1), )
        sizer_1_2_1.Add(self.IconButtonLabel, flag=wx.TOP, pos=(3,0), )
        sizer_1_2_1.Add(self.IconButton, pos=(3,1), )

        sizer_1_2.Add(sizer_1_2_1, flag=wx.EXPAND|wx.ALL, border=7)

        sizer_1.Add(sizer_1_1, flag=wx.EXPAND|wx.ALL, border=5)
        sizer_1.Add(sizer_1_2, proportion=1, flag=wx.EXPAND|wx.ALL, border=5)
        self.tab_Profile.SetSizerAndFit(sizer_1)
        self.tab_Profile.Layout()

        # SESSION TAB
        sizer_2 = wx.BoxSizer(wx.VERTICAL)
        sizer_2_1 = wx.StaticBoxSizer(self.staticbox_SessionType, wx.VERTICAL)
        sizer_2_1_1 = wx.GridBagSizer(hgap=2,vgap=6)
        sizer_2_1_1.Add(self.AutoConnectSessionProfile, pos=(0,0), span=(1,2), flag=wx.EXPAND, )
        sizer_2_1_1.Add(self.AutoStartSession, pos=(1,0), span=(1,2), flag=wx.EXPAND, )
        sizer_2_1_1.Add(self.SessionTypeLabel, pos=(2,0), flag=wx.ALIGN_CENTRE_VERTICAL, )
        sizer_2_1_1.Add(self.SessionType, pos=(2,1), flag=wx.EXPAND, )
        sizer_2_1_1.Add(self.ApplicationLabel, pos=(3,0), flag=wx.ALIGN_CENTRE_VERTICAL, )
        sizer_2_1_1.Add(self.Application, pos=(3,1), flag=wx.EXPAND, )
        sizer_2_1_1.Add(self.CommandLabel, pos=(4,0), flag=wx.ALIGN_CENTRE_VERTICAL, )
        sizer_2_1_1.Add(self.Command, pos=(4,1), flag=wx.EXPAND, )
        sizer_2_1_1.Add(self.XDMCPServerLabel, (5,0), flag=wx.ALIGN_CENTRE_VERTICAL, )
        sizer_2_1_1.Add(self.XDMCPServer, pos=(5,1), flag=wx.EXPAND, )
        sizer_2_1_1.Add(self.RDPServerLabel, pos=(6,0), flag=wx.ALIGN_CENTRE_VERTICAL, )
        sizer_2_1_1.Add(self.RDPServer, pos=(6,1), flag=wx.EXPAND, )
        sizer_2_1_1.Add(self.RDPOptionsLabel, pos=(7,0), flag=wx.ALIGN_CENTRE_VERTICAL, )
        sizer_2_1_1.Add(self.RDPOptions, pos=(7,1), flag=wx.EXPAND, )
        sizer_2_1_1.Add(self.RootlessSession, pos=(8,0), span=(1,2), flag=wx.EXPAND, )
        sizer_2_1_1.Add(self.UsePublishedApplications, pos=(9,0), span=(1,2), flag=wx.EXPAND, )
        sizer_2_1.Add(sizer_2_1_1, flag=wx.EXPAND|wx.ALL, border=7)
        sizer_2.Add(sizer_2_1, proportion=1, flag=wx.EXPAND|wx.ALL, border=5)
        self.tab_Session.SetSizerAndFit(sizer_2)
        self.tab_Session.Layout()

        ## CONNECTION TAB
        sizer_3 = wx.BoxSizer(wx.VERTICAL)
        sizer_3_1 = wx.StaticBoxSizer(self.staticbox_Server, wx.VERTICAL)
        sizer_3_1_1 = wx.GridBagSizer(hgap=6,vgap=6)
        sizer_3_1_1.Add(self.UserNameLabel, pos=(0,0), flag=wx.ALIGN_CENTRE_VERTICAL)
        sizer_3_1_1.Add(self.UserName, pos=(0,1))
        sizer_3_1_1.Add((16,0), pos=(0,2))
        sizer_3_1_1.Add(self.SSHKeyFileLabel, pos=(0,3), flag=wx.ALIGN_CENTRE_VERTICAL)
        sizer_3_1_1.Add(self.SSHKeyFile, pos=(0,4), flag=wx.ALIGN_CENTRE_VERTICAL)
        sizer_3_1_1.Add(self.SSHKeyFileBrowseButton, pos=(0,5), flag=wx.ALIGN_CENTRE_VERTICAL|wx.LEFT, border=2)
        sizer_3_1_1.Add(self.HostLabel, pos=(1,0), flag=wx.ALIGN_CENTRE_VERTICAL)
        sizer_3_1_1.Add(self.Host, pos=(1,1))
        sizer_3_1_1.Add(self.SSHPortLabel, pos=(1,3), flag=wx.ALIGN_CENTRE_VERTICAL)
        sizer_3_1_1.Add(self.SSHPort, pos=(1,4), span=(1,2))
        sizer_3_1_1.Add(self.SSHAutoLogin, pos=(2,0), span=(1,6), flag=wx.ALIGN_CENTRE_VERTICAL)
        if PARAMIKO_FEATURE['forward-ssh-agent']:
            sizer_3_1_1.Add(self.SSHForwardAuthAgent, pos=(3,0), span=(1,6), flag=wx.ALIGN_CENTRE_VERTICAL)
        sizer_3_1_1.Add(self.UniqueHostKeyAliases, pos=(4,0), span=(1,6))
        sizer_3_1_1.Add(self.UseSSHProxy, pos=(5,0), span=(1,6), flag=wx.ALIGN_CENTRE_VERTICAL)
        sizer_3_1.Add(sizer_3_1_1, flag=wx.EXPAND|wx.ALL, border=7)

        sizer_3_2 = wx.StaticBoxSizer(self.staticbox_Proxy, wx.VERTICAL)
        sizer_3_2_1 = wx.GridBagSizer(hgap=6,vgap=6)
        sizer_3_2_1.Add(self.SSHProxySameUser, pos=(0,0), span=(1,6))
        sizer_3_2_1.Add(self.SSHProxySamePassword, pos=(1,0), span=(1,6), flag=wx.ALIGN_CENTRE_VERTICAL)
        sizer_3_2_1.Add(self.SSHProxyUserLabel, pos=(2,0), flag=wx.ALIGN_CENTRE_VERTICAL)
        sizer_3_2_1.Add(self.SSHProxyUser, pos=(2,1), flag=wx.ALIGN_CENTRE_VERTICAL)
        sizer_3_2_1.Add((16,0), pos=(2,2))
        sizer_3_2_1.Add(self.SSHProxyKeyFileLabel, pos=(2,3),  flag=wx.ALIGN_CENTRE_VERTICAL)
        sizer_3_2_1.Add(self.SSHProxyKeyFile, pos=(2,4), flag=wx.ALIGN_CENTRE_VERTICAL)
        sizer_3_2_1.Add(self.SSHProxyKeyFileBrowseButton, pos=(2,5), flag=wx.ALIGN_CENTRE_VERTICAL|wx.LEFT, border=2)
        sizer_3_2_1.Add(self.SSHProxyHostLabel, pos=(3,0), flag=wx.ALIGN_CENTRE_VERTICAL)
        sizer_3_2_1.Add(self.SSHProxyHost, pos=(3,1), flag=wx.ALIGN_CENTRE_VERTICAL)
        sizer_3_2_1.Add(self.SSHProxyPortLabel, pos=(3,3), flag=wx.ALIGN_CENTRE_VERTICAL)
        sizer_3_2_1.Add(self.SSHProxyPort, pos=(3,4), span=(1,2), flag=wx.ALIGN_CENTRE_VERTICAL)
        sizer_3_2_1.Add(self.SSHProxyAutoLogin, pos=(4,0), span=(1,6), flag=wx.ALIGN_CENTRE_VERTICAL)
        sizer_3_2.Add(sizer_3_2_1, flag=wx.EXPAND|wx.ALL, border=7)

        sizer_3.Add(sizer_3_1, flag=wx.EXPAND|wx.ALL, border=5)
        sizer_3.Add(sizer_3_2, proportion=1, flag=wx.EXPAND|wx.ALL, border=5)
        self.tab_Connection.SetSizerAndFit(sizer_3)
        self.tab_Connection.Layout()

        ## LINK QUALITY TAB
        sizer_4 = wx.BoxSizer(wx.VERTICAL)
        sizer_4_1 = wx.StaticBoxSizer(self.staticbox_LinkSpeed, wx.VERTICAL)
        sizer_4_1_1 = wx.BoxSizer(wx.VERTICAL)
        sizer_4_1_1_1 = wx.BoxSizer(wx.VERTICAL)
        sizer_4_1_1_1.Add(self.LinkSpeed)
        sizer_4_1_1_2 = wx.GridSizer(1,5,0,0)
        sizer_4_1_1_2.SetMinSize((454/5*6 - 30, 36))
        sizer_4_1_1_2.Add(self.ModemLabel, flag=wx.ALIGN_CENTRE_HORIZONTAL)
        sizer_4_1_1_2.Add(self.ISDNLabel, flag=wx.ALIGN_CENTRE_HORIZONTAL)
        sizer_4_1_1_2.Add(self.ADSLLabel, flag=wx.ALIGN_CENTRE_HORIZONTAL)
        sizer_4_1_1_2.Add(self.WANLabel, flag=wx.ALIGN_CENTRE_HORIZONTAL)
        sizer_4_1_1_2.Add(self.LANLabel, flag=wx.ALIGN_CENTRE_HORIZONTAL)
        sizer_4_1_1.Add(sizer_4_1_1_1, flag=wx.ALIGN_CENTRE_HORIZONTAL)
        sizer_4_1_1.Add(sizer_4_1_1_2, flag=wx.ALIGN_CENTRE_HORIZONTAL)
        sizer_4_1.Add(sizer_4_1_1, flag=wx.EXPAND|wx.ALL, border=7)

        sizer_4_2 = wx.StaticBoxSizer(self.staticbox_Compression, wx.VERTICAL)
        sizer_4_2_1 = wx.BoxSizer(wx.VERTICAL)
        sizer_4_2_1_1 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_4_2_1_1.Add(self.CompressionLabel, flag=wx.ALIGN_CENTRE_VERTICAL)
        sizer_4_2_1_1.Add(self.Compression)
        sizer_4_2_1_1.Add((0,32))
        sizer_4_2_1_2 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_4_2_1_2.Add(self.ImageQualityLabel, flag=wx.ALIGN_CENTRE_VERTICAL)
        sizer_4_2_1_2.Add(self.ImageQuality)
        sizer_4_2_1.Add(sizer_4_2_1_1, flag=wx.EXPAND)
        sizer_4_2_1.Add(sizer_4_2_1_2, flag=wx.EXPAND)
        sizer_4_2.Add(sizer_4_2_1, flag=wx.EXPAND|wx.ALL, border=7)

        sizer_4.Add(sizer_4_1, flag=wx.EXPAND|wx.ALL, border=5)
        sizer_4.Add(sizer_4_2, proportion=1, flag=wx.EXPAND|wx.ALL, border=5)
        self.tab_LinkQuality.SetSizerAndFit(sizer_4)
        self.tab_LinkQuality.Layout()

        ## INPUT/OUTPUT TAB
        sizer_5 = wx.BoxSizer(wx.VERTICAL)
        sizer_5_1 = wx.StaticBoxSizer(self.staticbox_Display, wx.VERTICAL)
        sizer_5_1_1 = wx.BoxSizer(wx.VERTICAL)
        sizer_5_1_1_1 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_5_1_1_1.Add(self.DisplayTypeFullscreen, flag=wx.ALIGN_CENTRE_VERTICAL)
        sizer_5_1_1_1.Add((16, 0))
        sizer_5_1_1_1.Add(self.DisplayTypeMaximize, flag=wx.ALIGN_CENTRE_VERTICAL)
        sizer_5_1_1_1.Add((16, 0))
        sizer_5_1_1_1.Add(self.DisplayTypeCustom, flag=wx.ALIGN_CENTRE_VERTICAL)
        sizer_5_1_1_1.Add(self.ScreenWidthLabel, flag=wx.ALIGN_CENTRE_VERTICAL)
        sizer_5_1_1_1.Add((8,0))
        sizer_5_1_1_1.Add(self.ScreenWidth)
        sizer_5_1_1_1.Add((8,0))
        sizer_5_1_1_1.Add(self.ScreenHeightLabel, flag=wx.ALIGN_CENTRE_VERTICAL)
        sizer_5_1_1_1.Add((8,0))
        sizer_5_1_1_1.Add(self.ScreenHeight)
        sizer_5_1_1_2 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_5_1_1_2.Add((-1,48))
        sizer_5_1_1_2.Add(self.SetDisplayDPI, flag=wx.ALIGN_CENTRE_VERTICAL)
        sizer_5_1_1_2.Add((8,0))
        sizer_5_1_1_2.Add(self.DisplayDPI, flag=wx.ALIGN_CENTRE_VERTICAL)
        sizer_5_1_1.Add(sizer_5_1_1_1)
        sizer_5_1_1.Add(sizer_5_1_1_2)
        sizer_5_1.Add(sizer_5_1_1, flag=wx.EXPAND|wx.ALL, border=7)

        sizer_5_2 = wx.StaticBoxSizer(self.staticbox_Clipboard, wx.VERTICAL)
        sizer_5_2_1 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_5_2_1_1 = wx.GridBagSizer(hgap=1, vgap=3)
        sizer_5_2_1_1.Add(self.ClipboardModeLabel, flag=wx.ALIGN_CENTRE_VERTICAL, pos=(0,0),)
        sizer_5_2_1_1.Add((8,0), pos=(0,1),)
        sizer_5_2_1_1.Add(self.ClipboardMode, flag=wx.EXPAND|wx.ALIGN_CENTRE_VERTICAL, pos=(0,2),)
        sizer_5_2_1.Add(sizer_5_2_1_1)
        sizer_5_2.Add(sizer_5_2_1, flag=wx.EXPAND|wx.ALL, border=7)

        sizer_5_3 = wx.StaticBoxSizer(self.staticbox_Keyboard, wx.VERTICAL)
        sizer_5_3_1 = wx.BoxSizer(wx.VERTICAL)
        sizer_5_3_1_1 = wx.BoxSizer(wx.VERTICAL)
        sizer_5_3_1_1.Add(self.DontSetKeyboard, )
        sizer_5_3_1_1.Add(self.AutoSetKeyboard, )
        sizer_5_3_1_1.Add(self.CustomSetKeyboard, )
        sizer_5_3_1_1.Add((0,8))
        sizer_5_3_1_2 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_5_3_1_2.Add((32,0))
        sizer_5_3_1_2_1 = wx.GridBagSizer(hgap=2, vgap=2)
        sizer_5_3_1_2_1.Add(self.KeyboardModelLabel, pos=(0,0),)
        sizer_5_3_1_2_1.Add(self.KeyboardModel, flag=wx.EXPAND, pos=(1,0),)
        sizer_5_3_1_2_1.Add((32,0), pos=(0,1), span=(2,1))
        sizer_5_3_1_2_1.Add(self.KeyboardLayoutLabel, flag=wx.ALIGN_CENTRE_VERTICAL, pos=(0,2), )
        sizer_5_3_1_2_1.Add(self.KeyboardLayout, flag=wx.EXPAND, pos=(1,2), )
        sizer_5_3_1_2_1.Add((32,0), pos=(0,3), span=(2,1))
        sizer_5_3_1_2_1.Add(self.KeyboardVariantLabel, pos=(0,4),)
        sizer_5_3_1_2_1.Add(self.KeyboardVariant, flag=wx.EXPAND, pos=(1,4),)
        sizer_5_3_1_2.Add(sizer_5_3_1_2_1)
        sizer_5_3_1.Add(sizer_5_3_1_1)
        sizer_5_3_1.Add(sizer_5_3_1_2)
        sizer_5_3.Add(sizer_5_3_1, flag=wx.EXPAND|wx.ALL, border=7)

        sizer_5.Add(sizer_5_1, flag=wx.EXPAND|wx.ALL, border=5)
        sizer_5.Add(sizer_5_2, flag=wx.EXPAND|wx.ALL, border=5)
        sizer_5.Add(sizer_5_3, proportion=1, flag=wx.EXPAND|wx.ALL, border=5)
        self.tab_IO.SetSizerAndFit(sizer_5)
        self.tab_IO.Layout()

        # MEDIA TAB
        sizer_6 = wx.BoxSizer(wx.VERTICAL)
        sizer_6_1 = wx.StaticBoxSizer(self.staticbox_Sound, wx.VERTICAL)
        sizer_6_1_1 = wx.GridBagSizer(vgap=4, hgap=2)
        sizer_6_1_1.Add(self.EnableSound, pos=(0,0), span=(1,2), border=16, )
        sizer_6_1_1.Add(self.PulseAudio, pos=(1,0), flag=wx.RIGHT, border=16, )
        sizer_6_1_1.Add(self.Arts, pos=(2,0), flag=wx.RIGHT, border=16, )
        sizer_6_1_1.Add(self.Esd, pos=(3,0), flag=wx.RIGHT, border=16, )
        sizer_6_1_1.Add(self.DefaultSoundPort, pos=(1,1), )
        sizer_6_1_1_1 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_6_1_1_1.Add(self.SoundPortLabel, flag=wx.ALIGN_CENTRE_VERTICAL)
        sizer_6_1_1_1.Add((8, -1))
        sizer_6_1_1_1.Add(self.SoundPort, flag=wx.ALIGN_CENTRE_VERTICAL)
        sizer_6_1_1.Add(sizer_6_1_1_1, pos=(2,1), )
        sizer_6_1.Add(sizer_6_1_1, flag=wx.EXPAND|wx.ALL, border=7)

        sizer_6_2 = wx.StaticBoxSizer(self.staticbox_Printing, wx.VERTICAL)
        sizer_6_2.Add(self.ClientSidePrinting, flag=wx.EXPAND|wx.ALL, border=7)

        sizer_6.Add(sizer_6_1, flag=wx.EXPAND|wx.ALL, border=5)
        sizer_6.Add(sizer_6_2, proportion=1, flag=wx.EXPAND|wx.ALL, border=5)
        self.tab_MediaResources.SetSizerAndFit(sizer_6)
        self.tab_MediaResources.Layout()

        # RESOURCE SHARING TAB
        sizer_7 = wx.BoxSizer(wx.VERTICAL)
        sizer_7_1 = wx.StaticBoxSizer(self.staticbox_FolderSharing, wx.VERTICAL)
        sizer_7_1_1 = wx.BoxSizer(wx.VERTICAL)
        sizer_7_1_1_1 = wx.GridBagSizer(vgap=1, hgap=3)
        sizer_7_1_1_1.Add(self.UseLocalFolderSharing, pos=(0,0))
        sizer_7_1_1_1.Add((32,-1), pos=(0,1))
        sizer_7_1_1_1.Add(self.RestoreSharedLocalFolders, pos=(0,2), flag=wx.ALIGN_RIGHT|wx.EXPAND)
        sizer_7_1_1_2 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_7_1_1_2_1 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_7_1_1_2_1.Add(self.SharedFolderPathLabel, flag=wx.ALIGN_CENTRE_VERTICAL)
        sizer_7_1_1_2_1.Add(self.SharedFolderPath, flag=wx.ALIGN_CENTRE_VERTICAL|wx.LEFT, border=5)
        sizer_7_1_1_2_1.Add(self.SharedFolderPathBrowseButton, flag=wx.ALIGN_CENTRE_VERTICAL|wx.LEFT, border=2)
        sizer_7_1_1_2_2 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_7_1_1_2_3 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_7_1_1_2_3.Add(self.AddSharedFolderPathButton, flag=wx.ALIGN_CENTRE_VERTICAL)
        sizer_7_1_1_2_3.Add(self.DeleteSharedFolderPathButton, flag=wx.ALIGN_CENTRE_VERTICAL|wx.LEFT, border=2)
        sizer_7_1_1_2.Add(sizer_7_1_1_2_1, flag=wx.EXPAND|wx.ALIGN_LEFT)
        sizer_7_1_1_2.Add(sizer_7_1_1_2_2, proportion=1, flag=wx.EXPAND|wx.ALIGN_LEFT)
        sizer_7_1_1_2.Add(sizer_7_1_1_2_3, flag=wx.EXPAND|wx.ALIGN_RIGHT)
        sizer_7_1_1_3 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_7_1_1_3.Add(self.SharedFoldersList, proportion=1, flag=wx.EXPAND)
        sizer_7_1_1.Add(sizer_7_1_1_1, flag=wx.EXPAND|wx.BOTTOM, border=12)
        sizer_7_1_1.Add(sizer_7_1_1_2, flag=wx.EXPAND)
        sizer_7_1_1.Add(sizer_7_1_1_3, flag=wx.EXPAND|wx.TOP|wx.BOTTOM, border=5)
        sizer_7_1_2 = wx.BoxSizer(wx.VERTICAL)
        sizer_7_1_2_1 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_7_1_2_1.Add(self.UseEncodingConverter, flag=wx.BOTTOM, border=5)
        sizer_7_1_2_2 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_7_1_2_2.Add(self.ClientEncodingLabel, flag=wx.ALIGN_CENTRE_VERTICAL)
        sizer_7_1_2_2.Add((8,0))
        sizer_7_1_2_2.Add(self.ClientEncoding)
        sizer_7_1_2_2.Add((16,0))
        sizer_7_1_2_2.Add(self.ServerEncodingLabel, flag=wx.ALIGN_CENTRE_VERTICAL)
        sizer_7_1_2_2.Add((8,0))
        sizer_7_1_2_2.Add(self.ServerEncoding)
        sizer_7_1_2.Add(sizer_7_1_2_1, flag=wx.EXPAND)
        sizer_7_1_2.Add(sizer_7_1_2_2, flag=wx.EXPAND)
        sizer_7_1.Add(sizer_7_1_1, flag=wx.EXPAND|wx.ALL, border=7)
        sizer_7_1.Add(sizer_7_1_2, flag=wx.EXPAND|wx.ALL, border=7)

        sizer_7_2 = wx.StaticBoxSizer(self.staticbox_FileMIMEbox, wx.VERTICAL)
        sizer_7_2_1 = wx.BoxSizer(wx.VERTICAL)
        sizer_7_2_1_1 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_7_2_1_1.Add(self.UseFileMIMEbox, flag=wx.BOTTOM, border=5)
        sizer_7_2_1_2 = wx.GridBagSizer(vgap=2, hgap=3)
        sizer_7_2_1_2.Add(self.FileMIMEboxActionLabel, pos=(0,0), flag=wx.ALIGN_CENTRE_VERTICAL)
        sizer_7_2_1_2.Add(self.FileMIMEboxAction, pos=(0,2))
        sizer_7_2_1_2.Add((8,0), pos=(0,1))
        sizer_7_2_1_2.Add((8,0), pos=(1,1))
        sizer_7_2_1_2.Add(self.FileMIMEboxExtensionsLabel, pos=(1,0), flag=wx.ALIGN_CENTRE_VERTICAL)
        sizer_7_2_1_2.Add(self.FileMIMEboxExtensions, pos=(1,2))
        sizer_7_2_1.Add(sizer_7_2_1_1, flag=wx.EXPAND)
        sizer_7_2_1.Add(sizer_7_2_1_2, flag=wx.EXPAND)
        sizer_7_2.Add(sizer_7_2_1, flag=wx.EXPAND|wx.ALL, border=7)

        sizer_7.Add(sizer_7_1, flag=wx.EXPAND|wx.ALL, border=5)
        sizer_7.Add(sizer_7_2, proportion=1, flag=wx.EXPAND|wx.ALL, border=5)
        self.tab_SharedResources.SetSizerAndFit(sizer_7)
        self.tab_SharedResources.Layout()

        self.X2GoTabs.AddPage(self.tab_Profile, _(u"Profile"))
        self.X2GoTabs.AddPage(self.tab_Session, _(u"Session"))
        self.X2GoTabs.AddPage(self.tab_Connection, _(u"Connection"))
        self.X2GoTabs.AddPage(self.tab_LinkQuality, _(u"Link Quality"))
        self.X2GoTabs.AddPage(self.tab_IO, _(u"Input/Output"))
        self.X2GoTabs.AddPage(self.tab_MediaResources, _(u"Media"))
        self.X2GoTabs.AddPage(self.tab_SharedResources, _(u"Sharing"))

        # the bottom area with OK, Defaults and Cancel buttons
        sizer_B = wx.BoxSizer(wx.HORIZONTAL)
        sizer_B_1 = wx.GridSizer(1, 4, 7, 14)
        sizer_B_1.Add(self.OKButton)
        sizer_B_1.Add(self.ApplyButton)
        sizer_B_1.Add(self.DefaultButton)
        sizer_B_1.Add(self.CancelButton)
        sizer_B.Add(sizer_B_1, proportion=1, flag=wx.EXPAND|wx.ALL, border=5)

        # put it all together...
        MainSizer = wx.BoxSizer(wx.VERTICAL)
        MainSizer.Add(self.X2GoTabs, proportion=1, flag=wx.EXPAND|wx.FIXED_MINSIZE)
        MainSizer.Add(sizer_B, flag=wx.ALIGN_RIGHT)
        self.SetSizerAndFit(MainSizer)

        max1_x, max1_y = self.tab_Profile.GetBestSize()
        max2_x, max2_y = self.tab_Session.GetBestSize()
        max3_x, max3_y = self.tab_Connection.GetBestSize()
        max4_x, max4_y = self.tab_LinkQuality.GetBestSize()
        max5_x, max5_y = self.tab_IO.GetBestSize()
        max6_x, max6_y = self.tab_MediaResources.GetBestSize()
        max7_x, max7_y = self.tab_SharedResources.GetBestSize()

        self.SetSize((max(max1_x, max2_x, max3_x, max4_x, max5_x, max6_x, max7_x) * 1.05, max(max1_y, max2_y, max3_y, max4_y, max5_y, max6_y, max7_y) * 1.10 + 50))

        self.SetAutoLayout(True)
        self.Layout()
        self.CentreOnScreen()
        self.Show(True)

        # derive ListCtrl widths from sizer information
        _sizer_width = sizer_7_1_1_3.GetSize().GetWidth()
        self.SharedFoldersList.SetColumnWidth(0, abs(_sizer_width*.7))
        self.SharedFoldersList.SetColumnWidth(1, abs(_sizer_width*.3))

    def __update_fields(self):
        """\
        Update widget fields/values from session profile configuration.

        """
        self.ProfileName.SetValue(self.profile_config['name'])
        self.SetSessionWindowTitle.SetValue(self.profile_config['setsessiontitle'])
        self.CustomSessionWindowTitle.SetValue(self.profile_config['sessiontitle'])

        if type(self.profile_config['host']) is types.ListType:
            self.Host.SetValue(",".join(self.profile_config['host']))
        else:
            self.Host.SetValue(self.profile_config['host'])
        self.UserName.SetValue(self.profile_config['user'])
        self.SSHPort.SetValue(self.profile_config['sshport'])
        self.SSHAutoLogin.SetValue(self.profile_config['autologin'])
        if PARAMIKO_FEATURE['forward-ssh-agent']:
            self.SSHForwardAuthAgent.SetValue(self.profile_config['forwardsshagent'])
        self.SSHKeyFile.SetValue(self.profile_config['key'])
        if self.profile_config['autologin']:
            self.SSHKeyFileLabel.Enable(False)
            self.SSHKeyFile.Enable(False)
            self.SSHKeyFileBrowseButton.Enable(False)
        self.UseSSHProxy.SetValue(self.profile_config['usesshproxy'])
        self.UniqueHostKeyAliases.SetValue(self.profile_config['uniquehostkeyaliases'])
        self.SSHProxyAutoLogin.SetValue(self.profile_config['sshproxyautologin'])

        _ssh_proxy = self.profile_config['usesshproxy']
        _ssh_proxy_host = self.profile_config['sshproxyhost'].strip()
        _ssh_proxy_port = 22
        try:
            _ssh_proxy_port = int(self.profile_config['sshproxyport'])
        except TypeError:
            pass
        if ":" in _ssh_proxy_host:
            try:
                _ssh_proxy_port = int(_ssh_proxy_host.split(":")[1])
            except TypeError:
                pass
            _ssh_proxy_host = _ssh_proxy_host.split(":")[0]
        self.SSHProxyHost.SetValue(_ssh_proxy_host)
        self.SSHProxyPort.SetValue(_ssh_proxy_port)
        if self.profile_config['sshproxysameuser']:
            self.SSHProxyUser.SetValue(self.profile_config['user'])
        else:
            self.SSHProxyUser.SetValue(self.profile_config['sshproxyuser'])

        if self.profile_config['sshproxysamepass']:
            self.SSHProxyKeyFile.SetValue(self.profile_config['sshproxykeyfile'])
        else:
            self.SSHProxyKeyFile.SetValue(self.profile_config['key'])

        self.UseSSHProxy.SetValue(_ssh_proxy)
        self.SSHProxySameUser.SetValue(self.profile_config['sshproxysameuser'])
        self.SSHProxySamePassword.SetValue(self.profile_config['sshproxysamepass'])
        self._toggle_SSHProxy()

        self.AutoStartSession.SetValue(self.profile_config['autostart'])
        self.AutoConnectSessionProfile.SetValue(self.profile_config['autoconnect'])

        _command = self.profile_config['command']
        _published = self.profile_config['published']
        self.RootlessSession.SetValue(self.profile_config['rootless'])

        # disable all command relevant widgets first
        self.ApplicationLabel.Enable(False)
        self.Application.Enable(False)
        self.CommandLabel.Enable(False)
        self.Command.Enable(False)
        self.XDMCPServerLabel.Enable(False)
        self.XDMCPServer.Enable(False)
        self.RootlessSession.Enable(False)

        self.UsePublishedApplications.SetValue(_published)
        self.Application.SetItems(self.applicationChoices.values())
        # XFCE4 has been renamed to XFCE for 0.2.1.0
        if _command == "XFCE4": _command = "XFCE"
        if _command == 'RDP' and self.profile_config['directrdp']:
            self.SessionType.SetValue(self.sessionChoices['DirectRDP'])
            self.Command.SetValue('')
        elif _command == 'SHADOW':
            self.SessionType.SetValue(self.sessionChoices[_command])
            self.Application.SetValue('')
            self.Command.SetValue('')
            self.AutoStartSession.Enable(False)
            self.AutoStartSession.SetValue(False)
        elif _command in self.sessionChoices.keys():
            self.SessionType.SetValue(self.sessionChoices[_command])
            self.Application.SetValue('')
            self.Command.SetValue('')
            if _command not in defaults.X2GO_DESKTOPSESSIONS.keys():
                self.RootlessSession.SetValue(True)
        elif _command in self.applicationChoices.keys():
            self.SessionType.SetValue(self.sessionChoices['APPLICATION'])
            self.ApplicationLabel.Enable(True)
            self.Application.Enable(True)
            self.Application.SetValue(self.applicationChoices[_command])
            self._last_application = self.applicationChoices[_command]
            self.Command.SetValue('')
            self.UsePublishedApplications.SetValue(False)
            self.UsePublishedApplications.Enable(False)
            self.RootlessSession.SetValue(True)
        elif not _command and _published:
            self.SessionType.SetValue(self.sessionChoices['PUBLISHEDAPPLICATIONS'])
            self.UsePublishedApplications.Enable(False)
            self.AutoStartSession.Enable(False)
            self.AutoStartSession.SetValue(True)
            self.Command.SetValue('')
            self._last_pubapp_value = True
            self.RootlessSession.SetValue(True)
        else:
            self.SessionType.SetValue(self.sessionChoices['CUSTOM'])
            self.UsePublishedApplications.SetValue(False)
            self.UsePublishedApplications.Enable(False)
            self.Command.Enable(True)
            self.Command.SetValue(_command)
            self.RootlessSession.Enable(True)

        if _command == 'XDMCP':
            self.XDMCPServerLabel.Enable(True)
            self.XDMCPServer.Enable(True)
            self.UsePublishedApplications.SetValue(False)
            self.UsePublishedApplications.Enable(False)
            self.RootlessSession.Enable(False)

        if self.profile_config['speed'] in range(5):
            _link_speed = self.profile_config['speed']
        else:
            _link_speed = self.profileManagerDefaults['speed']
        self.LinkSpeed.SetValue(_link_speed)
        if '%s-%%' % self.profile_config['pack'] in self._compressions and self.profile_config['quality'] and (self.profile_config['quality'] in range(1,10)):
            self.Compression.SetValue('%s-%%' % self.profile_config['pack'])
            self.ImageQuality.SetValue(self.profile_config['quality'])
            self.ImageQuality.Enable(True)
        else:
            self.Compression.SetValue(self.profile_config['pack'])
            self.ImageQuality.SetValue(9)
            self.ImageQuality.Enable(False)

        if self.profile_config['usekbd']:
            self.DontSetKeyboard.SetValue(False)
            if self.profile_config['type'] == 'auto':
                self.AutoSetKeyboard.SetValue(True)
                self.CustomSetKeyboard.SetValue(False)
            else:
                self.AutoSetKeyboard.SetValue(False)
                self.CustomSetKeyboard.SetValue(True)
        else:
            self.DontSetKeyboard.SetValue(True)
        if self.profile_config['type'] == 'auto':
            self.KeyboardModel.SetValue(_(u'<xkbtype>'))
            self.KeyboardLayout.SetValue(_(u'<xkblayout>'))
            self.KeyboardVariant.SetValue(_(u'<xkbvariant>'))
        else:
            self.KeyboardModel.SetValue(self.profile_config['type'])
            self.KeyboardLayout.SetValue(self.profile_config['layout'])
            self.KeyboardVariant.SetValue(self.profile_config['variant'])

        if self.profile_config['clipboard'] in self.clipboardModeChoices.keys():
            self.ClipboardMode.SetValue(self.clipboardModeChoices[self.profile_config['clipboard']])
        else:
            self.ClipboardMode.SetValue(self.clipboardModeChoices['both'])

        if self.DontSetKeyboard.GetValue() or self.AutoSetKeyboard.GetValue():
            self.KeyboardModelLabel.Enable(False)
            self.KeyboardLayoutLabel.Enable(False)
            self.KeyboardVariantLabel.Enable(False)
            self.KeyboardModel.Enable(False)
            self.KeyboardLayout.Enable(False)
            self.KeyboardVariant.Enable(False)
        else:
            self.KeyboardLayoutLabel.Enable(True)
            self.KeyboardModelLabel.Enable(True)
            self.KeyboardVariantLabel.Enable(True)
            self.KeyboardLayout.Enable(True)
            self.KeyboardModel.Enable(True)
            self.KeyboardVariant.Enable(True)

        if _command != 'SHADOW':
            self.ClientSidePrinting.SetValue(self.profile_config['print'])
        else:
            self.ClientSidePrinting.SetValue(False)
            self.ClientSidePrinting.Enable(False)
            self.staticbox_Printing.Enable(False)

        if _command == 'RDP':
            if self.profile_config['directrdp']:
                self.UseSSHProxy.SetValue(False)
                self._toggle_SSHProxy()
                self.enable_DirectRDP()
                self._toggle_SetKeyboard()
                self.PulseAudio.SetValue(True)
                self._toggle_DefaultSoundPort()
                self.SSHPort.SetValue(self.profile_config['rdpport'])
                self.SSHAutoLogin.SetValue(False)
                if PARAMIKO_FEATURE['forward-ssh-agent']:
                    self.SSHForwardAuthAgent.SetValue(False)
                self.RDPOptions.SetValue(self.profile_config['directrdpsettings'])
                self.RDPServerLabel.Enable(True)
                self.RDPServer.Enable(False)
                self.RDPOptionsLabel.Enable(True)
                self.RDPOptions.Enable(True)
                self.UsePublishedApplications.SetValue(False)
                self.UsePublishedApplications.Enable(False)
                self.RootlessSession.SetValue(False)
                self.RootlessSession.Enable(False)
            else:
                self.disable_DirectRDP()
                self._toggle_SetKeyboard()
                self._toggle_SSHProxy()
                self.RDPServerLabel.Enable(True)
                self.RDPServer.Enable(True)
                self.RDPOptionsLabel.Enable(True)
                self.RDPOptions.Enable(True)
                self.UsePublishedApplications.SetValue(False)
                self.UsePublishedApplications.Enable(False)
                self.RootlessSession.SetValue(False)
                self.RootlessSession.Enable(False)
        else:
            self.disable_DirectRDP()
            self._toggle_SetKeyboard()
            self._toggle_SSHProxy()
            self.RDPServerLabel.Enable(False)
            self.RDPServer.Enable(False)
            self.RDPOptionsLabel.Enable(False)
            self.RDPOptions.Enable(False)

        if _command != 'SHADOW':
            self.EnableSound.SetValue(self.profile_config['sound'])
            self.DefaultSoundPort.SetValue(self.profile_config['defsndport'])
            self.SoundPort.SetValue(self.profile_config['sndport'])
            if self.EnableSound.GetValue():
                self.PulseAudio.Enable(True)
                self.Esd.Enable(True)
                self.DefaultSoundPort.Enable(True)
                self._toggle_DefaultSoundPort()
        else:
            self.EnableSound.SetValue(False)
            self.EnableSound.Enable(False)
            self.PulseAudio.Enable(False)
            self.Arts.Enable(False)
            self.Esd.Enable(False)
            self.DefaultSoundPort.Enable(False)
            self.SoundPortLabel.Enable(False)
            self.SoundPort.Enable(False)
            self.staticbox_Sound.Enable(False)

        self.XDMCPServer.SetValue(self.profile_config['xdmcpserver'])

        self.DisplayTypeFullscreen.SetValue(self.profile_config['fullscreen'] and not self.profile_config['maxdim'])
        self.DisplayTypeMaximize.SetValue(self.profile_config['maxdim'])
        self.DisplayTypeCustom.SetValue(not (self.profile_config['fullscreen'] or self.profile_config['maxdim']))
        self.ScreenWidth.SetValue(self.profile_config['width'])
        self.ScreenHeight.SetValue(self.profile_config['height'])

        self._toggle_DisplayProperties()

        self.SetDisplayDPI.SetValue(self.profile_config['setdpi'])
        self.DisplayDPI.SetValue(self.profile_config['dpi'])
        if not self.profile_config['setdpi']:
            self.DisplayDPI.Enable(False)
        else:
            self.DisplayDPI.Enable(True)

        if _command != 'SHADOW':
            self.UseLocalFolderSharing.SetValue(self.profile_config['useexports'])
        else:
            self.UseLocalFolderSharing.SetValue(False)
            self.UseLocalFolderSharing.Enable(False)
            self.staticbox_FolderSharing.Enable(False)

        self.RestoreSharedLocalFolders.SetValue(self.profile_config['restoreexports'])
        self._toggle_localFolderSharing()
        self.SharedFoldersList.DeleteAllItems()

        # until pyhoca-gui 0.1.0.8 we used a wrong format for the export field in session profiles
        # the correct export field format is: 
        #
        #   export = "{string(path_1)}:{boolint(autoconnect_1);...;string(path_n)}:{boolint(autoconnect_n)};"

        # rewrite path separator from "," to ";" to correct pyhoca-gui (<0.1.0.9)
        #if ',' in self.profile_config['export']:
        #    self.profile_config['export'] = self.profile_config['export'].replace(',', ';')

        # strip off whitespaces and ";" from beginning and end of string
        _shared_folders = self.profile_config['export'].keys()

        for _shared_folder_path in _shared_folders:

            if self.profile_config['export'][_shared_folder_path]:
                _shared_folder_autoconnect = _("automatically")
            else:
                _shared_folder_autoconnect = _("manually")

            if self.SharedFoldersList.FindItem(0, _shared_folder_path) == -1:

                idx = self.SharedFoldersList.InsertStringItem(0, _shared_folder_path)
                self.SharedFoldersList.SetStringItem(idx, 1, _shared_folder_autoconnect)
                if self.profile_config['export'][_shared_folder_path]:
                    self.SharedFoldersList.CheckItem(idx)

        self.AddSharedFolderPathButton.Enable(False)
        self.DeleteSharedFolderPathButton.Enable(False)

        self.UseEncodingConverter.SetValue(self.profile_config['useiconv'])
        self.ClientEncoding.SetValue(self.profile_config['iconvfrom'])
        self.ServerEncoding.SetValue(self.profile_config['iconvto'])
        self._toggle_useEncodingConverter()

        if _command != 'SHADOW':
            self.UseFileMIMEbox.SetValue(self.profile_config['usemimebox'])
        else:
            self.UseFileMIMEbox.SetValue(False)
            self.UseFileMIMEbox.Enable(False)
            self.staticbox_FileMIMEbox.Enable(False)

        self.FileMIMEboxExtensions.SetValue(self.profile_config['mimeboxextensions'])
        if self.profile_config['mimeboxaction'] in self.mimeboxactionChoices.keys():
            self.FileMIMEboxAction.SetValue(self.mimeboxactionChoices[self.profile_config['mimeboxaction']])
        else:
            self.FileMIMEboxAction.SetValue(self.mimeboxactionChoices['OPEN'])
        self._toggle_useFileMIMEbox()

        self.disable_EditConnected_options()

        self._last_session_type = [ i for i in self.sessionChoices.keys() if self.sessionChoices[i] == self.SessionType.GetValue() ][0]

    def _toggle_DisplayProperties(self):
        """\
        Toggle display properties, depend on activation/deactivation of rootless session mode.

        @param event: event
        @type event: C{obj}

        """
        if not self.RootlessSession.GetValue():
            self.DisplayTypeFullscreen.Enable(True)
            self.DisplayTypeMaximize.Enable(True)
            self.DisplayTypeCustom.Enable(True)
            if self.DisplayTypeFullscreen.GetValue() or self.DisplayTypeMaximize.GetValue():
                self.ScreenWidth.Enable(False)
                self.ScreenHeightLabel.Enable(False)
                self.ScreenHeight.Enable(False)
            else:
                self.ScreenWidth.Enable(True)
                self.ScreenHeightLabel.Enable(True)
                self.ScreenHeight.Enable(True)

            self.SetSessionWindowTitle.Enable(True)
            self.SetSessionWindowTitle.SetValue(self.profile_config_bak['setsessiontitle'])
            self.CustomSessionWindowTitle.SetValue(self.profile_config_bak['sessiontitle'])

            if not self.profile_config['setsessiontitle']:
                self.CustomSessionWindowTitleLabel.Enable(False)
                self.CustomSessionWindowTitle.Enable(False)
                self.UseDefaultSessionWindowTitle.Enable(False)
            else:
                if self.profile_config['sessiontitle']:
                    self.UseDefaultSessionWindowTitle.SetValue(False)
                else:
                    self.UseDefaultSessionWindowTitle.SetValue(True)
                    self.CustomSessionWindowTitleLabel.Enable(False)
                    self.CustomSessionWindowTitle.Enable(False)

        else:
            self.DisplayTypeFullscreen.Enable(False)
            self.DisplayTypeMaximize.Enable(False)
            self.DisplayTypeCustom.Enable(False)
            self.ScreenWidth.Enable(False)
            self.ScreenHeightLabel.Enable(False)
            self.ScreenHeight.Enable(False)

            self.SetSessionWindowTitle.Enable(False)
            self.SetSessionWindowTitle.SetValue(False)
            self.CustomSessionWindowTitleLabel.Enable(False)
            self.CustomSessionWindowTitle.Enable(False)
            self.UseDefaultSessionWindowTitle.Enable(False)
            self.profile_config_bak['setsessiontitle'] = self.SetSessionWindowTitle.GetValue()
            if self.UseDefaultSessionWindowTitle.GetValue():
                self.profile_config_bak['sessiontitle'] = ''
            else:
                self.profile_config_bak['sessiontitle'] = self.CustomSessionWindowTitle.GetValue()
            self.SetSessionWindowTitle.SetValue(False)
            self.UseDefaultSessionWindowTitle.SetValue(False)
            self.CustomSessionWindowTitle.SetValue("")

    def disable_EditConnected_options(self):
        """\
        If C{action} in the constructor has been set to C{EDIT_CONNECTED} this
        method will disable several profile manager widgets.

        """
        # disable widgets when editing connected sessions
        if self.action == 'EDIT_CONNECTED':

            self.staticbox_Profile.Enable(False)
            self.ProfileNameLabel.Enable(False)
            self.ProfileName.Enable(False)
            self.HostLabel.Enable(False)
            self.Host.Enable(False)
            self.UserNameLabel.Enable(False)
            self.UserName.Enable(False)
            self.staticbox_Server.Enable(False)
            self.SSHPortLabel.Enable(False)
            self.SSHPort.Enable(False)
            self.SSHKeyFileLabel.Enable(False)
            self.SSHKeyFile.Enable(False)
            self.UniqueHostKeyAliases.Enable(False)
            self.SSHAutoLogin.Enable(False)
            if PARAMIKO_FEATURE['forward-ssh-agent']:
                self.SSHForwardAuthAgent.Enable(False)
            self.UseSSHProxy.Enable(False)
            self.staticbox_Proxy.Enable(False)
            self.SSHProxyUserLabel.Enable(False)
            self.SSHProxyUser.Enable(False)
            self.SSHProxySameUser.Enable(False)
            self.SSHProxySamePassword.Enable(False)
            self.SSHProxyKeyFileLabel.Enable(False)
            self.SSHProxyKeyFile.Enable(False)
            self.SSHProxyKeyFileBrowseButton.Enable(False)
            self.SSHProxyHostLabel.Enable(False)
            self.SSHProxyHost.Enable(False)
            self.SSHProxyPortLabel.Enable(False)
            self.SSHProxyPort.Enable(False)
            self.SSHProxyAutoLogin.Enable(False)


    def __update_from_screen(self):
        """\
        Update session profile configuration from the widget fields and their values.

        """
        self.profile_config['name'] = self.ProfileName.GetValue()
        self.profile_config['setsessiontitle'] = self.SetSessionWindowTitle.GetValue()
        _session_type = [ s for s in self.sessionChoices.keys() if self.sessionChoices[s] == self.SessionType.GetValue() ][0]
        if self.UseDefaultSessionWindowTitle.GetValue():
            self.profile_config['sessiontitle'] = ''
        else:
            self.profile_config['sessiontitle'] = self.CustomSessionWindowTitle.GetValue()
        self.profile_config['autostart'] = self.AutoStartSession.GetValue()
        self.profile_config['autoconnect'] = self.AutoConnectSessionProfile.GetValue()
        self.profile_config['autologin'] = self.SSHAutoLogin.GetValue()
        if PARAMIKO_FEATURE['forward-ssh-agent']:
            self.profile_config['forwardsshagent'] = self.SSHForwardAuthAgent.GetValue()
        else:
            self.profile_config['forwardsshagent'] = False
        self.profile_config['published'] = self.UsePublishedApplications.GetValue()
        if not self.default_icon:
            _icon = self.IconPath
            if _icon.startswith(os.environ['HOME']):
                _icon = _icon.replace(os.environ['HOME'], "~", 1)
            self.profile_config['icon'] = _icon
        else:
            self.profile_config['icon'] = ':icons/128x128/x2gosession.png'
        self.profile_config['user'] = self.UserName.GetValue()
        self.profile_config['key'] = self.SSHKeyFile.GetValue()
        _hosts = self.Host.GetValue()
        self.profile_config['host'] = _hosts.split(',')
        self.profile_config['usesshproxy'] = self.UseSSHProxy.GetValue()
        if _session_type != 'DirectRDP':
            self.profile_config['sshport'] = self.SSHPort.GetValue()
        self.profile_config['sshproxysameuser'] = self.SSHProxySameUser.GetValue()
        self.profile_config['sshproxysamepass'] = self.SSHProxySamePassword.GetValue()

        self.profile_config['sshproxyhost'] = self.SSHProxyHost.GetValue()
        self.profile_config['sshproxyport'] = self.SSHProxyPort.GetValue()
        self.profile_config['sshproxyautologin'] = self.SSHProxyAutoLogin.GetValue()
        self.profile_config['uniquehostkeyaliases'] = self.UniqueHostKeyAliases.GetValue()
        if self.profile_config['sshproxysameuser']:
            self.profile_config['sshproxyuser'] = ''
        else:
            self.profile_config['sshproxyuser'] = self.SSHProxyUser.GetValue()
        if self.profile_config['sshproxysamepass']:
            self.profile_config['sshproxykeyfile'] = ''
        else:
            self.profile_config['sshproxykeyfile'] = self.SSHProxyKeyFile.GetValue()

        self.profile_config['applications'] = self.applicationChoices.keys()
        self.profile_config['directrdp'] = False
        if _session_type == 'APPLICATION':
            _command = [ a for a in self.applicationChoices.keys() if self.applicationChoices[a] == self.Application.GetValue() ][0]
            self.profile_config['rootless'] = True
        elif _session_type == 'CUSTOM':
            _command = self.Command.GetValue()
            self.profile_config['rootless'] = self.RootlessSession.GetValue()
        elif _session_type == 'RDP':
            _command = _session_type
            self.profile_config['rootless'] = False
            self.profile_config['rdpserver'] = self.RDPServer.GetValue()
            self.profile_config['rdpoptions'] = self.RDPOptions.GetValue()
        elif _session_type == 'DirectRDP':
            _command = 'RDP'
            self.profile_config['usesshproxy'] = False
            self.profile_config['autologin'] = False
            self.profile_config['rootless'] = False
            self.profile_config['directrdp'] = True
            self.profile_config['directrdpsettings'] = self.RDPOptions.GetValue()
            self.profile_config['rdpport'] = self.SSHPort.GetValue()
            self.profile_config['rdpclient'] = [ rc for rc in self.rdpclientChoices.keys() if self.rdpclientChoices[rc] == self.Application.GetValue() ][0]
        elif _session_type == 'PUBLISHEDAPPLICATIONS':
            _command = ""
            self.profile_config['rootless'] = True
        else:
            _command = _session_type
            self.profile_config['rootless'] = False
        self.profile_config['command'] = _command
        self.profile_config['xdmcpserver'] = self.XDMCPServer.GetValue()

        _link_idx = self.LinkSpeed.GetValue()
        self.profile_config['speed'] = _link_idx

        self.profile_config['pack'] = self.Compression.GetValue().rstrip('-%')
        if '%s-%%' % self.profile_config['pack'] in self._compressions:
            self.profile_config['quality'] = self.ImageQuality.GetValue()
        else:
            self.profile_config['quality'] = 0
        self.profile_config['fullscreen'] = self.DisplayTypeFullscreen.GetValue()
        self.profile_config['maxdim'] = self.DisplayTypeMaximize.GetValue()
        self.profile_config['width'] = self.ScreenWidth.GetValue()
        self.profile_config['height'] = self.ScreenHeight.GetValue()

        self.profile_config['setdpi'] = self.SetDisplayDPI.GetValue()
        self.profile_config['dpi'] = self.DisplayDPI.GetValue()

        self.profile_config['clipboard'] = [ m for m in self.clipboardModeChoices.keys() if self.clipboardModeChoices[m] == self.ClipboardMode.GetValue() ][0]

        self.profile_config['usekbd'] = self.CustomSetKeyboard.GetValue() or self.AutoSetKeyboard.GetValue()
        self.profile_config['type'] = self.AutoSetKeyboard.GetValue() and "auto" or self.KeyboardModel.GetValue()
        self.profile_config['layout'] = self.AutoSetKeyboard.GetValue() and "null" or self.KeyboardLayout.GetValue()
        self.profile_config['variant'] = self.AutoSetKeyboard.GetValue() and "null" or self.KeyboardVariant.GetValue()
        if self.profile_config['layout'] == "null": self.profile_config['layout'] = ""
        if self.profile_config['variant'] == "null": self.profile_config['variant'] = ""

        self.profile_config['sound'] = self.EnableSound.GetValue()
        self.profile_config['defsndport'] = self.DefaultSoundPort.GetValue()
        self.profile_config['sndport'] = self.SoundPort.GetValue()

        self.profile_config['soundsystem'] = self._get_SoundSystem()

        self.profile_config['print'] = self.ClientSidePrinting.GetValue()

        self.profile_config['useexports'] = self.UseLocalFolderSharing.GetValue()
        self.profile_config['restoreexports'] = self.RestoreSharedLocalFolders.GetValue()
        _shared_folders = {}
        _item_id = self.SharedFoldersList.GetTopItem()
        while _item_id != -1 and self.SharedFoldersList.ItemCount > 0:
            _item = self.SharedFoldersList.GetItem(_item_id)

            if self.SharedFoldersList.IsChecked(_item_id):
                _auto_connect = 1
            else:
                _auto_connect = 0

            _shared_folders.update({ _item.GetText().strip(): bool(_auto_connect) })
            _item_id = self.SharedFoldersList.GetNextItem(_item_id)

        if _shared_folders:
            self.profile_config['export'] = '"' + ';'.join([ '%s:%s' % (_sf,int(_shared_folders[_sf])) for _sf in _shared_folders.keys() ]) + ';"'
        else:
            self.profile_config['export'] = ''
        self.profile_config['useiconv'] = self.UseEncodingConverter.GetValue()
        self.profile_config['iconvfrom'] = self.ClientEncoding.GetValue()
        self.profile_config['iconvto'] = self.ServerEncoding.GetValue()

        self.profile_config['usemimebox'] = self.UseFileMIMEbox.GetValue()
        _extensions = self.FileMIMEboxExtensions.GetValue()
        _extensions = _extensions.replace(' ', ',').replace(';', ',')
        _normalized_exts = []
        for _ext in _extensions.split(','):
            _ext = _ext.upper()
            _ext = _ext.lstrip().lstrip('.').rstrip()
            if _ext:
                _normalized_exts.append(_ext)
        self.profile_config['mimeboxextensions'] = ','.join(_normalized_exts)
        try:
            _mimebox_action = [ a for a in self.mimeboxactionChoices.keys() if self.mimeboxactionChoices[a] == self.FileMIMEboxAction.GetValue() ][0]
        except IndexError:
            _mimebox_action = 'OPEN'
        self.profile_config['mimeboxaction'] = _mimebox_action

    def _get_SoundSystem(self):
        if self.PulseAudio.GetValue():
            return 'pulse'
        elif self.Arts.GetValue():
            return 'arts'
        elif self.Esd.GetValue():
            return 'esd'

    def _set_SoundSystem(self, sound_system='pulse'):
        self.PulseAudio.SetValue(False)
        self.Arts.SetValue(False)
        self.Esd.SetValue(False)
        if self.profile_config['soundsystem'] == 'pulse':
            self.PulseAudio.SetValue(True)
        elif self.profile_config['soundsystem'] == 'arts':
            self.Arts.SetValue(True)
        elif self.profile_config['soundsystem'] == 'esd':
            self.Esd.SetValue(True)

    def OnIconChange(self, event):
        """\
        Gets called on profile icon change requests.

        @param event: event
        @type event: C{obj}

        """
        iconsdir = self._icons_location
        if not os.path.exists(iconsdir):
            iconsdir = os.getcwd()
        wildcard = _(u"Icon Files (*.png)|*.png|" \
                     u"All files (*.*)|*")
        dlg = wx.FileDialog(
            self, message=_(u"Choose an icon for this session profile"), defaultDir=iconsdir,
            defaultFile="", wildcard=wildcard, style=wx.FD_OPEN | wx.FD_CHANGE_DIR )
        # Show the dialog and retrieve the user response. If it is the OK response,
        # process the data.
        if dlg.ShowModal() == wx.ID_OK:
            # This returns a Python list of files that were selected.
            path_to_icon = dlg.GetPath()
            self.IconButton.SetBitmapLabel(wx.Bitmap(path_to_icon, wx.BITMAP_TYPE_ANY))
            self.IconPath = path_to_icon
            self.default_icon = False

    def OnSetSessionWindowTitle(self, event):
        """\
        Gets called if the change-session-window-title checkbox gets marked.

        @param event: event
        @type event: C{obj}

        """
        if self.SetSessionWindowTitle.GetValue():
            self.UseDefaultSessionWindowTitle.Enable(True)
            if not self.UseDefaultSessionWindowTitle.GetValue():
                self.CustomSessionWindowTitleLabel.Enable(True)
                self.CustomSessionWindowTitle.Enable(True)
        else:
            self.UseDefaultSessionWindowTitle.Enable(False)
            self.CustomSessionWindowTitleLabel.Enable(False)
            self.CustomSessionWindowTitle.Enable(False)

    def OnUseDefaultSessionWindowTitle(self, event):
        """\
        Gets called if the use-default-session-window-title checkbox gets marked.

        @param event: event
        @type event: C{obj}

        """
        if self.UseDefaultSessionWindowTitle.GetValue():
            self.CustomSessionWindowTitleLabel.Enable(False)
            self.CustomSessionWindowTitle.Enable(False)
        else:
            self.CustomSessionWindowTitleLabel.Enable(True)
            self.CustomSessionWindowTitle.Enable(True)

    def enable_DirectRDP(self):
        """\
        Gets called if the use-direct-RDP checkbox gets marked.

        @param event: event
        @type event: C{obj}

        """
        self.HostLabel.Enable(True)
        self.Host.Enable(True)
        self.SSHPortLabel.Enable(True)
        self.SSHPort.Enable(True)
        self.SSHPort.SetValue(self.profile_config_bak['rdpport'])
        self.SSHKeyFileLabel.Enable(False)
        self.SSHKeyFile.Enable(False)
        self.SSHKeyFileBrowseButton.Enable(False)
        self.SSHAutoLogin.Enable(False)
        if PARAMIKO_FEATURE['forward-ssh-agent']:
            self.SSHForwardAuthAgent.Enable(False)
        self.UniqueHostKeyAliases.Enable(False)
        self.UseSSHProxy.Enable(False)
        self.staticbox_LinkSpeed.Enable(False)
        self.staticbox_Proxy.Enable(False)
        self.SSHProxyUserLabel.Enable(False)
        self.SSHProxyUser.Enable(False)
        self.SSHProxySameUser.Enable(False)
        self.SSHProxySamePassword.Enable(False)
        self.SSHProxyKeyFileLabel.Enable(False)
        self.SSHProxyKeyFile.Enable(False)
        self.SSHProxyKeyFileBrowseButton.Enable(False)
        self.SSHProxyHostLabel.Enable(False)
        self.SSHProxyHost.Enable(False)
        self.SSHProxyPortLabel.Enable(False)
        self.SSHProxyPort.Enable(False)
        self.SSHProxyAutoLogin.Enable(False)
        self.LinkSpeed.Enable(False)
        self.ModemLabel.Enable(False)
        self.ISDNLabel.Enable(False)
        self.ADSLLabel.Enable(False)
        self.WANLabel.Enable(False)
        self.LANLabel.Enable(False)
        self.staticbox_Compression.Enable(False)
        self.CompressionLabel.Enable(False)
        self.Compression.Enable(False)
        self.ImageQualityLabel.Enable(False)
        self.ImageQuality.Enable(False)
        self.staticbox_Keyboard.Enable(False)
        self.DontSetKeyboard.Enable(False)
        self.AutoSetKeyboard.Enable(False)
        self.CustomSetKeyboard.Enable(False)
        self.CustomSetKeyboard.SetValue(True)
        self.DefaultSoundPort.Enable(False)
        self.SoundPortLabel.Enable(False)
        self.SoundPort.Enable(False)
        self.Esd.Enable(False)
        if self.session_profiles.is_mutable(self.profile_id) or self.action.startswith('ADD'):
            self.tab_SharedResources.Enable(True)
        self.RDPServer.Enable(False)
        _hosts = self.Host.GetValue()
        # only one host address supported
        self.RDPServer.SetValue(_hosts.split(',')[0])
        self.RDPOptions.SetValue(self.profile_config_bak['directrdpsettings'])
        if self.Application.GetValue() in self.applicationChoices.keys():
            self._last_application = self.Application.GetValue()
        self.Application.SetItems(self.rdpclientChoices.values())
        self.Application.SetValue(self._last_rdpclient)
        self.Application.Enable(True)

    def disable_DirectRDP(self):
        """\
        Gets called if the use-direct-RDP checkbox gets unmarked.

        @param event: event
        @type event: C{obj}

        """
        self.HostLabel.Enable(True)
        self.Host.Enable(True)
        self.SSHPortLabel.Enable(True)
        self.SSHPort.Enable(True)
        self.SSHPort.SetValue(self.profile_config_bak['sshport'])
        self.SSHAutoLogin.Enable(True)
        if PARAMIKO_FEATURE['forward-ssh-agent']:
            self.SSHForwardAuthAgent.Enable(True)
            self.SSHForwardAuthAgent.SetValue(self.profile_config_bak['forwardsshagent'])
        self.SSHAutoLogin.SetValue(self.profile_config_bak['autologin'])
        if not self.SSHAutoLogin.GetValue():
            self.SSHKeyFileLabel.Enable(True)
            self.SSHKeyFile.Enable(True)
            self.SSHKeyFileBrowseButton.Enable(True)
        self.UniqueHostKeyAliases.Enable(True)
        self.UseSSHProxy.Enable(True)
        self.staticbox_Proxy.Enable(True)
        self.staticbox_LinkSpeed.Enable(True)
        self.LinkSpeed.Enable(True)
        self.ModemLabel.Enable(True)
        self.ISDNLabel.Enable(True)
        self.ADSLLabel.Enable(True)
        self.WANLabel.Enable(True)
        self.LANLabel.Enable(True)
        self.staticbox_Compression.Enable(True)
        self.CompressionLabel.Enable(True)
        self.Compression.Enable(True)
        self.ImageQualityLabel.Enable(True)
        self.ImageQuality.Enable(True)
        self.staticbox_Keyboard.Enable(True)
        self.DontSetKeyboard.Enable(True)
        self.AutoSetKeyboard.Enable(True)
        self.CustomSetKeyboard.Enable(True)
        self.EnableSound.Enable(True)
        if self.EnableSound.GetValue():
            self.DefaultSoundPort.Enable(True)
            self.DefaultSoundPort.SetValue(True)
            self.Esd.Enable(True)
        if self.session_profiles.is_mutable(self.profile_id) or self.action.startswith('ADD'):
            self.tab_SharedResources.Enable(True)
        self.RDPServer.SetValue(self.profile_config_bak['rdpserver'])
        self.RDPOptions.SetValue(self.profile_config_bak['rdpoptions'])
        if self.Application.GetValue() in self.rdpclientChoices.keys():
            self._last_rdpclient = self.Application.GetValue()
        self.Application.SetItems(self.applicationChoices.values())
        self.Application.SetValue(self._last_application)

    def OnSessionTypeSelected(self, event):
        """\
        Gets called if another session type gets selected.

        @param event: event
        @type event: C{obj}

        """
        _session_type = [ i for i in self.sessionChoices.keys() if self.sessionChoices[i] == self.SessionType.GetValue() ][0]
        if self._last_session_type == 'SHADOW':

            self.EnableSound.SetValue(self.profile_config_bak['sound'])
            self.RootlessSession.SetValue(self.profile_config_bak['rootless'])
            self.UseLocalFolderSharing.SetValue(self.profile_config_bak['useexports'])
            self.ClientSidePrinting.SetValue(self.profile_config_bak['print'])
            self.UseFileMIMEbox.SetValue(self.profile_config_bak['usemimebox'])
            self.AutoStartSession.SetValue(self.profile_config_bak['autostart'])

            self.RootlessSession.Enable(True)

            if self.EnableSound.GetValue():
                self.PulseAudio.Enable(True)
                self.Esd.Enable(True)
                self.DefaultSoundPort.Enable(True)
                self._toggle_DefaultSoundPort()
            else:
                self.PulseAudio.Enable(False)
                self.Esd.Enable(False)
                self.DefaultSoundPort.Enable(False)
                self.SoundPortLabel.Enable(False)
                self.SoundPort.Enable(False)

            self.staticbox_Sound.Enable(True)

            # no local folder sharing available
            self.staticbox_FolderSharing.Enable(True)
            self.UseLocalFolderSharing.Enable(True)
            self._toggle_localFolderSharing()

            # no printing available
            self.ClientSidePrinting.Enable(True)
            self.staticbox_Printing.Enable(True)

            # no file MIME box available
            self.UseFileMIMEbox.Enable(True)
            self.staticbox_FileMIMEbox.Enable(True)

        self.UsePublishedApplications.Enable(True)
        self.AutoStartSession.Enable(True)

        if _session_type in defaults.X2GO_DESKTOPSESSIONS.keys():
            self.RootlessSession.SetValue(False)
            self.RootlessSession.Enable(False)

        if _session_type == 'APPLICATION':
            self.ApplicationLabel.Enable(True)
            self.Application.Enable(True)
            self.UsePublishedApplications.SetValue(False)
            self.UsePublishedApplications.Enable(False)
            if not self.Application.GetValue():
                self.Application.SetValue(self.applicationChoices['TERMINAL'])
            self.RootlessSession.SetValue(True)
            self.RootlessSession.Enable(False)
        else:
            self.ApplicationLabel.Enable(False)
            self.Application.Enable(False)

        if _session_type == 'CUSTOM':
            self.CommandLabel.Enable(True)
            self.Command.Enable(True)
            self.UsePublishedApplications.SetValue(False)
            self.UsePublishedApplications.Enable(False)
            if not self.Command.GetValue():
                self.Command.SetValue('xterm')
                self.RootlessSession.SetValue(True)
            self.RootlessSession.Enable(True)
        else:
            self.CommandLabel.Enable(False)
            self.Command.Enable(False)

        if _session_type == 'XDMCP':
            self.XDMCPServerLabel.Enable(True)
            self.XDMCPServer.Enable(True)
            self.UsePublishedApplications.SetValue(False)
            self.UsePublishedApplications.Enable(False)
            self.RootlessSession.SetValue(False)
            self.RootlessSession.Enable(False)
        else:
            self.XDMCPServerLabel.Enable(False)
            self.XDMCPServer.Enable(False)

        if _session_type == 'DirectRDP':
            self.profile_config_bak['sshport'] = self.SSHPort.GetValue()
            self.profile_config_bak['rdpserver'] = self.RDPServer.GetValue()
            self.profile_config_bak['rdpoptions'] = self.RDPOptions.GetValue()
            self.profile_config_bak['soundsystem'] = self._get_SoundSystem()
            self.profile_config_bak['usesshproxy'] = self.UseSSHProxy.GetValue()
            self.profile_config_bak['autologin'] = self.SSHAutoLogin.GetValue()
            if PARAMIKO_FEATURE['forward-ssh-agent']:
                self.profile_config_bak['forwardsshagent'] = self.SSHForwardAuthAgent.GetValue()
                self.SSHForwardAuthAgent.SetValue(False)
            self.UseSSHProxy.SetValue(False)
            self.SSHAutoLogin.SetValue(False)
            self.PulseAudio.SetValue(True)
            self.Arts.SetValue(False)
            self.Esd.SetValue(False)
            self.DefaultSoundPort.SetValue(True)
            self._toggle_DefaultSoundPort()
            self.enable_DirectRDP()
            self._toggle_SetKeyboard()
            self.RDPServerLabel.Enable(True)
            self.RDPServer.Enable(False)
            self.RDPOptionsLabel.Enable(True)
            self.RDPOptions.Enable(True)
            self.UsePublishedApplications.SetValue(False)
            self.UsePublishedApplications.Enable(False)
            self.RootlessSession.SetValue(False)
            self.RootlessSession.Enable(False)
        elif _session_type == 'RDP':
            self.profile_config_bak['rdpport'] = self.SSHPort.GetValue()
            self.profile_config_bak['directrdpsettings'] = self.RDPOptions.GetValue()
            self.disable_DirectRDP()
            self._toggle_SetKeyboard()
            self.UseSSHProxy.SetValue(self.profile_config_bak['usesshproxy'])
            self._toggle_SSHProxy()
            self._set_SoundSystem(self.profile_config_bak['soundsystem'])
            self._toggle_DefaultSoundPort()
            self.SSHAutoLogin.SetValue(self.profile_config_bak['autologin'])
            if PARAMIKO_FEATURE['forward-ssh-agent']:
                self.SSHForwardAuthAgent.SetValue(self.profile_config_bak['forwardsshagent'])
            self.RDPServerLabel.Enable(True)
            self.RDPServer.Enable(True)
            self.RDPOptionsLabel.Enable(True)
            self.RDPOptions.Enable(True)
            self.UsePublishedApplications.SetValue(False)
            self.UsePublishedApplications.Enable(False)
            self.RootlessSession.SetValue(False)
            self.RootlessSession.Enable(False)
        else:
            self.profile_config_bak['rdpport'] = self.SSHPort.GetValue()
            self.profile_config_bak['directrdpsettings'] = self.RDPOptions.GetValue()
            if self.RDPServer.GetValue() != self.Host.GetValue().split(',')[0]:
                self.profile_config_bak['rdpserver'] = self.RDPServer.GetValue()
                self.profile_config_bak['rdpoptions'] = self.RDPOptions.GetValue()
            self.disable_DirectRDP()
            self._toggle_SetKeyboard()
            self.SSHAutoLogin.SetValue(self.profile_config_bak['autologin'])
            if PARAMIKO_FEATURE['forward-ssh-agent']:
                self.SSHForwardAuthAgent.SetValue(self.profile_config_bak['forwardsshagent'])
            self.UseSSHProxy.SetValue(self.profile_config_bak['usesshproxy'])
            self._toggle_SSHProxy()
            self._set_SoundSystem(self.profile_config_bak['soundsystem'])
            self._toggle_DefaultSoundPort()
            self.RDPServerLabel.Enable(False)
            self.RDPServer.Enable(False)
            self.RDPOptionsLabel.Enable(False)
            self.RDPOptions.Enable(False)

        if _session_type == 'PUBLISHEDAPPLICATIONS':
            self._last_pubapp_value = self.UsePublishedApplications.GetValue()
            self._last_auto_start_value = self.AutoStartSession.GetValue()
            self.UsePublishedApplications.SetValue(True)
            self.UsePublishedApplications.Enable(False)
            self.AutoStartSession.SetValue(True)
            self.AutoStartSession.Enable(False)
            self.Command.SetValue('')
            self.RootlessSession.SetValue(True)
            self.RootlessSession.Enable(False)
        else:
            if self._last_pubapp_value is not None:
                self.UsePublishedApplications.SetValue(self._last_pubapp_value)
                self._last_pubapp_value = None
            if self._last_auto_start_value is not None:
                self.AutoStartSession.SetValue(self._last_auto_start_value)
                self._last_auto_start_value = None

        if _session_type == 'SHADOW':

            self.profile_config_bak['autostart'] = self.AutoStartSession.GetValue()
            self.profile_config_bak['sound'] = self.EnableSound.GetValue()
            self.profile_config_bak['rootless'] = self.RootlessSession.GetValue()
            self.profile_config_bak['useexports'] = self.UseLocalFolderSharing.GetValue()
            self.profile_config_bak['print'] = self.ClientSidePrinting.GetValue()
            self.profile_config_bak['usemimebox'] = self.UseFileMIMEbox.GetValue()

            self.AutoStartSession.SetValue(False)
            self.AutoStartSession.Enable(False)

            # shadow sessions are always desktop sessions
            self.RootlessSession.SetValue(True)
            self.RootlessSession.Enable(False)

            # no sound available with SHADOW sessions
            self.EnableSound.SetValue(False)
            self.EnableSound.Enable(False)
            self.PulseAudio.Enable(False)
            self.Esd.Enable(False)
            self.DefaultSoundPort.Enable(False)
            self.SoundPortLabel.Enable(False)
            self.SoundPort.Enable(False)
            self.staticbox_Sound.Enable(False)

            # no local folder sharing available
            self.UseLocalFolderSharing.SetValue(False)
            self.UseLocalFolderSharing.Enable(False)
            self.staticbox_FolderSharing.Enable(False)
            self._toggle_localFolderSharing()

            # no printing available
            self.ClientSidePrinting.SetValue(False)
            self.ClientSidePrinting.Enable(False)
            self.staticbox_Printing.Enable(False)

            # no file MIME box available
            self.UseFileMIMEbox.SetValue(False)
            self.UseFileMIMEbox.Enable(False)
            self.staticbox_FileMIMEbox.Enable(False)
            self._toggle_useFileMIMEbox()

        self._toggle_DisplayProperties()
        self.disable_EditConnected_options()

        self._last_session_type = _session_type

    def OnCompressionSelected(self, event):
        """\
        Gets called if another compression method gets selected.

        @param event: event
        @type event: C{obj}

        """
        _pack = self.Compression.GetValue()
        if _pack.endswith('-%'):
            self.ImageQuality.Enable(True)
        else:
            self.ImageQuality.Enable(False)

    def OnUserNameKeyPressed(self, event):
        """\
        Gets called whenever something gets typed in the user name field.

        @param event: event
        @type event: C{obj}

        """
        if self.UseSSHProxy.GetValue() and self.SSHProxySameUser.GetValue():
            self.SSHProxyUser.SetValue(self.UserName.GetValue())

    def OnSSHKeyFileKeyPressed(self, event):
        """\
        Gets called whenever something gets typed in the SSH key file field.

        @param event: event
        @type event: C{obj}

        """
        if self.UseSSHProxy.GetValue() and self.SSHProxySamePassword.GetValue():
            self.SSHProxyKeyFile.SetValue(self.SSHKeyFile.GetValue())

    def OnHostKeyPressed(self, event):
        """\
        Gets called whenever something gets typed in the host name field.

        @param event: event
        @type event: C{obj}

        """
        if [ k for k in self.sessionChoices.keys() if self.sessionChoices[k] == self.SessionType.GetValue() ][0] == 'DirectRDP':
            self.RDPServer.SetValue(self.Host.GetValue().split(',')[0])

    def OnSSHKeyFileBrowse(self, event):
        """\
        Gets called if the user requests to browse for an SSH key file (for X2Go client/server connection).

        @param event: event
        @type event: C{obj}

        """
        sshdir = os.path.expanduser('~/.ssh')
        if not os.path.exists(sshdir):
            sshdir = os.getcwd()
        wildcard = _(u"All files (*.*)|*")
        dlg = wx.FileDialog(
            self, message=_(u"Choose a public SSH key"), defaultDir=sshdir,
            defaultFile="", wildcard=wildcard, style=wx.FD_OPEN | wx.FD_CHANGE_DIR )
        # Show the dialog and retrieve the user response. If it is the OK response,
        # process the data.
        if dlg.ShowModal() == wx.ID_OK:
            # This returns a Python list of files that were selected.
            path = dlg.GetPath()
            self.SSHKeyFile.SetValue(path)
            if self.SSHProxySamePassword.GetValue():
                self.SSHProxyKeyFile.SetValue(path)

    def OnSSHProxyKeyFileBrowse(self, event):
        """\
        Gets called if the user requests to browse for an SSH key file (for SSH proxy client/server connection).

        @param event: event
        @type event: C{obj}

        """
        sshdir = os.path.expanduser('~/.ssh')
        if not os.path.exists(sshdir):
            sshdir = os.getcwd()
        wildcard = "All files (*.*)|*"
        dlg = wx.FileDialog(
            self, message=_(u"Choose a public SSH key"), defaultDir=sshdir,
            defaultFile="", wildcard=wildcard, style=wx.FD_OPEN | wx.FD_CHANGE_DIR )
        # Show the dialog and retrieve the user response. If it is the OK response,
        # process the data.
        if dlg.ShowModal() == wx.ID_OK:
            # This returns a Python list of files that were selected.
            path = dlg.GetPath()
            self.SSHProxyKeyFile.SetValue(path)

    def OnSSHAutoLogin(self, event):
        """\
        Gets called if the ssh-proxy-auto-login checkbox gets marked.

        @param event: event
        @type event: C{obj}

        """
        if self.SSHAutoLogin.GetValue():
            self.SSHKeyFileLabel.Enable(False)
            self.SSHKeyFile.Enable(False)
            self.SSHKeyFileBrowseButton.Enable(False)
        else:
            self.SSHKeyFileLabel.Enable(True)
            self.SSHKeyFile.Enable(True)
            self.SSHKeyFileBrowseButton.Enable(True)

    def OnSSHProxyAutoLogin(self, event):
        """\
        Gets called if the ssh-proxy-auto-login checkbox gets marked.

        @param event: event
        @type event: C{obj}

        """
        if self.SSHProxyAutoLogin.GetValue():
            self.SSHProxyKeyFileLabel.Enable(False)
            self.SSHProxyKeyFile.Enable(False)
            self.SSHProxyKeyFileBrowseButton.Enable(False)
        else:
            self.SSHProxyKeyFileLabel.Enable(True)
            self.SSHProxyKeyFile.Enable(True)
            self.SSHProxyKeyFileBrowseButton.Enable(True)

    def OnUseSSHProxy(self, event):
        """\
        Gets called if the use-ssh-proxy checkbox gets marked.

        @param event: event
        @type event: C{obj}

        """
        if self.UseSSHProxy.GetValue():
            self.profile_config_bak['host'] = self.Host.GetValue().split(',')
            self.profile_config_bak['sshport'] = self.SSHPort.GetValue()
        self._toggle_SSHProxy()

    def OnSSHProxySameUser(self, event):
        """\
        Gets called if the use-same-user-for-proxy checkbox gets marked.

        @param event: event
        @type event: C{obj}

        """
        if self.SSHProxySameUser.GetValue():
            self.profile_config_bak['sshproxyuser'] = self.SSHProxyUser.GetValue()
        self._toggle_SSHProxy()

    def OnSSHProxySamePassword(self, event):
        """\
        Gets called if the use-same-user-authinfo checkbox gets marked.

        @param event: event
        @type event: C{obj}

        """
        if self.SSHProxySamePassword.GetValue():
            self.profile_config_bak['sshproxykeyfile'] = self.SSHProxyKeyFile.GetValue()
        self._toggle_SSHProxy()

    def _toggle_SSHProxy(self):
        """\
        Gets called if the use-ssh-proxy checkbox gets marked.

        @param event: event
        @type event: C{obj}

        """
        if self.UseSSHProxy.GetValue():
            self.staticbox_Proxy.Enable(True)
            self.SSHProxySameUser.Enable(True)
            self.SSHProxySamePassword.Enable(True)
            self.SSHProxyHostLabel.Enable(True)
            self.SSHProxyHost.Enable(True)
            self.SSHProxyPortLabel.Enable(True)
            self.SSHProxyPort.Enable(True)
            if self.SSHProxySameUser.GetValue():
                self.SSHProxyUser.SetValue(self.UserName.GetValue())
                self.SSHProxyUser.Enable(False)
            else:
                self.SSHProxyUser.SetValue(self.profile_config_bak['sshproxyuser'])
                self.SSHProxyUserLabel.Enable(True)
                self.SSHProxyUser.Enable(True)
            if self.SSHProxySamePassword.GetValue():
                self.SSHProxyKeyFile.SetValue(self.SSHKeyFile.GetValue())
            else:
                self.SSHProxyKeyFile.SetValue(self.profile_config_bak['sshproxykeyfile'])
            if self.SSHProxySamePassword.GetValue() or self.SSHProxyAutoLogin.GetValue():
                self.SSHProxyKeyFile.Enable(False)
                self.SSHProxyKeyFileBrowseButton.Enable(False)
            else:
                self.SSHProxyKeyFileLabel.Enable(True)
                self.SSHProxyKeyFile.Enable(True)
                self.SSHProxyKeyFileBrowseButton.Enable(True)
            if self.SSHProxyAutoLogin.GetValue():
                self.SSHProxyKeyFileLabel.Enable(False)
            self.SSHProxyAutoLogin.Enable(True)
        else:
            self.staticbox_Proxy.Enable(False)
            self.SSHProxySameUser.Enable(False)
            self.SSHProxySamePassword.Enable(False)
            self.SSHProxyHostLabel.Enable(False)
            self.SSHProxyHost.Enable(False)
            self.SSHProxyPortLabel.Enable(False)
            self.SSHProxyPort.Enable(False)
            self.SSHProxyUserLabel.Enable(False)
            self.SSHProxyUser.Enable(False)
            self.SSHProxyKeyFileLabel.Enable(False)
            self.SSHProxyKeyFile.Enable(False)
            self.SSHProxyKeyFileBrowseButton.Enable(False)
            self.SSHProxyAutoLogin.Enable(False)

    def OnSetKeyboard(self, event):
        """\
        Gets called whenever the either of the keyboard-settings radio buttons is selected.

        @param event: event
        @type event: C{obj}

        """
        self._toggle_SetKeyboard()

    def _toggle_SetKeyboard(self):
        """\
        Toggle keyboard settings, depends on activation/deactivation of custom keyboard settings.

        @param event: event
        @type event: C{obj}

        """
        if self.CustomSetKeyboard.GetValue():
            self.KeyboardModelLabel.Enable(True)
            self.KeyboardLayoutLabel.Enable(True)
            self.KeyboardVariantLabel.Enable(True)
            self.KeyboardLayout.Enable(True)
            self.KeyboardModel.Enable(True)
            self.KeyboardVariant.Enable(True)
        else:
            self.KeyboardModelLabel.Enable(False)
            self.KeyboardLayoutLabel.Enable(False)
            self.KeyboardVariantLabel.Enable(False)
            self.KeyboardLayout.Enable(False)
            self.KeyboardModel.Enable(False)
            self.KeyboardVariant.Enable(False)

    def OnSoundEnable(self, event):
        """\
        Gets called whenever the enable-sound checkbox gets marked.

        @param event: event
        @type event: C{obj}

        """
        _session_type = [ i for i in self.sessionChoices.keys() if self.sessionChoices[i] == self.SessionType.GetValue() ][0]
        if self.EnableSound.GetValue():
            self.PulseAudio.Enable(True)
            if _session_type != 'DirectRDP':
                self.Esd.Enable(True)
                self.DefaultSoundPort.Enable(True)
                if self.DefaultSoundPort.GetValue() is False:
                    self.SoundPortLabel.Enable(True)
                    self.SoundPort.Enable(True)
        else:
            self.PulseAudio.Enable(False)
            self.Esd.Enable(False)
            self.DefaultSoundPort.Enable(False)
            self.SoundPortLabel.Enable(False)
            self.SoundPort.Enable(False)

    def OnSetDisplayFullscreen(self, event):
        """\
        Gets called whenever the fullscreen-display radion button gets checked.

        @param event: event
        @type event: C{obj}

        """
        self.ScreenWidthLabel.Enable(False)
        self.ScreenWidth.Enable(False)
        self.ScreenHeightLabel.Enable(False)
        self.ScreenHeight.Enable(False)

    def OnSetDisplayMaximize(self, event):
        """\
        Gets called whenever the maximize-display radion button gets checked.

        @param event: event
        @type event: C{obj}

        """
        self.ScreenWidthLabel.Enable(False)
        self.ScreenWidth.Enable(False)
        self.ScreenHeightLabel.Enable(False)
        self.ScreenHeight.Enable(False)

    def OnSetDisplayCustom(self, event):
        """\
        Gets called whenever the custom-size-display radion button gets checked.

        @param event: event
        @type event: C{obj}

        """
        self.ScreenWidthLabel.Enable(True)
        self.ScreenWidth.Enable(True)
        self.ScreenHeightLabel.Enable(True)
        self.ScreenHeight.Enable(True)

    def OnSetDisplayDPI(self, event):
        """\
        Gets called whenever the set-dpi checkbox gets marked.

        @param event: event
        @type event: C{obj}

        """
        if self.SetDisplayDPI.GetValue():
            self.DisplayDPI.Enable(True)
        else:
            self.DisplayDPI.Enable(False)

    def OnPulseAudio(self, event):
        """\
        Gets called whenever the pulseaudio system is seleced.

        @param event: event
        @type event: C{obj}

        """
        if self.DefaultSoundPort.GetValue():
            self.SoundPort.SetValue(self.audioPorts['pulse'])

    def OnEsd(self, event):
        """\
        Gets called whenever the esound system is seleced.

        @param event: event
        @type event: C{obj}

        """
        if self.DefaultSoundPort.GetValue():
            self.SoundPort.SetValue(self.audioPorts['esd'])

    def OnDefaultSoundPort(self, event):
        """\
        Gets called if the user chooses to use the audio system's default audio port.

        @param event: event
        @type event: C{obj}

        """
        self._toggle_DefaultSoundPort()

    def _toggle_DefaultSoundPort(self):
        """\
        Gets called indirectly on activation/deactivation of the default-sound-port checkbox.

        @param event: event
        @type event: C{obj}

        """
        if not self.DefaultSoundPort.GetValue():
            self.SoundPortLabel.Enable(True)
            self.SoundPort.Enable(True)
        else:
            if self.PulseAudio.GetValue():
                self.SoundPort.SetValue(self.audioPorts['pulse'])
            if self.Esd.GetValue():
                self.SoundPort.SetValue(self.audioPorts['esd'])
            self.SoundPortLabel.Enable(False)
            self.SoundPort.Enable(False)

    def _toggle_localFolderSharing(self):
        """\
        Helper method for L{OnToggleLocalFolderSharing}.

        """
        if self.UseLocalFolderSharing.GetValue():
            self.RestoreSharedLocalFolders.Enable(True)
            self.SharedFolderPathLabel.Enable(True)
            self.SharedFolderPath.Enable(True)
            self.SharedFolderPathBrowseButton.Enable(True)
            self.SharedFoldersList.Enable(True)
            self.UseEncodingConverter.Enable(True)
            self._toggle_useEncodingConverter()
        else:
            self.RestoreSharedLocalFolders.Enable(False)
            self.AddSharedFolderPathButton.Enable(False)
            self.DeleteSharedFolderPathButton.Enable(False)
            self.SharedFolderPathLabel.Enable(False)
            self.SharedFolderPath.Enable(False)
            self.SharedFolderPathBrowseButton.Enable(False)
            self.SharedFoldersList.Enable(False)
            self.UseEncodingConverter.Enable(False)
            self.ClientEncodingLabel.Enable(False)
            self.ClientEncoding.Enable(False)
            self.ServerEncodingLabel.Enable(False)
            self.ServerEncoding.Enable(False)

    def OnToggleLocalFolderSharing(self, event):
        self._toggle_localFolderSharing()

    def OnSelectSharedFolderPath(self, event):
        """\
        Gets called whenever the uses evokes a file browser dialog that allows to choose a folder for sharing.

        @param event: event
        @type event: C{obj}

        """
        shared_folder = os.path.expanduser('~')
        if not os.path.exists(shared_folder):
            shared_folder = os.getcwd()
        dlg = wx.DirDialog(
            self, message=_(u"Choose a folder to share within a session"), style=1, defaultPath=shared_folder, )
        # Show the dialog and retrieve the user response. If it is the OK response,
        # process the data.
        if dlg.ShowModal() == wx.ID_OK:
            # This returns a Python list of files that were selected.
            self.SharedFolderPath.SetValue(dlg.GetPath())

    def OnSharedFolderListItemSelected(self, event):
        """\
        Gets called whenever a shared folder in the list of already configured locally shared folders is selected.

        @param event: event
        @type event: C{obj}

        """
        self.DeleteSharedFolderPathButton.Enable(True)

    def OnSharedFolderListItemDeselected(self, event):
        """\
        Gets called whenever a shared folder in the list of already configured locally shared folders is deselected.

        @param event: event
        @type event: C{obj}

        """
        self.DeleteSharedFolderPathButton.Enable(False)

    def OnSharedFolderPathKeyPressed(self, event):
        """\
        Gets called whenever something gets typed in the sharable folder path field.

        @param event: event
        @type event: C{obj}

        """
        self.AddSharedFolderPathButton.Enable(True)

    def OnAddSharedFolderPath(self, event):
        """\
        Gets called whenever the user requests to add a folder name to the list of locally shared folders.

        @param event: event
        @type event: C{obj}

        """
        _shared_folder_path = self.SharedFolderPath.GetValue()
        if _shared_folder_path and (self.SharedFoldersList.FindItem(0, _shared_folder_path) == -1):
            idx = self.SharedFoldersList.InsertStringItem(0, _shared_folder_path)
            self.SharedFoldersList.SetStringItem(idx, 1, _("automatically"))
            self.SharedFoldersList.CheckItem(idx)
            self.SharedFolderPath.SetValue('')
        self.AddSharedFolderPathButton.Enable(False)

    def OnDeleteSharedFolderPath(self, event):
        """\
        Gets called whenever the user requests to remove a folder name from the list of locally shared folders.

        @param event: event
        @type event: C{obj}

        """
        _item = self.SharedFoldersList.GetFocusedItem()
        self.SharedFoldersList.DeleteItem(_item)
        self.DeleteSharedFolderPathButton.Enable(False)

    def _toggle_useEncodingConverter(self):
        """\
        Helper method for L{OnToggleEncodingConverter}.

        """
        if self.UseEncodingConverter.GetValue():
            self.ClientEncodingLabel.Enable(True)
            self.ClientEncoding.Enable(True)
            self.ServerEncodingLabel.Enable(True)
            self.ServerEncoding.Enable(True)
        else:
            self.ClientEncodingLabel.Enable(False)
            self.ClientEncoding.Enable(False)
            self.ServerEncodingLabel.Enable(False)
            self.ServerEncoding.Enable(False)

    def OnToggleEncodingConverter(self, event):
        """\
        Gets called whenever the encoding conversion gets enabled/disabled.

        @param event: event
        @type event: C{obj}

        """
        self._toggle_useEncodingConverter()

    def _toggle_useFileMIMEbox(self):
        """\
        Helper method for L{OnToggleFileMIMEbox}.

        """
        if self.UseFileMIMEbox.GetValue():
            self.FileMIMEboxExtensionsLabel.Enable(True)
            self.FileMIMEboxExtensions.Enable(True)
            self.FileMIMEboxActionLabel.Enable(True)
            self.FileMIMEboxAction.Enable(True)
        else:
            self.FileMIMEboxExtensionsLabel.Enable(False)
            self.FileMIMEboxExtensions.Enable(False)
            self.FileMIMEboxActionLabel.Enable(False)
            self.FileMIMEboxAction.Enable(False)

    def OnToggleFileMIMEbox(self, event):
        """\
        Gets called whenever the user enables/disabled the MIME box feature.

        @param event: event
        @type event: C{obj}

        """
        self._toggle_useFileMIMEbox()

    def __validate(self):
        """\
        Validation of all widget fields, called when the user requests to save the session profile.

        @return: status of validation; C{True} for successfully validated, C{False} otherwise
        @rtype: C{bool}

        """
        validateOk = True
        if len(self.profile_config['name'].strip()) == 0:
            validateOk = False
            self._PyHocaGUI.notifier.send(title=_(u'Profile Manager'), text=_(u'Profile name is missing, profile unusable!!!'), icon='profile_error')
        elif self.profile_config['name'].strip() in self.session_profiles.profile_names and self.action == 'ADD':
            validateOk = False
            self._PyHocaGUI.notifier.send(title=_(u'Profile Manager'), text=_(u'Profile name %s already exists!!!') % self.profile_config['name'].strip(), icon='profile_error')
        elif self.profile_config['name'].strip() != self.profile_config_bak['name'] and self.profile_config['name'].strip() in self.session_profiles.profile_names:
            validateOk = False
            self._PyHocaGUI.notifier.send(title=_(u'Profile Manager'), text=_(u'Profile name %s already exists!!!') % self.profile_config['name'].strip(), icon='profile_error')
        return validateOk

    def OnApplyButton(self, event):
        """\
        Gets called if the users clicks on the ,,Apply'' button.

        @param event: event
        @type event: C{obj}

        """
        wx.BeginBusyCursor()
        self.__update_from_screen()
        if self.__validate():

            if self.profile_config != self.profile_config_orig:

                if self.action in ('ADD', 'COPY'):
                    self.profile_id = self.session_profiles.add_profile(**self.profile_config)
                else:
                    for k in self.profile_config.keys():
                        self.session_profiles.update_value(self.profile_id, k, self.profile_config[k])

                self.session_profiles.write_user_config = True
                self.session_profiles.write()
                self.profile_id = self.session_profiles.to_profile_id(self.profile_config['name'])

                if self.action == 'ADD':
                    self._PyHocaGUI.notifier.send(title=_(u'%s - profile added') % self.profile_config['name'],
                                                  text=_(u'A new session profile has been added.'),
                                                  icon='profile_add',
                                                 )
                elif self.action == 'EDIT':
                    self._PyHocaGUI.notifier.send(title=_(u'%s - modified') % self.profile_config['name'],
                                                  text=_(u'Changes to profile have been saved.'),
                                                  icon='profile_save',
                                                 )
                self._PyHocaGUI.register_available_server_sessions_by_profile_name(profile_name=self.profile_config['name'], re_register=True)

            try: wx.EndBusyCursor()
            except: pass

            self.config_saved = True
            self.profile_config_orig = copy.deepcopy(self.profile_config)
            self.profile_config_bak = copy.deepcopy(self.profile_config)
        else:
            try: wx.EndBusyCursor()
            except: pass
            self.config_saved = False

    def OnOKButton(self, event):
        """\
        Gets called if the users clicks on the ,,Save'' button.

        @param event: event
        @type event: C{obj}

        """
        self.OnApplyButton(event)
        if self.config_saved: self.Close()

    def OnCancel(self, event):
        """\
        Gets called if the users clicks on the ,,Cancel'' button.

        @param event: event
        @type event: C{obj}

        """
        self.Close()

    def OnDefault(self, event):
        """\
        Gets called if the users clicks on the ,,Defaults'' button.

        @param event: event
        @type event: C{obj}

        """
        self.profile_config = copy.deepcopy(self.profile_config_orig)
        self.__update_fields()

    def Close(self):
        """\
        Clean-up disabled profile_names when closing the profile manager dialog.

        """
        self._PyHocaGUI.gevent_sleep_when_idle = 0.25
        try:
            self._PyHocaGUI._temp_disabled_profile_names.remove(self.profile_name)
        except ValueError:
            pass
        wx.Dialog.Close(self)

    def Destroy(self):
        """\
        Tidy up some stuff in the main application instance before allowing desctruction of the
        profile manager window.

        """
        self._PyHocaGUI.gevent_sleep_when_idle = 0.25
        try:
            self._PyHocaGUI._sub_windows.remove(self)
        except ValueError:
            pass
        wx.Dialog.Destroy(self)
