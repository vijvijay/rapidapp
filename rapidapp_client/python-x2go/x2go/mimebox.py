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
L{X2GoMIMEboxQueue} sets up a thread that listens for incoming files that
shall be opened locally on the client.

For each file that gets dropped in the MIME box an individual 
thread is started (L{X2GoMIMEboxJob}) that handles the processing 
of the incoming file.

"""
__NAME__ = 'x2gomimeboxqueue-pylib'

# modules
import os
import copy
import types
import threading
import gevent

# Python X2Go modules
import defaults
import utils
import log
import mimeboxactions


class X2GoMIMEboxQueue(threading.Thread):
    """\
    If the X2Go MIME box is supported in a particaluar L{X2GoSession} instance
    this class provides a sub-thread for handling incoming files in the MIME box
    directory. The actual handling of a dropped file is handled by the classes
    L{X2GoMIMEboxActionOPEN}, L{X2GoMIMEboxActionOPENWITH} and L{X2GoMIMEboxActionSAVEAS}.

    """
    mimebox_action = None

    mimebox = None
    active_jobs = {}
    mimebox_history = []

    def __init__(self, profile_name='UNKNOWN', session_name='UNKNOWN', 
                       mimebox_dir=None, mimebox_action=None, mimebox_extensions=[],
                       client_instance=None, logger=None, loglevel=log.loglevel_DEFAULT):
        """\
        @param profile_name: name of the session profile this print queue belongs to
        @type profile_name: C{str}
        @param mimebox_dir: local directory for incoming MIME box files
        @type mimebox_dir: C{str}
        @param mimebox_action: name or instance of either of the possible X2Go print action classes
        @type mimebox_action: C{str} or instance
        @param client_instance: the underlying L{X2GoClient} instance
        @type client_instance: C{obj}
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
        self.mimebox_dir = mimebox_dir
        if self.mimebox_dir: self.mimebox_dir = os.path.normpath(self.mimebox_dir)
        self.mimebox_extensions = mimebox_extensions
        self.client_instance = client_instance
        self.client_rootdir = client_instance.get_client_rootdir()

        # this has to be set before we set the MIME box action...
        self._accept_jobs = False

        if mimebox_action is None:
            mimebox_action = mimeboxactions.X2GoMIMEboxActionOPEN(client_instance=self.client_instance, logger=self.logger)
        elif type(mimebox_action) in (types.StringType, types.UnicodeType):
            mimebox_action = self.set_mimebox_action(mimebox_action, client_instance=self.client_instance, logger=self.logger)
        else:
            # hope it's already an instance...
            self.mimebox_action = mimebox_action

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
        Prevent acceptance of new incoming files. The processing of MIME box jobs that 
        are currently still active will be completed, though.

        """
        if self._accept_jobs == True:
            self._accept_jobs = False
            self.logger('paused thread: %s' % repr(self), loglevel=log.loglevel_DEBUG)

    def resume(self):
        """\
        Resume operation of the X2Go MIME box queue and continue accepting new incoming 
        files.

        """
        if self._accept_jobs == False:
            self._accept_jobs = True
            self.logger('resumed thread: %s' % repr(self), loglevel=log.loglevel_DEBUG)

    def stop_thread(self):
        """\
        Stops this L{X2GoMIMEboxQueue} thread completely.

        """
        self.pause()
        self._keepalive = False
        self.logger('stopping thread: %s' % repr(self), loglevel=log.loglevel_DEBUG)

    @property
    def _incoming_mimebox_jobs(self):
        if os.path.exists(self.mimebox_dir):
            l = os.listdir(self.mimebox_dir)
            mimebox_jobs = []
            for _ext in self.mimebox_extensions:
                mimebox_jobs.extend([ dj for dj in l if dj.upper().endswith(_ext.upper()) ])
            else:
                mimebox_jobs = l
            return [ dj for dj in mimebox_jobs if dj not in self.active_jobs.keys() ]
        else:
            return []

    def set_mimebox_action(self, mimebox_action, **kwargs):
        """\
        Modify the MIME box action of this L{X2GoMIMEboxQueue} thread during runtime. The 
        change of the MIME box action will be valid for the next incoming file in the MIME box
        directory.

        @param mimebox_action: the MIME box action to execute for incoming files
        @type mimebox_action: C{str} or C{obj}
        @param kwargs: extra options for the specified MIME box action
        @type kwargs: C{dict}

        """
        if mimebox_action in defaults.X2GO_MIMEBOX_ACTIONS.keys():
            mimebox_action = defaults.X2GO_MIMEBOX_ACTIONS[mimebox_action]

        if mimebox_action in defaults.X2GO_MIMEBOX_ACTIONS.values():
            self.mimebox_action = eval ('mimeboxactions.%s(**kwargs)' % mimebox_action)

    def run(self):
        """\
        This method gets called once the L{X2GoMIMEboxQueue} thread is started by the C{X2GoMIMEboxQueue.start()} method.

        """
        self.logger('starting MIME box queue thread: %s' % repr(self), loglevel=log.loglevel_DEBUG)

        self._keepalive = True
        while self._keepalive:

            while self._accept_jobs:

                if self._incoming_mimebox_jobs:

                    for _job in self._incoming_mimebox_jobs:
                        self.logger('processing incoming X2Go MIME box job: %s' % _job, loglevel=log.loglevel_NOTICE)
                        _new_mimeboxjob_thread = X2GoMIMEboxJob(target=x2go_mimeboxjob_handler,
                                                                kwargs={ 
                                                                  'mimebox_file': _job,
                                                                  'mimebox_extensions': self.mimebox_extensions,
                                                                  'mimebox_action': self.mimebox_action,
                                                                  'parent_thread': self,
                                                                  'logger': self.logger, 
                                                                }
                                                               )
                        self.active_jobs['%s' % _job] = _new_mimeboxjob_thread
                        _new_mimeboxjob_thread.start()

                gevent.sleep(3)

            gevent.sleep(1)


def x2go_mimeboxjob_handler(mimebox_file=None, 
                            mimebox_extensions=[],
                            mimebox_action=None,
                            parent_thread=None, logger=None, ):
    """\
    This function is called as a handler function for each incoming X2Go MIME box file
    represented by the class L{X2GoMIMEboxJob}.

    @param mimebox_file: MIME box file name as placed in to the X2Go MIME box spool directory
    @type mimebox_file: C{str}
    @param mimebox_action: an instance of either of the possible C{X2GoMIMEboxActionXXX} classes
    @type mimebox_action: C{X2GoMIMEboxActionXXX} nstance
    @param parent_thread: the L{X2GoMIMEboxQueue} thread that actually created this handler's L{X2GoMIMEboxJob} instance
    @type parent_thread: C{obj}
    @param logger: the L{X2GoMIMEboxQueue}'s logging instance
    @type logger: C{obj}

    """
    mimebox_action.profile_name = parent_thread.profile_name
    mimebox_action.session_name = parent_thread.session_name

    logger('action for printing is: %s' % mimebox_action, loglevel=log.loglevel_DEBUG)

    _dotfile = mimebox_file.startswith('.')
    _blacklisted = mimebox_file.upper().split('.')[-1] in defaults.X2GO_MIMEBOX_EXTENSIONS_BLACKLIST
    _really_process = bool(not _blacklisted  and ((not mimebox_extensions) or [ ext for ext in mimebox_extensions if mimebox_file.upper().endswith('%s' % ext.upper()) ]))
    if _really_process and not _blacklisted and not _dotfile:
        mimebox_action.do_process(mimebox_file=mimebox_file,
                                  mimebox_dir=parent_thread.mimebox_dir,
                                 )
    elif not _blacklisted and not _dotfile:
        logger('file extension of MIME box file %s is prohibited by session profile configuration' % mimebox_file, loglevel=log.loglevel_NOTICE)
    elif _dotfile:
        logger('placing files starting with a dot (.<file>) into the X2Go MIME box is prohibited, ignoring the file ,,%s\'\'' % mimebox_file, loglevel=log.loglevel_WARN)
    else:
        logger('file extension of MIME box file %s has been found in Python X2Go\' hardcoded MIME box extenstions blacklist' % mimebox_file, loglevel=log.loglevel_WARN)

    logger('removing MIME box file %s' % mimebox_file, loglevel=log.loglevel_DEBUG)

    utils.patiently_remove_file(parent_thread.mimebox_dir, mimebox_file)
    logger('removed print job file %s' % mimebox_file, loglevel=log.loglevel_DEBUG)

    del parent_thread.active_jobs['%s' % mimebox_file]
    parent_thread.mimebox_history.append(mimebox_file)
    # in case we do a lot of mimebox file exports we do not want to risk an
    # endlessly growing mimebox job history
    if len(parent_thread.mimebox_history) > 100:
        parent_thread.mimebox_history = parent_thread.mimebox_history[-100:]


class X2GoMIMEboxJob(threading.Thread):
    """\
    For each X2Go MIME box job we create a sub-thread that let's 
    the MIME box job be processed in the background.

    As a handler for this class the function L{x2go_mimeboxjob_handler()} 
    is used.

    """
    def __init__(self, **kwargs):
        """\
        Construct the X2Go MIME box job thread...

        All parameters (**kwargs) are passed through to the constructor
        of C{threading.Thread()}.

        """
        threading.Thread.__init__(self, **kwargs)
        self.daemon = True
