#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (C) 2010-2014 by Mike Gabriel <mike.gabriel@das-netzwerkteam.de>
# 
# PyHoca is free software; you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# PyHoca is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program; if not, write to the
# Free Software Foundation, Inc.,
# 51 Franklin St, Fifth Floor, Boston, MA 02110-1301, USA.

# import the PyHoca-GUI
import sys
import os
import platform

PROGRAM_NAME = 'App-O-Cloud'
# Windows:  UNINSTALL_NAME is for add/remove programs
UNINSTALL_NAME = 'App-O-Cloud (Cloud Apps)'
SCRIPT_NAME = 'app-o-cloud'
PROGRAM_DESC = '%s is a Cloud Application Delivery Platform.' % PROGRAM_NAME
PROGRAM_DESC_SHORT = '%s is a collection of Cloud Apps.' % PROGRAM_NAME

# silence pyflakes with assigning a dummy version here... the real __VERSION__ assignment happens below
__VERSION__ = '0.0.0.0'
for line in file(os.path.join('pyhoca', 'wxgui', '__init__.py')).readlines():
    if (line.startswith('__VERSION__')):
        exec(line.strip())
PROGRAM_VERSION = __VERSION__

PROGRAM_ICON = "pixmaps/app-o-cloud-48.ico"
# Windows:  UNINSTALL_ICON is for add/remove programs.
UNINSTALL_ICON = "icons\\app-o-cloud-32.ico"
LICENSE = 'AGPLv3+'
AUTHOR = 'App-O-Cloud Team'
PUBLISHER = 'App-O-Cloud'
URL = 'http://www.appocloud.com'
LIBRARY_ZIP = r"lib\shardlib.zip"

if platform.system() == 'Windows':
    REGULAR_NSIS = os.path.join(os.environ['ProgramFiles'], 'NSIS', 'makensis.exe')
    UNICODE_NSIS = os.path.join(os.environ['ProgramFiles'], 'NSIS','Unicode', 'makensis.exe')

from setuptools import setup
from distutils.core import Command

base = None
executables = []
if platform.system() == 'Windows':
    default_win32exe_freezer = 'bbfreeze'

    # Prefer Unicode NSIS over regular NSIS.
    # See x2goclient bug #528 for reasoning.
    # This should be reevaluated once regular NSIS 3.0 is released.
    if os.path.isfile(UNICODE_NSIS): 
        NSIS_COMPILE = UNICODE_NSIS
    else:
        NSIS_COMPILE = REGULAR_NSIS

    if 'build_with_py2exe' in (sys.argv[1], 'build_with_{freezer}'.format(freezer=default_win32exe_freezer)):
        from py2exe.build_exe import py2exe
        Freezer = object
    elif 'build_with_bbfreeze' in (sys.argv[1], 'build_with_{freezer}'.format(freezer=default_win32exe_freezer)):
        from bbfreeze import Freezer
        py2exe = object
    else:
        py2exe = object
        Freezer = object
    import os, os.path
    import subprocess
    sys.path.append(os.path.normpath('../pyhoca-contrib/mswin/ms-vc-runtime'))

elif platform.system() == 'Linux':
    import DistUtilsExtra.command.build_extra
    import DistUtilsExtra.command.build_i18n
    import DistUtilsExtra.command.clean_i18n
    py2exe = object
    Freezer = object

from glob import glob
import shutil

from nsis_template import NSIS_SCRIPT_TEMPLATE

#
# to build .exe file, run on Windows:
# ,,python setup.py py2exe''
#
# to update i18n .mo files (and merge .pot file into .po files) run on Linux:
# ,,python setup.py build_i18n -m''

cmd_class = {}
data_files = []

def datafilelist(installbase, sourcebase):
    datafileList = []
    for root, subFolders, files in os.walk(sourcebase):
        fileList = []
        for f in files:
            fileList.append(os.path.join(root, f))
        datafileList.append((root.replace(sourcebase, installbase), fileList))
    return datafileList


