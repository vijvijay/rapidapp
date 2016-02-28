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

NSIS_SCRIPT_TEMPLATE = """
;{program_name}.nsi
;

!define VERSION {program_version}

!define UNINSTALL_REGKEY    "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{program_name}"

;--------------------------------

; The name of the installer
Name "{program_name}"

; Sets the title bar text
Caption "{program_desc_short}"

!define distOutputDirectory '{output_dir}'

; The file to write
OutFile "..\\{program_name}_${{VERSION}}_win32-setup.exe"

; The default installation directory
InstallDir $PROGRAMFILES\\{program_name}

; NSIS 2.46 defaults to zlib. Setting this reduces the size of current
; builds (which include no fonts for the X server) by about 27%
SetCompressor /SOLID lzma

; Registry key to check for directory (so if you install again, it will 
; overwrite the old one automatically)
InstallDirRegKey HKLM "Software\\{program_name}" "Install_Dir"

; OBSOLETE WITH MUI2: Request application privileges for Windows Vista
;RequestExecutionLevel admin

!define MULTIUSER_EXECUTIONLEVEL Highest
!define MULTIUSER_MUI
!define MULTIUSER_INSTALLMODE_COMMANDLINE
!include MultiUser.nsh
!include MUI2.nsh

!insertmacro MULTIUSER_PAGE_INSTALLMODE
!insertmacro MUI_PAGE_LICENSE COPYING
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_INSTFILES

!insertmacro MUI_LANGUAGE "English" ;first language is the default language
;!insertmacro MUI_LANGUAGE "French"
!insertmacro MUI_LANGUAGE "German"
!insertmacro MUI_LANGUAGE "Spanish"
;!insertmacro MUI_LANGUAGE "SpanishInternational"
;!insertmacro MUI_LANGUAGE "SimpChinese"
;!insertmacro MUI_LANGUAGE "TradChinese"
;!insertmacro MUI_LANGUAGE "Japanese"
;!insertmacro MUI_LANGUAGE "Korean"
;!insertmacro MUI_LANGUAGE "Italian"
!insertmacro MUI_LANGUAGE "Dutch"
;!insertmacro MUI_LANGUAGE "Danish"
!insertmacro MUI_LANGUAGE "Swedish"
;!insertmacro MUI_LANGUAGE "Norwegian"
;!insertmacro MUI_LANGUAGE "NorwegianNynorsk"
;!insertmacro MUI_LANGUAGE "Finnish"
;!insertmacro MUI_LANGUAGE "Greek"
!insertmacro MUI_LANGUAGE "Russian"
;!insertmacro MUI_LANGUAGE "Portuguese"
;!insertmacro MUI_LANGUAGE "PortugueseBR"
;!insertmacro MUI_LANGUAGE "Polish"
;!insertmacro MUI_LANGUAGE "Ukrainian"
;!insertmacro MUI_LANGUAGE "Czech"
;!insertmacro MUI_LANGUAGE "Slovak"
;!insertmacro MUI_LANGUAGE "Croatian"
;!insertmacro MUI_LANGUAGE "Bulgarian"
;!insertmacro MUI_LANGUAGE "Hungarian"
;!insertmacro MUI_LANGUAGE "Thai"
;!insertmacro MUI_LANGUAGE "Romanian"
;!insertmacro MUI_LANGUAGE "Latvian"
;!insertmacro MUI_LANGUAGE "Macedonian"
;!insertmacro MUI_LANGUAGE "Estonian"
;!insertmacro MUI_LANGUAGE "Turkish"
;!insertmacro MUI_LANGUAGE "Lithuanian"
;!insertmacro MUI_LANGUAGE "Slovenian"
;!insertmacro MUI_LANGUAGE "Serbian"
;!insertmacro MUI_LANGUAGE "SerbianLatin"
;!insertmacro MUI_LANGUAGE "Arabic"
;!insertmacro MUI_LANGUAGE "Farsi"
;!insertmacro MUI_LANGUAGE "Hebrew"
;!insertmacro MUI_LANGUAGE "Indonesian"
;!insertmacro MUI_LANGUAGE "Mongolian"
;!insertmacro MUI_LANGUAGE "Luxembourgish"
;!insertmacro MUI_LANGUAGE "Albanian"
;!insertmacro MUI_LANGUAGE "Breton"
;!insertmacro MUI_LANGUAGE "Belarusian"
;!insertmacro MUI_LANGUAGE "Icelandic"
;!insertmacro MUI_LANGUAGE "Malay"
;!insertmacro MUI_LANGUAGE "Bosnian"
;!insertmacro MUI_LANGUAGE "Kurdish"
;!insertmacro MUI_LANGUAGE "Irish"
;!insertmacro MUI_LANGUAGE "Uzbek"
;!insertmacro MUI_LANGUAGE "Galician"
;!insertmacro MUI_LANGUAGE "Afrikaans"
;!insertmacro MUI_LANGUAGE "Catalan"
;!insertmacro MUI_LANGUAGE "Esperanto"
;!insertmacro MUI_LANGUAGE "Asturian"

; License data
; Not exactly translated, but it shows what's needed
LicenseLangString myLicenseData ${{LANG_ENGLISH}} "COPYING"
LicenseLangString myLicenseData ${{LANG_DUTCH}} "COPYING"
;LicenseLangString myLicenseData ${{LANG_FRENCH}} "COPYING"
LicenseLangString myLicenseData ${{LANG_GERMAN}} "COPYING"
;LicenseLangString myLicenseData ${{LANG_KOREAN}} "COPYING"
LicenseLangString myLicenseData ${{LANG_RUSSIAN}} "COPYING"
LicenseLangString myLicenseData ${{LANG_SPANISH}} "COPYING"
LicenseLangString myLicenseData ${{LANG_SWEDISH}} "COPYING"
;LicenseLangString myLicenseData ${{LANG_TRADCHINESE}} "COPYING"
;LicenseLangString myLicenseData ${{LANG_SIMPCHINESE}} "COPYING"
;LicenseLangString myLicenseData ${{LANG_SLOVAK}} "COPYING"

LicenseData $(myLicenseData)

; Set name using the normal interface (Name command)
LangString Name ${{LANG_ENGLISH}} "English"
LangString Name ${{LANG_DUTCH}} "Dutch"
;LangString Name ${{LANG_FRENCH}} "French"
LangString Name ${{LANG_GERMAN}} "German"
;LangString Name ${{LANG_KOREAN}} "Korean"
LangString Name ${{LANG_RUSSIAN}} "Russian"
LangString Name ${{LANG_SPANISH}} "Spanish"
LangString Name ${{LANG_SWEDISH}} "Swedish"
;LangString Name ${{LANG_TRADCHINESE}} "Traditional Chinese"
;LangString Name ${{LANG_SIMPCHINESE}} "Simplified Chinese"
;LangString Name ${{LANG_SLOVAK}} "Slovak"

;--------------------------------

; Installer Language Configuration

;!include LogicLib.nsh

var LC_MESSAGES

; i18n strings
var REQUIRED
var DESKTOP_LINKS
var STARTMENU_LINKS
var WITHOUT_PULSEAUDIO
var GSPRINT

Function .onInit

;        ;Language selection dialog
;
        Push ""
        Push ${{LANG_ENGLISH}}
        Push English
        Push ${{LANG_DUTCH}}
        Push Dutch
;       Push ${{LANG_FRENCH}}
;       Push French
        Push ${{LANG_GERMAN}}
        Push German
;       Push ${{LANG_KOREAN}}
;       Push Korean
        Push ${{LANG_RUSSIAN}}
        Push Russian
        Push ${{LANG_SPANISH}}
        Push Spanish
        Push ${{LANG_SWEDISH}}
        Push Swedish
;       Push ${{LANG_TRADCHINESE}}
;       Push "Traditional Chinese"
;       Push ${{LANG_SIMPCHINESE}}
;       Push "Simplified Chinese"
;       Push ${{LANG_SLOVAK}}
;       Push Slovak
        Push A ; A means auto count languages
               ; for the auto count to work the first empty push (Push "") must remain
        LangDLL::LangDialog "Installer Language" "Please select the language of the installer"

        Pop $LANGUAGE

        ${{Switch}} $LANGUAGE
          ${{Case}} 1031
            StrCpy $LC_MESSAGES "de"
            !include "nsis_include\\de.nsi"
            ${{Break}}
          ${{Case}} 1033
            StrCpy $LC_MESSAGES "en"
            !include "nsis_include\\en.nsi"
            ${{Break}}
          ${{Case}} 1043
            StrCpy $LC_MESSAGES "nl"
            !include "nsis_include\\nl.nsi"
            ${{Break}}
          ${{Case}} 1034
            StrCpy $LC_MESSAGES "es"
            !include "nsis_include\\es.nsi"
            ${{Break}}
          ${{Case}} 1053
            StrCpy $LC_MESSAGES "sv"
            !include "nsis_include\\sv.nsi"
            ${{Break}}
          ${{Case}} 1049
            StrCpy $LC_MESSAGES "ru"
            !include "nsis_include\\ru.nsi"
            ${{Break}}
        ${{EndSwitch}}

        StrCmp $LANGUAGE "cancel" 0 +2
            Abort

        !insertmacro MULTIUSER_INIT

FunctionEnd

Function un.onInit

        !insertmacro MULTIUSER_UNINIT

FunctionEnd

;--------------------------------

;--------------------------------

; The stuff to install
Section "{program_name} ($REQUIRED)"

  SectionIn RO
  ; Set output path to the installation directory.
  SetOutPath "$INSTDIR"
  ; Empty $INSTDIR before writing new files to it.
  RmDir /r "$INSTDIR\\*.*"
  ; Install new files...
  File /r /x .svn /x .git "${{distOutputDirectory}}\\*.*"

  ; Write the installation path into the registry
  WriteRegStr HKLM SOFTWARE\\{program_name} "Install_Dir" "$INSTDIR"

  ; Write the uninstall keys for Windows
  
  WriteRegStr HKLM ${{UNINSTALL_REGKEY}}   "InstallLocation"      "$INSTDIR"
  WriteRegStr HKLM ${{UNINSTALL_REGKEY}}   "UninstallString"      "$INSTDIR\\uninstall.exe"
  WriteRegStr HKLM ${{UNINSTALL_REGKEY}}   "DisplayIcon"          "$INSTDIR\\{icon_location}"
  WriteRegStr HKLM ${{UNINSTALL_REGKEY}}   "DisplayName"          "{uninstall_name}"
  WriteRegStr HKLM ${{UNINSTALL_REGKEY}}   "DisplayVersion"       "${{VERSION}}"
  WriteRegStr HKLM ${{UNINSTALL_REGKEY}}   "Publisher"            "{publisher}"
  WriteRegStr HKLM ${{UNINSTALL_REGKEY}}   "HelpLink"             "{url}"
  WriteRegStr HKLM ${{UNINSTALL_REGKEY}}   "URLInfoAbout"         "{url}"
  WriteRegStr HKLM ${{UNINSTALL_REGKEY}}   "URLUpdateInfo"        "{url}"
  WriteRegDWORD HKLM ${{UNINSTALL_REGKEY}} "NoModify" 1
  WriteRegDWORD HKLM ${{UNINSTALL_REGKEY}} "NoRepair" 1
  WriteUninstaller "uninstall.exe"

SectionEnd

; Optional section (can be disabled by the user)
Section "$STARTMENU_LINKS"

  SetOutPath "$INSTDIR"
  CreateDirectory "$SMPROGRAMS\\{program_name}"
  CreateShortCut "$SMPROGRAMS\\{program_name}\\{program_name}.lnk" "$INSTDIR\\{program_name}.exe" "--quiet --start-xserver --start-pulseaudio --lang $LC_MESSAGES" "$INSTDIR\\icons\\{program_name}.ico" 0
  CreateShortCut "$SMPROGRAMS\\{program_name}\\{program_name} ($WITHOUT_PULSEAUDIO).lnk" "$INSTDIR\\{program_name}.exe" "--quiet --start-xserver --lang $LC_MESSAGES" "$INSTDIR\\icons\\{program_name}.ico" 0
  CreateShortCut "$SMPROGRAMS\\{program_name}\\{program_name} (debug).lnk" "$INSTDIR\\{program_name}.exe" "--debug --libdebug --start-xserver --start-pulseaudio --lang $LC_MESSAGES" "$INSTDIR\\icons\\{program_name}.ico" 0
  CreateShortCut "$SMPROGRAMS\\{program_name}\\{program_name} ($WITHOUT_PULSEAUDIO, debug).lnk" "$INSTDIR\\{program_name}.exe" "--debug --libdebug --start-xserver --lang $LC_MESSAGES" "$INSTDIR\\icons\\{program_name}.ico" 0
  CreateShortCut "$SMPROGRAMS\\{program_name}\\X2Go Website.lnk" "http://www.x2go.org" "" "$INSTDIR\\icons\\pyhoca_x2go-logo-ubuntu.ico" 0
  CreateShortCut "$SMPROGRAMS\\{program_name}\\Uninstall.lnk" "$INSTDIR\\uninstall.exe" "" "$INSTDIR\\uninstall.exe" 0

SectionEnd

; Optional section (can be disabled by the user)
Section "$DESKTOP_LINKS"

  SetOutPath "$INSTDIR"
  CreateShortCut "$DESKTOP\\{program_name}.lnk" "$INSTDIR\\{program_name}.exe" "--quiet --start-xserver --start-pulseaudio --lang $LC_MESSAGES" "$INSTDIR\\icons\\{program_name}.ico" 0

SectionEnd

; Hidden section, always enabled
Section -EstimatedSize
  SectionIn RO
  ${{GetSize}} "$INSTDIR" "/S=0K" $0 $1 $2
  IntFmt $0 "0x%08X" $0
  WriteRegDWORD HKLM ${{UNINSTALL_REGKEY}} "EstimatedSize" "$0"
SectionEnd

;--------------------------------

; Uninstaller

Section "Uninstall"

  ; Remove registry keys
  DeleteRegKey HKLM ${{UNINSTALL_REGKEY}}
  DeleteRegKey HKLM SOFTWARE\\{program_name}

  ; Remove files and uninstaller
  Delete $INSTDIR\\uninstall.exe

  ; Remove shortcuts, if any
  Delete "$SMPROGRAMS\\{program_name}\\*.*"
  Delete "$DESKTOP\\{program_name}.lnk"

  ; Remove directories used
  RMDir "$SMPROGRAMS\\{program_name}"
  RMDir /r /REBOOTOK $INSTDIR

SectionEnd
"""
