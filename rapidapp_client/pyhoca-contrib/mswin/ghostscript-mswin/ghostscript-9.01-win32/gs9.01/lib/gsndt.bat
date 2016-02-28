@echo off
@rem $Id: gsndt.bat 11684 2010-09-03 06:52:44Z ken $

call "%~dp0gssetgs.bat"
%GSC% -P- -dSAFER -DNODISPLAY %1 %2 %3 %4 %5 %6 %7 %8 %9 >t