class NSISScript(object):

    def __init__(self, program_name, uninstall_name, program_desc, program_desc_short, program_version, publisher, url, dist_dir, icon_loc):
        self.program_name = program_name
        self.uninstall_name = uninstall_name
        self.program_desc =  program_desc
        self.program_desc_short =  program_desc_short
        self.program_version = program_version
        self.publisher = publisher
        self.url = url
        self.dist_dir = dist_dir
        self.icon_loc = icon_loc
        self.pathname = "setup_%s.nsi" % self.program_name

    def create(self):
        contents = NSIS_SCRIPT_TEMPLATE.format(
                    program_name = self.program_name,
                    uninstall_name = self.uninstall_name,
                    program_version = self.program_version,
                    program_desc = self.program_desc,
                    program_desc_short = self.program_desc_short,
                    publisher = self.publisher,
                    url = self.url,
                    output_dir = self.dist_dir,
                    icon_location = self.icon_loc
        )

        with open(self.pathname, "w") as outfile:
            outfile.write(contents)

    def compile(self):
        print NSIS_COMPILE
        print self.pathname
        subproc = subprocess.Popen(
            [NSIS_COMPILE, self.pathname], env=os.environ)
        subproc.communicate()

        retcode = subproc.returncode

        if retcode:
            raise RuntimeError("NSIS compilation return code: %d" % retcode)


class build_installer(object):

    # This class first invokes building the the exe file(s) and then creates an NSIS
    # installer
    def __init__(self, dist_dir):
        self.dist_dir = dist_dir

    def do_build_exe(self):
        # replace this method with the freezer's build_exe logic
        pass

    def run(self):

        # clean up dist_dir
        shutil.rmtree(self.dist_dir, ignore_errors=True)
        # and recreate a clean one afterwards
        os.makedirs(self.dist_dir)

        # First, build the exe file
        self.do_build_exe()

        # Create the installer, using the files py2exe has created.
        script = NSISScript(
                            PROGRAM_NAME,
                            UNINSTALL_NAME,
                            PROGRAM_DESC,
                            PROGRAM_DESC_SHORT,
                            PROGRAM_VERSION,
                            PUBLISHER,
                            URL,
                            self.dist_dir,
                            UNINSTALL_ICON
                           )
        print "*** creating the NSIS setup script***"
        script.create()
        print "*** compiling the NSIS setup script***"
        script.compile()


class build_installer_py2exe(build_installer, py2exe):

    def __init__(self, *args, **kwargs):
        py2exe.__init__(self, *args, **kwargs)
        build_installer.__init__(self, dist_dir=self.dist_dir)

    def do_build_exe(self):

        # First, let py2exe do it's work.
        py2exe.run(self)

class build_installer_bbfreeze(build_installer, Freezer, Command):

    user_options = [
        ('dist-dir=', 'd',
         "directory to put final built distributions in (default is dist)"),

        ("excludes=", 'e',
         "comma-separated list of modules to exclude"),
        ("includes=", 'i',
         "comma-separated list of modules to include"),
    ]

    def __init__(self, *args, **kwargs):
        Command.__init__(self, *args)
        build_installer.__init__(self, dist_dir=self.dist_dir)

    def initialize_options(self):
        self.includes = []
        self.excludes = []
        self.packages = []
        self.compressed = False
        self.include_py = False
        self.dist_dir = None

    def finalize_options(self):
        self.includes = fancy_split(self.includes)
        self.excludes = fancy_split(self.excludes)
        self.compressed = False
        if self.dist_dir is None:
            self.dist_dir = 'dist'
        self.dist_dir = os.path.abspath(os.path.join(os.getcwd(), self.dist_dir))
        if not os.path.exists(self.dist_dir):
            os.makedirs(self.dist_dir)


    def do_build_exe(self):
        Freezer.__init__(self, self.dist_dir,
            includes=self.includes,
            excludes=self.excludes,
        )
        self.addScript(SCRIPT_NAME, gui_only=True)
        self.setIcon('pixmaps/app-o-cloud-32.ico')
        Freezer.__call__(self)
        if self.distribution.has_data_files():
            print "*** copy data files ***"
            install_data = self.reinitialize_command('install_data')
            install_data.install_dir = self.dist_dir
            install_data.ensure_finalized()
            install_data.run()

def fancy_split(str, sep=","):
    # a split which also strips whitespace from the items
    # passing a list or tuple will return it unchanged
    if str is None:
        return []
    if hasattr(str, "split"):
        return [item.strip() for item in str.split(sep)]
    return str


