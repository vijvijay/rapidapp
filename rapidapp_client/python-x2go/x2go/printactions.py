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
Print jobs can either be sent to any of the local print queues (CUPS, Win32API),
be opened in an external PDF viewer, be saved to a local folder or be handed 
over to a custom (print) command. This is defined by four print action classes
(L{X2GoPrintActionDIALOG}, L{X2GoPrintActionPDFVIEW}, L{X2GoPrintActionPDFSAVE}, L{X2GoPrintActionPRINT} and 
L{X2GoPrintActionPRINTCMD}).

"""
__NAME__ = 'x2goprintactions-pylib'

# modules
import os
import shutil
import copy
import time
import gevent

from defaults import X2GOCLIENT_OS as _X2GOCLIENT_OS
if _X2GOCLIENT_OS in ("Windows"):
    import subprocess
    import win32api
    import win32print
else:
    import gevent_subprocess as subprocess
    import x2go_exceptions
    WindowsError = x2go_exceptions.WindowsError

# Python X2Go modules
import log
import defaults
# we hide the default values from epydoc (that's why we transform them to _UNDERSCORE variables)
import utils
import x2go_exceptions

_PRINT_ENV = os.environ.copy()


class X2GoPrintAction(object):

    __name__ = 'NAME'
    __description__ = 'DESCRIPTION'

    def __init__(self, client_instance=None, logger=None, loglevel=log.loglevel_DEFAULT):
        """\
        This is a meta class and has no functionality as such. It is used as parent 
        class by »real« X2Go print actions.

        @param client_instance: the underlying L{X2GoClient} instance
        @type client_instance: C{obj}
        @param logger: you can pass an L{X2GoLogger} object to the
            L{X2GoPrintAction} constructor
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

        # these get set from within the X2GoPrintQueue class
        self.profile_name = 'UNKNOWN'
        self.session_name = 'UNKNOWN'

        self.client_instance = client_instance

    @property
    def name(self):
        """\
        Return the X2Go print action's name.

        """
        return self.__name__

    @property
    def description(self):
        """\
        Return the X2Go print action's description text.

        """
        return self.__description__

    def _do_print(self, pdf_file, job_title, spool_dir, ):
        """
        Perform the defined print action (doing nothing in L{X2GoPrintAction} parent class).

        @param pdf_file: PDF file name as placed in to the X2Go spool directory
        @type pdf_file: C{str}
        @param job_title: human readable print job title
        @type job_title: C{str}
        @param spool_dir: location of the X2Go client's spool directory
        @type spool_dir: C{str}

        """
        pass

    def do_print(self, pdf_file, job_title, spool_dir, ):
        """\
        Wrap around the actual print action (C{self._do_print}) with
        gevent.spawn().

        @param pdf_file: PDF file name as placed in to the X2Go spool directory
        @type pdf_file: C{str}
        @param job_title: human readable print job title
        @type job_title: C{str}
        @param spool_dir: location of the X2Go client's spool directory
        @type spool_dir: C{str}

        """
        pdf_file = os.path.normpath(pdf_file)
        spool_dir = os.path.normpath(spool_dir)

        self._do_print(pdf_file, job_title, spool_dir)

    def _humanreadable_filename(self, pdf_file, job_title, target_path):
        """\
        Extract a human readable filename for the X2Go print job file.

        @param pdf_file: PDF file name as placed in to the X2Go spool directory
        @type pdf_file: C{str}
        @param job_title: human readable print job title
        @type job_title: C{str}
        @param target_path: target path for human readable file
        @type target_path: C{str}
        @return: full readable file name path
        @rtype: C{str}

        """
        _hr_path = os.path.normpath(os.path.expanduser(os.path.join(os.path.normpath(target_path), '%s.pdf' % utils.slugify(job_title))))
        i = 0

        while os.path.exists(_hr_path):
            i += 1
            _hr_path = os.path.normpath(os.path.expanduser(os.path.join(os.path.normpath(target_path), '%s(%s).pdf' % (utils.slugify(job_title), i))))

        return _hr_path


