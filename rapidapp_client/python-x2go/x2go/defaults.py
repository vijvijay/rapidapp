# -*- coding: utf-8 -*-

# Copyright (C) 2010-2014 by Mike Gabriel <mike.gabriel@das-netzwerkteam.de>
#
# Python X2Go is free software; you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# Python X2Go is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program; if not, write to the
# Free Software Foundation, Inc.,
# 51 Franklin St, Fifth Floor, Boston, MA 02110-1301, USA.

"""\
Default variables and values for Python X2Go.

"""
__NAME__ = 'x2godefaults-pylib'

import os
import paramiko
import platform

##
## Common X2Go defaults
##

X2GOCLIENT_OS = platform.system()

if X2GOCLIENT_OS != 'Windows':
    import Xlib.display
    import Xlib.error

    # handle missing X displays on package build
    try:
        X_DISPLAY = Xlib.display.Display()
    except Xlib.error.DisplayNameError:
        X_DISPLAY = None
    except Xlib.error.DisplayConnectionError:
        X_DISPLAY = None

LOCAL_HOME = os.path.normpath(os.path.expanduser('~'))
X2GO_SESSIONS_ROOTDIR = '.apprime'
X2GO_CLIENT_ROOTDIR = '.apprime'
X2GO_SSH_ROOTDIR = os.path.join('.apprime','.ssh')

# setting OS dependent variables
if X2GOCLIENT_OS == "Windows":
    # on Windows we will use the current directory as ,,ROOTDIR'' which 
    # will normally be the application directory
    ROOT_DIR = os.path.abspath(os.path.curdir)
    ETC_DIR = os.path.join(ROOT_DIR, 'etc')
    import win32api
    CURRENT_LOCAL_USER = win32api.GetUserName()
    #X2GO_SSH_ROOTDIR = '.ssh'
    X2GO_SSH_ROOTDIR = os.path.join('.apprime','.ssh')
    SUPPORTED_SOUND = True
    SUPPORTED_PRINTING = True
    SUPPORTED_FOLDERSHARING = True
    SUPPORTED_MIMEBOX = True
    SUPPORTED_TELEKINESIS = False

elif X2GOCLIENT_OS == "Linux":
    ROOT_DIR = '/'
    ETC_DIR = os.path.join(ROOT_DIR, 'etc', 'x2goclient')
    import getpass
    CURRENT_LOCAL_USER = getpass.getuser()
    X2GO_SSH_ROOTDIR = '.ssh'
    SUPPORTED_SOUND = True
    SUPPORTED_PRINTING = True
    SUPPORTED_FOLDERSHARING = True
    SUPPORTED_MIMEBOX = True
    SUPPORTED_TELEKINESIS = True

elif X2GOCLIENT_OS == "Mac":
    ROOT_DIR = '/'
    ETC_DIR = os.path.join(ROOT_DIR, 'etc', 'x2goclient')
    import getpass
    CURRENT_LOCAL_USER = getpass.getuser()
    X2GO_SSH_ROOTDIR = '.ssh'
    SUPPORTED_SOUND = True
    SUPPORTED_PRINTING = True
    SUPPORTED_FOLDERSHARING = True
    SUPPORTED_MIMEBOX = True
    SUPPORTED_TELEKINESIS = False

else:
    import exceptions
    class OSNotSupportedException(exceptions.StandardError): pass
    raise OSNotSupportedException('Platform %s is not supported' % platform.system())

##
## backends of Python X2Go
##

