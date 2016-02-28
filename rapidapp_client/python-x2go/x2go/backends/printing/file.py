# -*- coding: utf-8 -*-

"""\
L{X2GoClientPrinting} class is one of Python X2Go's public API classes. 

Retrieve an instance of this class from your L{X2GoClient} instance.
Use this class in your Python X2Go based applications to access the »printing« 
configuration of your X2Go client application.

"""
__NAME__ = 'x2goprinting-pylib'

# modules
import types

# Python X2Go modules
import x2go.log as log
import x2go.printactions as printactions
# we hide the default values from epydoc (that's why we transform them to _UNDERSCORE variables)
from x2go.defaults import X2GO_CLIENTPRINTING_DEFAULTS as _X2GO_CLIENTPRINTING_DEFAULTS
from x2go.defaults import X2GO_PRINTING_CONFIGFILES as _X2GO_PRINTING_CONFIGFILES
import x2go.inistring as inistring
import x2go.x2go_exceptions as x2go_exceptions

_print_property_map = {
        'pdfview_cmd': {
            'ini_section': 'view',
            'ini_option': 'command',
        },
        'save_to_folder': {
            'ini_section': 'save',
            'ini_option': 'folder',
        },
        'printer': {
            'ini_section': 'CUPS',
            'ini_option': 'defaultprinter',
        },
        'print_cmd': {
            'ini_section': 'print', 
            'ini_option': 'command',
        },
}