class X2GoPrintActionPDFVIEW(X2GoPrintAction):
    """\
    Print action that views incoming print job in an external PDF viewer application.

    """
    __name__= 'PDFVIEW'
    __decription__= 'View as PDF document'

    pdfview_cmd = None

    def __init__(self, client_instance=None, pdfview_cmd=None, logger=None, loglevel=log.loglevel_DEFAULT):
        """\
        @param client_instance: the underlying L{X2GoClient} instance
        @type client_instance: C{obj}
        @param pdfview_cmd: command that starts the external PDF viewer application
        @type pdfview_cmd: C{str}
        @param logger: you can pass an L{X2GoLogger} object to the
            L{X2GoPrintActionPDFVIEW} constructor
        @type logger: C{obj}
        @param loglevel: if no L{X2GoLogger} object has been supplied a new one will be
            constructed with the given loglevel
        @type loglevel: C{int}

        """
        if pdfview_cmd is None:
            pdfview_cmd = defaults.DEFAULT_PDFVIEW_CMD
        self.pdfview_cmd = pdfview_cmd
        X2GoPrintAction.__init__(self, client_instance=client_instance, logger=logger, loglevel=loglevel)

    def _do_print(self, pdf_file, job_title, spool_dir, ):
        """\
        Open an incoming X2Go print job (PDF file) in an external PDF viewer application.

        @param pdf_file: PDF file name as placed in to the X2Go spool directory
        @type pdf_file: C{str}
        @param job_title: human readable print job title
        @type job_title: C{str}
        @param spool_dir: location of the X2Go client's spool directory
        @type spool_dir: C{str}

        @raise OSError: pass through all C{OSError}s except no. 2

        """
        pdf_file = os.path.normpath(pdf_file)
        spool_dir = os.path.normpath(spool_dir)

        if _X2GOCLIENT_OS == "Windows":
            self.logger('viewing incoming job in PDF viewer with Python\'s os.startfile(command): %s' % pdf_file, loglevel=log.loglevel_DEBUG)
            try:
                gevent.spawn(os.startfile, pdf_file)
            except WindowsError, win_err:
                if self.client_instance:
                    self.client_instance.HOOK_printaction_error(pdf_file,
                                                                profile_name=self.profile_name,
                                                                session_name=self.session_name,
                                                                err_msg=str(win_err)
                                                               )
                else:
                    self.logger('Encountered WindowsError: %s' % str(win_err), loglevel=log.loglevel_ERROR)
            time.sleep(20)
        else:
            _hr_filename = self._humanreadable_filename(pdf_file, job_title, spool_dir, )
            shutil.copy2(pdf_file, _hr_filename)
            cmd_line = [ self.pdfview_cmd, _hr_filename, ]
            self.logger('viewing incoming PDF with command: %s' % ' '.join(cmd_line), loglevel=log.loglevel_DEBUG)
            try:
                subprocess.Popen(cmd_line, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=_PRINT_ENV)
            except OSError, e:
                if e.errno == 2:
                    cmd_line = [ defaults.DEFAULT_PDFVIEW_CMD, _hr_filename ]
                    subprocess.Popen(cmd_line, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=_PRINT_ENV)
                else:
                    raise(e)
            self.logger('waiting 20s longer before deleting the PDF file ,,%s\'\'' % _hr_filename, loglevel=log.loglevel_DEBUG)
            time.sleep(20)
            os.remove(_hr_filename)


