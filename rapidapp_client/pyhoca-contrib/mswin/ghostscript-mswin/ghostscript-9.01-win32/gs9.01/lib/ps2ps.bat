@echo off 
@rem $Id: ps2ps.bat 11952 2010-12-15 16:12:54Z ken $
@rem "Distill" PostScript.

if %1/==/ goto usage
if %2/==/ goto usage
call "%~dp0gssetgs.bat"
echo -dNOPAUSE -P- -dSAFER -dBATCH >"%TEMP%\_.at"
:cp
if %3/==/ goto doit
echo %1 >>"%TEMP%\_.at"
shift
goto cp

:doit
rem Watcom C deletes = signs, so use # instead.
%GSC% -q -sDEVICE#ps2write -sOutputFile#%2 @"%TEMP%\_.at" %1
if exist "%TEMP%\_.at" erase "%TEMP%\_.at"
goto end

:usage
echo "Usage: ps2ps [options] input.ps output.ps"
echo "  e.g. ps2ps -sPAPERSIZE=a4 input.ps output.ps

:end
