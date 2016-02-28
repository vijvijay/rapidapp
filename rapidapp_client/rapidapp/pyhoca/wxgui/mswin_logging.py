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

import sys
import os

def setup_mswinlog(PROG_NAME):
    if hasattr(sys, 'frozen') and str(sys.frozen) in ("windows_exe", "console_exe", "1", ):
        class MSWin_Logging(object):

            softspace = 0
            _fname = os.path.normpath(os.path.join(os.environ['AppData'], PROG_NAME, '%s.%s.log' % (PROG_NAME, os.getpid())))
            _file = None

            def __init__(self, filemode='a'):
                try:
                    os.mkdir(os.path.dirname(self._fname))
                except:
                    pass
                self._filemode = filemode
                if self._filemode == "w+":
                    for _file in os.listdir(os.path.dirname(self._fname)):
                        try:
                            os.remove(os.path.join(os.path.dirname(self._fname), _file))
                        except WindowsError:
                            pass

            def write(self, text, **kwargs):
                if self._file is None:
                    try:
                        try:
                            os.mkdir(os.path.dirname(self._fname))
                        except:
                            pass
                        self._file = open(self._fname, self._filemode)
                    except:
                        pass
                else:
                    self._file.write(text)
                    self._file.flush()

            def flush(self):
                if self._file is not None:
                    self._file.flush()

        sys.stdout = MSWin_Logging(filemode='w+')
        sys.stderr = MSWin_Logging(filemode='a')
        del MSWin_Logging