class X2GoPrintActionPDFSAVE(X2GoPrintAction):
    """\
    Print action that saves incoming print jobs to a local folder.

    """
    __name__ = 'PDFSAVE'
    __decription__= 'Save as PDF'

    save_to_folder = None

    def __init__(self, client_instance=None, save_to_folder=None, logger=None, loglevel=log.loglevel_DEFAULT):
        """\
        @param client_instance: the underlying L{X2GoClient} instance
        @type client_instance: C{obj}
        @param save_to_folder: saving location for incoming print jobs (PDF files)
        @type save_to_folder: C{str}
        @param logger: you can pass an L{X2GoLogger} object to the
            L{X2GoPrintActionPDFSAVE} constructor
        @type logger: C{obj}
        @param loglevel: if no L{X2GoLogger} object has been supplied a new one will be
            constructed with the given loglevel
        @type loglevel: C{int}

        """
        if save_to_folder is None:
            save_to_folder = defaults.DEFAULT_PDFSAVE_LOCATION
        if not utils.is_abs_path(save_to_folder):
            if not save_to_folder.startswith('~'):
                save_to_folder = os.path.normpath('~/%s' % save_to_folder)
            save_to_folder = os.path.expanduser(save_to_folder)
        self.save_to_folder = save_to_folder

        X2GoPrintAction.__init__(self, client_instance=client_instance, logger=None, loglevel=loglevel)

        self.logger('Save location for incoming PDFs is: %s' % self.save_to_folder, loglevel=log.loglevel_DEBUG)
        if not os.path.exists(self.save_to_folder):
            os.makedirs(self.save_to_folder, mode=0755)

    def _do_print(self, pdf_file, job_title, spool_dir):
        """\
        Save an incoming X2Go print job (PDF file) to a local folder.

        @param pdf_file: PDF file name as placed in to the X2Go spool directory
        @type pdf_file: C{str}
        @param job_title: human readable print job title
        @type job_title: C{str}
        @param spool_dir: location of the X2Go client's spool directory
        @type spool_dir: C{str}

        """
        pdf_file = os.path.normpath(pdf_file)
        spool_dir = os.path.normpath(spool_dir)

        dest_file = self._humanreadable_filename(pdf_file, job_title, target_path=self.save_to_folder)
        shutil.copy2(pdf_file, dest_file)


