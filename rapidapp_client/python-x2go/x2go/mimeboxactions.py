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
For MIME box jobs there are currently three handling actions available:
L{X2GoMIMEboxActionOPEN}, L{X2GoMIMEboxActionOPENWITH} and L{X2GoMIMEboxActionSAVEAS}.

"""
__NAME__ = 'x2gomimeboxactions-pylib'

# modules
import os
import copy
import time

from defaults import X2GOCLIENT_OS as _X2GOCLIENT_OS
if _X2GOCLIENT_OS in ("Windows"):
    import subprocess
    import win32api
else:
    import gevent_subprocess as subprocess
    import x2go_exceptions
    WindowsErrror = x2go_exceptions.WindowsError

# Python X2Go modules
import log
import x2go_exceptions

_MIMEBOX_ENV = os.environ.copy()


class X2GoMIMEboxAction(object):

    __name__ = 'NAME'
    __description__ = 'DESCRIPTION'

    def __init__(self, client_instance=None, logger=None, loglevel=log.loglevel_DEFAULT):
        """\
        This is a meta class and has no functionality as such. It is used as parent
        class by »real« X2Go MIME box actions.

        @param client_instance: the underlying L{X2GoClient} instance
        @type client_instance: C{obj}
        @param logger: you can pass an L{X2GoLogger} object to the
            L{X2GoMIMEboxAction} constructor
        @type logger: C{obj}
        @param loglevel: if no L{X2GoLogger} object has been supplied a new one will be
            constructed with the given loglevel
        @type loglevel: C{int}

        """
        if logger is None:
            self.logger = log.X2GoLogger(loglevel=loglevel)
        else:
            self.logger = copy.deepcopy(logger)
        self.logger.tag = __NAME__

        # these get set from within the X2GoMIMEboxQueue class
        self.profile_name = 'UNKNOWN'
        self.session_name = 'UNKNOWN'

        self.client_instance = client_instance

    @property
    def name(self):
        """\
        Return the X2Go MIME box action's name.

        """
        return self.__name__

    @property
    def description(self):
        """\
        Return the X2Go MIME box action's description text.

        """
        return self.__description__

    def _do_process(self, mimebox_file, mimebox_dir, ):
        """\
        Perform the defined MIME box action (doing nothing in L{X2GoMIMEboxAction} parent class).

        @param mimebox_file: file name as placed in to the X2Go MIME box directory
        @type mimebox_file: C{str}
        @param mimebox_dir: location of the X2Go session's MIME box directory
        @type mimebox_dir: C{str}

        """
        pass

    def do_process(self, mimebox_file, mimebox_dir, ):
        """\
        Wrapper method for the actual processing of MIME
        box actions.

        @param mimebox_file: file name as placed in to the X2Go MIME box directory
        @type mimebox_file: C{str}
        @param mimebox_dir: location of the X2Go session's MIME box directory
        @type mimebox_dir: C{str}

        """
        mimebox_file = os.path.normpath(mimebox_file)
        mimebox_dir = os.path.normpath(mimebox_dir)

        self._do_process(mimebox_file, mimebox_dir)


class X2GoMIMEboxActionOPEN(X2GoMIMEboxAction):
    """\
    MIME box action that opens incoming files in the system's default application.

    """
    __name__= 'OPEN'
    __decription__= 'Open incoming file with local system\'s default application.'

    def __init__(self, client_instance=None, logger=None, loglevel=log.loglevel_DEFAULT):
        """\
        @param client_instance: the underlying L{X2GoClient} instance
        @type client_instance: C{obj}
        @param logger: you can pass an L{X2GoLogger} object to the
            L{X2GoMIMEboxActionOPEN} constructor
        @type logger: C{obj}
        @param loglevel: if no L{X2GoLogger} object has been supplied a new one will be
            constructed with the given loglevel
        @type loglevel: C{int}

        """
        self.client_instance = client_instance
        X2GoMIMEboxAction.__init__(self, logger=logger, loglevel=loglevel)

    def _do_process(self, mimebox_file, mimebox_dir, ):
        """\
        Open an incoming MIME box file in the system's default application.

        @param mimebox_file: file name as placed in to the MIME box directory
        @type mimebox_file: C{str}
        @param mimebox_dir: location of the X2Go session's MIME box directory
        @type mimebox_dir: C{str}

        """
        mimebox_file = os.path.normpath(mimebox_file)
        mimebox_dir = os.path.normpath(mimebox_dir)

        if _X2GOCLIENT_OS == "Windows":
            self.logger('opening incoming MIME box file with Python\'s os.startfile() command: %s' % mimebox_file, loglevel=log.loglevel_DEBUG)
            try:
                os.startfile(os.path.join(mimebox_dir, mimebox_file))
            except WindowsError, win_err:
                if self.client_instance:
                    self.client_instance.HOOK_mimeboxaction_error(mimebox_file,
                                                                  profile_name=self.profile_name,
                                                                  session_name=self.session_name,
                                                                  err_msg=str(win_err)
                                                                 )
                else:
                    self.logger('Encountered WindowsError: %s' % str(win_err), loglevel=log.loglevel_ERROR)
            time.sleep(20)
        else:
            cmd_line = [ 'xdg-open', os.path.join(mimebox_dir, mimebox_file), ]
            self.logger('opening MIME box file with command: %s' % ' '.join(cmd_line), loglevel=log.loglevel_DEBUG)
            subprocess.Popen(cmd_line, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=_MIMEBOX_ENV)
            time.sleep(20)


class X2GoMIMEboxActionOPENWITH(X2GoMIMEboxAction):
    """\
    MIME box action that calls the system's ,,Open with...'' dialog on incoming files. Currently only
    properly implementable on Windows platforms.

    """
    __name__= 'OPENWITH'
    __decription__= 'Evoke ,,Open with...\'\' dialog on incoming MIME box files.'

    def __init__(self, client_instance=None, logger=None, loglevel=log.loglevel_DEFAULT):
        """\
        @param client_instance: the underlying L{X2GoClient} instance
        @type client_instance: C{obj}
        @param logger: you can pass an L{X2GoLogger} object to the
            L{X2GoMIMEboxActionOPENWITH} constructor
        @type logger: C{obj}
        @param loglevel: if no L{X2GoLogger} object has been supplied a new one will be
            constructed with the given loglevel
        @type loglevel: C{int}

        """
        self.client_instance = client_instance
        X2GoMIMEboxAction.__init__(self, logger=logger, loglevel=loglevel)

    def _do_process(self, mimebox_file, mimebox_dir, ):
        """\
        Open an incoming MIME box file in the system's default application.

        @param mimebox_file: file name as placed in to the MIME box directory
        @type mimebox_file: C{str}
        @param mimebox_dir: location of the X2Go session's MIME box directory
        @type mimebox_dir: C{str}

        """
        mimebox_file = os.path.normpath(mimebox_file)
        mimebox_dir = os.path.normpath(mimebox_dir)

        if _X2GOCLIENT_OS == "Windows":
            self.logger('evoking Open-with dialog on incoming MIME box file: %s' % mimebox_file, loglevel=log.loglevel_DEBUG)
            win32api.ShellExecute (
                  0,
                  "open",
                  "rundll32.exe",
                  "shell32.dll,OpenAs_RunDLL %s" % os.path.join(mimebox_dir, mimebox_file),
                  None,
                  0,
            )
            time.sleep(20)
        else:
            self.logger('the evocation of the Open-with dialog box is currently not available on Linux, falling back to MIME box action OPEN', loglevel=log.loglevel_WARN)
            cmd_line = [ 'xdg-open', os.path.join(mimebox_dir, mimebox_file), ]
            self.logger('opening MIME box file with command: %s' % ' '.join(cmd_line), loglevel=log.loglevel_DEBUG)
            subprocess.Popen(cmd_line, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=_MIMEBOX_ENV)
            time.sleep(20)


class X2GoMIMEboxActionSAVEAS(X2GoMIMEboxAction):
    """\
    MIME box action that allows saving incoming MIME box files to a local folder. What this 
    MIME box actually does is calling a hook method in the L{X2GoClient} instance that
    can be hi-jacked by one of your application's methods which then can handle the ,,Save as...''
    request.

    """
    __name__ = 'SAVEAS'
    __decription__= 'Save incoming file as...'

    def __init__(self, client_instance=None, logger=None, loglevel=log.loglevel_DEFAULT):
        """\
        @param client_instance: an L{X2GoClient} instance, within your customized L{X2GoClient} make sure 
            you have a C{HOOK_open_mimebox_saveas_dialog(filename=<str>)} method defined that will actually
            handle the incoming mimebox file.
        @type client_instance: C{obj}
        @param logger: you can pass an L{X2GoLogger} object to the
            L{X2GoMIMEboxActionSAVEAS} constructor
        @type logger: C{obj}
        @param loglevel: if no L{X2GoLogger} object has been supplied a new one will be
            constructed with the given loglevel
        @type loglevel: C{int}

        @raise X2GoMIMEboxActionException: if the client_instance has not been passed to the SAVEAS MIME box action

        """
        if client_instance is None:
            raise x2go_exceptions.X2GoMIMEboxActionException('the SAVEAS MIME box action needs to know the X2GoClient instance (client=<instance>)')
        X2GoMIMEboxAction.__init__(self, client_instance=client_instance, logger=logger, loglevel=loglevel)

    def _do_process(self, mimebox_file, mimebox_dir):
        """\
        Call an L{X2GoClient} hook method (C{HOOK_open_mimebox_saveas_dialog}) that
        can handle the MIME box's SAVEAS action.

        @param mimebox_file: file name as placed in to the MIME box directory
        @type mimebox_file: C{str}
        @param mimebox_dir: location of the X2Go session's MIME box directory
        @type mimebox_dir: C{str}
        @param mimebox_file: PDF file name as placed in to the X2Go spool directory

        """
        mimebox_file = os.path.normpath(mimebox_file)
        mimebox_dir = os.path.normpath(mimebox_dir)

        self.logger('Session %s (%s) is calling X2GoClient class hook method <client_instance>.HOOK_open_mimebox_saveas_dialog(%s)' % (self.session_name, self.profile_name, mimebox_file), loglevel=log.loglevel_NOTICE)
        self.client_instance.HOOK_open_mimebox_saveas_dialog(os.path.join(mimebox_dir, mimebox_file), profile_name=self.profile_name, session_name=self.session_name)
        time.sleep(60)

