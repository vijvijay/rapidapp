# -*- coding: utf-8 -*-

import os.path
import wx
import StringIO
import base64

import x2go.defaults
import x2go.x2go_exceptions

import basepath

class PyHocaGUI_Menu_TaskbarManageProfile(wx.Menu):
    """\
    Individual profile management submenu: copy, use as template or delete session profile.

    """
    def __init__(self, _PyHocaGUI, caller=None, profile_name=None):
        """\
        Individual profile management submenu (constructor).

        @param _PyHocaGUI: main application instance
        @type _PyHocaGUI: C{obj}
        @param caller: unused
        @type caller: C{None}
        @param profile_name: session profile name this submenu is for
        @type profile_name: C{str}

        """
        self._PyHocaGUI = _PyHocaGUI
        self._pyhoca_logger = self._PyHocaGUI._pyhoca_logger

        wx.Menu.__init__(self)

        ID_EDITPROFILE = wx.NewId()
        ID_COPYPROFILE = wx.NewId()
        ID_EXPORTPROFILE = wx.NewId()
        ID_DELETEPROFILE = wx.NewId()

        # preparing profile_name information for the main PyHocaGUI instance
        self._PyHocaGUI._eventid_profilenames_map[ID_EDITPROFILE] = \
            self._PyHocaGUI._eventid_profilenames_map[ID_COPYPROFILE] = \
            self._PyHocaGUI._eventid_profilenames_map[ID_EXPORTPROFILE] = \
            self._PyHocaGUI._eventid_profilenames_map[ID_DELETEPROFILE] = profile_name

        if self._PyHocaGUI.session_profiles.is_mutable(profile_name):
            self.Append(text=_(u"Edit Profile"), id=ID_EDITPROFILE)
        else:
            self.Append(text=_(u"View Profile"), id=ID_EDITPROFILE)
        self._PyHocaGUI.Bind(wx.EVT_MENU, self._PyHocaGUI.OnProfileEdit, id=ID_EDITPROFILE)

        if not self._PyHocaGUI.args.single_session_profile:

            self.AppendSeparator()

            if self._PyHocaGUI.session_profiles.is_mutable(profile_name):
                self.Append(text=_(u"Use as Template for New Profile"), id=ID_COPYPROFILE)
                self._PyHocaGUI.Bind(wx.EVT_MENU, self._PyHocaGUI.OnProfileCopy, id=ID_COPYPROFILE)
                self.AppendSeparator()

            self.Append(text=_(u"Export Profile"), id=ID_EXPORTPROFILE)
            self._PyHocaGUI.Bind(wx.EVT_MENU, self._PyHocaGUI.OnProfileExport, id=ID_EXPORTPROFILE)

            if self._PyHocaGUI.session_profiles.is_mutable(profile_name):
                self.Append(text=_(u"Delete Profile"), id=ID_DELETEPROFILE)
                self._PyHocaGUI.Bind(wx.EVT_MENU, self._PyHocaGUI.OnProfileDelete, id=ID_DELETEPROFILE)


class PyHocaGUI_Menu_TaskbarOptionsManager(wx.Menu):
    """\
    Right-click menu of the L{PyHocaGUI} systray icon.

    """
    def __init__(self, _PyHocaGUI, caller=None):
        """\
        Client and profile management menu of L{PyHocaGUI} (constructor).

        @param _PyHocaGUI: main application instance
        @type _PyHocaGUI: C{obj}
        @param caller: unused
        @type caller: C{None}

        """
        self._PyHocaGUI = _PyHocaGUI
        self._pyhoca_logger = self._PyHocaGUI._pyhoca_logger

        wx.Menu.__init__(self)

        # ID_ABOUT = wx.NewId()
        # ID_ABOUT_PYTHONX2GO = wx.NewId()
        # vgabt = wx.MenuItem(id=ID_ABOUT, text=_(u"About %s (%s)...") % (self._PyHocaGUI.appname, self._PyHocaGUI.version))
        # vgabt.SetBitmap(wx.Bitmap('%s/App-O-Cloud/16x16/system-search.png' % basepath.icons_basepath, wx.BITMAP_TYPE_ANY))
        # self.AppendItem(vgabt);
        # #self.Append(id=ID_ABOUT, text=_(u"About %s (%s)...") % (self._PyHocaGUI.appname, self._PyHocaGUI.version))
        # self.Append(id=ID_ABOUT_PYTHONX2GO, text=_(u"About %s (%s)...") % ("Python X2Go", x2go.__VERSION__))
        # self._PyHocaGUI.Bind(wx.EVT_MENU, self._PyHocaGUI.OnAbout, id=ID_ABOUT)
        # self._PyHocaGUI.Bind(wx.EVT_MENU, self._PyHocaGUI.OnAboutPythonX2Go, id=ID_ABOUT_PYTHONX2GO)

        # if not self._PyHocaGUI.restricted_trayicon:

            # self.AppendSeparator()

            # if not self._PyHocaGUI.args.single_session_profile:

                # ID_PROFILEMANAGER = wx.NewId()
                # _maintain_profiles_item = self.AppendMenu(id=ID_PROFILEMANAGER,
                                                          # text=_(u"Profile Manager"),
                                                          # submenu=PyHocaGUI_Menu_TaskbarProfileNames(self._PyHocaGUI,
                                                                                                     # caller=self,
                                                                                                     # filter_profiles=[],
                                                                                                     # disabled_profiles=self._PyHocaGUI.client_connected_profiles(return_profile_names=True) + self._PyHocaGUI._temp_disabled_profile_names,
                                                                                                     # submenu=PyHocaGUI_Menu_TaskbarManageProfile,
                                                                                                     # group_menus=True,
                                                                                                    # )
                                                         # )
                # if self._PyHocaGUI.profilemanager_disabled:
                    # _maintain_profiles_item.Enable(False)

                # self.AppendSeparator()

            # elif self._PyHocaGUI.session_profiles.has_profile_name(self._PyHocaGUI.args.session_profile):
                # ID_SINGLEPROFILEMANAGER = wx.NewId()
                # _maintain_profile_item = self.AppendMenu(id=ID_SINGLEPROFILEMANAGER,
                                                         # text=_(u'Manage Session Profile'),
                                                         # submenu=PyHocaGUI_Menu_TaskbarManageProfile(self._PyHocaGUI, caller=self, profile_name=self._PyHocaGUI.args.session_profile),
                                                        # )
                # if self._PyHocaGUI.args.session_profile in self._PyHocaGUI.client_connected_profiles(return_profile_names=True):
                    # _maintain_profile_item.Enable(False)
                # self.AppendSeparator()

        # if self._PyHocaGUI.with_brokerage and self._PyHocaGUI.session_profiles.is_broker_authenticated():
            # ID_BROKER_DISCONNECT = wx.NewId()
            # self.Append(id=ID_BROKER_DISCONNECT, text=_(u"Disconnect from session broker"))
            # self._PyHocaGUI.Bind(wx.EVT_MENU, self._PyHocaGUI.OnBrokerDisconnect, id=ID_BROKER_DISCONNECT)
            # self.AppendSeparator()

        # ID_PRINTINGPREFS = wx.NewId()
        # _printingprefs_item = self.Append(id=ID_PRINTINGPREFS, text=_(u"Printing Preferences"))
        # self._PyHocaGUI.Bind(wx.EVT_MENU, self._PyHocaGUI.OnPrintingPreferences, id=ID_PRINTINGPREFS)
        # if self._PyHocaGUI.printingprefs_disabled:
            # _printingprefs_item.Enable(False)

        # if not self._PyHocaGUI.restricted_trayicon:

            # ID_OPTIONS = wx.NewId()
            # _options_item = self.Append(id=ID_OPTIONS, text=_(u"Client Options"))
            # self._PyHocaGUI.Bind(wx.EVT_MENU, self._PyHocaGUI.OnOptions, id=ID_OPTIONS)
            # if self._PyHocaGUI.options_disabled:
                # _options_item.Enable(False)

        # self.AppendSeparator()

        #Apprime: Add ServerInfo menu item here with name "Connection Status" - later we'll add "account status" too
        ID_EXIT = wx.NewId()
        self.Append(id=ID_EXIT, text=_("E&xit"))
        self._PyHocaGUI.Bind(wx.EVT_MENU, self._PyHocaGUI.OnTaskbarExit, id=ID_EXIT)