class X2GoPrintActionPRINT(X2GoPrintAction):
    """\
    Print action that actually prints an incoming print job file.

    """
    __name__ = 'PRINT'
    __decription__= 'UNIX/Win32GDI printing'

    def __init__(self, client_instance=None, printer=None, logger=None, loglevel=log.loglevel_DEFAULT):
        """\
        @param client_instance: the underlying L{X2GoClient} instance
        @type client_instance: C{obj}
        @param printer: name of the preferred printer, if C{None} the system's/user's default printer will be used
        @type printer: C{str}
        @param logger: you can pass an L{X2GoLogger} object to the
            L{X2GoPrintActionPRINT} constructor
        @type logger: C{obj}
        @param loglevel: if no L{X2GoLogger} object has been supplied a new one will be
            constructed with the given loglevel
        @type loglevel: C{int}

        """
        self.printer = printer
        X2GoPrintAction.__init__(self, client_instance=client_instance, logger=logger, loglevel=loglevel)

    def _do_print(self, pdf_file, job_title, spool_dir, ):
        """\
        Really print an incoming X2Go print job (PDF file) to a local printer device.

        @param pdf_file: PDF file name as placed in to the X2Go spool directory
        @type pdf_file: C{str}
        @param job_title: human readable print job title
        @type job_title: C{str}
        @param spool_dir: location of the X2Go client's spool directory
        @type spool_dir: C{str}

        """
        pdf_file = os.path.normpath(pdf_file)
        spool_dir = os.path.normpath(spool_dir)

        _hr_filename = self._humanreadable_filename(pdf_file, job_title, spool_dir)
        if _X2GOCLIENT_OS == 'Windows':
            _default_printer = win32print.GetDefaultPrinter()
            if self.printer:
                _printer = self.printer
                win32print.SetDefaultPrinter(_printer)
            else:
                _printer = _default_printer
            self.logger('printing incoming PDF file %s' % pdf_file, loglevel=log.loglevel_NOTICE)
            self.logger('printer name is ,,%s\'\'' % _printer, loglevel=log.loglevel_DEBUG)
            try:
                _stdin = file('nul', 'r')
                _shell = True
                if self.client_instance:
                    _gsprint_bin = self.client_instance.client_printing.get_value('print', 'gsprint')
                    self.logger('Using gsprint.exe path from printing config file: %s' % _gsprint_bin, loglevel=log.loglevel_DEBUG)
                else:
                    _program_files = os.environ['ProgramFiles']
                    _gsprint_bin = os.path.normpath(os.path.join(_program_files, 'ghostgum', 'gsview', 'gsprint.exe',))
                    self.logger('Using hard-coded gsprint.exe path: %s' % _gsprint_bin, loglevel=log.loglevel_DEBUG)
                self.logger('Trying Ghostgum tool ,,gsprint.exe'' for printing first (full path: %s)' % _gsprint_bin, loglevel=log.loglevel_DEBUG)
                subprocess.Popen([_gsprint_bin, pdf_file, ],
                                  stdin=_stdin,
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT,
                                  shell=_shell,
                                 )
                # give gsprint.exe a little time to find our printer
                time.sleep(10)

            except:
                self.logger('Falling back to win32api printing...', loglevel=log.loglevel_DEBUG)
                try:
                    win32api.ShellExecute (
                          0,
                          "print",
                          pdf_file,
                          None,
                          ".",
                          0
                    )
                    # give the win32api some time to find our printer...
                    time.sleep(10)
                except win32api.error, e:
                    if self.client_instance:
                        self.client_instance.HOOK_printaction_error(filename=_hr_filename, printer=_printer, err_msg=e.message, profile_name=self.profile_name, session_name=self.session_name)
                    else:
                        self.logger('Encountered win32api.error: %s' % str(e), loglevel=log.loglevel_ERROR)

            if self.printer:
                win32print.SetDefaultPrinter(_default_printer)
            time.sleep(60)

        else:
            _hr_filename = self._humanreadable_filename(pdf_file, job_title, spool_dir)
            self.logger('printing incoming PDF file %s' % _hr_filename, loglevel=log.loglevel_NOTICE)
            if self.printer:
                self.logger('printer name is %s' % self.printer, loglevel=log.loglevel_DEBUG)
            else:
                self.logger('using default CUPS printer', loglevel=log.loglevel_DEBUG)
            shutil.copy2(pdf_file, _hr_filename)
            if self.printer is None:
                cmd_line = [ 'lpr',
                             '-h',
                             '-r',
                             '-J%s' % job_title, 
                             '%s' % _hr_filename,
                           ]
            else:
                cmd_line = [ 'lpr',
                             '-h',
                             '-r',
                             '-P%s' % self.printer,
                             '-J%s' % job_title, 
                             '%s' % _hr_filename,
                           ]
            self.logger('executing local print command: %s' % " ".join(cmd_line), loglevel=log.loglevel_DEBUG)
            subprocess.Popen(cmd_line, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=_PRINT_ENV)

            # this is nasty!!!!
            self.logger('waiting 20s longer before deleting the PDF file ,,%s\'\'' % _hr_filename, loglevel=log.loglevel_DEBUG)
            time.sleep(20)
            try: os.remove(_hr_filename)
            except OSError: pass


