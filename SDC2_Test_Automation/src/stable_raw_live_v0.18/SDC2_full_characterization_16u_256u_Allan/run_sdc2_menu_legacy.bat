@echo off
cd /d "%~dp0"

echo.
echo ========================================
echo SDC2 MENU TEST - UPLOAD AND RUN
echo ========================================
echo.

set PORT=COM5
set FQBN=arduino:mbed_giga:giga
set SKETCH_NAME=SDC2_TestRunner_Menu
set SKETCH_DIR=%~dp0%SKETCH_NAME%
set SKETCH_FILE=%SKETCH_DIR%\%SKETCH_NAME%.ino

if not exist "%SKETCH_DIR%" (
    echo Sketch folder not found. Creating:
    echo %SKETCH_DIR%
    mkdir "%SKETCH_DIR%"
)

if not exist "%SKETCH_FILE%" (
    if exist "%~dp0%SKETCH_NAME%.ino" (
        echo Moving %SKETCH_NAME%.ino into sketch folder...
        move "%~dp0%SKETCH_NAME%.ino" "%SKETCH_FILE%"
    ) else (
        echo.
        echo ERROR: Could not find %SKETCH_NAME%.ino
        echo Expected either:
        echo   %~dp0%SKETCH_NAME%.ino
        echo or:
        echo   %SKETCH_FILE%
        echo.
        pause
        exit /b 1
    )
)

echo Using port: %PORT%
echo Using board FQBN: %FQBN%
echo Sketch file:
echo %SKETCH_FILE%
echo.

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
    echo Upload failed.
    echo Check that the Arduino is on %PORT%.
    pause
    exit /b 1
)

echo.
echo Upload complete.
echo Waiting for board reset...
timeout /t 5 /nobreak >nul

echo.
echo Starting logger/menu...
python sdc2_logger_plotter.py --port %PORT% --baud 115200 --outdir SDC2_results

pause