class X2GoClientPrinting(inistring.X2GoIniString):
    """\
    L{x2go.backends.printing.file.X2GoClientPrinting} provides access to the X2Go ini-like file
    »printing« as stored in C{~/.x2goclient/printing} resp. globally
    C{/etc/x2goclient/printing}.

    An instance of L{x2go.backends.printing.file.X2GoClientPrinting} is created on each incoming
    print job. This facilitates that on every print job the print action
    for this job is derived from the »printing« configuration file.

    Thus, changes on the file are active for the next incoming print job.

    """
    config_files = []
    _print_action = None

    def __init__(self, config_files=_X2GO_PRINTING_CONFIGFILES, defaults=_X2GO_CLIENTPRINTING_DEFAULTS, client_instance=None, logger=None, loglevel=log.loglevel_DEFAULT):
        """\
        @param config_files: a list of configuration files names (e.g. a global filename and a user's home 
            directory filename)
        @type config_files: C{list}
        @param defaults: a cascaded Python dicitionary structure with ini file defaults (to override 
            Python X2Go's hard coded defaults in L{defaults}
        @type defaults: C{dict}
        @param logger: you can pass an L{X2GoLogger} object to the
            L{X2GoPrintAction} constructor
        @type logger: C{obj}
        @param loglevel: if no L{X2GoLogger} object has been supplied a new one will be
            constructed with the given loglevel
        @type loglevel: C{int}

        """
        self.config_string = """\
[print]
gsprint = C:\Program Files (x86)\GhostGum\gsview\gsprint.exe
command = lpr
stdin = 0
startcmd = 0
ps = 0

[CUPS]
defaultprinter = PDF

[save]
folder = PDF

[view]
command = xdg-open
open = 1

[General]
pdfview = 1
showdialog = 0

"""
        self.client_instance = client_instance
        inistring.X2GoIniString.__init__(self, self.config_string, defaults=defaults, logger=logger, loglevel=loglevel)

        self._detect_print_action()

    def _detect_print_action(self):
        """\
        Derive a print action from sections, keys and their values in a typical
        X2Go client »printing« configuration file.

        """
        _general_pdfview = self.get('General', 'pdfview', key_type=types.BooleanType)
        _view_open = self.get('view', 'open', key_type=types.BooleanType)
        _print_startcmd = self.get('print', 'startcmd', key_type=types.BooleanType)
        _show_dialog = self.get('General', 'showdialog', key_type=types.BooleanType)

        if _show_dialog and self.client_instance is not None:
            self._print_action = printactions.X2GoPrintActionDIALOG(client_instance=self.client_instance, logger=self.logger)

        elif _general_pdfview and _view_open:
            _view_command = self.get('view', 'command')
            self._print_action = printactions.X2GoPrintActionPDFVIEW(client_instance=self.client_instance, pdfview_cmd=_view_command, logger=self.logger)

        elif _general_pdfview and not _view_open:
            _safe_folder = self.get('save', 'folder')
            self._print_action = printactions.X2GoPrintActionPDFSAVE(client_instance=self.client_instance, save_to_folder=_safe_folder, logger=self.logger)

        elif not _general_pdfview and not _print_startcmd:
            _cups_defaultprinter = self.get('CUPS', 'defaultprinter')
            self._print_action = printactions.X2GoPrintActionPRINT(client_instance=self.client_instance, printer=_cups_defaultprinter, logger=self.logger)

        elif not _general_pdfview and _print_startcmd:
            _print_command = self.get('print', 'command')
            self._print_action = printactions.X2GoPrintActionPRINTCMD(client_instance=self.client_instance, print_cmd=_print_command, logger=self.logger)

    @property
    def print_action(self):
        """\
        Return the print action described by the »printing« configuration file.

        This method has property status and wraps around the L{get_print_action}
        method.

        """
        return self.get_print_action()

    def get_print_action(self, reload=False, reinit=False, return_name=False):
        """\
        Return the print action described by the »printing« configuration file.

        @param reload: reload the configuration file before retrieving the print action?
        @type reload: C{bool}
        @param reinit: re-detect the print action from what is stored in cache?
        @type reinit: C{bool}
        @param return_name: return the print action name, not the class
        @type return_name: C{bool}

        @return: the configured print action
        @rtype: C{obj} or C{str}

        """
        if reload:
            self.load()

        if reinit:
            self._detect_print_action()

        if return_name:
            return self._print_action.__name__
        else:
            return self._print_action

    def get_property(self, print_property):
        """\
        Retrieve a printing property as mapped by the L{_print_property_map} dictionary.

        @param print_property: a printing property
        @type print_property: C{str}

        @return: the stored value for C{<print_property>}
        @rtype: C{str}

        @raise X2GoClientPrintingException: if the printing property does not exist

        """
        if print_property in _print_property_map.keys():
            _ini_section = _print_property_map[print_property]['ini_section']
            _ini_option = _print_property_map[print_property]['ini_option']
            return self.get_value(_ini_section, _ini_option)
        else:
            raise x2go_exceptions.X2GoClientPrintingException('No such X2Go client printing property ,,%s\'\'' % print_property)

    def set_property(self, print_property, value):
        """\
        Set a printing property as mapped by the L{_print_property_map} dictionary.

        @param print_property: a printing property
        @type print_property: C{str}
        @param value: the value to be stored as C{<print_property>}
        @rtype: C{str}

        @raise X2GoClientPrintingException: if the printing property does not exist or if there is a type mismatch

        """
        if print_property in _print_property_map.keys():
            _ini_section = _print_property_map[print_property]['ini_section']
            _ini_option = _print_property_map[print_property]['ini_option']
            _default_type = self.get_type(_ini_section, _ini_option)
            if type(value) is types.UnicodeType:
                value = value.encode('utf-8')
            if  _default_type != type(value):
                raise x2go_exceptions.X2GoClientPrintingException('Type mismatch error for property ,,%s\'\' - is: %s, should be: %s' % (print_property, str(type(value)), str(_default_type)))
            self.update_value(_ini_section, _ini_option, value)
        else:
            raise x2go_exceptions.X2GoClientPrintingException('No such X2Go client printing property ,,%s\'\'' % print_property)

    def store_print_action(self, print_action, **print_properties):
        """\
        Accept a new print action configuration. This includes the print action
        itself (DIALOG, PDFVIEW, PDFSAVE, PRINT or PRINTCMD) and related printing properties
        as mapped by the L{_print_property_map} dictionary.

        @param print_action: the print action name
        @type print_action: C{str}
        @param print_properties: the printing properties to set for the given print action
        @type print_properties: C{dict}

        """
        if print_action == 'DIALOG':
            self.update_value('General', 'showdialog', True)
        else:
            self.update_value('General', 'showdialog', False)

        if print_action == 'PDFVIEW':
            self.update_value('General', 'pdfview', True)
            self.update_value('view', 'open', True)

        elif print_action == 'PDFSAVE':
            self.update_value('General', 'pdfview', True)
            self.update_value('view', 'open', False)

        elif print_action == 'PRINT':
            self.update_value('General', 'pdfview', False)
            self.update_value('print', 'startcmd', False)

        elif print_action == 'PRINTCMD':
            self.update_value('General', 'pdfview', False)
            self.update_value('print', 'startcmd', True)

        for print_property in print_properties.keys():
            self.set_property(print_property, print_properties[print_property])

