# -*- coding: utf-8 -*-

# Copyright (C) 2010 by Mike Gabriel <mike.gabriel@das-netzwerkteam.de>
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

import unittest
import tempfile

# Python X2Go modules
import x2go

class TestX2GoClientPrinting(unittest.TestCase):

    def test_client_printing_dialog(self):
        _printing = """\
[General]
pdfview=true
showdialog=true
[print]
startcmd=false
command=lpr
[view]
open=true
command=xpdf
[CUPS]
defaultprinter=PDF
"""
        tf = tempfile.NamedTemporaryFile()
        print >> tf, _printing
        tf.seek(0)
        p_action = x2go.backends.printing.X2GoClientPrinting(config_files=tf.name, client_instance='DUMMY')
        self.assertEqual(type(p_action.print_action), x2go.printactions.X2GoPrintActionDIALOG)
        tf.close()

    def test_client_printing_pdfview(self):
        _printing = """\
[General]
pdfview=true
[print]
startcmd=false
command=lpr
[view]
open=true
command=xpdf
[CUPS]
defaultprinter=PDF
"""
        tf = tempfile.NamedTemporaryFile()
        print >> tf, _printing
        tf.seek(0)
        p_action = x2go.backends.printing.X2GoClientPrinting(config_files=tf.name)
        self.assertEqual(type(p_action.print_action), x2go.printactions.X2GoPrintActionPDFVIEW)
        tf.close()

    def test_client_printing_pdfsave(self):
        _printing = """\
[General]
pdfview=true
[print]
startcmd=false
command=lpr
[view]
open=false
command=xpdf
[CUPS]
defaultprinter=PDF
"""
        tf = tempfile.NamedTemporaryFile()
        print >> tf, _printing
        tf.seek(0)
        p_action = x2go.backends.printing.X2GoClientPrinting(config_files=tf.name)
        self.assertEqual(type(p_action.print_action), x2go.printactions.X2GoPrintActionPDFSAVE)
        tf.close()

    def test_client_printing_print(self):
        _printing = """\
[General]
pdfview=false
[print]
startcmd=false
command=lpr
[view]
open=false
command=xpdf
[CUPS]
defaultprinter=PDF
"""
        tf = tempfile.NamedTemporaryFile()
        print >> tf, _printing
        tf.seek(0)
        p_action = x2go.backends.printing.X2GoClientPrinting(config_files=tf.name)
        self.assertEqual(type(p_action.print_action), x2go.printactions.X2GoPrintActionPRINT)
        tf.close()

    def test_client_printing_printcmd(self):
        _printing = """\
[General]
pdfview=false
[print]
startcmd=true
command=lpr
[view]
open=false
command=xpdf
[CUPS]
defaultprinter=PDF
"""
        tf = tempfile.NamedTemporaryFile()
        print >> tf, _printing
        tf.seek(0)
        p_action = x2go.backends.printing.X2GoClientPrinting(config_files=tf.name)
        self.assertEqual(type(p_action.print_action), x2go.printactions.X2GoPrintActionPRINTCMD)
        tf.close()

def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestX2GoClientPrinting))
    return suite
