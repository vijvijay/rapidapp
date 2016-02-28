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
L{X2GoPrintQueue} sets up a thread that listens for incoming print jobs.

For each incoming print job in an X2Go session's spool directory an 
individual thread is started (L{X2GoPrintJob}) that handles the processing 
of the incoming print job.

"""
__NAME__ = 'x2goprintqueue-pylib'

# modules
import os
import copy
import threading
import gevent

# Python X2Go modules
import defaults
import utils
import log

from defaults import X2GO_PRINTING_FILENAME as _X2GO_PRINTING_FILENAME
from defaults import BACKENDS as _BACKENDS

class X2GoPrintQueue(threading.Thread):
    """\
    If X2Go printing is supported in a particular L{X2GoSession} instance
    this class provides a sub-thread for handling incoming X2Go print jobs.

    """
    print_action = None

    spooldir = None
    active_jobs = {}
    job_history = []

    def __init__(self, 
                 profile_name='UNKNOWN',
                 session_name='UNKNOWN',
                 spool_dir=None,
                 print_action=None,
                 print_action_args={},
                 client_instance=None,
                 printing_backend=_BACKENDS['X2GoClientPrinting']['default'],
                 logger=None,
                 loglevel=log.loglevel_DEFAULT):
        """\
        @param profile_name: name of the session profile this print queue belongs to
        @type profile_name: C{str}
        @param spool_dir: local spool directory for incoming print job files
        @type spool_dir: C{str}
        @param print_action: name or instance of either of the possible X2Go print action classes
        @type print_action: C{str} or instance
        @param print_action_args: depending of the chosen C{print_action} this dictionary may contain different
            values; the C{print_action_args} will be passed on to the X2Go print action instance constructor, so 
            refer to either of these: L{X2GoPrintActionPDFVIEW}, L{X2GoPrintActionPRINT} et al.
        @param client_instance: the underlying L{X2GoClient} instance
        @type client_instance: C{obj}
        @param printing_backend: the client printing configuration backend class
        @type printing_backend: C{obj}
        @param logger: you can pass an L{X2GoLogger} object to the
            L{X2GoPrintQueue} constructor
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

        self.profile_name = profile_name
        self.session_name = session_name
        self.spool_dir = spool_dir
        if self.spool_dir: self.spool_dir = os.path.normpath(self.spool_dir)
        self.client_instance = client_instance
        self.client_rootdir = client_instance.get_client_rootdir()
        self.printing_backend = utils._get_backend_class(printing_backend, "X2GoClientPrinting")
        if print_action is not None:
            self.set_print_action(print_action, client_instance=self.client_instance, logger=logger, **print_action_args)
        threading.Thread.__init__(self)
        self.daemon = True
        self._accept_jobs = True

    def __del__(self):
        """\
        Class destructor.

        """
        self.stop_thread()

    def pause(self):
        """\
        Prevent acceptance of new incoming print jobs. The processing of print jobs that 
        are currently still active will be completed, though.

        """
        if self._accept_jobs == True:
            self._accept_jobs = False
            self.logger('paused thread: %s' % repr(self), loglevel=log.loglevel_DEBUG)

    def resume(self):
        """\
        Resume operation of the X2Go print spooler and continue accepting new incoming 
        print jobs.

        """
        if self._accept_jobs == False:
            self._accept_jobs = True
            self.logger('resumed thread: %s' % repr(self), loglevel=log.loglevel_DEBUG)

    def stop_thread(self):
        """\
        Stops this L{X2GoPrintQueue} thread completely.

        """
        self.pause()
        self._keepalive = False
        self.logger('stopping thread: %s' % repr(self), loglevel=log.loglevel_DEBUG)

    @property
    def _incoming_print_jobs(self):

        if os.path.exists(self.spool_dir):
            l = os.listdir(self.spool_dir)
            job_files = [ jf for jf in l if jf.endswith('.ready') ]
            jobs = []
            for _job_file in job_files:
                _job_file_handle = open(os.path.join(self.spool_dir, _job_file), 'r')
                content = _job_file_handle.read()
                try:
                    (pdf_filename, job_title) = content.split('\n')[0:2]
                except ValueError:
                    pdf_filename = content
                    job_title = 'X2Go Print Job'
                _job_file_handle.close()
                jobs.append((_job_file, pdf_filename, job_title))
            return [ j for j in jobs if j[1] not in self.active_jobs.keys() ]
        else:
            return []

    def set_print_action(self, print_action, **kwargs):
        """\
        Modify the print action of this L{X2GoPrintQueue} thread during runtime. The 
        change of print action will be valid for the next incoming print job.

        As kwargs you can pass arguments for the print action class to be set. Refer
        to the class descriptions of L{X2GoPrintActionDIALOG}, L{X2GoPrintActionPDFVIEW},
        L{X2GoPrintActionPRINT}, etc.

        @param print_action: new print action to be valid for incoming print jobs
        @type print_action: C{str} or C{class}
        @param kwargs: extra options for the specified print action
        @type kwargs: C{dict}

        """
        if print_action in defaults.X2GO_PRINT_ACTIONS.keys():
            print_action = defaults.X2GO_PRINT_ACTIONS[print_action]

        if print_action in defaults.X2GO_PRINT_ACTIONS.values():
            self.print_action = eval ('printactions.%s(**kwargs)' % print_action)

    def run(self):
        """\
        Start this L{X2GoPrintQueue} thread...

        """
        self.logger('starting print queue thread: %s' % repr(self), loglevel=log.loglevel_DEBUG)

        self._keepalive = True
        while self._keepalive:

            while self._accept_jobs:

                if self._incoming_print_jobs:

                    for _job in self._incoming_print_jobs:
                        self.logger('processing incoming X2Go print job: %s' % _job[1], loglevel=log.loglevel_NOTICE)
                        _new_printjob_thread = X2GoPrintJob(target=x2go_printjob_handler,
                                                            kwargs={ 
                                                            'job_file': _job[0],
                                                            'pdf_file': _job[1],
                                                            'job_title': _job[2],
                                                            'print_action': self.print_action,
                                                            'parent_thread': self, 
                                                            'logger': self.logger, 
                                                          }
                                                  )
                        self.active_jobs['%s' % _job[1]] = _new_printjob_thread
                        _new_printjob_thread.start()

                gevent.sleep(3)

            gevent.sleep(1)


