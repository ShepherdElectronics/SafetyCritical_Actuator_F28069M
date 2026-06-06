@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

echo.
echo ========================================
echo SDC2 CHARACTERIZATION - 16u / 256u + ALLAN
echo ========================================
echo.

REM ============================================================
REM USER SETTINGS
REM ============================================================

set PORT=COM5
set FQBN=arduino:mbed_giga:giga
set BAUD=115200

set LOGGER=sdc2_serial_logger.py
set POST=sdc2_postprocess_fullchar.py
set ALLAN=sdc2_allan_analysis.py
set RUNS_DIR=runs

REM ============================================================
REM CHECK FILES
REM ============================================================

if not exist "%LOGGER%" (
    echo ERROR: Could not find %LOGGER%
    pause
    exit /b 1
)

if not exist "%POST%" (
    echo ERROR: Could not find %POST%
    pause
    exit /b 1
)

if not exist "%ALLAN%" (
    echo ERROR: Could not find %ALLAN%
    pause
    exit /b 1
)

if not exist "%RUNS_DIR%" mkdir "%RUNS_DIR%"

REM ============================================================
REM MICROSTEP / SKETCH SELECTION
REM ============================================================

:MICROSTEP_MENU
echo.
echo Select R725 microstep firmware to compile/upload:
echo.
echo 1 = 16 ustep    DIP: SW1=D, SW2=D, SW3=U, SW4=U
echo 2 = 256 ustep   DIP: SW1=D, SW2=D, SW3=D, SW4=U
echo 3 = Skip upload and only use logger/analyzer menu
echo 0 = Exit
echo.
set /p USTEP_CHOICE=Enter choice: 

if "%USTEP_CHOICE%"=="1" (
    set USTEP=16
    set SKETCH_NAME=SDC2_TestRunner_Menu_16u
    set OUTDIR=SDC2_results_16u
    set DIPTEXT=SW1=D, SW2=D, SW3=U, SW4=U
    goto SETUP_SKETCH
)
if "%USTEP_CHOICE%"=="2" (
    set USTEP=256
    set SKETCH_NAME=SDC2_TestRunner_Menu_256u
    set OUTDIR=SDC2_results_256u
    set DIPTEXT=SW1=D, SW2=D, SW3=D, SW4=U
    goto SETUP_SKETCH
)
if "%USTEP_CHOICE%"=="3" (
    echo.
    set /p USTEP=Enter microstep label for output folders, usually 16 or 256: 
    if "!USTEP!"=="" set USTEP=unknown
    set OUTDIR=SDC2_results_!USTEP!u
    goto MENU
)
if "%USTEP_CHOICE%"=="0" goto DONE

echo Invalid choice.
goto MICROSTEP_MENU

:SETUP_SKETCH
set SKETCH_DIR=%~dp0%SKETCH_NAME%
set SKETCH_FILE=%SKETCH_DIR%\%SKETCH_NAME%.ino

if not exist "%SKETCH_DIR%" (
    echo.
    echo ERROR: Sketch folder not found:
    echo   %SKETCH_DIR%
    pause
    exit /b 1
)

if not exist "%SKETCH_FILE%" (
    echo.
    echo ERROR: Sketch file not found:
    echo   %SKETCH_FILE%
    pause
    exit /b 1
)

if not exist "%OUTDIR%" mkdir "%OUTDIR%"

echo.
echo Using port:      %PORT%
echo Using board:     %FQBN%
echo Using baud:      %BAUD%
echo Microstep:       %USTEP% ustep
echo Required DIP:    %DIPTEXT%
echo Sketch file:
echo   %SKETCH_FILE%
echo Runs folder:
echo   %RUNS_DIR%
echo Results folder:
echo   %OUTDIR%
echo.
echo IMPORTANT: physically set the R725 DIP switches to match before running.
echo.

REM ============================================================
REM COMPILE AND UPLOAD
REM ============================================================

echo Compiling sketch...
arduino-cli compile --fqbn %FQBN% "%SKETCH_DIR%"

if errorlevel 1 (
    echo.
    echo Compile failed.
    pause
    exit /b 1
)

echo.
echo Uploading sketch to Arduino...
arduino-cli upload -p %PORT% --fqbn %FQBN% "%SKETCH_DIR%"

if errorlevel 1 (
    echo.
    echo Upload failed. Check that the Arduino is on %PORT%.
    pause
    exit /b 1
)

echo.
echo Upload complete.
echo Waiting for board reset...
timeout /t 5 /nobreak >nul

REM ============================================================
REM LOGGER MENU
REM ============================================================

:MENU
if not exist "%OUTDIR%" mkdir "%OUTDIR%"
echo.
echo ========================================
echo SDC2 LOGGER MENU - %USTEP% ustep
echo ========================================
echo.
echo 1 = DEBUG        short sanity test
echo 2 = HIGHSPEED    10, 20, 30, 40, 50 deg/s both directions
echo 3 = PROTOCOL     0.01, 0.03, 1, 3, 5, 10, 15 deg/s both directions
echo 4 = STATIC       static 50 Hz and 100 Hz hold tests for Allan deviation
echo 5 = SINE         sine velocity tests, peak 15 deg/s
echo 6 = ALL          static + protocol + highspeed + sine
echo 7 = MENU ONLY    send ? to Arduino and log response briefly
echo 8 = Analyze existing CSV: event plots + Allan plots
echo 9 = Open results folder
echo C = Change/upload microstep firmware
echo 0 = Exit
echo.
set /p CHOICE=Enter choice: 

