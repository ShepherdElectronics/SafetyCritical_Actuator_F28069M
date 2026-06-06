@echo off
REM Short debug run at 16 microsteps.
set PORT=COM3
python python\sdc2_serial_logger.py --port %PORT% --command D --output runs\sdc2_16u_debug.csv
pause