class X2GoPrintActionPRINTCMD(X2GoPrintAction):
    """\
    Print action that calls an external command for further processing of incoming print jobs.

    The print job's PDF filename will be prepended as last argument to the print command
    used in L{X2GoPrintActionPRINTCMD} instances.

    """
    __name__      = 'PRINTCMD'
    __decription__= 'Print via a command (like LPR)'

    def __init__(self, client_instance=None, print_cmd=None, logger=None, loglevel=log.loglevel_DEFAULT):
        """\
        @param client_instance: the underlying L{X2GoClient} instance
        @type client_instance: C{obj}
        @param print_cmd: external command to be called on incoming print jobs
        @type print_cmd: C{str}
        @param logger: you can pass an L{X2GoLogger} object to the
            L{X2GoPrintActionPRINTCMD} constructor
        @type logger: C{obj}
        @param loglevel: if no L{X2GoLogger} object has been supplied a new one will be
            constructed with the given loglevel
        @type loglevel: C{int}

        """
        if print_cmd is None:
            print_cmd = defaults.DEFAULT_PRINTCMD_CMD
        self.print_cmd = print_cmd
        X2GoPrintAction.__init__(self, client_instance=client_instance, logger=logger, loglevel=loglevel)

    def _do_print(self, pdf_file, job_title, spool_dir):
        """\
        Execute an external command that has been defined on construction 
        of this L{X2GoPrintActionPRINTCMD} instance.

        @param pdf_file: PDF file name as placed in to the X2Go spool directory
        @type pdf_file: C{str}
        @param job_title: human readable print job title
        @type job_title: C{str}
        @param spool_dir: location of the X2Go client's spool directory
        @type spool_dir: C{str}

        """
        pdf_file = os.path.normpath(pdf_file)
        spool_dir = os.path.normpath(spool_dir)

        _hr_filename = self._humanreadable_filename(pdf_file, job_title, spool_dir)
        shutil.copy2(pdf_file, _hr_filename)
        self.logger('executing external command ,,%s\'\' on PDF file %s' % (self.print_cmd, _hr_filename), loglevel=log.loglevel_NOTICE)
        cmd_line = self.print_cmd.split()
        cmd_line.append(_hr_filename)
        self.logger('executing external command: %s' % " ".join(cmd_line), loglevel=log.loglevel_DEBUG)
        subprocess.Popen(cmd_line, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=_PRINT_ENV)

        # this is nasty!!!!
        self.logger('waiting 20s longer before deleting the PDF file ,,%s\'\'' % _hr_filename, loglevel=log.loglevel_DEBUG)
        time.sleep(20)
        try: os.remove(_hr_filename)
        except OSError: pass


class X2GoPrintActionDIALOG(X2GoPrintAction):
    """\
    Print action that mediates opening a print dialog window. This class is rather empty,
    the actual print dialog box must be implemented in our GUI application (with the application's
    L{X2GoClient} instance.

    """
    __name__      = 'DIALOG'
    __decription__= 'Open a print dialog box'

    def __init__(self, client_instance=None, logger=None, loglevel=log.loglevel_DEFAULT):
        """\
        @param client_instance: an L{X2GoClient} instance, within your customized L{X2GoClient} make sure 
            you have a C{HOOK_open_print_dialog(filename=<str>)} method defined that will actually
            open the print dialog.
        @type client_instance: C{obj}
        @param logger: you can pass an L{X2GoLogger} object to the
            L{X2GoPrintActionDIALOG} constructor
        @type logger: C{obj}
        @param loglevel: if no L{X2GoLogger} object has been supplied a new one will be
            constructed with the given loglevel
        @type loglevel: C{int}

        @raise X2GoPrintActionException: if the client_instance has not been passed to the DIALOG print action

        """
        if client_instance is None:
            raise x2go_exceptions.X2GoPrintActionException('the DIALOG print action needs to know the X2GoClient instance (client=<instance>)')
        X2GoPrintAction.__init__(self, client_instance=client_instance, logger=logger, loglevel=loglevel)

    def _do_print(self, pdf_file, job_title, spool_dir):
        """\
        Execute an external command that has been defined on construction 
        of this L{X2GoPrintActionPRINTCMD} instance.

        @param pdf_file: PDF file name as placed in to the X2Go spool directory
        @type pdf_file: C{str}
        @param job_title: human readable print job title
        @type job_title: C{str}
        @param spool_dir: location of the X2Go client's spool directory
        @type spool_dir: C{str}

        """
        pdf_file = os.path.normpath(pdf_file)
        spool_dir = os.path.normpath(spool_dir)

        self.logger('Session %s (%s) is calling X2GoClient class hook method <client_instance>.HOOK_open_print_dialog' % (self.session_name, self.profile_name), loglevel=log.loglevel_NOTICE)
        _new_print_action = self.client_instance.HOOK_open_print_dialog(profile_name=self.profile_name, session_name=self.session_name)
        if _new_print_action and type(_new_print_action) != type(self):
            _new_print_action._do_print(pdf_file, job_title, spool_dir)