class PyHocaGUI_Menu_TaskbarSessionActions(wx.Menu):
    """\
    Session action submenu for individual sessions: start, resume, suspend, terminate etc. sessions.

    """
    def __init__(self, _PyHocaGUI, caller=None, profile_name=None, session_name=None, session_info=None, status=None):
        """\
        Session action submenu (constructor).

        @param _PyHocaGUI: main application instance
        @type _PyHocaGUI: C{obj}
        @param caller: unused
        @type caller: C{None}
        @param profile_name: session profile name this submenu is for
        @type profile_name: C{str}
        @param session_name: X2Go session name this submenu is for
        @type session_name: C{str}
        @param session_info: session info object (C{X2GoServerSessionInfo*} from Python X2Go)
        @type session_info: C{obj}
        @param status: status of this session (R for running, S for suspended)
        @type status: C{str}

        """
        self._PyHocaGUI = _PyHocaGUI
        self._pyhoca_logger = self._PyHocaGUI._pyhoca_logger

        wx.Menu.__init__(self)

        ID_RAISESESSION = wx.NewId()
        ID_RENAMESESSION = wx.NewId()
        ID_TRANSFERSESSION = wx.NewId()
        ID_TRANSFERSESSION_DISABLED = wx.NewId()
        ID_RESUMESESSION = wx.NewId()
        ID_RESUMESESSION_DISABLED = wx.NewId()
        ID_REFRESHMENU = wx.NewId()
        ID_SUSPENDSESSION = wx.NewId()
        ID_TERMINATESESSION = wx.NewId()

        # preparing profile_name information for the main PyHocaGUI instance
        self._PyHocaGUI._eventid_profilenames_map[ID_RAISESESSION] = \
            self._PyHocaGUI._eventid_profilenames_map[ID_RENAMESESSION] = \
            self._PyHocaGUI._eventid_profilenames_map[ID_TRANSFERSESSION] = \
            self._PyHocaGUI._eventid_profilenames_map[ID_RESUMESESSION] = \
            self._PyHocaGUI._eventid_profilenames_map[ID_REFRESHMENU] = \
            self._PyHocaGUI._eventid_profilenames_map[ID_SUSPENDSESSION] = \
            self._PyHocaGUI._eventid_profilenames_map[ID_TERMINATESESSION] = profile_name

        # preparing session_name information for the main PyHocaGUI instance
        self._PyHocaGUI._eventid_sessionnames_map[ID_RAISESESSION] = \
            self._PyHocaGUI._eventid_sessionnames_map[ID_RENAMESESSION] = \
            self._PyHocaGUI._eventid_sessionnames_map[ID_TRANSFERSESSION] = \
            self._PyHocaGUI._eventid_sessionnames_map[ID_RESUMESESSION] = \
            self._PyHocaGUI._eventid_sessionnames_map[ID_REFRESHMENU] = \
            self._PyHocaGUI._eventid_sessionnames_map[ID_SUSPENDSESSION] = \
            self._PyHocaGUI._eventid_sessionnames_map[ID_TERMINATESESSION] = session_name

        _s = self._PyHocaGUI.get_session_of_session_name(session_name, return_object=True, match_profile_name=profile_name)
        _session_status = status
        if session_info is not None:
            _session_status = session_info.get_status()
        elif _s.get_session_info() is not None:
            _session_status = _s.get_session_info().get_status()

        if _s is not None and \
           _s.get_session_type() in ('D', 'S') and \
           _session_status == 'R' and \
           not _s.is_published_applications_provider():

            self.Append(text=_("Window title") + ": " + _s.get_session_title(), id=wx.NewId())
            self.AppendSeparator()

        if _session_status == 'S':

            if _s is not None and _s.is_color_depth_ok():
                _rs = self.Append(text=_("Resume Session"), id=ID_RESUMESESSION)
            else:
                _rs = self.Append(text=_(u"Resume Session (not possible)"), id=ID_RESUMESESSION_DISABLED)
                _rs.Enable(False)

            if session_info is not None and session_info.is_published_applications_provider() and not self._PyHocaGUI.get_profile_config(profile_name, 'published'):
                _rs.Enable(False)

        elif _session_status == 'R':

            if not session_name in self._PyHocaGUI.client_associated_sessions_of_profile_name(profile_name, return_session_names=True):

                if _s is not None and _s.is_color_depth_ok():
                    self.Append(text=_(u"Transfer Session"), id=ID_TRANSFERSESSION)
                else:
                    _ts = self.Append(text=_(u"Transfer Session (not possible)"), id=ID_TRANSFERSESSION_DISABLED)
                    _ts.Enable(False)

            if not _s.is_shadow_session():
                if self._PyHocaGUI.disconnect_on_suspend and self._PyHocaGUI.exit_on_disconnect and _s.has_terminal_session():
                    _ss = self.Append(text=_(u"Suspend Session (and disconnect/exit)"), id=ID_SUSPENDSESSION)
                elif self._PyHocaGUI.disconnect_on_suspend and _s.has_terminal_session():
                    _ss = self.Append(text=_(u"Suspend Session (and disconnect)"), id=ID_SUSPENDSESSION)
                else:
                    _ss = self.Append(text=_(u"Suspend Session"), id=ID_SUSPENDSESSION)

                if _s.is_published_applications_provider() and not self._PyHocaGUI.get_profile_config(profile_name, 'published'):
                    _ss.Enable(False)
        if not _s.is_shadow_session():
            if self._PyHocaGUI.disconnect_on_terminate and self._PyHocaGUI.exit_on_disconnect and _s.has_terminal_session():
                self.Append(text=_(u"Terminate Session (and disconnect/exit)"), id=ID_SUSPENDSESSION)
            elif self._PyHocaGUI.disconnect_on_terminate and _s.has_terminal_session():
                self.Append(text=_(u"Terminate Session (and disconnect)"), id=ID_TERMINATESESSION)
            else:
                self.Append(text=_(u"Terminate Session"), id=ID_TERMINATESESSION)
        else:
            if self._PyHocaGUI.disconnect_on_terminate and self._PyHocaGUI.exit_on_disconnect and _s.has_terminal_session():
                self.Append(text=_(u"End Desktop Sharing (and disconnect/exit)"), id=ID_SUSPENDSESSION)
            elif self._PyHocaGUI.disconnect_on_terminate and _s.has_terminal_session():
                self.Append(text=_(u"End Desktop Sharing (and disconnect)"), id=ID_TERMINATESESSION)
            else:
                self.Append(text=_(u"End Desktop Sharing"), id=ID_TERMINATESESSION)

        if _s is not None and _s.is_published_applications_provider() and self._PyHocaGUI.get_profile_config(profile_name, 'published'):
            self.AppendSeparator()
            self.Append(text=_(u"Refresh menu tree"), id=ID_REFRESHMENU)

        if _s is not None and \
           _s.get_session_type() in ('D', 'S') and \
           not _s.is_published_applications_provider() and \
           _session_status == 'R' and \
           _s in self._PyHocaGUI.client_associated_sessions_of_profile_name(profile_name, return_objects=True):

            self.AppendSeparator()
            self.Append(text=_("Rename Session Window"), id=ID_RENAMESESSION)
            self.Append(text=_("Show Session Window"), id=ID_RAISESESSION)

        self._PyHocaGUI.Bind(wx.EVT_MENU, self._PyHocaGUI.OnSessionFocus, id=ID_RAISESESSION)
        self._PyHocaGUI.Bind(wx.EVT_MENU, self._PyHocaGUI.OnSessionRename, id=ID_RENAMESESSION)
        self._PyHocaGUI.Bind(wx.EVT_MENU, self._PyHocaGUI.OnSessionResume, id=ID_RESUMESESSION)
        self._PyHocaGUI.Bind(wx.EVT_MENU, self._PyHocaGUI.OnSessionResume, id=ID_TRANSFERSESSION)
        self._PyHocaGUI.Bind(wx.EVT_MENU, self._PyHocaGUI.OnPubAppRefreshMenu, id=ID_REFRESHMENU)
        self._PyHocaGUI.Bind(wx.EVT_MENU, self._PyHocaGUI.OnSessionSuspend, id=ID_SUSPENDSESSION)
        self._PyHocaGUI.Bind(wx.EVT_MENU, self._PyHocaGUI.OnSessionTerminate, id=ID_TERMINATESESSION)