BACKENDS = {
    'X2GoControlSession': {
        'default': 'PLAIN',
        'PLAIN': 'x2go.backends.control.plain',
    },
    'X2GoTerminalSession': {
        'default': 'PLAIN',
        'PLAIN': 'x2go.backends.terminal.plain',
    },
    'X2GoServerSessionInfo': {
        'default': 'PLAIN',
        'PLAIN': 'x2go.backends.info.plain',
    },
    'X2GoServerSessionList': {
        'default': 'PLAIN',
        'PLAIN': 'x2go.backends.info.plain',
    },
    'X2GoProxy': {
        'default': 'NX3',
        'NX3': 'x2go.backends.proxy.nx3',
    },
    'X2GoSessionProfiles': {
        'default': 'FILE',
        'FILE': 'x2go.backends.profiles.file',
        'GCONF': 'x2go.backends.profiles.gconf',
        'HTTPBROKER': 'x2go.backends.profiles.httpbroker',
        'SSHBROKER': 'x2go.backends.profiles.sshbroker',
        'WINREG': 'x2go.backends.profiles.winreg',
    },
    'X2GoClientSettings': {
        'default': 'FILE',
        'FILE': 'x2go.backends.settings.file',
        'GCONF': 'x2go.backends.settings.gconf',
        'WINREG': 'x2go.backends.settings.winreg',
    },
    'X2GoClientPrinting': {
        'default': 'FILE',
        'FILE': 'x2go.backends.printing.file',
        'GCONF': 'x2go.backends.printing.gconf',
        'WINREG': 'x2go.backends.printing.winreg',
    }
}

##
## X2Go Printing
##

X2GO_SETTINGS_FILENAME = 'settings'
X2GO_SETTINGS_CONFIGFILES = [
    os.path.normpath(os.path.join(LOCAL_HOME, X2GO_CLIENT_ROOTDIR, 'settings')),
    os.path.normpath(os.path.join(ETC_DIR,X2GO_SETTINGS_FILENAME)),
]
X2GO_PRINTING_FILENAME = 'printing'
X2GO_PRINTING_CONFIGFILES = [
    os.path.normpath(os.path.join(LOCAL_HOME, X2GO_CLIENT_ROOTDIR, 'printing')),
    os.path.normpath(os.path.join(ETC_DIR,X2GO_PRINTING_FILENAME)),
]
X2GO_SESSIONPROFILES_FILENAME = 'sessions'
X2GO_SESSIONPROFILES_CONFIGFILES = [
    os.path.normpath(os.path.join(LOCAL_HOME, X2GO_CLIENT_ROOTDIR, 'sessions')),
    os.path.normpath(os.path.join(ETC_DIR,X2GO_SESSIONPROFILES_FILENAME)),
]
X2GO_XCONFIG_FILENAME = 'xconfig'
X2GO_XCONFIG_CONFIGFILES = [
    os.path.normpath(os.path.join(LOCAL_HOME, X2GO_CLIENT_ROOTDIR, 'xconfig')),
    os.path.normpath(os.path.join(ETC_DIR,X2GO_XCONFIG_FILENAME)),
]

X2GO_CLIENTSETTINGS_DEFAULTS = {
    'LDAP': {
        'useldap': False,
        'port': 389,
        'server': 'localhost',
        'port1': 0,
        'port2': 0,
    },
    'General': {
        # clientport is not needed for Python X2Go
        'clientport': 22, 
        'autoresume': True,
    },
    'Authorization': {
        'newprofile': True,
        'suspend': True,
        'editprofile': True,
        'resume': True
    },
    'trayicon': {
        'enabled': True,
        'mintotray': True,
        'noclose': True,
        'mincon': True,
        'maxdiscon': True,
    },
}
X2GO_CLIENTPRINTING_DEFAULTS = {
    'General': {
        # showdialog will result in a print action that allows opening a print dialog box
        'showdialog': False,
        # if true, open a PDF viewer (or save as PDF file). If false, print via CUPS or print command
        'pdfview': True,
    },
    'print': {
        # If false, print via CUPS. If true, run "command" to process the print job
        'startcmd': False,
        # print command for non-CUPS printing
        'command': 'lpr',
        # ignored in Python X2Go
        'stdin': False,
        # ignored in Python X2Go
        'ps': False,
    },
    'save': {
        # a path relative to the user's home directory
        'folder': 'PDF',
    },
    'view': {
        # If General->pdfview is true: 
        #   if open is true, the PDF viewer command is executed
        #   if open is false, the incoming print job is saved in ~/PDF folder 
        'open': True,
        # command to execute as PDF viewer
        'command': 'xdg-open',
    },
    'CUPS': {
        # default print queue for CUPS, if print queue does not exist, the default 
        # CUPS queue is detected
        'defaultprinter': 'PDF',
    },
}
if X2GOCLIENT_OS == 'Windows':
    X2GO_CLIENTPRINTING_DEFAULTS['print'].update({'gsprint': os.path.join(os.environ['ProgramFiles'], 'GhostGum', 'gsview', 'gsprint.exe'), })


