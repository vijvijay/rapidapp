@echo off 
@rem $Id: pfbtopfa.bat 11684 2010-09-03 06:52:44Z ken $
@rem Convert .pfb fonts to .pfa format

if %1/==/ goto usage
if %2/==/ goto usage
if not %3/==/ goto usage
call "%~dp0gssetgs.bat"

%GSC% -P- -dSAFER -q -dNODISPLAY -- pfbtopfa.ps %1 %2
goto end

:usage
echo "Usage: pfbtopfa input.pfb output.pfa"

:end