class PyHocaGUI_Menu_TaskbarProfileSharedFolders(wx.Menu):
    """\
    Submenu that manages folder sharing per connected session profile.

    """
    def __init__(self, _PyHocaGUI, caller=None, profile_name=None):
        """\
        Folder sharing submenu (constructor).

        @param _PyHocaGUI: main application instance
        @type _PyHocaGUI: C{obj}
        @param caller: unused
        @type caller: C{None}
        @param profile_name: session profile name this submenu is for
        @type profile_name: C{str}

        """
        self._PyHocaGUI = _PyHocaGUI
        self._pyhoca_logger = self._PyHocaGUI._pyhoca_logger

        wx.Menu.__init__(self)

        ID_SHARECUSTOMLOCALFOLDER = wx.NewId()
        ID_UNSHAREALLLOCALFOLDERS = wx.NewId()
        ID_REMEMBERSHAREDFOLDERS = wx.NewId()

        # preparing profile_name information for the main PyHocaGUI instance
        self._PyHocaGUI._eventid_profilenames_map[ID_SHARECUSTOMLOCALFOLDER] = \
            self._PyHocaGUI._eventid_profilenames_map[ID_UNSHAREALLLOCALFOLDERS] = \
            self._PyHocaGUI._eventid_profilenames_map[ID_REMEMBERSHAREDFOLDERS] = profile_name

        self.Append(id=ID_SHARECUSTOMLOCALFOLDER, text=_(u"&Share custom local folder"))

        self.AppendSeparator()
        self._PyHocaGUI._eventid_unshared_folders_map={}

        _exported_folders = self._PyHocaGUI.get_profile_config(profile_name, 'export')
        _shared_folders = self._PyHocaGUI._X2GoClient__profile_get_shared_folders(profile_name=profile_name, check_list_mounts=True) or []
        _sharable_folders = _exported_folders.keys()
        _unshared_folders = [ f for f in _sharable_folders if f and f not in _shared_folders ]

        self._PyHocaGUI._eventid_unshared_folders_map = {}
        if _unshared_folders:
            self.Append(id=wx.NewId(), text=_(u'Share:'))
            for _unshared_folder in _unshared_folders:
                ID_THISFOLDER = wx.NewId()
                self.Append(id=ID_THISFOLDER, text="      %s" % _unshared_folder)
                self._PyHocaGUI._eventid_profilenames_map[ID_THISFOLDER] = profile_name
                self._PyHocaGUI._eventid_unshared_folders_map[ID_THISFOLDER] = _unshared_folder
                self._PyHocaGUI.Bind(wx.EVT_MENU, self._PyHocaGUI.OnShareLocalFolder, id=ID_THISFOLDER)

        self._PyHocaGUI._eventid_shared_folders_map = {}
        if _shared_folders:
            self.Append(id=wx.NewId(), text=_(u'Unshare:'))
            for _shared_folder in _shared_folders:
                ID_THISFOLDER = wx.NewId()
                self.Append(id=ID_THISFOLDER, text="      %s" % _shared_folder)
                self._PyHocaGUI._eventid_profilenames_map[ID_THISFOLDER] = profile_name
                self._PyHocaGUI._eventid_shared_folders_map[ID_THISFOLDER] = _shared_folder
                self._PyHocaGUI.Bind(wx.EVT_MENU, self._PyHocaGUI.OnUnshareLocalFolder, id=ID_THISFOLDER)

        _unshare_folders = self.Append(id=ID_UNSHAREALLLOCALFOLDERS, text=_(u"Unshare &all local folders"))
        if not _shared_folders:
            _unshare_folders.Enable(False)

        self.AppendSeparator()

        _remember_shared_folders_item = self.AppendCheckItem(id=ID_REMEMBERSHAREDFOLDERS, text=_(u"Restore shares in next session"))
        if not self._PyHocaGUI._remember_shared_folders.has_key(profile_name):
            self._PyHocaGUI._remember_shared_folders[profile_name] = self._PyHocaGUI.get_profile_config(profile_name, 'restoreexports')
        _remember_shared_folders_item.Check(self._PyHocaGUI._remember_shared_folders[profile_name])

        self._PyHocaGUI.Bind(wx.EVT_MENU, self._PyHocaGUI.OnShareCustomLocalFolder, id=ID_SHARECUSTOMLOCALFOLDER)
        self._PyHocaGUI.Bind(wx.EVT_MENU, self._PyHocaGUI.OnRememberSharedFolders, id=ID_REMEMBERSHAREDFOLDERS)
        self._PyHocaGUI.Bind(wx.EVT_MENU, self._PyHocaGUI.OnUnshareAllLocalFolders, id=ID_UNSHAREALLLOCALFOLDERS)


class PyHocaGUI_Menu_LaunchSingleApplication(wx.Menu):
    """\
    Submenu that triggers single application launches.

    """
    def __init__(self, _PyHocaGUI, caller=None, profile_name=None):
        """\
        Single application launching submenu (constructor).

        @param _PyHocaGUI: main application instance
        @type _PyHocaGUI: C{obj}
        @param caller: unused
        @type caller: C{None}
        @param profile_name: session profile name this submenu is for
        @type profile_name: C{str}

        """
        self._PyHocaGUI = _PyHocaGUI
        self._pyhoca_logger = self._PyHocaGUI._pyhoca_logger

        wx.Menu.__init__(self)

        _available_applications = {
            'WWWBROWSER': _(u'Internet Browser'),
            'MAILCLIENT': _(u'Email Client'),
            'OFFICE': _(u'Office'),
            'TERMINAL': _(u'Terminal'),
            }

        for application in self._PyHocaGUI.get_profile_config(profile_name, 'applications'):

            _app_id = wx.NewId()
            self._PyHocaGUI._eventid_profilenames_map[_app_id] = profile_name
            self._PyHocaGUI._eventid_applications_map[_app_id] = application
            self.Append(id=_app_id, text=_available_applications[application])
            self._PyHocaGUI.Bind(wx.EVT_MENU, self._PyHocaGUI.OnApplicationStart, id=_app_id)


