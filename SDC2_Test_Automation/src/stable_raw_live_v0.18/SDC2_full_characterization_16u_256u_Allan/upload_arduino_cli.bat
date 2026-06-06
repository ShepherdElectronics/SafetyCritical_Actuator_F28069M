@echo off
REM Upload SDC2 16-ustep full characterization firmware.
REM Edit COM port as needed.
set PORT=COM3
set FQBN=arduino:mbed_giga:giga

echo Compiling...
arduino-cli compile --fqbn %FQBN% arduino\SDC2_FullChar_16u
if errorlevel 1 goto fail

echo Uploading to %PORT%...
arduino-cli upload -p %PORT% --fqbn %FQBN% arduino\SDC2_FullChar_16u
if errorlevel 1 goto fail

echo Done.
goto end

:fail
echo Compile or upload failed. Check board package, FQBN, and COM port.
:end
pause
