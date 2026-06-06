@echo off
REM Official protocol constant-speed characterization at 16 microsteps.
set PORT=COM3
python python\sdc2_serial_logger.py --port %PORT% --command P --output runs\sdc2_16u_protocol_constants.csv
pause
