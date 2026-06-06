@echo off
cd /d "%~dp0"

if "%~1"=="" (
  echo Drag a raw SDC2 CSV onto this BAT file, or pass the CSV path as an argument.
  pause
  exit /b 1
)

python sdc2_logger_plotter.py --csv "%~1" --outdir SDC2_reprocessed_results
pause