if /I "%CHOICE%"=="1" goto RUN_DEBUG
if /I "%CHOICE%"=="2" goto RUN_HIGHSPEED
if /I "%CHOICE%"=="3" goto RUN_PROTOCOL
if /I "%CHOICE%"=="4" goto RUN_STATIC
if /I "%CHOICE%"=="5" goto RUN_SINE
if /I "%CHOICE%"=="6" goto RUN_ALL
if /I "%CHOICE%"=="7" goto RUN_INFO
if /I "%CHOICE%"=="8" goto ANALYZE_EXISTING
if /I "%CHOICE%"=="9" goto OPEN_RESULTS
if /I "%CHOICE%"=="C" goto MICROSTEP_MENU
if /I "%CHOICE%"=="0" goto DONE

echo Invalid choice.
goto MENU

:RUN_DEBUG
set CMD=D
set LABEL=debug
goto RUN_COMMAND

:RUN_HIGHSPEED
set CMD=H
set LABEL=highspeed_10_50
goto RUN_COMMAND

:RUN_PROTOCOL
set CMD=P
set LABEL=protocol_constants
goto RUN_COMMAND

:RUN_STATIC
set CMD=S
set LABEL=static_allan_source
goto RUN_COMMAND

:RUN_SINE
set CMD=N
set LABEL=sine
goto RUN_COMMAND

:RUN_ALL
set CMD=A
set LABEL=all_tests
goto RUN_COMMAND

:RUN_INFO
set CMD=?
set LABEL=arduino_menu
goto RUN_COMMAND_SHORT

:RUN_COMMAND
echo.
echo Starting %LABEL% run with Arduino command %CMD% at %USTEP% ustep...
set CSV=%RUNS_DIR%\sdc2_%USTEP%u_%LABEL%.csv
python "%LOGGER%" --port %PORT% --baud %BAUD% --command %CMD% --output "%CSV%"
if errorlevel 1 (
    echo.
    echo Logger failed or was interrupted.
    goto AFTER_RUN
)
echo.
echo Postprocessing event-based figures and summaries...
python "%POST%" --input "%CSV%" --out "%OUTDIR%\%LABEL%\event_analysis" --microstep %USTEP%

echo.
echo Running Allan deviation analysis...
python "%ALLAN%" --input "%CSV%" --out "%OUTDIR%\%LABEL%\allan_analysis" --microstep %USTEP%
goto AFTER_RUN

:RUN_COMMAND_SHORT
echo.
echo Sending command %CMD% and logging briefly...
set CSV=%RUNS_DIR%\sdc2_%USTEP%u_%LABEL%.csv
python "%LOGGER%" --port %PORT% --baud %BAUD% --command %CMD% --output "%CSV%" --max-seconds 8
if errorlevel 1 (
    echo.
    echo Logger failed or was interrupted.
)
goto AFTER_RUN

:ANALYZE_EXISTING
echo.
echo Enter CSV path to analyze.
echo Example:
echo   runs\sdc2_16u_static_allan_source.csv
echo   runs\sdc2_256u_protocol_constants.csv
echo.
set /p CSVPATH=CSV path: 

if not exist "%CSVPATH%" (
    echo.
    echo ERROR: CSV file not found:
    echo %CSVPATH%
    goto AFTER_RUN
)

echo.
echo Enter output subfolder name, or press Enter for existing_csv_analysis.
set /p SUBOUT=Output subfolder: 
if "%SUBOUT%"=="" set SUBOUT=existing_csv_analysis

echo.
echo Running event-based postprocess...
python "%POST%" --input "%CSVPATH%" --out "%OUTDIR%\%SUBOUT%\event_analysis" --microstep %USTEP%

echo.
echo Running Allan deviation analysis...
python "%ALLAN%" --input "%CSVPATH%" --out "%OUTDIR%\%SUBOUT%\allan_analysis" --microstep %USTEP%
goto AFTER_RUN

:OPEN_RESULTS
echo.
if not exist "%OUTDIR%" (
    echo Results folder does not exist yet: %OUTDIR%
) else (
    explorer "%OUTDIR%"
)
goto MENU

:AFTER_RUN
echo.
echo ========================================
echo Run/analyze step finished.
echo ========================================
echo.
echo Runs are in:
echo   %CD%\%RUNS_DIR%
echo Results are in:
echo   %CD%\%OUTDIR%
echo.
echo Event figures are under: event_analysis
echo Allan figures are under: allan_analysis\allan_figures
echo.
echo Options:
echo   M = return to menu
echo   O = open results folder
echo   C = change/upload microstep firmware
echo   X = exit
echo.
set /p NEXT=Enter M, O, C, or X: 

if /I "%NEXT%"=="M" goto MENU
if /I "%NEXT%"=="O" (
    if exist "%OUTDIR%" explorer "%OUTDIR%"
    goto MENU
)
if /I "%NEXT%"=="C" goto MICROSTEP_MENU
if /I "%NEXT%"=="X" goto DONE

goto MENU

:DONE
echo.
echo Done.
pause
endlocal