def _generate_Menu_PublishedApplications(_PyHocaGUI, caller=None, profile_name=None, session_name=None):
    """\
    Generate wxPython based menu tree for X2Go published applications.

    @param _PyHocaGUI: main application instance
    @type _PyHocaGUI: C{obj}
    @param caller: unused
    @type caller: C{None}
    @param profile_name: session profile name this submenu is for
    @type profile_name: C{str}
    @param session_name: X2Go session name this submenu is for
    @type session_name: C{str}

    @return: dictionary based menu tree containing wx.Menu objects for menu rendering.
    @rtype: C{dict}

    """
    _lang = _PyHocaGUI.lang
    _pubapp_session = _PyHocaGUI.get_session_of_session_name(session_name, return_object=True, match_profile_name=profile_name)
    try:
        menu_map = _pubapp_session.get_published_applications(lang=_lang, max_no_submenus=_PyHocaGUI.args.published_applications_no_submenus)
    except AttributeError:
        menu_map = None
    if not menu_map or not menu_map.has_key(_lang):
        menu_map = { _lang: {} }

    if x2go.defaults.X2GOCLIENT_OS == 'Windows':
        _icon_size = "16x16"
    else:
        _icon_size = "22x22"

    _icons_location = basepath.icons_basepath
    _category_name_translator = {
        'Multimedia': (_(u'Multimedia'), os.path.normpath('%s/PyHoca/%s/applications-multimedia.png' % (_icons_location, _icon_size), ), ),
        'Development': (_(u'Development'), os.path.normpath('%s/PyHoca/%s/applications-development.png' % (_icons_location, _icon_size), ), ),
        'Education': (_(u'Education'), os.path.normpath('%s/PyHoca/%s/applications-education.png' % (_icons_location, _icon_size), ), ),
        'Games': (_(u'Games'), os.path.normpath('%s/PyHoca/%s/applications-games.png' % (_icons_location, _icon_size), ), ),
        'Graphics': (_(u'Graphics'), os.path.normpath('%s/PyHoca/%s/applications-graphics.png' % (_icons_location, _icon_size), ), ),
        'Internet': (_(u'Internet'), os.path.normpath('%s/PyHoca/%s/applications-internet.png' % (_icons_location, _icon_size), ), ),
        'Office': (_(u'Office Applications'), os.path.normpath('%s/PyHoca/%s/applications-office.png' % (_icons_location, _icon_size), ), ),
        'System': (_(u'System'), os.path.normpath('%s/PyHoca/%s/applications-system.png' % (_icons_location, _icon_size), ), ),
        'Utilities': (_(u'Utilities'), os.path.normpath('%s/PyHoca/%s/applications-utilities.png' % (_icons_location, _icon_size), ), ),
        'Other Applications': (_(u'Other Applications'), os.path.normpath('%s/PyHoca/%s/applications-other.png' % (_icons_location, _icon_size), ), ),
        'TOP': ('TOP', os.path.normpath('%s/PyHoca/%s/x2go-logo-grey.png' % (_icons_location, _icon_size), ), ),
    }

    _PyHocaGUI._eventid_pubapp_execmap[profile_name] = {}

    nolog = wx.LogNull()
    _wx_menu_map = {}
    if menu_map[_lang].keys():
        for cat in menu_map[_lang].keys():

            _wx_menu_map[_category_name_translator[cat][0]] = (wx.Menu(), _category_name_translator[cat][1])

            for _item in menu_map[_lang][cat]:
                _pubapp_id = wx.NewId()
                _PyHocaGUI._eventid_profilenames_map[_pubapp_id] = profile_name
                _PyHocaGUI._eventid_sessionnames_map[_pubapp_id] = session_name
                _PyHocaGUI._eventid_pubapp_execmap[profile_name][_pubapp_id] = _item['exec']

                _menu_item = wx.MenuItem(_wx_menu_map[_category_name_translator[cat][0]][0], id=_pubapp_id, text=_item['name'], help=_item['comment'])
                if not _item['icon']:
                    _menu_item.SetBitmap(wx.Bitmap(os.path.normpath('%s/PyHoca/%s/x2go-logo-grey.png' % (_icons_location, _icon_size))))
                else:
                    _menu_entry_icon_decoded = base64.b64decode(_item['icon'])
                    _icon_image = wx.ImageFromStream(StringIO.StringIO(_menu_entry_icon_decoded))
                    if x2go.defaults.X2GOCLIENT_OS == 'Windows':
                        _icon_bitmap = wx.BitmapFromImage(_icon_image.Scale(16,16))
                    else:
                        _icon_bitmap = wx.BitmapFromImage(_icon_image.Scale(22,22))
                    _menu_item.SetBitmap(_icon_bitmap)

                _wx_menu_map[_category_name_translator[cat][0]][0].AppendItem(_menu_item)
                _PyHocaGUI.Bind(wx.EVT_MENU, _PyHocaGUI.OnPubAppExecution, id=_pubapp_id)

    del nolog
    return _wx_menu_map