if platform.system() == 'Windows':

    dll_data_files = [("Microsoft.VC90.CRT", glob(r'..\\pyhoca-contrib\\mswin\\ms-vc-runtime\\*.*'))]
    nxproxy_files = [("nxproxy", glob(r'..\\pyhoca-contrib\\mswin\\nxproxy-mswin\\nxproxy-3.5.0.27\\*.*'))]
    pulseaudio_files = [("pulseaudio", glob(r'..\\pyhoca-contrib\\mswin\\pulseaudio-mswin\\pulseaudio-5.0-rev18\\*.*'))]
    xserver_files = datafilelist('vcxsrv', r'..\\pyhoca-contrib\\mswin\\vcxsrv-mswin\\VcXsrv-xp-1.14.3.2')

    icon_files = datafilelist('icons\\App-O-Cloud', r'icons\\App-O-Cloud')
    img_files = [("img", glob(r'img\\*.*'))]
    i18n_files = datafilelist('mo', r'build\\mo')

    data_files.extend([ ('icons', ["pixmaps\\app-o-cloud-32.ico"]), ] +
                      [ ('icons', ["pixmaps\\app-o-cloud-48.ico"]), ] +
                      dll_data_files +
                      icon_files +
                      img_files +
                      nxproxy_files +
                      pulseaudio_files +
                      xserver_files +
                      i18n_files
    )

    cmd_class.update(
        {
            "build_with_py2exe": build_installer_py2exe,
            "build_with_bbfreeze": build_installer_bbfreeze,
        }
    )
    cmd_class.update({ 'build_exe': cmd_class['build_with_{freezer}'.format(freezer=default_win32exe_freezer)] })

elif platform.system() == 'Linux':
    cmd_class.update(
        {
            "build" : DistUtilsExtra.command.build_extra.build_extra,
            "build_i18n" :  DistUtilsExtra.command.build_i18n.build_i18n,
            "clean": DistUtilsExtra.command.clean_i18n.clean_i18n,
        }
    )

    icon_files = datafilelist('{prefix}/share/icons/PyHoca'.format(prefix=sys.prefix), r'icons/PyHoca')
    img_files = [("{prefix}/share/pyhoca/img".format(prefix=sys.prefix), glob('img/*.*'))]
    desktop_files = [
        ('{prefix}/share/applications'.format(prefix=sys.prefix), glob('desktop/*')),
        ('{prefix}/share/pixmaps'.format(prefix=sys.prefix), glob('pixmaps/*.svg')),
    ]
    manpage_files = [
        ('{prefix}/share/man/man1'.format(prefix=sys.prefix), glob('man/man1/*.1')),
    ]
    i18n_files = datafilelist('{prefix}/share/locale'.format(prefix=sys.prefix), 'build/mo')

    data_files.extend(icon_files +
                      img_files +
                      desktop_files +
                      manpage_files +
                      i18n_files
    )

if platform.system() == 'Windows':
    cmd_options={
        'py2exe': {
            'includes': ['greenlet', 'gevent.core', 'gevent.ares', 'gevent._semaphore', 'gevent._util', ],
            'compressed': 1,
            'optimize': 2,
        },
        'build_with_py2exe': {
            'includes': ['greenlet', 'gevent.core', 'gevent.ares', 'gevent._semaphore', 'gevent._util', ],
            'compressed': 1,
            'optimize': 2,
        },
        'build_with_bbfreeze': {
            'includes': ['hmac', 'greenlet', 'gevent.core', 'gevent.ares', 'gevent._semaphore', 'gevent._util', 'gevent.resolver_thread', 'gevent.resolver_ares', 'gevent.server', 'gevent.socket', 'gevent.threadpool', 'gevent.select', 'gevent.subprocess', 'distutils.version', 'Crypto', 'Crypto.Random', 'Crypto.Hash', 'Crypto.PublicKey', 'Crypto.PublicKey.DSA', 'Crypto.PublicKey.RSA', 'Crypto.Cipher', 'Crypto.Cipher.AES', 'Crypto.Cipher.ARC4', 'Crypto.Cipher.Blowfish', 'Crypto.Cipher.DES3', 'Crypto.Util', 'getpass', 'platform', 'uuid', 'ConfigParser', 'win32process', 'win32event', 'ctypes', 'ctypes.wintypes', 'requests', 'win32gui', ],
            'excludes': ['MSVCR90.dll', 'MSVCP90.dll', ],
        }
    }
    cmd_options.update({ 'build_exe': cmd_options['build_with_{freezer}'.format(freezer=default_win32exe_freezer)] })
else:
    cmd_options={}


if __name__ == "__main__":
    setup(
        name = PROGRAM_NAME,
        version = PROGRAM_VERSION,
        description = PROGRAM_DESC,
        license = LICENSE,
        author = AUTHOR,
        url = URL,
        namespace_packages = [ 'pyhoca', ],
        packages = [ 'pyhoca.wxgui', ],
        package_dir = {'': '.'},
        install_requires = [ 'setuptools', ],
        cmdclass = cmd_class,
        windows = [
            {
                "script": SCRIPT_NAME,
                "icon_resources": [(0, os.path.normpath(PROGRAM_ICON))],
                "dest_base": PROGRAM_NAME,
            },
        ],
        data_files = data_files,
        zipfile = LIBRARY_ZIP,
        executables = executables,
        options = cmd_options,
    )
