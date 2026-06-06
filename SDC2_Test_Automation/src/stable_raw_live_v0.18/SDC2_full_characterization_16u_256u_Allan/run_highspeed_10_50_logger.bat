@echo off
REM 10-50 deg/s high-speed characterization at 16 microsteps.
set PORT=COM3
python python\sdc2_serial_logger.py --port %PORT% --command H --output runs\sdc2_16u_highspeed_10_50.csv
pause
