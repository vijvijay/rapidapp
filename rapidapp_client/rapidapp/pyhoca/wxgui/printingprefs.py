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

import os
import re

import wx

import x2go.log as log
import x2go.utils as utils
from x2go import X2GOCLIENT_OS as _X2GOCLIENT_OS
from x2go import CURRENT_LOCAL_USER as _CURRENT_LOCAL_USER
from x2go import LOCAL_HOME as _LOCAL_HOME

if _X2GOCLIENT_OS != "Windows":
    import cups
else:
    import win32print

import basepath

_icons_location = basepath.icons_basepath

class PyHocaGUI_PrintingPreferences(wx.Dialog):
    """\
    The print preferences dialog box allowing the configuration and re-configuration
    of the processing of incoming / client-side print jobs.

    """
    def __init__(self, _PyHocaGUI, profile_name=None, session_name=None, mode='edit'):
        """\
        Printing preferences dialog box (constructor).

        @param _PyHocaGUI: the master/parent object of the application
        @type _PyHocaGUI: C{obj}
        @param profile_name: session profile name
        @type profile_name: C{str}
        @param session_name: the X2Go session name of the Window that we intend to modify the name of
        @type session_name C{str}
        @param sesion_name: is this instance launched on an incoming pring job? Or are wie in editor mode.

        """
        self._PyHocaGUI = _PyHocaGUI
        self._pyhoca_logger = self._PyHocaGUI._pyhoca_logger
        self.mode = mode

        self._pyhoca_logger('opening client printing configuration dialog, mode: ,,%s\'\'' % self.mode, loglevel=log.loglevel_INFO)

        if self.mode == 'edit':
            _title = _(u'%s - Printing Preferences') % self._PyHocaGUI.appname
        else:
            _title = _(u'%s - Incoming Print Job from  %s (%s)') % (self._PyHocaGUI.appname, profile_name, session_name)
        wx.Dialog.__init__(self, None, -1, title=_title, style=wx.DEFAULT_DIALOG_STYLE, )
        self._PyHocaGUI._sub_windows.append(self)

        self._availablePrintActions = {
            'DIALOG': _(u'Open this dialog window'),
            'PDFVIEW': _(u'Open with PDF viewer'),
            'PDFSAVE': _(u'Save to a local folder'),
            'PRINT': _(u'Print to a local printer'),
            'PRINTCMD': _(u'Run custom print command'),
            }
        if self.mode != 'edit':
            self._availablePrintActions['DIALOG'] = _(u'<Select a print action here>')

        self._availablePrinters = {}
        if _X2GOCLIENT_OS != "Windows":
            # initialize CUPS config API and retrieve a list of local print queues
            try:
                cups.setUser(_CURRENT_LOCAL_USER)
                cups_connection = cups.Connection()
                cups_printers = cups_connection.getPrinters()
                for p in cups_printers.keys():
                    self._availablePrinters.update({ p: '%s (%s)' % (p, cups_printers[p]['printer-info']), })
                self._defaultPrinter = cups_connection.getDefault()
            except RuntimeError:
                self._defaultPrinter = '#PRINTSYSTEM_UNAVAILABLE#'
        else:
            # initialize win32print API and retrieve a list of local print queues
            try:
                win32_printers = win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL)
                for p in win32_printers:
                    if p[3]:
                        self._availablePrinters.update({p[2]: '%s (%s)' % (p[2], p[3]), })
                    else:
                        self._availablePrinters.update({p[2]: '%s' % p[2], })
                        self._defaultPrinter = win32print.GetDefaultPrinter()
            except:
                # FIXME: find out what exception could occur here.
                self._defaultPrinter = '#PRINTSYSTEM_UNAVAILABLE#'

        self.client_printing = self._PyHocaGUI.client_printing

        ###
        ### widgets for CLIENT PRINTING
        ###
        if self.mode != 'edit':
            self.PrintActionLabel = wx.StaticText(self, -1, _(u"Print action")+':')
        else:
            self.PrintActionLabel = wx.StaticText(self, -1, _(u"Default action for incoming print jobs")+':')
        self.PrintAction = wx.ComboBox(self, -1, choices=self._availablePrintActions.values(), style=wx.CB_DROPDOWN|wx.CB_READONLY)

        # widgets for print action PDFVIEW
        self.PdfViewCmdLabel = wx.StaticText(self, -1, _(u'PDF viewer command') + ':', )
        self.PdfViewCmd = wx.TextCtrl(self, -1, '', )
        self.PdfViewCmdBrowseButton = wx.BitmapButton(self, -1,
                                                      wx.Bitmap('%s/PyHoca/16x16/system-search.png' % _icons_location, wx.BITMAP_TYPE_ANY)
                                                     )

        # widgets for print action PDFSAVE
        self.PdfSaveToFolderLabel = wx.StaticText(self, -1, _(u'Save PDFs to folder') + ':', )
        self.PdfSaveToFolder = wx.TextCtrl(self, -1, '', )
        self.PdfSaveToFolderBrowseButton = wx.BitmapButton(self, -1,
                                                           wx.Bitmap('%s/PyHoca/16x16/system-search.png' % _icons_location, wx.BITMAP_TYPE_ANY)
                                                          )

        # widgets for print action PRINT
        self.PrintPrinterLabel = wx.StaticText(self, -1, _(u'Use this printer') + ':', )
        self.PrintPrinter = wx.ComboBox(self, -1, choices=self._availablePrinters.values(), style=wx.CB_DROPDOWN|wx.CB_READONLY)

        # widgets for print action PRINTCMD
        self.PrintCmdLabel = wx.StaticText(self, -1, _(u'Custom print command') + ':', )
        self.PrintCmd = wx.TextCtrl(self, -1, '', )

        if self.mode == 'edit':
            self.OKButton = wx.Button(self, wx.ID_OK, _(u"Ok"))
            self.ApplyButton = wx.Button(self, -1, _(u"Apply"))
        else:
            self.OKButton = wx.Button(self, wx.ID_OK, _(u"Print"))
        self.OKButton.SetDefault()
        self.CancelButton = wx.Button(self, wx.ID_CANCEL, _(u"Cancel"))

        self.__set_properties()
        self.__update_fields()
        self.__do_layout()

        self.Bind(wx.EVT_COMBOBOX, self.OnPrintActionChange, self.PrintAction)

        self.Bind(wx.EVT_BUTTON, self.OnPdfViewCmdBrowseButton, self.PdfViewCmdBrowseButton)
        self.Bind(wx.EVT_BUTTON, self.OnPdfSaveToFolderBrowseButton, self.PdfSaveToFolderBrowseButton)

        self.Bind(wx.EVT_BUTTON, self.OnOKButton, self.OKButton)
        if self.mode == 'edit':
            self.Bind(wx.EVT_BUTTON, self.OnApplyButton, self.ApplyButton)
        self.Bind(wx.EVT_BUTTON, self.OnCancel, self.CancelButton)


    def __set_properties(self):
        """\
        Set field properties (before layouting).

        """
        _textfield_height = self.PdfViewCmdBrowseButton.GetBestSize().GetHeight()-2
        self.PrintActionLabel.SetMinSize((-1, 16))
        self.PrintAction.SetMinSize((-1, _textfield_height+4))
        self.PdfViewCmdBrowseButton.SetMinSize(self.PdfViewCmdBrowseButton.GetBestSize())
        self.PdfSaveToFolderBrowseButton.SetMinSize(self.PdfSaveToFolderBrowseButton.GetBestSize())
        self.OKButton.SetMinSize((-1, 30))
        if self.mode == 'edit':
            self.ApplyButton.SetMinSize((-1, 30))
        self.CancelButton.SetMinSize((-1, 30))

    def __do_layout(self):
        """\
        Arrange the frame's widget layout.

        """
        sizer_1 = wx.BoxSizer(wx.VERTICAL)
        sizer_1_1 = wx.GridBagSizer(hgap=2, vgap=5)
        sizer_1_1.Add(self.PrintActionLabel, pos=(0,0), flag=wx.ALIGN_CENTER_VERTICAL|wx.RIGHT|wx.BOTTOM, border=7, )
        sizer_1_1.Add(self.PrintAction, pos=(0,1), flag=wx.BOTTOM, border=7, )

        sizer_1_1.Add(self.PdfViewCmdLabel, pos=(1,0), flag=wx.ALIGN_CENTER_VERTICAL|wx.RIGHT, border=7, )
        sizer_1_1_1 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_1_1_1.Add(self.PdfViewCmd, proportion=1, flag=wx.EXPAND|wx.RIGHT, border=7, )
        sizer_1_1_1.Add(self.PdfViewCmdBrowseButton, )
        sizer_1_1.Add(sizer_1_1_1, pos=(1,1), flag=wx.EXPAND|wx.ALIGN_CENTER_VERTICAL, )

        sizer_1_1.Add(self.PdfSaveToFolderLabel, pos=(2,0), flag=wx.ALIGN_CENTER_VERTICAL|wx.RIGHT, border=7, )
        sizer_1_1_2 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_1_1_2.Add(self.PdfSaveToFolder, proportion=1, flag=wx.EXPAND|wx.RIGHT, border=7, )
        sizer_1_1_2.Add(self.PdfSaveToFolderBrowseButton, )
        sizer_1_1.Add(sizer_1_1_2, pos=(2,1), flag=wx.EXPAND|wx.ALIGN_CENTER_VERTICAL, )

        sizer_1_1.Add(self.PrintPrinterLabel, pos=(3,0), flag=wx.ALIGN_CENTER_VERTICAL|wx.RIGHT, border=7, )
        sizer_1_1_3 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_1_1_3.Add(self.PrintPrinter, proportion=1, flag=wx.EXPAND, )
        sizer_1_1.Add(sizer_1_1_3, pos=(3,1), flag=wx.EXPAND|wx.ALIGN_CENTER_VERTICAL, )

        sizer_1_1.Add(self.PrintCmdLabel, pos=(4,0), flag=wx.ALIGN_CENTER_VERTICAL|wx.RIGHT, border=7, )
        sizer_1_1_4 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_1_1_4.Add(self.PrintCmd, proportion=1, flag=wx.EXPAND, )
        sizer_1_1.Add(sizer_1_1_4, pos=(4,1), flag=wx.EXPAND|wx.ALIGN_CENTER_VERTICAL, )
        sizer_1.Add(sizer_1_1, flag=wx.EXPAND|wx.ALL, border=10)

        # the bottom area with OK and Cancel buttons
        sizer_B = wx.BoxSizer(wx.HORIZONTAL)
        sizer_B.Add(self.OKButton, flag=wx.ALL, border=5)
        if self.mode == 'edit':
            sizer_B.Add(self.ApplyButton, flag=wx.ALL, border=5)
        sizer_B.Add(self.CancelButton, flag=wx.ALL, border=5)

        # put it all together...
        MainSizer = wx.BoxSizer(wx.VERTICAL)
        MainSizer.Add(sizer_1, proportion=1, flag=wx.EXPAND|wx.FIXED_MINSIZE)
        MainSizer.Add(sizer_B, flag=wx.ALIGN_RIGHT)
        self.SetSizerAndFit(MainSizer)

        self.SetAutoLayout(True)
        self.Layout()
        self.CentreOnScreen()
        self.Show(True)

    def __update_fields(self):
        """\
        Update field from running application.

        """
        print_action_name = self.client_printing.get_print_action(reload=True, reinit=True, return_name=True)

        self.PdfViewCmd.SetValue(self.client_printing.get_property('pdfview_cmd'))
        self.PdfSaveToFolder.SetValue(self.client_printing.get_property('save_to_folder'))
        if self._defaultPrinter != '#PRINTSYSTEM_UNAVAILABLE#':
            if self._availablePrinters:
                try:
                    _printer_name = self._availablePrinters[self.client_printing.get_property('printer')]
                except KeyError:
                    if self._defaultPrinter != None:
                        _printer_name = self._availablePrinters[self._defaultPrinter]
                    else:
                        _printer_name = self._availablePrinters[self._availablePrinters.keys()[0]]
            else:
                _printer_name = _(u'- no printers installed -')
                self.PrintPrinter.Clear()
                self.PrintPrinter.Append(_(_printer_name))
                self.PrintPrinter.Enable(False)
        else:
            _printer_name = _(u'- print system is not available -')
            self.PrintPrinter.Clear()
            self.PrintPrinter.Append(_(_printer_name))
            self.PrintPrinter.Enable(False)
        self.PrintPrinter.SetValue(_printer_name)
        self.PrintCmd.SetValue(self.client_printing.get_property('print_cmd'))

        if self._availablePrintActions.has_key(print_action_name):
            self.PrintAction.SetValue(self._availablePrintActions[print_action_name])
        else:
            self.PrintAction.SetValue(print_action_name)
        self._onPrintActionChange()

        if self.mode != 'edit':
            if self._print_action == 'DIALOG':
                self.OKButton.Enable(False)

    def __update_from_screen(self):
        self.client_printing.store_print_action(self._print_action, **self._print_action_properties)

    @property
    def _print_action(self):
        return [ p for p in self._availablePrintActions.keys() if self._availablePrintActions[p] == self.PrintAction.GetValue() ][0]

    @property
    def _print_action_properties(self):

        # handle missing print system
        _printer = [ p for p in self._availablePrinters.keys() if self._availablePrinters[p] == self.PrintPrinter.GetValue() and self._defaultPrinter != '#PRINTSYSTEM_UNAVAILABLE#' ]
        try:
            _printer = _printer[0]
        except IndexError:
            _printer = ''

        return {
            'pdfview_cmd': self.PdfViewCmd.GetValue(),
            'save_to_folder': self.PdfSaveToFolder.GetValue(),
            'printer': _printer,
            'print_cmd': self.PrintCmd.GetValue(),
        }

    def get_print_action(self):
        """\
        Retrieve the current print action.

        """
        self.__update_from_screen()
        return self.client_printing.get_print_action(reinit=True)

    def get_print_action_properties(self):
        """\
        Retrieve action properties from all users.

        """
        return self._print_action_properties

    def _onPrintActionChange(self):
        """\
        Helper method for L{OnPrintActionChange}.

        """
        if self._print_action == 'PDFVIEW':
            self.PdfViewSelected()
        elif self._print_action == 'PDFSAVE':
            self.PdfSaveToFolderSelected()
        elif self._print_action == 'PRINT':
            self.PrintPrinterSelected()
        elif self._print_action == 'PRINTCMD':
            self.PrintCmdSelected()
        else:
            self._disable_PrintOptions()
        self.__update_from_screen()

    def OnPrintActionChange(self, evt):
        """
        Gets called whenever a print action change has been requested.

        @param evt: event
        @type evt: C{obj}

        """
        self._onPrintActionChange()

    def _disable_PrintOptions(self):
        """\
        Helper method for L{PdfViewSelected}, L{PdfSaveToFolderSelected}, L{PrintPrinterSelected}, and L{PrintCmdSelected}.

        """
        self.PdfViewCmdLabel.Enable(False)
        self.PdfViewCmd.Enable(False)
        self.PdfViewCmdBrowseButton.Enable(False)
        self.PdfSaveToFolderLabel.Enable(False)
        self.PdfSaveToFolder.Enable(False)
        self.PdfSaveToFolderBrowseButton.Enable(False)
        self.PrintPrinterLabel.Enable(False)
        self.PrintPrinter.Enable(False)
        self.PrintCmdLabel.Enable(False)
        self.PrintCmd.Enable(False)

        if self.mode != 'edit':
            if self._print_action == 'DIALOG':
                self.OKButton.Enable(False)
            else:
                self.OKButton.Enable(True)

    def PdfViewSelected(self):
        """\
        Enable/disable widgets for PDFVIEW print action.

        """
        self._disable_PrintOptions()
        self.PdfViewCmdLabel.Enable(True)
        self.PdfViewCmd.Enable(True)
        self.PdfViewCmdBrowseButton.Enable(True)

    def PdfSaveToFolderSelected(self):
        """\
        Enable/disable widgets for PDFSAVE print action.

        """
        self._disable_PrintOptions()
        self.PdfSaveToFolderLabel.Enable(True)
        self.PdfSaveToFolder.Enable(True)
        self.PdfSaveToFolderBrowseButton.Enable(True)

    def PrintPrinterSelected(self):
        """\
        Enable/disable widgets for PRINT print action.

        """
        self._disable_PrintOptions()
        if self._defaultPrinter != '#PRINTSYSTEM_UNAVAILABLE#':
            self.PrintPrinterLabel.Enable(True)
            self.PrintPrinter.Enable(True)

    def PrintCmdSelected(self):
        """\
        Enable/disable widgets for PRINTCMD print action.

        """
        self._disable_PrintOptions()
        self.PrintCmdLabel.Enable(True)
        self.PrintCmd.Enable(True)

    def OnPdfViewCmdBrowseButton(self, evt):
        """\
        Gets called if the user requests to browse for a PDF view executable.

        @param evt: event
        @type evt: C{obj}

        """
        wildcard = "All files (*.*)|*"
        dlg = wx.FileDialog(
            self, message=_(u"Choose PDF viewer application"), defaultDir=_LOCAL_HOME,
            defaultFile="", wildcard=wildcard, style=wx.FD_OPEN | wx.FD_CHANGE_DIR )
        # Show the dialog and retrieve the user response. If it is the OK response,
        # process the data.
        if dlg.ShowModal() == wx.ID_OK:
            # This returns a Python list of files that were selected.
            _pdfview_cmd = dlg.GetPath()
            self.PdfViewCmd.SetValue(_pdfview_cmd)

    def OnPdfSaveToFolderBrowseButton(self, evt):
        """\
        Gets called if the user requests to set the PDFSAVE folder location.

        @param evt: event
        @type evt: C{obj}

        """
        _start_dir = self.PdfSaveToFolder.GetValue()
        if not utils.is_abs_path(_start_dir):
            if not _start_dir.startswith('~'):
                _start_dir = '~/%s' % _start_dir
            _start_dir = os.path.expanduser(_start_dir)
        dlg = wx.DirDialog(
            self, message=_(u"Choose PDF saving location"), style=1, defaultPath=_start_dir, )
        # Show the dialog and retrieve the user response. If it is the OK response,
        # process the data.
        if dlg.ShowModal() == wx.ID_OK:
            # This returns a Python list of files that were selected.
            _save_to_folder = dlg.GetPath()
            if _X2GOCLIENT_OS != 'Windows':
                if _save_to_folder.startswith(_LOCAL_HOME):
                    _save_to_folder = re.sub('^%s\/' % _LOCAL_HOME, '', _save_to_folder)
            else:
                if os.path.normpath(_save_to_folder).lower().startswith(os.path.normpath(_LOCAL_HOME).lower()):
                    _save_to_folder = re.sub('^%s\\\\' % os.path.normpath(_LOCAL_HOME).replace('\\', '\\\\'), '', _save_to_folder, flags=re.IGNORECASE)
            self.PdfSaveToFolder.SetValue(_save_to_folder)

    def __validate(self):
        """\
        Dummy field validation method. Always returns C{True}.

        """
        validateOk = True
        return validateOk

    def _apply_changes(self):
        """\
        Apply changes in the dialog to the client printing configuration.

        """
        self.__update_from_screen()
        if self.__validate():
            if self.mode == 'edit': self.client_printing.write()
            return True
        return False

    def OnOKButton(self, evt):
        """\
        Gets called if the user presses the ,,Ok'' button.

        @param evt: event
        @type evt: C{obj}

        """
        wx.BeginBusyCursor()
        if self._apply_changes():
            try: wx.EndBusyCursor()
            except: pass
            self.Close()
            self.Destroy()
        else:
            try: wx.EndBusyCursor()
            except: pass

    def OnApplyButton(self, evt):
        """\
        Gets called if the user presses the ,,Apply'' button.

        @param evt: event
        @type evt: C{obj}

        """
        wx.BeginBusyCursor()
        self._apply_changes()
        try: wx.EndBusyCursor()
        except: pass

    def OnCancel(self, evt):
        """\
        Gets called if the user presses the ,,Cancel'' button.

        @param evt: event
        @type evt: C{obj}

        """
        self.client_printing.load()
        self.Close()
        self.Destroy()

    def Destroy(self):
        """\
        Tidy up some stuff in the main application instance before allowing desctruction of the
        printing preferences window.

        """
        try:
            self._PyHocaGUI._sub_windows.remove(self)
        except ValueError:
            pass
        wx.Dialog.Destroy(self)