if X2GOCLIENT_OS == 'Windows':
    X2GO_CLIENTXCONFIG_DEFAULTS = {
        'XServers': {
            'known_xservers': ['VcXsrv_development', 'VcXsrv_shipped', 'VcXsrv', 'Xming', 'Cygwin-X', ],
        },
        'Cygwin-X': {
            'display': 'localhost:40',
            'last_display': 'localhost:40',
            'process_name': 'XWin.exe',
            'test_installed': os.path.join(os.environ['SystemDrive'], '\\', 'cygwin', 'bin', 'XWin.exe'),
            'run_command': os.path.join(os.environ['SystemDrive'], '\\', 'cygwin', 'bin', 'XWin.exe'),
            'parameters': [':40', '-clipboard', '-multiwindow', '-notrayicon', '-nowinkill', '-nounixkill', '-swcursor', ],
        },
        'VcXsrv': {
            'display': 'localhost:40',
            'last_display': 'localhost:40',
            'process_name': 'vcxsrv.exe',
            'test_installed': os.path.join(os.environ['ProgramFiles'], 'VcXsrv', 'vcxsrv.exe'), 
            'run_command': os.path.join(os.environ['ProgramFiles'], 'VcXsrv', 'vcxsrv.exe'),
            'parameters': [':40', '-clipboard', '-multiwindow', '-notrayicon', '-nowinkill', '-nounixkill', '-swcursor', ],
        },
        'VcXsrv_shipped': {
            'display': 'localhost:40',
            'last_display': 'localhost:40',
            'process_name': 'vcxsrv.exe',
            'test_installed': os.path.join(os.getcwd(), 'VcXsrv', 'vcxsrv.exe'), 
            'run_command': os.path.join(os.getcwd(), 'VcXsrv', 'vcxsrv.exe'),
            'parameters': [':40', '-clipboard', '-multiwindow', '-notrayicon', '-nowinkill', '-nounixkill', '-swcursor', ],
        },
        'VcXsrv_development': {
            'display': 'localhost:40',
            'last_display': 'localhost:40',
            'process_name': 'vcxsrv.exe',
            'test_installed': os.path.join(os.getcwd(), '..', 'pyhoca-contrib', 'mswin', 'vcxsrv-mswin', 'VcXsrv-xp-1.14.3.2', 'vcxsrv.exe'), 
            'run_command': os.path.join(os.getcwd(), '..', 'pyhoca-contrib', 'mswin', 'vcxsrv-mswin', 'VcXsrv-xp-1.14.3.2', 'vcxsrv.exe'), 
            'parameters': [':40', '-clipboard', '-multiwindow', '-notrayicon', '-nowinkill', '-nounixkill', '-swcursor', ],
        },
        'Xming': {
            'display': 'localhost:40',
            'last_display': 'localhost:40',
            'process_name': 'Xming.exe',
            'test_installed': os.path.join(os.environ['ProgramFiles'], 'Xming', 'Xming.exe'), 
            'run_command': os.path.join(os.environ['ProgramFiles'], 'Xming', 'Xming.exe'),
            'parameters': [':40', '-clipboard', '-multiwindow', '-notrayicon', '-nowinkill', '-nounixkill', '-swcursor', ],
        },
    }
else:
    # make the variable available when building API documentation with epydoc
    X2GO_CLIENTXCONFIG_DEFAULTS = {}

X2GO_GENERIC_APPLICATIONS = [ 'WWWBROWSER', 'MAILCLIENT', 'OFFICE', 'TERMINAL', ]
"""X2Go's generic applications."""