class PyHocaGUI_Menu_TaskbarSessionProfile(wx.Menu):
    """\
    Submenu for a connected session profile.

    """
    def __init__(self, _PyHocaGUI, caller=None, profile_name=None):
        """\
        Session profile submenu (constructor).

        @param _PyHocaGUI: main application instance
        @type _PyHocaGUI: C{obj}
        @param caller: unused
        @type caller: C{None}
        @param profile_name: session profile name this submenu is for
        @type profile_name: C{str}

        """
        self._PyHocaGUI = _PyHocaGUI
        self._pyhoca_logger = self._PyHocaGUI._pyhoca_logger

        wx.Menu.__init__(self)

        ID_AUTHENTICATE_BROKER=wx.NewId()
        ID_CONNECT=wx.NewId()
        ID_PUBAPPSESSIONSTART=wx.NewId()
        ID_SESSIONSTART=wx.NewId()
        ID_SHADOWSESSIONSTART=wx.NewId()
        ID_LAUNCHAPPLICATION = wx.NewId()
        ID_CLEANSESSIONS = wx.NewId()
        ID_EDITPROFILEWHILECONNECTED = wx.NewId()
        ID_SHARELOCALFOLDER = wx.NewId()
        ID_UNSHAREFOLDERS = wx.NewId()

        _foldersharing_disabled = False

        if self._PyHocaGUI.with_brokerage and not self._PyHocaGUI.session_profiles.is_broker_authenticated():
            _auth_menu_text = _(u'Connect to') + self._PyHocaGUI.broker_name
            self.Append(id=ID_AUTHENTICATE_BROKER, text=_auth_menu_text)
            self._PyHocaGUI.Bind(wx.EVT_MENU, self._PyHocaGUI.OnBrokerAuthenticate, id=ID_AUTHENTICATE_BROKER)

        elif self._PyHocaGUI.args.single_session_profile and not self._PyHocaGUI.is_session_profile(profile_name):
            connect = self.Append(id=ID_CONNECT, text=_(u'Connect %s') % profile_name)
            connect.Enable(False)
        else:
            _applications = self._PyHocaGUI.get_profile_config(profile_name, 'applications')
            _command = self._PyHocaGUI.get_profile_config(profile_name, 'command')
            _published = self._PyHocaGUI.get_profile_config(profile_name, 'published')
            _useexports = self._PyHocaGUI.get_profile_config(profile_name, 'useexports')

            if profile_name in self._PyHocaGUI._temp_disabled_profile_names:
                _connecting_info = self.Append(wx.NewId(), text=_(u'Currently connecting...'))
                _connecting_info.Enable(False)

            elif self._PyHocaGUI.args.single_session_profile and \
                 not self._PyHocaGUI.is_profile_connected(profile_name=profile_name):
                    self._PyHocaGUI._eventid_profilenames_map[ID_CONNECT] = profile_name
                    self.Append(id=ID_CONNECT, text=_(u'Connect %s') % profile_name)
                    self._PyHocaGUI.Bind(wx.EVT_MENU, self._PyHocaGUI.OnSessionAuthenticate, id=ID_CONNECT)

            else:

                self._PyHocaGUI._eventid_profilenames_map[ID_SESSIONSTART] = \
                    self._PyHocaGUI._eventid_profilenames_map[ID_SHADOWSESSIONSTART] = profile_name

                if _command in x2go.defaults.X2GO_DESKTOPSESSIONS:
                    self.Append(id=ID_SESSIONSTART, text='%s (%s)' % (_(u"Start &new Desktop Session"), _command))
                    self._PyHocaGUI.Bind(wx.EVT_MENU, self._PyHocaGUI.OnSessionStart, id=ID_SESSIONSTART)

                elif _command == 'SHADOW':
                    self.Append(id=ID_SHADOWSESSIONSTART, text=_(u"Start Desktop Sharing Session"))
                    self._PyHocaGUI.Bind(wx.EVT_MENU, self._PyHocaGUI.OnShadowSessionStart, id=ID_SHADOWSESSIONSTART)

                elif _command == '' and _published:
                    #appprime code start
                    #_pub_app_start_item = None
                    #_pub_app_start_item = self.Append(id=ID_PUBAPPSESSIONSTART, text=_(u"Retrieving Application Menu..."))
                    #_pub_app_start_item.Enable(False)
                    #self._PyHocaGUI.Bind(wx.EVT_MENU, self._PyHocaGUI.OnPubAppSessionStart, id=ID_PUBAPPSESSIONSTART)
                    #apprime code end
                    """\
                    if profile_name in self._PyHocaGUI._temp_launching_pubapp_profiles:
                        _pub_app_start_item = self.Append(id=ID_PUBAPPSESSIONSTART, text=_(u"Retrieving Application Menu..."))
                        _pub_app_start_item.Enable(False)
                    elif not (self._PyHocaGUI.disconnect_on_suspend and self._PyHocaGUI.disconnect_on_terminate):
                        self._PyHocaGUI._eventid_profilenames_map[ID_PUBAPPSESSIONSTART] = profile_name
                        #apprime
                        #_pub_app_start_item = self.Append(id=ID_PUBAPPSESSIONSTART, text=_(u"Retrieve Application Menu"))
                        #self._PyHocaGUI.Bind(wx.EVT_MENU, self._PyHocaGUI.OnPubAppSessionStart, id=ID_PUBAPPSESSIONSTART)
                    """
                elif _command == 'RDP':
                    self.Append(id=ID_SESSIONSTART, text=_(u"Start &new RDP Session"))
                    self._PyHocaGUI.Bind(wx.EVT_MENU, self._PyHocaGUI.OnSessionStart, id=ID_SESSIONSTART)
                else:
                    self.Append(id=ID_SESSIONSTART, text=_(u"Start &new Session"))
                    self._PyHocaGUI.Bind(wx.EVT_MENU, self._PyHocaGUI.OnSessionStart, id=ID_SESSIONSTART)

                if _command == '' and _published:

                    _pubapp_sessions = [ _pas for _pas in self._PyHocaGUI.client_pubapp_sessions_of_profile_name(profile_name, return_objects=True) if _pas.is_running() ]
                    if _pubapp_sessions:
                        _pubapp_session = _pubapp_sessions[0]
                        #if _pub_app_start_item is not None:
                        #    _pub_app_start_item.Enable(False)
                        _foldersharing_disabled = _session_name_disabled = self._PyHocaGUI.is_session_name_disabled(profile_name, _pubapp_session.get_session_name())
                        _category_map = _generate_Menu_PublishedApplications(self._PyHocaGUI, caller=self, profile_name=profile_name, session_name=_pubapp_session.get_session_name())
                        _category_names = _category_map.keys()
                        _category_names.sort()
                        #if (not self._PyHocaGUI.restricted_trayicon and not (self._PyHocaGUI.disconnect_on_suspend and self._PyHocaGUI.disconnect_on_terminate)) or (profile_name in self._PyHocaGUI._temp_launching_pubapp_profiles and _category_names):
                        #    self.AppendSeparator()
                        for cat_name in [ _cn for _cn in _category_names if _cn != 'TOP' ]:
                            _submenu = self.AppendMenu(id=wx.NewId(), text=cat_name, submenu=_category_map[cat_name][0])
                            _submenu.SetBitmap(wx.Bitmap(_category_map[cat_name][1]))
                            if _session_name_disabled:
                                _submenu.Enable(False)
                        if 'TOP' in _category_names:
                            for _menu_item in _category_map['TOP'][0].GetMenuItems():
                                _item = self.AppendItem(item=_menu_item)
                                if _session_name_disabled:
                                    _item.Enable(False)
                        if _category_names:
                            self.AppendSeparator()

                        ID_RESUMESESSION = wx.NewId()
                        ID_REFRESHMENU = wx.NewId()
                        ID_SUSPENDSESSION = wx.NewId()
                        ID_TERMINATESESSION = wx.NewId()
                        self._PyHocaGUI._eventid_profilenames_map[ID_RESUMESESSION] = \
                            self._PyHocaGUI._eventid_profilenames_map[ID_REFRESHMENU] = \
                            self._PyHocaGUI._eventid_profilenames_map[ID_SUSPENDSESSION] = \
                            self._PyHocaGUI._eventid_profilenames_map[ID_TERMINATESESSION] = profile_name
                        self._PyHocaGUI._eventid_sessionnames_map[ID_RESUMESESSION] = \
                            self._PyHocaGUI._eventid_sessionnames_map[ID_REFRESHMENU] = \
                            self._PyHocaGUI._eventid_sessionnames_map[ID_SUSPENDSESSION] = \
                            self._PyHocaGUI._eventid_sessionnames_map[ID_TERMINATESESSION] = _pubapp_session.get_session_name()

                        """\
                        if _pubapp_session.is_running():
                            _refresh_menu_item = self.Append(text=_(u"Refresh menu tree"), id=ID_REFRESHMENU)
                            self.AppendSeparator()
                            if self._PyHocaGUI.disconnect_on_suspend and self._PyHocaGUI.exit_on_disconnect and _pubapp_session.has_terminal_session():
                                _suspend_item = self.Append(text=_(u"Suspend Session (and disconnect/exit)"), id=ID_SUSPENDSESSION)
                            elif self._PyHocaGUI.disconnect_on_suspend and _pubapp_session.has_terminal_session():
                                _suspend_item = self.Append(text=_(u"Suspend Session (and disconnect)"), id=ID_SUSPENDSESSION)
                            else:
                                _suspend_item = self.Append(text=_(u"Suspend Session"), id=ID_SUSPENDSESSION)
                            if _session_name_disabled:
                                _refresh_menu_item.Enable(False)
                                _suspend_item.Enable(False)
                        elif _pubapp_session.is_suspended():
                            _resume_item = self.Append(text=_(u"Resume Session"), id=ID_RESUMESESSION)
                            if _session_name_disabled:
                                _resume_item.Enable(False)
                        """
                        ID_SERVERINFO = wx.NewId()
                        self._PyHocaGUI._eventid_profilenames_map[ID_SERVERINFO] = profile_name
                        self.Append(id=ID_SERVERINFO, text=_(u"Connection Status"))
                        self._PyHocaGUI.Bind(wx.EVT_MENU, self._PyHocaGUI.OnViewServerInformation, id=ID_SERVERINFO)
                        
                        if self._PyHocaGUI.disconnect_on_terminate and self._PyHocaGUI.exit_on_disconnect and _pubapp_session.has_terminal_session():
                            _terminate_item = self.Append(text=_(u"Terminate Session (and disconnect/exit)"), id=ID_TERMINATESESSION)
                        elif self._PyHocaGUI.disconnect_on_terminate and _pubapp_session.has_terminal_session():
                            _terminate_item = self.Append(text=_(u"Terminate Session (and disconnect)"), id=ID_TERMINATESESSION)
                        else:
                            _terminate_item = self.Append(text=_(u"Close Session"), id=ID_TERMINATESESSION)
                        if _session_name_disabled:
                            _terminate_item.Enable(False)

                        self._PyHocaGUI.Bind(wx.EVT_MENU, self._PyHocaGUI.OnSessionResume, id=ID_RESUMESESSION)
                        self._PyHocaGUI.Bind(wx.EVT_MENU, self._PyHocaGUI.OnPubAppRefreshMenu, id=ID_REFRESHMENU)
                        self._PyHocaGUI.Bind(wx.EVT_MENU, self._PyHocaGUI.OnSessionSuspend, id=ID_SUSPENDSESSION)
                        self._PyHocaGUI.Bind(wx.EVT_MENU, self._PyHocaGUI.OnSessionTerminate, id=ID_TERMINATESESSION)
                    else: #apprime
                        #appprime code start
                        _pub_app_start_item = None
                        _pub_app_start_item = self.Append(id=ID_PUBAPPSESSIONSTART, text=_(u"Retrieving Application Menu..."))
                        _pub_app_start_item.Enable(False)
                        self._PyHocaGUI.Bind(wx.EVT_MENU, self._PyHocaGUI.OnPubAppSessionStart, id=ID_PUBAPPSESSIONSTART)
                        #apprime code end
                    
                else:

                    # preparing profile_name information for the main PyHocaGUI instance
                    self._PyHocaGUI._eventid_profilenames_map[ID_LAUNCHAPPLICATION] = \
                        self._PyHocaGUI._eventid_profilenames_map[ID_CLEANSESSIONS] = profile_name

                    if _applications and _command in x2go.defaults.X2GO_DESKTOPSESSIONS.keys() and not _published:
                        self.AppendSeparator()
                        self.AppendMenu(id=ID_LAUNCHAPPLICATION, text=_(u"Launch Single Application"),
                                        submenu=PyHocaGUI_Menu_LaunchSingleApplication(self._PyHocaGUI, caller=self, profile_name=profile_name)
                                       )
                        if _command != 'SHADOW' and not self._PyHocaGUI.restricted_trayicon:
                            self.Append(id=ID_SHADOWSESSIONSTART, text=_(u"Start Desktop Sharing Session"))
                            self._PyHocaGUI.Bind(wx.EVT_MENU, self._PyHocaGUI.OnShadowSessionStart, id=ID_SHADOWSESSIONSTART)

                    if _published:

                        if not self._PyHocaGUI.restricted_trayicon:
                            self.AppendSeparator()

                        _pubapp_session = None
                        _pubapp_sessions = [ _pas for _pas in self._PyHocaGUI.client_pubapp_sessions_of_profile_name(profile_name, return_objects=True) if _pas.is_running() ]
                        if _pubapp_sessions:
                            _pubapp_session = _pubapp_sessions[0]
                        if _pubapp_session and _pubapp_session.is_running():
                            _session_name_disabled = self._PyHocaGUI.is_session_name_disabled(profile_name, _pubapp_session.get_session_name())
                            self._pyhoca_logger('====>>>>_generate_Menu_PublishedApplications for profile %s' % profile_name)
                            _category_map = _generate_Menu_PublishedApplications(self._PyHocaGUI, caller=self, profile_name=profile_name, session_name=_pubapp_session.get_session_name())
                            _category_names = _category_map.keys()
                            _category_names.sort()
                            for cat_name in [ _cn for _cn in _category_names if _cn != 'TOP' ]:
                                _submenu = self.AppendMenu(id=wx.NewId(), text=cat_name, submenu=_category_map[cat_name][0])
                                _submenu.SetBitmap(wx.Bitmap(_category_map[cat_name][1]))
                                if _session_name_disabled:
                                    _submenu.Enable(False)
                            if 'TOP' in _category_names:
                                for _menu_item in _category_map['TOP'][0].GetMenuItems():
                                    _item = self.AppendItem(item=_menu_item)
                                    if _session_name_disabled:
                                        _item.Enable(False)

                            self.AppendSeparator()

                            _marker = ''
                            _status = None
                            if _pubapp_session.is_master_session(): _marker = '(*)'
                            if _pubapp_session.is_running(): _status = 'R'
                            elif _pubapp_session.is_suspended(): _status = 'S'

                            if _status:
                                _submenu = self.AppendMenu(id=wx.NewId(), text=_(u'Manage Application Menu')+' %s' % _marker,
                                                           submenu=PyHocaGUI_Menu_TaskbarSessionActions(self._PyHocaGUI, caller=self,
                                                                                                        profile_name=profile_name,
                                                                                                        session_name=_pubapp_session.get_session_name(),
                                                                                                        status=_status,
                                                                                                       )
                                                      )
                                if _session_name_disabled:
                                    _submenu.Enable(False)

                        else:
                            _ram = self.Append(id=ID_PUBAPPSESSIONSTART, text=_(u"Retrieving Application Menu..."))
                            _ram.Enable(False)
                            self._PyHocaGUI.Bind(wx.EVT_MENU, self._PyHocaGUI.OnPubAppSessionStart, id=ID_PUBAPPSESSIONSTART)
                            """ #apprime
                            self._PyHocaGUI._eventid_profilenames_map[ID_PUBAPPSESSIONSTART] = profile_name
                            if profile_name in self._PyHocaGUI._temp_launching_pubapp_profiles:
                                _ram = self.Append(id=ID_PUBAPPSESSIONSTART, text=_(u"Retrieving Application Menu..."))
                                _ram.Enable(False)
                            else:
                                vg_a = 16 #dummy
                                #apprime - do not show "retrieve menu". We will try to always get the menu within 5 secs
                                #   even if not, we do not want users to click and try upsetting the control session.
                                #self.Append(id=ID_PUBAPPSESSIONSTART, text=_(u"Retrieve Application Menu"))
                            self._PyHocaGUI.Bind(wx.EVT_MENU, self._PyHocaGUI.OnPubAppSessionStart, id=ID_PUBAPPSESSIONSTART)
                            """
                    _query_session_uuid = self._PyHocaGUI.client_connected_sessions_of_profile_name(profile_name, return_objects=False)[0]
                    _session_list = self._PyHocaGUI.list_sessions(_query_session_uuid)

                    _session_list_names = []
                    if _session_list:

                        # newest sessions at the top
                        if _published:
                            _session_list_names = [ _s_name for _s_name in _session_list.keys() if not _session_list[_s_name].is_published_applications_provider() ]
                        else:
                            _session_list_names = _session_list.keys()
                        _session_list_names.reverse()

                    if _session_list_names:

                        _session_list_matching_profile = []
                        for session_name in _session_list_names:

                            session = self._PyHocaGUI.get_session_of_session_name(session_name, return_object=True, match_profile_name=profile_name)

                            if not session:
                                continue
                            else:
                                _session_list_matching_profile.append(session)

                        if _session_list_matching_profile:

                            self.AppendSeparator()

                            for session in _session_list_matching_profile:

                                session_name = session.get_session_name()

                                _s_id = wx.NewId()

                                if _session_list[session_name].get_status() == 'R':
                                    state = _(u'Running')
                                elif _session_list[session_name].get_status() == 'S':
                                    state = _(u'Suspended')
                                _marker = ''
                                if session and session.is_master_session():
                                    _marker = '(*)'
                                if session:
                                    session_submenu = self.AppendMenu(id=_s_id, text=u'%s: »%s« %s' % (state, session_name, _marker),
                                                                      submenu=PyHocaGUI_Menu_TaskbarSessionActions(self._PyHocaGUI, caller=self,
                                                                                                                   profile_name=profile_name,
                                                                                                                   session_name=session_name,
                                                                                                                   session_info=_session_list[session_name],
                                                                                                                  )
                                                                 )
                                    if self._PyHocaGUI._temp_disabled_session_names.has_key(profile_name) and session_name in self._PyHocaGUI._temp_disabled_session_names[profile_name]:
                                        session_submenu.Enable(False)

                            # redefine list of session names to decide if the clean all session menu item is not be shown
                            _session_list_names = [ _s.get_session_name() for _s in _session_list_matching_profile if not _session_list[_s.get_session_name()].is_published_applications_provider() ]

                            if _session_list_names:
                                self.Append(id=ID_CLEANSESSIONS, text=_(u"&Clean all sessions"))
                                self._PyHocaGUI.Bind(wx.EVT_MENU, self._PyHocaGUI.OnCleanSessions, id=ID_CLEANSESSIONS)

                if not self._PyHocaGUI.restricted_trayicon:
                    """\
                    self.AppendSeparator()
                    if self._PyHocaGUI.session_profiles.is_mutable(profile_name):
                        self.Append(id=ID_EDITPROFILEWHILECONNECTED, text=_(u"Customize &profile"))
                    else:
                        self.Append(id=ID_EDITPROFILEWHILECONNECTED, text=_(u"View &profile"))
                    self._PyHocaGUI.Bind(wx.EVT_MENU, self._PyHocaGUI.OnProfileEditWhileConnected, id=ID_EDITPROFILEWHILECONNECTED)
                    """
                self._PyHocaGUI._eventid_profilenames_map[ID_EDITPROFILEWHILECONNECTED] = \
                    self._PyHocaGUI._eventid_profilenames_map[ID_SHARELOCALFOLDER] = \
                    self._PyHocaGUI._eventid_profilenames_map[ID_UNSHAREFOLDERS] = profile_name

                if _useexports and \
                   self._PyHocaGUI._X2GoClient__profile_is_folder_sharing_available(profile_name=profile_name) and \
                   self._PyHocaGUI.get_master_session(profile_name) is not None and \
                   self._PyHocaGUI.is_session_name_enabled(profile_name, self._PyHocaGUI.get_master_session(profile_name).get_session_name()):

                    if self._PyHocaGUI.restricted_trayicon:
                        self.AppendSeparator()

                    _shared_folders = self.AppendMenu(id=ID_SHARELOCALFOLDER, text=_(u"Shared &folders"),
                                                      submenu=PyHocaGUI_Menu_TaskbarProfileSharedFolders(self._PyHocaGUI, caller=self,
                                                      profile_name=profile_name)
                                                     )
                    if not self._PyHocaGUI.get_master_session(profile_name=profile_name) or _foldersharing_disabled:
                        _shared_folders.Enable(False)


        if profile_name in self._PyHocaGUI.client_connected_profiles(return_profile_names=True) and not self._PyHocaGUI.restricted_trayicon:
            vg_a = 16 #dummy line
