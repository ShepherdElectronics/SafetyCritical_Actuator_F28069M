# 09 - Verification Plan

## Environment

| Item | Value |
|---|---|
| Target | TI C2000 F28069M |
| IDE | Code Composer Studio |
| Communication | SCI/UART |
| Baud | 115200 |
| PWM Output | GPIO0 / ePWM1A |
| Evidence | Serial logs, PNG scope captures, MP4 verification videos |

## Test Cases

| ID | Test | Procedure | Expected Result |
|---|---|---|---|
| TEST-001 | Startup safe state | Load/run firmware | READY, PWM=0 |
| TEST-002 | SCI command handling | Send RST/EN/DIS/FLT | Commands parsed and telemetry updated |
| TEST-003 | PWM scaling | Send EN,250 / EN,500 / EN,750 | 25/50/75% duty on GPIO0 |
| TEST-004 | Disable safe-low | Send DIS after EN | PWM=0, state READY |
| TEST-005 | Fault safe-low | Send FLT after EN | FAULT_LATCHED, SENSOR_FAULT, PWM=0 |
| TEST-006 | Invalid setpoint | Send EN,1500 | FAULT_LATCHED, INVALID_SETPOINT, PWM=0 |
| TEST-007 | CPU Timer0 timeout | Send EN,500 and stop commands | COMMS_TIMEOUT after 3000 ms, PWM=0 |
| TEST-008 | Final integrated verification | Run full automated command sequence | All command, fault, PWM, reset, and timeout behaviors verified |

## Automated Command Sequence

```powershell
python tools/serial_auto_scope_demo.py COM6 --baud 115200 --manual
```

## Final Evidence Order

```text
00_rst_ready_safe_low.png
01_en250_pwm_25pct.png
02_dis_after_25_safe_low.png
03_en500_pwm_50pct.png
04_dis_after_50_safe_low.png
05_en750_pwm_75pct.png
05b_en750_pwm_75pct_alternate.png
06_dis_after_75_safe_low.png
07_en500_before_fault_pwm_50pct.png
08_flt_sensor_fault_safe_low.png
09_rst_after_fault_safe_low.png
10_en1500_invalid_setpoint_safe_low.png
11_rst_after_invalid_setpoint_safe_low.png
12_en500_before_timeout_pwm_50pct.png
13_cpu_timer_timeout_safe_low.png
14_final_verification_scope_and_serial.mp4
15_cpu_timer_timeout_transition.mp4
```
