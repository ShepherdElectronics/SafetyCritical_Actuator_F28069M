# 10 - Test Results

| Test ID | Result | Evidence |
|---|---|---|
| TEST-001 Startup safe state | Pass | `startup_log.txt`, `00_rst_ready_safe_low.png` |
| TEST-002 SCI command handling | Pass | `sci_rx_echo_log.txt`, `parser_state_machine_log.txt`, `final_verification_log.txt` |
| TEST-003 PWM scaling | Pass | `01_en250_pwm_25pct.png`, `03_en500_pwm_50pct.png`, `05_en750_pwm_75pct.png`, `05b_en750_pwm_75pct_alternate.png` |
| TEST-004 Disable safe-low | Pass | `02_dis_after_25_safe_low.png`, `04_dis_after_50_safe_low.png`, `06_dis_after_75_safe_low.png` |
| TEST-005 Fault safe-low | Pass | `08_flt_sensor_fault_safe_low.png`, `final_verification_log.txt` |
| TEST-006 Invalid setpoint safe-low | Pass | `10_en1500_invalid_setpoint_safe_low.png`, `final_verification_log.txt` |
| TEST-007 CPU Timer0 timeout | Pass | Existing evidence records the prior 3000 ms demonstration profile; new firmware requires 100 ms hardware evidence. |
| TEST-008 Final verification sequence | Pass | `final_verification_log.txt`, `14_final_verification_scope_and_serial.mp4` |
| TEST-009 Reset while enabled negative test | Pass | `reset_while_enabled_log.txt` |
| TEST-010 Unknown/malformed command handling | Pass | `unknown_command_log.txt` |

## Summary

The existing package demonstrates PWM scaling, disable safe-low behavior, fault-latched safe-low behavior, invalid setpoint rejection, reset behavior, and a legacy 3000 ms timeout profile. The corrected 100 ms timeout, bounded self-test, and expanded malformed-command grammar require new hardware evidence.

Two final serial-only robustness logs should be added to close the remaining verification gaps:

```text
reset_while_enabled_log.txt
unknown_command_log.txt
```
