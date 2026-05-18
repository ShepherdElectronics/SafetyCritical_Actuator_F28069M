# 12 - Evidence Capture Naming

## Purpose

This document defines the final evidence naming convention. Visual evidence is numbered in the same order as the automated command sequence.

## Final Command Sequence

| Step | Command/Event | Evidence |
|---:|---|---|
| 00 | `RST,0` | `00_rst_ready_safe_low.png` |
| 01 | `EN,250,1` | `01_en250_pwm_25pct.png` |
| 02 | `DIS,2` | `02_dis_after_25_safe_low.png` |
| 03 | `EN,500,3` | `03_en500_pwm_50pct.png` |
| 04 | `DIS,4` | `04_dis_after_50_safe_low.png` |
| 05 | `EN,750,5` | `05_en750_pwm_75pct.png` |
| 05b | alternate 75% | `05b_en750_pwm_75pct_alternate.png` |
| 06 | `DIS,6` | `06_dis_after_75_safe_low.png` |
| 07 | `EN,500,7` | `07_en500_before_fault_pwm_50pct.png` |
| 08 | `FLT,8` | `08_flt_sensor_fault_safe_low.png` |
| 09 | `RST,9` | `09_rst_after_fault_safe_low.png` |
| 10 | `EN,1500,10` | `10_en1500_invalid_setpoint_safe_low.png` |
| 11 | `RST,11` | `11_rst_after_invalid_setpoint_safe_low.png` |
| 12 | `EN,500,12` | `12_en500_before_timeout_pwm_50pct.png` |
| 13 | CPU Timer0 timeout | `13_cpu_timer_timeout_safe_low.png` |
| 14 | final verification video | `14_final_verification_scope_and_serial.mp4` |
| 15 | timeout transition video | `15_cpu_timer_timeout_transition.mp4` |