def x2go_printjob_handler(job_file=None, pdf_file=None, job_title=None, print_action=None, parent_thread=None, logger=None, ):
    """\
    This function is called as a handler function for each incoming X2Go print job 
    represented by the class L{X2GoPrintJob}.

    The handler function will (re-)read the »printing« configuration file (if no
    explicit C{print_action} is passed to this function...). It then will
    execute the C{<print_action>.do_print()} command.

    @param pdf_file: PDF file name as placed in to the X2Go spool directory
    @type pdf_file: C{str}
    @param job_title: human readable print job title
    @type job_title: C{str}
    @param print_action: an instance of either of the possible C{X2GoPrintActionXXX} classes
    @type print_action: C{X2GoPrintActionXXX} nstance
    @param parent_thread: the L{X2GoPrintQueue} thread that actually created this handler's L{X2GoPrintJob} instance
    @type parent_thread: C{obj}
    @param logger: the L{X2GoPrintQueue}'s logging instance
    @type logger: C{obj}

    """
    if print_action is None:
        if parent_thread.client_instance is not None and parent_thread.client_instance.has_custom_client_rootdir:
            _printing = parent_thread.printing_backend(config_files=[os.path.join(parent_thread.client_instance.get_client_rootdir(), _X2GO_PRINTING_FILENAME)],
                                                       client_instance=parent_thread.client_instance, 
                                                       logger=logger
                                                      )
        else:
            _printing = parent_thread.printing_backend(client_instance=parent_thread.client_instance, 
                                                       logger=logger
                                                      )

        print_action = _printing.print_action
    print_action.profile_name = parent_thread.profile_name
    print_action.session_name = parent_thread.session_name

    logger('action for printing is: %s' % print_action, loglevel=log.loglevel_DEBUG)
    print_action.do_print(pdf_file=os.path.normpath(os.path.join(parent_thread.spool_dir, pdf_file)),
                          job_title=job_title,
                          spool_dir=parent_thread.spool_dir,
                         )

    logger('removing print job files for %s' % pdf_file, loglevel=log.loglevel_DEBUG)

    utils.patiently_remove_file(parent_thread.spool_dir, job_file)
    logger('removed print job file %s' % job_file, loglevel=log.loglevel_DEBUG)
    utils.patiently_remove_file(parent_thread.spool_dir, pdf_file)
    logger('removed print pdf file %s' % pdf_file, loglevel=log.loglevel_DEBUG)

    del parent_thread.active_jobs['%s' % pdf_file]
    parent_thread.job_history.append(pdf_file)

    # in case we print a lot we do not want to risk an endlessly growing 
    # print job history
    if len(parent_thread.job_history) > 100:
        parent_thread.job_history = parent_thread.job_history[-100:]


class X2GoPrintJob(threading.Thread):
    """\
    For each X2Go print job we create a sub-thread that let's 
    the print job be processed in the background.

    As a handler for this class the function L{x2go_printjob_handler()} 
    is used.

    """
    def __init__(self, **kwargs):
        """\
        Construct the X2Go print job thread...

        All parameters (**kwargs) are passed through to the constructor
        of C{threading.Thread()}.

        """
        threading.Thread.__init__(self, **kwargs)
        self.daemon = True