X2GO_SESSIONPROFILE_DEFAULTS = {
    'autologin': True, 'autoconnect': False, 'autostart': False, 'setsessiontitle': False, 'sessiontitle': "",
    'speed': 2, 'pack': '16m-jpeg', 'quality': 9,
    'iconvto': 'UTF-8', 'iconvfrom': 'UTF-8', 'useiconv': False,
    'usesshproxy': False, 'sshproxyhost': 'proxyhost.mydomain', 'sshproxyport': 22, 'sshproxyuser': '', 'sshproxykeyfile': '',
    'sshproxytype': 'SSH', 'sshproxysameuser': False, 'sshproxysamepass': False, 'sshproxyautologin': True,
    'uniquehostkeyaliases': False,
    'useexports': True, 'restoreexports': False, 'fstunnel': True, 'export': {},
    'usemimebox': False, 'mimeboxextensions': '', 'mimeboxaction': 'OPEN',
    'fullscreen': False, 'clipboard': 'both',
    'width': 800,'height': 600, 'maxdim': False, 'dpi': 96, 'setdpi': False, 'xinerama': False, 'multidisp': False, 'display': 1,
    'usekbd': True, 'layout': 'us', 'type': 'pc105/us', 'variant': '',
    'sound': False, 'soundsystem': 'pulse', 'startsoundsystem': False, 'soundtunnel':True, 'defsndport':True, 'sndport':4713,
    'name': 'NEW_PROFILE', 'icon': ':icons/128x128/x2gosession.png',
    'host': ['server.mydomain'], 'user': CURRENT_LOCAL_USER, 'key': '', 'sshport': 22, 'krblogin': False, 'forwardsshagent': False,
    'rootless': True, 'applications': X2GO_GENERIC_APPLICATIONS, 'command':'TERMINAL', 'published': False,
    'directrdp': False, 'directrdpsettings': '', 'rdpclient': 'rdesktop', 'rdpport': 3389,
    'rdpoptions': '-u X2GO_USER -p X2GO_PASSWORD', 'rdpserver': '',
    'print': False,
    'xdmcpserver': 'localhost',
}
"""L{X2GoSessionProfiles} default values to fill a new session profile with."""
##
## X2Go Proxy defaults
##

# here is a list of NX 3.x compression methods, this is the "%"-hashed list that
# can also be used for printing in help texts, docs etc.
# The "%"-sign can be replaced by digits 0-9.
pack_methods_nx3_noqual  = ['nopack','8','64','256','512','4k','32k','64k','256k','2m','16m',
                            '256-rdp','256-rdp-compressed','32k-rdp','32k-rdp-compressed','64k-rdp',
                            '64k-rdp-compressed','16m-rdp','16m-rdp-compressed',
                            'rfb-hextile','rfb-tight','rfb-tight-compressed',
                            '8-tight','64-tight','256-tight','512-tight','4k-tight','32k-tight',
                            '64k-tight','256k-tight','2m-tight','16m-tight',
                            '8-jpeg-%','64-jpeg','256-jpeg','512-jpeg','4k-jpeg','32k-jpeg',
                            '64k-jpeg','256k-jpeg','2m-jpeg','16m-jpeg-%',
                            '8-png-jpeg-%','64-png-jpeg','256-png-jpeg','512-png-jpeg','4k-png-jpeg',
                            '32k-png-jpeg','64k-png-jpeg','256k-png-jpeg','2m-png-jpeg','16m-png-jpeg-%',
                            '8-png-%','64-png','256-png','512-png','4k-png',
                            '32k-png','64k-png','256k-png','2m-png','16m-png-%',
                            '16m-rgb-%','16m-rle-%',]
"""Available NX3 compression methods."""