#            self.AppendSeparator()
#            ID_SERVERINFO = wx.NewId()
#            self._PyHocaGUI._eventid_profilenames_map[ID_SERVERINFO] = profile_name
#            self.Append(id=ID_SERVERINFO, text=_(u"Connection Status"))
#            self._PyHocaGUI.Bind(wx.EVT_MENU, self._PyHocaGUI.OnViewServerInformation, id=ID_SERVERINFO)
            
        if profile_name in self._PyHocaGUI.client_connected_profiles(return_profile_names=True) and not self._PyHocaGUI.exit_on_disconnect:
            #self.AppendSeparator()
            ID_DISCONNECT = wx.NewId()
            self._PyHocaGUI._eventid_profilenames_map[ID_DISCONNECT] = profile_name
            self.Append(id=ID_DISCONNECT, text=_(u"&Logout"))
            self._PyHocaGUI.Bind(wx.EVT_MENU, self._PyHocaGUI.OnServerDisconnect, id=ID_DISCONNECT)

        if self._PyHocaGUI.args.single_session_profile:
            ID_EXIT = wx.NewId()
            if self._PyHocaGUI.client_running_sessions_of_profile_name(profile_name=self._PyHocaGUI.args.session_profile) and self._PyHocaGUI.exit_on_disconnect and not self._PyHocaGUI.disconnect_on_suspend:
                self.AppendSeparator()
                self.Append(id=ID_EXIT, text=_(u"Suspend Session and E&xit application"))
                self._PyHocaGUI.Bind(wx.EVT_MENU, self._PyHocaGUI.OnTaskbarExit, id=ID_EXIT)
            elif self._PyHocaGUI.is_profile_connected(profile_name=self._PyHocaGUI.args.session_profile) and self._PyHocaGUI.exit_on_disconnect and not self._PyHocaGUI.disconnect_on_suspend:
                self.AppendSeparator()
                self.Append(id=ID_EXIT, text=_(u"Disconnect and E&xit application"))
                self._PyHocaGUI.Bind(wx.EVT_MENU, self._PyHocaGUI.OnTaskbarExit, id=ID_EXIT)
            elif not self._PyHocaGUI.exit_on_disconnect and not (self._PyHocaGUI.disconnect_on_suspend or self._PyHocaGUI.disconnect_on_terminate):
                self.AppendSeparator()
                self.Append(id=ID_EXIT, text=_(u"E&xit"))
                self._PyHocaGUI.Bind(wx.EVT_MENU, self._PyHocaGUI.OnTaskbarExit, id=ID_EXIT)


