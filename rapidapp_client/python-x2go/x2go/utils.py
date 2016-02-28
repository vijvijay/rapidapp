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
Python X2Go helper functions, constants etc.

"""
__NAME__ = 'x2goutils-pylib'

import sys
import os
import locale
import re
import types
import copy
import socket
import gevent
import string
import subprocess
import distutils.version
import paramiko

# Python X2Go modules
from defaults import X2GOCLIENT_OS as _X2GOCLIENT_OS
from defaults import X2GO_SESSIONPROFILE_DEFAULTS as _X2GO_SESSIONPROFILE_DEFAULTS
from defaults import X2GO_MIMEBOX_ACTIONS as _X2GO_MIMEBOX_ACTIONS
from defaults import pack_methods_nx3

from defaults import BACKENDS as _BACKENDS

import x2go_exceptions

if _X2GOCLIENT_OS != 'Windows':
    import Xlib
    from defaults import X_DISPLAY as _X_DISPLAY

if _X2GOCLIENT_OS == 'Windows':
    import win32gui
    import win32print
    import win32con

def is_in_nx3packmethods(method):

    """\
    Test if a given compression method is valid for NX3 Proxy.

    @return: C{True} if C{method} is in the hard-coded list of NX3 compression methods.
    @rtype: C{bool}

    """
    return method in pack_methods_nx3


def find_session_line_in_x2golistsessions(session_name, stdout):
    """\
    Return the X2Go session meta information as returned by the 
    C{x2golistsessions} server command for session C{session_name}.

    @param session_name: name of a session
    @type session_name: C{str}
    @param stdout: raw output from the ,,x2golistsessions'' command, as list of strings
    @type stdout: C{list}

    @return: the output line that contains C{<session_name>}
    @rtype: C{str} or C{None}

    """
    sessions = stdout.read().split("\n")
    for line in sessions:
        # skip empty lines
        if not line:
            continue
        if session_name == line.split("|")[1]:
            return line
    return None


def slugify(value):
    """\
    Normalizes string, converts to lowercase, removes non-alpha characters,
    converts spaces to hyphens and replaces round brackets by pointed brackets.

    @param value: a string that shall be sluggified
    @type value: C{str}

    @return: the sluggified string
    @rtype: C{str}

    """
    import unicodedata
    value = unicodedata.normalize('NFKD', unicode(value)).encode('ascii', 'ignore')
    value = re.sub('[^\w\s-]', '', value).strip().lower()
    value = re.sub('[(]', '<', value).strip().lower()
    value = re.sub('[)]', '>', value).strip().lower()
    return value

def _genSessionProfileId():
    """\
    Generate a session profile ID as used in x2goclient's sessions config file.

    @return: profile ID
    @rtype: C{str}

    """
    import datetime
    return datetime.datetime.utcnow().strftime('%Y%m%d%H%m%S%f')


def _checkIniFileDefaults(data_structure):
    """\
    Check an ini file data structure passed on by a user app or class.

    @param data_structure: an ini file date structure
    @type data_structure: C{dict} of C{dict}s

    @return: C{True} if C{data_structure} matches that of an ini file data structure
    @rtype: C{bool}

    """
    if data_structure is None:
        return False
    if type(data_structure) is not types.DictType:
        return False
    for sub_dict in data_structure.values():
        if type(sub_dict) is not types.DictType:
            return False
    return True


def _checkSessionProfileDefaults(data_structure):
    """\
    Check the data structure of a default session profile passed by a user app.

    @param data_structure: an ini file date structure
    @type data_structure: C{dict} of C{dict}s

    @return: C{True} if C{data_structure} matches that of an ini file data structure
    @rtype: C{bool}

    """
    if data_structure is None:
        return False
    if type(data_structure) is not types.DictType:
        return False
    return True


def _convert_SessionProfileOptions_2_SessionParams(options):
    """\
    Convert session profile options as used in x2goclient's sessions file to
    Python X2Go session parameters.

    @param options: a dictionary of options, parameter names as in the X2Go ,,sessions'' file
    @type options: C{dict}

    @return: session options as used in C{X2GoSession} instances
    @rtype: C{dict}

    """
    _params = copy.deepcopy(options)

    # get rid of unknown session profile options
    _known_options = _X2GO_SESSIONPROFILE_DEFAULTS.keys()
    for p in _params.keys():
        if p not in _known_options:
            del _params[p]

    _rename_dict = {
            'host': 'server',
            'user': 'username',
            'soundsystem': 'snd_system',
            'sndport': 'snd_port',
            'type': 'kbtype',
            'layout': 'kblayout',
            'variant': 'kbvariant',
            'speed': 'link',
            'sshport': 'port',
            'useexports': 'allow_share_local_folders',
            'restoreexports': 'restore_shared_local_folders',
            'usemimebox': 'allow_mimebox',
            'mimeboxextensions': 'mimebox_extensions',
            'mimeboxaction': 'mimebox_action',
            'print': 'printing',
            'name': 'profile_name',
            'key': 'key_filename',
            'command': 'cmd',
            'rdpserver': 'rdp_server',
            'rdpoptions': 'rdp_options',
            'xdmcpserver': 'xdmcp_server',
            'useiconv': 'convert_encoding',
            'iconvto': 'server_encoding',
            'iconvfrom': 'client_encoding',
            'usesshproxy': 'use_sshproxy',
            'sshproxyhost': 'sshproxy_host',
            'sshproxyport': 'sshproxy_port',
            'sshproxyuser': 'sshproxy_user',
            'sshproxykeyfile': 'sshproxy_key_filename',
            'sessiontitle': 'session_title',
            'setsessiontitle': 'set_session_title',
            'published': 'published_applications',
            'autostart': 'auto_start_or_resume',
            'autoconnect': 'auto_connect',
            'forwardsshagent': 'forward_sshagent',
            'autologin': 'look_for_keys',
            'sshproxyautologin': 'sshproxy_look_for_keys',
            'uniquehostkeyaliases': 'unique_hostkey_aliases',
    }
    _speed_dict = {
            '0': 'modem',
            '1': 'isdn',
            '2': 'adsl',
            '3': 'wan',
            '4': 'lan',
    }

    for opt, val in options.iteritems():

        # rename options if necessary
        if opt in _rename_dict.keys():
            del _params[opt]
            opt = _rename_dict[opt]
            if opt in _known_options:
                _type = type(_known_options[opt])
                _params[opt] = _type(val)
            else:
                _params[opt] = val

        # translate integer values for connection speed to readable strings
        if opt == 'link':
            val = str(val).lower()
            if val in _speed_dict.keys():
                val = _speed_dict[val]
            val = val.lower()
            _params['link'] = val

        # share_local_folders is a list
        if opt in ('share_local_folders', 'mimebox_extensions'):
            if type(val) is types.StringType:
                if val:
                    _params[opt] = val.split(',')
                else:
                    _params[opt] = []

    if _params['cmd'] == "XFCE4": _params['cmd'] = "XFCE"
    if _params['look_for_keys']:
        _params['allow_agent'] = True
    if _params['sshproxy_look_for_keys']:
        _params['sshproxy_allow_agent'] = True

    # append value for quality to value for pack method
    if _params['quality']:
        _params['pack'] = '%s-%s' % (_params['pack'], _params['quality'])
    # delete quality in any case...
    del _params['quality']

    del _params['fstunnel']

    if _params.has_key('export'):

        _export = _params['export']
        del _params['export']
        if type(_export) is types.DictType:

            # since Python X2Go 0.5.0.0
            _params['share_local_folders'] = _export.keys()

        else:

            # before Python X2Go 0.5.0.0 (analysing the INI file's format for the export field)

            # fix for wrong export field usage in PyHoca-GUI/CLI and python-x2go before 20110923
            _export = _export.replace(",", ";")

            _export = _export.strip().strip('"').strip().strip(';').strip()
            _export_list = [ f for f in _export.split(';') if f ]

            _params['share_local_folders'] = []
            for _shared_folder in _export_list:
                # fix for wrong export field usage in PyHoca-GUI/CLI and python-x2go before 20110923
                if not ":" in _shared_folder: _shared_folder = "%s:1" % _shared_folder
                if _shared_folder.split(":")[-1] == "1":
                    _params['share_local_folders'].append(":".join(_shared_folder.split(":")[:-1]))

    if options['fullscreen']:
        _params['geometry'] = 'fullscreen'
    elif options['maxdim']:
        _params['geometry'] = 'maximize'
    else:
        _params['geometry'] = '%sx%s' % (options['width'], options['height'])
    del _params['width']
    del _params['height']
    del _params['fullscreen']
    del _params['maxdim']

    if not options['sound']:
        _params['snd_system'] = 'none'
    del _params['sound']

    if not options['rootless']:
        _params['session_type'] = 'desktop'
    else:
        _params['session_type'] = 'application'
    del _params['rootless']

    if _params['mimebox_action'] not in _X2GO_MIMEBOX_ACTIONS.keys():
        _params['mimebox_action'] = 'OPEN'

    if not options['usekbd']:
        _params['kbtype'] = 'null/null'
        _params['kblayout'] = 'null'
        _params['kbvariant'] = 'null'
    del _params['usekbd']

    if not _params['kbtype'].strip(): _params['kbtype'] = 'null/null'
    if not _params['kblayout'].strip(): _params['kblayout'] = 'null'
    if not _params['kbvariant'].strip(): _params['kbvariant'] = 'null'

    if not options['setdpi']:
        del _params['dpi']
    del _params['setdpi']

    if options['sshproxysameuser']:
        _params['sshproxy_user'] = _params['username']
    del _params['sshproxysameuser']
    if options['sshproxysamepass']:
        _params['sshproxy_reuse_authinfo'] = True
        _params['sshproxy_key_filename'] = _params['key_filename']
    del _params['sshproxysamepass']

    if _params['use_sshproxy']:

        # compat code for Python X2Go 0.2.1.0 -> 0.2.2.0
        if options.has_key('sshproxytunnel'):
            if not options['sshproxytunnel'].startswith('DEPRECATED'):
                _params['server'] = options['sshproxytunnel'].split(":")[-2]
                _params['port'] = options['sshproxytunnel'].split(":")[-1]
            try: del _params['sshproxytunnel']
            except KeyError: pass


    # currently known but ignored in Python X2Go
    _ignored_options = [
            'startsoundsystem',
            'soundtunnel',
            'defsndport',
            'icon',
            'xinerama',
            'multidisp',
            'display',
            'krblogin',
            'directrdp',
            'directrdpsettings',
            'rdpclient',
            'rdpport',
            'sshproxytype',
    ]
    for i in _ignored_options:
        del _params[i]

    return _params


def session_names_by_timestamp(session_infos):
    """\
    Sorts session profile names by their timestamp (as used in the file format's section name).

    @param session_infos: a dictionary of session infos as reported by L{X2GoClient.list_sessions()}
    @type session_infos: C{dict}

    @return: a timestamp-sorted list of session names found in C{session_infos}
    @rtype: C{list}

    """
    session_names = session_infos.keys()
    sortable_session_names = [ '%s|%s' % (session_name.split('-')[-1].split('_')[0], session_name) for session_name in session_names ]
    sortable_session_names.sort()
    return [ session_name.split('|')[1] for session_name in sortable_session_names ]


def touch_file(filename, mode='a'):
    """\
    Imitates the behaviour of the GNU/touch command.

    @param filename: name of the file to touch
    @type filename: C{str}
    @param mode: the file mode (as used for Python file objects)
    @type mode: C{str}

    """
    if not os.path.isdir(os.path.dirname(filename)):
        os.makedirs(os.path.dirname(filename), mode=00700)
    f = open(filename, mode=mode)
    f.close()


def unique(seq):
    """\
    Imitates the behaviour of the GNU/uniq command.

    @param seq: a list/sequence containing consecutive duplicates.
    @type seq: C{list}

    @return: list that has been clean up from the consecutive duplicates
    @rtype: C{list}

    """
    # order preserving
    noDupes = []
    [noDupes.append(i) for i in seq if not noDupes.count(i)]
    return noDupes


def known_encodings():
    """\
    Render a list of all-known-to-Python character encodings (including 
    all known aliases)

    """
    from encodings.aliases import aliases
    _raw_encname_list = []
    _raw_encname_list.extend(aliases.keys())
    _raw_encname_list.extend(aliases.values())
    _raw_encname_list.sort()
    _encname_list = []
    for _raw_encname in _raw_encname_list:
        _encname = _raw_encname.upper()
        _encname = _encname.replace('_', '-')
        _encname_list.append(_encname)
    _encname_list.sort()
    _encname_list = unique(_encname_list)
    return _encname_list


def patiently_remove_file(dirname, filename):
    """\
    Try to remove a file, wait for unlocking, remove it once removing is possible...

    @param dirname: directory name the file is in
    @type dirname: C{str}
    @param filename: name of the file to be removed
    @type filename: C{str}

    """
    _not_removed = True
    while _not_removed:
        try:
            os.remove(os.path.join(dirname, filename))
            _not_removed = False
        except:
            # file is probably locked
            gevent.sleep(5)


def detect_unused_port(bind_address='127.0.0.1', preferred_port=None):
    """\
    Detect an unused IP socket.

    @param bind_address: IP address to bind to
    @type bind_address: C{str}
    @param preferred_port: IP socket port that shall be tried first for availability
    @type preferred_port: C{str}

    @return: free local IP socket port that can be used for binding
    @rtype: C{str}

    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
    try:
        if preferred_port:
            sock.bind((bind_address, preferred_port))
            ipaddr, port = sock.getsockname()
        else:
            raise
    except:
        sock.bind(('', 0))
        ipaddr, port = sock.getsockname()
    return port


def get_encoding():
    """\
    Detect systems default character encoding.

    @return: The system's local character encoding.
    @rtype: C{str}

    """
    try:
        encoding = locale.getdefaultlocale()[1]
        if encoding is None:
            raise BaseException
    except:
        try:
            encoding = sys.getdefaultencoding()
        except:
            encoding = 'ascii'
    return encoding


def is_abs_path(path):
    """\
    Test if a given path is an absolute path name.

    @param path: test this path for absolutism...
    @type path: C{str}

    @return: Returns C{True} if path is an absolute path name
    @rtype: C{bool}

    """
    return bool((path.startswith('/') or re.match('^[%s]\:\\\\' % string.ascii_letters, path)))


def xkb_rules_names():
    """\
    Wrapper for: xprop -root _XKB_RULES_NAMES

    @return: A Python dictionary that contains the current X11 keyboard rules.
    @rtype: C{dict}

    """
    p = subprocess.Popen(['xprop', '-root', '_XKB_RULES_NAMES',], stdout=subprocess.PIPE, )
    _rn_list = p.stdout.read().split('"')
    _rn_dict = {
        'rules': _rn_list[1],
        'model': _rn_list[3],
        'layout': _rn_list[5],
        'variant': _rn_list[7],
        'options': _rn_list[9],
    }
    return _rn_dict

def local_color_depth():
    """\
    Detect the current local screen's color depth.

    @return: the local color depth in bits
    @rtype: C{int}

    """
    if _X2GOCLIENT_OS != 'Windows':
        try:
            p = subprocess.Popen(['xwininfo', '-root',], stdout=subprocess.PIPE, )
            _depth_line = [ _info.strip() for _info in p.stdout.read().split('\n') if 'Depth:' in _info ][0]
            _depth = _depth_line.split(' ')[1]
            return int(_depth)
        except IndexError:
            # a sensible default value
            return 24
        except OSError:
            # for building your package...
            return 24

    else:
        # This gets the color depth of the primary monitor. All monitors need not have the same color depth.
        dc = win32gui.GetDC(None)
        _depth = win32print.GetDeviceCaps(dc, win32con.BITSPIXEL) * win32print.GetDeviceCaps(dc, win32con.PLANES)
        win32gui.ReleaseDC(None, dc)
        return _depth

def is_color_depth_ok(depth_session, depth_local):
    """\
    Test if color depth of this session is compatible with the
    local screen's color depth.

    @param depth_session: color depth of the session
    @type depth_session: C{int}
    @param depth_local: color depth of local screen
    @type depth_local: C{int}

    @return: Does the session color depth work with the local display?
    @rtype: C{bool}

    """
    if depth_session == 0:
        return True
    if depth_session == depth_local:
        return True
    if ( ( depth_session == 24 or depth_session == 32 ) and ( depth_local == 24 or depth_local == 32 ) ):
        return True;
    if ( ( depth_session == 16 or depth_session == 17 ) and ( depth_local == 16 or depth_local == 17 ) ):
        return True;
    return False


def find_session_window(session_name):
    """\
    Find a session window by its X2GO session ID.

    @param session_name: session name/ID of an X2Go session window
    @type session_name: C{str}

    @return: the window object (or ID) of the searched for session window
    @rtype: C{obj} on Unix, C{int} on Windows

    """
    if _X2GOCLIENT_OS != 'Windows':
        # establish connection to the win API in use...
        display = _X_DISPLAY
        if display:
            root = display.screen().root

            success = False
            windowIDs_obj = root.get_full_property(display.intern_atom('_NET_CLIENT_LIST'), Xlib.X.AnyPropertyType)

            if windowIDs_obj is None:
                # works with i3 session manager...
                windowIDs_obj = root.get_full_property(display.intern_atom('_NET_CLIENT_LIST_STACKING'), Xlib.X.AnyPropertyType)

            if windowIDs_obj is not None:
                windowIDs = windowIDs_obj.value

                for windowID in windowIDs:
                    window = display.create_resource_object('window', windowID)
                    try:
                        name = window.get_wm_name()
                    except Xlib.error.BadWindow:
                        continue
                    if name is not None and "X2GO-{session_name}".format(session_name=session_name) == name:
                        success = True
                        break

            if success:
                return window

    else:

        windows = []
        window = None

        def _callback(hwnd, extra):
            if win32gui.GetWindowText(hwnd) == "X2GO-%s" % session_name:
                windows.append(hwnd)

        win32gui.EnumWindows(_callback, None)
        if len(windows): window = windows[0]

        return window


def get_desktop_geometry():
    """\
    Get the geometry of the current screen's desktop.

    @return: a (<width>, <height>) tuple will be returned
    @rtype: C{tuple}

    """
    if _X2GOCLIENT_OS != 'Windows':
        display = _X_DISPLAY
        if display:
            root = display.screen().root
            return (root.get_geometry().width, root.get_geometry().height)

    return None

def get_workarea_geometry():
    """\
    Get the geometry of the current screen's work area by
    wrapping around::

        xprop -root '_NET_WORKAREA'

    @return: a (<width>, <height>) tuple will be returned
    @rtype: C{tuple}

    """
    if _X2GOCLIENT_OS != 'Windows':
        p = subprocess.Popen(['xprop', '-root', '_NET_WORKAREA',], stdout=subprocess.PIPE, )
        _list = p.stdout.read().rstrip('\n').split(',')
        if len(_list) == 4:
            return (_list[2].strip(), _list[3].strip())
        else:
            return None
    else:

        return None


def set_session_window_title(session_window, session_title):
    """\
    Set title of session window.

    @param session_window: session window instance
    @type session_window: C{obj}
    @param session_title: session title to be set for C{session_window}
    @type session_title: C{str}

    """
    if _X2GOCLIENT_OS != 'Windows':
        try:
            session_window.set_wm_name(str(session_title))
            session_window.set_wm_icon_name(str(session_title))
            _X_DISPLAY.sync()
        except Xlib.error.BadWindow:
            pass

    else:
        win32gui.SetWindowText(session_window, session_title)


def raise_session_window(session_window):
    """\
    Raise session window. Not functional for Unix-like operating systems.

    @param session_window: session window instance
    @type session_window: C{obj}

    """
    if _X2GOCLIENT_OS != 'Windows':
        pass
    else:
        if session_window is not None:
            win32gui.SetForegroundWindow(session_window)


def merge_ordered_lists(l1, l2):
    """\
    Merge sort two sorted lists

    @param l1: first sorted list
    @type l1: C{list}
    @param l2: second sorted list
    @type l2: C{list}

    @return: the merge result of both sorted lists
    @rtype: C{list}

    """
    ordered_list = []

    # Copy both the args to make sure the original lists are not
    # modified
    l1 = l1[:]
    l2 = l2[:]

    while (l1 and l2):
        if l1[0] not in l2:
            item = l1.pop(0)
        elif l2[0] not in l1:
            item = l2.pop(0)
        elif l1[0] in l2:
            item = l1.pop(0)
            l2.remove(item)
        if item not in ordered_list:
            ordered_list.append(item)

    # Add the remaining of the lists
    ordered_list.extend(l1 if l1 else l2)

    return ordered_list

def compare_versions(version_a, op, version_b):
    """\
    Compare <version_a> with <version_b> using operator <op>.
    In the background C{distutils.version.LooseVersion} is
    used for the comparison operation.

    @param version_a: a version string
    @type version_a: C{str}
    @param op: an operator provide as string (e.g. '<', '>', '==', '>=' etc.)
    @type op: C{str}
    @param version_b: another version string that is to be compared with <version_a>
    @type version_b: C{str}

    """

    ### FIXME: this comparison is not reliable with beta et al. version strings

    ver_a = distutils.version.LooseVersion(version_a)
    ver_b = distutils.version.LooseVersion(version_b)

    return eval("ver_a %s ver_b" % op)

class ProgressStatus(object):
    """\
    A simple progress status iterator class.

    """
    def __init__(self, progress_event, progress_func=range(0, 100, 10)):
        """\
        @param progress_event: a threading.Event() object that gets notified on progress
        @type progress_event: C{obj}
        @param progress_func: a function that delivers a value between 0 and 100 (progress percentage value)
        @type progress_func: C{func}

        """
        self.ev = progress_event
        self.progress_func = progress_func

    def __iter__(self):
        """\
        Intialize the L{ProgressStatus} iterator object.

        """
        self.status = self.progress_func()
        return self

    def next(self):
        """\
        On each iteration wait for the progress event to get triggered from an outside
        part of the application.

        Once the event fires read the progress status from the progress retrieval function
        and clear the event afterwards (so we wait for the next firing of the event).

        """
        if self.status < 100 and self.status != -1:
            self.ev.wait()
            self.status = self.progress_func()
            self.ev.clear()
            return self.status
        else:
            raise StopIteration

def _get_backend_class(backend, class_name):
    # silence pyflakes, the _this_class var will be assigned in an exec() statement below...
    _this_class = None
    if type(backend) not in (types.StringType, types.UnicodeType): return backend
    backend = backend.upper()
    available_backends = [ k for k in _BACKENDS[class_name].keys() if k != 'default' ]
    # if for backend is given 'default' use the default backend module
    if backend == 'default': backend = _BACKENDS[class_name]['default']
    if backend in available_backends:
        exec("from {backend} import {class_name} as _this_class".format(backend=_BACKENDS[class_name][backend], class_name=class_name))
    else:
        raise x2go_exceptions.X2GoBackendException('unknown backend name %s for class %s' % (backend, class_name))
    return _this_class

def genkeypair(local_username, client_address, key_type='RSA'):
    """\
    Generate an SSH pub/priv key pair without writing the private key to file.

    @param local_username: the key is for this user
    @type local_username: C{unicode}
    @param client_address: the key is only valid for this client
    @type client_address: C{unicode}
    @param key_type: either of: RSA, DSA
    @type key_type: C{unicode}

    """
    key = None
    pubkey = None

    # generate key pair
    if unicode(key_type) == u'RSA':
        key = paramiko.RSAKey.generate(2048)
    elif unicode(key_type) == u'DSA':
        key = paramiko.DSSKey.generate(1024)

    if key:

        # assemble the public key
        if key_type == "RSA":
            pubkey_type = 'ssh-rsa'
        elif key_type == "DSA":
            pubkey_type = 'ssh-dss'

        # FIXME: the from option does not work properly by some reason. Fix it later
        #pubkey = "from={client_address},no-X11-forwarding,no-pty,no-user-rc {pubkey_type} {pubkey} {local_username}@{client_address}".format(pubkey=key.get_base64(), pubkey_type=pubkey_type, local_username=local_username, client_address=client_address)
        pubkey = "no-X11-forwarding,no-pty,no-user-rc {pubkey_type} {pubkey} {local_username}@{client_address}".format(pubkey=key.get_base64(), pubkey_type=pubkey_type, local_username=local_username, client_address=client_address)

    return (pubkey, key)


def which(basename):
    """\
    Python equivalent to the shell command "which".

    @param basename: the basename of an application to be search for in $PATH
    @type basename: C{str}

    @return: full path to the application
    @rtype: C{str}

    """
    if _X2GOCLIENT_OS == 'Windows':
        delim = ";"
    else:
        delim = ":"

    for path in os.environ["PATH"].split(delim):
        if os.path.exists(os.path.join(path, basename)):
                return os.path.join(path, basename)

    return None
