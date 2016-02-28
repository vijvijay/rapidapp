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
Python X2Go is a python module that implements X2Go client support for 
the free X2Go server project (U{http://wiki.x2go.org}) in Python.

Introduction
============
    With Python X2Go you can write your own X2Go clients or embed X2Go client
    features into already existing application environments.

    NOTE: Beginning with v0.4.0.0 of Python X2Go all class names start with
    X2Go***. Earlier versions used X2go***. As X2Go is the official name of the
    project (i.e. with a capital X and a capital G) we have adapted the class
    names to this circumstance.

API Concept
===========

    Python X2Go consists of quite a few classes. Furthermore,
    Python X2Go is quite heavily taking advantage of Python\'s
    threading features. When providing a library like Python
    X2Go, it is always quite a task to keep the library code
    compatible with former versions of the same library. This is
    intended for Python X2Go, but with some restraints.

    Python X2Go only offers five public API classes. With the release of
    version 0.1.0.0, we will try to keep these five public API classes
    of future releases as compatible as possible with versions of Python X2Go
    greater/equal than v0.1.0.0.

    The five public API classes are:

        - L{X2GoClient} --- a whole X2Go client API
        - L{X2GoSession} --- management of an individual X2Go 
        session--either started standalone or from within an L{X2GoClient} instance
        - L{X2GoClientSettings} --- provide access to X2Go (global and 
        user) configuration node »settings«
        - L{X2GoClientPrinting} --- provide access to X2Go (global and 
        user) configuration node »printing«
        - L{X2GoSessionProfiles} --- provide access to X2Go (global and 
        user) configuration node »sessions«

    Plus two extra classes on MS Windows platforms:

       - L{X2GoClientXConfig} and L{X2GoXServer} --- these classes will be initialized 
       during L{X2GoClient} instantiation on MS Windows platforms and start an installed XServer

    Any other of the Python X2Go classes may be subject to internal changes
    and the way of addressing these classes in code may vary between different
    versions of Python X2Go. If you directly use other than the five public API 
    classes in your own applications, so please be warned.


API Structure
=============

    When using Python X2Go in your applications, the basic idea is that you
    create your own class and inherit the X2GoClient class in that::

        import x2go
        class MyX2GoClient(x2go.X2GoClient):

            ...

    Python X2Go is capable of handling multiple running/suspended sessions within the
    same client instance, so for your application, there should not be any need of
    instantiating more than one L{X2GoClient} object in parallel. 

    NOTE: Doing so is--herewith--fully disrecommended.

    The L{X2GoClient} class flattens the complex structure of Python X2Go into
    many L{X2GoClient} methods that you can use in your own C{MyX2GoClient} instance.

    However, it might be handy to retrieve a whole X2Go session instance 
    from the L{X2GoClient} instance. This can be achieved by the 
    L{X2GoClient.register_session()} method::

        import x2go
        my_x2gocli = MyX2GoClient()
        reg_session_instance = my_x2gocli.register_session(<options>, return_object=True)

    Whereas <options> can be as simple as::

         »profile_name=<PROFILE_NAME_IN_SESSIONS_FILE>«

    or contain a whole set of L{X2GoSession} parameters that can be used to start a 
    session manually (i.e. a session that is based on a pre-configured session profile 
    in either of the »sessions« config files).

    The L{X2GoClient.register_session()} method---in object-retrieval-mode---returns
    an L{X2GoSession} instance. With this instance you can then manage
    your X2Go session::

        import gevent, getpass
        pw=getpass.getpass()
        # authenticate
        reg_session_instance.connect(password=pw, <further_options>)
        # then launch the session window with either a new session
        if start:
            reg_session_instance.start()
        # or resume a session
        if resume:
            reg_session_instance.resume(session_name=<X2Go-session-name>)
        # leave it runnint for 60 seconds
        gevent.sleep(60)
        # and then suspend
        if suspend:
            reg_session_instance.suspend()
        # or alternatively terminate it
        elif terminate:
            reg_session_instance.terminate()

    How to access---especially how to modify---the X2Go client configuration
    files »settings«, »printing«, »sessions« and »xconfig« (Windows only)
    is explained in detail with each class declaration in this API documentation. 
    Please refer to the class docs of L{X2GoClientSettings}, L{X2GoClientPrinting},
    L{X2GoSessionProfiles} and L{X2GoXServer}.


Configuration and Session Management
====================================

    Python X2Go strictly separates configuration management from
    session management. The classes needed for session management
    / administration are supposed to only gain »read access« to the 
    classes handling the X2Go client configuration nodes.

    A configuration node in Python X2Go can be a file, a gconf database
    section, a section in the Windows registry, etc.

    NOTE: Each configuration node will be re-read whenever it is needed 
    by an X2Go sesion or the X2GoClient class itself.

    Conclusively, any change to either of the configuration nodes
    will be reflected as a change in your X2Go client behaviour:

      - L{X2GoSessionProfiles}: changes to a session profile in
      the »sessions« node will be available for the next registered
      L{X2GoSession} instance
      - L{X2GoClientPrinting}: on each incoming X2Go print job the
      »printing« configuration node will be re-read, thus you can 
      change your X2Go client's print setup during a running session
      - L{X2GoClientSettings}: also the configuration node »settings« 
      is re-read whenever needed in the course of X2Go session management
      - L{X2GoClientXConfig} and L{X2GoXServer} (Windows only): these classes will only be initialized 
      once (starting the XServer on Windows platforms) on construction
      of an L{X2GoClient} instance

Dependencies
============
    Python X2Go takes advantage of the libevent/greenlet implementation 
    gevent (http://www.gevent.org). The least needed version of Python gevent
    is 0.13.0. On MS Windows Python gevent 1.0 is highly recommended.

    Python X2Go (because of gevent) requires at least Python 2.6. Further recent
    information on Python X2Go is available at: 
    U{http://wiki.x2go.org/python-x2go}

Contact
=======
    If you have any questions concerning Python X2Go, please sign up for the
    x2go-dev list (https://lists.berlios.de/mailman/listinfo/x2go-dev) and post
    your questions, requests and feedbacks there.

"""

__NAME__    = 'python-x2go'
__VERSION__ = '0.5.0.1'

import os
from defaults import X2GOCLIENT_OS

if X2GOCLIENT_OS != 'Windows':
    # enforce "ares" resolve in gevent (>= 1.0~)...
    os.environ["GEVENT_RESOLVER"] = "ares"

from gevent import monkey
monkey.patch_all()

import utils

from client import X2GoClient
from backends.profiles.file import X2GoSessionProfiles
from backends.printing.file import X2GoClientPrinting
from backends.settings.file import X2GoClientSettings
from session import X2GoSession
from sshproxy import X2GoSSHProxy
from x2go_exceptions import *
from log import *

from cleanup import x2go_cleanup

from defaults import CURRENT_LOCAL_USER
from defaults import LOCAL_HOME
from defaults import X2GO_CLIENT_ROOTDIR
from defaults import X2GO_SESSIONS_ROOTDIR
from defaults import X2GO_SSH_ROOTDIR
from defaults import BACKENDS

if X2GOCLIENT_OS == 'Windows':
    from xserver import X2GoClientXConfig, X2GoXServer

# compat section
X2goClient = X2GoClient
X2goSessionProfiles = X2GoSessionProfiles
X2goClientPrinting = X2GoClientPrinting
X2goClientSettings = X2GoClientSettings
X2goSession = X2GoSession
X2goSSHProxy = X2GoSSHProxy

if X2GOCLIENT_OS == 'Windows':
    X2goClientXConfig = X2GoClientXConfig
    X2goXServer = X2GoXServer