class PyHocaGUI_Menu_TaskbarProfileNames(wx.Menu):
    """\
    Render a (recursive) menu subtree that contains a cascaded menu tree of all session profile names.

    If session profile names contain '/' as a separator character then those session profile names
    will be rendered in a tree-like fashion.

    """
    def __init__(self, _PyHocaGUI, caller=None,
                 sub_profile_items=[], filter_profiles=[], disabled_profiles=[],
                 bind_method=None,
                 submenu=None,
                 group_menus=True, group_name='', parent_group=''):
        """\
        Session profile name (recursive) menu subtree

        @param _PyHocaGUI: main application instance
        @type _PyHocaGUI: C{obj}
        @param caller: unused
        @type caller: C{None}
        @param sub_profile_items: on recursion this argument contains those session profile names
            that will be rendered for this session profile subtree
        @type  sub_profile_items: C{list}
        @param filter_profiles: allow filtering of profile names (hiding certain session profiles)
        @type filter_profiles: C{list}
        @param disabled_profiles: session profile names that get greyed out in the menu tree
        @type disabled_profiles: C{list}
        @param bind_method: if session profile names are menu items this argument names the Python method that menu items will bind to
        @type bind_method: C{method}
        @param submenu: if session profile names are submenus this argument names the wx.Menu class that handles the submenu rendering
        @type submenu: C{class}
        @param group_menus: group session profile names in submenus (i.e. switch on recursion mode)
        @type group_menus: C{bool}
        @param group_name: on recursion, this argument names the parent menu folder of the current submenu
        @type group_name: C{str}
        @param parent_group: on recursion, the parent group of C{group_name}
        @type parent_group: C{str}

        """
        self._PyHocaGUI = _PyHocaGUI
        self._pyhoca_logger = self._PyHocaGUI._pyhoca_logger

        wx.Menu.__init__(self)

        if type(caller) == PyHocaGUI_Menu_TaskbarOptionsManager and self._PyHocaGUI.session_profiles.supports_mutable_profiles():
            ID_ADDPROFILE = wx.NewId()
            self.Append(id=ID_ADDPROFILE, text=_(u"Add Profile"))
            self._PyHocaGUI.Bind(wx.EVT_MENU, self._PyHocaGUI.OnProfileAdd, id=ID_ADDPROFILE)

            self.AppendSeparator()

        if sub_profile_items:
            _profile_names = sub_profile_items
        else:
            _profile_names = self._PyHocaGUI.session_profiles.profile_names
        _profile_names.sort()

        _profile_groups = []
        if group_menus:

            _parent_group = group_name

            # grouping of session profile menus
            for profile_name in _profile_names:
                if len(profile_name.split('/')) >= 2:
                    _group_name = profile_name.split('/')[0]
                    if not _group_name in _profile_groups:
                        _profile_groups.append(_group_name)

            _profile_groups.sort()

            for profile_group in _profile_groups:
                _sub_profile_items = []
                for profile_name in [ p for p in _profile_names if p.startswith('%s/' % profile_group) ]:
                    _sub_profile_name = "/".join(profile_name.split('/')[1:])
                    _sub_profile_items.append(_sub_profile_name)
                    filter_profiles.append(profile_name)

                _this_id = wx.NewId()
                self.AppendMenu(text=profile_group, id=_this_id,
                                     submenu=PyHocaGUI_Menu_TaskbarProfileNames(self._PyHocaGUI,
                                                                                caller=self,
                                                                                sub_profile_items=_sub_profile_items,
                                                                                filter_profiles=[],
                                                                                disabled_profiles=disabled_profiles,
                                                                                submenu=submenu,
                                                                                bind_method=bind_method,
                                                                                group_name=profile_group,
                                                                                parent_group=_parent_group,
                                                                                group_menus=True)

                                    )
        if filter_profiles:
            _profile_names = [ p for p in _profile_names if p not in filter_profiles ]

        for profile_name in _profile_names:
            if group_name:
                if parent_group:
                    _real_profile_name = '%s/%s/%s' % (parent_group, group_name, profile_name)
                else:
                    _real_profile_name = '%s/%s' % (group_name, profile_name)
                _show_profile_name = profile_name
            else:
                _real_profile_name = profile_name
                _show_profile_name = profile_name
            _this_id = wx.NewId()
            self._PyHocaGUI._eventid_profilenames_map[_this_id] = _real_profile_name
            _menu_profile_name = self._PyHocaGUI.show_profile_metatypes and '%s (%s)' % (_show_profile_name, self._PyHocaGUI.get_profile_metatype(_real_profile_name)) or _show_profile_name
            if submenu is not None:
                _sub = self.AppendMenu(text=_menu_profile_name, id=_this_id, submenu=submenu(self._PyHocaGUI, caller=self, profile_name=_real_profile_name))
                if disabled_profiles and _real_profile_name in disabled_profiles:
                    _sub.Enable(False)
            else:
                _item = self.Append(text=_menu_profile_name, id=_this_id)

                if disabled_profiles and _real_profile_name in disabled_profiles:
                    _item.Enable(False)
                if bind_method is not None:
                    self._PyHocaGUI.Bind(wx.EVT_MENU, bind_method, id=_this_id)
                    self._PyHocaGUI.Bind(wx.EVT_UPDATE_UI, self.OnUpdateUI, id=_this_id)

        if not group_name and (not _profile_groups and not _profile_names) and not filter_profiles:
            if self._PyHocaGUI.with_brokerage:
                _dummy = self.Append(text=_(u'Session broker is not connected'), id=wx.NewId())
            else:
                _dummy = self.Append(text=_(u'No session profiles defined'), id=wx.NewId())
            _dummy.Enable(False)

        else:
            if bind_method is None:
                self.AppendSeparator()
                _export_id = wx.NewId()
                _export_group_name = "%s/%s" % (parent_group, group_name)
                _export_group_name = _export_group_name.strip("/")
                self._PyHocaGUI._eventid_exportprofiles_map[_export_id] = _export_group_name
                if not group_name:
                    self.Append(text=_(u'Export all Profiles'), id=_export_id)
                else:
                    self.Append(text=_(u'Export Profile Group'), id=_export_id)
                self._PyHocaGUI.Bind(wx.EVT_MENU, self._PyHocaGUI.OnProfileExport, id=_export_id)

        if bind_method is None and not group_name and self._PyHocaGUI.session_profiles.supports_mutable_profiles():
            _import_id = wx.NewId()
            self.AppendSeparator()
            self.Append(text=_(u'Import Session Profiles'), id=_import_id)
            self._PyHocaGUI.Bind(wx.EVT_MENU, self._PyHocaGUI.OnProfileImport, id=_import_id)

    def OnUpdateUI(self, evt):
        profile_name = self._PyHocaGUI._eventid_profilenames_map[evt.GetId()]
        if profile_name in self._PyHocaGUI._temp_disabled_profile_names:
            self._pyhoca_logger('Updating UI, temporarily disabling session profile %s' % profile_name)
            self.Enable(id=evt.GetId(), enable=False)
        elif profile_name not in self._PyHocaGUI._temp_disabled_profile_names and profile_name not in self._PyHocaGUI.client_connected_sessions(return_profile_names=True):
            self._pyhoca_logger('Updating UI, re-enabling session profile %s' % profile_name)
            self.Enable(id=evt.GetId(), enable=True)


