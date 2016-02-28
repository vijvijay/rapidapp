@echo off
@rem $Id: lpgs.bat 11686 2010-09-03 07:21:06Z ken $

call "%~dp0gssetgs.bat"
%GSC% -sDEVICE#djet500 -P- -dSAFER -dNOPAUSE -sPROGNAME=lpgs -- gslp.ps -fCourier9 %1 %2 %3 %4 %5 %6 %7 %8 %9