# use for printing on screen...
pack_methods_nx3_formatted="""
    \'%s\'
    \'%s\'
    \'%s\'
    \'%s\'
    \'%s\'
    \'%s\'
    \'%s\'
    \'%s\'
    \'%s\'
    \'%s\'
    \'%s\'
    \'%s\'
    \'%s\'
""" % ('\', \''.join(pack_methods_nx3_noqual[0:11]), \
           '\', \''.join(pack_methods_nx3_noqual[11:16]), \
           '\', \''.join(pack_methods_nx3_noqual[16:19]), \
           '\', \''.join(pack_methods_nx3_noqual[19:22]), \
           '\', \''.join(pack_methods_nx3_noqual[22:28]), \
           '\', \''.join(pack_methods_nx3_noqual[28:32]), \
           '\', \''.join(pack_methods_nx3_noqual[32:38]), \
           '\', \''.join(pack_methods_nx3_noqual[38:42]), \
           '\', \''.join(pack_methods_nx3_noqual[42:47]), \
           '\', \''.join(pack_methods_nx3_noqual[47:52]), \
           '\', \''.join(pack_methods_nx3_noqual[52:57]), \
           '\', \''.join(pack_methods_nx3_noqual[57:62]), \
           '\', \''.join(pack_methods_nx3_noqual[62:]))

# pack_methods_nx3 is the complete list of NX3 pack methods that can be used to check options 
# against
pack_methods_nx3 = [ m for m in pack_methods_nx3_noqual if "%" not in m ]
for meth in [ m for m in pack_methods_nx3_noqual if "%" in m ]:
    pack_methods_nx3 += [ meth.replace('%','%s' % str(i)) for i in range(0,10) ]
pack_methods_nx3.sort()
##
## X2Go session defaults
##

X2GO_DESKTOPSESSIONS={
    'CINNAMON': 'cinnamon',
    'KDE': 'startkde',
    'GNOME': 'gnome-session',
    'MATE': 'mate-session',
    'XFCE': 'xfce4-session',
    'LXDE': 'startlxde',
    'TRINITY': 'starttrinity',
    'UNITY': 'unity',
}
"""A dictionary with meta-commands for X2Go's window manager sessions."""

##
## X2Go SFTP server defaults
##

RSAKEY_STRENGTH = 1024
RSAHostKey = paramiko.RSAKey.generate(RSAKEY_STRENGTH)
"""\
An RSA host key for this client session. Python X2Go does not use the
system's host key but generates its own host key for each running
application instance.

"""

X2GO_PRINT_ACTIONS = {
    'PDFVIEW': 'X2GoPrintActionPDFVIEW',
    'PDFSAVE': 'X2GoPrintActionPDFSAVE',
    'PRINT': 'X2GoPrintActionPRINT',
    'PRINTCMD': 'X2GoPrintActionPRINTCMD',
    'DIALOG': 'X2GoPrintActionDIALOG',
}
"""Relating print action names and classes."""

DEFAULT_PDFVIEW_CMD = 'xdg-open'
"""Default PDF viewer command for Linux systems (PDFVIEW print action)."""
DEFAULT_PDFSAVE_LOCATION = 'PDF'
"""Default location for saving PDF files (PDFSAVE print action)."""
DEFAULT_PRINTCMD_CMD = 'lpr'
"""Default command for the PRINTCMD print action."""

X2GO_MIMEBOX_ACTIONS = {
    'OPEN': 'X2GoMIMEboxActionOPEN',
    'OPENWITH': 'X2GoMIMEboxActionOPENWITH',
    'SAVEAS': 'X2GoMIMEboxActionSAVEAS',
}
"""Relating MIME box action names and classes."""

X2GO_MIMEBOX_EXTENSIONS_BLACKLIST = [
    'LOCK', 'SYS', 'SWP', 
    'EXE', 'COM', 'CMD', 'PS1', 'PS2', 'BAT',
    'JS', 'PY', 'PL', 'SH',
]
"""Black-listed MIME box file extenstions."""

# X2Go desktop sharing
X2GO_SHARE_VIEWONLY=0
"""Constant representing read-only access to shared desktops."""
X2GO_SHARE_FULLACCESS=1
"""Constant representing read-write (full) access to shared desktops."""

PUBAPP_MAX_NO_SUBMENUS=10
"""Less than ten applications will not get rendered into submenus."""