class PyHocaGUI_Menu_TaskbarSessionManager(wx.Menu):
    """\
    Right-click menu of the L{PyHocaGUI} systray icon.

    """
    def __init__(self, _PyHocaGUI, caller=None):
        """\
        Session management menu of L{PyHocaGUI} (constructor).

        @param _PyHocaGUI: main application instance
        @type _PyHocaGUI: C{obj}
        @param caller: unused
        @type caller: C{None}

        """
        self._PyHocaGUI = _PyHocaGUI
        self._pyhoca_logger = self._PyHocaGUI._pyhoca_logger

        wx.Menu.__init__(self)

        ID_AUTHENTICATE_SESSION = wx.NewId()
        ID_AUTHENTICATE_BROKER = wx.NewId()
        ID_EXIT = wx.NewId()
        ID_DIRECT_LOGIN = wx.NewId()

        if self._PyHocaGUI.with_brokerage and not self._PyHocaGUI.session_profiles.is_broker_authenticated():
            _auth_menu_text = _(u'Connect to') + ' ' + self._PyHocaGUI.broker_name
            self.Append(id=ID_AUTHENTICATE_BROKER, text=_auth_menu_text)
            self._PyHocaGUI.Bind(wx.EVT_MENU, self._PyHocaGUI.OnBrokerAuthenticate, id=ID_AUTHENTICATE_BROKER)
            self.AppendSeparator()
        else:
            _auth_menu_text = _(u'Login')
            self.AppendMenu(id=ID_AUTHENTICATE_SESSION,
                            text=_auth_menu_text,
                            submenu=PyHocaGUI_Menu_TaskbarProfileNames(self._PyHocaGUI,
                                                                       caller=self,
                                                                       filter_profiles=[],
                                                                       disabled_profiles=self._PyHocaGUI.client_connected_profiles(return_profile_names=True) + self._PyHocaGUI._temp_disabled_profile_names,
                                                                       bind_method=self._PyHocaGUI.OnSessionAuthenticate))
            #self.AppendSeparator()

        _profile_names = self._PyHocaGUI.session_profiles.profile_names
        _profile_names.sort()

        _connected_sessions = False
        for profile_name in _profile_names:
            if profile_name in self._PyHocaGUI._X2GoClient__client_connected_sessions(return_profile_names=True):
                _connected_sessions = True
                _this_id = wx.NewId()

                _menu_profile_name = self._PyHocaGUI.show_profile_metatypes and '%s (%s)' % (profile_name, self._PyHocaGUI.get_profile_metatype(profile_name)) or profile_name
                try:
                    self.AppendMenu(text=_menu_profile_name,
                                    id=_this_id,
                                    submenu=PyHocaGUI_Menu_TaskbarSessionProfile(self._PyHocaGUI, caller=self, profile_name=profile_name))
                except x2go.x2go_exceptions.X2GoSessionRegistryException:
                    pass

        #if _connected_sessions:
        #    self.AppendSeparator()

        #self.Append(id=ID_EXIT, text=_(u"E&xit"))
        #self._PyHocaGUI.Bind(wx.EVT_MENU, self._PyHocaGUI.OnTaskbarExit, id=ID_EXIT)

